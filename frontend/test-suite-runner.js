#!/usr/bin/env node

const { spawn } = require('child_process');
const os = require('os');
const path = require('path');

// Test suite definitions with priority and resource allocation
const TEST_SUITES = {
  // Fast unit tests - can run many in parallel
  components: { priority: 1, weight: 0.8, timeout: 60 },
  hooks: { priority: 1, weight: 0.6, timeout: 30 },
  imports: { priority: 1, weight: 0.2, timeout: 20 },
  
  // Medium tests
  chat: { priority: 2, weight: 0.8, timeout: 60 },
  auth: { priority: 2, weight: 0.4, timeout: 40 },
  core: { priority: 2, weight: 0.4, timeout: 40 },
  
  // Slower integration tests
  'integration-basic': { priority: 3, weight: 0.5, timeout: 90 },
  'integration-advanced': { priority: 3, weight: 0.6, timeout: 120 },
  system: { priority: 3, weight: 0.4, timeout: 90 },
  
  // Heaviest tests - run fewer in parallel
  'integration-comprehensive': { priority: 4, weight: 0.8, timeout: 180 },
  'integration-critical': { priority: 4, weight: 0.8, timeout: 150 },
};

// Parse command line arguments
const args = process.argv.slice(2);
const options = {
  suites: [],
  parallel: true,
  maxParallel: Math.max(1, Math.floor(os.cpus().length * 0.75)),
  bail: false,
  silent: false,
  watch: false,
  coverage: false,
};

// Process arguments
for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  
  switch (arg) {
    case '--suite':
    case '-s':
      options.suites.push(args[++i]);
      break;
    case '--all':
      options.suites = Object.keys(TEST_SUITES);
      break;
    case '--sequential':
      options.parallel = false;
      break;
    case '--max-parallel':
      options.maxParallel = parseInt(args[++i], 10);
      break;
    case '--bail':
      options.bail = true;
      break;
    case '--silent':
      options.silent = true;
      break;
    case '--watch':
      options.watch = true;
      break;
    case '--coverage':
      options.coverage = true;
      break;
    case '--priority':
      const priorityLevel = parseInt(args[++i], 10);
      options.suites = Object.entries(TEST_SUITES)
        .filter(([_, config]) => config.priority <= priorityLevel)
        .map(([name]) => name);
      break;
    case '--help':
      printHelp();
      process.exit(0);
    default:
      if (TEST_SUITES[arg]) {
        options.suites.push(arg);
      }
  }
}

// Default to all suites if none specified
if (options.suites.length === 0) {
  options.suites = Object.keys(TEST_SUITES);
}

function printHelp() {
  console.log(`
Frontend Test Suite Runner

Usage: node test-suite-runner.js [options] [suite-names]

Options:
  --suite, -s <name>      Run specific test suite
  --all                   Run all test suites
  --priority <level>      Run suites up to priority level (1-4)
  --sequential            Run suites sequentially instead of parallel
  --max-parallel <n>      Maximum parallel suite executions
  --bail                  Stop on first test failure
  --silent                Minimal output
  --watch                 Watch mode
  --coverage              Generate coverage report
  --help                  Show this help

Available Suites:
${Object.entries(TEST_SUITES)
  .map(([name, config]) => `  ${name.padEnd(25)} (priority: ${config.priority}, weight: ${config.weight})`)
  .join('\n')}

Examples:
  # Run all component and hook tests in parallel
  node test-suite-runner.js components hooks
  
  # Run all priority 1 tests
  node test-suite-runner.js --priority 1
  
  # Run integration tests sequentially
  node test-suite-runner.js --sequential integration-basic integration-advanced
  
  # Run all tests with max 4 parallel
  node test-suite-runner.js --all --max-parallel 4
`);
}

