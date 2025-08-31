#!/usr/bin/env node

/**
 * WebSocket Agent Response Regression Test Suite Runner
 * 
 * This script runs all tests related to the agent_response handler fix
 * to prevent regression of the critical bug where agent responses were not displayed.
 * 
 * Related to: SPEC/learnings/websocket_agent_response_missing_handler.xml
 */

const { execSync } = require('child_process');
const chalk = require('chalk');
const path = require('path');
const fs = require('fs');

// Test configuration
const TEST_SUITES = {
  unit: {
    name: 'Unit Tests',
    command: 'npm test -- __tests__/websocket-agent-response-handler.test.ts',
    critical: true
  },
  integration: {
    name: 'Integration Tests',
    command: 'npm test -- __tests__/websocket-message-alignment.test.ts',
    critical: true
  },
  e2e: {
    name: 'E2E Cypress Tests',
    command: 'npm run cypress:run -- --spec "cypress/e2e/websocket-agent-response-regression.cy.ts"',
    critical: true
  }
};

// Helper functions
const log = {
  info: (msg) => console.log(chalk.blue('[INFO]'), msg),
  success: (msg) => console.log(chalk.green('[SUCCESS]'), msg),
  error: (msg) => console.log(chalk.red('[ERROR]'), msg),
  warning: (msg) => console.log(chalk.yellow('[WARNING]'), msg),
  section: (msg) => console.log(chalk.cyan('\n' + '='.repeat(60) + '\n' + msg + '\n' + '='.repeat(60)))
};

function runCommand(command, description) {
  try {
    log.info(`Running: ${description}`);
    execSync(command, { 
      stdio: 'inherit',
      cwd: path.resolve(__dirname, '..')
    });
    return true;
  } catch (error) {
    log.error(`Failed: ${description}`);
    return false;
  }
}

function checkPrerequisites() {
  log.section('Checking Prerequisites');
  
  // Check if we're in the frontend directory
  const packageJson = path.join(process.cwd(), 'package.json');
  if (!fs.existsSync(packageJson)) {
    log.error('package.json not found. Please run this script from the frontend directory.');
    return false;
  }
  
  // Check if required test files exist
  const testFiles = [
    '__tests__/websocket-agent-response-handler.test.ts',
    '__tests__/websocket-message-alignment.test.ts',
    'cypress/e2e/websocket-agent-response-regression.cy.ts'
  ];
  
  const missingFiles = testFiles.filter(file => 
    !fs.existsSync(path.join(process.cwd(), file))
  );
  
  if (missingFiles.length > 0) {
    log.warning('Missing test files:');
    missingFiles.forEach(file => log.warning(`  - ${file}`));
    return false;
  }
  
  log.success('All prerequisites met');
  return true;
}

function runRegressionTests() {
  log.section('WebSocket Agent Response Regression Test Suite');
  
  if (!checkPrerequisites()) {
    log.error('Prerequisites check failed. Exiting.');
    process.exit(1);
  }
  
  const results = {
    passed: [],
    failed: [],
    skipped: []
  };
  
  // Install dependencies if needed
  log.info('Ensuring dependencies are installed...');
  runCommand('npm install', 'Install dependencies');
  
  // Run each test suite
  Object.entries(TEST_SUITES).forEach(([key, suite]) => {
    log.section(`Running ${suite.name}`);
    
    const success = runCommand(suite.command, suite.name);
    
    if (success) {
      results.passed.push(suite.name);
      log.success(`${suite.name} passed`);
    } else {
      results.failed.push(suite.name);
      if (suite.critical) {
        log.error(`CRITICAL: ${suite.name} failed - this could cause agent responses to not display!`);
      }
    }
  });
  
  // Generate summary report
  log.section('Test Results Summary');
  
  console.log('\nPassed Tests:', chalk.green(results.passed.length));
  results.passed.forEach(test => console.log(chalk.green('  ✓'), test));
  
  if (results.failed.length > 0) {
    console.log('\nFailed Tests:', chalk.red(results.failed.length));
    results.failed.forEach(test => console.log(chalk.red('  ✗'), test));
  }
  
  // Check critical regression
  const agentResponseHandlerExists = !results.failed.includes('Unit Tests');
  const messageAlignmentCorrect = !results.failed.includes('Integration Tests');
  const e2eDisplayWorks = !results.failed.includes('E2E Cypress Tests');
  
  log.section('Regression Check');
  
  if (agentResponseHandlerExists && messageAlignmentCorrect) {
    log.success('✓ Agent response handler is properly implemented');
    log.success('✓ Frontend can handle all backend message types');
  } else {
    log.error('✗ CRITICAL REGRESSION DETECTED!');
    log.error('Agent responses may not display in the UI');
  }
  
  if (e2eDisplayWorks) {
    log.success('✓ Agent responses display correctly in UI');
  } else {
    log.warning('⚠ E2E tests failed - manual verification recommended');
  }
  
  // Exit code
  const exitCode = results.failed.length > 0 ? 1 : 0;
  
  if (exitCode === 0) {
    log.section('All Regression Tests Passed! 🎉');
    log.info('The agent_response handler fix is working correctly.');
    log.info('Agent responses will display properly in the chat UI.');
  } else {
    log.section('Regression Tests Failed! ⚠️');
    log.error('The agent_response bug may have resurfaced.');
    log.error('Users might not see agent responses in the chat.');
    log.info('\nTo fix:');
    log.info('1. Ensure handleAgentResponse is in websocket-agent-handlers.ts');
    log.info('2. Ensure agent_response is registered in websocket-event-handlers-main.ts');
    log.info('3. Run tests again: npm run test:websocket-regression');
  }
  
  process.exit(exitCode);
}

// Run tests if executed directly
if (require.main === module) {
  runRegressionTests();
}

module.exports = { runRegressionTests };