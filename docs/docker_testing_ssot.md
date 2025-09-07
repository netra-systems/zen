# Docker Testing Configuration - Single Source of Truth (SSOT)

## Overview
This document defines the authoritative Docker testing configuration for Netra Apex. All test runners and testing processes MUST adhere to this specification.

## CRITICAL: Default Testing Mode
**DEFAULT: Use integrated Docker test environment via `docker-compose.test.yml`**
- Tests MUST use real services by default (PostgreSQL, Redis, ClickHouse)
- Mocks are FORBIDDEN except for smoke tests
- All services run in isolated test containers with tmpfs for speed

## Docker Environment Management

### 1. Test Environment Lifecycle

#### Startup Sequence
```bash
# ALWAYS clean up before starting
docker compose -f docker-compose.test.yml down --volumes --remove-orphans

# Start test environment
docker compose -f docker-compose.test.yml up -d

# Wait for health checks
docker compose -f docker-compose.test.yml ps --format json | python -c "
import json, sys, time
for i in range(30):
    data = json.loads(sys.stdin.read())
    if all(s.get('Health', '') == 'healthy' for s in data):
        sys.exit(0)
    time.sleep(1)
sys.exit(1)
"
```

#### Shutdown Sequence
```bash
# Clean shutdown
docker compose -f docker-compose.test.yml down --volumes --remove-orphans

# Force cleanup if needed
docker ps -aq --filter "name=netra-test-" | xargs -r docker stop
docker ps -aq --filter "name=netra-test-" | xargs -r docker rm -f
docker network ls --filter "name=netra-test-" -q | xargs -r docker network rm
```

### 2. Container Naming Convention
All test containers MUST follow this naming pattern:
- `netra-test-{service}` for shared test environment
- `netra-test-{run_id}-{service}` for dedicated test runs

Services:
- `netra-test-postgres` - PostgreSQL database
- `netra-test-redis` - Redis cache
- `netra-test-clickhouse` - ClickHouse analytics
- `netra-test-rabbitmq` - Message queue

### 3. Port Allocation
Test services use dedicated ports to avoid conflicts:

| Service | Test Port | Dev Port | Production Port |
|---------|-----------|----------|-----------------|
| PostgreSQL | 5434 | 5433 | 5432 |
| Redis | 6381 | 6380 | 6379 |
| ClickHouse | 8125 | 8124 | 8123 |
| RabbitMQ | 5673 | 5672 | 5672 |

### 4. Environment Variables
Test runner MUST set these environment variables:

```python
# Required for all tests
TEST_ENV = "test"
TESTING = "1"
TEST_USE_SHARED_DOCKER = "false"  # Use dedicated containers

# Database connections
#removed-legacy= "postgresql://test_user:test_pass@localhost:5434/netra_test"
REDIS_URL = "redis://localhost:6381/1"
CLICKHOUSE_URL = "http://localhost:8125"

# Service configuration
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5434"
POSTGRES_USER = "test_user"
POSTGRES_PASSWORD = "test_pass"
POSTGRES_DB = "netra_test"

REDIS_HOST = "localhost"
REDIS_PORT = "6381"
REDIS_DB = "1"

CLICKHOUSE_HOST = "localhost"
CLICKHOUSE_PORT = "8125"
```

## Test Execution Process

### 1. Unified Test Runner Usage

#### Basic Commands
```bash
# Run smoke tests (no external dependencies)
python tests/unified_test_runner.py --category smoke

# Run unit tests with real services
python tests/unified_test_runner.py --category unit --real-services

# Run integration tests with dedicated Docker
python tests/unified_test_runner.py --category integration --docker-dedicated

# Run all tests with real LLM
python tests/unified_test_runner.py --categories all --real-llm --docker-dedicated
```

#### Docker Management Flags
- `--docker-dedicated`: Use isolated Docker environment per test run
- `--docker-production`: Use production Docker images (lower memory)
- `--docker-no-cleanup`: Keep containers after tests (debugging)
- `--docker-force-restart`: Force restart even with cooldown
- `--docker-stats`: Show Docker resource usage

### 2. Test Categories and Dependencies

| Category | External Services | Docker Required | Default Mode |
|----------|------------------|-----------------|--------------|
| smoke | None | No | Mock |
| unit | Optional | No | Mock |
| integration | Required | Yes | Real Services |
| api | Required | Yes | Real Services |
| websocket | Required | Yes | Real Services |
| database | Required | Yes | Real Services |
| e2e | Required | Yes | Real Services |
| performance | Required | Yes | Real Services |

