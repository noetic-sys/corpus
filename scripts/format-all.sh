#!/bin/bash

# Run formatting checks for all projects in the multi-project workspace
# This script runs nox -s format in each project directory

# Don't exit on error - we want to run all checks and report at the end
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
echo "Running format checks for all projects"
echo "=========================================="
echo ""

# Function to run format check in a directory
run_format_check() {
    local project_name=$1
    local project_dir=$2

    echo "----------------------------------------"
    echo "Format check: ${project_name}"
    echo "Directory: ${project_dir}"
    echo "----------------------------------------"

    if [ ! -d "${project_dir}" ]; then
        echo -e "${YELLOW}⚠ Directory not found, skipping${NC}"
        echo ""
        return
    fi

    cd "${project_dir}"

    # Check if noxfile.py exists
    if [ ! -f "noxfile.py" ]; then
        echo -e "${YELLOW}⚠ No noxfile.py found, skipping${NC}"
        cd - > /dev/null
        echo ""
        return
    fi

    # Run nox format session via poetry
    poetry run nox -s format
    local exit_code=$?

    if [ ${exit_code} -eq 0 ]; then
        echo -e "${GREEN}✓ Format check passed for ${project_name}${NC}"
        PASSED_PROJECTS+=("${project_name}")
    else
        echo -e "${RED}✗ Format check failed for ${project_name}${NC}"
        FAILED_PROJECTS+=("${project_name}")
    fi

    cd - > /dev/null
    echo ""
}

# Store the root directory
ROOT_DIR=$(pwd)

# Check backend
run_format_check "Backend" "${ROOT_DIR}/backend"

# Check agents
run_format_check "Workflow Agent" "${ROOT_DIR}/agents/workflow"
run_format_check "QA Agent" "${ROOT_DIR}/agents/qa"
run_format_check "Chunking Agent" "${ROOT_DIR}/agents/chunking"

# Check shared libraries
for lib_dir in ${ROOT_DIR}/libs/*/; do
    if [ -d "${lib_dir}" ]; then
        lib_name=$(basename "${lib_dir}")
        run_format_check "Library: ${lib_name}" "${lib_dir}"
    fi
done

# Print summary
echo "=========================================="
echo "Format Check Summary"
echo "=========================================="
echo ""

if [ ${#PASSED_PROJECTS[@]} -gt 0 ]; then
    echo -e "${GREEN}Passed projects (${#PASSED_PROJECTS[@]}):${NC}"
    for project in "${PASSED_PROJECTS[@]}"; do
        echo -e "  ${GREEN}✓${NC} ${project}"
    done
    echo ""
fi

if [ ${#FAILED_PROJECTS[@]} -gt 0 ]; then
    echo -e "${RED}Failed projects (${#FAILED_PROJECTS[@]}):${NC}"
    for project in "${FAILED_PROJECTS[@]}"; do
        echo -e "  ${RED}✗${NC} ${project}"
    done
    echo ""
    echo -e "${RED}Some format checks failed!${NC}"
    exit 1
else
    echo -e "${GREEN}All format checks passed!${NC}"
    exit 0
fi
