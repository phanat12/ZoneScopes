"""
01_number_disks.py
---------------------------------
ขั้นที่ 1 ของ pipeline สร้าง label วง zone (แบบระบุชื่อยา)

ทำอะไร:
  - หาแผ่นยา (disk 6mm) ในภาพทุกใบด้วย Hough  (param พิสูจน์แล้วกับภาพจริง 4096x2304)
  - ใส่ "เลขแผ่น" 1..N เรียงตามเข็มนาฬิกาจากด้านบน (คงที่ ทำซ้ำได้)
  - เซฟภาพ overlay ที่มีเลขกำกับแต่ละแผ่น -> ไว้เปิดดูตอนกรอก
  - เซฟพิกัดแผ่น (disks_geometry.csv) -> ให้สคริปต์ที่ 2 ใช้ต่อ (numbering ตรงกันเป๊ะ)
  - เซฟ fill_template.csv -> ตารางให้ "นุข" กรอกชื่อยา + ค่า mm ตามเลขแผ่น
  - เซฟ sheet_reference.csv -> ค่าจากชีตเดิม (ไว้ก๊อปตอนกรอก)

วิธีใช้:
  python 01_number_disks.py
  -> เปิด ./zonescope_out/number_overlays/*.jpg  ดูเลขแผ่น
  -> กรอก ./zonescope_out/fill_template.csv  (คอลัมน์ antibiotic, diameter_mm)
     โดยดูเลขแผ่นจาก overlay + ชื่อยาที่พิมพ์บนแผ่น + ค่าจากชีต
  -> แล้วรัน 02_build_labels.py
"""
import csv
from pathlib import Path

import cv2
import numpy as np

# ============ ตั้งค่า ============
IMAGE_DIR = Path(r"C:\Users\Administrator\Downloads\Automated Disk diffusion\Automated Disk diffusion")
CSV_PATH  = Path(r"C:\Users\Administrator\Downloads\Automated disk diffusion zone reader system - ชีต1.csv")
OUT_DIR   = Path("./zonescope_out")
DISK_MM   = 6.0

# Hough — พิสูจน์กับภาพจริงแล้ว ไม่ต้องแก้ (ภาพ 4096x2304 ย่อ long->1500)
RESIZE_LONG  = 1500
DISK_R_MIN   = 14
DISK_R_MAX   = 34
DISK_MINDIST = 45
HOUGH_P1     = 120
HOUGH_P2     = 28
# กรอง false positive ด้วยความสว่างในแผ่น (แผ่นจริงเป็นกระดาษขาว)
DISK_MIN_INNER = 100    # ความสว่างเฉลี่ยกลางแผ่นขั้นต่ำ (0-255)
DISK_MIN_RATIO = 3.0    # และต้องสว่าง >= เท่านี้เท่าของพื้นหลังจาน
# ================================


def _inner_mean(gray, cx, cy, r, frac=0.55):
    """ความสว่างเฉลี่ยกลางแผ่น (ใช้แยกแผ่นกระดาษขาวจาก false positive บนวุ้น)"""
    rr = max(int(r * frac), 1)
    H, W = gray.shape
    x0, x1 = max(0, int(cx - rr)), min(W, int(cx + rr))
    y0, y1 = max(0, int(cy - rr)), min(H, int(cy + rr))
    patch = gray[y0:y1, x0:x1]
    if patch.size == 0:
        return 0.0
    yy, xx = np.ogrid[y0:y1, x0:x1]
    mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= rr * rr
    return float(patch[mask].mean()) if mask.any() else float(patch.mean())


def detect_disks(gray):
    g = cv2.medianBlur(gray, 5)
    c = cv2.HoughCircles(
        g, cv2.HOUGH_GRADIENT, dp=1.0, minDist=DISK_MINDIST,
        param1=HOUGH_P1, param2=HOUGH_P2,
        minRadius=DISK_R_MIN, maxRadius=DISK_R_MAX,
    )
    if c is None:
        return [], None
    # กรอง false positive: แผ่นจริง = กระดาษขาวสว่างมาก (inner ~140-180)
    # false บนวุ้น/ขอบจาน = มืด (inner ~55) -> ตัดออกด้วยความสว่างสัมบูรณ์ + เทียบพื้นหลัง
    bg = float(np.median(gray))
    disks = []
    for x, y, r in c[0]:
        m = _inner_mean(gray, x, y, r)
        if m >= DISK_MIN_INNER and m >= DISK_MIN_RATIO * bg:
            disks.append((float(x), float(y), float(r)))
    if not disks:
        return [], None
    px_per_mm = (float(np.median([d[2] for d in disks])) * 2) / DISK_MM
    return disks, px_per_mm


