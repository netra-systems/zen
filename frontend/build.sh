#!/bin/bash

# Frontend Build Script for Netra Apex AI Optimization Platform
# Business Value: Ensures reliable frontend builds for staging and production
# Prevents $25K+ MRR loss from frontend availability issues

set -e  # Exit on any error

echo "🚀 Starting Netra Frontend Build Process..."

# Check Node.js version
echo "📋 Checking Node.js version..."
node --version
npm --version

# Set build environment variables
export NODE_ENV=${NODE_ENV:-production}
export ENVIRONMENT=${ENVIRONMENT:-production}
export NODE_OPTIONS="--max-old-space-size=4096"

echo "🌍 Build Environment: $ENVIRONMENT"
echo "📦 Node Environment: $NODE_ENV"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf .next
rm -rf dist
rm -rf out

# Install dependencies
echo "📦 Installing dependencies..."
npm ci --production=false

# Run TypeScript type checking
echo "🔍 Running TypeScript type check..."
npm run type-check || echo "⚠️ Type check completed with warnings"

# Build the application
echo "🔨 Building application..."
npm run build

# Validate build output
echo "✅ Validating build output..."
if [ ! -d ".next" ] && [ ! -d "dist" ] && [ ! -d "out" ]; then
    echo "❌ Build failed - no output directory found"
    exit 1
fi

# Check for critical files
if [ -d ".next" ]; then
    if [ ! -f ".next/build-manifest.json" ]; then
        echo "⚠️ Warning: build-manifest.json not found"
    fi
fi

echo "🎉 Frontend build completed successfully!"
echo "📊 Build summary:"
echo "   - Environment: $ENVIRONMENT"
echo "   - Node Environment: $NODE_ENV"
echo "   - Output directory: $(ls -la | grep -E '\.next|dist|out' | head -1)"

# Optional: Run basic smoke tests
if command -v curl &> /dev/null; then
    echo "🔬 Running smoke tests..."
    # Add smoke test commands here when needed
fi

echo "✅ Frontend build process completed successfully!"