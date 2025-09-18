#!/bin/bash
# Build distribution packages for Zen Orchestrator

set -e  # Exit on error

echo "🔧 Building Zen Orchestrator distribution packages..."

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_DIR"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info

# Install/upgrade build tools
echo "📦 Installing build tools..."
pip install --upgrade build twine

# Build the package
echo "🏗️  Building package..."
python -m build

# Check the distribution
echo "🔍 Checking distribution..."
twine check dist/*

# Show package info
echo ""
echo "✅ Build complete!"
echo ""
echo "📦 Built packages:"
ls -lh dist/

echo ""
echo "📋 Package contents:"
tar -tzf dist/*.tar.gz | head -20
echo "... (showing first 20 files)"

echo ""
echo "🚀 Next steps:"
echo "  Test locally: pip install dist/*.whl"
echo "  Upload to TestPyPI: twine upload --repository testpypi dist/*"
echo "  Upload to PyPI: twine upload dist/*"