# Dev Launcher Startup Integration Test

## Overview

This test file (`test_dev_launcher_startup.py`) provides comprehensive testing for the dev launcher startup processes to prevent regression and ensure reliable development environment initialization.

## Test Coverage

### Core Functionality Tests

1. **Database URL Normalization Fix** (`test_database_url_normalization_fix`)
   - Tests the specific fix for asyncpg URL compatibility
   - Validates URL normalization for various PostgreSQL URL formats
   - Ensures `postgresql+asyncpg://` and `postgres://` URLs are properly converted

2. **Port Allocation and Conflict Resolution** (`test_port_allocation_and_conflict_resolution`)
   - Tests dynamic port allocation functionality
   - Validates conflict resolution when preferred ports are unavailable
   - Verifies proper port tracking and cleanup

3. **Environment Variable Loading Consistency** (`test_environment_variable_loading_consistency`)
   - Tests consistent loading of database connection strings
   - Validates Redis, PostgreSQL, and ClickHouse configuration loading
   - Ensures environment isolation works correctly

4. **Service Initialization Order** (`test_service_initialization_order`)
   - Validates proper initialization sequence of launcher components
   - Tests dependency injection and component availability
   - Ensures critical services are initialized before dependent services

### Platform Compatibility Tests

5. **Signal Handlers Windows Compatibility** (`test_signal_handlers_windows_compatibility`)
   - Tests signal handler initialization without triggering actual signal setup
   - Validates platform detection (Windows vs Unix-like systems)
   - Ensures signal handling components are properly initialized

6. **Windows-Specific Features** (`test_windows_specific_features`)
   - Tests availability of Windows-specific tools (taskkill, netstat)
   - Validates Windows process management capabilities
   - Skips on non-Windows platforms

### Error Recovery and Configuration Tests

7. **Error Recovery Scenarios** (`test_error_recovery_scenarios`)
   - Tests graceful handling of missing dependencies
   - Validates emergency cleanup capabilities
   - Ensures launcher doesn't crash on initialization errors

8. **Launcher Configuration Validation** (`test_launcher_configuration_validation`)
   - Tests configuration defaults and validation
   - Validates port conflict resolution in configuration
   - Tests various configuration scenarios

9. **Database Connectivity Validation** (`test_database_connectivity_validation`)
   - Tests database connection validation with mocked connections
   - Validates error handling for connection failures
   - Ensures graceful degradation when databases are unavailable

10. **Emoji Support Detection** (`test_emoji_support_detection`)
    - Tests emoji support detection for different environments
    - Validates cross-platform emoji handling

## Business Value

This test suite provides:
- **Development Velocity**: Prevents startup failures that block development
- **System Stability**: Catches regressions in critical startup components
- **Platform Compatibility**: Ensures dev launcher works across Windows and Unix systems
- **Error Resilience**: Tests error recovery scenarios to prevent cascading failures

## Running the Tests

### Individual Test Execution
```bash
# Run specific test
python -m pytest netra_backend/tests/integration/test_dev_launcher_startup.py::TestDevLauncherStartup::test_database_url_normalization_fix -v

# Run all dev launcher startup tests
python -m pytest netra_backend/tests/integration/test_dev_launcher_startup.py -v
```

### Core Tests (Non-problematic)
```bash
# Run core functionality tests without async issues
python -m pytest netra_backend/tests/integration/test_dev_launcher_startup.py::TestDevLauncherStartup::test_database_url_normalization_fix netra_backend/tests/integration/test_dev_launcher_startup.py::TestDevLauncherStartup::test_port_allocation_and_conflict_resolution netra_backend/tests/integration/test_dev_launcher_startup.py::TestDevLauncherStartup::test_environment_variable_loading_consistency -v
```

## Key Features

### Regression Prevention
- **Database URL Normalization**: Prevents asyncpg connection failures
- **Port Conflict Resolution**: Prevents service startup conflicts
- **Environment Loading**: Ensures consistent configuration loading

### Windows Compatibility
- Tests Windows-specific process management tools
- Validates Windows signal handling
- Ensures cross-platform functionality

### Mock-Based Testing
- Uses actual dev launcher components where possible
- Strategic mocking to avoid external dependencies
- Real service validation with fallback graceful handling

## Test Patterns

### Fixture Usage
```python
@pytest.fixture
def launcher_config(self):
    """Create a test launcher configuration."""
    return LauncherConfig(
        dynamic_ports=True,
        backend_reload=False,
        verbose=True,
        no_browser=True
    )
```

### Mock Patterns
```python
with patch('dev_launcher.config.find_project_root', return_value=temp_path):
    # Test launcher creation with controlled environment
    launcher = DevLauncher(launcher_config)
```

### Environment Testing
```python
with patch.dict(os.environ, mock_environment, clear=False):
    # Test environment variable loading
    env = get_env()
    assert env.get('DATABASE_URL') is not None
```

## Integration with Test Suite

This test is integrated into the main test suite as an integration test and can be run through:
- Direct pytest execution
- Unified test runner (as part of integration category)
- CI/CD pipelines

## Notes

- Some signal handler tests may show cleanup warnings - this is expected and doesn't affect test functionality
- Database connectivity tests use strategic mocking to avoid requiring actual database connections
- Windows-specific tests automatically skip on non-Windows platforms