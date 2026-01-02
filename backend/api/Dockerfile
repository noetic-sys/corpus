# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==2.0.1

# Copy ONLY dependency files (cached unless dependencies change)
COPY backend/pyproject.toml backend/poetry.lock ./backend/
COPY libs/ ./libs/

# Install dependencies (this layer is cached)
WORKDIR /app/backend
RUN poetry config virtualenvs.create false \
    && poetry install -vvv --no-interaction --no-ansi --no-root

# Development stage
FROM python:3.11-slim as development

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy libs and prompts (changes less frequently)
COPY libs/ ./libs/
COPY prompts/ ./prompts/

# Copy application code (changes frequently - put last)
COPY backend/ ./backend/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

WORKDIR /app/backend

# Production stage
FROM python:3.11-slim as production

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy libs and prompts (changes less frequently)
COPY --chown=1000:1000 libs/ ./libs/
COPY --chown=1000:1000 prompts/ ./prompts/

# Copy application code (changes frequently - put last)
COPY --chown=1000:1000 backend/ ./backend/

# Create non-root user
RUN useradd -m -u 1000 appuser
USER appuser

WORKDIR /app/backend

# Default command - use Gunicorn with Uvicorn workers for better concurrency
# Workers configurable via GUNICORN_WORKERS env var (default: 2 for horizontal scaling)
CMD ["sh", "-c", "gunicorn api.main:app -w ${GUNICORN_WORKERS:-2} -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120 --keep-alive 5"]
