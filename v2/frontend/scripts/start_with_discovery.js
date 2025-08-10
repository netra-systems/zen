#!/usr/bin/env node
/**
 * Start frontend with automatic backend discovery
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

// Read backend service discovery info
function readBackendInfo() {
  const discoveryFile = path.join('..', '.netra', 'backend.json');
  
  if (fs.existsSync(discoveryFile)) {
    try {
      const content = fs.readFileSync(discoveryFile, 'utf8');
      return JSON.parse(content);
    } catch (error) {
      console.error('Error reading backend discovery file:', error);
    }
  }
  
  return null;
}

// Start the frontend with proper environment variables
function startFrontend() {
  const backendInfo = readBackendInfo();
  
  let apiUrl = 'http://localhost:8000';  // Default
  let wsUrl = 'ws://localhost:8000/ws';  // Default
  
  if (backendInfo) {
    apiUrl = backendInfo.api_url;
    wsUrl = backendInfo.ws_url;
    console.log(`🔍 Backend discovered at ${apiUrl}`);
  } else {
    console.log('⚠️  No backend discovery info found, using defaults');
    console.log('   Start the backend first with: python run_server.py --dynamic-port');
  }
  
  // Set environment variables
  const env = {
    ...process.env,
    NEXT_PUBLIC_API_URL: apiUrl,
    NEXT_PUBLIC_WS_URL: wsUrl
  };
  
  console.log(`📡 Frontend connecting to backend at:`);
  console.log(`   API: ${apiUrl}`);
  console.log(`   WebSocket: ${wsUrl}`);
  
  // Determine the npm command based on the first argument
  const command = process.argv[2] || 'dev';  // 'dev' for hot reload, 'start' for production mode
  console.log(`   Mode: ${command === 'dev' ? 'Development (with hot reload)' : 'Production (no hot reload)'}`);
  
  // Start Next.js
  const child = spawn('npm', ['run', command], {
    env,
    stdio: 'inherit',
    shell: true
  });
  
  child.on('error', (error) => {
    console.error('Failed to start frontend:', error);
    process.exit(1);
  });
  
  child.on('exit', (code) => {
    process.exit(code);
  });
}

// Main execution
startFrontend();