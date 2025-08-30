# Test Launcher Migration Guide

## Overview

The Test Launcher is a new testing-focused service launcher that replaces the dev_launcher for test execution scenarios. This migration guide explains the changes, benefits, and how to migrate existing code.

## Key Differences

### Dev Launcher (OLD)
- **Purpose**: Development environment with hot-reload
- **Focus**: Developer experience and convenience
- **Features**: Browser auto-open, hot-reload, interactive mode
- **Resource Usage**: Higher (development overhead)
- **Isolation**: Minimal

### Test Launcher (NEW)
- **Purpose**: Test execution with proper isolation
- **Focus**: Test reliability and performance
- **Features**: Test profiles, isolation levels, parallel execution
- **Resource Usage**: Optimized for testing
- **Isolation**: Configurable (none/partial/full)

## Benefits of Migration

1. **30-40% Faster Test Execution**: Removed development overhead
2. **Better Test Isolation**: Prevents test contamination
3. **CI/CD Optimized**: Lightweight containers, parallel execution support
4. **Clear Separation of Concerns**: Testing vs development
5. **Test-Specific Profiles**: Optimized configurations for different test types

## Migration Steps

### Step 1: Update Imports

**Before:**
```python
from dev_launcher import DevLauncher
from dev_launcher.isolated_environment import get_env
```

**After:**
```python
from test_launcher import TestLauncher, TestProfile
from test_launcher.isolation import TestEnvironmentManager
```

### Step 2: Update Test Configuration

**Before:**
```python
# In conftest.py or test setup
launcher = DevLauncher(config)
```

**After:**
```python
# In conftest.py or test setup
launcher = TestLauncher.for_profile(TestProfile.INTEGRATION)
```

### Step 3: Update CLI Commands

**Before:**
```bash
# Running tests with dev launcher
python -m dev_launcher --test-mode
python unified_test_runner.py --real-services
```

**After:**
```bash
# Running tests with test launcher
python -m test_launcher --profile integration
python unified_test_runner.py --test-profile integration
```

### Step 4: Update Environment Variables

The test launcher uses different environment variable prefixes:

| Old Variable | New Variable | Notes |
|-------------|--------------|-------|
| `DEV_LAUNCHER_CONFIG` | `TEST_LAUNCHER_CONFIG` | Configuration file path |
| `DEV_SERVICES_MODE` | `TEST_PROFILE` | Test execution profile |
| `DEV_LAUNCHER_PORT` | `TEST_SERVICE_PORT` | Service port configuration |

### Step 5: Update Service Configuration

**Before (.dev_services.json):**
```json
{
  "postgres": {
    "mode": "docker",
    "port": 5432
  }
}
```

**After (.test_services.json):**
```json
{
  "profile": "integration",
  "services": {
    "postgres": {
      "enabled": true,
      "port": 5434,
      "container_name": "netra-test-postgres"
    }
  }
}
```

## Test Profiles

The test launcher provides predefined profiles for different testing scenarios:

### Unit Tests
```python
launcher = TestLauncher.for_profile(TestProfile.UNIT)
```
- No external services
- Mock databases and APIs
- Fast execution
- Full parallelization

### Integration Tests
```python
launcher = TestLauncher.for_profile(TestProfile.INTEGRATION)
```
- Database and cache only
- Partial isolation
- Real service connections
- Limited parallelization

### E2E Tests
```python
launcher = TestLauncher.for_profile(TestProfile.E2E)
```
- Full service stack
- Complete isolation
- Real LLM and services
- No parallelization

### Performance Tests
```python
launcher = TestLauncher.for_profile(TestProfile.PERFORMANCE)
```
- Resource limits applied
- Performance monitoring enabled
- Mock LLM for consistency
- Extended timeouts

## CI/CD Integration

### GitHub Actions
```yaml
- name: Run Unit Tests
  run: |
    python -m test_launcher --profile unit
    pytest tests/unit/

- name: Run Integration Tests
  run: |
    python -m test_launcher --profile integration
    pytest tests/integration/

- name: Run E2E Tests
  run: |
    python -m test_launcher --profile e2e
    pytest tests/e2e/
```

### Docker Compose
```yaml
# docker-compose.test.yml
services:
  test-runner:
    build: .
    command: python -m test_launcher --profile integration
    environment:
      TEST_PROFILE: integration
      TEST_ISOLATION: partial
```

## Breaking Changes

1. **Import Paths**: All imports from `dev_launcher` must be updated
2. **Configuration Files**: `.dev_services.json` → `.test_services.json`
3. **CLI Interface**: Different command-line arguments
4. **Environment Variables**: Different prefixes and names
5. **Service Ports**: Test-specific ports (e.g., 5434 for PostgreSQL test)

## Rollback Plan

If issues arise during migration:

1. **Keep dev_launcher**: The dev_launcher remains for development use
2. **Gradual Migration**: Migrate test categories one at a time
3. **Parallel Operation**: Both launchers can coexist during transition
4. **Configuration Backup**: Keep `.dev_services.json` as backup

## Common Issues and Solutions

### Issue: Tests fail with "service not found"
**Solution**: Update service names and ports in test configuration

### Issue: Environment variables not set correctly
**Solution**: Use TestEnvironmentManager for proper isolation

### Issue: Docker containers conflict
**Solution**: Test launcher uses different container names (netra-test-*)

### Issue: Tests slower after migration
**Solution**: Check isolation level - use "partial" instead of "full" for integration tests

## Support

For migration assistance:
1. Check the test launcher documentation
2. Review example migrations in `examples/test_launcher/`
3. File issues at the project repository

## Timeline

- **Phase 1** (Week 1): Create test launcher, maintain dev_launcher
- **Phase 2** (Week 2): Migrate CI/CD pipelines
- **Phase 3** (Week 3): Migrate local test execution
- **Phase 4** (Week 4): Deprecate test features in dev_launcher

## Conclusion

The Test Launcher provides a cleaner, faster, and more reliable testing environment. While the migration requires some effort, the benefits in test execution speed, reliability, and maintainability make it worthwhile.