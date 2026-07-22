---
title: ZoneScope Backend
emoji: 🧫
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
---

# ZoneScope Backend

FastAPI service สำหรับวิเคราะห์จานเพาะเชื้อ Kirby-Bauer:
disk detection + calibration → Roboflow zone detection → OCR antibiotic → วัด mm → S/I/R (verified breakpoints)

## Endpoints
- `POST /api/analyze` — multipart field `image` → คืน disks / zones / ocr_guess
- `GET /api/breakpoints` — ตาราง breakpoints (verified_by_lab)
- `POST /api/report` — stub

## Environment (ตั้งใน Space → Settings → Variables and secrets)
- `ROBOFLOW_API_KEY` (secret) — คีย์ Roboflow serverless
- `ZONESCOPE_CORS_ORIGINS` — URL frontend เช่น `https://your-app.vercel.app`

รายละเอียดเพิ่มเติมดู `PROGRESS.md`
