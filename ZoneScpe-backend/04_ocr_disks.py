"""
04_ocr_disks.py
---------------------------------
OCR อ่าน "ชื่อยา" ที่พิมพ์บนแผ่นยาแต่ละแผ่น (ZoneScope M5 / OCR-assist)

แนวคิด: โมเดล YOLO ตรวจ zone เป็น class เดียวแล้ว (แม่น 99%) ส่วน "ชื่อยา"
ไม่ต้องให้โมเดลเดา -> อ่านจากตัวอักษรบนแผ่นด้วย OCR แล้ว match กับรหัสยาที่รู้จัก

ทำอะไร:
  - โหลดพิกัดแผ่นจาก disks_geometry.csv (พิกัดในภาพย่อ long=1500)
  - สเกลกลับไปภาพต้นฉบับ (ความละเอียดสูง) แล้ว crop แผ่น + ขยาย
  - OCR ด้วย easyocr (ลองหมุน 90/180/270 เพราะตัวอักษรบนแผ่นหันได้ทุกทิศ)
  - fuzzy-match ข้อความที่อ่านได้กับ "รหัสยาที่รู้จัก" (closed set) -> เดารหัสที่ใกล้สุด
  - เทียบกับ ground truth (ชื่อยาจริงจาก build_report.csv) -> วัดความแม่น

ผลลัพธ์:
  ocr_results.csv : image, disk_no, truth, ocr_raw, predicted, score, correct
  ocr_crops/      : ภาพแผ่นที่ crop ไว้ (ไว้ตรวจตา)

วิธีใช้:
  python 04_ocr_disks.py          # ทำครบทุกใบ
  python 04_ocr_disks.py 5        # ทำแค่ 5 ใบแรก (ไว้เทสต์เร็ว)
"""
import csv
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import cv2
import easyocr

# ============ ตั้งค่า ============
BACKEND   = Path(__file__).resolve().parent
IMAGE_DIR = Path(r"C:\Users\Administrator\Downloads\22\ZoneScope-main\Automated Disk diffusion")
OUT_DIR   = BACKEND / "zonescope_out"
GEOM_CSV  = OUT_DIR / "disks_geometry.csv"
TRUTH_CSV = OUT_DIR / "build_report.csv"   # มีคอลัมน์ antibiotic = ground truth
CROP_DIR  = OUT_DIR / "ocr_crops"
RESIZE_LONG = 1500          # ต้องตรงกับ geometry
PAD_RATIO = 1.05            # crop = รัศมีแผ่น x เท่านี้ (แน่น ตัด agar รอบแผ่นออก)
UPSCALE_TO = 384            # ขยาย crop ให้สูงเท่านี้ก่อน OCR
ALLOW = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/"
# ================================


def norm(s):
    """normalize รหัสยา/ข้อความ OCR: ตัวใหญ่ เอาเฉพาะ A-Z0-9 (ทิ้งช่องว่าง/ /)"""
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def load_geometry(path):
    geo = defaultdict(list)   # image -> list of (disk_no, cx, cy, r_px)
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            geo[row["image_file"]].append(
                (int(row["disk_no"]), float(row["cx"]), float(row["cy"]), float(row["r_px"]))
            )
    return geo


def load_truth(path):
    truth = {}                # (image, disk_no) -> antibiotic
    candidates = set()
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            abx = (row.get("antibiotic") or "").strip()
            key = (row["image_file"], int(row["disk_no"]))
            truth[key] = abx
            if abx and norm(abx):
                candidates.add(abx)
    return truth, sorted(candidates)


def _alpha(s):
    return re.sub(r"[0-9]", "", s)


def best_match(ocr_text, candidates):
    """คืน (predicted_code, score 0-1) — เน้นตัวอักษร (discriminative) มากกว่าตัวเลข
    เพราะ OCR อ่านเลขบนแผ่นเพี้ยนบ่อย (30->8) แต่ตัวอักษรแยกยาได้เกือบหมด"""
    o = norm(ocr_text)
    if not o:
        return "", 0.0
    oa = _alpha(o)
    best, best_s = "", 0.0
    for c in candidates:
        cn = norm(c)
        ca = _alpha(cn)
        s_full = SequenceMatcher(None, o, cn).ratio()
        s_alpha = SequenceMatcher(None, oa, ca).ratio() if ca else s_full
        s = 0.65 * s_alpha + 0.35 * s_full
        if ca and ca in oa:            # ตัวอักษรรหัสโผล่ครบในสิ่งที่อ่านได้
            s += 0.10
        if s > best_s:
            best, best_s = c, s
    return best, round(min(best_s, 1.0), 3)


def _rotate(im, deg):
    """หมุนภาพมุมใดก็ได้ ขยายกรอบไม่ให้มุมโดนตัด พื้นหลังขาว (แผ่นเป็นกระดาษขาว)"""
    if deg == 0:
        return im
    h, w = im.shape[:2]
    cX, cY = w / 2, h / 2
    M = cv2.getRotationMatrix2D((cX, cY), deg, 1.0)
    cos, sin = abs(M[0, 0]), abs(M[0, 1])
    nW, nH = int(h * sin + w * cos), int(h * cos + w * sin)
    M[0, 2] += nW / 2 - cX
    M[1, 2] += nH / 2 - cY
    return cv2.warpAffine(im, M, (nW, nH), borderValue=(255, 255, 255))


