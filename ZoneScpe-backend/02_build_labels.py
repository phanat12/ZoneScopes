"""
02_build_labels.py
---------------------------------
ขั้นที่ 2 — สร้าง YOLO-seg label (แยกชนิดยา) จาก template ที่กรอกแล้ว

ใช้ต่อจาก 01_number_disks.py หลังกรอก fill_template.csv เสร็จ

ทำอะไร:
  - อ่านพิกัดแผ่นจาก disks_geometry.csv (numbering ตรงกับ overlay)
  - อ่าน fill_template.csv ที่กรอกชื่อยา + ค่า mm ตามเลขแผ่นแล้ว
  - map ชื่อยา -> class id (สร้าง classes.txt อัตโนมัติ)
  - วาดวง zone ด้วยรัศมี = (mm/2) * px_per_mm รอบแผ่นตามเลข
  - export:  labels/*.txt   (YOLOv8-seg: <class> x1 y1 x2 y2 ...)
             overlays/*.jpg (ตรวจด้วยตา: เขียว=วง, ชื่อยากำกับ)
             classes.txt / data_names.txt
             build_report.csv

กติกาค่า diameter_mm ใน fill_template.csv:
  - ปล่อยว่าง -> ดึงค่าจากชีตให้อัตโนมัติ โดย match ชื่อยา (antibiotic) ของภาพนั้น
                  *** ปกติกรอกแค่ช่อง antibiotic ก็พอ ปล่อย diameter_mm ว่างไว้ ***
  - พิมพ์เลข > 6  -> ใช้ค่านั้นวาดวง (override ชีต)
  - พิมพ์ 0 หรือ <=6 -> ไม่มี zone (ดื้อ) ไม่วาด
  - "non-cir" / "manual" -> ข้าม + flag ให้ทำมือ
  - ถ้าชีตมียาตัวเดียวกันซ้ำ (ค่าต่างกัน) จะไม่เดา -> flag ทำมือ (พิมพ์ค่าเองได้)

คอลัมน์ source ใน build_report.csv: sheet=ดึงจากชีต, template=พิมพ์เอง

วิธีใช้:  python 02_build_labels.py
"""
import csv
import re
from pathlib import Path

import cv2
import numpy as np

# ============ ตั้งค่า ============
IMAGE_DIR = Path(r"C:\Users\Administrator\Downloads\22\ZoneScope-main\Automated Disk diffusion")
OUT_DIR   = Path("./zonescope_out")
GEOM_CSV  = OUT_DIR / "disks_geometry.csv"
FILL_CSV  = OUT_DIR / "fill_template.csv"
SHEET_REF = OUT_DIR / "sheet_reference.csv"   # ไว้ดึง diameter_mm อัตโนมัติ
DISK_MM   = 6.0
POLY_N    = 32            # จำนวนจุดของ polygon วง
RESIZE_LONG = 1500        # ต้องตรงกับสคริปต์ที่ 1

# ชื่อยาที่พิมพ์เพี้ยนในชีต -> ชื่อจริงที่ใช้เป็น class
# (key/value ผ่าน norm_abx แล้ว คือตัวใหญ่ ไม่มีช่องว่าง)
SHEET_ALIAS = {
    "TPZ110": "TZP110",   # P049 สลับตัวอักษร piperacillin-tazobactam
    "P10*":   "P10",      # P013 มีดอกจันต่อท้าย
    "CAZ50":  "CZA50",    # P052 สลับตัวอักษร ceftazidime-avibactam
}

# ยาที่ "ตัดทิ้งทั้ง class" ไม่เอาเข้า dataset (ผ่าน norm_abx แล้ว)
#   CL10 = colistin: polymyxin กระจายในวุ้นไม่ได้ ทดสอบด้วย disk diffusion ไม่ได้
#   (CLSI/EUCAST ต้องใช้ MIC) -> วงในภาพไม่ใช่ clear zone จริง ทำ label เพี้ยน
DROP_ABX = {"CL10"}
# ================================


