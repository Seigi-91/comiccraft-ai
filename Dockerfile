FROM node:20-alpine AS frontend
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-cjk && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN python -m pip install --no-cache-dir -e .
COPY --from=frontend /ui/dist ./frontend/dist
ENV COMIC_FONT_PATH=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
