#!/bin/bash

echo ""
echo "===================================================="
echo "   Netra AI Platform - macOS/Linux Quick Setup"
echo "===================================================="
echo ""
echo "This script will set up your complete development"
echo "environment automatically."
echo ""
echo "Prerequisites:"
echo "  - Python 3.9 or higher"
echo "  - Node.js 18 or higher"
echo "  - Git"
echo ""
echo "Press Enter to start setup, or Ctrl+C to cancel..."
read

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python from: https://www.python.org/downloads/"
    echo ""
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo ""
    echo "ERROR: Python $required_version or higher is required (found $python_version)"
    echo "Please upgrade Python from: https://www.python.org/downloads/"
    echo ""
    exit 1
fi

# Run the installer
echo ""
echo "Starting installation..."
echo ""
python3 scripts/install_dev_env.py

if [ $? -eq 0 ]; then
    echo ""
    echo "===================================================="
    echo "   Setup Complete!"
    echo "===================================================="
    echo ""
    echo "To start the development environment, run:"
    echo "   ./start_dev.sh"
    echo ""
    echo "Or manually:"
    echo "   python3 scripts/dev_launcher.py --dynamic"
    echo ""
else
    echo ""
    echo "===================================================="
    echo "   Setup Failed"
    echo "===================================================="
    echo ""
    echo "Please check the error messages above and try again."
    echo "For help, see README.md or CLAUDE.md"
    echo ""
fi