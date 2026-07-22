"""
analyze.py  — "รวมร่าง" pipeline ครบวงจร (ZoneScope backend core)
---------------------------------
รับภาพจาน 1 ใบ + ชนิดเชื้อ  ->  ผล S/I/R ต่อแผ่น

ขั้นตอน:
  1. หาแผ่น + คาลิเบรต (px/mm)      : Hough (reuse 01_number_disks.py)
  2. ตรวจ zone (วงยับยั้ง)          : Roboflow workflow serverless (zone_infer.py)  *ใช้ credit*
  3. อ่านชื่อยาบนแผ่น               : easyocr (reuse 04_ocr_disks.py)
  4. จับคู่ zone<->แผ่น + วัด มม.    : zone concentric กับแผ่น
  5. ตัดสิน S/I/R                    : interpret.py + breakpoints.json

หมายเหตุ credit: zone (ขั้น 2) เรียก serverless คิด credit -> cache ผลไว้ที่ zone_cache/
  เรียกซ้ำภาพเดิมใช้ cache (0 credit) เว้นแต่ส่ง use_cache=False

พิกัด: geometry ทำงานใน "ภาพย่อ long=1500" (ตรงกับ 01) — zone จาก Roboflow (พิกัดภาพต้นฉบับ)
       ถูกสเกลเข้ามาที่ 1500 ก่อนจับคู่/วัด

CLI:  python analyze.py <plate.jpg> <organism_id>
      เช่น  python analyze.py ".../P001.jpg" enterobacterales
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

import cv2

import zone_backend as zone_infer   # สลับ local/roboflow ให้อัตโนมัติ (ดู zone_backend.py)
import interpret as interp

BACKEND = Path(__file__).resolve().parent
DISK_MM = 6.0                 # แผ่น 6mm — floor เมื่อไม่มี zone (§9.4)
RESIZE_LONG = 1500            # ต้องตรงกับ 01/04
ZONE_EDGE_PCT = 80            # percentile ของระยะขอบ zone (ดู fit_zone_diameter) — จูนจาก val 13 ภาพ
ZONE_CACHE = BACKEND / "zone_cache"
BUILD_REPORT = BACKEND / "zonescope_out" / "build_report.csv"


def _load_module(filename, modname):
    """โหลดไฟล์ที่ชื่อขึ้นต้นด้วยตัวเลข (import ปกติไม่ได้) เป็น module"""
    spec = importlib.util.spec_from_file_location(modname, BACKEND / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_disk = _load_module("01_number_disks.py", "zs_disk01")
_ocr = _load_module("04_ocr_disks.py", "zs_ocr04")


def _ocr_candidates():
    """รหัสยาที่ใช้ match OCR — จากชุดจริงใน build_report (แม่นสุดตามที่เทสต์ 89%)"""
    cands = set()
    if BUILD_REPORT.exists():
        with open(BUILD_REPORT, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                a = (row.get("antibiotic") or "").strip()
                if a and _ocr.norm(a):
                    cands.add(a)
    return sorted(cands)


def get_zones(image_path, use_cache=True):
    """ตรวจ zone (โมเดลเราเอง หรือ Roboflow — ดู zone_backend) -> list พิกัดภาพต้นฉบับ

    ใช้ extract_predictions เพื่อเก็บ polygon "points" ไว้ด้วย เพราะ fit_zone_diameter
    ต้องใช้ขอบวงจริง ไม่ใช่แค่กรอบ bbox
    """
    ZONE_CACHE.mkdir(exist_ok=True)
    cache = ZONE_CACHE / f"{Path(image_path).stem}.json"
    if use_cache and cache.exists():
        entry = json.loads(cache.read_text(encoding="utf-8"))
    else:
        outputs = zone_infer.run_zone_workflow(str(image_path))
        entry = outputs[0] if outputs else {}
        cache.write_text(json.dumps(entry), encoding="utf-8")  # กัน credit รอบหน้า
    return zone_infer.extract_predictions(entry)


def fit_zone_diameter(points, cx, cy, scale=1.0):
    """เส้นผ่านศูนย์กลาง zone โดยวัดจาก "ศูนย์กลางแผ่นยา" ออกไปหาขอบ polygon

    ทำไมไม่ใช้กรอบ bbox ตรงๆ: เมื่อ zone ซ้อนกัน mask จะถูกวงข้างเคียงตัด กรอบเลยเล็ก
    กว่าจริง (วัดได้ต่ำกว่าความจริงอย่างเป็นระบบ ~3%)

    วิธีนี้: zone เป็นวงกลมร่วมศูนย์กับแผ่น และศูนย์กลางแผ่นได้จาก Hough ซึ่งไม่ถูกบัง
    จุดขอบที่โดนตัดจะอยู่ "ใกล้" ศูนย์กลางผิดปกติ จึงใช้ percentile สูงแทนค่าสูงสุด/เฉลี่ย
    — ข้ามส่วนที่ถูกตัดได้โดยไม่ไวต่อจุด outlier

    วัดกับ ground truth 13 ภาพ: bias -2.9% -> +0.2% (ความกระจายเท่าเดิม ~6.8%)

    points : [{"x":..,"y":..}] พิกัดจากโมเดล (ภาพต้นฉบับ)
    cx, cy : ศูนย์กลางแผ่น — ต้องอยู่ในระบบพิกัดที่ต้องการผลลัพธ์
    scale  : ตัวคูณแปลง points ให้เข้าระบบพิกัดของ cx,cy (1.0 = ระบบเดียวกัน)
    คืน None ถ้าไม่มี polygon -> ผู้เรียกควร fallback ไปใช้ bbox
    """
    dists = []
    for p in points or []:
        px, py = p.get("x"), p.get("y")
        if px is None or py is None:
            continue
        dists.append((((px * scale) - cx) ** 2 + ((py * scale) - cy) ** 2) ** 0.5)
    if not dists:
        return None
    dists.sort()
    k = (len(dists) - 1) * ZONE_EDGE_PCT / 100.0      # percentile แบบ interpolate (เท่า numpy)
    lo = int(k)
    hi = min(lo + 1, len(dists) - 1)
    radius = dists[lo] + (dists[hi] - dists[lo]) * (k - lo)
    return radius * 2.0


def _crop_disk(img0, cx1500, cy1500, r1500, up):
    """crop แผ่นจากภาพต้นฉบับ (เหมือน 04) -> ภาพขยายพร้อม OCR"""
    cxo, cyo, ro = cx1500 * up, cy1500 * up, r1500 * up
    pad = ro * _ocr.PAD_RATIO
    H0, W0 = img0.shape[:2]
    x0, y0 = max(0, int(cxo - pad)), max(0, int(cyo - pad))
    x1, y1 = min(W0, int(cxo + pad)), min(H0, int(cyo + pad))
    crop = img0[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    h = crop.shape[0]
    if h < _ocr.UPSCALE_TO:
        s = _ocr.UPSCALE_TO / h
        crop = cv2.resize(crop, (int(crop.shape[1] * s), int(crop.shape[0] * s)),
                          interpolation=cv2.INTER_CUBIC)
    return crop


def analyze_plate(image_path, organism, use_cache=True):
    bp = interp.load_breakpoints()
    candidates = interp.ocr_candidates(bp)         # disk-print codes
    alias_map = interp.disk_alias_map(bp)          # disk-code -> system code
    reader = _ocr.easyocr.Reader(["en"], gpu=False, verbose=False)

    img0 = cv2.imread(str(image_path))
    if img0 is None:
        raise FileNotFoundError(f"อ่านภาพไม่ได้: {image_path}")
    H0, W0 = img0.shape[:2]
    scale = RESIZE_LONG / max(H0, W0)          # ต้นฉบับ -> 1500
    up = 1.0 / scale                            # 1500 -> ต้นฉบับ
    img = cv2.resize(img0, (int(W0 * scale), int(H0 * scale)))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. แผ่น + คาลิเบรต (พิกัด 1500-space)
    disks, ppm = _disk.detect_disks(gray)
    disks = _disk.order_clockwise(disks)
    if not ppm:
        raise RuntimeError("คาลิเบรตไม่ได้ (หาแผ่นไม่เจอ)")

    # 2. zone (พิกัดต้นฉบับ) -> สเกลเข้า 1500-space
    zones = get_zones(image_path, use_cache=use_cache)
    z1500 = []
    for z in zones:
        if z.get("x") is None:
            continue
        z1500.append({
            "cx": z["x"] * scale, "cy": z["y"] * scale,
            "d": ((z.get("width", 0) + z.get("height", 0)) / 2.0) * scale,   # fallback
            "points": z.get("points"),          # พิกัดต้นฉบับ — fit_zone_diameter สเกลเอง
            "conf": z.get("confidence"),
        })

    # 3+4+5 ต่อแผ่น
    results = []
    for i, (cx, cy, r) in enumerate(disks, start=1):
        crop = _crop_disk(img0, cx, cy, r, up)
        abx, ocr_score = "", 0.0
        if crop is not None:
            _, alias, ocr_score = _ocr.ocr_best(reader, crop, candidates)
            abx = alias_map.get(interp._norm(alias), alias) if alias else ""  # -> system code

        # จับ zone ที่ center ใกล้แผ่นสุด (zone concentric กับแผ่น)
        best_z, best_d = None, r * 2.0
        for z in z1500:
            dist = ((z["cx"] - cx) ** 2 + (z["cy"] - cy) ** 2) ** 0.5
            if dist < best_d:
                best_z, best_d = z, dist

        if best_z is not None:
            # วัดจากศูนย์กลางแผ่น (แม่นกว่า) ถ้าไม่มี polygon ค่อยถอยไปใช้ bbox
            d_px = fit_zone_diameter(best_z.get("points"), cx, cy, scale) or best_z["d"]
            diameter_mm = round(d_px / ppm, 1)
            zone_conf = best_z["conf"]
        else:
            diameter_mm = DISK_MM          # ไม่มี zone = ดื้อสนิท (§9.4)
            zone_conf = None
        if diameter_mm < DISK_MM:
            diameter_mm = DISK_MM

        sir = interp.interpret(bp, organism, abx, diameter_mm)
        results.append({
            "disk_no": i,
            "antibiotic": abx,
            "ocr_score": ocr_score,
            "diameter_mm": diameter_mm,
            "zone_conf": round(zone_conf, 3) if zone_conf else None,
            "result": sir["result"],
            "reason": sir.get("reason", ""),
        })

    return {
        "image": Path(image_path).name,
        "organism": organism,
        "px_per_mm": round(ppm, 3),
        "n_disks": len(disks),
        "n_zones": len(z1500),
        "verified_by_lab": bp.get("verified_by_lab", False),
        "results": results,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("ใช้: python analyze.py <plate.jpg> <organism_id>")
        print("organism_id เช่น: enterobacterales, escherichia_coli, pseudomonas_aeruginosa")
        raise SystemExit(2)
    out = analyze_plate(sys.argv[1], sys.argv[2])
    print(f"\n=== {out['image']} | เชื้อ: {out['organism']} | "
          f"px/mm {out['px_per_mm']} | แผ่น {out['n_disks']} | zone {out['n_zones']} ===")
    print(f"{'#':>2}  {'ยา(OCR)':<10} {'มม.':>6}  {'S/I/R':<5} {'zoneConf':>8}")
    for r in out["results"]:
        print(f"{r['disk_no']:>2}  {r['antibiotic']:<10} {r['diameter_mm']:>6}  "
              f"{r['result']:<5} {str(r['zone_conf']):>8}")
    if not out["verified_by_lab"]:
        print("\n⚠️  breakpoints ยังไม่ผ่านการรับรอง (verified_by_lab=false) — ห้ามใช้ตัดสินผลจริง")
