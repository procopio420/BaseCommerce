FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy basecore package
COPY packages/basecore /app/packages/basecore

# Copy service code
COPY apps/vertical-materials/src /app

# Copy shared app code (models, schemas, domain, platform, etc.)
COPY backend/app /app/app

# Install basecore package
WORKDIR /app/packages/basecore
RUN pip install --no-cache-dir -e .

# Install service dependencies
WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

EXPOSE 8000

CMD ["uvicorn", "materials_app.main:app", "--host", "0.0.0.0", "--port", "8000"]

