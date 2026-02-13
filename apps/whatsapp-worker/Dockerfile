FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy packages first (changes less frequently)
COPY packages/basecore /app/packages/basecore
COPY packages/messaging_whatsapp /app/packages/messaging_whatsapp

# Install packages
WORKDIR /app/packages/basecore
RUN pip install --no-cache-dir -e .

WORKDIR /app/packages/messaging_whatsapp
RUN pip install --no-cache-dir -e .

# Copy service code
WORKDIR /app
COPY apps/whatsapp-worker/src /app

# NOTE: No vertical code is copied - worker is fully independent

CMD ["python", "-m", "whatsapp_worker.main"]