def order_clockwise(disks):
    """เรียงแผ่นตามเข็มนาฬิกาเริ่มจากบนสุด (12 นาฬิกา) คืน list ที่เรียงแล้ว"""
    if not disks:
        return []
    cx0 = float(np.median([d[0] for d in disks]))
    cy0 = float(np.median([d[1] for d in disks]))
    # angle 0 = ด้านบน, เพิ่มตามเข็มนาฬิกา
    def ang(d):
        return np.arctan2(d[0] - cx0, -(d[1] - cy0)) % (2 * np.pi)
    return sorted(disks, key=ang)


def load_sheet(csv_path):
    """คืน dict image_file -> list ของ (antibiotic, diameter_raw, interpretation)"""
    from collections import defaultdict
    per = defaultdict(list)
    with open(csv_path, encoding="utf-8") as f:
        r = csv.reader(f)
        next(r, None)
        for ln in r:
            if len(ln) < 9:
                continue
            img = ln[0].strip()
            if not img.lower().endswith(".jpg"):
                continue
            abx = ln[7].strip()
            dia = ln[8].strip()
            interp = ln[9].strip() if len(ln) > 9 else ""
            if abx == "" and dia == "":
                continue
            per[img].append((abx, dia, interp))
    return per


def draw_number(img, cx, cy, r, cx0, cy0, num):
    """เขียนเลขแผ่นไว้ด้านนอกแผ่น (ฝั่งตรงข้ามจุดกลางจาน) จะได้ไม่บังชื่อยาบนแผ่น"""
    # ทิศจากกลางจาน -> แผ่น
    dx, dy = cx - cx0, cy - cy0
    d = (dx * dx + dy * dy) ** 0.5 or 1.0
    ox = int(cx + dx / d * (r + 20))
    oy = int(cy + dy / d * (r + 20))
    cv2.circle(img, (int(cx), int(cy)), int(r), (0, 255, 0), 2)
    txt = str(num)
    font, fs, th = cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2
    (tw, tht), _ = cv2.getTextSize(txt, font, fs, th)
    org = (ox - tw // 2, oy + tht // 2)
    cv2.putText(img, txt, org, font, fs, (0, 0, 0), th + 3, cv2.LINE_AA)
    cv2.putText(img, txt, org, font, fs, (0, 255, 255), th, cv2.LINE_AA)


def main():
    (OUT_DIR / "number_overlays").mkdir(parents=True, exist_ok=True)
    sheet = load_sheet(CSV_PATH)

    geom_rows = [("image_file", "disk_no", "cx", "cy", "r_px", "px_per_mm",
                  "img_w", "img_h")]
    fill_rows = [("image_file", "disk_no", "antibiotic", "diameter_mm")]
    ref_rows  = [("image_file", "antibiotic", "diameter_mm", "interpretation")]
    report    = [("image_file", "n_disks", "n_sheet", "note")]

    imgs = sorted(p for p in IMAGE_DIR.glob("*.jpg"))
    for p in imgs:
        name = p.name
        img0 = cv2.imread(str(p))
        if img0 is None:
            report.append((name, "", "", "READ_FAIL"))
            continue
        H0, W0 = img0.shape[:2]
        scale = RESIZE_LONG / max(H0, W0)
        img = cv2.resize(img0, (int(W0 * scale), int(H0 * scale)))
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        disks, ppm = detect_disks(gray)
        disks = order_clockwise(disks)
        n_sheet = len(sheet.get(name, []))
        note = "ok" if len(disks) == n_sheet else f"count_diff(disk={len(disks)},sheet={n_sheet})"
        report.append((name, len(disks), n_sheet, note))

        cx0 = float(np.median([d[0] for d in disks])) if disks else w / 2
        cy0 = float(np.median([d[1] for d in disks])) if disks else h / 2
        overlay = img.copy()
        for i, (cx, cy, r) in enumerate(disks, start=1):
            draw_number(overlay, cx, cy, r, cx0, cy0, i)
            geom_rows.append((name, i, f"{cx:.2f}", f"{cy:.2f}", f"{r:.2f}",
                              f"{ppm:.3f}" if ppm else "", w, h))
            fill_rows.append((name, i, "", ""))
        cv2.imwrite(str(OUT_DIR / "number_overlays" / name), overlay)

        # reference จากชีตเดิม
        for abx, dia, interp in sheet.get(name, []):
            ref_rows.append((name, abx, dia, interp))

    def write(path, rows):
        with open(OUT_DIR / path, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(rows)

    write("disks_geometry.csv", geom_rows)
    write("fill_template.csv", fill_rows)
    write("sheet_reference.csv", ref_rows)
    write("number_report.csv", report)

    n_ok = sum(1 for r in report[1:] if r[3] == "ok")
    print(f"เสร็จ {len(imgs)} ใบ | นับตรงชีต {n_ok} | ดูที่ ./zonescope_out/")
    print("ถัดไป: เปิด number_overlays/ ดูเลขแผ่น -> กรอก fill_template.csv -> รัน 02_build_labels.py")


if __name__ == "__main__":
    main()
