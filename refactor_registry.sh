#!/bin/bash

# Type Registry Refactoring Script - Day 1 Implementation
# Creates modular structure for 893-line registry.ts

set -e  # Exit on any error

echo "🔄 Starting Type Registry Refactoring..."

# 1. Create directory structure
echo "📁 Creating directory structure..."
mkdir -p frontend/types/domains
mkdir -p frontend/types/shared
mkdir -p frontend/types/backend-sync

# 2. Backup original registry
echo "💾 Creating backup..."
cp frontend/types/registry.ts frontend/types/registry.ts.backup

# 3. Verify directory structure
echo "✅ Directory structure created:"
ls -la frontend/types/
ls -la frontend/types/domains/
ls -la frontend/types/shared/
ls -la frontend/types/backend-sync/

echo "🎯 Directory setup complete. Ready for module extraction."