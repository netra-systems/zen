# Podman Testing User Guide

## Overview

This guide provides comprehensive instructions for using Podman as a Docker alternative for the Netra test infrastructure. Podman provides container functionality without requiring Docker Desktop licensing.

## Key Features

- **Dynamic Port Allocation**: Automatic port assignment prevents conflicts
- **Parallel Test Execution**: Multiple test runs can execute simultaneously
- **Docker Compatibility**: Drop-in replacement for Docker in test infrastructure
- **Rootless Containers**: Enhanced security by default
- **No Licensing Requirements**: Completely open source

## Quick Start

### 1. Verify Installation

```bash
# Check Podman is installed and running
podman --version
podman machine list

# Verify environment variable is set
echo %CONTAINER_RUNTIME%
# Should output: podman
```

### 2. Run Tests with Dynamic Ports

```bash
# Run smoke tests with real services (uses Podman automatically)
python tests/unified_test_runner.py --category smoke --real-services

# Run specific test categories
python tests/unified_test_runner.py --category integration --real-services

# Run without real services (mock mode)
python tests/unified_test_runner.py --category unit
```

### 3. Manual Container Management

```bash
# View running containers
podman ps

# View all containers (including stopped)
podman ps -a

# Stop all test containers
podman stop $(podman ps -q)

# Remove all test containers
podman rm $(podman ps -aq)
```

## Architecture

### Dynamic Port Allocation

The system uses dynamic port allocation to prevent conflicts:

| Service | Port Range | Example |
|---------|-----------|---------|
| PostgreSQL | 30000-30099 | 30038 |
| Redis | 30100-30199 | 30118 |
| ClickHouse | 30200-30299 | 30248 |
| Backend | 30300-30399 | 30305 |
| Auth | 30400-30499 | 30447 |
| Frontend | 30500-30599 | 30574 |

### Container Naming

Containers are named with the pattern: `test-{service}-{test_id}`

Example: `test-postgres-test_run_1756937221_58896`

This ensures unique container names for parallel test execution.

## Configuration

### Environment Variables

The system respects these environment variables:

```bash
# Set in .env file or system environment
CONTAINER_RUNTIME=podman  # Use Podman instead of Docker
```

### Test Configuration

The test runner automatically:
1. Detects Podman when `CONTAINER_RUNTIME=podman`
2. Allocates dynamic ports for services
3. Configures test environment with allocated ports
4. Cleans up containers after test completion

## Common Tasks

### Running Different Test Categories

```bash
# Unit tests (no containers needed)
python tests/unified_test_runner.py --category unit

# Integration tests with real services
python tests/unified_test_runner.py --category integration --real-services

# API tests
python tests/unified_test_runner.py --category api --real-services

# Full test suite
python tests/unified_test_runner.py --categories smoke unit integration api --real-services
```

### Debugging Container Issues

```bash
# Check container logs
podman logs test-postgres-{test_id}

# Execute command in container
podman exec -it test-postgres-{test_id} psql -U test

# Inspect container
podman inspect test-postgres-{test_id}

# Check port mappings
podman port test-postgres-{test_id}
```

### Manual Service Start for Development

```bash
# Start PostgreSQL with specific port
podman run -d --name dev-postgres \
  -e POSTGRES_USER=test \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=netra_test \
  -p 5432:5432 \
  docker.io/postgres:15-alpine

# Start Redis
podman run -d --name dev-redis \
  -p 6379:6379 \
  docker.io/redis:7-alpine
```

## Troubleshooting

### Issue: Podman Machine Not Started

```bash
# Check machine status
podman machine list

# Start the machine
podman machine start

# If issues persist, recreate
podman machine rm
podman machine init
podman machine start
```

### Issue: Port Already in Use

The system automatically finds free ports, but if manual containers are using ports:

```bash
# Find what's using a port (Windows)
netstat -ano | findstr :30038

# Stop conflicting containers
podman ps --filter publish=30038
podman stop <container_id>
```

### Issue: Container Build Failures

```bash
# Clear Podman cache
podman system prune -a

# Pull fresh images
podman pull docker.io/postgres:15-alpine
podman pull docker.io/redis:7-alpine
```

### Issue: Tests Can't Connect to Services

1. Verify containers are running:
   ```bash
   podman ps
   ```

2. Check container health:
   ```bash
   podman exec test-postgres-{test_id} pg_isready -U test
   podman exec test-redis-{test_id} redis-cli ping
   ```

3. Verify port allocation in test logs:
   ```
   [INFO] Allocated port 30038 for postgres
   [INFO] Allocated port 30118 for redis
   ```

## Performance Optimization

### Tips for Faster Tests

1. **Use Alpine Images**: Smaller images start faster
2. **Limit Memory**: Containers use only what they need
3. **Parallel Execution**: Dynamic ports enable parallel test runs
4. **Cleanup Regularly**: Remove stopped containers and unused images

### Resource Management

```bash
# View resource usage
podman stats

# Set resource limits (in container run)
podman run -d --memory="512m" --cpus="0.5" ...

# Clean up unused resources
podman system prune -a
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Test with Podman

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Install Podman
      run: |
        sudo apt-get update
        sudo apt-get install -y podman
    
    - name: Set environment
      run: echo "CONTAINER_RUNTIME=podman" >> $GITHUB_ENV
    
    - name: Run tests
      run: |
        python tests/unified_test_runner.py --real-services
```

## Advanced Usage

### Custom Port Ranges

Modify `PORT_RANGES` in `test_framework/podman_dynamic_ports.py`:

```python
PORT_RANGES = {
    'postgres': (40000, 40099),  # Custom range
    'redis': (40100, 40199),
    # ...
}
```

### Parallel Test Execution

```bash
# Run multiple test suites in parallel
python tests/unified_test_runner.py --category unit &
python tests/unified_test_runner.py --category integration --real-services &
python tests/unified_test_runner.py --category api --real-services &
wait
```

Each run gets unique ports, preventing conflicts.

## Best Practices

1. **Always use dynamic ports** for test environments
2. **Clean up containers** after test runs
3. **Use meaningful test IDs** for debugging
4. **Monitor resource usage** with `podman stats`
5. **Pull images regularly** for security updates
6. **Use rootless mode** for better security
7. **Set resource limits** to prevent resource exhaustion

## Migration from Docker

If migrating from Docker:

1. Install Podman
2. Set `CONTAINER_RUNTIME=podman` in `.env`
3. Run tests as usual - the system auto-detects Podman
4. No code changes required!

## Support and Resources

- [Podman Documentation](https://docs.podman.io/)
- [Podman Desktop](https://podman-desktop.io/)
- [Container Image Sources](https://hub.docker.com/)
- Project Issues: Report in project repository

## Summary

Podman provides a seamless, license-free alternative to Docker for running the Netra test infrastructure. With dynamic port allocation and automatic container management, it enables efficient parallel testing while maintaining full compatibility with existing test code.