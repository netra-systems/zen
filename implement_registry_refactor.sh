#!/bin/bash

# Registry Refactor Implementation Script
# Safely replaces monolithic registry with modular structure

set -e

echo "🚀 Implementing Type Registry Refactoring..."

# Store current directory
ORIGINAL_DIR=$(pwd)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Safety checks
if [ ! -f "frontend/types/registry.ts" ]; then
    echo "❌ Original registry.ts not found"
    exit 1
fi

if [ ! -f "frontend/types/registry_modular.ts" ]; then
    echo "❌ Modular registry not found"
    exit 1
fi

# 1. Create comprehensive backup
echo "💾 Creating comprehensive backup..."
mkdir -p "backups/registry_refactor_${TIMESTAMP}"
cp -r frontend/types "backups/registry_refactor_${TIMESTAMP}/"
echo "✅ Backup created at backups/registry_refactor_${TIMESTAMP}/"

# 2. Run validation
echo "🔍 Running validation checks..."
chmod +x validate_registry_refactor.sh
if ! ./validate_registry_refactor.sh; then
    echo "❌ Validation failed - aborting implementation"
    exit 1
fi

# 3. Replace registry.ts with modular version
echo "🔄 Replacing registry.ts with modular version..."
mv frontend/types/registry.ts frontend/types/registry_original.ts
mv frontend/types/registry_modular.ts frontend/types/registry.ts

# 4. Run tests to ensure no breaking changes
echo "🧪 Running tests to verify no breaking changes..."
cd frontend

# TypeScript compilation test
echo "  📦 TypeScript compilation..."
if ! npx tsc --noEmit --project tsconfig.json; then
    echo "❌ TypeScript compilation failed - rolling back"
    cd "$ORIGINAL_DIR"
    mv frontend/types/registry.ts frontend/types/registry_modular.ts
    mv frontend/types/registry_original.ts frontend/types/registry.ts
    exit 1
fi

# Test imports work
echo "  🔗 Testing imports..."
if ! node -e "
const registry = require('./types/registry.ts');
console.log('Import test passed:', Object.keys(registry).slice(0, 5));
"; then
    echo "❌ Import test failed - rolling back"
    cd "$ORIGINAL_DIR"
    mv frontend/types/registry.ts frontend/types/registry_modular.ts
    mv frontend/types/registry_original.ts frontend/types/registry.ts
    exit 1
fi

cd "$ORIGINAL_DIR"

# 5. Update import statements across codebase (if needed)
echo "🔧 Checking for import updates needed..."
# Most imports should still work due to re-exports, but check for any edge cases
grep -r "from.*registry" frontend/components/ frontend/services/ frontend/hooks/ || echo "No additional imports to update"

# 6. Final validation
echo "✅ Running final validation..."
if ! ./validate_registry_refactor.sh; then
    echo "❌ Final validation failed - rolling back"
    mv frontend/types/registry.ts frontend/types/registry_modular.ts
    mv frontend/types/registry_original.ts frontend/types/registry.ts
    exit 1
fi

# 7. Success - clean up
echo "🎉 Refactoring successful!"
echo "📊 File size reduction:"
echo "  Original registry.ts: $(wc -l < frontend/types/registry_original.ts) lines"
echo "  New registry.ts: $(wc -l < frontend/types/registry.ts) lines"
echo "  Modular files:"
find frontend/types -name "*.ts" -not -name "registry_original.ts" -exec wc -l {} \;

echo ""
echo "📁 New structure:"
tree frontend/types/ || ls -la frontend/types/

echo ""
echo "🔄 Next steps:"
echo "1. Test your application thoroughly"
echo "2. Run: python test_runner.py --level integration --no-coverage --fast-fail"
echo "3. If everything works, delete: frontend/types/registry_original.ts"
echo "4. Commit changes with: git add frontend/types && git commit -m 'Refactor: Split 893-line registry into modular structure'"

echo ""
echo "🔙 Rollback command (if needed):"
echo "mv frontend/types/registry.ts frontend/types/registry_modular.ts && mv frontend/types/registry_original.ts frontend/types/registry.ts"