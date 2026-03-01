#!/usr/bin/env bash
# =============================================================================
# Fly.io Teardown Script
# Destroys all Corpus Fly apps. USE WITH CAUTION.
#
# Usage:
#   bash scripts/teardown-fly.sh              # Interactive (confirms each app)
#   bash scripts/teardown-fly.sh --force      # Destroy all without prompting
# =============================================================================
set -euo pipefail

FORCE=false
for arg in "$@"; do
    case $arg in
        --force) FORCE=true ;;
    esac
done

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

ALL_APPS=(
    corpus-api
    corpus-agent
    corpus-worker-qa
    corpus-worker-document-indexing
    corpus-temporal-routing
    corpus-temporal-pdf
    corpus-temporal-page
    corpus-temporal-generic
    corpus-temporal-chunking
    corpus-temporal-workflow
    corpus-temporal-qa
)

echo ""
echo -e "${RED}==========================================="
echo "  Corpus — Fly.io TEARDOWN"
echo -e "===========================================${NC}"
echo ""
echo "This will DESTROY the following apps:"
for app in "${ALL_APPS[@]}"; do
    echo "  - $app"
done
echo ""

if ! $FORCE; then
    read -rp "Type 'destroy' to confirm: " confirm
    if [[ "$confirm" != "destroy" ]]; then
        echo "Aborted."
        exit 0
    fi
fi

for app in "${ALL_APPS[@]}"; do
    if fly apps list --json 2>/dev/null | grep -q "\"$app\""; then
        fly apps destroy "$app" --yes 2>/dev/null \
            && echo -e "${GREEN}[OK]${NC} Destroyed $app" \
            || echo -e "${YELLOW}[WARN]${NC} Failed to destroy $app"
    else
        echo -e "${YELLOW}[SKIP]${NC} $app does not exist"
    fi
done

echo ""
echo -e "${GREEN}Teardown complete.${NC}"
