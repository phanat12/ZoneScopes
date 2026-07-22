"""
zone_local.py
---------------------------------
ตรวจ "inhibition zone" ด้วยโมเดลที่เราเทรนเอง (YOLOv8-seg ผ่าน ultralytics)

ต่างจาก zone_infer.py (Roboflow serverless) ตรงที่:
  - รันในเครื่อง/บนเซิร์ฟเวอร์เอง -> **ไม่ใช้ credit ไม่จำกัดจำนวนภาพ**
  - ไม่ต้องต่อเน็ต
  - แลกกับใช้ RAM มากขึ้น (โหลด torch + weight)

รูปแบบผลลัพธ์ทำให้ "เหมือน Roboflow" ทุกประการ เพื่อให้ extract_zones / extract_predictions
ของ zone_infer.py ใช้กับผลจากที่นี่ได้เลย (พิกัด x,y = จุดกึ่งกลาง, หน่วยเป็น px ของภาพต้นฉบับ)

env ที่ปรับได้:
  ZONE_WEIGHTS  path ไฟล์ weight            (ค่าเริ่มต้น: weights/best.pt ข้างไฟล์นี้)
  ZONE_CONF     confidence ขั้นต่ำ           (ค่าเริ่มต้น 0.25)
  ZONE_IMGSZ    ขนาดภาพตอน inference        (ค่าเริ่มต้น 1024 — ต้องตรงกับตอนเทรน)

CLI:
  python zone_local.py <path/to/plate.jpg>
"""
import os
from pathlib import Path

BACKEND = Path(__file__).resolve().parent

WEIGHTS = Path(os.environ.get("ZONE_WEIGHTS") or (BACKEND / "weights" / "best.pt"))
CONF = float(os.environ.get("ZONE_CONF", "0.25"))
IMGSZ = int(os.environ.get("ZONE_IMGSZ", "1024"))

_model = None


class ZoneLocalError(RuntimeError):
    """error ของการตรวจ zone ด้วยโมเดลในเครื่อง (ไม่พบ weight / ultralytics ไม่ได้ลง)"""


def available():
    """มี weight พร้อมใช้ไหม — ใช้ตัดสินใจ fallback ไป Roboflow"""
    return WEIGHTS.is_file()


def _load():
    """โหลดโมเดลครั้งเดียวแล้ว cache ไว้ (โหลดใหม่ทุก request จะช้ามาก)"""
    global _model
    if _model is None:
        if not WEIGHTS.is_file():
            raise ZoneLocalError(
                f"ไม่พบไฟล์ weight ที่ {WEIGHTS} — วางไฟล์ best.pt ไว้ที่นั่น "
                "หรือชี้ path ใหม่ผ่าน env ZONE_WEIGHTS"
            )
        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise ZoneLocalError(
                "ยังไม่ได้ติดตั้ง ultralytics (pip install ultralytics)"
            ) from e
        _model = YOLO(str(WEIGHTS))
    return _model


def run_zone_workflow(image_path, **_kw):
    """
    ตรวจ zone ในภาพ 1 ใบ — คืนโครงสร้างเดียวกับ zone_infer.run_zone_workflow
    คือ list ที่มี entry เดียว: [{"predictions": [...]}]

    รับ **_kw ไว้เฉยๆ เพื่อให้สลับกับ zone_infer ได้โดยไม่พังเรื่อง signature
    """
    model = _load()
    result = model.predict(str(image_path), conf=CONF, imgsz=IMGSZ, verbose=False)[0]

    preds = []
    boxes = result.boxes
    if boxes is None:
        return [{"predictions": preds}]

    # masks.xy = polygon พิกัด px ของภาพต้นฉบับ (ultralytics สเกลกลับให้แล้ว)
    polys = result.masks.xy if result.masks is not None else None

    for i in range(len(boxes)):
        cx, cy, w, h = (float(v) for v in boxes.xywh[i].tolist())
        points = []
        if polys is not None and i < len(polys):
            points = [{"x": float(px), "y": float(py)} for px, py in polys[i]]
        preds.append({
            "x": cx, "y": cy, "width": w, "height": h,
            "confidence": float(boxes.conf[i]),
            "class": "zone",
            "class_id": 0,
            "detection_id": f"local-{i}",
            "points": points,
        })

    return [{"predictions": preds}]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("ใช้: python zone_local.py <path/to/plate.jpg>")
        raise SystemExit(2)
    print(f"weights: {WEIGHTS} (มีไฟล์: {available()})")
    entry = run_zone_workflow(sys.argv[1])[0]
    zones = entry["predictions"]
    print(f"zones detected: {len(zones)}")
    for z in zones:
        print(f"  - conf={z['confidence']:.3f} "
              f"center=({z['x']:.0f},{z['y']:.0f}) "
              f"w={z['width']:.0f} h={z['height']:.0f} pts={len(z['points'])}")
