# Integration Test Setup Guide

This guide helps you set up the required infrastructure for running integration tests that require real Redis and PostgreSQL services.

## Quick Start (5 minutes)

### Prerequisites

1. **Docker Desktop** must be running
2. **2GB+ free RAM** for test services

### 1. Start Test Infrastructure

```bash
# Navigate to project root
cd /path/to/netra-apex

# Start Redis and PostgreSQL for tests
python scripts/setup_test_infrastructure.py --start
```

### 2. Verify Services are Ready

```bash
# Check service status
python scripts/setup_test_infrastructure.py --status
```

Expected output:
```
=== Test Infrastructure Status ===
Docker Available: ✓

Services:
  Redis        Running: ✓  Healthy: ✓  Accessible: ✓
  Postgres     Running: ✓  Healthy: ✓  Accessible: ✓

✅ Infrastructure ready for integration tests!
```

### 3. Run Integration Tests

```bash
# Run 3-tier persistence tests
python -m pytest tests/integration/test_3tier_persistence_integration.py -v

# Run all integration tests
python -m pytest tests/integration/ -v
```

### 4. Stop Services (Optional)

```bash
# Stop test infrastructure when done
python scripts/setup_test_infrastructure.py --stop
```

## Service Configuration

The test infrastructure uses these ports:

- **Redis**: localhost:6381 (database 0)
- **PostgreSQL**: localhost:5436 (database: netra_test, user: test, password: test)

## Troubleshooting

### Docker Issues

**Error: Docker not found**
```bash
# Install Docker Desktop from https://docker.com/products/docker-desktop
# Ensure it's running before proceeding
```

**Error: Docker daemon not running**
```bash
# Start Docker Desktop application
# Wait for it to fully start (green icon in system tray)
```

### Service Issues

**Services not starting**
```bash
# Check service logs
python scripts/setup_test_infrastructure.py --logs

# Try stopping and restarting
python scripts/setup_test_infrastructure.py --stop
python scripts/setup_test_infrastructure.py --start
```

**Port conflicts**
```bash
# Check what's using the ports
netstat -an | grep 6381  # Redis
netstat -an | grep 5436  # PostgreSQL

# If conflicts exist, stop the conflicting services or change ports in:
# docker/docker-compose.minimal-test.yml
```

### Test Failures

**"Redis connection required for persistence tests"**
```bash
# Ensure Redis is accessible
python scripts/setup_test_infrastructure.py --status

# If Redis shows as not accessible, restart services
python scripts/setup_test_infrastructure.py --stop
python scripts/setup_test_infrastructure.py --start
```

## Manual Setup (Alternative)

If the automated script doesn't work:

```bash
# Navigate to project root
cd /path/to/netra-apex

# Start services manually using Docker Compose
cd docker
docker-compose -f docker-compose.minimal-test.yml up -d minimal-test-redis minimal-test-postgres

# Check they're running
docker-compose -f docker-compose.minimal-test.yml ps

# Test Redis connection
docker exec $(docker ps -q -f name=minimal-test-redis) redis-cli ping

# Test PostgreSQL connection
docker exec $(docker ps -q -f name=minimal-test-postgres) pg_isready -U test
```

## Architecture Note

These tests follow the CLAUDE.md mandate: **"Real Services Required"**. Integration tests use actual Redis and PostgreSQL instances, not mocks, to ensure:

- Realistic performance characteristics
- Real network behavior
- Actual database constraints
- True concurrency patterns

This provides higher confidence in the test results and catches issues that mocks would miss.

## Performance Tips

- **Memory**: Test services are configured with minimal memory footprints
- **Storage**: Uses named Docker volumes for persistence across test runs
- **Networking**: Uses bridge networking for fast local communication
- **Cleanup**: Services are configured to not persist data between test runs

## Integration with Test Runner

The unified test runner automatically detects when Redis/PostgreSQL services are required:

```bash
# These commands automatically use real services when available
python tests/unified_test_runner.py --category integration
python tests/unified_test_runner.py --real-services
```

The test framework will gracefully degrade if services aren't available, but integration tests requiring real persistence will be skipped.