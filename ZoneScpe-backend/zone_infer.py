"""
zone_infer.py
---------------------------------
เรียก Roboflow Workflow (serverless) เพื่อตรวจ "inhibition zone" บนภาพจาน disk diffusion

Workflow:
  name       : disk-zone-detect vdisk-zone-detect-1-yolov8s-seg-t1 Logic
  workspace  : nuxh
  workflow_id: disk-zone-detect-vdisk-zone-detect-1-yolov8s-seg-t1-logic
  endpoint   : POST https://serverless.roboflow.com/nuxh/workflows/<workflow_id>
  input      : image (image)

การจัดการ key:
  อ่าน ROBOFLOW_API_KEY จาก environment variable หรือไฟล์ .env ข้างไฟล์นี้
  *** ห้าม hardcode key ในโค้ด *** (หาได้ที่ app.roboflow.com/settings/api)

ใช้ stdlib ล้วน (urllib) ไม่ต้องลง dependency เพิ่ม

CLI:
  python zone_infer.py <path/to/plate.jpg>
"""
import base64
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

WORKSPACE   = "nuxh"
WORKFLOW_ID = "disk-zone-detect-vdisk-zone-detect-1-yolov8s-seg-t1-logic"
ENDPOINT    = f"https://serverless.roboflow.com/{WORKSPACE}/workflows/{WORKFLOW_ID}"
TIMEOUT_S   = 60
RETRIES     = 3
# ฟิลด์ที่เก็บต่อ prediction (ไม่เอา polygon "points" ดิบ payload จะได้ไม่บวม)
ZONE_FIELDS = ("x", "y", "width", "height", "confidence", "class", "class_id", "detection_id")


class ZoneInferError(RuntimeError):
    """error ของการเรียก zone workflow (network / http / config)"""


def load_api_key():
    """อ่าน ROBOFLOW_API_KEY จาก env ก่อน ถ้าไม่มีลองไฟล์ .env ข้างสคริปต์"""
    import os
    key = os.environ.get("ROBOFLOW_API_KEY", "").strip()
    if not key:
        envf = Path(__file__).with_name(".env")
        if envf.exists():
            for line in envf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("ROBOFLOW_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        raise ZoneInferError(
            "ไม่พบ ROBOFLOW_API_KEY — ตั้ง environment variable หรือใส่ในไฟล์ .env "
            "(ดูตัวอย่างที่ .env.example)"
        )
    return key


def _image_to_base64(image_path):
    p = Path(image_path)
    if not p.exists():
        raise ZoneInferError(f"ไม่พบไฟล์ภาพ: {p}")
    return base64.b64encode(p.read_bytes()).decode("ascii")


def run_zone_workflow(image_path, api_key=None, timeout=TIMEOUT_S, retries=RETRIES):
    """
    ยิงภาพเข้า Roboflow workflow แล้วคืน "list ของผลต่อภาพ"
    (แต่ละ entry = dict คีย์ตามชื่อ output ของ workflow เอง — parse แบบ defensive)

    raise ZoneInferError เมื่อ config/network/http ผิดพลาด (หลัง retry แล้ว)
    """
    key = api_key or load_api_key()
    payload = json.dumps({
        "api_key": key,
        "inputs": {"image": {"type": "base64", "value": _image_to_base64(image_path)}},
    }).encode("utf-8")

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                ENDPOINT, data=payload, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            # serverless คืน {"outputs": [ {output_name: ...}, ... ]}
            outputs = body.get("outputs", body)
            if not isinstance(outputs, list):
                outputs = [outputs]
            return outputs
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:300]
            last_err = ZoneInferError(f"HTTP {e.code} จาก Roboflow: {detail}")
            if e.code in (401, 403, 404):     # key ผิด/ไม่มีสิทธิ์/ไม่พบ workflow -> ไม่ retry
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = ZoneInferError(f"เชื่อมต่อ Roboflow ไม่ได้: {e}")
        except (ValueError, KeyError) as e:
            last_err = ZoneInferError(f"response ไม่ใช่ JSON ที่คาดไว้: {e}")
            break
        if attempt < retries:
            time.sleep(1.5 * attempt)          # backoff
    raise last_err


def extract_zones(entry):
    """
    ดึง prediction ของ zone จาก entry (1 ภาพ) แบบ defensive
    หา dict ที่มีคีย์ 'predictions' เป็น list แล้วเก็บเฉพาะฟิลด์ที่ใช้ (ไม่เอา polygon points)
    """
    zones = []
    if not isinstance(entry, dict):
        return zones
    for val in entry.values():
        preds = val.get("predictions") if isinstance(val, dict) else (
            val if isinstance(val, list) else None)
        if isinstance(preds, list):
            for p in preds:
                if isinstance(p, dict) and ("x" in p or "width" in p):
                    zones.append({k: p.get(k) for k in ZONE_FIELDS})
    return zones


def extract_predictions(entry):
    """
    คืน list ของ prediction "ดิบ" (มี points/polygon ครบ) — ใช้ตอนต้องวาดวงให้ frontend
    (ต่างจาก extract_zones ที่ตัด points ทิ้งเพื่อ payload เล็ก)
    """
    if not isinstance(entry, dict):
        return []
    for val in entry.values():
        preds = val.get("predictions") if isinstance(val, dict) else (
            val if isinstance(val, list) else None)
        if isinstance(preds, list):
            return preds
    return []


def save_image_outputs(entry, out_dir):
    """
    เขียน output ที่เป็นภาพ (base64) ลงดิสก์ — ไม่ log/ไม่ถือใน memory นาน
    คืน list ของ path ที่เซฟ
    """
    saved = []
    if not isinstance(entry, dict):
        return saved
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for key, val in entry.items():
        b64 = None
        if isinstance(val, str):
            b64 = val
        elif isinstance(val, dict) and isinstance(val.get("value"), str):
            b64 = val["value"]
        if b64 and len(b64) > 1000:            # น่าจะเป็นภาพ (blob ใหญ่)
            try:
                raw = base64.b64decode(b64, validate=True)
            except Exception:
                continue
            if raw[:3] == b"\xff\xd8\xff" or raw[:8] == b"\x89PNG\r\n\x1a\n":  # JPEG/PNG
                ext = "jpg" if raw[:3] == b"\xff\xd8\xff" else "png"
                path = out / f"{key}.{ext}"
                path.write_bytes(raw)
                saved.append(str(path))
    return saved


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("ใช้: python zone_infer.py <path/to/plate.jpg>")
        raise SystemExit(2)
    outputs = run_zone_workflow(sys.argv[1])
    print(f"จำนวนภาพในผล: {len(outputs)}")
    for i, entry in enumerate(outputs):
        keys = list(entry.keys()) if isinstance(entry, dict) else type(entry).__name__
        zones = extract_zones(entry)
        print(f"[image {i}] output keys: {keys}")
        print(f"           zones detected: {len(zones)}")
        for z in zones[:12]:
            print(f"             - {z.get('class')} conf={z.get('confidence')} "
                  f"w={z.get('width')} h={z.get('height')}")
        saved = save_image_outputs(entry, Path(__file__).with_name("zone_infer_out"))
        if saved:
            print(f"           saved image outputs: {saved}")
