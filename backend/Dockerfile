FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pip-tools for reproducible installs
RUN pip install --no-cache-dir --upgrade pip

# Copy source first so pip install has the package available
COPY . .

# Install dependencies (no -e: regular install, source already present)
RUN pip install --no-cache-dir ".[dev]"

EXPOSE 8000

# Railway injects $PORT; fall back to 8000 for local Docker use
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
