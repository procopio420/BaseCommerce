FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy basecore package first (changes less frequently)
COPY packages/basecore /app/packages/basecore

# Install basecore package (separate layer for better caching)
RUN pip install --no-cache-dir -e /app/packages/basecore

# Install Python dependencies (before copying code for better caching)
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    pydantic-settings \
    pydantic[email] \
    sqlalchemy \
    psycopg2-binary \
    jinja2 \
    python-multipart

# Copy auth service code last (changes most frequently)
COPY apps/auth/src /app/src

# Set PYTHONPATH
ENV PYTHONPATH=/app/src

EXPOSE 8001

# HEALTHCHECK removed - using docker-compose.yml healthcheck instead to avoid duplication

CMD ["uvicorn", "auth_app.main:app", "--host", "0.0.0.0", "--port", "8001"]
