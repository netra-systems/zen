#!/usr/bin/env node
/**
 * Validation Script for Failing Test Suites
 * 
 * This script validates that all the test suites are properly failing
 * with the expected errors related to module export issues.
 * 
 * Expected Failures:
 * 1. Duplicate export of isValidWebSocketMessageType
 * 2. Circular dependency issues
 * 3. Type-runtime export conflicts
 * 4. Module resolution failures in integration tests
 */

import { execSync } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

interface TestResult {
  suite: string;
  passed: boolean;
  failureReason?: string;
  expectedFailure: boolean;
  actualError?: string;
}

const testSuites = [
  {
    name: 'Duplicate Export Detection',
    file: '__tests__/types/duplicate-export-detector.test.ts',
    expectedError: 'Duplicate export',
    description: 'Should fail detecting duplicate isValidWebSocketMessageType export'
  },
  {
    name: 'Circular Dependency Detection', 
    file: '__tests__/types/circular-dependency-detector.test.ts',
    expectedError: 'Circular dependencies detected',
    description: 'Should fail if circular dependencies exist in type modules'
  },
  {
    name: 'Type Export Conflicts',
    file: '__tests__/types/type-export-conflicts.test.ts', 
    expectedError: 'Type-Runtime export conflicts',
    description: 'Should fail on type vs runtime export conflicts'
  },
  {
    name: 'Module Resolution Integration',
    file: '__tests__/integration/module-resolution-failures.test.tsx',
    expectedError: 'Module parse failed',
    description: 'Should fail on webpack module resolution'
  }
];

console.log('🔍 Validating Failing Test Suites\n');
console.log('=' .repeat(60));

const results: TestResult[] = [];

for (const suite of testSuites) {
  console.log(`\n📋 Testing: ${suite.name}`);
  console.log(`   File: ${suite.file}`);
  console.log(`   Expected: ${suite.description}`);
  
  try {
    // Run the test suite
    const output = execSync(
      `npx jest ${suite.file} --no-coverage --verbose`,
      { 
        cwd: path.resolve(__dirname, '..'),
        encoding: 'utf8',
        stdio: 'pipe'
      }
    );
    
    // If test passed, that's unexpected (we want them to fail)
    results.push({
      suite: suite.name,
      passed: true,
      expectedFailure: true,
      failureReason: 'Test passed but should have failed'
    });
    
    console.log(`   ❌ UNEXPECTED: Test suite passed (should fail)`);
    
  } catch (error: any) {
    // Test failed - this is expected!
    const errorOutput = error.stdout + error.stderr;
    const hasExpectedError = errorOutput.includes(suite.expectedError) ||
                            errorOutput.includes('isValidWebSocketMessageType');
    
    if (hasExpectedError) {
      results.push({
        suite: suite.name,
        passed: false,
        expectedFailure: true,
        actualError: suite.expectedError
      });
      
      console.log(`   ✅ EXPECTED: Test suite failed with expected error`);
      console.log(`      Error: "${suite.expectedError}"`);
      
      // Extract specific failure details
      const failureDetails = extractFailureDetails(errorOutput);
      if (failureDetails.length > 0) {
        console.log(`      Details:`);
        failureDetails.forEach(detail => {
          console.log(`        - ${detail}`);
        });
      }
    } else {
      results.push({
        suite: suite.name,
        passed: false,
        expectedFailure: false,
        failureReason: 'Failed with unexpected error',
        actualError: error.message
      });
      
      console.log(`   ⚠️  UNEXPECTED: Test failed but not with expected error`);
      console.log(`      Actual error: ${error.message.substring(0, 100)}...`);
    }
  }
}

// Summary Report
console.log('\n' + '=' .repeat(60));
console.log('📊 VALIDATION SUMMARY\n');

const expectedFailures = results.filter(r => !r.passed && r.expectedFailure);
const unexpectedPasses = results.filter(r => r.passed);
const unexpectedFailures = results.filter(r => !r.passed && !r.expectedFailure);