// Run test suites
async function runTestSuites() {
  if (!options.silent) {
    console.log('🧪 Test Suite Runner');
    console.log('='.repeat(60));
    console.log(`Suites to run: ${options.suites.join(', ')}`);
    console.log(`Parallel mode: ${options.parallel}`);
    console.log(`Max parallel: ${options.maxParallel}`);
    console.log('='.repeat(60) + '\n');
  }
  
  const startTime = Date.now();
  const results = {};
  
  if (options.parallel) {
    // Group suites by priority
    const priorityGroups = {};
    options.suites.forEach(suite => {
      const priority = TEST_SUITES[suite].priority;
      if (!priorityGroups[priority]) {
        priorityGroups[priority] = [];
      }
      priorityGroups[priority].push(suite);
    });
    
    // Run each priority group
    for (const priority of Object.keys(priorityGroups).sort()) {
      const suites = priorityGroups[priority];
      if (!options.silent) {
        console.log(`\n🎯 Running Priority ${priority} suites: ${suites.join(', ')}\n`);
      }
      
      // Calculate parallel slots based on suite weights
      const chunks = [];
      let currentChunk = [];
      let currentWeight = 0;
      
      for (const suite of suites) {
        const weight = TEST_SUITES[suite].weight;
        if (currentWeight + weight > 1 && currentChunk.length > 0) {
          chunks.push(currentChunk);
          currentChunk = [suite];
          currentWeight = weight;
        } else {
          currentChunk.push(suite);
          currentWeight += weight;
        }
      }
      if (currentChunk.length > 0) {
        chunks.push(currentChunk);
      }
      
      // Run chunks in parallel
      for (const chunk of chunks) {
        const promises = chunk.map(suite => runSuite(suite));
        const chunkResults = await Promise.all(promises);
        chunkResults.forEach((result, i) => {
          results[chunk[i]] = result;
          if (options.bail && !result.success) {
            if (!options.silent) {
              console.log(`\n❌ Suite ${chunk[i]} failed. Bailing out.`);
            }
            process.exit(1);
          }
        });
      }
    }
  } else {
    // Sequential execution
    for (const suite of options.suites) {
      if (!options.silent) {
        console.log(`\n🎯 Running suite: ${suite}\n`);
      }
      results[suite] = await runSuite(suite);
      if (options.bail && !results[suite].success) {
        if (!options.silent) {
          console.log(`\n❌ Suite ${suite} failed. Bailing out.`);
        }
        process.exit(1);
      }
    }
  }
  
  // Print summary
  const duration = Date.now() - startTime;
  if (!options.silent) {
    console.log('\n' + '='.repeat(60));
    console.log('📊 FINAL SUMMARY');
    console.log('='.repeat(60));
  }
  
  let totalPassed = 0;
  let totalFailed = 0;
  
  Object.entries(results).forEach(([suite, result]) => {
    const status = result.success ? '✅' : '❌';
    if (!options.silent) {
      console.log(`${status} ${suite}: ${result.duration}ms`);
    }
    if (result.success) totalPassed++;
    else totalFailed++;
  });
  
  if (!options.silent) {
    console.log('='.repeat(60));
    console.log(`Total duration: ${(duration / 1000).toFixed(2)}s`);
    console.log(`Suites passed: ${totalPassed}/${options.suites.length}`);
    if (totalFailed > 0) {
      console.log(`Suites failed: ${totalFailed}`);
    }
    console.log('='.repeat(60) + '\n');
  }
  
  process.exit(totalFailed > 0 ? 1 : 0);
}

// Run individual test suite
function runSuite(suiteName) {
  return new Promise((resolve) => {
    const startTime = Date.now();
    const timeout = TEST_SUITES[suiteName].timeout * 1000;
    
    const args = [
      'run-jest.js',
      '--config', 'jest.config.suites.cjs',
      '--selectProjects', suiteName,
    ];
    
    if (options.silent) args.push('--silent');
    if (options.bail) args.push('--bail');
    if (options.watch) args.push('--watch');
    if (options.coverage) args.push('--coverage');
    
    const child = spawn('node', args, {
      stdio: options.silent ? 'pipe' : 'inherit',
      cwd: process.cwd(),
    });
    
    let killed = false;
    const timer = setTimeout(() => {
      if (!options.silent) {
        console.log(`\n⏱️ Suite ${suiteName} timed out after ${TEST_SUITES[suiteName].timeout}s`);
      }
      killed = true;
      child.kill('SIGTERM');
    }, timeout);
    
    child.on('exit', (code) => {
      clearTimeout(timer);
      const duration = Date.now() - startTime;
      resolve({
        success: code === 0 && !killed,
        duration,
        code,
        killed,
      });
    });
    
    child.on('error', (err) => {
      clearTimeout(timer);
      if (!options.silent) {
        console.log(`Error running suite ${suiteName}:`, err);
      }
      resolve({
        success: false,
        duration: Date.now() - startTime,
        error: err.message,
      });
    });
  });
}

// Run the test suites
runTestSuites().catch(err => {
  if (!options.silent) {
    console.log('Fatal error:', err);
  }
  process.exit(1);
});