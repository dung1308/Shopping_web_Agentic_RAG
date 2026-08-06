FROM python:3.11-slim

WORKDIR /workspace

# System dependencies (for Playwright + asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Install Playwright browsers
RUN playwright install chromium --with-deps

COPY . .

EXPOSE 8000 8001
