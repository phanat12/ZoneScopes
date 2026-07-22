"""
server.py — FastAPI backend ของ ZoneScope
---------------------------------
ห่อ pipeline (analyze.py) เป็น REST ให้ frontend เรียก (web_spec §6)

endpoints:
  POST /api/analyze     multipart field "image"  -> ผลตาม analyze.json shape
                        (disks + zone polygon + ocr_guess + flags; **ไม่มี S/I/R** — client คำนวณเอง)
  GET  /api/breakpoints -> breakpoints.json (เกณฑ์ S/I/R)
  POST /api/report      -> { ok, csv_url, pdf_url }  (stub — ต่อ export ทีหลัง)
  /uploads/*            static: ภาพจาน + crop ต่อแผ่น

พิกัดทุกอย่างในผล = พิกเซล "ภาพต้นฉบับ" (ตรงกับ image_url/width/height) — frontend สเกลเอง

หมายเหตุ credit: zone เรียก Roboflow serverless (คิด credit) แต่ cache ตาม cache_key
  (= ชื่อไฟล์ที่อัปโหลด) เรียกภาพเดิมซ้ำ = 0 credit

รัน:  python -m uvicorn server:app --port 8000
      (แล้ว frontend ตั้ง VITE_USE_MOCK=false -> proxy /api -> :8000)
"""
import json
import os
import shutil
import uuid
from pathlib import Path

import cv2
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import analyze as az
import interpret as interp
import zone_backend as zone_infer   # สลับ local/roboflow ให้อัตโนมัติ (ดู zone_backend.py)

BACKEND = Path(__file__).resolve().parent
UPLOADS = BACKEND / "uploads"
UPLOADS.mkdir(exist_ok=True)

app = FastAPI(title="ZoneScope backend", version="0.1.0")

