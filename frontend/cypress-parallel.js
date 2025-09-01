#!/usr/bin/env node
/**
 * Cypress Parallel Test Runner
 * Runs Cypress tests in parallel with configurable workers and timeouts
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const glob = require('glob');

// Configuration
const CONFIG = {
  workers: parseInt(process.env.CYPRESS_WORKERS || '4'),
  testTimeout: parseInt(process.env.CYPRESS_TEST_TIMEOUT || '300'), // seconds
  suiteTimeout: parseInt(process.env.CYPRESS_SUITE_TIMEOUT || '3600'), // seconds (1 hour)
  browser: process.env.CYPRESS_BROWSER || 'chrome',
  headed: process.env.CYPRESS_HEADED === 'true',
  baseUrl: process.env.CYPRESS_BASE_URL || 'http://localhost:3000',
  configFile: process.env.CYPRESS_CONFIG || 'cypress.parallel.config.ts'
};

// Parse command line arguments
const args = process.argv.slice(2);
const argMap = {};
for (let i = 0; i < args.length; i++) {
  if (args[i].startsWith('--')) {
    const key = args[i].substring(2);
    const value = args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : true;
    argMap[key] = value;
    if (value !== true) i++;
  }
}

// Override config with command line args
if (argMap.workers) CONFIG.workers = parseInt(argMap.workers);
if (argMap.timeout) CONFIG.testTimeout = parseInt(argMap.timeout);
if (argMap['suite-timeout']) CONFIG.suiteTimeout = parseInt(argMap['suite-timeout']);
if (argMap.browser) CONFIG.browser = argMap.browser;
if (argMap.headed) CONFIG.headed = true;
if (argMap.headless) CONFIG.headed = false;

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function log(message, color = '') {
  const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
  console.log(`${color}[${timestamp}] ${message}${colors.reset}`);
}

function discoverTests() {
  // Use forward slashes for glob pattern even on Windows
  const pattern = 'cypress/e2e/**/*.cy.{js,ts,jsx,tsx}';
  const files = glob.sync(pattern, { cwd: __dirname });
  log(`Found ${files.length} test files`, colors.cyan);
  return files.map(f => path.relative(__dirname, f).replace(/\\/g, '/'));
}

function splitTests(tests, numWorkers) {
  const chunks = [];
  const chunkSize = Math.ceil(tests.length / numWorkers);
  
  for (let i = 0; i < numWorkers; i++) {
    const start = i * chunkSize;
    const end = Math.min(start + chunkSize, tests.length);
    if (start < tests.length) {
      chunks.push(tests.slice(start, end));
    }
  }
  
  return chunks;
}

function runWorker(workerId, tests) {
  return new Promise((resolve) => {
    const startTime = Date.now();
    const env = {
      ...process.env,
      CYPRESS_WORKER_ID: String(workerId),
      CYPRESS_PARALLEL: 'true',
      CYPRESS_TEST_TIMEOUT: String(CONFIG.testTimeout * 1000),
      CYPRESS_BASE_URL: CONFIG.baseUrl,
      NO_COLOR: '0',
      FORCE_COLOR: '1'
    };
    
    const specs = tests.join(',');
    const args = [
      'cypress', 'run',
      '--config-file', CONFIG.configFile,
      '--spec', specs,
      '--browser', CONFIG.browser,
      '--reporter', 'spec'
    ];
    
    if (!CONFIG.headed) {
      args.push('--headless');
    }
    
    log(`Worker ${workerId}: Starting ${tests.length} tests`, colors.blue);
    
    const child = spawn('npx', args, {
      env,
      cwd: __dirname,
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: true
    });
    
    let output = '';
    let errorOutput = '';
    let testResults = { passed: 0, failed: 0, skipped: 0 };
    
    // Parse output to track progress
    child.stdout.on('data', (data) => {
      const text = data.toString();
      output += text;
      
      // Parse test results from output
      if (text.includes('✓')) {
        testResults.passed++;
      } else if (text.includes('✗') || text.includes('✖')) {
        testResults.failed++;
      }
      
      // Show worker progress
      if (text.includes('Running:') || text.includes('✓') || text.includes('✗')) {
        const lines = text.split('\n').filter(l => l.trim());
        lines.forEach(line => {
          if (line.trim()) {
            console.log(`  ${colors.bright}[W${workerId}]${colors.reset} ${line}`);
          }
        });
      }
    });
    
    child.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });
    
    // Handle timeout
    const timeout = setTimeout(() => {
      log(`Worker ${workerId}: Timeout after ${CONFIG.testTimeout}s`, colors.red);
      child.kill('SIGTERM');
    }, CONFIG.testTimeout * 1000);
    
    child.on('close', (code) => {
      clearTimeout(timeout);
      const duration = ((Date.now() - startTime) / 1000).toFixed(1);
      
      if (code === 0) {
        log(`Worker ${workerId}: Completed successfully in ${duration}s`, colors.green);
      } else {
        log(`Worker ${workerId}: Failed with code ${code} in ${duration}s`, colors.red);
        if (errorOutput) {
          console.error(`Worker ${workerId} errors:`, errorOutput);
        }
      }
      
      resolve({
        workerId,
        exitCode: code,
        duration: parseFloat(duration),
        tests: tests.length,
        results: testResults,
        output,
        errorOutput
      });
    });
  });
}

