
# Multi-stage Dockerfile for digicloset
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY DIGICLOSET /frontend
RUN cd /app/frontend && if [ -f package.json ]; then npm ci --production=false && npm run build || true; fi

FROM python:3.11-slim AS backend-build
WORKDIR /app/backend
COPY DIGICLOSET /backend
RUN pip install --no-cache-dir -U pip setuptools wheel &&     if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt || true; fi

FROM python:3.11-slim
WORKDIR /app
# Copy backend
COPY --from=backend-build /app/backend /app/backend
# Copy frontend build (if exists)
COPY --from=frontend-build /app/frontend/build /app/backend/static || true

ENV PYTHONUNBUFFERED=1
CMD ["python", "backend/app.py"]
