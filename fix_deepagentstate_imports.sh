#!/bin/bash

# Comprehensive DeepAgentState SSOT Migration Script
# Purpose: Complete remaining 112 imports to maximize 136% test collection improvement

echo "🚀 Starting comprehensive DeepAgentState SSOT migration..."

# Count files before fix
BEFORE_COUNT=$(find tests -name "*.py" -type f -exec grep -l "from netra_backend.app.agents.state" {} \; | wc -l | tr -d ' ')
echo "📊 Found $BEFORE_COUNT files with deprecated imports"

# Create backup of critical files
echo "💾 Creating backup directory..."
mkdir -p /tmp/deepagentstate_backup_$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/deepagentstate_backup_$(date +%Y%m%d_%H%M%S)"

# Get list of files to fix
FILES_TO_FIX=$(find tests -name "*.py" -type f -exec grep -l "from netra_backend.app.agents.state" {} \;)

# Count files to process
FILE_COUNT=$(echo "$FILES_TO_FIX" | wc -l | tr -d ' ')
echo "📝 Processing $FILE_COUNT files..."

# Process each file
FIXED_COUNT=0
SKIPPED_COUNT=0

for file in $FILES_TO_FIX; do
    echo "Processing: $file"
    
    # Create backup
    cp "$file" "$BACKUP_DIR/$(basename "$file").bak"
    
    # Apply comprehensive fixes
    
    # 1. Standard import pattern
    sed -i 's|from netra_backend\.app\.agents\.state import DeepAgentState|from netra_backend.app.schemas.agent_models import DeepAgentState|g' "$file"
    
    # 2. Multi-line import patterns 
    sed -i 's|from netra_backend\.app\.agents\.state import (|from netra_backend.app.schemas.agent_models import (|g' "$file"
    sed -i 's|from netra_backend\.app\.agents\.state import|from netra_backend.app.schemas.agent_models import|g' "$file"
    
    # 3. Aliased imports
    sed -i 's|from netra_backend\.app\.agents\.state import DeepAgentState as|from netra_backend.app.schemas.agent_models import DeepAgentState as|g' "$file"
    
    # 4. Mixed imports with other classes
    sed -i 's|from netra_backend\.app\.agents\.state import DeepAgentState,|from netra_backend.app.schemas.agent_models import DeepAgentState,|g' "$file"
    
    # 5. String literals in test files (for test verification)
    sed -i 's|"from netra_backend\.app\.agents\.state import DeepAgentState"|"from netra_backend.app.schemas.agent_models import DeepAgentState"|g' "$file"
    sed -i "s|'from netra_backend\.app\.agents\.state import DeepAgentState'|'from netra_backend.app.schemas.agent_models import DeepAgentState'|g" "$file"
    
    # Check if any changes were made
    if ! diff -q "$BACKUP_DIR/$(basename "$file").bak" "$file" > /dev/null; then
        FIXED_COUNT=$((FIXED_COUNT + 1))
        echo "✅ Fixed: $file"
    else
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        echo "⚠️  No changes: $file"
    fi
done

# Count files after fix
AFTER_COUNT=$(find tests -name "*.py" -type f -exec grep -l "from netra_backend.app.agents.state" {} \; | wc -l | tr -d ' ')

echo ""
echo "📊 MIGRATION SUMMARY:"
echo "   Files before: $BEFORE_COUNT"
echo "   Files after:  $AFTER_COUNT"
echo "   Files fixed:  $FIXED_COUNT"
echo "   Files skipped: $SKIPPED_COUNT"
echo "   Reduction:    $((BEFORE_COUNT - AFTER_COUNT)) files"
echo ""

if [ $AFTER_COUNT -eq 0 ]; then
    echo "🎉 SUCCESS: All deprecated imports eliminated!"
    echo "💾 Backups saved in: $BACKUP_DIR"
else
    echo "⚠️  $AFTER_COUNT files still have deprecated imports"
    echo "🔍 Remaining files:"
    find tests -name "*.py" -type f -exec grep -l "from netra_backend.app.agents.state" {} \;
fi

echo ""
echo "✅ Migration script complete"