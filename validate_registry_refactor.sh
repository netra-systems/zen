#!/bin/bash

# Registry Refactor Validation Script
# Ensures zero breaking changes during modularization

set -e

echo "🔍 Validating Type Registry Refactoring..."

# 1. TypeScript compilation check
echo "📦 Running TypeScript compilation check..."
cd frontend
npx tsc --noEmit --project tsconfig.json
if [ $? -eq 0 ]; then
    echo "✅ TypeScript compilation successful"
else
    echo "❌ TypeScript compilation failed"
    exit 1
fi

# 2. Check for module resolution
echo "🔗 Checking module resolution..."
node -e "
try {
  const registry = require('./types/registry_modular.ts');
  console.log('✅ Module imports successful');
  
  // Check key exports exist
  const requiredExports = [
    'MessageType', 'AgentStatus', 'WebSocketMessageType',
    'User', 'Message', 'ChatMessage', 'Thread', 'WebSocketMessage',
    'createMessage', 'getThreadTitle', 'isWebSocketMessage'
  ];
  
  const missing = requiredExports.filter(exp => !registry[exp]);
  if (missing.length > 0) {
    console.log('❌ Missing exports:', missing);
    process.exit(1);
  }
  
  console.log('✅ All required exports present');
} catch (error) {
  console.log('❌ Module resolution failed:', error.message);
  process.exit(1);
}
"

# 3. Check file sizes
echo "📏 Checking file size compliance (≤300 lines)..."
find types -name "*.ts" -exec wc -l {} \; | while read lines file; do
    if [ "$lines" -gt 300 ]; then
        echo "❌ File $file has $lines lines (exceeds 300 line limit)"
        exit 1
    else
        echo "✅ $file: $lines lines (within limit)"
    fi
done

# 4. Check for circular dependencies
echo "🔄 Checking for circular dependencies..."
npx madge --circular types/
if [ $? -eq 0 ]; then
    echo "✅ No circular dependencies found"
else
    echo "❌ Circular dependencies detected"
    exit 1
fi

# 5. Test import patterns
echo "🧪 Testing common import patterns..."
node -e "
// Test individual imports
const { MessageType } = require('./types/shared/enums.ts');
const { Message } = require('./types/domains/messages.ts');
const { Thread } = require('./types/domains/threads.ts');
const { WebSocketMessage } = require('./types/backend-sync/websockets.ts');

// Test registry re-exports
const registry = require('./types/registry_modular.ts');
if (!registry.MessageType || !registry.Message || !registry.Thread) {
  console.log('❌ Registry re-exports failed');
  process.exit(1);
}

console.log('✅ All import patterns working');
"

echo "🎉 Validation complete - Ready for safe deployment!"