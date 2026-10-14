# syntax=docker/dockerfile:1

# --- 1) Build the PWA (React + Vite) ---------------------------------------
FROM node:20-alpine AS web
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json vite.config.ts index.html ./
COPY public ./public
COPY src ./src
RUN npm run build

# --- 2) Runtime: FastAPI (also serves the built PWA) + Playwright ----------
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
# Kept as its own layer so a requirements change does not re-download Chromium.
RUN python -m playwright install --with-deps chromium
COPY backend/ ./backend/
COPY --from=web /web/dist ./dist
WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
