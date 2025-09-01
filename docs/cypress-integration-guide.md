# Cypress E2E Test Integration Guide

## Overview

Cypress E2E tests are now fully integrated into the unified test runner, providing seamless execution of 95+ frontend E2E tests alongside other test categories. This integration leverages existing Docker service management and provides comprehensive test execution capabilities.

## Quick Start

### Basic Execution

```bash
# Run all Cypress tests with default settings
python unified_test_runner.py --category cypress

# Run Cypress tests with browser UI visible (debugging)
python unified_test_runner.py --category cypress --cypress-headed

# Run with a specific browser
python unified_test_runner.py --category cypress --cypress-browser firefox

# Run with real services (ensures Docker containers are started)
python unified_test_runner.py --category cypress --real-services
```

### Advanced Execution

```bash
# Run specific Cypress test patterns
python unified_test_runner.py --category cypress --pattern "auth"

# Run with verbose output
python unified_test_runner.py --category cypress --verbose

# Run with fail-fast mode
python unified_test_runner.py --category cypress --fast-fail

# Combine with other test categories
python unified_test_runner.py --categories integration api cypress
```

## Architecture

### Integration Points

The Cypress integration seamlessly connects with existing infrastructure:

1. **Unified Test Runner** (`tests/unified_test_runner.py`)
   - Recognizes "cypress" as a test category
   - Manages execution lifecycle
   - Aggregates results with other test categories

2. **Cypress Runner** (`test_framework/cypress_runner.py`)
   - Main orchestration class
   - Handles service dependencies
   - Executes Cypress tests
   - Processes results

3. **Service Management** (`test_framework/cypress/service_manager.py`)
   - Integrates with `dev_launcher` Docker services
   - Ensures all services are healthy before tests
   - Provides service URL discovery

4. **Configuration** (`test_framework/cypress/config_manager.py`)
   - Generates dynamic Cypress configuration
   - Manages environment-specific settings
   - Handles browser and execution options

## Service Dependencies

### Required Services

Cypress tests require the following services to be running:

| Service | Port | Health Check | Purpose |
|---------|------|--------------|---------|
| Backend | 8000 | `/api/health` | Main API server |
| Frontend | 3000 | `/` | Next.js application |
| PostgreSQL | 5432 | Connection test | Primary database |
| Redis | 6379 | PING command | Cache and sessions |
| ClickHouse | 8123 | `/ping` | Analytics (optional) |

### Automatic Service Management

The integration automatically:
1. Checks if required services are running
2. Starts Docker containers if needed (when `--real-services` is used)
3. Waits for all services to be healthy
4. Provides service URLs to Cypress configuration

## Test Organization

### Test Categories

Cypress tests are organized into logical groups:

```
frontend/cypress/e2e/
├── critical-*.cy.ts        # Critical user flows
├── auth-*.cy.ts           # Authentication tests
├── websocket-*.cy.ts      # WebSocket functionality
├── file-upload-*.cy.ts    # File upload features
├── performance-*.cy.ts    # Performance metrics
├── state-sync-*.cy.ts     # State synchronization
├── thread-*.cy.ts         # Thread management
├── enterprise-*.cy.ts     # Enterprise features
├── roi-calculator-*.cy.ts # ROI calculator
└── demo-*.cy.ts          # Demo and examples
```

### Running Specific Test Groups

```bash
# Run only critical tests
python unified_test_runner.py --category cypress --pattern "critical"

# Run authentication tests
python unified_test_runner.py --category cypress --pattern "auth"

# Run WebSocket tests
python unified_test_runner.py --category cypress --pattern "websocket"
```

## Configuration

### Category Configuration

The cypress category is configured in `test_framework/config/categories.yaml`:

```yaml
cypress:
  description: Cypress E2E tests with full service integration
  priority: MEDIUM
  timeout_seconds: 1800  # 30 minutes
  requires_real_services: true
  requires_frontend: true
  requires_backend: true
  requires_database: true
  parallel_safe: false  # Run serially to avoid conflicts
```

### Browser Options

Supported browsers:
- **chrome** (default) - Best performance and compatibility
- **firefox** - Alternative browser testing
- **edge** - Microsoft Edge testing
- **electron** - Lightweight, headless-optimized

### Timeout Configuration

Default timeouts (configurable):
- Service startup: 300 seconds
- Test execution: 60 seconds per test
- Page load: 30 seconds
- API requests: 10 seconds

## Development Workflow

### Local Development

1. **Start services manually** (if preferred):
   ```bash
   # Start all services with dev launcher
   python scripts/dev_launcher.py
   
   # In another terminal, run Cypress tests
   python unified_test_runner.py --category cypress
   ```

2. **Let the runner manage services**:
   ```bash
   # Automatically starts required services
   python unified_test_runner.py --category cypress --real-services
   ```

3. **Debug with headed mode**:
   ```bash
   # Shows browser UI for debugging
   python unified_test_runner.py --category cypress --cypress-headed
   ```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Run E2E Tests
  run: |
    # Start services in background
    python scripts/dev_launcher.py &
    sleep 30  # Wait for services
    
    # Run Cypress tests
    python unified_test_runner.py --category cypress --fast-fail
