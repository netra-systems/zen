#!/usr/bin/env node

/**
 * Frontend Navigation and Error Testing Script
 * Tests all major routes and checks for potential issues
 */

const https = require('https');
const http = require('http');

// Configuration
const FRONTEND_BASE = 'http://localhost:3000';
const BACKEND_BASE = 'http://localhost:8000';

// Routes to test
const ROUTES = [
  '/',
  '/chat',
  '/demo',
  '/enterprise-demo',
  '/corpus',
  '/ingestion',
  '/synthetic-data-generation',
  '/login',
  '/auth/error',
  '/auth/logout'
];

// API endpoints to test
const API_ENDPOINTS = [
  '/health',
  '/api/health',
  '/ws'
];

/**
 * Makes HTTP request and returns response data
 */
function makeRequest(url, timeout = 5000) {
  return new Promise((resolve, reject) => {
    const module = url.startsWith('https:') ? https : http;
    
    const req = module.get(url, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        resolve({
          statusCode: res.statusCode,
          headers: res.headers,
          body: data,
          url: url
        });
      });
    });
    
    req.on('error', (err) => {
      resolve({
        statusCode: 0,
        error: err.message,
        url: url
      });
    });
    
    req.setTimeout(timeout, () => {
      req.destroy();
      resolve({
        statusCode: 0,
        error: 'Request timeout',
        url: url
      });
    });
  });
}

/**
 * Analyzes HTML response for potential issues
 */
function analyzeHTMLResponse(response) {
  const issues = [];
  const body = response.body || '';
  
  // Check for common error indicators
  if (body.includes('Application error')) {
    issues.push('Application error detected in HTML');
  }
  
  if (body.includes('404') && response.statusCode === 200) {
    issues.push('404 content in successful response');
  }
  
  if (body.includes('Error:') || body.includes('TypeError:') || body.includes('ReferenceError:')) {
    issues.push('JavaScript errors detected in HTML');
  }
  
  if (body.includes('undefined') && body.includes('TypeError')) {
    issues.push('Undefined variable errors detected');
  }
  
  if (body.includes('Failed to fetch') || body.includes('Network error')) {
    issues.push('Network/API errors detected');
  }
  
  if (body.includes('WebSocket') && body.includes('failed')) {
    issues.push('WebSocket connection issues detected');
  }
  
  // Check for missing resources
  if (body.includes('Cannot resolve module') || body.includes('Module not found')) {
    issues.push('Missing module/resource errors detected');
  }
  
  return issues;
}

/**
 * Tests a single route
 */
async function testRoute(route) {
  console.log(`Testing route: ${route}`);
  
  const response = await makeRequest(`${FRONTEND_BASE}${route}`);
  
  const result = {
    route: route,
    statusCode: response.statusCode,
    accessible: response.statusCode === 200,
    issues: [],
    error: response.error
  };
  
  if (response.statusCode === 200) {
    result.issues = analyzeHTMLResponse(response);
  }
  
  return result;
}

/**
 * Tests backend connectivity
 */
async function testBackendConnectivity() {
  console.log('Testing backend connectivity...');
  
  const results = [];
  
  for (const endpoint of API_ENDPOINTS) {
    const response = await makeRequest(`${BACKEND_BASE}${endpoint}`);
    
    results.push({
      endpoint: endpoint,
      statusCode: response.statusCode,
      accessible: response.statusCode > 0 && response.statusCode < 500,
      error: response.error
    });
  }
  
  return results;
}

/**
 * Main testing function
 */
async function runTests() {
  console.log('🚀 Starting Frontend Navigation and Error Testing\n');
  
  // Test all routes
  console.log('📝 Testing Frontend Routes...');
  const routeResults = [];
  
  for (const route of ROUTES) {
    const result = await testRoute(route);
    routeResults.push(result);
    
    if (result.accessible) {
      console.log(`✅ ${route} - OK`);
      if (result.issues.length > 0) {
        console.log(`⚠️  Issues found: ${result.issues.join(', ')}`);
      }
    } else {
      console.log(`❌ ${route} - Failed (${result.statusCode}) ${result.error || ''}`);
    }
  }
  
  console.log('\n🔗 Testing Backend Connectivity...');
  const backendResults = await testBackendConnectivity();
  
  for (const result of backendResults) {
    if (result.accessible) {
      console.log(`✅ Backend ${result.endpoint} - OK (${result.statusCode})`);
    } else {
      console.log(`❌ Backend ${result.endpoint} - Failed (${result.statusCode}) ${result.error || ''}`);
    }
  }
  
  // Generate summary
  console.log('\n📊 Test Summary:');
  console.log('================');
  
  const accessibleRoutes = routeResults.filter(r => r.accessible).length;
  const totalRoutes = routeResults.length;
  
  console.log(`Frontend Routes: ${accessibleRoutes}/${totalRoutes} accessible`);
  
  const routesWithIssues = routeResults.filter(r => r.issues.length > 0);
  if (routesWithIssues.length > 0) {
    console.log(`⚠️  Routes with issues: ${routesWithIssues.length}`);
    routesWithIssues.forEach(r => {
      console.log(`   ${r.route}: ${r.issues.join(', ')}`);
    });
  }
  
  const accessibleBackend = backendResults.filter(r => r.accessible).length;
  const totalBackend = backendResults.length;
  
  console.log(`Backend Endpoints: ${accessibleBackend}/${totalBackend} accessible`);
  
  if (accessibleBackend === 0) {
    console.log('⚠️  Backend appears to be offline - frontend will work with limited functionality');
  }
  
  console.log('\n🎯 Recommendations:');
  console.log('==================');
  
  if (accessibleRoutes === totalRoutes && routesWithIssues.length === 0) {
    console.log('✅ All frontend routes are working correctly!');
  }
  
  if (routesWithIssues.length > 0) {
    console.log('⚠️  Some routes have issues - check browser console for details');
  }
  
  if (accessibleBackend === 0) {
    console.log('🔧 Start the backend server to enable full functionality');
    console.log('   Run: python app/main.py (or appropriate backend startup command)');
  }
  
  return {
    frontend: {
      total: totalRoutes,
      accessible: accessibleRoutes,
      withIssues: routesWithIssues.length
    },
    backend: {
      total: totalBackend,
      accessible: accessibleBackend
    }
  };
}

// Run tests if script is executed directly
if (require.main === module) {
  runTests().catch(console.error);
}

module.exports = { runTests, testRoute, testBackendConnectivity };