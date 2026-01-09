FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first and install dependencies (changes less frequently than code)
COPY apps/verticals/construction/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared packages and install (changes less frequently than app code)
COPY packages/basecore /app/packages/basecore
COPY packages/engines_core /app/packages/engines_core
RUN pip install --no-cache-dir -e /app/packages/basecore
RUN pip install --no-cache-dir -e /app/packages/engines_core

# Copy application code last (changes most frequently)
COPY apps/verticals/construction/src /app/src
COPY apps/verticals/construction/alembic /app/alembic
COPY apps/verticals/construction/alembic.ini /app/alembic.ini

# Set PYTHONPATH
ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uvicorn", "construction_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
