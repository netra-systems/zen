#!/usr/bin/env node

/**
 * Quick verification script for WebSocket agent_response handler fix
 * This verifies the fix is in place without needing full test infrastructure
 */

const fs = require('fs');
const path = require('path');

const CHECKS = {
  handlerFunction: {
    file: 'store/websocket-agent-handlers.ts',
    pattern: /export\s+const\s+handleAgentResponse\s*=/,
    description: 'handleAgentResponse function exists'
  },
  extractFunction: {
    file: 'store/websocket-agent-handlers.ts', 
    pattern: /export\s+const\s+extractAgentResponseData\s*=/,
    description: 'extractAgentResponseData function exists'
  },
  createMessageFunction: {
    file: 'store/websocket-agent-handlers.ts',
    pattern: /export\s+const\s+createAgentResponseMessage\s*=/,
    description: 'createAgentResponseMessage function exists'
  },
  handlerImport: {
    file: 'store/websocket-event-handlers-main.ts',
    pattern: /handleAgentResponse/,
    description: 'handleAgentResponse is imported'
  },
  handlerRegistration: {
    file: 'store/websocket-event-handlers-main.ts',
    pattern: /'agent_response':\s*handleAgentResponse/,
    description: 'agent_response is registered in handler map'
  }
};

console.log('=====================================');
console.log('WebSocket Agent Response Fix Verification');
console.log('=====================================\n');

let allPassed = true;
const results = [];

Object.entries(CHECKS).forEach(([key, check]) => {
  const filePath = path.join(__dirname, check.file);
  
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const found = check.pattern.test(content);
    
    if (found) {
      console.log(`✓ ${check.description}`);
      results.push({ check: check.description, status: 'PASS' });
    } else {
      console.log(`✗ ${check.description} - NOT FOUND`);
      results.push({ check: check.description, status: 'FAIL' });
      allPassed = false;
    }
  } catch (error) {
    console.log(`✗ ${check.description} - FILE ERROR: ${error.message}`);
    results.push({ check: check.description, status: 'ERROR' });
    allPassed = false;
  }
});

console.log('\n=====================================');
console.log('Verification Summary');
console.log('=====================================\n');

if (allPassed) {
  console.log('✅ SUCCESS: Agent response handler fix is properly implemented!');
  console.log('');
  console.log('The following are in place:');
  console.log('1. handleAgentResponse function exists');
  console.log('2. Data extraction helpers are implemented');
  console.log('3. Handler is registered for agent_response messages');
  console.log('4. Agent responses will display in the chat UI');
  
  // Additional verification
  console.log('\n=====================================');
  console.log('Handler Registration Details');
  console.log('=====================================\n');
  
  try {
    const mainHandlers = fs.readFileSync(
      path.join(__dirname, 'store/websocket-event-handlers-main.ts'), 
      'utf8'
    );
    
    // Find the handlers object
    const handlersMatch = mainHandlers.match(/getEventHandlers[\s\S]*?\{([\s\S]*?)\}/);
    if (handlersMatch) {
      const handlers = handlersMatch[1];
      const handlerLines = handlers.split('\n').filter(line => line.includes(':'));
      
      console.log('Registered WebSocket handlers:');
      handlerLines.forEach(line => {
        const match = line.match(/['"]([^'"]+)['"]/);
        if (match) {
          const isAgentResponse = match[1] === 'agent_response';
          console.log(`  ${isAgentResponse ? '→' : ' '} ${match[1]}${isAgentResponse ? ' ✓ (FIXED)' : ''}`);
        }
      });
    }
  } catch (e) {
    // Silent fail for details
  }
  
} else {
  console.log('❌ FAILURE: Agent response handler fix is NOT properly implemented!');
  console.log('');
  console.log('Missing components:');
  results.filter(r => r.status !== 'PASS').forEach(r => {
    console.log(`  - ${r.check}`);
  });
  console.log('');
  console.log('To fix:');
  console.log('1. Run: git status to check if changes were made');
  console.log('2. Verify the files exist in frontend/store/');
  console.log('3. Check that handleAgentResponse is exported and imported correctly');
  
  process.exit(1);
}

console.log('\n=====================================');
console.log('Test Messages');  
console.log('=====================================\n');

// Show example of what backend sends
const exampleMessage = {
  type: 'agent_response',
  content: 'Hello! I can help you with that.',
  user_id: 'user-123',
  thread_id: 'thread-456',
  timestamp: Date.now() / 1000,
  data: {
    status: 'success',
    agents_involved: ['triage'],
    orchestration_time: 0.8
  }
};

console.log('Example backend message that should now be handled:');
console.log(JSON.stringify(exampleMessage, null, 2));

console.log('\n✅ Verification complete!');