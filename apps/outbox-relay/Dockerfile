FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy basecore package
COPY packages/basecore /app/packages/basecore

# Copy service code
COPY apps/outbox-relay/src /app

# Install basecore package
WORKDIR /app/packages/basecore
RUN pip install --no-cache-dir -e .

# Back to app directory
WORKDIR /app

CMD ["python", "-m", "outbox_relay.main"]

