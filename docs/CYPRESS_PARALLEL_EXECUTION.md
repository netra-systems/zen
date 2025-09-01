# Cypress Parallel Test Execution Guide

## Overview
This guide documents the parallel execution system for Cypress tests, designed to significantly reduce test execution time while maintaining reliability through proper timeout management.

## Key Features
- **Parallel Worker Execution**: Run tests across 2-8 workers simultaneously
- **Smart Test Distribution**: Load-balanced test splitting across workers
- **Timeout Management**: Individual test timeouts with overall suite timeout (1 hour default)
- **Worker Isolation**: Each worker has separate cache, screenshots, and downloads folders
- **Real-time Progress**: Live progress reporting from all workers
- **Failure Tracking**: Detailed reporting of failures, timeouts, and skipped tests

## Quick Start

### Basic Parallel Execution
```bash
# Run with default 4 workers
npm run cypress:parallel

# Run with specific number of workers
npm run cypress:parallel:2   # 2 workers
npm run cypress:parallel:4   # 4 workers  
npm run cypress:parallel:8   # 8 workers
```

### Execution Modes
```bash
# Quick validation (15 minute timeout, 2 minute per test)
npm run cypress:parallel:quick

# Full test suite (1 hour timeout, 5 minute per test)
npm run cypress:parallel:full

# Show browser (headed mode)
npm run cypress:parallel:headed

# Use different browser
npm run cypress:parallel:firefox
```

## Configuration

### Timeout Settings
The parallel runner uses a two-tier timeout system:

1. **Individual Test Timeout**: Maximum time for a single test file
   - Default: 300 seconds (5 minutes)
   - Quick mode: 120 seconds (2 minutes)
   - Configurable via `--timeout` flag

2. **Suite Timeout**: Maximum time for entire test suite
   - Default: 3600 seconds (1 hour)
   - Quick mode: 900 seconds (15 minutes)
   - Ensures tests don't run indefinitely

### Environment Variables
```bash
# Configure via environment variables
CYPRESS_WORKERS=6 npm run cypress:parallel
CYPRESS_TEST_TIMEOUT=180 npm run cypress:parallel
CYPRESS_SUITE_TIMEOUT=1800 npm run cypress:parallel
CYPRESS_BROWSER=firefox npm run cypress:parallel
CYPRESS_HEADED=true npm run cypress:parallel
```

### Command Line Options
```bash
# Using the Node.js runner directly
node cypress-parallel.js --workers 6 --timeout 180 --suite-timeout 1800

# Using the Python runner
python ../scripts/cypress_parallel_runner.py --workers 6 --test-timeout 180 --suite-timeout 1800
```

## Architecture

### Test Discovery and Distribution
1. **Discovery**: Automatically finds all `*.cy.{js,ts,jsx,tsx}` files in `cypress/e2e/`
2. **Load Estimation**: Estimates test duration based on file size and complexity
3. **Load Balancing**: Distributes tests to minimize total execution time
4. **Worker Assignment**: Each test is assigned to a specific worker

### Worker Isolation
Each worker runs with:
- Unique `CYPRESS_WORKER_ID` environment variable
- Separate screenshot folder: `cypress/screenshots/worker-{id}`
- Separate video folder: `cypress/videos/worker-{id}`
- Separate downloads folder: `cypress/downloads/worker-{id}`
- Independent Cypress cache to avoid conflicts

### Parallel Configuration File
The `cypress.parallel.config.ts` file provides:
- Extended timeouts for parallel execution
- Memory management optimizations
- Worker-specific folder configuration
- Test isolation settings
- Minimal retries to save time

## Usage Examples

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Run Cypress Tests in Parallel
  run: |
    npm run cypress:parallel:8
  timeout-minutes: 60
  env:
    CYPRESS_SUITE_TIMEOUT: 3600
    CYPRESS_TEST_TIMEOUT: 300
```

### Development Workflow
```bash
# Quick smoke test during development
npm run cypress:parallel:quick

# Full test before commit
npm run cypress:parallel:4

# Debug specific tests
CYPRESS_HEADED=true npm run cypress:parallel:2
```

### Performance Testing
```bash
# Maximum parallelization for performance testing
npm run cypress:parallel:8 -- --suite-timeout 7200

