# Test Infrastructure Documentation

**Last Updated:** 2025-09-14  
**Test Coverage Status:** ✅ EXCELLENT - 16,000+ tests across 14,567+ files with >99.9% collection success  
**Infrastructure Health:** ✅ OPERATIONAL - SSOT compliance achieved

## Overview

The Netra platform test infrastructure has been updated to use **Docker Compose as the default** for managing test services. This provides better isolation, consistency, and reliability compared to the previous dev_launcher approach.

## Key Components

### 1. Docker Compose Test Configuration
- **File**: `docker-compose.test.yml`
- **Purpose**: Defines isolated test services (PostgreSQL, Redis, ClickHouse, Backend, Auth, Frontend)
- **Benefits**: 
  - Isolated test databases (separate from development)
  - Consistent environment across all developers
  - Fast startup and teardown
  - No port conflicts with development services

### 2. Test Service Manager
- **Module**: `test_framework/docker_test_manager.py`
- **Class**: `DockerTestManager`
- **Features**:
  - Automatic Docker detection with fallback to mocks
  - Service health checking
  - Environment configuration
  - Multiple execution modes (docker, local, mock)

### 3. Test Fixtures
- **Module**: `test_framework/conftest_base.py`
- **Key Fixtures**:
  - `docker_test_manager`: Session-scoped service lifecycle management
  - `test_services`: Access to service URLs and configuration
  - `e2e_services`: Full E2E stack for integration tests
  - `service_urls`: Convenience fixture for service endpoints

## Usage

### Running Tests with Docker Infrastructure

#### Option 1: Using the Test Runner (Recommended)
```bash
# Run with Docker services (default)
python unified_test_runner.py --level integration

# Run with mock services only (no Docker required)
TEST_SERVICE_MODE=mock python unified_test_runner.py --level unit

# Run with legacy dev_launcher
TEST_SERVICE_MODE=local python unified_test_runner.py --level integration
```

#### Option 2: Using the Management Script
```bash
# Start core test services (PostgreSQL, Redis)
python scripts/manage_test_services.py start

# Start full E2E stack
python scripts/manage_test_services.py start --e2e

# Check service status
python scripts/manage_test_services.py status

# Stop services
python scripts/manage_test_services.py stop

# Stop and clean all data
python scripts/manage_test_services.py clean

# Run tests with automatic service management
python scripts/manage_test_services.py test
```

#### Option 3: Direct Docker Compose Commands
```bash
# Start test services
docker compose -f docker-compose.test.yml up -d

# Start with E2E profile
docker compose -f docker-compose.test.yml --profile e2e up -d

# View logs
docker compose -f docker-compose.test.yml logs -f

# Stop services
docker compose -f docker-compose.test.yml down

# Stop and clean volumes
docker compose -f docker-compose.test.yml down -v
```

## Service Modes

### Docker Mode (Default)
- Uses `docker-compose.test.yml`
- Isolated test containers
- Test-specific ports (PostgreSQL: 5433, Redis: 6380, Backend: 8001, Auth: 8082)
- Automatic health checking
- Best for integration and E2E tests

### Local Mode (Legacy)
- Uses dev_launcher for service management
- Shares services with development environment
- May have port conflicts
- Use only if Docker is not available

### Mock Mode
- No real services required
- Uses in-memory databases and mocks
- Fastest execution
- Best for unit tests

## Environment Variables

### Service Mode Selection
```bash
# Use Docker services (default)
export TEST_SERVICE_MODE=docker

# Use dev_launcher
export TEST_SERVICE_MODE=local

# Use mocks only
export TEST_SERVICE_MODE=mock
```

### Custom Ports (Docker Mode)
```bash
export TEST_POSTGRES_PORT=5433
export TEST_REDIS_PORT=6380
export TEST_BACKEND_PORT=8001
export TEST_AUTH_PORT=8082
export TEST_FRONTEND_PORT=3001
```

## Test Categories

### Unit Tests
- Use mock mode by default
- No external dependencies
- Fast execution
```python
@pytest.mark.unit
def test_business_logic():
    # Test with mocks
    pass
```

### Integration Tests
- Use Docker services by default
- Test service interactions
- Real databases
```python
@pytest.mark.integration
async def test_database_operations(test_services):
    # Test with real PostgreSQL
    db_url = test_services.get_service_url("postgres")
    # ...
```

### E2E Tests
- Use full Docker stack
- Test complete workflows
- All services running
```python
@pytest.mark.e2e
async def test_full_workflow(e2e_services):
    # Test with backend, auth, and frontend
    backend_url = e2e_services.get_service_url("backend")
    # ...
```

## Migration Guide

### For Existing Tests

Tests that currently use dev_launcher directly should be updated to use the test service fixtures:

#### Before (Using dev_launcher):
```python
from dev_launcher import DevLauncher

@pytest.fixture
async def services():
    launcher = DevLauncher()
    await launcher.start()
    yield launcher
    await launcher.stop()
```

#### After (Using Docker test manager):
```python
# No fixture needed - use the provided ones!

async def test_something(test_services):
    # Services are already running
    postgres_url = test_services.get_service_url("postgres")
    # ...
```

### For CI/CD Pipelines

Update CI/CD configurations to use Docker Compose:

```yaml
# GitHub Actions example
steps:
  - name: Start test services
    run: docker compose -f docker-compose.test.yml up -d
    
  - name: Wait for services
    run: docker compose -f docker-compose.test.yml wait postgres-test redis-test
    
  - name: Run tests
    run: python unified_test_runner.py --level integration
    
  - name: Stop services
    if: always()
    run: docker compose -f docker-compose.test.yml down -v
```

## Troubleshooting

### Docker Not Available
- The system automatically falls back to mock mode
- Install Docker Desktop or Docker Engine
- Ensure Docker daemon is running

### Port Conflicts
- Test services use different ports than development
- Check `docker-compose.test.yml` for port mappings
- Use environment variables to customize ports

### Slow Startup
- First run downloads Docker images
- Subsequent runs use cached images
- Use `--no-cache` flag to force rebuild

### Test Failures
- Check service health: `python scripts/manage_test_services.py status`
- View logs: `docker compose -f docker-compose.test.yml logs`
- Ensure migrations are applied: Check backend-test logs

## Best Practices

1. **Always use fixtures**: Don't manage services manually in tests
2. **Mark tests appropriately**: Use `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`
3. **Clean up resources**: Services are automatically cleaned after test sessions
4. **Use appropriate mode**: Unit tests with mocks, integration tests with Docker
5. **Check service health**: Wait for services to be healthy before running tests

## Performance Tips

1. **Reuse containers**: The session-scoped fixture reuses containers across tests
2. **Use profiles**: Only start services you need (e.g., skip ClickHouse if not testing analytics)
3. **Parallel execution**: Tests can run in parallel within the same session
4. **Volume management**: Clean volumes periodically with `docker compose down -v`

## Future Improvements

- [ ] Add test data seeding capabilities
- [ ] Implement snapshot testing for databases
- [ ] Add performance benchmarking fixtures
- [ ] Create test environment provisioning for cloud testing
- [ ] Add distributed testing support