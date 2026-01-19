#!/bin/bash

set -e
set -x

echo "Generating API clients..."

# Change to the backend directory
cd backend

# Create specs directory in vite
mkdir -p ../vite/specs

# Generate API service OpenAPI spec
poetry run python -c "
import sys
import io
import json

old_stdout = sys.stdout
sys.stdout = io.StringIO()

sys.path.append('.')
from apps.api.main import app

sys.stdout = old_stdout
print(json.dumps(app.openapi(), indent=2))
" > ../vite/specs/api.openapi.json

echo "Generated API OpenAPI specification"

# Generate Agent service OpenAPI spec
poetry run python -c "
import sys
import io
import json

old_stdout = sys.stdout
sys.stdout = io.StringIO()

sys.path.append('.')
from apps.agent.main import app

sys.stdout = old_stdout
print(json.dumps(app.openapi(), indent=2))
" > ../vite/specs/agent.openapi.json

echo "Generated Agent OpenAPI specification"

# Copy combined spec to libs/mcp_tools for agent builds (use API spec for now)
cp ../vite/specs/api.openapi.json ../libs/mcp_tools/mcp_tools/openapi.json

echo "Copied OpenAPI spec to libs/mcp_tools/mcp_tools for agents"

# Change to the frontend directory
cd ../vite

# Generate both TypeScript clients
npm run generate-client:api
npm run generate-client:agent

echo "Generated TypeScript API clients"

# Format the generated code (if prettier is available)
if command -v npx &> /dev/null; then
    if npm list --depth=0 prettier &> /dev/null; then
        echo "Formatting generated client code..."
        npx prettier --write src/client/
        echo "Formatted generated client code"
    fi
fi

echo "API client generation completed successfully!"
echo "Generated client files are available in vite/src/client/api/ and vite/src/client/agent/"