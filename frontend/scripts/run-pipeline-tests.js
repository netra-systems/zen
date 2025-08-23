#!/usr/bin/env node

/**
 * Message Pipeline Test Runner
 * 
 * Comprehensive test execution script for the message pipeline test suite.
 * Provides different execution modes, performance monitoring, and detailed reporting.
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// Test configuration
const TEST_CONFIGS = {
  unit: {
    pattern: '__tests__/message-pipeline/*.test.tsx',
    description: 'Unit tests for individual components',
    timeout: 30000
  },
  integration: {
    pattern: '__tests__/message-pipeline/*integration*.test.tsx',
    description: 'Integration tests for complete pipeline',
    timeout: 60000
  },
  performance: {
    pattern: '__tests__/message-pipeline/*.test.tsx',
    testNamePattern: 'performance|memory|load|concurrent',
    description: 'Performance and load testing',
    timeout: 120000
  },
  errors: {
    pattern: '__tests__/message-pipeline/*Error*.test.tsx',
    description: 'Error handling and recovery tests',
    timeout: 45000
  },
  optimistic: {
    pattern: '__tests__/message-pipeline/*Optimistic*.test.tsx',
    description: 'Optimistic UI and reconciliation tests',
    timeout: 30000
  },
  edge: {
    pattern: '__tests__/message-pipeline/*Edge*.test.tsx',
    description: 'Edge cases and boundary conditions',
    timeout: 90000
  },
  all: {
    pattern: '__tests__/message-pipeline/',
    description: 'Complete message pipeline test suite',
    timeout: 300000
  }
};

// Command line argument parsing
const args = process.argv.slice(2);
const testType = args[0] || 'all';
const options = {
  coverage: args.includes('--coverage'),
  verbose: args.includes('--verbose'),
  watch: args.includes('--watch'),
  bail: args.includes('--bail'),
  silent: args.includes('--silent'),
  parallel: args.includes('--parallel'),
  updateSnapshot: args.includes('--updateSnapshot'),
  detectOpenHandles: args.includes('--detectOpenHandles'),
  forceExit: args.includes('--forceExit')
};

// Performance monitoring
class TestMetrics {
  constructor() {
    this.startTime = Date.now();
    this.memoryStart = process.memoryUsage();
  }

  getExecutionTime() {
    return Date.now() - this.startTime;
  }

  getMemoryUsage() {
    const current = process.memoryUsage();
    return {
      heapUsed: Math.round((current.heapUsed - this.memoryStart.heapUsed) / 1024 / 1024),
      heapTotal: Math.round((current.heapTotal - this.memoryStart.heapTotal) / 1024 / 1024),
      rss: Math.round((current.rss - this.memoryStart.rss) / 1024 / 1024)
    };
  }

  generateReport() {
    const executionTime = this.getExecutionTime();
    const memoryUsage = this.getMemoryUsage();
    
    return {
      executionTimeMs: executionTime,
      executionTimeFormatted: this.formatTime(executionTime),
      memoryUsageMB: memoryUsage,
      timestamp: new Date().toISOString(),
      nodeVersion: process.version,
      platform: os.platform(),
      cpus: os.cpus().length
    };
  }

  formatTime(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    const remainingMs = ms % 1000;

    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}.${Math.floor(remainingMs / 100)}s`;
    } else if (seconds > 0) {
      return `${seconds}.${Math.floor(remainingMs / 100)}s`;
    } else {
      return `${ms}ms`;
    }
  }
}

// Colored console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
  if (!options.silent) {
    console.log(colors[color] + message + colors.reset);
  }
}

function logError(message) {
  console.error(colors.red + message + colors.reset);
}

function logSuccess(message) {
  log(message, 'green');
}

function logWarning(message) {
  log(message, 'yellow');
}

function logInfo(message) {
  log(message, 'blue');
}

// Test execution
async function runTests(config, metrics) {
  return new Promise((resolve, reject) => {
    const jestArgs = [
      config.pattern,
      '--testTimeout=' + config.timeout
    ];

    // Add Jest options based on command line arguments
    if (config.testNamePattern) {
      jestArgs.push('--testNamePattern=' + config.testNamePattern);
    }
    
    if (options.coverage) {
      jestArgs.push('--coverage');
      jestArgs.push('--coverageReporters=text');
      jestArgs.push('--coverageReporters=lcov');
    }
    
    if (options.verbose) {
      jestArgs.push('--verbose');
    }
    
    if (options.watch) {
      jestArgs.push('--watch');
    }
    
    if (options.bail) {
      jestArgs.push('--bail');
    }
    
    if (options.parallel) {
      jestArgs.push('--maxWorkers=' + Math.max(1, os.cpus().length - 1));
    } else {
      jestArgs.push('--runInBand');
    }
    
    if (options.updateSnapshot) {
      jestArgs.push('--updateSnapshot');
    }
    
    if (options.detectOpenHandles) {
      jestArgs.push('--detectOpenHandles');
    }
    
    if (options.forceExit) {
      jestArgs.push('--forceExit');
    }

    // Additional Jest configuration for pipeline tests
    jestArgs.push('--setupFilesAfterEnv=<rootDir>/jest.setup.js');
    jestArgs.push('--testEnvironment=jsdom');
    jestArgs.push('--clearMocks');

    log(`\n${colors.bright}Running ${config.description}...${colors.reset}`);
    log(`Command: npx jest ${jestArgs.join(' ')}\n`, 'dim');

    const jest = spawn('npx', ['jest', ...jestArgs], {
      stdio: 'inherit',
      cwd: process.cwd(),
      env: {
        ...process.env,
        NODE_ENV: 'test',
        // Increase Node.js memory limit for large test suites
        NODE_OPTIONS: '--max-old-space-size=4096'
      }
    });

    jest.on('close', (code) => {
      if (code === 0) {
        logSuccess(`✓ ${config.description} completed successfully`);
        resolve(code);
      } else {
        logError(`✗ ${config.description} failed with exit code ${code}`);
        reject(new Error(`Tests failed with exit code ${code}`));
      }
    });

    jest.on('error', (error) => {
      logError(`Failed to start Jest: ${error.message}`);
      reject(error);
    });
  });
}

// Report generation
function generateTestReport(metrics, testType, success) {
  const report = {
    testSuite: 'Message Pipeline Tests',
    testType: testType,
    success: success,
    metrics: metrics.generateReport(),
    timestamp: new Date().toISOString(),
    environment: {
      nodeVersion: process.version,
      platform: process.platform,
      arch: process.arch,
      cpuCount: os.cpus().length,
      totalMemoryGB: Math.round(os.totalmem() / 1024 / 1024 / 1024)
    }
  };

  // Save report to file
  const reportDir = path.join(process.cwd(), 'test-reports');
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  const reportFile = path.join(
    reportDir,
    `pipeline-test-report-${testType}-${Date.now()}.json`
  );

  try {
    fs.writeFileSync(reportFile, JSON.stringify(report, null, 2));
    logInfo(`Test report saved: ${reportFile}`);
  } catch (error) {
    logWarning(`Failed to save test report: ${error.message}`);
  }

  return report;
}

// Display help information
function showHelp() {
  log('\n' + colors.bright + 'Message Pipeline Test Runner' + colors.reset);
  log('Comprehensive test execution for the message pipeline system\n');
  
  log(colors.bright + 'Usage:' + colors.reset);
  log('  node scripts/run-pipeline-tests.js [test-type] [options]\n');
  
  log(colors.bright + 'Test Types:' + colors.reset);
  Object.entries(TEST_CONFIGS).forEach(([key, config]) => {
    log(`  ${colors.cyan}${key.padEnd(12)}${colors.reset} ${config.description}`);
  });
  
  log('\n' + colors.bright + 'Options:' + colors.reset);
  log(`  ${colors.cyan}--coverage${colors.reset}        Generate code coverage report`);
  log(`  ${colors.cyan}--verbose${colors.reset}         Enable verbose test output`);
  log(`  ${colors.cyan}--watch${colors.reset}           Run tests in watch mode`);
  log(`  ${colors.cyan}--bail${colors.reset}            Stop on first test failure`);
  log(`  ${colors.cyan}--silent${colors.reset}          Suppress runner output`);
  log(`  ${colors.cyan}--parallel${colors.reset}        Run tests in parallel`);
  log(`  ${colors.cyan}--updateSnapshot${colors.reset}  Update test snapshots`);
  log(`  ${colors.cyan}--detectOpenHandles${colors.reset} Detect memory leaks`);
  log(`  ${colors.cyan}--forceExit${colors.reset}       Force exit after tests`);
  
  log('\n' + colors.bright + 'Examples:' + colors.reset);
  log('  node scripts/run-pipeline-tests.js all --coverage');
  log('  node scripts/run-pipeline-tests.js performance --verbose');
  log('  node scripts/run-pipeline-tests.js unit --watch');
  log('  node scripts/run-pipeline-tests.js errors --bail\n');
}

// Main execution
async function main() {
  if (args.includes('--help') || args.includes('-h')) {
    showHelp();
    return;
  }

  if (!TEST_CONFIGS[testType]) {
    logError(`Unknown test type: ${testType}`);
    logError('Use --help to see available test types');
    process.exit(1);
  }

  const metrics = new TestMetrics();
  const config = TEST_CONFIGS[testType];

  log('\n' + colors.bright + '🚀 Message Pipeline Test Runner' + colors.reset);
  log('═'.repeat(50));
  
  logInfo(`Test Type: ${testType}`);
  logInfo(`Description: ${config.description}`);
  logInfo(`Pattern: ${config.pattern}`);
  if (config.testNamePattern) {
    logInfo(`Name Pattern: ${config.testNamePattern}`);
  }
  logInfo(`Timeout: ${config.timeout}ms`);
  logInfo(`Parallel: ${options.parallel ? 'Yes' : 'No'}`);
  logInfo(`Coverage: ${options.coverage ? 'Yes' : 'No'}`);
  
  log('═'.repeat(50));

  try {
    await runTests(config, metrics);
    
    const report = generateTestReport(metrics, testType, true);
    
    log('\n' + colors.bright + '📊 Test Execution Summary' + colors.reset);
    log('═'.repeat(50));
    logSuccess(`✓ Tests completed successfully`);
    logInfo(`Execution Time: ${report.metrics.executionTimeFormatted}`);
    logInfo(`Memory Usage: ${report.metrics.memoryUsageMB.heapUsed}MB heap, ${report.metrics.memoryUsageMB.rss}MB RSS`);
    logInfo(`Platform: ${report.environment.platform} (${report.environment.arch})`);
    logInfo(`Node.js: ${report.environment.nodeVersion}`);
    log('═'.repeat(50) + '\n');
    
  } catch (error) {
    const report = generateTestReport(metrics, testType, false);
    
    log('\n' + colors.bright + '❌ Test Execution Failed' + colors.reset);
    log('═'.repeat(50));
    logError(`Tests failed: ${error.message}`);
    logInfo(`Execution Time: ${report.metrics.executionTimeFormatted}`);
    logInfo(`Memory Usage: ${report.metrics.memoryUsageMB.heapUsed}MB heap, ${report.metrics.memoryUsageMB.rss}MB RSS`);
    log('═'.repeat(50) + '\n');
    
    process.exit(1);
  }
}

// Handle process signals
process.on('SIGINT', () => {
  logWarning('\nReceived SIGINT, shutting down gracefully...');
  process.exit(130);
});

process.on('SIGTERM', () => {
  logWarning('\nReceived SIGTERM, shutting down gracefully...');
  process.exit(143);
});

process.on('unhandledRejection', (reason, promise) => {
  logError(`Unhandled Rejection at: ${promise}, reason: ${reason}`);
  process.exit(1);
});

// Execute main function
main().catch((error) => {
  logError(`Unexpected error: ${error.message}`);
  console.error(error);
  process.exit(1);
});