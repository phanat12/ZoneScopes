# ZoneScope — สรุปงาน & แผนต่อ

อัปเดตล่าสุด: 2026-07-22

เป้าหมาย: สร้าง label วง zone of inhibition (แบบ **แยกชนิดยา / multi-class**) สำหรับเทรน YOLO-seg
จากภาพจานเพาะเชื้อ disk diffusion 61 ใบ โดยใช้ค่า diameter ที่ผู้เชี่ยวชาญวัดไว้ในชีต

---

## ทำถึงไหนแล้ว (เสร็จ ✅)

1. **ติดตั้ง environment** — เครื่องนี้ไม่มี Python มาก่อน ลง Python 3.12.7 (per-user) + `opencv-python` (cv2 5.0.0), `numpy` 2.5.1, `scipy` 1.18.0, `pandas`
   - รันสคริปต์ด้วย: `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" ชื่อไฟล์.py`
   - (python ไม่ได้อยู่บน PATH ต้องเรียกด้วย full path)

2. **ทดสอบ + จูนการหาแผ่นยา (Hough) กับภาพจริงทั้ง 61 ใบ**
   - ภาพจริง 4096×2304, ย่อ long→1500 ก่อนประมวลผล
   - **หาแผ่นได้แม่นมาก ไม่ต้องจูน param** — แผ่น 6mm เท่ากันหมด รัศมีนิ่ง 26–27px, px/mm ~8.7–9.4
   - param ที่ใช้: `minDist=45, param1=120, param2=28, minRadius=14, maxRadius=34`

3. **เจอปัญหา + ตัดสินใจ approach**
   - วิธีเดิม (`make_circle_labels.py`) จับคู่แผ่น→ค่าอัตโนมัติด้วย Hungarian → **ใช้ไม่ได้** สลับชื่อยา+ขนาดวงมั่ว (ดูตัวอย่างที่ P001, P005)
   - **เปลี่ยนเป็น workflow "เลขแผ่น" (เลือกโดยนุข)**: สคริปต์ใส่เลขแผ่นให้ → นุขระบุว่าเลขไหน=ยาอะไร → แม่น 100% ตัดการเดาออก

4. **เขียน pipeline ใหม่ 2 สคริปต์ (เทสต์แล้วทำงานครบ)**
   - `01_number_disks.py` — หาแผ่น + ใส่เลข 1..N (ตามเข็มนาฬิกาจากบน) + เก็บพิกัด
   - `02_build_labels.py` — อ่าน template ที่กรอก → วาดวง → export YOLO-seg + classes.txt

5. **แก้ false positive** — เพิ่มตัวกรองความสว่างในแผ่น (แผ่นจริง=กระดาษขาว inner 141–178, จุดปลอมบนวุ้น inner ~55)
   - P010 แก้แล้ว (เดิมเจอแผ่นปลอมที่ขอบล่าง) → ตอนนี้ **60/61 ใบนับตรงชีต**

6. **เพิ่มการดึง diameter จากชีตอัตโนมัติ** — กรอกแค่ช่อง `antibiotic` ปล่อย `diameter_mm` ว่าง สคริปต์ match ชื่อยากับชีตแล้วเติมค่า mm ให้เอง (เทสต์: ดึงได้ 386 ค่า)

7. **กรอก template เสร็จ + build label แล้ว (2026-07-22)**
   - นุขกรอก `antibiotic` ครบ 386 แถว (61 ใบ) → คัดลอกเข้า `zonescope_out/fill_template.csv`
     (ต้นฉบับที่นุขกรอก: `C:\Users\Administrator\Downloads\ZoneScope-main\antibiotic label - fill_template.csv`;
      template เปล่าเดิมสำรองไว้ที่ `fill_template.blank.bak.csv`)
   - เพิ่ม `SHEET_ALIAS` ใน `02_build_labels.py` แก้ชื่อยาพิมพ์เพี้ยนในชีต:
     `TPZ110→TZP110`, `P10*→P10`, `CAZ50→CZA50` → auto-lookup เจอ 386/387 แถว
   - `02_build_labels.py` fallback ใช้ `number_overlays/` วาด overlay เมื่อไม่มีภาพต้นฉบับ
   - **ผล: 61 label files, zone 281 วง, 29 classes, ไม่มี zone(ดื้อ) 98, ทำมือ 8**

