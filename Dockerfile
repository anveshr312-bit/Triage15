# Multi-stage Dockerfile for Triage15 Cloud Deployment on Railway

# ==========================================
# Stage 1: Build the React / Vite Frontend
# ==========================================
FROM node:22-bookworm-slim AS frontend-builder
WORKDIR /build/frontend

# Build-time arguments for Vite public environment variables (secrets never exposed here)
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_PUBLISHABLE_KEY
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
    VITE_SUPABASE_PUBLISHABLE_KEY=$VITE_SUPABASE_PUBLISHABLE_KEY

# Install dependencies using clean install
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source and build static distribution
COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Python Backend Runtime
# ==========================================
FROM python:3.12-slim AS runtime

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend:/app \
    FRONTEND_DIST_DIR=/app/frontend/dist \
    DATABASE_URL=sqlite:////data/triage15.db \
    ENVIRONMENT=production \
    ALLOW_DATABASE_RESET=false \
    PORT=8000

WORKDIR /app

# Install system dependencies (curl for container health inspection)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application code
COPY backend/ /app/backend/
COPY ml/ /app/ml/

# Copy compiled frontend assets from builder stage
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# Ensure the /data mount directory exists for the Railway persistent volume
RUN mkdir -p /data && chmod 777 /data

# Expose default port (Railway injects $PORT at runtime)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://127.0.0.1:${PORT:-8000}/api/health || exit 1

# Start Uvicorn with single worker on 0.0.0.0 binding to $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