async function runParallel() {
  const startTime = Date.now();
  
  console.log(`\n${colors.bright}${'='.repeat(60)}`);
  console.log(`CYPRESS PARALLEL TEST RUNNER`);
  console.log(`${'='.repeat(60)}${colors.reset}`);
  console.log(`Workers: ${CONFIG.workers}`);
  console.log(`Test Timeout: ${CONFIG.testTimeout}s`);
  console.log(`Suite Timeout: ${CONFIG.suiteTimeout}s`);
  console.log(`Browser: ${CONFIG.browser} (${CONFIG.headed ? 'headed' : 'headless'})`);
  console.log(`Base URL: ${CONFIG.baseUrl}`);
  console.log(`${'='.repeat(60)}\n`);
  
  // Discover and split tests
  const allTests = discoverTests();
  if (allTests.length === 0) {
    log('No tests found!', colors.red);
    process.exit(1);
  }
  
  const testChunks = splitTests(allTests, CONFIG.workers);
  
  // Show distribution
  testChunks.forEach((chunk, i) => {
    log(`Worker ${i}: ${chunk.length} tests assigned`, colors.cyan);
  });
  console.log('');
  
  // Run workers in parallel
  const workers = testChunks.map((tests, i) => runWorker(i, tests));
  
  // Set suite timeout
  const suiteTimeout = setTimeout(() => {
    log(`Suite timeout reached (${CONFIG.suiteTimeout}s)`, colors.red);
    process.exit(1);
  }, CONFIG.suiteTimeout * 1000);
  
  // Wait for all workers
  const results = await Promise.all(workers);
  clearTimeout(suiteTimeout);
  
  // Calculate summary
  const totalDuration = ((Date.now() - startTime) / 1000).toFixed(1);
  const totalTests = results.reduce((sum, r) => sum + r.tests, 0);
  const totalPassed = results.reduce((sum, r) => sum + r.results.passed, 0);
  const totalFailed = results.reduce((sum, r) => sum + r.results.failed, 0);
  const totalSkipped = results.reduce((sum, r) => sum + r.results.skipped, 0);
  const failedWorkers = results.filter(r => r.exitCode !== 0).length;
  
  // Print summary
  console.log(`\n${colors.bright}${'='.repeat(60)}`);
  console.log(`TEST EXECUTION SUMMARY`);
  console.log(`${'='.repeat(60)}${colors.reset}`);
  console.log(`Total Tests: ${totalTests}`);
  console.log(`${colors.green}Passed: ${totalPassed}${colors.reset}`);
  console.log(`${colors.red}Failed: ${totalFailed}${colors.reset}`);
  console.log(`${colors.yellow}Skipped: ${totalSkipped}${colors.reset}`);
  console.log(`Workers Used: ${CONFIG.workers}`);
  console.log(`Failed Workers: ${failedWorkers}`);
  console.log(`Total Duration: ${totalDuration}s (${(totalDuration/60).toFixed(1)} minutes)`);
  console.log(`Average per Test: ${(totalDuration/totalTests).toFixed(1)}s`);
  console.log(`${'='.repeat(60)}\n`);
  
  // Save results to file
  const reportPath = path.join(__dirname, 'cypress', 'parallel-results.json');
  const report = {
    timestamp: new Date().toISOString(),
    config: CONFIG,
    summary: {
      totalTests,
      passed: totalPassed,
      failed: totalFailed,
      skipped: totalSkipped,
      duration: parseFloat(totalDuration),
      workers: CONFIG.workers,
      failedWorkers
    },
    workers: results.map(r => ({
      id: r.workerId,
      tests: r.tests,
      duration: r.duration,
      exitCode: r.exitCode,
      results: r.results
    }))
  };
  
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  log(`Report saved to: ${reportPath}`, colors.cyan);
  
  // Exit with appropriate code
  process.exit(failedWorkers > 0 ? 1 : 0);
}

// Handle interrupts
process.on('SIGINT', () => {
  log('\nInterrupted by user', colors.yellow);
  process.exit(130);
});

process.on('SIGTERM', () => {
  log('\nTerminated', colors.yellow);
  process.exit(143);
});

// Run
runParallel().catch(err => {
  log(`Error: ${err.message}`, colors.red);
  console.error(err);
  process.exit(1);
});