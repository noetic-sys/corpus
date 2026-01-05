FROM python:3.11-slim

# Ensure Python output is not buffered (logs appear immediately in containers)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required by claude-agent-sdk)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry for Python dependency management
RUN pip install --no-cache-dir poetry==2.0.1

# Copy ONLY dependency files (cached unless dependencies change)
COPY agents/qa/package.json agents/qa/pyproject.toml agents/qa/poetry.lock ./agents/qa/
COPY libs/ ./libs/

# Install Node dependencies globally
COPY agents/qa/package.json /tmp/package.json
RUN cd /tmp && \
    node -e "const pkg = require('./package.json'); \
             const deps = Object.keys(pkg.dependencies); \
             console.log(deps.join(' '))" | xargs npm install -g && \
    rm /tmp/package.json

# Install dependencies (this layer is cached)
WORKDIR /app/agents/qa
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main

# SECURITY: Remove package managers to prevent installation at runtime
RUN pip uninstall -y pip setuptools wheel && \
    rm -rf /usr/local/bin/pip* && \
    rm -rf /usr/local/lib/python3.11/site-packages/pip* && \
    rm -rf /usr/local/lib/python3.11/site-packages/setuptools* && \
    apt-get remove -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# SECURITY: Remove npm to prevent runtime package installation
RUN rm -rf /usr/bin/npm /usr/bin/npx /usr/lib/node_modules/npm

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 agentuser

# Copy prompts BEFORE code (changes less frequently)
COPY --chown=agentuser:agentuser prompts/ ./prompts/
COPY --chown=agentuser:agentuser agents/qa/prompts/ ./prompts/

# Copy application code (changes frequently - put LAST)
COPY --chown=agentuser:agentuser agents/qa/ ./agents/qa/

USER agentuser

WORKDIR /app/agents/qa

ENV PYTHONPATH=/app:/app/agents/qa/src

CMD ["python", "-m", "src.runner"]
