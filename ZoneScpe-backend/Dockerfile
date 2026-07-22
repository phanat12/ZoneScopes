# ZoneScope backend — FastAPI + easyocr (CPU) + opencv
FROM python:3.12-slim

# lib ที่ opencv / easyocr ต้องใช้ตอน runtime
# libgl1 จำเป็นเพราะ ultralytics ดึง opencv-python (ตัวเต็ม) มาทับ headless -> import cv2 ต้องมี libGL
RUN apt-get update && apt-get install -y --no-install-recommends \
      libglib2.0-0 libgomp1 libgl1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ติดตั้ง torch/torchvision แบบ CPU ก่อน (image เล็กกว่า CUDA มาก)
RUN pip install --no-cache-dir torch torchvision \
      --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# โหลดโมเดล easyocr เข้า image ตั้งแต่ build (เลี่ยงดาวน์โหลดตอน request แรก)
RUN python -c "import easyocr; easyocr.Reader(['en'])"

COPY . .

# ROBOFLOW_API_KEY / ZONESCOPE_CORS_ORIGINS ตั้งเป็น env บน host (อย่า hardcode)
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
