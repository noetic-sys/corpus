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
    && poetry install --no-interaction --no-ansi --no-root

# Production stage (no development stage needed for migrations)
FROM python:3.11-slim as production

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy libs (changes less frequently)
COPY --chown=1000:1000 libs/ ./libs/

# Copy ONLY what's needed for alembic (not entire backend/)
COPY --chown=1000:1000 backend/alembic.ini ./backend/alembic.ini
COPY --chown=1000:1000 backend/alembic/ ./backend/alembic/
COPY --chown=1000:1000 backend/common/ ./backend/common/
COPY --chown=1000:1000 backend/packages/ ./backend/packages/

# Create non-root user
RUN useradd -m -u 1000 appuser
USER appuser

WORKDIR /app/backend

# Default command
CMD ["alembic", "upgrade", "head"]