# CORS — ตั้ง origin ของ frontend ผ่าน env ZONESCOPE_CORS_ORIGINS (คั่นด้วย ,)
# ค่าเริ่มต้น "*" สำหรับ dev; production ควรระบุ domain Vercel จริง
_origins = os.environ.get("ZONESCOPE_CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _origins.strip() == "*" else [o.strip() for o in _origins.split(",")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _zone_flags(conf):
    return ["low_confidence"] if (conf is not None and conf < 0.5) else []


def _load_zone_entry(image_path, cache_key, use_cache=True):
    """เรียก workflow หรือใช้ cache (คีย์ = cache_key) -> raw entry (มี points)"""
    az.ZONE_CACHE.mkdir(exist_ok=True)
    cache = az.ZONE_CACHE / f"{cache_key}.json"
    if use_cache and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    outputs = zone_infer.run_zone_workflow(str(image_path))
    entry = outputs[0] if outputs else {}
    cache.write_text(json.dumps(entry), encoding="utf-8")
    return entry


def build_response(image_path, image_id, cache_key, use_cache=True):
    """สร้าง dict ตาม analyze.json contract (พิกัดภาพต้นฉบับ)"""
    img0 = cv2.imread(str(image_path))
    if img0 is None:
        raise HTTPException(400, f"อ่านภาพไม่ได้: {Path(image_path).name}")
    H0, W0 = img0.shape[:2]
    scale = az.RESIZE_LONG / max(H0, W0)      # ต้นฉบับ -> 1500 (สำหรับหาแผ่น)
    up = 1.0 / scale                           # 1500 -> ต้นฉบับ
    img = cv2.resize(img0, (int(W0 * scale), int(H0 * scale)))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    disks, ppm = az._disk.detect_disks(gray)
    disks = az._disk.order_clockwise(disks)
    ppm_orig = (ppm or 0) * up                 # px/mm ในภาพต้นฉบับ

    entry = _load_zone_entry(image_path, cache_key, use_cache)
    preds = zone_infer.extract_predictions(entry)

    reader = az._ocr.easyocr.Reader(["en"], gpu=False, verbose=False)
    bp = interp.load_breakpoints()
    cands = interp.ocr_candidates(bp)          # disk-print codes (aliases)
    alias_map = interp.disk_alias_map(bp)      # disk-code -> system code

    out_dir = UPLOADS / image_id
    (out_dir / "crops").mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_dir / "plate.jpg"), img0)

    disks_out, xs, ys = [], [], []
    for i, (cx, cy, r) in enumerate(disks, start=1):
        cxo, cyo, ro = cx * up, cy * up, r * up
        xs.append(cxo); ys.append(cyo)

        # OCR ชื่อยา
        crop = az._crop_disk(img0, cx, cy, r, up)
        code, score, crop_url = "", 0.0, None
        if crop is not None:
            _, alias, score = az._ocr.ocr_best(reader, crop, cands)
            code = alias_map.get(interp._norm(alias), alias) if alias else ""  # -> system code
            cv2.imwrite(str(out_dir / "crops" / f"d{i}.jpg"), crop)
            crop_url = f"/uploads/{image_id}/crops/d{i}.jpg"

        # จับ zone ที่ center ใกล้แผ่นสุด (zone concentric กับแผ่น)
        best, bestd = None, ro * 2.0
        for p in preds:
            if p.get("x") is None:
                continue
            d = ((p["x"] - cxo) ** 2 + (p["y"] - cyo) ** 2) ** 0.5
            if d < bestd:
                best, bestd = p, d

        if best is not None:
            diam_px = (best.get("width", 0) + best.get("height", 0)) / 2.0
            diameter_mm = round(diam_px / ppm_orig, 1) if ppm_orig else None
            if diameter_mm is not None and diameter_mm < az.DISK_MM:
                diameter_mm = az.DISK_MM
            conf = round(float(best.get("confidence", 0)), 3)
            polygon = [[round(pt["x"], 1), round(pt["y"], 1)]
                       for pt in best.get("points", []) if "x" in pt]
            zone = {"diameter_mm": diameter_mm, "radius_px": int(round(diam_px / 2)),
                    "polygon": polygon, "confidence": conf, "flags": _zone_flags(conf)}
        else:
            zone = {"diameter_mm": az.DISK_MM, "radius_px": int(round(ro)),
                    "polygon": [], "confidence": 0.9, "flags": ["no_zone"]}

        disks_out.append({
            "id": f"d{i}", "index": i,
            "cx": round(cxo, 1), "cy": round(cyo, 1), "r_px": int(round(ro)),
            "crop_url": crop_url,
            "ocr_guess": ({"code": code, "confidence": round(score, 2)} if code else None),
            "zone": zone,
        })

    # dish (วงครอบแผ่นทั้งหมด — ใช้ frontend จัดเฟรม)
    if xs:
        dcx, dcy = sum(xs) / len(xs), sum(ys) / len(ys)
        dr = max(((x - dcx) ** 2 + (y - dcy) ** 2) ** 0.5 for x, y in zip(xs, ys))
        dr += ppm_orig * 8 if ppm_orig else 100
    else:
        dcx, dcy, dr = W0 / 2, H0 / 2, min(W0, H0) / 2

    return {
        "image_id": image_id,
        "image_url": f"/uploads/{image_id}/plate.jpg",
        "width": W0, "height": H0,
        "exif_orientation_applied": True,
        "dish": {"cx": round(dcx, 1), "cy": round(dcy, 1), "r": round(dr, 1)},
        "calibration": {"px_per_mm": round(ppm_orig, 2), "source": "disk_6mm",
                        "n_disks_used": len(disks), "disk_ellipticity": 0.0},
        "disks": disks_out,
        "warnings": [],
    }


@app.post("/api/analyze")
async def api_analyze(image: UploadFile = File(...)):
    cache_key = Path(image.filename or "plate").stem or "plate"
    image_id = uuid.uuid4().hex[:8]
    tmp = UPLOADS / f"_tmp_{image_id}.jpg"
    with open(tmp, "wb") as f:
        shutil.copyfileobj(image.file, f)
    try:
        return build_response(tmp, image_id, cache_key, use_cache=True)
    finally:
        tmp.unlink(missing_ok=True)


@app.get("/api/breakpoints")
async def api_breakpoints():
    return interp.load_breakpoints()


@app.post("/api/report")
async def api_report(payload: dict):
    # stub — เก็บ payload ไว้ก่อน ต่อ CSV/PDF ทีหลัง (§5.4)
    (UPLOADS / "last_report.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "csv_url": None, "pdf_url": None}


app.mount("/uploads", StaticFiles(directory=str(UPLOADS)), name="uploads")
