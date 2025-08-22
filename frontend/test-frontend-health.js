/**
 * Frontend Health Check Script
 * Tests if frontend loads and basic functionality works
 */

const http = require('http');
const https = require('https');

// Helper function to make HTTP requests
function makeRequest(url, timeout = 10000) {
  return new Promise((resolve, reject) => {
    const module = url.startsWith('https:') ? https : http;
    const timeoutId = setTimeout(() => {
      reject(new Error(`Request timeout after ${timeout}ms`));
    }, timeout);

    const req = module.get(url, (res) => {
      clearTimeout(timeoutId);
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        resolve({
          statusCode: res.statusCode,
          headers: res.headers,
          data: data
        });
      });
    });

    req.on('error', (err) => {
      clearTimeout(timeoutId);
      reject(err);
    });
  });
}

async function testFrontendHealth() {
  console.log('🔍 Testing Frontend Health...\n');
  
  const tests = [
    {
      name: 'Main Page Load',
      url: 'http://localhost:3000',
      expectedStatus: 200
    },
    {
      name: 'Login Page Load',
      url: 'http://localhost:3000/login',
      expectedStatus: 200
    },
    {
      name: 'Chat Page Load',
      url: 'http://localhost:3000/chat',
      expectedStatus: 200
    },
    {
      name: 'Static Assets',
      url: 'http://localhost:3000/_next/static/chunks/main.js',
      expectedStatus: 200,
      optional: true
    }
  ];

  let passed = 0;
  let failed = 0;

  for (const test of tests) {
    try {
      console.log(`Testing: ${test.name}...`);
      const result = await makeRequest(test.url, 8000);
      
      if (result.statusCode === test.expectedStatus) {
        console.log(`✅ ${test.name} - Status: ${result.statusCode}`);
        
        // Check if HTML contains React root
        if (result.data.includes('id="__next"') || result.data.includes('id="root"')) {
          console.log(`✅ ${test.name} - React root element found`);
        }
        
        // Check for obvious errors
        if (result.data.includes('Error') && !result.data.includes('error-boundary')) {
          console.log(`⚠️  ${test.name} - Possible errors in response`);
        }
        
        passed++;
      } else {
        console.log(`❌ ${test.name} - Expected ${test.expectedStatus}, got ${result.statusCode}`);
        if (!test.optional) failed++;
      }
    } catch (error) {
      console.log(`❌ ${test.name} - ${error.message}`);
      if (!test.optional) failed++;
    }
    console.log('');
  }

  console.log(`\n📊 Results: ${passed} passed, ${failed} failed`);
  
  if (failed === 0) {
    console.log('🎉 Frontend appears to be working correctly!');
    return true;
  } else {
    console.log('⚠️  Some tests failed. Check the issues above.');
    return false;
  }
}

// Wait a moment for server to start if needed
setTimeout(() => {
  testFrontendHealth().catch(console.error);
}, 2000);