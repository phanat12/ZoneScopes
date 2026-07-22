"""
03_build_single_class.py
---------------------------------
สร้าง dataset แบบ "class เดียว" (zone) จาก label 28-class เดิม

แนวคิด (ZoneScope M5 / OCR-assist):
  - ให้ YOLO ตรวจแค่ "มี inhibition zone ตรงไหน + ขนาดเท่าไหร่" เป็น class เดียว
  - ชื่อยา (AN30, IPM10, ...) พิมพ์อยู่บนแผ่นแล้ว ไปอ่านด้วย OCR แยกทีหลัง
  - ผล: 266 วงจาก 28 class -> class เดียว 266 ตัวอย่าง = ข้อมูลต่อ class เยอะขึ้นมาก

ทำอะไร:
  - อ่าน label เดิมจาก zonescope_out/labels/*.txt (YOLOv8-seg polygon)
  - เขียนใหม่โดยเปลี่ยน class id ทุกบรรทัดเป็น 0
  - ก๊อปภาพต้นฉบับ + สร้าง data.yaml (nc:1, names:['zone'])
  - output: zonescope_dataset_single/  (train/images, train/labels, data.yaml)

ไม่แตะไฟล์ multi-class เดิมเลย (zonescope_out/ คงไว้)

วิธีใช้:  python 03_build_single_class.py
"""
import shutil
from pathlib import Path

# ============ ตั้งค่า ============
BACKEND   = Path(__file__).resolve().parent
SRC_LABEL = BACKEND / "zonescope_out" / "labels"
IMAGE_DIR = Path(r"C:\Users\Administrator\Downloads\22\ZoneScope-main\Automated Disk diffusion")
OUT_DIR   = BACKEND / "zonescope_dataset_single"
CLASS_NAME = "zone"
# ================================


def main():
    img_out = OUT_DIR / "train" / "images"
    lab_out = OUT_DIR / "train" / "labels"
    img_out.mkdir(parents=True, exist_ok=True)
    lab_out.mkdir(parents=True, exist_ok=True)

    n_files = n_zones = n_empty = n_img = 0

    for txt in sorted(SRC_LABEL.glob("*.txt")):
        lines_out = []
        for line in txt.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(" ")
            parts[0] = "0"                      # บังคับ class เดียว
            lines_out.append(" ".join(parts))
            n_zones += 1
        (lab_out / txt.name).write_text("\n".join(lines_out), encoding="utf-8")
        n_files += 1
        if not lines_out:
            n_empty += 1

        # ก๊อปภาพคู่กัน (ชื่อ stem เดียวกัน .jpg)
        img = IMAGE_DIR / f"{txt.stem}.jpg"
        if img.exists():
            shutil.copy2(img, img_out / img.name)
            n_img += 1

    # data.yaml (1 class)
    (OUT_DIR / "data.yaml").write_text(
        "# ZoneScope — single-class 'zone' dataset (YOLOv8-seg)\n"
        "# ตรวจ inhibition zone เป็น class เดียว | ชื่อยาอ่านด้วย OCR แยก (M5)\n"
        "path: .\n"
        "train: train/images\n"
        "val: train/images\n"
        "nc: 1\n"
        f"names:\n  0: {CLASS_NAME}\n",
        encoding="utf-8",
    )

    print(f"label files : {n_files}  (ว่าง/background {n_empty})")
    print(f"images copied: {n_img}")
    print(f"zones (class 'zone'): {n_zones}")
    print(f"output -> {OUT_DIR}")


if __name__ == "__main__":
    main()
