#!/usr/bin/env node

/**
 * Windows-compatible Jest runner
 * Fixes Bus error by calling Jest directly through Node.js
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
  console.error('Error running Jest:', err);
  process.exit(1);
});