def parse_mm(raw):
    """คืน (mm, kind) — kind: 'num' | 'none' | 'manual'"""
    s = (raw or "").strip().lower()
    if s in ("", "0", "none", "nz", "no", "-"):
        return 0.0, "none"
    if "non-cir" in s or "noncir" in s or "manual" in s or "มือ" in s:
        return None, "manual"
    m = re.search(r"(\d+(\.\d+)?)", s)
    if m:
        return float(m.group(1)), "num"
    return None, "manual"


def norm_abx(name):
    """normalize ชื่อยาให้เป็น class name เดียวกัน (ตัดช่องว่าง/ทำตัวใหญ่)"""
    return re.sub(r"\s+", "", (name or "").strip()).upper()


def load_geometry(path):
    geo = {}
    dims = {}
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            key = (row["image_file"], int(row["disk_no"]))
            geo[key] = (float(row["cx"]), float(row["cy"]), float(row["r_px"]),
                        float(row["px_per_mm"]) if row["px_per_mm"] else None)
            dims[row["image_file"]] = (int(row["img_w"]), int(row["img_h"]))
    return geo, dims


def load_fill(path):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append((row["image_file"], int(row["disk_no"]),
                         row.get("antibiotic", ""), row.get("diameter_mm", "")))
    return rows


def load_sheet_lookup(path):
    """คืน (lookup, dup) — lookup[image][norm_abx] = diameter_raw จากชีต
    dup[image] = set ของยาที่ชีตมีซ้ำ (ค่าต่างกัน) -> ไม่ auto-fill ให้ทำมือ"""
    lookup, dup = {}, {}
    if not Path(path).exists():
        return lookup, dup
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            img = row["image_file"]
            key = norm_abx(row.get("antibiotic", ""))
            key = SHEET_ALIAS.get(key, key)
            dia = (row.get("diameter_mm", "") or "").strip()
            if not key:
                continue
            m = lookup.setdefault(img, {})
            if key in m and m[key] != dia:
                dup.setdefault(img, set()).add(key)
            m[key] = dia
    return lookup, dup


def circle_polygon(cx, cy, r, w, h, n=POLY_N):
    pts = []
    for k in range(n):
        a = 2 * np.pi * k / n
        x = min(max((cx + r * np.cos(a)) / w, 0.0), 1.0)
        y = min(max((cy + r * np.sin(a)) / h, 0.0), 1.0)
        pts.extend([x, y])
    return pts


