FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy basecore package first (changes less frequently)
COPY packages/basecore /app/packages/basecore

# Install basecore package (separate layer for better caching)
WORKDIR /app/packages/basecore
RUN pip install --no-cache-dir -e .

# Copy service code last (changes most frequently)
WORKDIR /app
COPY apps/outbox-relay/src /app

CMD ["python", "-m", "outbox_relay.main"]

