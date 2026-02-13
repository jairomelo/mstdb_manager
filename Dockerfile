# ================================
# Stage 1: Build Svelte Frontend
# ================================
FROM node:22-alpine AS frontend-builder

WORKDIR /frontend

# Copy package files
COPY mstdb_theme/package*.json ./

# Install dependencies
RUN npm ci --prefer-offline --no-audit

# Copy source files
COPY mstdb_theme/ ./

# Build static files
RUN npm run build

# ================================
# Stage 2: Development
# ================================
FROM python:3.11-slim AS development

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements
COPY mstdb_manager/requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY mstdb_manager/ .

# Copy frontend build (for development with mounted volumes)
COPY --from=frontend-builder /frontend/build /app/staticfiles/frontend

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /app/logs

# Expose port
EXPOSE 8000

# Development command (overridden in docker-compose.dev.yml)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ================================
# Stage 3: Production
# ================================
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=mdb.settings

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/staticfiles /app/media /app/logs /backups && \
    chown -R appuser:appuser /app /backups

WORKDIR /app

# Copy requirements and install as root
COPY mstdb_manager/requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt gunicorn

# Copy application code
COPY --chown=appuser:appuser mstdb_manager/ .

# Copy frontend build from builder stage
COPY --from=frontend-builder --chown=appuser:appuser /frontend/build /app/staticfiles/frontend

# Copy entrypoint script
COPY --chown=appuser:appuser mstdb_manager/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Collect static files (Django admin, API browsable, etc.)
RUN python manage.py collectstatic --noinput --clear || true

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command
CMD ["gunicorn", "mdb.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