---

## ยังไม่เสร็จ / รอบหน้าต้องทำ (TODO)

### ✅ แก้แล้ว (2026-07-22 รอบบ่าย)
- **ภาพต้นฉบับกลับมาแล้ว** ย้ายมาอยู่ที่ `C:\Users\Administrator\Downloads\22\ZoneScope-main\Automated Disk diffusion\P001–P061.jpg` (61 ใบครบ ไม่มีโฟลเดอร์ซ้อน)
  - แก้ `IMAGE_DIR` ใน `02_build_labels.py` ให้ชี้ path ใหม่แล้ว
- **ลง Python + lib ใหม่บนเครื่องนี้** (ของเดิมหายอีก): Python 3.12.7 (per-user) + opencv 5.0.0 + numpy 2.5.1
- **รัน `02_build_labels.py` ใหม่ด้วยภาพจริง** → overlay วาดบนภาพจานจริงแล้ว (ไม่ใช่ fallback number_overlays)
  - ผลเท่าเดิมเป๊ะ: 61 label, 281 วง, 29 classes, ไม่มี zone 98, ทำมือ 8, ดึงจากชีต 386
  - ตรวจตาแล้ว P001/P049 วงตรงตำแหน่ง — **ยืนยันปัญหา CL10 (P049 แผ่น1) วงใหญ่เกินจริง** (ดูข้อ 1 ด้านล่าง)

### ตัดสินใจแล้ว (2026-07-22)
1. ✅ **`CL10` (colistin) — ตัดทั้ง class แล้ว** colistin เป็น polymyxin กระจายในวุ้นไม่ได้
   (CLSI/EUCAST ต้องใช้ MIC) ตรวจภาพจริง 6 ใบ (P002/P006/P017/P049/P056 ฯลฯ) ไม่มีใบไหน
   ที่วงตรงกับ clear zone จริง — วาดคร่อมคราบดำ/พื้น lawn ทั้งหมด → poison dataset
   - เพิ่ม `DROP_ABX = {"CL10"}` ใน `02_build_labels.py` (ข้ามทั้งตอนสร้าง class + วาด)
   - CL10 ทั้ง 17 แผ่นขึ้น `dropped_class` ใน build_report
