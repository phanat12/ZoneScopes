"""
make_circle_labels.py
---------------------------------
สร้าง label วงกลม (zone of inhibition) อัตโนมัติ สำหรับเทรน YOLO-seg
โดยไม่ต้องลากมือทีละวง

หลักการ:
  - หาแผ่นยา (disk) ในภาพด้วย Hough
  - ใช้แผ่นยา 6mm เป็นไม้บรรทัด -> px ต่อ mm
  - อ่านค่า diameter ที่ผู้เชี่ยวชาญวัดจากชีต (CSV)
  - จับคู่ว่าแผ่นไหน = ค่าไหน (Hungarian matching จากการวัดหยาบ ๆ)
  - วาดวงกลม 32 จุด รอบใจกลางแผ่น ด้วยรัศมีจากชีต
  - export เป็น YOLOv8-seg label + ภาพ overlay ไว้ตรวจ

*** ต้องรันในเครื่องที่มีโฟลเดอร์ภาพ 61 ใบ ***
*** Hough params (ค่าตัวแปรด้านล่าง) อาจต้องจูนตามความละเอียดภาพจริง ***

ติดตั้ง:  pip install opencv-python numpy pandas scipy
รัน:      python make_circle_labels.py
ผลลัพธ์:  ./out/labels/*.txt      (YOLO-seg สำหรับอัปเข้า Roboflow/เทรน)
          ./out/overlays/*.jpg    (ภาพวงที่วาด ไว้ตรวจด้วยตา)
          ./out/report.csv        (สรุปว่าจานไหนผ่าน จานไหนต้องทำมือ)
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

# ============ ตั้งค่าตรงนี้ ============
IMAGE_DIR = Path("./images")        # โฟลเดอร์ภาพ 61 ใบ
CSV_PATH  = Path("./data.csv")      # ไฟล์ชีต export
OUT_DIR   = Path("./out")
DISK_MM   = 6.0                     # ขนาดแผ่นยามาตรฐาน (มม.)
CLASS_ID  = 0                       # index ของ class "zone" ใน YOLO

# Hough — จูนตามภาพจริง (ค่าเริ่มต้นสำหรับภาพ ~1500-3000px)
RESIZE_LONG   = 1500               # ย่อภาพด้านยาวเป็นเท่านี้ก่อนประมวลผล
DISK_R_MIN    = 14                 # รัศมีแผ่นยาต่ำสุด (px หลังย่อ)
DISK_R_MAX    = 34                 # รัศมีแผ่นยาสูงสุด (px หลังย่อ)
DISK_MINDIST  = 45                 # ระยะห่างขั้นต่ำระหว่างแผ่น (px)
HOUGH_PARAM2  = 28                 # ยิ่งต่ำ = เจอง่ายแต่ noise เยอะ
# =====================================


def parse_diameter(raw: str):
    """คืน (value_mm, kind) — kind: 'num' | 'none' | 'noncir'"""
    s = (raw or "").strip().lower()
    if s in ("", "0"):
        return 0.0, "none"          # ไม่มีวง (ดื้อ)
    if "non-cir" in s or "noncir" in s:
        return None, "noncir"       # วงไม่กลม -> ทำมือ
    m = re.search(r"(\d+(\.\d+)?)", s)
    if m:
        return float(m.group(1)), "num"
    return None, "noncir"


def load_sheet(csv_path):
    """คืน dict: image_file -> list ของ (antibiotic, value_mm, kind)"""
    per = defaultdict(list)
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)                       # ข้าม header
        for ln in reader:
            if len(ln) < 9:
                continue
            img = ln[0].strip()
            if not img.lower().endswith(".jpg"):
                continue
            abx = ln[7].strip()
            val, kind = parse_diameter(ln[8])
            if abx == "" and kind == "none":
                continue
            per[img].append((abx, val, kind))
    return per


def detect_disks(gray):
    """คืน (list ของ (cx,cy,r_px), px_per_mm)"""
    g = cv2.medianBlur(gray, 5)
    circles = cv2.HoughCircles(
        g, cv2.HOUGH_GRADIENT, dp=1.0, minDist=DISK_MINDIST,
        param1=120, param2=HOUGH_PARAM2,
        minRadius=DISK_R_MIN, maxRadius=DISK_R_MAX,
    )
    if circles is None:
        return [], None
    disks = [(float(x), float(y), float(r)) for x, y, r in circles[0]]
    px_per_mm = (np.median([d[2] for d in disks]) * 2) / DISK_MM
    return disks, px_per_mm


def rough_zone_diameter_mm(gray, cx, cy, disk_r, px_per_mm, max_mm=40):
    """วัดวงแบบหยาบ ๆ (ไว้ใช้จับคู่เท่านั้น ไม่ใช่ค่าจริง)"""
    start = int(disk_r)
    end = int(max_mm * px_per_mm)
    ang = np.linspace(0, 2 * np.pi, 120, endpoint=False)
    ca, sa = np.cos(ang), np.sin(ang)
    H, W = gray.shape
    prof = []
    for r in range(start, end):
        xs = np.clip((cx + r * ca).astype(int), 0, W - 1)
        ys = np.clip((cy + r * sa).astype(int), 0, H - 1)
        prof.append(gray[ys, xs].mean())
    if len(prof) < 5:
        return DISK_MM
    prof = cv2.GaussianBlur(np.array(prof, np.float32).reshape(-1, 1), (1, 9), 0).ravel()
    grad = np.abs(np.gradient(prof))
    edge = int(np.argmax(grad))
    radius_px = start + edge
    return (radius_px / px_per_mm) * 2


def match_disks_to_values(rough_mm, sheet_vals):
    """
    จับคู่ disk (rough_mm) กับค่าในชีต (sheet_vals) ให้ผลต่างรวมน้อยสุด
    คืน list เท่ากับจำนวน disk: index ของ sheet ที่ match (หรือ None)
    """
    n_disk = len(rough_mm)
    n_val = len(sheet_vals)
    n = max(n_disk, n_val)
    BIG = 1e6
    cost = np.full((n, n), BIG)
    for i in range(n_disk):
        for j in range(n_val):
            v = sheet_vals[j]
            cost[i, j] = abs(rough_mm[i] - v) if v is not None else 50.0
    row, col = linear_sum_assignment(cost)
    out = [None] * n_disk
    for i, j in zip(row, col):
        if i < n_disk and j < n_val:
            out[i] = j
    return out


def circle_polygon(cx, cy, r, w, h, n=32):
    """คืน list พิกัด normalized [x1,y1,...] สำหรับ YOLO-seg"""
    pts = []
    for k in range(n):
        a = 2 * np.pi * k / n
        x = (cx + r * np.cos(a)) / w
        y = (cy + r * np.sin(a)) / h
        pts.extend([min(max(x, 0), 1), min(max(y, 0), 1)])
    return pts


def process(img_path, sheet_entries):
    img0 = cv2.imread(str(img_path))
    if img0 is None:
        return None, "read_fail"
    H0, W0 = img0.shape[:2]
    scale = RESIZE_LONG / max(H0, W0)
    img = cv2.resize(img0, (int(W0 * scale), int(H0 * scale)))
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    disks, ppm = detect_disks(gray)
    status = "ok"
    n_rows = len(sheet_entries)
    if not disks or ppm is None:
        return None, "no_disks"
    if len(disks) != n_rows:
        status = f"count_mismatch(disk={len(disks)},sheet={n_rows})"

    rough = [rough_zone_diameter_mm(gray, cx, cy, r, ppm) for cx, cy, r in disks]
    sheet_vals = [v if k != "none" else DISK_MM for (_, v, k) in sheet_entries]
    assign = match_disks_to_values(rough, sheet_vals)

    lines, overlay = [], img.copy()
    for i, (cx, cy, dr) in enumerate(disks):
        j = assign[i]
        if j is None:
            continue
        abx, val, kind = sheet_entries[j]
        if kind == "noncir":
            cv2.circle(overlay, (int(cx), int(cy)), int(dr), (0, 0, 255), 2)
            cv2.putText(overlay, f"{abx} non-cir", (int(cx) - 30, int(cy) - int(dr) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            continue
        radius_mm = max(val if val else DISK_MM, DISK_MM) / 2
        r_px = radius_mm * ppm
        poly = circle_polygon(cx, cy, r_px, w, h)
        lines.append(f"{CLASS_ID} " + " ".join(f"{p:.6f}" for p in poly))
        color = (0, 200, 0) if kind == "num" else (0, 180, 255)
        cv2.circle(overlay, (int(cx), int(cy)), int(r_px), color, 2)
        cv2.circle(overlay, (int(cx), int(cy)), int(dr), (255, 255, 0), 1)
        cv2.putText(overlay, f"{abx} {val:.0f}mm", (int(cx) - 30, int(cy) - int(r_px) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    return {"lines": lines, "overlay": overlay, "n_disks": len(disks),
            "n_rows": n_rows, "ppm": ppm}, status


def main():
    (OUT_DIR / "labels").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "overlays").mkdir(parents=True, exist_ok=True)
    sheet = load_sheet(CSV_PATH)

    report = [("image", "status", "n_disks", "n_sheet", "px_per_mm")]
    ok = mism = fail = 0
    for img_name, entries in sorted(sheet.items()):
        p = IMAGE_DIR / img_name
        if not p.exists():
            report.append((img_name, "image_missing", "", len(entries), ""))
            fail += 1
            continue
        res, status = process(p, entries)
        if res is None:
            report.append((img_name, status, "", len(entries), ""))
            fail += 1
            continue
        (OUT_DIR / "labels" / (p.stem + ".txt")).write_text("\n".join(res["lines"]))
        cv2.imwrite(str(OUT_DIR / "overlays" / (p.stem + ".jpg")), res["overlay"])
        report.append((img_name, status, res["n_disks"], res["n_rows"], f'{res["ppm"]:.2f}'))
        if status == "ok":
            ok += 1
        else:
            mism += 1

    with open(OUT_DIR / "report.csv", "w", newline="") as f:
        csv.writer(f).writerows(report)

    print(f"เสร็จ: ผ่าน {ok} | จำนวนไม่ตรง/ต้องดู {mism} | พลาด {fail}")
    print(f"เปิดดู ./out/overlays/ เพื่อตรวจวงที่วาด ก่อนอัปเข้า Roboflow")
    print(f"จานที่ status != ok ใน report.csv = ต้องตรวจ/ทำมือเป็นพิเศษ")


if __name__ == "__main__":
    main()
