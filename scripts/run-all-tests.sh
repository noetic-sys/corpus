#!/bin/bash

# Run all tests in the multi-project workspace
# This script runs tests in each project directory that contains them

# Don't exit on error - we want to run all tests and report at the end
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
echo "Running tests for all projects"
echo "=========================================="
echo ""

# Function to run tests in a directory
run_tests() {
    local project_name=$1
    local project_dir=$2
    local test_path=${3:-"tests"}  # Default to "tests" if not specified

    echo "----------------------------------------"
    echo "Testing: ${project_name}"
    echo "Directory: ${project_dir}"
    echo "Test path: ${test_path}"
    echo "----------------------------------------"

    if [ ! -d "${project_dir}" ]; then
        echo -e "${YELLOW}⚠ Directory not found, skipping${NC}"
        echo ""
        return
    fi

    cd "${project_dir}"

    # Check if test path exists
    if [ ! -d "${test_path}" ]; then
        echo -e "${YELLOW}⚠ Test path '${test_path}' not found, skipping${NC}"
        cd - > /dev/null
        echo ""
        return
    fi

    # Run tests with poetry (stream output directly)
    poetry run pytest -v "${test_path}"
    local exit_code=$?

    if [ ${exit_code} -eq 0 ]; then
        echo -e "${GREEN}✓ Tests passed for ${project_name}${NC}"
        PASSED_PROJECTS+=("${project_name}")
    else
        echo -e "${RED}✗ Tests failed for ${project_name}${NC}"
        FAILED_PROJECTS+=("${project_name}")
    fi

    cd - > /dev/null
    echo ""
}

# Store the root directory
ROOT_DIR=$(pwd)

# Test backend (only unit tests)
run_tests "Backend" "${ROOT_DIR}/backend" "tests/unit"

# Test workflow agent
run_tests "Workflow Agent" "${ROOT_DIR}/agents/workflow"

# Test QA agent
run_tests "QA Agent" "${ROOT_DIR}/agents/qa"

# Test chunking agent
run_tests "Chunking Agent" "${ROOT_DIR}/agents/chunking"

# Test shared libraries that have tests
for lib_dir in ${ROOT_DIR}/libs/*/; do
    if [ -d "${lib_dir}" ]; then
        lib_name=$(basename "${lib_dir}")
        run_tests "Library: ${lib_name}" "${lib_dir}"
    fi
done

# Print summary
echo "=========================================="
echo "Test Summary"
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
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