def main():
    (OUT_DIR / "labels").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "label_overlays").mkdir(parents=True, exist_ok=True)

    geo, dims = load_geometry(GEOM_CSV)
    fill = load_fill(FILL_CSV)
    sheet_lu, sheet_dup = load_sheet_lookup(SHEET_REF)

    # รวมชื่อยาทั้งหมด -> class id (ตัดยาใน DROP_ABX ออกจาก class list)
    classes = sorted({norm_abx(a) for (_, _, a, _) in fill
                      if norm_abx(a) and norm_abx(a) not in DROP_ABX})
    cls_id = {c: i for i, c in enumerate(classes)}
    (OUT_DIR / "classes.txt").write_text("\n".join(classes), encoding="utf-8")

    # จัดกลุ่มตามภาพ
    per_img = {}
    for img, no, abx, dia in fill:
        per_img.setdefault(img, []).append((no, abx, dia))

    report = [("image_file", "disk_no", "antibiotic", "diameter_mm", "source", "kind", "result")]
    n_zone = n_none = n_manual = n_skip = 0
    n_fromsheet = 0

    for img, entries in sorted(per_img.items()):
        w, h = dims.get(img, (0, 0))
        # โหลดภาพไว้ทำ overlay (ย่อขนาดเท่ากับตอน detect)
        img0 = cv2.imread(str(IMAGE_DIR / img))
        overlay = None
        if img0 is not None:
            scale = RESIZE_LONG / max(img0.shape[:2])
            overlay = cv2.resize(img0, (int(img0.shape[1] * scale), int(img0.shape[0] * scale)))
        else:
            # ไม่มีภาพต้นฉบับ -> ใช้ภาพเลขแผ่นจากขั้นที่ 1 (ย่อขนาดเท่ากันอยู่แล้ว)
            overlay = cv2.imread(str(OUT_DIR / "number_overlays" / img))

        lines = []
        for no, abx, dia in sorted(entries):
            key = (img, no)
            if key not in geo:
                report.append((img, no, abx, dia, "", "", "no_geometry"))
                continue
            cx, cy, dr, ppm = geo[key]
            cname = norm_abx(abx)

            # ยาที่ตัดทิ้งทั้ง class (เช่น colistin) -> ไม่วาด ไม่นับ ไม่ใส่ overlay
            if cname in DROP_ABX:
                n_skip += 1
                report.append((img, no, abx, dia, "", "drop", "dropped_class"))
                continue

            # ถ้า diameter_mm ว่าง -> ดึงจากชีตโดย match ชื่อยาของภาพนั้น
            dia_use, source = (dia or "").strip(), "template"
            if dia_use == "" and cname:
                if cname in sheet_dup.get(img, set()):
                    source = "sheet_dup"          # ชีตมียาซ้ำค่าต่างกัน -> ให้ทำมือ
                else:
                    looked = sheet_lu.get(img, {}).get(cname)
                    if looked not in (None, ""):
                        dia_use, source = looked, "sheet"
                        n_fromsheet += 1
                    elif looked == "":
                        dia_use, source = "0", "sheet"   # ชีตมีแต่ค่าว่าง = ไม่มี zone
                        n_fromsheet += 1

            mm, kind = parse_mm(dia_use)
            if source == "sheet_dup":
                kind = "manual"

            if kind == "manual":
                n_manual += 1
                report.append((img, no, abx, dia, source, "manual", "flag_manual"))
                if overlay is not None:
                    cv2.circle(overlay, (int(cx), int(cy)), int(dr), (0, 0, 255), 2)
                    cv2.putText(overlay, f"{no}:{abx} manual", (int(cx) - 30, int(cy) - int(dr) - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1, cv2.LINE_AA)
                continue

            if kind == "none" or mm <= DISK_MM:
                n_none += 1
                report.append((img, no, abx, dia, source, "none", "no_zone_skip"))
                if overlay is not None:
                    cv2.circle(overlay, (int(cx), int(cy)), int(dr), (0, 165, 255), 2)
                continue

            if not cname:
                n_skip += 1
                report.append((img, no, abx, dia, source, "num", "no_antibiotic_skip"))
                continue
            if ppm is None or w == 0:
                n_skip += 1
                report.append((img, no, abx, dia, source, "num", "no_ppm_skip"))
                continue

            r_px = (mm / 2.0) * ppm
            poly = circle_polygon(cx, cy, r_px, w, h)
            lines.append(f"{cls_id[cname]} " + " ".join(f"{v:.6f}" for v in poly))
            n_zone += 1
            report.append((img, no, abx, dia, source, "num", f"zone_cls{cls_id[cname]}"))
            if overlay is not None:
                cv2.circle(overlay, (int(cx), int(cy)), int(r_px), (0, 220, 0), 2)
                cv2.circle(overlay, (int(cx), int(cy)), int(dr), (255, 255, 0), 1)
                cv2.putText(overlay, f"{no}:{cname} {mm:.0f}", (int(cx) - 30, int(cy) - int(r_px) - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 0), 1, cv2.LINE_AA)

        stem = Path(img).stem
        (OUT_DIR / "labels" / f"{stem}.txt").write_text("\n".join(lines), encoding="utf-8")
        if overlay is not None:
            cv2.imwrite(str(OUT_DIR / "label_overlays" / img), overlay)

    with open(OUT_DIR / "build_report.csv", "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(report)

    print(f"classes: {len(classes)} ชนิด -> classes.txt")
    print(f"zone ที่วาด: {n_zone} | ไม่มี zone(ดื้อ): {n_none} | ทำมือ: {n_manual} | ข้าม: {n_skip}")
    print(f"ค่า diameter ที่ดึงจากชีตอัตโนมัติ: {n_fromsheet} (ที่เหลือกรอกเองในช่อง diameter_mm)")
    print("ตรวจ ./zonescope_out/label_overlays/ ก่อนอัปเข้า Roboflow")
    print("label อยู่ ./zonescope_out/labels/ (คู่กับภาพต้นฉบับได้เลย เพราะ normalized)")


if __name__ == "__main__":
    main()
