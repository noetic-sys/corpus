#!/usr/bin/env bash
# =============================================================================
# Fly.io Provisioning Script
# Creates all Corpus apps and sets secrets from .env.fly
#
# Usage:
#   bash scripts/provision-fly.sh              # Full provisioning
#   bash scripts/provision-fly.sh --dry-run    # Print what would happen
#   bash scripts/provision-fly.sh --secrets    # Only set secrets (apps exist)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.fly"
REGION="iad"
ORG="${FLY_ORG:-personal}"

DRY_RUN=false
SECRETS_ONLY=false

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
        --secrets) SECRETS_ONLY=true ;;
    esac
done

# -- Colors --
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; }

# -- App definitions --
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

# Per-app Temporal task queues (app_name:queue_name)
get_task_queue() {
    case "$1" in
        corpus-temporal-routing)   echo "document-routing-queue" ;;
        corpus-temporal-pdf)       echo "pdf-processing-queue" ;;
        corpus-temporal-page)      echo "page-processing-queue" ;;
        corpus-temporal-generic)   echo "generic-processing-queue" ;;
        corpus-temporal-chunking)  echo "chunking-queue" ;;
        corpus-temporal-workflow)  echo "workflow-execution-queue" ;;
        corpus-temporal-qa)        echo "qa-processing-queue" ;;
        *)                         echo "" ;;
    esac
}

# -- Preflight checks --
preflight() {
    if ! command -v fly &>/dev/null; then
        err "flyctl not installed. Install: curl -L https://fly.io/install.sh | sh"
        exit 1
    fi

    if ! fly auth whoami &>/dev/null; then
        err "Not logged in to Fly. Run: fly auth login"
        exit 1
    fi

    if [[ ! -f "$ENV_FILE" ]]; then
        err "Missing $ENV_FILE"
        echo ""
        echo "  cp scripts/.env.fly.template scripts/.env.fly"
        echo "  # Fill in your values, then re-run this script."
        echo ""
        exit 1
    fi

    ok "flyctl installed and authenticated"
    ok "Found $ENV_FILE"
}

# -- Parse .env.fly into secrets string --
parse_env_file() {
    local secrets=""
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip comments and blank lines
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        # Skip lines without =
        [[ "$line" != *"="* ]] && continue

        local key="${line%%=*}"
        local val="${line#*=}"

        # Skip empty values
        [[ -z "$val" ]] && continue

        secrets+="${key}=${val} "
    done < "$ENV_FILE"

    echo "$secrets"
}

# -- Create apps --
create_apps() {
    info "Creating ${#ALL_APPS[@]} Fly apps in region $REGION..."
    echo ""

    for app in "${ALL_APPS[@]}"; do
        if fly apps list --json 2>/dev/null | grep -q "\"$app\""; then
            ok "$app already exists"
        else
            if $DRY_RUN; then
                info "[DRY RUN] fly apps create $app --org $ORG"
            else
                fly apps create "$app" --org "$ORG" 2>/dev/null && ok "Created $app" || warn "$app may already exist"
            fi
        fi
    done
    echo ""
}

# -- Set shared secrets --
set_secrets() {
    local secrets
    secrets=$(parse_env_file)

    if [[ -z "$secrets" ]]; then
        err "No secrets parsed from $ENV_FILE — is it filled in?"
        exit 1
    fi

    # Count secrets
    local count
    count=$(echo "$secrets" | tr ' ' '\n' | grep -c '=' || true)
    info "Setting $count shared secrets across ${#ALL_APPS[@]} apps..."
    echo ""

    for app in "${ALL_APPS[@]}"; do
        # Build per-app secrets (shared + app-specific)
        local app_secrets="$secrets"

        # Add OTEL service name (same as app name)
        app_secrets+="OTEL_SERVICE_NAME=${app} "

        # Add Temporal task queue (only for temporal workers)
        local queue
        queue=$(get_task_queue "$app")
        if [[ -n "$queue" ]]; then
            app_secrets+="TEMPORAL_TASK_QUEUE=${queue} "
        fi

        # Add environment + execution mode
        app_secrets+="ENVIRONMENT=production "
        app_secrets+="WORKFLOW_EXECUTION_MODE=modal "

        # API endpoint for Fly internal networking
        app_secrets+="API_ENDPOINT=http://corpus-api.internal:8000 "

        if $DRY_RUN; then
            info "[DRY RUN] fly secrets set <${count}+ secrets> -a $app"
        else
            echo "$app_secrets" | xargs fly secrets set -a "$app" --stage 2>/dev/null \
                && ok "$app — secrets staged" \
                || warn "$app — failed to set secrets"
        fi
    done
    echo ""
}

# -- Deploy secrets (unstage) --
deploy_secrets() {
    info "Deploying staged secrets..."
    echo ""
    for app in "${ALL_APPS[@]}"; do
        if $DRY_RUN; then
            info "[DRY RUN] fly secrets deploy -a $app"
        else
            fly secrets deploy -a "$app" 2>/dev/null \
                && ok "$app — secrets deployed" \
                || warn "$app — no staged secrets or deploy failed (ok if app has no machines yet)"
        fi
    done
    echo ""
}

# -- Summary --
summary() {
    echo ""
    echo "============================================="
    echo -e "${GREEN} Provisioning complete!${NC}"
    echo "============================================="
    echo ""
    echo "Apps created:"
    for app in "${ALL_APPS[@]}"; do
        echo "  - $app"
    done
    echo ""
    echo "Next steps:"
    echo "  1. Verify:  fly apps list"
    echo "  2. Check:   fly secrets list -a corpus-api"
    echo "  3. Deploy:  git push (triggers .github/workflows/deploy-fly.yaml)"
    echo "     Or manually: fly deploy -a corpus-api --config fly-deploy/api.toml --image <image>"
    echo ""
    echo "External services checklist:"
    echo "  [ ] Neon Postgres — https://neon.tech"
    echo "  [ ] CloudAMQP     — https://www.cloudamqp.com"
    echo "  [ ] Cloudflare R2 — https://dash.cloudflare.com → R2"
    echo "  [ ] Turbopuffer   — https://turbopuffer.com"
    echo "  [ ] Temporal Cloud — https://cloud.temporal.io"
    echo "  [ ] Axiom         — https://axiom.co"
    echo "  [ ] Stripe        — https://dashboard.stripe.com"
    echo ""
}

# -- Main --
main() {
    echo ""
    echo "==========================================="
    echo "  Corpus — Fly.io Provisioning"
    echo "==========================================="
    echo ""

    if $DRY_RUN; then
        warn "DRY RUN MODE — no changes will be made"
        echo ""
    fi

    preflight

    if ! $SECRETS_ONLY; then
        create_apps
    fi

    set_secrets
    deploy_secrets
    summary
}

main
