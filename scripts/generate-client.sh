#!/bin/bash

set -e
set -x

echo "Generating API client..."

# Change to the backend directory
cd backend

# Generate OpenAPI JSON by importing the FastAPI app and extracting its OpenAPI spec
poetry run python -c "
import json
import sys
sys.path.append('.')
from api.main import app
print(json.dumps(app.openapi(), indent=2))
" > openapi.json

echo "Generated OpenAPI specification"

# Move the OpenAPI JSON to the frontend directory
mv openapi.json ../vite/

echo "Moved OpenAPI spec to frontend directory"

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