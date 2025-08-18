#!/usr/bin/env node

/**
 * Windows-compatible Jest runner
 * Fixes Bus error by calling Jest directly through Node.js
 * Handles extended glob patterns by converting to Jest project selection
 */

const { spawn } = require('child_process');
const path = require('path');

// Parse command line arguments
const args = process.argv.slice(2);

// Default to the main Jest config if no config specified
const hasConfig = args.some(arg => arg.includes('--config'));
if (!hasConfig) {
  args.unshift('--config', 'jest.config.cjs');
}

// Handle the complex testMatch pattern for core test categories
const testMatchIndex = args.findIndex(arg => 
  arg.includes('--testMatch') && 
  arg.includes('@(components|hooks|store|services|lib|utils)')
);

if (testMatchIndex !== -1) {
  // Remove the problematic testMatch argument
  args.splice(testMatchIndex, 1);
  
  // Add project selection for the core categories
  args.push('--selectProjects=components,hooks,store,services,lib,utils');
}

// Path to Jest binary
const jestPath = path.join(__dirname, 'node_modules', 'jest', 'bin', 'jest.js');

// Run Jest with arguments
const child = spawn('node', [jestPath, ...args], {
  stdio: 'inherit',
  cwd: __dirname
});

// Handle process exit
child.on('close', (code) => {
  process.exit(code);
});

child.on('error', (err) => {
  // console output removed: console.log('Error running Jest:', err);
  process.exit(1);
});