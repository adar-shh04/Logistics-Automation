FROM python:3.11-slim

LABEL maintainer="adar-shh04"

# System deps for EasyOCR and others
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential tesseract-ocr libgl1 libglib2.0-0 curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app/requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /app/requirements.txt

# Create necessary directories
RUN mkdir -p /app/models /data/uploads /app/hsdata

COPY app /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/
ENV UPLOAD_DIR=/data/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
