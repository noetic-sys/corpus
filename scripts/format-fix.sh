#!/bin/bash

# Auto-fix formatting issues for all projects in the multi-project workspace
# This script runs black and ruff --fix in each project directory

# Don't exit on error - we want to run all fixes and report at the end
set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall results
FAILED_PROJECTS=()
PASSED_PROJECTS=()

echo "=========================================="
echo "Auto-fixing formatting for all projects"
echo "=========================================="
echo ""

# Function to auto-fix formatting in a directory
fix_formatting() {
    local project_name=$1
    local project_dir=$2
    local target_dirs=$3  # Directories to format (e.g., "src" or "api common packages workers")

    echo "----------------------------------------"
    echo "Fixing: ${project_name}"
    echo "Directory: ${project_dir}"
    echo "Target: ${target_dirs}"
    echo "----------------------------------------"

    if [ ! -d "${project_dir}" ]; then
        echo -e "${YELLOW}⚠ Directory not found, skipping${NC}"
        echo ""
        return
    fi

    cd "${project_dir}"

    # Check if pyproject.toml exists
    if [ ! -f "pyproject.toml" ]; then
        echo -e "${YELLOW}⚠ No pyproject.toml found, skipping${NC}"
        cd - > /dev/null
        echo ""
        return
    fi

    local all_success=true

    # Run black (auto-fix)
    echo "Running black..."
    poetry run black ${target_dirs}
    if [ $? -ne 0 ]; then
        all_success=false
    fi

    # Run ruff check --fix (auto-fix)
    echo "Running ruff check --fix..."
    poetry run ruff check --fix .
    if [ $? -ne 0 ]; then
        all_success=false
    fi

    if [ "$all_success" = true ]; then
        echo -e "${GREEN}✓ Formatting fixed for ${project_name}${NC}"
        PASSED_PROJECTS+=("${project_name}")
    else
        echo -e "${RED}✗ Formatting fix failed for ${project_name}${NC}"
        FAILED_PROJECTS+=("${project_name}")
    fi

    cd - > /dev/null
    echo ""
}

# Store the root directory
ROOT_DIR=$(pwd)

# Fix backend
fix_formatting "Backend" "${ROOT_DIR}/backend" "api common packages workers"

# Fix agents (they use src/)
fix_formatting "Workflow Agent" "${ROOT_DIR}/agents/workflow" "src"
fix_formatting "QA Agent" "${ROOT_DIR}/agents/qa" "src"
fix_formatting "Chunking Agent" "${ROOT_DIR}/agents/chunking" "src"

# Fix shared libraries (they use their own directory name)
fix_formatting "Library: ai_config" "${ROOT_DIR}/libs/ai_config" "ai_config"
fix_formatting "Library: documents" "${ROOT_DIR}/libs/documents" "documents"
fix_formatting "Library: matrices" "${ROOT_DIR}/libs/matrices" "matrices"
fix_formatting "Library: mcp_tools" "${ROOT_DIR}/libs/mcp_tools" "mcp_tools"
fix_formatting "Library: qa" "${ROOT_DIR}/libs/qa" "qa"
fix_formatting "Library: questions" "${ROOT_DIR}/libs/questions" "questions"
fix_formatting "Library: workflows" "${ROOT_DIR}/libs/workflows" "workflows"

# Print summary
echo "=========================================="
echo "Format Fix Summary"
echo "=========================================="
echo ""

if [ ${#PASSED_PROJECTS[@]} -gt 0 ]; then
    echo -e "${GREEN}Successfully fixed (${#PASSED_PROJECTS[@]}):${NC}"
    for project in "${PASSED_PROJECTS[@]}"; do
        echo -e "  ${GREEN}✓${NC} ${project}"
    done
    echo ""
fi

if [ ${#FAILED_PROJECTS[@]} -gt 0 ]; then
    echo -e "${RED}Failed to fix (${#FAILED_PROJECTS[@]}):${NC}"
    for project in "${FAILED_PROJECTS[@]}"; do
        echo -e "  ${RED}✗${NC} ${project}"
    done
    echo ""
    echo -e "${RED}Some formatting fixes failed!${NC}"
    exit 1
else
    echo -e "${GREEN}All formatting fixed successfully!${NC}"
    exit 0
fi
