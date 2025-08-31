#!/usr/bin/env node
/**
 * Test Hanging Fixes Verification Script
 * 
 * This script tests a few problematic test files to verify our fixes work
 */

const { spawn } = require('child_process');
const path = require('path');

// Test files that were problematic
const PROBLEMATIC_TESTS = [
  '__tests__/critical/memory-exhaustion.test.tsx',
  '__tests__/auth/dev-auto-login.test.tsx', 
  '__tests__/auth/staging-refresh-loop.test.tsx',
];

// Configuration
const TIMEOUT_MS = 30000; // 30 seconds max per test file
const MAX_WORKERS = 1; // Run sequentially to avoid resource conflicts

async function runTestFile(testFile) {
  return new Promise((resolve, reject) => {
    console.log(`🧪 Testing: ${testFile}`);
    
    const jestProcess = spawn('npm', ['test', testFile, '--', '--silent', '--maxWorkers=1'], {
      cwd: __dirname,
      stdio: ['pipe', 'pipe', 'pipe']
    });
    
    let stdout = '';
    let stderr = '';
    let timedOut = false;
    
    const timeout = setTimeout(() => {
      timedOut = true;
      jestProcess.kill('SIGTERM');
      setTimeout(() => {
        if (!jestProcess.killed) {
          jestProcess.kill('SIGKILL');
        }
      }, 5000);
    }, TIMEOUT_MS);
    
    jestProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    
    jestProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    
    jestProcess.on('close', (code) => {
      clearTimeout(timeout);
      
      if (timedOut) {
        console.log(`❌ ${testFile} - TIMED OUT after ${TIMEOUT_MS/1000}s`);
        resolve({ file: testFile, success: false, reason: 'timeout', code: -1 });
      } else if (code === 0) {
        console.log(`✅ ${testFile} - PASSED`);
        resolve({ file: testFile, success: true, code: 0 });
      } else {
        console.log(`⚠️  ${testFile} - COMPLETED with code ${code} (may have test failures but didn't hang)`);
        resolve({ file: testFile, success: true, code: code, hasFailures: true });
      }
    });
    
    jestProcess.on('error', (error) => {
      clearTimeout(timeout);
      console.log(`❌ ${testFile} - ERROR:`, error.message);
      resolve({ file: testFile, success: false, reason: 'error', error });
    });
  });
}

async function main() {
  console.log('🚀 Testing hanging fixes...');
  console.log(`Testing ${PROBLEMATIC_TESTS.length} problematic test files\n`);
  
  const results = [];
  
  for (const testFile of PROBLEMATIC_TESTS) {
    const result = await runTestFile(testFile);
    results.push(result);
    console.log(''); // Add spacing between tests
  }
  
  // Summary
  console.log('📊 Test Results Summary:');
  console.log('========================');
  
  const successful = results.filter(r => r.success);
  const timedOut = results.filter(r => r.reason === 'timeout');
  const errors = results.filter(r => r.reason === 'error');
  const withFailures = results.filter(r => r.hasFailures);
  
  console.log(`✅ Completed without hanging: ${successful.length}/${results.length}`);
  console.log(`❌ Timed out (still hanging): ${timedOut.length}/${results.length}`);
  console.log(`🔥 Had errors: ${errors.length}/${results.length}`);
  console.log(`⚠️  Had test failures: ${withFailures.length}/${results.length}`);
  
  if (timedOut.length > 0) {
    console.log('\n🚨 Files still hanging:');
    timedOut.forEach(r => console.log(`  - ${r.file}`));
  }
  
  if (errors.length > 0) {
    console.log('\n💥 Files with errors:');
    errors.forEach(r => console.log(`  - ${r.file}: ${r.error?.message}`));
  }
  
  if (withFailures.length > 0) {
    console.log('\n⚠️  Files with test failures (but completed):');
    withFailures.forEach(r => console.log(`  - ${r.file} (exit code: ${r.code})`));
  }
  
  const hangingFixed = timedOut.length === 0;
  
  console.log('\n' + '='.repeat(50));
  if (hangingFixed) {
    console.log('🎉 SUCCESS: No tests are hanging anymore!');
    console.log('✅ All hanging tests have been fixed');
  } else {
    console.log('⚠️  PARTIAL SUCCESS: Some tests may still be hanging');
    console.log('💡 Check the timeout files above and apply additional fixes');
  }
  
  process.exit(hangingFixed ? 0 : 1);
}

if (require.main === module) {
  main().catch(console.error);
}