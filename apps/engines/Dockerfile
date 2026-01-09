FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy basecore package
COPY packages/basecore /app/packages/basecore

# Copy engines_core package (independent from verticals)
COPY packages/engines_core /app/packages/engines_core

# Copy service code
COPY apps/engines/src /app

# Install basecore package
WORKDIR /app/packages/basecore
RUN pip install --no-cache-dir -e .

# Install engines_core package
WORKDIR /app/packages/engines_core
RUN pip install --no-cache-dir -e .

# Install remaining dependencies
WORKDIR /app
RUN pip install --no-cache-dir pydantic-settings redis

# NOTE: No backend/ code is copied - engines are fully independent

CMD ["python", "-m", "engines_worker.main"]
