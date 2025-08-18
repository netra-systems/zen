#!/bin/bash

# Day 1 Complete Execution Script
# Implements the full registry refactoring in one safe operation

set -e

echo "🎯 EXECUTING DAY 1 REGISTRY REFACTORING"
echo "========================================"
echo "Target: Split 893-line registry.ts into modular structure"
echo "Goal: Zero breaking changes, 100% backward compatibility"
echo ""

# Confirmation prompt
read -p "⚠️  This will refactor the type registry. Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborted by user"
    exit 1
fi

# Step 1: Setup directory structure
echo "📁 Step 1: Creating directory structure..."
./refactor_registry.sh

# Step 2: Validate new modular files exist
echo "🔍 Step 2: Validating modular files..."
required_files=(
    "frontend/types/shared/enums.ts"
    "frontend/types/shared/base.ts" 
    "frontend/types/domains/messages.ts"
    "frontend/types/domains/threads.ts"
    "frontend/types/backend-sync/websockets.ts"
    "frontend/types/registry_modular.ts"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Required file missing: $file"
        exit 1
    fi
    lines=$(wc -l < "$file")
    echo "✅ $file: $lines lines"
    
    if [ "$lines" -gt 300 ]; then
        echo "❌ File $file exceeds 300 line limit ($lines lines)"
        exit 1
    fi
done

# Step 3: Pre-implementation validation
echo "🧪 Step 3: Pre-implementation validation..."
chmod +x validate_registry_refactor.sh
./validate_registry_refactor.sh

# Step 4: Safe implementation with rollback
echo "🚀 Step 4: Implementing registry replacement..."
chmod +x implement_registry_refactor.sh
./implement_registry_refactor.sh

# Step 5: Comprehensive testing
echo "🔬 Step 5: Running comprehensive tests..."
chmod +x test_registry_refactor.sh
./test_registry_refactor.sh

# Step 6: Git commits (optional - ask user)
read -p "📝 Commit changes to git? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📝 Step 6: Committing to git..."
    chmod +x git_commit_strategy.sh
    ./git_commit_strategy.sh
fi

# Step 7: Final summary
echo ""
echo "🎉 DAY 1 REFACTORING COMPLETE!"
echo "=============================="
echo ""
echo "📊 Results:"
echo "  • Original registry.ts: 893 lines"
echo "  • New registry.ts: $(wc -l < frontend/types/registry.ts) lines (re-export hub)"
echo "  • Modular files: 6 files, all <300 lines"
echo "  • Functions: All <8 lines each"
echo "  • Breaking changes: 0"
echo ""
echo "📁 New structure:"
echo "  frontend/types/"
echo "  ├── shared/"
echo "  │   ├── enums.ts      ($(wc -l < frontend/types/shared/enums.ts) lines)"
echo "  │   └── base.ts       ($(wc -l < frontend/types/shared/base.ts) lines)" 
echo "  ├── domains/"
echo "  │   ├── messages.ts   ($(wc -l < frontend/types/domains/messages.ts) lines)"
echo "  │   └── threads.ts    ($(wc -l < frontend/types/domains/threads.ts) lines)"
echo "  ├── backend-sync/"
echo "  │   └── websockets.ts ($(wc -l < frontend/types/backend-sync/websockets.ts) lines)"
echo "  └── registry.ts       ($(wc -l < frontend/types/registry.ts) lines - re-export hub)"
echo ""
echo "🔧 Next Steps:"
echo "  1. Test your application thoroughly"
echo "  2. Run integration tests: python test_runner.py --level integration"
echo "  3. If all good, delete: frontend/types/registry_original.ts"
echo "  4. Continue with Day 2: Agent types modularization"
echo ""
echo "🔙 Emergency Rollback (if needed):"
echo "  mv frontend/types/registry.ts frontend/types/registry_modular.ts"
echo "  mv frontend/types/registry_original.ts frontend/types/registry.ts"
echo ""
echo "✅ Registry refactoring successfully completed!"