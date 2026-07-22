# ZoneScope — Frontend (M1)

เว็บอ่านจาน **Disk Diffusion (Kirby–Bauer)** อัตโนมัติ — วัดวงยับยั้ง (inhibition zone) แล้วตัดสิน **S / I / R**
มือถือเป็นหลัก (mobile-first). เฟสนี้ (M1) รันด้วย **mock data** ล้วน ยังไม่ต้องมี backend

## รันเดโม

```bash
npm install
npm run dev        # เปิด http://localhost:5173
```

Build / preview:

```bash
npm run build && npm run preview
```

## สลับ mock / backend จริง

แก้ไฟล์ `.env`:

```
VITE_USE_MOCK=true    # อ่าน src/mocks/analyze.json (ค่าเริ่มต้น, ไม่ต้องมี backend)
VITE_USE_MOCK=false   # ยิง POST /api/analyze จริง (dev proxy -> FastAPI :8000)
```

## Flow (4 หน้า)

1. **Upload** — เลือกรูปจาน + เลือกชนิดเชื้อ (จำเป็น) + รหัสจาน (ไม่บังคับ)
2. **Processing** — progress บอกขั้นตอน: หาจาน → หา disk + คาลิเบรต → วัดวงยับยั้ง
3. **Review & Assign** — ภาพจาน (marker 1..N + overlay ขอบวง, ซูม/แพน, sync สองทางกับรายการ),
   ระบุยาต่อ disk (dropdown พิมพ์กรอง), แก้ค่า มม. ได้, S/I/R คำนวณสด, กันยาซ้ำ, จำ panel ล่าสุด
4. **Results** — ภาพ overlay + ค่า มม., ตารางผล S/I/R, มาร์คค่าที่คนแก้, export CSV / PDF

## โครงสร้าง

```
src/
  lib/
    api.js            สลับ mock/real + จำลองขั้นตอน pipeline
    interpret.js      ตรรกะ S/I/R (client-side, §5.3) + ความหมาย flag/warning
    exportReport.js   สร้าง payload /api/report + CSV (เก็บ edited_by_user + ค่าเดิม)
    recentPanel.js    จำชุดยาล่าสุด (localStorage)
  store/useSession.js  session ต่อจาน (Zustand) + selectors (results, ยาที่ใช้แล้ว)
  components/          ImageCanvas, DiskRow, AntibioticSelect, Sheet, SIRChip,
                       FlagBadge, CalibrationBar, ResultTable, PrintReport, AppBar
  pages/              Upload, Processing, Review, Results
  mocks/              analyze.json, breakpoints.json
scripts/gen-mock.mjs  สร้างภาพจานสังเคราะห์ (public/plate.svg) + mock ที่พิกัดตรงกัน
```

Regenerate mock + synthetic plate: `npm run gen:mock`

## หมายเหตุสำคัญ

- **พิกัดทุกอย่าง = พิกเซลภาพต้นฉบับ** frontend สเกลเองตอนแสดง (§5.1, §9.2)
- **`no_zone` = 6.0 มม.** (เท่าขนาด disk = ดื้อสนิท) ไม่ใช่ 0/null (§9.4)
- **ค่า breakpoint ใน `mocks/breakpoints.json` เป็นค่าสมมติสำหรับเดโม** — ต้องให้ทีมแลปกรอกค่าจริง
  จาก CLSI/EUCAST ก่อนใช้งานจริง (§5.2, §9.8)
- ไม่มีถ่ายสดผ่านเบราว์เซอร์ (ตั้งใจ — คงค่าคาลิเบรตให้ตรงโดเมนที่โมเดลเทรน, §2)

## ถัดไป (ยังไม่ทำใน M1)

M2 backend `/api/analyze` (OpenCV classical) · M3 YOLO-seg · M4 breakpoint จริง · M5 export + OCR-assist
