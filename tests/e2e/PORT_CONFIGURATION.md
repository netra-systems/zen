# E2E Test Port Configuration

## Overview

The E2E test suite now uses a dynamic port management system to handle different execution environments (local, Docker, CI) automatically. This prevents port conflicts and enables parallel test execution.

## Key Components

### 1. Dynamic Port Manager (`dynamic_port_manager.py`)
- Automatically detects execution environment
- Manages port allocation for all services
- Supports three modes: LOCAL, DOCKER, CI
- Provides consistent service URLs across environments

### 2. Port Configuration

#### Local Mode (Default)
```
Backend: 8000
Auth: 8081
Frontend: 3000
PostgreSQL: 5432
Redis: 6379
ClickHouse: 8123
```

#### Docker Mode (docker-compose.test.yml)
```
Backend: 8001
Auth: 8082
Frontend: 3001
PostgreSQL: 5433
Redis: 6380
ClickHouse: 8124
```

#### CI Mode
- All ports are dynamically allocated
- Prevents conflicts in CI/CD pipelines

## Usage

### Running E2E Tests Locally
```bash
# Default local configuration
pytest tests/e2e

# With explicit port setup
python scripts/setup_e2e_test_ports.py --export
pytest tests/e2e
```

### Running E2E Tests with Docker
```bash
# Using unified test runner (recommended)
python tests/unified_test_runner.py --category e2e --real-services

# Manual setup
docker-compose -f docker-compose.test.yml up -d --profile e2e
python scripts/setup_e2e_test_ports.py --mode docker --export --wait
pytest tests/e2e
docker-compose -f docker-compose.test.yml down
```

### Environment Variables

The system respects these environment variables:
- `TEST_BACKEND_PORT`: Override backend service port
- `TEST_AUTH_PORT`: Override auth service port
- `TEST_FRONTEND_PORT`: Override frontend port
- `TEST_POSTGRES_PORT`: Override PostgreSQL port
- `TEST_REDIS_PORT`: Override Redis port
- `TEST_CLICKHOUSE_PORT`: Override ClickHouse port
- `DOCKER_CONTAINER`: Set to "true" to force Docker mode
- `CI`: Set to "true" to force CI mode with dynamic ports

## Integration with Tests

Tests automatically use the dynamic port configuration through:
1. `tests/e2e/config.py` - Main configuration module
2. `tests/e2e/conftest.py` - Pytest fixtures
3. Individual test files inherit configuration automatically

### Example Test Usage
```python
from tests.e2e.config import get_backend_service_url, get_auth_service_url

async def test_service_connection():
    backend_url = get_backend_service_url()  # Automatically uses correct port
    auth_url = get_auth_service_url()        # Based on execution environment
    
    # Test implementation...
```

## Troubleshooting

### Port Conflicts
If you encounter port conflicts:
1. Check running services: `docker ps`
2. Stop conflicting services
3. Use environment variables to override ports
4. Or use CI mode for dynamic allocation

### Service Discovery Issues
The port manager automatically handles service discovery:
- Local mode: Uses `localhost`
- Docker mode: Uses Docker service names (e.g., `backend-test`)
- CI mode: Uses `localhost` with dynamic ports

### Debugging Port Configuration
```bash
# Check current configuration
python scripts/setup_e2e_test_ports.py --json

# Check if services are available
python scripts/setup_e2e_test_ports.py --wait
```

## Benefits

1. **No More Hardcoded Ports**: Tests adapt to environment automatically
2. **Parallel Testing**: CI mode enables parallel test execution
3. **Docker Integration**: Seamless switching between local and Docker testing
4. **Port Conflict Prevention**: Dynamic allocation prevents conflicts
5. **Service Discovery**: Automatic URL generation for all services