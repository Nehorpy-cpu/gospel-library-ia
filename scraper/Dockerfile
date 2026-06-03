FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    SCRAPY_SETTINGS_MODULE=app.crawler.settings

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gcc \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-spa \
    tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml scrapy.cfg alembic.ini ./
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts

RUN pip install --no-cache-dir ".[ocr]" \
    && playwright install --with-deps chromium

CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8080"]
