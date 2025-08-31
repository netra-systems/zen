#!/bin/sh
# Docker development startup script for Next.js
# Pre-compiles pages to avoid lazy loading issues

echo "🚀 Starting frontend in Docker development mode..."

# Set environment flag for Docker
export DOCKER_ENV=1

# Create .next directory if it doesn't exist
mkdir -p .next

echo "📦 Pre-compiling pages for faster initial load..."

# Use Next.js build API to pre-compile critical pages without full build
node -e "
const { createRequire } = require('module');
const require2 = createRequire(process.cwd());

async function precompilePages() {
  try {
    console.log('Pre-compiling critical pages...');
    
    // Touch main pages to trigger compilation
    const pages = [
      '/',
      '/chat',
      '/auth/login',
      '/auth/signup',
      '/api/health'
    ];
    
    const http = require('http');
    
    // Start dev server in background
    const { spawn } = require('child_process');
    const devServer = spawn('npm', ['run', 'dev'], {
      stdio: 'inherit',
      detached: false
    });
    
    // Wait for server to be ready
    await new Promise(resolve => setTimeout(resolve, 10000));
    
    // Pre-fetch pages to trigger compilation
    for (const page of pages) {
      try {
        await new Promise((resolve, reject) => {
          http.get(\`http://localhost:3000\${page}\`, (res) => {
            res.on('data', () => {});
            res.on('end', resolve);
          }).on('error', reject);
        });
        console.log(\`✓ Pre-compiled: \${page}\`);
      } catch (e) {
        console.log(\`⚠ Could not pre-compile: \${page}\`);
      }
    }
    
    console.log('✅ Pre-compilation complete!');
    
    // Keep the dev server running
    process.on('SIGTERM', () => {
      devServer.kill('SIGTERM');
      process.exit(0);
    });
    
    process.on('SIGINT', () => {
      devServer.kill('SIGINT');
      process.exit(0);
    });
    
  } catch (error) {
    console.error('Pre-compilation failed:', error);
    // Start dev server anyway
    require('child_process').spawn('npm', ['run', 'dev'], {
      stdio: 'inherit'
    });
  }
}

precompilePages();
" &

# Keep container running
wait