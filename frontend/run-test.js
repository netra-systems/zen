#!/usr/bin/env node

/**
 * Test runner script for frontend tests
 * Handles environment setup and Jest execution
 */

const { spawn } = require('child_process');
const path = require('path');

// Set up environment variables
process.env.NODE_ENV = 'test';

// Parse command line arguments
const args = process.argv.slice(2);

// Extract environment variables from args
const envArgs = args.filter(arg => arg.includes('='));
const jestArgs = args.filter(arg => !arg.includes('='));

// Set environment variables
envArgs.forEach(arg => {
  const [key, value] = arg.split('=');
  process.env[key] = value;
});

// Default Jest configuration
const defaultConfig = path.join(__dirname, 'jest.config.unified.cjs');

// Check if a specific config was provided
let configIndex = jestArgs.indexOf('--config');
let configFile = defaultConfig;

if (configIndex !== -1 && jestArgs[configIndex + 1]) {
  configFile = jestArgs[configIndex + 1];
  // Remove config args as we'll add them back
  jestArgs.splice(configIndex, 2);
}

// Build Jest command
const jestCommand = 'jest';
const jestFinalArgs = [
  '--config', configFile,
  ...jestArgs
];

console.log(`Running Jest with args: ${jestFinalArgs.join(' ')}`);
console.log(`Environment: TEST_SUITE=${process.env.TEST_SUITE || 'all'}`);

// Run Jest
const jest = spawn('npx', [jestCommand, ...jestFinalArgs], {
  stdio: 'inherit',
  shell: true,
  env: process.env
});

jest.on('close', (code) => {
  process.exit(code);
});

jest.on('error', (err) => {
  console.error('Failed to start Jest:', err);
  process.exit(1);
});