FROM python:3.11-slim

# Ensure Python output is not buffered (logs appear immediately in containers)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install all system dependencies (before removal of package managers)
RUN apt-get update && apt-get install -y \
    # Build dependencies
    curl \
    # OOXML manipulation (DOCX/PPTX are ZIP archives)
    zip \
    unzip \
    # PDF processing tools
    poppler-utils \
    qpdf \
    tesseract-ocr \
    # Office document conversion (large: ~400MB)
    libreoffice \
    # Image processing dependencies for Sharp
    libpng-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required by claude-agent-sdk)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry for Python dependency management
RUN pip install --no-cache-dir poetry==2.0.1

# Copy ONLY dependency files (cached unless dependencies change)
COPY agents/workflow/package.json agents/workflow/pyproject.toml agents/workflow/poetry.lock ./agents/workflow/
COPY libs/ ./libs/

# Install Node dependencies globally
COPY agents/workflow/package.json /tmp/package.json
RUN cd /tmp && \
    node -e "const pkg = require('./package.json'); \
             const deps = Object.keys(pkg.dependencies); \
             console.log(deps.join(' '))" | xargs npm install -g && \
    rm /tmp/package.json

# Install dependencies (this layer is cached)
WORKDIR /app/agents/workflow
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main

# NOTE: Playwright browser binaries (Chromium) not installed until networking policies are configured
# TODO: Run `npx playwright install chromium --with-deps` once networking is figured out

# SECURITY: Remove package managers and build tools to prevent installation at runtime
RUN pip uninstall -y pip setuptools wheel && \
    rm -rf /usr/local/bin/pip* && \
    rm -rf /usr/local/lib/python3.11/site-packages/pip* && \
    rm -rf /usr/local/lib/python3.11/site-packages/setuptools* && \
    apt-get remove -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# SECURITY: Remove npm to prevent runtime package installation
# Claude Code CLI is already installed, node_modules are global, npm is no longer needed
RUN rm -rf /usr/bin/npm /usr/bin/npx /usr/lib/node_modules/npm

WORKDIR /app

# Create non-root user first
RUN useradd -m -u 1000 agentuser

# Copy skills in ONE layer (changes less frequently)
COPY --chown=agentuser:agentuser agents/workflow/skills/document-skills/ /home/agentuser/.claude/skills/

# Make skills directory read-only for containment
RUN chmod -R 555 /home/agentuser/.claude/skills

# Copy prompts (changes less frequently than code)
COPY --chown=agentuser:agentuser agents/workflow/prompts/ ./prompts/

# Copy application code (changes frequently - put LAST)
COPY --chown=agentuser:agentuser agents/workflow/ ./agents/workflow/

# Create workspace with subdirectories
RUN mkdir -p /workspace/inputs /workspace/outputs /workspace/scratch && \
    chown -R agentuser:agentuser /app /workspace
USER agentuser

WORKDIR /workspace

ENV PYTHONPATH=/app:/app/agents/workflow:/app/agents/workflow/src

CMD ["python", "-m", "src.runner"]
