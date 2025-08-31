/**
 * Cross-platform test runner for Jest with environment variable support
 */
const { spawn } = require('child_process');
const path = require('path');

// Parse command line arguments
const args = process.argv.slice(2);

// Extract environment variables from command
const envVars = {};
const jestArgs = [];

args.forEach(arg => {
  if (arg.includes('=')) {
    const [key, value] = arg.split('=');
    envVars[key] = value;
  } else {
    jestArgs.push(arg);
  }
});

// Set up environment - CRITICAL: Ensure test environment is properly set
const env = {
  ...process.env,
  ...envVars,
  NODE_ENV: 'test',
  NEXT_PUBLIC_ENVIRONMENT: 'test',
  NEXT_PUBLIC_API_URL: 'http://localhost:8000',
  NEXT_PUBLIC_WS_URL: 'ws://localhost:8000',
  NEXT_PUBLIC_AUTH_SERVICE_URL: 'http://localhost:8081',
  NEXT_PUBLIC_FRONTEND_URL: 'http://localhost:3000',
};

// Remove any staging environment variables that might be set
delete env.NEXT_PUBLIC_STAGING;

// Determine Jest path
const jestPath = path.join(__dirname, 'node_modules', 'jest', 'bin', 'jest.js');

// Spawn Jest process
const jest = spawn(
  'node',
  [jestPath, ...jestArgs],
  {
    env,
    stdio: 'inherit',
  }
);

// Handle process exit
jest.on('close', (code) => {
  process.exit(code);
});

jest.on('error', (err) => {
  console.error('Failed to start Jest:', err);
  process.exit(1);
});