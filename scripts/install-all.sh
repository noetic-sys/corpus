#!/bin/bash

# Install dependencies for all projects in the multi-project workspace
# This script runs poetry install in each project directory

# Don't exit on error - we want to run all installs and report at the end
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
echo "Installing dependencies for all projects"
echo "=========================================="
echo ""

# Function to install dependencies in a directory
install_dependencies() {
    local project_name=$1
    local project_dir=$2

    echo "----------------------------------------"
    echo "Installing: ${project_name}"
    echo "Directory: ${project_dir}"
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

    # Run poetry install (try without lock first, then with lock if needed)
    poetry install
    local exit_code=$?

    # If install failed, try running poetry lock first
    if [ ${exit_code} -ne 0 ]; then
        echo -e "${YELLOW}⚠ Install failed, trying to update lock file...${NC}"
        poetry lock
        local lock_exit=$?

        if [ ${lock_exit} -eq 0 ]; then
            echo -e "${YELLOW}⚠ Lock file updated, retrying install...${NC}"
            poetry install
            exit_code=$?
        fi
    fi

    if [ ${exit_code} -eq 0 ]; then
        echo -e "${GREEN}✓ Dependencies installed for ${project_name}${NC}"
        PASSED_PROJECTS+=("${project_name}")
    else
        echo -e "${RED}✗ Installation failed for ${project_name}${NC}"
        FAILED_PROJECTS+=("${project_name}")
    fi

    cd - > /dev/null
    echo ""
}

# Store the root directory
ROOT_DIR=$(pwd)

# Install backend
install_dependencies "Backend" "${ROOT_DIR}/backend"

# Install agents
install_dependencies "Workflow Agent" "${ROOT_DIR}/agents/workflow"
install_dependencies "QA Agent" "${ROOT_DIR}/agents/qa"
install_dependencies "Chunking Agent" "${ROOT_DIR}/agents/chunking"

# Install shared libraries
for lib_dir in ${ROOT_DIR}/libs/*/; do
    if [ -d "${lib_dir}" ]; then
        lib_name=$(basename "${lib_dir}")
        install_dependencies "Library: ${lib_name}" "${lib_dir}"
    fi
done

# Print summary
echo "=========================================="
echo "Installation Summary"
echo "=========================================="
echo ""

if [ ${#PASSED_PROJECTS[@]} -gt 0 ]; then
    echo -e "${GREEN}Successful installations (${#PASSED_PROJECTS[@]}):${NC}"
    for project in "${PASSED_PROJECTS[@]}"; do
        echo -e "  ${GREEN}✓${NC} ${project}"
    done
    echo ""
fi

if [ ${#FAILED_PROJECTS[@]} -gt 0 ]; then
    echo -e "${RED}Failed installations (${#FAILED_PROJECTS[@]}):${NC}"
    for project in "${FAILED_PROJECTS[@]}"; do
        echo -e "  ${RED}✗${NC} ${project}"
    done
    echo ""
    echo -e "${RED}Some installations failed!${NC}"
    exit 1
else
    echo -e "${GREEN}All dependencies installed successfully!${NC}"
    exit 0
fi
