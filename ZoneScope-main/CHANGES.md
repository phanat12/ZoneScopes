# บันทึกการแก้ไข — ZoneScope frontend

สรุปสิ่งที่ทำในเซสชันวันที่ 2026-07-18

## 0. ตั้งค่าเครื่อง (VSCode ใหม่)
- Node.js ลงไว้แล้วที่ `C:\Program Files\nodejs` (v24.18.0, npm 11.16.0) แต่ **ไม่อยู่ใน PATH**
- แก้แล้ว: เพิ่ม `C:\Program Files\nodejs` เข้า **User PATH** ถาวร
- รันเว็บ: `cd Autodisk/frontend` แล้ว `npm run dev` → http://localhost:5173/
  (ครั้งแรกหลังแก้ PATH ให้เปิด terminal/VSCode ใหม่ก่อน)

## 1. ฟอนต์ PSU Stidti
- แตกไฟล์ `PSU_Stidti _Webfont.zip` → ก๊อป woff2/woff เข้า `public/fonts/`
- ประกาศ `@font-face` 6 น้ำหนัก (light/regular/bold + italic) ใน `src/index.css`
- ตั้งเป็นฟอนต์หลัก (body + Tailwind `font-sans`), มี Inter เป็น fallback
- ตัวเลขวัดค่า (`.tnum`) ยังใช้ JetBrains Mono (tabular-nums) ตามเดิม

## 2. ธีมขาว–น้ำเงิน
- รีสกิน palette ทั้งระบบใน `tailwind.config.js` + `src/index.css`
  - primary: น้ำเงิน `#1E64C8` (เดิมเขียว teal)
  - surface/neutral: ขาว–ฟ้าอ่อน (เดิมครีม)
- ทุกหน้าเปลี่ยนตามอัตโนมัติ (ปุ่ม, แถบบน, marker, ผล S/I/R)

## 3. หน้า Upload
- ลบข้อความ "ใช้ภาพที่ถ่ายจากกล่องถ่ายภาพ… ไม่ถ่ายสดผ่านเบราว์เซอร์…"
- ลบข้อความ "เกณฑ์ S/I/R ขึ้นกับคู่ (เชื้อ + ยา) จึงต้องเลือกก่อน"
- ลบคำว่า "(จำเป็น)" ที่ชนิดเชื้อ
- ชนิดเชื้อ → **dropdown ค้นหาได้** (คอมโพเนนต์ใหม่ `src/components/OrganismSelect.jsx`)
- "รหัสจาน (ไม่บังคับ)" → **"Plate name"** และตัดตัวอย่าง "เช่น P023" ออก
- เพิ่มบรรทัดอ้างอิงมาตรฐาน + จัด section ให้ดูเป็นงานจริง

## 4. ข้อมูลเชื้อ/ยา จาก AST_data_review.xlsx
- ถอดข้อมูลจริงจาก Excel (ชีต Breakpoints + รหัสยา) เขียนลง `src/mocks/breakpoints.json`
- **เชื้อ 3 → 25 ตัว**, ยา 30 ตัว, เกณฑ์ S/I/R 127 คู่
- ใส่ธง `verified_by_lab: false` — ข้อมูลยังต้องให้ทีมแลปตรวจรับรองก่อนใช้จริง
  (ตามที่เอกสารต้นฉบับเตือน)

## ยังไม่ได้ทำ / ต่อได้
- เพิ่มเชื้อระดับ species จากชีต Intrinsic/QC (เช่น K. pneumoniae, P. mirabilis)
  โดยแมปเกณฑ์อิงกลุ่ม Enterobacterales
- ให้ทีมแลปตรวจค่า breakpoint รายแถวแล้วตั้ง verified_by_lab = true
