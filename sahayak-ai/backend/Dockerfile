# Pinned to bookworm: the apt package names below (notably libglib2.0-0, which
# becomes libglib2.0-0t64 in trixie) differ on newer Debian releases.
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Tesseract powers LIVE mode's offline OCR; without the binary the pipeline
# reports "no engine" and falls back to DEMO. The -eng language data is a
# Recommends, so --no-install-recommends would otherwise skip it. libglib2.0-0
# is required by opencv-python-headless on slim images.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"