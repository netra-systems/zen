#!/usr/bin/env node

/**
 * Staging WebSocket Ticket Authentication Test
 * Tests the newly deployed ticket authentication functionality on GCP staging
 */

const https = require('https');
const WebSocket = require('ws');

// Configuration for staging environment
const STAGING_CONFIG = {
  frontend: 'https://netra-frontend-staging-pnovr5vsba-uc.a.run.app',
  api: 'https://api.staging.netrasystems.ai',
  websocket: 'wss://api.staging.netrasystems.ai'
};

console.log('🚀 Testing Frontend Ticket Authentication on Staging');
console.log('Environment:', STAGING_CONFIG);
console.log('='.repeat(60));

// Test 1: Frontend Health Check
async function testFrontendHealth() {
  console.log('\n📊 Test 1: Frontend Health Check');
  
  return new Promise((resolve, reject) => {
    const url = `${STAGING_CONFIG.frontend}/health`;
    console.log(`Testing: ${url}`);
    
    https.get(url, (res) => {
      console.log(`✅ Frontend Health: HTTP ${res.statusCode}`);
      console.log(`Headers:`, res.headers);
      
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        if (res.statusCode === 200) {
          console.log(`📝 Response:`, data || 'OK');
          resolve({ success: true, status: res.statusCode });
        } else {
          console.log(`❌ Health check failed: ${res.statusCode}`);
          resolve({ success: false, status: res.statusCode, error: data });
        }
      });
    }).on('error', (err) => {
      console.log(`❌ Frontend health check error:`, err.message);
      resolve({ success: false, error: err.message });
    });
  });
}

// Test 2: API Connectivity Check
async function testAPIConnectivity() {
  console.log('\n🔗 Test 2: API Connectivity Check');
  
  return new Promise((resolve, reject) => {
    const url = `${STAGING_CONFIG.api}/health`;
    console.log(`Testing: ${url}`);
    
    https.get(url, (res) => {
      console.log(`✅ API Health: HTTP ${res.statusCode}`);
      
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        if (res.statusCode === 200) {
          console.log(`📝 Response:`, data || 'OK');
          resolve({ success: true, status: res.statusCode });
        } else {
          console.log(`❌ API health check failed: ${res.statusCode}`);
          resolve({ success: false, status: res.statusCode, error: data });
        }
      });
    }).on('error', (err) => {
      console.log(`❌ API connectivity error:`, err.message);
      resolve({ success: false, error: err.message });
    });
  });
}

// Test 3: WebSocket Connection Test
async function testWebSocketConnection() {
  console.log('\n🔌 Test 3: WebSocket Connection Test');
  
  return new Promise((resolve, reject) => {
    const url = `${STAGING_CONFIG.websocket}/ws`;
    console.log(`Testing: ${url}`);
    
    const ws = new WebSocket(url);
    let connected = false;
    let messages = [];
    
    const timeout = setTimeout(() => {
      if (!connected) {
        ws.close();
        console.log(`❌ WebSocket connection timeout`);
        resolve({ success: false, error: 'Connection timeout' });
      }
    }, 10000);
    
    ws.on('open', () => {
      connected = true;
      console.log(`✅ WebSocket connected successfully`);
      
      // Try to send a test message
      const testMessage = {
        type: 'test',
        data: { message: 'staging test' },
        timestamp: Date.now()
      };
      
      ws.send(JSON.stringify(testMessage));
      console.log(`📤 Sent test message:`, testMessage);
      
      // Close after a brief period
      setTimeout(() => {
        clearTimeout(timeout);
        ws.close();
        resolve({ 
          success: true, 
          connected: true, 
          messages: messages.length,
          messagesReceived: messages 
        });
      }, 2000);
    });
    
    ws.on('message', (data) => {
      try {
        const parsed = JSON.parse(data);
        messages.push(parsed);
        console.log(`📥 Received message:`, parsed);
      } catch (e) {
        console.log(`📥 Received raw message:`, data.toString());
        messages.push(data.toString());
      }
    });
    
    ws.on('error', (err) => {
      clearTimeout(timeout);
      console.log(`❌ WebSocket error:`, err.message);
      resolve({ success: false, error: err.message });
    });
    
    ws.on('close', (code, reason) => {
      console.log(`🔌 WebSocket closed: ${code} - ${reason || 'No reason'}`);
    });
  });
}

