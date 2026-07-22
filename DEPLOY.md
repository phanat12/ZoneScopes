# ZoneScope — คู่มือ Deploy

ระบบมี 2 ส่วนที่ deploy คนละที่:

| ส่วน | โฟลเดอร์ | Deploy ที่ | เหตุผล |
|---|---|---|---|
| **Frontend** (React/Vite) | `ZoneScope-main/` | **Vercel** (static) | เว็บ static |
| **Backend** (FastAPI + easyocr) | `ZoneScpe-backend/` | **host ที่รัน Python + RAM ≥ 2GB** | torch/easyocr หนัก, ต้องเป็น server ถาวร |

> ⚠️ **Backend ขึ้น Vercel ไม่ได้** — torch+easyocr เกินลิมิตขนาด (250MB) และ analyze ใช้ ~30 วิ/ภาพ เกิน timeout ของ serverless

---

## สิ่งที่ต้องรู้ก่อน

1. **RAM ของ backend**: easyocr + torch กินแรม ~1.5–2GB → **free tier ส่วนใหญ่ (512MB) จะ OOM**
   - host ที่พอ: **Hugging Face Spaces** (CPU space ฟรี RAM เยอะ), Railway, Render (plan standard+), Fly.io (2GB), VPS
2. **credit Roboflow**: ทุกภาพใหม่ที่วิเคราะห์ = 1 credit (serverless) → ระวังถ้าเปิด public
3. **API key เคยโผล่ในสกรีนช็อต** → ควร **Generate New Key** ที่ app.roboflow.com/settings/api แล้วใช้ตัวใหม่
4. **breakpoints ผ่านการรับรองแล้ว** (`verified_by_lab: true`, จาก AST_data_review2.xlsx) ✅

---

## 1) Backend (ตัวอย่าง: Render ผ่าน Docker)

โค้ด backend มี `Dockerfile` + `requirements.txt` พร้อมแล้ว

1. push repo ขึ้น GitHub (ดูส่วนล่าง)
2. Render → **New → Blueprint** ชี้ repo (จะอ่าน `render.yaml`) หรือ **New → Web Service (Docker)** ชี้ `ZoneScpe-backend/Dockerfile`
3. เลือก plan **RAM ≥ 2GB**
4. ตั้ง Environment Variables:
   - `ROBOFLOW_API_KEY` = คีย์จริง (secret)
   - `ZONESCOPE_CORS_ORIGINS` = URL frontend เช่น `https://your-app.vercel.app`
5. deploy → ได้ URL เช่น `https://zonescope-backend.onrender.com`
6. เช็ก: เปิด `https://<backend>/api/breakpoints` ต้องได้ JSON

> **Hugging Face Spaces (ฟรี RAM เยอะ)**: สร้าง Space แบบ Docker, อัป `ZoneScpe-backend/`, ตั้ง secret `ROBOFLOW_API_KEY` — ใช้ Dockerfile เดิมได้เลย (พอร์ต 7860 → แก้ CMD/`PORT` ตามที่ Spaces กำหนด)

---

## 2) Frontend (Vercel)

1. Vercel → **New Project** ชี้ repo
2. **Root Directory** = `ZoneScope-main` (โฟลเดอร์ frontend ที่มี `package.json`)
3. Framework: **Vite** (auto), Build: `npm run build`, Output: `dist`
4. Environment Variable: `VITE_USE_MOCK` = `false`
5. **แก้ `ZoneScope-main/vercel.json`** เปลี่ยน `REPLACE-WITH-YOUR-BACKEND-HOST` เป็น host backend จริง (ทั้ง 2 บรรทัด `/api` และ `/uploads`)
   - vercel.json นี้ทำหน้าที่ proxy `/api` และ `/uploads` ไป backend (แทน dev proxy ของ vite)
6. Deploy → ได้ URL frontend
7. กลับไปตั้ง `ZONESCOPE_CORS_ORIGINS` ที่ backend ให้ตรง URL นี้

---

## 3) ขึ้น GitHub

repo root = โฟลเดอร์นี้ (`ZoneScope-main/ZoneScope-main/`) มี frontend + backend + `.gitignore` แล้ว

```bash
git init
git add .
git commit -m "ZoneScope: full pipeline + FastAPI backend, verified breakpoints"
git branch -M main
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```

`.gitignore` กัน `node_modules/`, `.env` (คีย์!), `uploads/`, `zone_cache/`, ไฟล์ `.zip`, dataset ใหญ่ไว้แล้ว

---

## ตัวแปร environment ทั้งหมด

| ที่ | ตัวแปร | ค่า |
|---|---|---|
| Backend host | `ROBOFLOW_API_KEY` | คีย์ Roboflow (secret) |
| Backend host | `ZONESCOPE_CORS_ORIGINS` | `https://your-app.vercel.app` |
| Backend host | `PORT` | host ส่วนใหญ่ตั้งให้เอง |
| Vercel | `VITE_USE_MOCK` | `false` |

---

## ข้อควรระวังก่อน "ใช้จริง"
- ยังไม่มี auth ที่ `/api/analyze` → public = ใครก็ยิงเผา credit ได้ ควรเพิ่ม token/rate-limit
- การวัดขนาดวงใหญ่ที่ซ้อนกันยังต่ำกว่าจริง (ดู PROGRESS.md) — ควรปรับก่อนใช้ตัดสินทางคลินิก
- `/api/report` ยังเป็น stub (ยังไม่ export CSV/PDF)
