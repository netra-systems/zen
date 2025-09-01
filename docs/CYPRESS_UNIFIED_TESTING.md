# Cypress Testing via Unified Test Runner

## Overview
Cypress E2E tests are fully integrated into the Unified Test Runner as a test category. This ensures consistent Docker management, service orchestration, and test reporting across all test types.

## Running Cypress Tests

### Basic Usage
```bash
# Run all Cypress tests
python tests/unified_test_runner.py --category cypress

# Run Cypress with other test categories
python tests/unified_test_runner.py --categories unit api cypress

# Run with real services (Docker Compose)
python tests/unified_test_runner.py --category cypress --real-services
```

### Advanced Options
```bash
# Run Cypress tests in headed mode (show browser)
python tests/unified_test_runner.py --category cypress --cypress-headed

# Use a different browser
python tests/unified_test_runner.py --category cypress --cypress-browser firefox

# Run with real LLM (automatically enabled for E2E)
python tests/unified_test_runner.py --category cypress --real-llm
```

## Integration Architecture

### Centralized Docker Management
- All test categories share the same `UnifiedDockerManager`
- Prevents service restart storms during parallel test execution
- Coordinates service lifecycle across test runs
- File-based locking ensures proper synchronization

### Service Dependencies
The unified test runner automatically manages these services for Cypress tests:
- **Backend API** (port 8000)
- **Frontend Dev Server** (port 3000)
- **PostgreSQL Database** (port 5432)
- **Redis Cache** (port 6379)
- **Auth Service** (port 8001)

### Test Categories
Cypress tests are part of the E2E test categories:
- `cypress`: Full Cypress test suite
- `e2e_critical`: Critical E2E paths including Cypress
- `e2e`: Full E2E suite with Cypress tests

## Configuration

### Environment Setup
```bash
# Ensure frontend dependencies are installed
cd frontend
npm install

# Return to project root
cd ..
```

### Docker Compose
The unified test runner uses `docker-compose.test.yml` by default:
```bash
# Start test environment manually (optional - runner handles this)
docker compose -f docker-compose.test.yml up -d

# Run tests
python tests/unified_test_runner.py --category cypress
```

## Test Organization

### Spec Patterns
Different test categories run different Cypress specs:
- `cypress`: All specs in `cypress/e2e/`
- `smoke`: Critical tests only (`critical-basic-flow.cy.ts`, `basic-ui-test.cy.ts`)
- Custom categories: Configured via `CypressConfigManager`

### Test Discovery
The unified test runner automatically discovers Cypress tests based on:
- File patterns in `cypress/e2e/`
- Category-specific configurations
- Test markers and tags

## Execution Modes

### Fast Feedback Mode
```bash
python tests/unified_test_runner.py --execution-mode fast_feedback
```
Runs quick smoke tests including critical Cypress paths.

### Full Layered Execution
```bash
python tests/unified_test_runner.py --execution-mode nightly
```
Runs all test layers including full Cypress suite.

### Background E2E
```bash
python tests/unified_test_runner.py --background-e2e
```
Runs Cypress tests in background mode for CI/CD pipelines.

## Error Handling

### Service Unavailable
If services aren't available, the runner will:
1. Attempt to start Docker Compose services
2. Wait for health checks
3. Provide clear error messages with remediation steps

### Common Issues

#### Docker Not Running
```
ERROR: Docker Desktop is not running
SOLUTION: Start Docker Desktop or ensure services are running locally
```

#### Services Not Healthy
```
ERROR: Required services not available
SOLUTION: Check docker-compose logs:
  docker compose -f docker-compose.test.yml logs
```

#### Cypress Not Installed
```
ERROR: Cypress not installed
SOLUTION: cd frontend && npm install
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Run Cypress Tests
  run: |
    python tests/unified_test_runner.py \
      --category cypress \
      --real-services \
      --timeout 3600
```

### Jenkins
```groovy
stage('Cypress Tests') {
    steps {
        sh 'python tests/unified_test_runner.py --category cypress'
    }
}
```

## Reporting

### Test Results
Results are integrated into the unified test report:
- Pass/fail status per spec
- Execution time
- Screenshot/video artifacts (if configured)
- Service health status

### Output Formats
```bash
# JSON output
python tests/unified_test_runner.py --category cypress --output-format json

# JUnit XML for CI
python tests/unified_test_runner.py --category cypress --junit-xml

# HTML report
python tests/unified_test_runner.py --category cypress --html-report
```

## Best Practices

1. **Always use the unified test runner** for Cypress tests
2. **Don't run standalone Cypress** - use the integrated approach
3. **Leverage shared Docker management** to prevent conflicts
4. **Use test categories** to organize test execution
5. **Enable real services** for E2E testing reliability

## Troubleshooting

### Debug Mode
```bash
# Verbose output
python tests/unified_test_runner.py --category cypress --verbose

# Debug Docker issues
python tests/unified_test_runner.py --category cypress --debug-docker
```

### Manual Service Management
```bash
# Check service status
docker compose -f docker-compose.test.yml ps

# View service logs
docker compose -f docker-compose.test.yml logs backend

# Restart services
docker compose -f docker-compose.test.yml restart
```

## Migration from Standalone

If you were using a standalone Cypress launcher:
1. Remove any `cypress_launcher.py` files
2. Update CI/CD scripts to use `unified_test_runner.py`
3. Migrate any custom configurations to test framework
4. Use `--category cypress` instead of direct Cypress commands

## Summary

Cypress testing is now fully integrated into the unified test runner infrastructure:
- **Single entry point**: `tests/unified_test_runner.py`
- **Centralized Docker management**: Shared across all test types
- **Consistent reporting**: Unified test results and metrics
- **Service orchestration**: Automatic dependency management
- **Parallel execution support**: Coordinated with other test categories

For more information, see the main [Unified Test Runner documentation](../tests/unified_test_runner.py).