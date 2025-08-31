#!/usr/bin/env node
/**
 * Docker development startup script for Next.js
 * Pre-warms the application to avoid lazy loading delays
 */

const { spawn } = require('child_process');
const http = require('http');

// Pages to pre-warm
const PAGES_TO_WARM = [
  '/',
  '/chat',
  '/auth/login',
  '/api/health'
];

// Time to wait for server to start (ms)
const SERVER_START_DELAY = 15000;

// Time between page warming requests (ms)
const WARM_REQUEST_DELAY = 1000;

console.log('🚀 Starting Next.js development server with pre-warming...');

// Start the Next.js dev server
const devServer = spawn('npm', ['run', 'dev'], {
  stdio: 'inherit',
  env: { ...process.env, DOCKER_ENV: '1' }
});

// Handle process termination
process.on('SIGTERM', () => {
  console.log('\n🛑 Received SIGTERM, shutting down gracefully...');
  devServer.kill('SIGTERM');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('\n🛑 Received SIGINT, shutting down gracefully...');
  devServer.kill('SIGINT');
  process.exit(0);
});

// Pre-warm pages after server starts
setTimeout(async () => {
  console.log('\n📦 Pre-warming pages for faster initial load...');
  
  for (const page of PAGES_TO_WARM) {
    try {
      await new Promise((resolve, reject) => {
        const req = http.get(`http://localhost:3000${page}`, (res) => {
          res.on('data', () => {}); // Consume response
          res.on('end', resolve);
        });
        
        req.on('error', reject);
        req.setTimeout(5000, () => {
          req.destroy();
          reject(new Error('Request timeout'));
        });
      });
      
      console.log(`  ✓ Warmed: ${page}`);
      
      // Small delay between requests
      await new Promise(resolve => setTimeout(resolve, WARM_REQUEST_DELAY));
    } catch (error) {
      console.log(`  ⚠ Could not warm: ${page} (${error.message})`);
    }
  }
  
  console.log('\n✅ Pre-warming complete! Frontend is ready.\n');
}, SERVER_START_DELAY);

// Keep the process alive
devServer.on('exit', (code) => {
  console.log(`Dev server exited with code ${code}`);
  process.exit(code || 0);
});