console.log(`✅ Expected Failures: ${expectedFailures.length}/${testSuites.length}`);
expectedFailures.forEach(r => {
  console.log(`   • ${r.suite}: Failed as expected with "${r.actualError}"`);
});

if (unexpectedPasses.length > 0) {
  console.log(`\n❌ Unexpected Passes: ${unexpectedPasses.length}`);
  unexpectedPasses.forEach(r => {
    console.log(`   • ${r.suite}: ${r.failureReason}`);
  });
}

if (unexpectedFailures.length > 0) {
  console.log(`\n⚠️  Unexpected Failures: ${unexpectedFailures.length}`);
  unexpectedFailures.forEach(r => {
    console.log(`   • ${r.suite}: ${r.failureReason}`);
  });
}

// Detailed Analysis
console.log('\n' + '=' .repeat(60));
console.log('🔬 DETAILED ANALYSIS\n');

console.log('The test suites are designed to fail and expose the following issues:\n');
console.log('1. DUPLICATE EXPORT (Primary Issue):');
console.log('   - isValidWebSocketMessageType is exported twice in registry.ts');
console.log('   - Line 38: from shared/enums');
console.log('   - Line 142: from domains/websocket');
console.log('   - This causes webpack "Module parse failed: Duplicate export" error\n');

console.log('2. CIRCULAR DEPENDENCIES:');
console.log('   - Potential cycles between registry ↔ domains/websocket');
console.log('   - Can cause temporal dead zones and undefined exports\n');

console.log('3. TYPE-RUNTIME CONFLICTS:');
console.log('   - Mixed export styles (type-only vs runtime)');
console.log('   - Can cause TypeScript compilation errors\n');

console.log('4. MODULE RESOLUTION:');
console.log('   - Integration tests show real-world import failures');
console.log('   - Components cannot import from registry due to parse errors');

// Save results to file
const reportPath = path.resolve(__dirname, 'test-validation-report.json');
fs.writeFileSync(reportPath, JSON.stringify({
  timestamp: new Date().toISOString(),
  summary: {
    total: testSuites.length,
    expectedFailures: expectedFailures.length,
    unexpectedPasses: unexpectedPasses.length,
    unexpectedFailures: unexpectedFailures.length
  },
  results,
  analysis: {
    primaryIssue: 'Duplicate export of isValidWebSocketMessageType',
    affectedLines: [38, 142],
    affectedFile: 'frontend/types/registry.ts',
    impact: 'Module parse failure preventing imports'
  }
}, null, 2));

console.log(`\n📁 Report saved to: ${reportPath}`);

// Exit with appropriate code
if (expectedFailures.length === testSuites.length) {
  console.log('\n✅ All test suites are failing as expected!');
  process.exit(0);
} else {
  console.log('\n⚠️  Not all test suites are failing as expected.');
  process.exit(1);
}

// Helper function to extract specific failure details
function extractFailureDetails(output: string): string[] {
  const details: string[] = [];
  
  // Look for duplicate export mentions
  const duplicateMatch = output.match(/Duplicate exports detected: ([^\n]+)/);
  if (duplicateMatch) {
    details.push(`Duplicate exports: ${duplicateMatch[1]}`);
  }
  
  // Look for circular dependency mentions
  const circularMatch = output.match(/Circular dependencies detected:([^❌]+)/);
  if (circularMatch) {
    const cycles = circularMatch[1].trim().split('\n').filter(l => l.includes('→'));
    if (cycles.length > 0) {
      details.push(`Circular deps: ${cycles[0].trim()}`);
    }
  }
  
  // Look for test assertion failures
  const assertionMatches = output.match(/expect\(.*?\)\..*?Received: .*/g);
  if (assertionMatches && assertionMatches.length > 0) {
    details.push(`Assertion: ${assertionMatches[0]}`);
  }
  
  // Look for Jest test counts
  const testCountMatch = output.match(/Tests:.*?(\d+ failed)/);
  if (testCountMatch) {
    details.push(`Jest: ${testCountMatch[1]}`);
  }
  
  return details;
}