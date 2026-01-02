#!/bin/bash

# Lock all Poetry packages in the project

set -e

echo "Locking backend..."
cd backend
poetry lock
cd ..

echo ""
echo "Locking libs packages..."
for dir in libs/*/; do
    if [ -f "$dir/pyproject.toml" ]; then
        echo "Locking $(basename $dir)..."
        cd "$dir"
        poetry lock
        cd ../..
    fi
done

echo ""
echo "Locking agent packages..."
for dir in agents/*/; do
    if [ -f "$dir/pyproject.toml" ]; then
        echo "Locking $(basename $dir)..."
        cd "$dir"
        poetry lock
        cd ../..
    fi
done

echo ""
echo "✓ All packages locked"
