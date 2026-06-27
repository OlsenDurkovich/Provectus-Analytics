# Multi-stage build: Vite frontend → FastAPI runtime.
#
# Stage 1 (node) compiles the React app to /app/frontend/dist.
# Stage 2 (python) installs the backend, copies the built frontend in, and
# runs uvicorn. Railway expects the container to listen on $PORT.

# ── Stage 1: frontend build ───────────────────────────────────────────────
FROM node:20-bookworm-slim AS frontend
WORKDIR /app/frontend

# Reproducible install from the committed lockfile (package-lock.json).
# npm ci installs exact pinned versions and fails if lockfile and
# package.json disagree — better for deterministic deploys than npm install.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build


# ── Stage 2: python runtime ───────────────────────────────────────────────
FROM python:3.12-slim AS runtime
WORKDIR /app

# Build deps for any wheels that need them (bcrypt, pyjwt[cryptography] etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install deps first so changes to source don't blow the wheel cache.
COPY pyproject.toml requirements.txt ./
COPY src/ ./src/
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Synthetic dataset stays in the image so the app can boot before any FSP
# data is uploaded. Real PII (alumni_survey.xlsx, FSP Exports/) is uploaded
# at runtime to the mounted volume.
COPY synthetic_fsp_clients.csv synthetic_fsp_reservations.csv \
     synthetic_fsp_invoices.csv synthetic_alumni_survey.csv ./

# Bring in the built frontend from stage 1.
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# Static asset (favicon-ish) referenced by Sidebar.
COPY assets/ ./assets/

# Default storage paths — Railway should mount a volume at /data and rely on
# these defaults; locally, you can leave them unset and the in-repo paths win.
ENV DB_PATH=/data/provectus.db \
    FSP_EXPORTS_DIR=/data/fsp-exports \
    REAL_SURVEY_PATH=/data/alumni_survey.xlsx \
    PROVECTUS_ENV=prod

# Railway injects $PORT; default to 8080 locally.
ENV PORT=8080
EXPOSE 8080

# A small shim so we expand $PORT correctly (CMD JSON form doesn't interpolate).
CMD ["sh", "-c", "exec uvicorn provectus_analytics.api.main:app --host 0.0.0.0 --port ${PORT}"]
