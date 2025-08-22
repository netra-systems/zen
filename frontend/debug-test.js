#!/usr/bin/env node

// Debug script to test specific failing tests
const { exec } = require('child_process');

function runTest(testFile, testName) {
  const command = `npx jest "${testFile}" --testNamePattern="${testName}" --no-coverage --verbose --runInBand`;
  
  console.log(`Running: ${command}`);
  
  const child = exec(command, { timeout: 60000 }, (error, stdout, stderr) => {
    if (error) {
      console.error('Test failed with error:', error.message);
    }
    
    console.log('STDOUT:', stdout);
    if (stderr) {
      console.error('STDERR:', stderr);
    }
  });
  
  // Kill after 60 seconds
  setTimeout(() => {
    child.kill('SIGKILL');
  }, 60000);
}

// Test specific failing test
runTest(
  '__tests__/components/ChatSidebar/basic.test.tsx', 
  'should handle threads with missing metadata gracefully'
);