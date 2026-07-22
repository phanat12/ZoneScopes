"""05_split_dataset.py — แยก train/val สำหรับเทรนโมเดลเอง (ultralytics)

dataset เดิม (zonescope_dataset_single) ตั้ง val = train เดียวกัน → วัดผลไม่ได้จริง
สคริปต์นี้แบ่งเป็น train 80% / val 20% แบบ deterministic (ทุกภาพที่ index หาร 5 ลงตัว -> val)
เพื่อให้ผลเทรนซ้ำได้เหมือนเดิมทุกครั้ง

ผลลัพธ์: zonescope_yolo/{train,val}/{images,labels} + data.yaml  (พร้อมอัปขึ้น Colab)

ใช้:  python 05_split_dataset.py
"""

import shutil
from pathlib import Path

import cv2

BACKEND = Path(__file__).resolve().parent
SRC = BACKEND / "zonescope_dataset_single" / "train"
OUT = BACKEND / "zonescope_yolo"

VAL_EVERY = 5  # 1 ใน 5 ภาพเป็น val (~20%)

# ย่อภาพให้ด้านยาว = ค่านี้ ก่อนเขียนลง output
# label เป็นพิกัด normalized อยู่แล้ว -> ย่อภาพไม่ต้องแก้ label
# (ต้นฉบับ 2304x4096 ทำให้ zip ใหญ่ ~144MB อัป Colab ช้า)
RESIZE_LONG = 1280


def main() -> None:
    images = sorted((SRC / "images").glob("*.jpg"))
    if not images:
        raise SystemExit(f"ไม่พบภาพใน {SRC / 'images'}")

    if OUT.exists():
        shutil.rmtree(OUT)
    for split in ("train", "val"):
        (OUT / split / "images").mkdir(parents=True)
        (OUT / split / "labels").mkdir(parents=True)

    counts = {"train": 0, "val": 0}
    zones = {"train": 0, "val": 0}
    skipped = []

    for i, img in enumerate(images):
        label = SRC / "labels" / f"{img.stem}.txt"
        if not label.exists():
            skipped.append(img.name)
            continue
        split = "val" if i % VAL_EVERY == 0 else "train"

        im = cv2.imread(str(img))
        if im is None:
            skipped.append(img.name)
            continue
        h, w = im.shape[:2]
        scale = RESIZE_LONG / max(h, w)
        if scale < 1.0:
            im = cv2.resize(im, (round(w * scale), round(h * scale)),
                            interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(OUT / split / "images" / img.name), im,
                    [cv2.IMWRITE_JPEG_QUALITY, 92])

        shutil.copy2(label, OUT / split / "labels" / label.name)
        counts[split] += 1
        zones[split] += sum(1 for ln in label.read_text().splitlines() if ln.strip())

    (OUT / "data.yaml").write_text(
        "# ZoneScope — single-class 'zone' (YOLOv8-seg) แยก train/val แล้ว\n"
        "path: .\n"
        "train: train/images\n"
        "val: val/images\n"
        "nc: 1\n"
        "names:\n"
        "  0: zone\n",
        encoding="utf-8",
    )

    print(f"train : {counts['train']:3d} ภาพ / {zones['train']:4d} zones")
    print(f"val   : {counts['val']:3d} ภาพ / {zones['val']:4d} zones")
    if skipped:
        print(f"ข้าม (ไม่มี label): {skipped}")
    print(f"\nเสร็จ -> {OUT}")


if __name__ == "__main__":
    main()
