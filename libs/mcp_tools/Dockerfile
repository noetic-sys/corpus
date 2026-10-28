FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CORPUS_API_ENDPOINT=http://backend:8000 \
    CORPUS_MCP_HOST=0.0.0.0 \
    CORPUS_MCP_PORT=8100 \
    CORPUS_MCP_PATH=/mcp

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install poetry==2.0.1 \
    && poetry config virtualenvs.create false

COPY libs/mcp_tools/pyproject.toml libs/mcp_tools/poetry.lock libs/mcp_tools/README.md /app/
COPY libs/mcp_tools/mcp_tools /app/mcp_tools

RUN poetry install --no-interaction --no-ansi

EXPOSE 8100

CMD ["corpus-mcp", "--host", "0.0.0.0", "--port", "8100", "--path", "/mcp"]
