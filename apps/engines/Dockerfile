FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy packages first (changes less frequently)
COPY packages/basecore /app/packages/basecore
COPY packages/engines_core /app/packages/engines_core

# Install packages (separate layer for better caching)
WORKDIR /app/packages/basecore
RUN pip install --no-cache-dir -e .

WORKDIR /app/packages/engines_core
RUN pip install --no-cache-dir -e .

# Install remaining dependencies (before copying code for better caching)
WORKDIR /app
RUN pip install --no-cache-dir pydantic-settings redis

# Copy service code last (changes most frequently)
COPY apps/engines/src /app

# NOTE: No construction-backend/ code is copied - engines are fully independent

CMD ["python", "-m", "engines_worker.main"]
