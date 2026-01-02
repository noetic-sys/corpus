#!/bin/bash

set -e
set -x

echo "Generating API client..."

# Change to the backend directory
cd backend

# Generate OpenAPI JSON by importing the FastAPI app and extracting its OpenAPI spec
# Suppress stdout during import to avoid telemetry/logging messages in output
poetry run python -c "
import sys
import io
import json

# Capture stdout during import
old_stdout = sys.stdout
sys.stdout = io.StringIO()

sys.path.append('.')
from api.main import app

# Restore stdout and print only the JSON
sys.stdout = old_stdout
print(json.dumps(app.openapi(), indent=2))
" > openapi.json

echo "Generated OpenAPI specification"

# Copy the OpenAPI JSON to the frontend directory
cp openapi.json ../vite/

echo "Copied OpenAPI spec to frontend directory"

# Copy the OpenAPI JSON to libs/mcp_tools/mcp_tools for agent builds
cp openapi.json ../libs/mcp_tools/mcp_tools/

echo "Copied OpenAPI spec to libs/mcp_tools/mcp_tools for agents"

# Clean up
rm openapi.json

# Change to the frontend directory (from backend, go back to root then to vite)
cd ../vite

# Generate the TypeScript client
npm run generate-client

echo "Generated TypeScript API client"

# Format the generated code (if prettier is available)
if command -v npx &> /dev/null; then
    if npm list --depth=0 prettier &> /dev/null; then
        echo "Formatting generated client code..."
        npx prettier --write srcclient/
        echo "Formatted generated client code"
    fi
fi

echo "API client generation completed successfully!"
echo "Generated client files are available in vite/src/client/"