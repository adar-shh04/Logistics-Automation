FROM python:3.11-slim

# System deps for EasyOCR/Tesseract fallback (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential tesseract-ocr libgl1 libglib2.0-0 curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel && pip install -r /app/requirements.txt

# Create models dir
RUN mkdir -p /app/models /data/uploads /app/hsdata

COPY app /app

ENV PYTHONUNBUFFERED=1
ENV UPLOAD_DIR=/data/uploads
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