# Generate detailed report
python ../scripts/cypress_parallel_runner.py --workers 8 --report cypress-report.json
```

## Monitoring and Reporting

### Real-time Progress
The runner shows:
- Worker status and assigned tests
- Test execution progress per worker
- Pass/fail status in real-time
- Duration for each completed test

### Final Summary
After execution, you'll see:
- Total tests run
- Pass/fail/timeout/skip counts
- Total execution time
- Average time per test
- Worker utilization

### JSON Report
Results are saved to `cypress/parallel-results.json`:
```json
{
  "timestamp": "2025-01-30T10:00:00Z",
  "config": {
    "workers": 4,
    "testTimeout": 300,
    "suiteTimeout": 3600
  },
  "summary": {
    "totalTests": 90,
    "passed": 85,
    "failed": 3,
    "skipped": 2,
    "duration": 900.5
  },
  "workers": [...]
}
```

## Troubleshooting

### Common Issues

#### Tests Timing Out
- Increase individual test timeout: `--timeout 600`
- Check for resource contention between workers
- Reduce number of workers if system resources are limited

#### Worker Conflicts
- Ensure backend services can handle concurrent connections
- Check that test data doesn't conflict between workers
- Verify worker isolation folders are created properly

#### Memory Issues
- Reduce workers: `--workers 2`
- Enable memory management in config
- Clear Cypress cache: `npx cypress cache clear`

### Debug Mode
```bash
# Run with verbose output
CYPRESS_DEBUG=* npm run cypress:parallel:2

# Run single worker for debugging
npm run cypress:run -- --spec "cypress/e2e/specific-test.cy.ts"
```

## Best Practices

### Optimal Worker Count
- **Local Development**: 2-4 workers (based on CPU cores)
- **CI/CD**: 4-8 workers (based on available resources)
- **Rule of thumb**: Number of CPU cores - 1

### Test Design for Parallelization
1. **Independent Tests**: Ensure tests don't depend on each other
2. **Isolated State**: Each test should set up its own state
3. **Clean Teardown**: Tests should clean up after themselves
4. **Avoid Shared Resources**: Minimize contention for shared resources

### Timeout Guidelines
- **Unit-like tests**: 60-120 seconds
- **Integration tests**: 180-300 seconds
- **E2E workflows**: 300-600 seconds
- **Suite timeout**: 1.5x expected total time

## Performance Metrics

### Expected Improvements
With proper parallelization:
- **2 workers**: ~40-45% reduction in execution time
- **4 workers**: ~65-70% reduction in execution time
- **8 workers**: ~75-80% reduction in execution time

### Monitoring Performance
```bash
# Compare sequential vs parallel
time npm run cypress:run  # Sequential
time npm run cypress:parallel:4  # Parallel

# Generate performance report
python ../scripts/cypress_parallel_runner.py --workers 4 --report perf-report.json
```

## Integration with Unified Test Runner

The parallel Cypress runner can be integrated with the unified test runner:

```bash
# Run via unified test runner
python tests/unified_test_runner.py --category cypress --cypress-parallel --cypress-workers 4

# With other test categories
python tests/unified_test_runner.py --categories unit cypress --cypress-parallel
```

## Advanced Configuration

### Custom Test Splitting
```javascript
// In cypress-parallel.js, modify the splitTests function
function splitTests(tests, numWorkers) {
  // Custom logic for test distribution
  // e.g., group by feature area, priority, or historical duration
}
```

### Dynamic Worker Scaling
```bash
# Scale workers based on available resources
WORKERS=$(nproc --ignore=1)  # Linux/Mac
npm run cypress:parallel -- --workers $WORKERS
```

### Retry Failed Tests
```bash
# Run failed tests from previous run
node cypress-parallel.js --spec "cypress/e2e/failed-*.cy.ts" --workers 2
```

## Summary

The Cypress parallel execution system provides:
- **Significant time savings** through parallel execution
- **Robust timeout management** preventing hanging tests
- **Worker isolation** ensuring test independence
- **Detailed reporting** for debugging and analysis
- **Flexible configuration** for different scenarios

Use parallel execution for:
- Faster CI/CD pipelines
- Quick feedback during development
- Comprehensive testing before releases
- Performance benchmarking