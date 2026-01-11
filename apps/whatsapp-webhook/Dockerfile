FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
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

# Install additional dependencies
WORKDIR /app
RUN pip install --no-cache-dir uvicorn[standard]

# Copy service code
COPY apps/whatsapp-webhook/src /app

# Expose port
EXPOSE 8090

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8090/health || exit 1

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "whatsapp_webhook.main:app", "--host", "0.0.0.0", "--port", "8090"]

