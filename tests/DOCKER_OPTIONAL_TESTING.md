# Docker-Optional Test Execution

## Overview
The test runner now intelligently determines when Docker is required based on test categories, allowing faster execution for tests that don't need external services.

## Key Improvements

### 1. Automatic Docker Detection
The test runner automatically determines if Docker is needed based on:
- Test category requirements
- Environment settings
- Command-line flags

### 2. Explicit Control Options
- `--no-docker` / `--skip-docker` flag to explicitly disable Docker
- `TEST_NO_DOCKER=true` environment variable for CI/CD pipelines
- `--real-services` flag to explicitly require Docker

### 3. Faster Test Execution
Tests that don't need Docker run significantly faster:
- No Docker initialization overhead
- No container startup time
- No cleanup operations
- Works on systems without Docker installed

## Test Categories

### Docker NOT Required
These categories can run without Docker:
- **smoke** - Quick validation tests for pre-commit checks
- **unit** - Unit tests for isolated components
- **frontend** - Frontend component tests (React/UI)
- **agent** - Agent tests (can use mock LLM)
- **performance** - Performance tests (can use mock data)
- **security** - Security static analysis tests
- **startup** - Service startup tests

### Docker REQUIRED
These categories need Docker for real services:
- **e2e** - End-to-end user journey tests
- **e2e_critical** - Critical E2E tests
- **cypress** - Cypress E2E tests with full integration
- **database** - Database tests (need PostgreSQL)
- **api** - API endpoint tests (need backend services)
- **websocket** - WebSocket communication tests
- **integration** - Integration tests (need multiple services)
- **post_deployment** - Post-deployment validation tests

## Usage Examples

### 1. Run Unit Tests Without Docker
```bash
# Explicitly disable Docker
python tests/unified_test_runner.py --category unit --no-docker

# Auto-detection (Docker not needed for unit tests)
python tests/unified_test_runner.py --category unit
```

### 2. Run Smoke Tests for Pre-commit
```bash
# Fast pre-commit validation without Docker
python tests/unified_test_runner.py --category smoke --no-docker --fast-fail
```

### 3. CI/CD Pipeline Configuration
```bash
# Set environment variable to skip Docker
export TEST_NO_DOCKER=true
python tests/unified_test_runner.py --category unit

# Or use the flag
python tests/unified_test_runner.py --category unit --skip-docker
```

### 4. Run Tests That Need Docker
```bash
# E2E tests always require Docker
python tests/unified_test_runner.py --category e2e

# Database tests need PostgreSQL
python tests/unified_test_runner.py --category database
```

### 5. Force Real Services
```bash
# Force Docker even for categories that normally don't need it
python tests/unified_test_runner.py --category unit --real-services
```

## Implementation Details

### Docker Requirement Logic
The `_docker_required_for_tests()` method determines if Docker is needed by:

1. **Checking explicit flags**:
   - `--no-docker` flag disables Docker
   - `--real-services` flag requires Docker
   - `TEST_NO_DOCKER` environment variable

2. **Analyzing test categories**:
   - Categories are classified as Docker-required or Docker-optional
   - E2E categories always need Docker
   - Unit/smoke tests don't need Docker

3. **Environment considerations**:
   - Dev/staging environments require real services per CLAUDE.md
   - Test environment can use mocks for certain categories

4. **Test pattern detection**:
   - Unit test patterns indicate Docker not needed
   - Mock/stub patterns indicate Docker not needed

### Docker Cleanup Optimization
- Cleanup is skipped if Docker was not initialized
- No unnecessary Docker commands are executed
- Faster test completion for Docker-free tests

## Performance Benefits

### Without Docker
- **Startup time**: < 5 seconds
- **No container overhead**: 0 MB RAM
- **No cleanup time**: 0 seconds
- **Works offline**: Yes

### With Docker (when needed)
- **Startup time**: 30-60 seconds
- **Container overhead**: 2-4 GB RAM
- **Cleanup time**: 10-20 seconds
- **Requires Docker**: Yes

## Best Practices

1. **Use `--no-docker` for unit tests in CI/CD** to speed up pipelines
2. **Let auto-detection work** for local development
3. **Always use Docker for E2E tests** to ensure real integration
4. **Set `TEST_NO_DOCKER=true` in resource-constrained environments**
5. **Use category-specific commands** to run only what you need

## Troubleshooting

### Docker Not Starting When Needed
- Check if Docker Desktop is running
- Verify Docker commands work: `docker ps`
- Use `--real-services` to force Docker initialization

### Tests Failing Without Docker
- Some tests may have hidden dependencies
- Check test output for connection errors
- Consider if the test category is correctly classified

### Performance Not Improved
- Ensure you're using `--no-docker` flag
- Check that Docker cleanup is being skipped
- Verify test category doesn't require services

## Future Improvements

1. **Finer-grained detection**: Analyze individual test files for service dependencies
2. **Parallel execution**: Run Docker-free tests while Docker initializes
3. **Service mocking**: Provide lightweight mocks for more test categories
4. **Configuration profiles**: Pre-defined profiles for different testing scenarios