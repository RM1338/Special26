# 04 §8, D-33. One image: built React app + FastAPI + seeds (+ replay data once recorded).
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-hin \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt ./
RUN grep -v '^pytest' requirements.txt > req-runtime.txt && pip install --no-cache-dir -r req-runtime.txt
COPY backend/special26 ./special26
COPY data/seeds ./seeds
COPY data/demo.db ./replay/demo.db
COPY --from=web /web/dist ./static
ENV PYTHONUNBUFFERED=1 \
    SPECIAL26_SEEDS_DIR=/app/seeds \
    SPECIAL26_STATIC_DIR=/app/static \
    SPECIAL26_DB_PATH=/app/data/special26.db \
    SPECIAL26_UPLOADS_DIR=/app/data/uploads \
    SPECIAL26_DEMO_DB=/app/replay/demo.db
EXPOSE 8000
# Railway sets $PORT; one worker keeps memory inside the free plan (D-33)
CMD ["sh", "-c", "uvicorn special26.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
