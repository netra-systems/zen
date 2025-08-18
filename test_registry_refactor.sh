#!/bin/bash

# Comprehensive Test Suite for Registry Refactoring
# Validates all functionality after modular split

set -e

echo "🧪 Running Comprehensive Registry Refactor Tests..."

# 1. Unit Tests - Fast feedback
echo "1️⃣ Running unit tests..."
python test_runner.py --level unit --no-coverage --fast-fail --frontend-only

# 2. Integration Tests - Core functionality
echo "2️⃣ Running integration tests..."
python test_runner.py --level integration --no-coverage --fast-fail

# 3. TypeScript specific tests
echo "3️⃣ Running TypeScript validation..."
cd frontend

# Type checking
npx tsc --noEmit --strict

# Test specific type imports
echo "  🔍 Testing individual module imports..."
node -e "
const { MessageType, AgentStatus } = require('./types/shared/enums');
const { Message, createMessage } = require('./types/domains/messages');
const { Thread, getThreadTitle } = require('./types/domains/threads');
const { WebSocketMessage } = require('./types/backend-sync/websockets');

console.log('✅ Individual module imports successful');

// Test registry aggregation
const registry = require('./types/registry');
const requiredTypes = [
  'MessageType', 'Message', 'Thread', 'WebSocketMessage',
  'createMessage', 'getThreadTitle', 'isWebSocketMessage'
];

const missing = requiredTypes.filter(type => !registry[type]);
if (missing.length > 0) {
  console.log('❌ Missing from registry:', missing);
  process.exit(1);
}

console.log('✅ Registry aggregation successful');
"

cd ..

# 4. Component-level tests (if components use types)
echo "4️⃣ Testing component compatibility..."
python test_runner.py --level comprehensive-frontend --no-coverage

# 5. WebSocket tests (critical for real-time functionality)
echo "5️⃣ Testing WebSocket integration..."
python test_runner.py --level comprehensive-websocket --no-coverage

# 6. Architecture compliance check
echo "6️⃣ Running architecture compliance..."
python scripts/check_architecture_compliance.py

# 7. Final smoke test
echo "7️⃣ Running smoke tests..."
python test_runner.py --level smoke

echo "🎉 All tests passed! Registry refactoring is safe to deploy."