```

## Results and Reporting

### Result Format

Cypress results are converted to the unified test runner format:

```json
{
  "success": true,
  "duration": 245.3,
  "test_counts": {
    "total": 95,
    "passed": 92,
    "failed": 2,
    "skipped": 1
  },
  "errors": [],
  "artifacts": {
    "screenshots": ["cypress/screenshots/..."],
    "videos": ["cypress/videos/..."]
  }
}
```

### Viewing Results

Results are displayed in the terminal with:
- Test counts and success rate
- Execution time
- Failed test details
- Screenshot/video paths (if failures occur)

## Troubleshooting

### Common Issues

1. **Services not starting**
   - Check Docker is running: `docker info`
   - Verify ports are available: `netstat -an | grep -E "3000|8000"`
   - Try manual service start: `python scripts/dev_launcher.py`

2. **Browser launch failures**
   - Ensure browser is installed
   - Try different browser: `--cypress-browser electron`
   - Check system resources (Cypress needs ~512MB per browser)

3. **Test timeouts**
   - Increase timeout in configuration
   - Check service health: `curl http://localhost:8000/api/health`
   - Review network connectivity

4. **Flaky tests**
   - The integration includes automatic retry (2 attempts by default)
   - Use headed mode to debug: `--cypress-headed`
   - Check for race conditions in async operations

### Debug Commands

```bash
# Check if Cypress is installed
cd frontend && npx cypress verify

# Run Cypress directly (bypass unified runner)
cd frontend && npx cypress run

# Check service health
curl http://localhost:8000/api/health
curl http://localhost:3000/

# View Cypress configuration
cd frontend && npx cypress info
```

## Performance Optimization

### Execution Speed

- **Headless mode**: Default, fastest execution
- **Parallel execution**: Coming soon (currently serial)
- **Selective testing**: Use `--pattern` to run subsets
- **Resource management**: Automatic memory/CPU monitoring

### Best Practices

1. **Service Reuse**: Services stay running between test runs
2. **Container Caching**: Docker containers are reused when possible
3. **Test Isolation**: Each test file runs in a fresh browser context
4. **Retry Strategy**: Automatic retry for transient failures

## Migration from Standalone Cypress

If you were previously running Cypress tests standalone:

### Before (Standalone)
```bash
cd frontend
npm run dev &  # Start frontend
cd ../netra_backend
python app/main.py &  # Start backend
cd ../frontend
npm run cypress:open
```

### After (Integrated)
```bash
# All-in-one command
python unified_test_runner.py --category cypress --real-services
```

## Future Enhancements

### Planned Features

1. **Parallel Execution**: Run multiple spec files concurrently
2. **Cloud Recording**: Cypress Dashboard integration
3. **Visual Testing**: Screenshot comparison
4. **Performance Metrics**: Detailed timing analysis
5. **Custom Reporters**: Slack, email notifications
6. **Test Sharding**: Distribute tests across multiple machines

## API Reference

### Command Line Options

```bash
python unified_test_runner.py --category cypress [OPTIONS]

Options:
  --cypress-headed              Run with browser UI visible
  --cypress-browser BROWSER     Browser choice (chrome|firefox|edge|electron)
  --pattern PATTERN            Run specific test patterns
  --real-services              Ensure Docker services are started
  --verbose                    Detailed output
  --fast-fail                  Stop on first failure
  --env ENV                    Environment (dev|staging|prod)
  --timeout SECONDS            Overall execution timeout
```

### Python API

```python
from test_framework.cypress_runner import CypressTestRunner
from test_framework.cypress.config_manager import CypressConfig

# Create runner
config = CypressConfig(
    browser="chrome",
    headed=False,
    timeout=60
)
runner = CypressTestRunner(project_root, config)

# Run tests
results = await runner.run_tests(
    pattern="auth",
    headed=True
)

# Check results
if results.success:
    print(f"All {results.passed_tests} tests passed!")
else:
    print(f"Failed: {results.failed_tests}")
```

## Support

### Resources

- **Cypress Documentation**: https://docs.cypress.io
- **Test Files**: `frontend/cypress/e2e/`
- **Configuration**: `test_framework/config/categories.yaml`
- **Runner Code**: `test_framework/cypress_runner.py`

### Getting Help

1. Check this guide for common issues
2. Review test output for specific errors
3. Enable verbose mode for detailed debugging
4. Check service logs: `docker logs netra-dev-*`

## Summary

The Cypress E2E test integration provides:

✅ **Seamless Integration**: Works with unified test runner  
✅ **Service Management**: Automatic Docker container handling  
✅ **Flexible Execution**: Multiple browsers, headed/headless modes  
✅ **Comprehensive Testing**: 95+ tests covering all features  
✅ **Developer Friendly**: Simple commands, good debugging  
✅ **CI/CD Ready**: Designed for automation pipelines  

Run `python unified_test_runner.py --category cypress` to start testing!