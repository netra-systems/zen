#!/usr/bin/env node
/**
 * Pre-compile critical pages in Next.js to avoid lazy loading delays
 * This script is run after the dev server starts
 */

const http = require('http');

// Pages to pre-compile
const PAGES_TO_WARM = [
  '/',
  '/chat',
  '/auth/login',
  '/api/health'
];

// Time between requests (ms)
const REQUEST_DELAY = 1000;

async function warmPage(page) {
  return new Promise((resolve, reject) => {
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
}

async function precompilePages() {
  console.log('📦 Pre-compiling pages for faster initial load...');
  
  for (const page of PAGES_TO_WARM) {
    try {
      await warmPage(page);
      console.log(`  ✓ Pre-compiled: ${page}`);
      await new Promise(resolve => setTimeout(resolve, REQUEST_DELAY));
    } catch (error) {
      console.log(`  ⚠ Could not pre-compile: ${page}`);
    }
  }
  
  console.log('✅ Pre-compilation complete! Frontend is ready.\n');
}

// Wait a bit for the server to be fully ready
setTimeout(precompilePages, 5000);