### 3. Service Health Checks

All services MUST pass health checks before tests run:

```yaml
# PostgreSQL
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U test_user -d netra_test"]
  interval: 5s
  timeout: 3s
  retries: 10

# Redis
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 5s
  timeout: 3s
  retries: 10

# ClickHouse
healthcheck:
  test: ["CMD", "wget", "--spider", "-q", "http://localhost:8123/ping"]
  interval: 5s
  timeout: 3s
  retries: 10
```

## Known Issues and Solutions

### 1. Container Name Conflicts
**Problem**: "Container name already in use" errors
**Solution**: Always run cleanup before starting tests
```bash
docker compose -f docker-compose.test.yml down --volumes --remove-orphans
```

### 2. Port Conflicts
**Problem**: "Address already in use" errors
**Solution**: Check for conflicting services
```bash
lsof -i :5434  # Check PostgreSQL test port
lsof -i :6381  # Check Redis test port
```

### 3. Docker Daemon Crashes
**Problem**: Docker daemon becomes unresponsive during tests
**Root Causes**:
- Resource exhaustion (memory/CPU)
- Orphaned containers consuming resources
- Network bridge saturation

**Solutions**:
```bash
# 1. Implement resource limits in docker-compose.test.yml
services:
  test-postgres:
    mem_limit: 512m
    cpus: '0.5'

# 2. Automatic cleanup between test runs
docker system prune -f --volumes

# 3. Monitor Docker resources
docker stats --no-stream

# 4. Restart Docker if needed (macOS)
osascript -e 'quit app "Docker"'
sleep 5
open -a Docker
```

### 4. Slow Test Startup
**Problem**: Tests take too long to initialize
**Solution**: Use tmpfs for database storage (already configured)
```yaml
volumes:
  - type: tmpfs
    target: /var/lib/postgresql/data
    tmpfs:
      size: 1G
```

## Test Environment Validation

### Pre-flight Checks
Before running tests, validate the environment:

```python
def validate_test_environment():
    """Validate test environment is properly configured."""
    checks = {
        "docker_running": check_docker_daemon(),
        "ports_available": check_port_availability([5434, 6381, 8125]),
        "containers_healthy": check_container_health(),
        "disk_space": check_disk_space(min_gb=5),
        "memory_available": check_memory(min_gb=4)
    }
    
    failures = [k for k, v in checks.items() if not v]
    if failures:
        raise EnvironmentError(f"Test environment validation failed: {failures}")
```

## Performance Optimizations

### 1. Database Optimizations
- Use tmpfs for test databases (no disk I/O)
- Disable fsync and synchronous_commit for tests
- Use connection pooling with appropriate limits

### 2. Container Optimizations
- Use Alpine-based images where possible
- Limit container resources to prevent system overload
- Use Docker layer caching for faster rebuilds

### 3. Test Execution Optimizations
- Run tests in parallel where possible
- Use pytest-xdist for distributed testing
- Cache test fixtures between runs

## Monitoring and Debugging

### 1. Container Logs
```bash
# View all test container logs
docker compose -f docker-compose.test.yml logs

# Follow specific service logs
docker compose -f docker-compose.test.yml logs -f test-postgres

# Export logs for analysis
docker compose -f docker-compose.test.yml logs > test_logs.txt
```

### 2. Resource Monitoring
```bash
# Monitor resource usage
docker stats $(docker ps -q --filter "name=netra-test-")

# Check disk usage
docker system df

# Inspect container details
docker inspect netra-test-postgres
```

### 3. Network Debugging
```bash
# List test networks
docker network ls --filter "name=netra"

# Inspect network configuration
docker network inspect netra-test-network

# Test connectivity
docker exec netra-test-postgres pg_isready
```

## Compliance Checklist

Before merging any test-related changes:

- [ ] Tests run successfully with `--docker-dedicated` flag
- [ ] No hardcoded ports or hostnames in test code
- [ ] All containers cleaned up after test completion
- [ ] Resource limits defined for all test containers
- [ ] Health checks implemented for all services
- [ ] Documentation updated if new services added
- [ ] No use of production credentials in test configuration
- [ ] Test environment isolated from development environment

## References

- [Docker Compose Test Configuration](../docker-compose.test.yml)
- [Unified Test Runner](../tests/unified_test_runner.py)
- [Test Framework Documentation](../test_framework/README.md)
- [CI/CD Pipeline Configuration](../.github/workflows/test.yml)