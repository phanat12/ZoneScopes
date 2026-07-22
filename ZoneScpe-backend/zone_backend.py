"""
zone_backend.py
---------------------------------
ตัวสลับว่าจะตรวจ zone ด้วยอะไร ระหว่าง

  local     โมเดลที่เราเทรนเอง (zone_local.py + weights/best.pt) — ไม่ใช้ credit
  roboflow  Roboflow serverless (zone_infer.py)                  — ใช้ credit ต่อภาพ

เลือกผ่าน env `ZONE_BACKEND`:
  local     บังคับใช้โมเดลเรา (ไม่มี weight = error ชัดเจน ไม่แอบไปเผา credit)
  roboflow  บังคับใช้ Roboflow
  auto      (ค่าเริ่มต้น) ใช้ local ถ้ามี weight ไม่งั้น fallback ไป Roboflow

extract_zones / extract_predictions ใช้ของ zone_infer ได้เลย เพราะ zone_local
จงใจคืนผลรูปแบบเดียวกัน

วิธีใช้ในโค้ดเดิม: เปลี่ยน `import zone_infer` -> `import zone_backend as zone_infer`
"""
import os

import zone_infer
import zone_local
# re-export — รูปแบบผลของทั้งสอง backend เหมือนกัน จึง parse ด้วยตัวเดียวกันได้
from zone_infer import (  # noqa: F401
    ZoneInferError,
    extract_predictions,
    extract_zones,
    save_image_outputs,
)
from zone_local import ZoneLocalError  # noqa: F401


def mode():
    """ค่าที่ผู้ใช้ตั้งไว้ (อ่านทุกครั้ง เผื่อ env เปลี่ยนตอน runtime/เทสต์)"""
    return (os.environ.get("ZONE_BACKEND") or "auto").strip().lower()


def active():
    """backend ที่จะถูกใช้จริงตอนนี้ -> 'local' หรือ 'roboflow'"""
    m = mode()
    if m == "roboflow":
        return "roboflow"
    if m == "local":
        return "local"
    return "local" if zone_local.available() else "roboflow"


def run_zone_workflow(image_path, **kw):
    """ตรวจ zone ตาม backend ที่เลือก — คืนโครงสร้างเดียวกันทั้งสองทาง"""
    if active() == "local":
        return zone_local.run_zone_workflow(image_path, **kw)
    return zone_infer.run_zone_workflow(image_path, **kw)


if __name__ == "__main__":
    print(f"ZONE_BACKEND = {mode()}")
    print(f"weight ที่ {zone_local.WEIGHTS} -> มีไฟล์: {zone_local.available()}")
    print(f"backend ที่จะใช้จริง: {active()}")
