#!/bin/bash
# Critical Unified Tests Runner - Unix Shell Script
#
# This script runs the 10 critical unified tests with proper error handling
# and service management for Unix-like environments.

set -e  # Exit on any error

echo "================================================================================"
echo "CRITICAL UNIFIED TESTS RUNNER"
echo "================================================================================"
echo

# Change to project root directory
cd "$(dirname "$0")"

# Set environment variables
export NETRA_ENV=test
export LOG_LEVEL=INFO
export PYTHONPATH="$(pwd)"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python is not available in PATH"
        exit 1
    else
        PYTHON_CMD=python
    fi
else
    PYTHON_CMD=python3
fi

echo "Using Python: $PYTHON_CMD"

# Check if pytest is available
if ! $PYTHON_CMD -m pytest --version &> /dev/null; then
    echo "ERROR: pytest is not available. Please install it with: pip install pytest"
    exit 1
fi

# Run the critical tests runner
echo "Running 10 critical unified tests..."
echo

$PYTHON_CMD tests/unified/e2e/run_critical_unified_tests.py "$@"

# Capture exit code
TEST_EXIT_CODE=$?

echo
echo "================================================================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "ALL TESTS PASSED - System ready for production"
else
    echo "TESTS FAILED - Review results and fix issues before deployment"
fi
echo "================================================================================"

exit $TEST_EXIT_CODE