def _ocr_angles(reader, crop, candidates, angles):
    best = ("", "", 0.0)
    for deg in angles:
        res = reader.readtext(_rotate(crop, deg), allowlist=ALLOW, detail=1)
        parts = sorted(res, key=lambda r: r[0][0][1])   # บน->ล่าง
        raw = " ".join(t for _, t, conf in parts if conf > 0.10)
        pred, score = best_match(raw, candidates)
        if score > best[2]:
            best = (raw, pred, score)
    return best


def ocr_best(reader, crop, candidates):
    """2 ชั้น: มุมหยาบ 0/90/180/270 ก่อน (เร็ว) ถ้าคะแนนต่ำ (<0.70)
    ค่อยลองมุมละเอียด 45/135/225/315 (เผื่อตัวอักษรเอียง) -> คืน (raw, pred, score)"""
    best = _ocr_angles(reader, crop, candidates, [0, 90, 180, 270])
    if best[2] < 0.70:
        fine = _ocr_angles(reader, crop, candidates, [45, 135, 225, 315])
        if fine[2] > best[2]:
            best = fine
    return best


def main():
    # args:  (ไม่ใส่)=ทำครบ | "N"=N ใบแรก | "START END"=ช่วง [START:END] (append ต่อไฟล์)
    args = sys.argv[1:]
    start, end = 0, None
    if len(args) == 1:
        end = int(args[0])
    elif len(args) >= 2:
        start, end = int(args[0]), int(args[1])
    CROP_DIR.mkdir(parents=True, exist_ok=True)

    geo = load_geometry(GEOM_CSV)
    truth, candidates = load_truth(TRUTH_CSV)
    print(f"รหัสยาที่รู้จัก (candidates): {len(candidates)} ตัว")
    print("กำลังโหลดโมเดล easyocr (ครั้งแรกดาวน์โหลด ~64MB)...")
    reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    header = ("image_file", "disk_no", "truth", "ocr_raw", "predicted", "score", "correct")
    n_total = n_known = n_correct = 0

    images = sorted(geo.keys())[start:end]
    print(f"ทำช่วง [{start}:{end}] = {len(images)} ใบ", flush=True)

    # เปิดไฟล์ผลไว้ เขียนทีละแถว (กันผลหายถ้าครึ่งทางพัง) — chunk แรก 'w' ที่เหลือ 'a'
    mode = "a" if start > 0 else "w"
    out_f = open(OUT_DIR / "ocr_results.csv", mode, newline="", encoding="utf-8-sig")
    writer = csv.writer(out_f)
    if start == 0:
        writer.writerow(header)

    for name in images:
        p = IMAGE_DIR / name
        img0 = cv2.imread(str(p))
        if img0 is None:
            print(f"  !! อ่านภาพไม่ได้: {name}", flush=True)
            continue
        H0, W0 = img0.shape[:2]
        up = max(H0, W0) / RESIZE_LONG        # สเกลจากภาพย่อ -> ต้นฉบับ

        for disk_no, cx, cy, r in sorted(geo[name]):
            try:
                cxo, cyo, ro = cx * up, cy * up, r * up
                pad = ro * PAD_RATIO
                x0, y0 = max(0, int(cxo - pad)), max(0, int(cyo - pad))
                x1, y1 = min(W0, int(cxo + pad)), min(H0, int(cyo + pad))
                crop = img0[y0:y1, x0:x1]
                if crop.size == 0:
                    continue
                # ขยายให้สูง ~UPSCALE_TO เพื่อให้ตัวอักษรคมพอ
                h = crop.shape[0]
                if h < UPSCALE_TO:
                    s = UPSCALE_TO / h
                    crop = cv2.resize(crop, (int(crop.shape[1] * s), int(crop.shape[0] * s)),
                                      interpolation=cv2.INTER_CUBIC)
                cv2.imwrite(str(CROP_DIR / f"{Path(name).stem}_d{disk_no}.jpg"), crop)
                raw, pred, score = ocr_best(reader, crop, candidates)
            except Exception as e:
                raw, pred, score = f"ERROR:{type(e).__name__}", "", 0.0

            t = truth.get((name, disk_no), "")
            correct = ""
            n_total += 1
            if t and norm(t):
                n_known += 1
                correct = "1" if norm(pred) == norm(t) else "0"
                n_correct += (correct == "1")
            writer.writerow((name, disk_no, t, raw, pred, score, correct))

        out_f.flush()
        print(f"  {name}: {len(geo[name])} แผ่น  (รวมถูก {n_correct}/{n_known})", flush=True)

    out_f.close()

    acc = (n_correct / n_known * 100) if n_known else 0.0
    print("\n===== สรุป OCR =====")
    print(f"แผ่นทั้งหมดที่ OCR: {n_total}")
    print(f"แผ่นที่มี ground truth: {n_known}")
    print(f"ทายรหัสยาถูก: {n_correct}  ({acc:.1f}%)")
    print(f"ผลเต็ม -> {OUT_DIR / 'ocr_results.csv'}  | crop -> {CROP_DIR}")


if __name__ == "__main__":
    main()
