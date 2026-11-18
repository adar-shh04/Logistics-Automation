FROM python:3.11-slim

LABEL maintainer="adar-shh04"

# System deps for EasyOCR and others
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential tesseract-ocr libgl1 libglib2.0-0 curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root app user
RUN useradd -m -u 1001 appuser

WORKDIR /app
COPY app/requirements.txt /app/requirements.txt

# Install dependencies (CPU torch first to avoid downloading large CUDA packages)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /app/requirements.txt

# Pre-download EasyOCR models into /home/appuser/.EasyOCR as appuser
USER appuser
RUN python -c "import easyocr; easyocr.Reader(['en'])"
USER root

# Create necessary directories and set ownership
RUN mkdir -p /app/models /data/uploads /app/hsdata && \
    chown -R appuser:appuser /app /data/uploads

COPY --chown=appuser:appuser app /app

USER appuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/
ENV UPLOAD_DIR=/data/uploads

CMD ["python", "-m", "app.stream_worker"]