2. ⏭️ **`non-cir` 8 แผ่น — ปล่อยตามเดิม** (ไม่วาด flag manual) P004#6, P027#1-4,6, P028#4, P053#8
3. ⏭️ **P044 แผ่น 8 (TZP110) — ปล่อย** ชีตไม่มีค่า ไม่มี label แผ่นนี้
4. class `A` (P013#5) / `P` (P011#3) 0 instance — ยังปล่อยไว้ใน names (ถ้าจะลบ id จะเลื่อน)

### ผลล่าสุดหลังตัด CL10 (rebuild 2026-07-22)
- **28 classes, 266 วง zone, ไม่มี zone(ดื้อ) 96, ทำมือ 8, ข้าม(CL10) 17, ดึงจากชีต 369**
- overlay วาดบนภาพจริง ยืนยัน P056 ไม่มีวง colistin แล้ว

### ขั้นตอนถัดไป
1. ✅ ได้ภาพต้นฉบับคืน + rebuild ด้วยภาพจริงแล้ว → ตรวจ `label_overlays/` แล้ว
2. อัป `labels/` (28 class, 266 วง) + ภาพต้นฉบับ เข้า Roboflow
3. รัน build ใหม่ได้เสมอด้วย:
   ```
   & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" 02_build_labels.py
   ```

### เทรนรอบแรก 28-class บน Roboflow (2026-07-22) — baseline
- อัป Roboflow (Instance Segmentation) สำเร็จหลังแก้ปัญหา:
  - zip PowerShell เก็บ path เป็น `\` → Roboflow อ่าน label ไม่เจอ → ต้อง zip แบบ separator `/`
  - Resize อย่าใช้ "Fill (center crop)" (ครอปตัดแผ่น/วงขอบจานหาย) → ใช้ **"Fit within"**
- เทรน Roboflow 3.0 (Accurate) + checkpoint COCO → **mAP@50 ต่ำ: Valid 47% / Test 17.7%**
  (Test มีแค่ 5 รูป noise สูง) ปัญหาหลัก = **โมเดลตีวงได้ แต่แยกชนิดยาไม่ออก** (28 class ข้อมูลน้อย)

### 🔑 เปลี่ยนกลยุทธ์ → single-class "zone" + OCR (M5) — 2026-07-22
- ให้ YOLO ตรวจแค่ **"zone" class เดียว** (266 ตัวอย่าง) ชื่อยาไปอ่านด้วย OCR แยก
- สคริปต์ใหม่ `03_build_single_class.py` แปลง label 28-class → class id 0 ทั้งหมด (ไม่แตะของเดิม)
- output: `zonescope_dataset_single/` + `zonescope_dataset_single.zip` (Fit within, ทำ project ใหม่บน Roboflow)
- คาดว่า mAP จะสูงขึ้นมากเพราะข้อมูลต่อ class เยอะขึ้น

### OCR อ่านชื่อยา (M5) — 2026-07-22
- `04_ocr_disks.py` — crop แผ่นจากภาพต้นฉบับ → easyocr (หมุน 0/90/180/270, escalate 45° ถ้าคะแนนต่ำ)
  → fuzzy-match รหัสยา 29 ตัว (เน้นตัวอักษร) → เทียบ ground truth จาก build_report.csv
- ต้องลง easyocr (+torch CPU); CPU ช้า ~30 นาที/61 ใบ → รันเป็น chunk: `python 04_ocr_disks.py START END`
- **ผลรวมครบ 61 ใบ = 346/387 = 89.4%** (จูนจาก 50% ขึ้นมา; chunk [0:20]=87.8%, [20:61]=90.3%)
- เป็น OCR-assist: ~10% ที่พลาดให้คนยืนยัน (ดู score ต่ำใน ocr_results.csv)
- output: `ocr_results.csv` (truth เทียบ predicted), `ocr_crops/`

### zone inference ผ่าน Roboflow Workflow (serverless) — 2026-07-22
- local `inference` ต้อง premium → เปลี่ยนมาเรียก **workflow serverless ผ่าน REST** แทน
- `zone_infer.py` — `run_zone_workflow(image_path)` (urllib ล้วน, timeout+retry, `ZoneInferError`)
  - workflow: `disk-zone-detect-vdisk-zone-detect-1-yolov8s-seg-t1-logic` (workspace nuxh)
  - endpoint: `POST https://serverless.roboflow.com/nuxh/workflows/<id>`
  - **output key จริง = `predictions`** (ยืนยันจาก smoke test: P001 เจอ 8 zones)
  - `extract_zones()` เก็บ x/y/width/height/confidence/class (ไม่เอา polygon points), `save_image_outputs()` เขียนภาพ base64 ลงดิสก์
- **key**: `ROBOFLOW_API_KEY` อ่านจาก env หรือไฟล์ `.env` (ดู `.env.example`) — `.env` ถูก .gitignore
  - ⚠️ serverless คิด credit ต่อครั้ง (trial เหลือน้อย) เรียกเท่าที่จำเป็น
- smoke test: `python test_zone_infer.py` (ผ่านแล้ว ✅)

### รวมร่าง pipeline ครบวงจร (analyze.py) — 2026-07-22
- `interpret.py` — port ตรรกะ S/I/R จาก frontend (d≥s_min→S, d≤r_max→R, else I) + โหลด breakpoints.json
- `analyze.py` — `analyze_plate(image, organism)`: หาแผ่น+คาลิเบรต(01) → zone(zone_infer, cache) → OCR(04) → จับคู่ zone↔แผ่น → วัด มม. → interpret
  - cache zone ที่ `zone_cache/<stem>.json` (เรียกซ้ำ 0 credit)
  - **เทสต์ P001/enterobacterales: ออกผล S/I/R ครบ 8 แผ่น ✅** (ใช้ 1 credit)
- ⚠️ **จุดที่ต้องปรับต่อ (การวัดขนาด):**
  - วงเล็กวัดแม่น (AM10 11.3 vs ชีต 11, CRO30 30.8 vs 30) แต่ **วงใหญ่ที่ซ้อนกันวัดต่ำกว่าจริง**
    (AN30 19.8 vs 26 → พลิก S→I, CIP5 26.5 vs 34) เพราะ bbox ของ zone ที่ซ้อนถูกตัดสั้น
  - แนวทางแก้: วัดรัศมีจาก "จุดกลางแผ่น (รู้จาก Hough)" ไปขอบ zone ด้านที่ไม่ถูกวงข้างเคียงบัง
    (zone concentric กับแผ่น) แทนการใช้ bbox width/height
  - OCR ยังพลาด ~10% (P001#4 CXM30→AN30) — ให้คนยืนยัน

### FastAPI backend (server.py) — 2026-07-22
- `server.py` ห่อ pipeline เป็น REST ตาม contract frontend (`src/lib/api.js` + `analyze.json`)
  - `POST /api/analyze` (multipart `image`) → shape เดียวกับ analyze.json
    (disks + zone polygon + ocr_guess + flags, พิกัดภาพต้นฉบับ; **ไม่มี S/I/R** — client คำนวณเอง)
  - `GET /api/breakpoints` → breakpoints.json | `POST /api/report` → stub | `/uploads/*` static
  - cache zone ตาม cache_key = ชื่อไฟล์ที่อัป (ภาพเดิม = 0 credit; ภาพใหม่ = 1 credit)
- ลง `fastapi uvicorn python-multipart` แล้ว
- **เทสต์ผ่าน**: build_response(P001) + POST /api/analyze (P001, cache 0 credit) + static image 200
- **frontend ตั้ง `VITE_USE_MOCK=false` แล้ว** → proxy /api → :8000

### วิธีรันระบบเต็ม
```
# 1) backend (ต้องมี ROBOFLOW_API_KEY ใน ZoneScpe-backend/.env)
cd ZoneScpe-backend
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m uvicorn server:app --port 8000
# 2) frontend (restart ให้ Vite อ่าน .env ใหม่)
cd ../ZoneScope-main   (โฟลเดอร์ frontend)
npm run dev   → http://localhost:5173
# อัปโหลด P001.jpg = ฟรี (cache) ; ภาพอื่น = 1 credit/ใบ
```

### breakpoints ฉบับแลปรับรอง + เตรียม deploy — 2026-07-22
- **breakpoints.json ใหม่จาก `AST_data_review2.xlsx` (แลปรับรองแล้ว)** ผ่าน `gen_breakpoints.py`
  - **29 organisms, 30 antibiotics, 127 rules, `verified_by_lab=true`** เขียนทั้ง backend + frontend mock
  - เพิ่ม `antibiotics[]` มี `disk_aliases` → map **รหัส OCR (TZP110) → system code (TZP100_10)**
  - `interpret.py` อ่าน breakpoints จาก backend (ไม่ใช่ path frontend) + `disk_alias_map`/`ocr_candidates`
  - server.py/analyze.py แปลง OCR → system code ให้ตรง rules
- **เตรียม deploy ครบ:**
  - `requirements.txt`, `Dockerfile` (torch CPU + pre-download easyocr), `.dockerignore`
  - `server.py` เพิ่ม CORS (env `ZONESCOPE_CORS_ORIGINS`)
  - frontend `vercel.json` (rewrite /api,/uploads → backend), root `.gitignore`, `render.yaml`, `DEPLOY.md`
  - **git init + commit แล้ว** (repo root = โฟลเดอร์ frontend+backend) — พร้อม push GitHub
  - git ใช้ MinGit portable ที่ `C:\Users\Administrator\Downloads\MinGit\cmd\git.exe` (เครื่องไม่มี git)
- สถาปัตยกรรม: **Frontend→Vercel, Backend→host ที่ RAM≥2GB** (torch/easyocr หนัก; ดู DEPLOY.md)

### ต่อยอด (ถ้าจะทำ)
- ปรับการวัดขนาด zone (fit วงจากจุดกลางแผ่น) ให้แม่นขึ้น โดยเฉพาะวงซ้อน
- ทำ `/api/report` จริง (CSV/PDF export §5.4)
- เพิ่ม auth/rate-limit ที่ `/api/analyze` ก่อนเปิด public (กันเผา credit)
- rotate Roboflow API key (เคยโผล่ในสกรีนช็อต)

---

## ไฟล์สำคัญ

| ไฟล์ | คืออะไร |
|---|---|
| `01_number_disks.py` | ขั้น 1: หาแผ่น + ใส่เลข (รันแล้ว ผลอยู่ใน zonescope_out/) |
| `02_build_labels.py` | ขั้น 2: สร้าง label จาก template ที่กรอก |
| `03_build_single_class.py` | แปลง label 28-class → class เดียว "zone" (สำหรับเทรน) |
| `04_ocr_disks.py` | OCR อ่านชื่อยาบนแผ่น + วัดความแม่นกับ ground truth |
| `zone_infer.py` | เรียก Roboflow workflow ตรวจ zone (serverless) — `run_zone_workflow()` |
| `interpret.py` | ตรรกะ S/I/R (port จาก frontend) + โหลด breakpoints |
| `analyze.py` | **รวมร่างทั้ง pipeline** → ผล S/I/R ต่อแผ่น (`analyze_plate`) |
| `server.py` | **FastAPI backend** — `/api/analyze`, `/api/breakpoints`, `/api/report` |
| `uploads/` | ภาพจาน + crop ที่ backend เสิร์ฟ (gitignore ได้) |
| `test_zone_infer.py` | smoke test ของ zone_infer |
| `.env` / `.env.example` | เก็บ `ROBOFLOW_API_KEY` (`.env` gitignore ไว้) |
| `make_circle_labels.py` | สคริปต์เดิม (auto-match) — **เลิกใช้** เก็บไว้อ้างอิง |
| `zonescope_out/number_overlays/` | ภาพ 61 ใบ มีเลขแผ่นกำกับ — ไว้เปิดดูตอนกรอก |
| `zonescope_out/fill_template.csv` | **ตารางที่ต้องกรอก** (antibiotic ต่อเลขแผ่น) |
| `zonescope_out/sheet_reference.csv` | ค่าจากชีตเดิม ไว้อ้างอิง |
| `zonescope_out/disks_geometry.csv` | พิกัดแผ่น (สคริปต์ 2 ใช้ อย่าลบ) |
| `zonescope_out/number_report.csv` | สรุปว่าจานไหนนับตรง/ไม่ตรงชีต |

## Data
- ภาพ 61 ใบ: `C:\Users\Administrator\Downloads\Automated Disk diffusion\Automated Disk diffusion\P001–P061.jpg`
- ชีต: `C:\Users\Administrator\Downloads\Automated disk diffusion zone reader system - ชีต1.csv`
- (path ตั้งไว้ในตัวแปรหัวไฟล์ของแต่ละสคริปต์ ถ้าย้ายที่ต้องแก้)
