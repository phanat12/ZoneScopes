"""
test_zone_infer.py — smoke test ของ zone_infer.run_zone_workflow

ยิงภาพจานตัวอย่าง 1 ใบเข้า Roboflow workflow จริง แล้วเช็กว่า:
  - ได้ผลเป็น list (1 entry ต่อ 1 ภาพ)
  - entry แรกเป็น dict (มี output key ของ workflow)
  - ดึง zone ออกมาได้ (มี field ที่ต้องใช้)

ต้องมี ROBOFLOW_API_KEY (env หรือไฟล์ .env) ก่อนรัน
รัน:  python test_zone_infer.py
"""
from pathlib import Path

import zone_infer

SAMPLE = Path(r"C:\Users\Administrator\Downloads\22\ZoneScope-main\Automated Disk diffusion\P001.jpg")


def test_run_zone_workflow_smoke():
    assert SAMPLE.exists(), f"ไม่พบภาพตัวอย่าง: {SAMPLE}"

    outputs = zone_infer.run_zone_workflow(str(SAMPLE))

    # 1) ผลเป็น list (1 entry ต่อภาพ)
    assert isinstance(outputs, list) and len(outputs) >= 1, f"คาดว่าเป็น list ไม่ว่าง ได้: {type(outputs)}"

    entry = outputs[0]
    # 2) entry เป็น dict มี output key อย่างน้อย 1 ตัว
    assert isinstance(entry, dict) and len(entry) >= 1, f"entry ควรเป็น dict ที่มี output ได้: {entry!r}"
    print("output keys:", list(entry.keys()))

    # 3) ดึง zone ได้ (โครงถูก แม้บางภาพอาจ 0 วง)
    zones = zone_infer.extract_zones(entry)
    print(f"zones detected: {len(zones)}")
    if zones:
        z = zones[0]
        assert "confidence" in z and ("width" in z or "x" in z), f"zone ขาด field ที่ใช้: {z}"

    print("SMOKE TEST PASSED ✅")
    return outputs


if __name__ == "__main__":
    test_run_zone_workflow_smoke()
