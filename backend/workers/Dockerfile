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

# Install dependencies from backend directory (this layer is cached)
WORKDIR /app/backend
RUN poetry config virtualenvs.create false \
    && poetry install -vvv --no-interaction --no-ansi --no-root

# Development stage
FROM python:3.11-slim as development

# Ensure Python output is not buffered (logs appear immediately in containers)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Docker CLI for workflow execution
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application maintaining directory structure
COPY libs/ ./libs/
COPY prompts/ ./prompts/
COPY backend/ ./backend/
COPY backend/workers/entrypoint.sh /entrypoint.sh

# Create non-root user and add to docker group
RUN groupadd -g 999 docker || true \
    && useradd -m -u 1000 appuser \
    && usermod -aG docker appuser \
    && chown -R appuser:appuser /app \
    && chmod +x /entrypoint.sh

WORKDIR /app/backend

ENTRYPOINT ["/entrypoint.sh"]

# Production stage - NO DOCKER (K8s only)
FROM python:3.11-slim as production

# Ensure Python output is not buffered (logs appear immediately in containers)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime dependencies only (NO DOCKER)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application maintaining directory structure
COPY --chown=1000:1000 libs/ ./libs/
COPY --chown=1000:1000 prompts/ ./prompts/
COPY --chown=1000:1000 backend/ ./backend/

# Create non-root user (no docker group)
RUN useradd -m -u 1000 appuser
USER appuser

WORKDIR /app/backend

# Production uses K8s for workflow execution, not Docker
