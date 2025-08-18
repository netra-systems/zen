#!/bin/bash
# Netra AI Platform - Quick Start Development Script (macOS/Linux)
# This script starts both backend and frontend with optimal settings

echo ""
echo "==============================================="
echo "   Netra AI Development Environment"
echo "==============================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run: ./scripts/setup.sh"
    echo ""
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Start the dev launcher with optimal settings
echo ""
echo "Starting Backend and Frontend servers..."
echo "  - Dynamic port allocation (avoids conflicts)"
echo "  - No backend reload (30-50% faster)"
echo "  - Automatic secret loading"
echo ""

python scripts/dev_launcher.py --dynamic --no-backend-reload --load-secrets

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to start development environment"
    echo "Please check the error messages above"
    echo ""
fi