// Test 4: Frontend Configuration Check
async function testFrontendConfig() {
  console.log('\n⚙️  Test 4: Frontend Configuration Check');
  
  return new Promise((resolve, reject) => {
    const url = `${STAGING_CONFIG.frontend}/api/config/public`;
    console.log(`Testing: ${url}`);
    
    https.get(url, (res) => {
      console.log(`✅ Config endpoint: HTTP ${res.statusCode}`);
      
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try {
          if (data) {
            const config = JSON.parse(data);
            console.log(`📝 Frontend Configuration:`, JSON.stringify(config, null, 2));
            
            // Check for ticket authentication configuration
            const hasTicketConfig = config.websocket && 
              (config.websocket.enableTickets || config.features?.enableWebSocketTickets);
            
            resolve({ 
              success: true, 
              status: res.statusCode, 
              config,
              ticketAuthEnabled: hasTicketConfig
            });
          } else {
            resolve({ success: false, error: 'Empty response' });
          }
        } catch (e) {
          console.log(`❌ Failed to parse config:`, e.message);
          console.log(`Raw response:`, data);
          resolve({ success: false, error: 'Invalid JSON', raw: data });
        }
      });
    }).on('error', (err) => {
      console.log(`❌ Frontend config error:`, err.message);
      resolve({ success: false, error: err.message });
    });
  });
}

// Main test execution
async function runStagingTests() {
  const results = {
    timestamp: new Date().toISOString(),
    environment: 'staging',
    config: STAGING_CONFIG,
    tests: {}
  };
  
  console.log(`⏰ Starting tests at ${results.timestamp}`);
  
  // Execute tests
  results.tests.frontendHealth = await testFrontendHealth();
  results.tests.apiConnectivity = await testAPIConnectivity();
  results.tests.websocketConnection = await testWebSocketConnection();
  results.tests.frontendConfig = await testFrontendConfig();
  
  // Summary
  console.log('\n' + '='.repeat(60));
  console.log('📊 STAGING TEST RESULTS SUMMARY');
  console.log('='.repeat(60));
  
  const testNames = Object.keys(results.tests);
  const passedTests = testNames.filter(name => results.tests[name].success);
  const failedTests = testNames.filter(name => !results.tests[name].success);
  
  console.log(`✅ Passed: ${passedTests.length}/${testNames.length}`);
  console.log(`❌ Failed: ${failedTests.length}/${testNames.length}`);
  
  if (passedTests.length > 0) {
    console.log(`\n✅ Passed Tests:`);
    passedTests.forEach(name => console.log(`   - ${name}`));
  }
  
  if (failedTests.length > 0) {
    console.log(`\n❌ Failed Tests:`);
    failedTests.forEach(name => {
      console.log(`   - ${name}: ${results.tests[name].error || 'Unknown error'}`);
    });
  }
  
  // Check for ticket authentication readiness
  const configTest = results.tests.frontendConfig;
  if (configTest.success && configTest.ticketAuthEnabled) {
    console.log(`\n🎫 Ticket Authentication: ENABLED`);
  } else {
    console.log(`\n🎫 Ticket Authentication: NOT DETECTED`);
  }
  
  console.log('\n' + '='.repeat(60));
  
  // Save results to file
  const fs = require('fs');
  const resultsFile = `staging_test_results_${Date.now()}.json`;
  fs.writeFileSync(resultsFile, JSON.stringify(results, null, 2));
  console.log(`📁 Full results saved to: ${resultsFile}`);
  
  return results;
}

// Run the tests
if (require.main === module) {
  runStagingTests()
    .then(results => {
      const success = Object.values(results.tests).every(test => test.success);
      process.exit(success ? 0 : 1);
    })
    .catch(err => {
      console.error('❌ Test execution failed:', err);
      process.exit(1);
    });
}

module.exports = { runStagingTests };