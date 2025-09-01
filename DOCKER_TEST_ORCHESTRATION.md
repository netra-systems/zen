# Docker Test Orchestration System

## Overview

The new Docker test orchestration system provides centralized management of isolated test environments with fresh Alpine-based Docker images. This ensures complete test isolation, reproducibility, and efficient resource usage.

## Key Components

### 1. Alpine-Based Docker Images

Created optimized Alpine-based Dockerfiles for all services:
- `docker/backend.alpine.Dockerfile` - Backend service (Python 3.11 on Alpine)
- `docker/auth.alpine.Dockerfile` - Auth service (Python 3.11 on Alpine)  
- `docker/frontend.alpine.Dockerfile` - Frontend service (Node 20 on Alpine)

**Benefits:**
- **Minimal size**: Alpine images are 5-10x smaller than standard images
- **Fast builds**: Reduced build time due to smaller base images
- **Production-like**: Uses same optimization techniques as production
- **Security**: Minimal attack surface with non-root users

### 2. Docker Orchestrator (`test_framework/docker_orchestrator.py`)

Central orchestration system that manages:
- **Isolated test environments**: Each test suite gets its own Docker network and services
- **Dynamic port allocation**: Prevents port conflicts when running parallel tests
- **Fresh builds**: Always builds images with latest code (--no-cache)
- **Service dependencies**: Manages startup order and health checks
- **Parallel execution**: Run multiple test environments simultaneously

**Key Features:**
```python
orchestrator = DockerOrchestrator()

# Create isolated test environment
test_env = orchestrator.create_test_environment(
    name="api-tests",
    services=["postgres", "redis", "backend", "auth"],
    use_alpine=True
)

# Get service URLs
backend_url = orchestrator.get_service_url(test_env.id, "backend")

# Cleanup when done
orchestrator.cleanup_environment(test_env.id)
```

### 3. Dev Services Refresh (`scripts/refresh_dev_services.py`)

Management script for development services:
- **Refresh with latest code**: Rebuilds and restarts services
- **Quick restart**: Restart without rebuild
- **Status monitoring**: Check health of all services
- **Log viewing**: Stream logs from services

**Usage:**
```bash
# Refresh backend and auth with latest changes
python scripts/refresh_dev_services.py refresh --services backend auth

# Quick restart without rebuild  
python scripts/refresh_dev_services.py restart --services backend

# Check status
python scripts/refresh_dev_services.py status

# View logs
python scripts/refresh_dev_services.py logs --services backend -f
```

### 4. Integrated Test Runner (`test_framework/integrated_test_runner.py`)

Combines test execution with Docker orchestration:
- **Isolated mode**: Run tests in fresh environment
- **Parallel mode**: Multiple test suites in parallel environments
- **Refresh mode**: Update services then test
- **CI mode**: Watch files and auto-test on changes

**Usage:**
```bash
# Run tests in isolated Alpine environment
python test_framework/integrated_test_runner.py --mode isolated --suites unit integration

# Parallel execution
python test_framework/integrated_test_runner.py --mode parallel --suites unit api e2e

# Refresh and test
python test_framework/integrated_test_runner.py --mode refresh --services backend --suites api

# Continuous integration
python test_framework/integrated_test_runner.py --mode ci --watch-paths netra_backend auth_service
```

### 5. Alpine Test Compose (`docker-compose.alpine-test.yml`)

Dedicated compose file for Alpine-based testing:
- Uses tmpfs volumes for ultra-fast ephemeral storage
- Optimized PostgreSQL settings for testing
- Minimal resource limits
- Fast health checks

## Architecture Patterns

### Test Isolation

Each test environment gets:
1. **Unique network**: `test-net-{env_id}`
2. **Dedicated containers**: `test-{service}-{env_id}`
3. **Dynamic ports**: No conflicts between environments
4. **Fresh data**: Ephemeral storage, no state pollution

### Build Pattern

```dockerfile
# Multi-stage build for optimization
FROM python:3.11-alpine3.19 as builder
# Build dependencies only in builder stage
RUN apk add gcc musl-dev postgresql-dev

FROM python:3.11-alpine3.19
# Runtime only has minimal dependencies
RUN apk add libpq curl tini
```

### Service Dependency Management

```python
# Services start in dependency order
configs["backend"] = ServiceConfig(
    name=f"test-backend-{env_id}",
    depends_on=["postgres", "redis"],
    healthcheck={
        "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
        "interval": "5s",
        "retries": 10
    }
)
```

## Performance Optimizations

### Alpine Images
- Base image: ~50MB vs ~900MB for standard
- Build time: 30-60s vs 2-3 minutes
- Startup time: 2-5s vs 10-15s

### tmpfs Volumes
- Database writes: 10x faster than disk
- No cleanup needed (ephemeral)
- Perfect for test isolation

### Parallel Execution
- Run N test suites simultaneously
- Each in isolated environment
- Dynamic port allocation prevents conflicts

## Best Practices

### 1. Always Use Fresh Builds for Tests
```python
# Force fresh build with --no-cache
build_args = ["docker", "build", "--no-cache", ...]
```

### 2. Clean Up After Tests
```python
try:
    # Run tests
    results = run_tests(env)
finally:
    # Always cleanup
    orchestrator.cleanup_environment(env.id)
```

### 3. Use Health Checks
```python
healthcheck={
    "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
    "interval": "3s",
    "timeout": "2s",
    "retries": 10
}
```

### 4. Resource Limits
```yaml
deploy:
  resources:
    limits:
      memory: 256M
      cpus: '0.25'
```

## Migration Guide

### From Standard Docker Compose

1. Switch to Alpine compose file:
```bash
docker-compose -f docker-compose.alpine-test.yml up
```

2. Use orchestrator for isolation:
```python
from test_framework.docker_orchestrator import DockerOrchestrator

orchestrator = DockerOrchestrator()
env = orchestrator.create_test_environment("my-tests", ["postgres", "backend"])
```

### From Mock-Based Tests

1. Create real service environment:
```python
# Instead of mocks
env = orchestrator.create_test_environment(
    "integration-tests",
    services=["postgres", "redis", "backend"],
    use_alpine=True
)
```

2. Get real service URLs:
```python
backend_url = orchestrator.get_service_url(env.id, "backend")
# Use real backend_url in tests
```

## Troubleshooting

### Port Conflicts
- Orchestrator uses dynamic port allocation
- Each environment gets unique ports
- Check with `docker ps` for actual ports

### Build Failures
- Check Docker daemon is running
- Ensure sufficient disk space
- Review Dockerfile syntax

### Health Check Timeouts
- Increase timeout in ServiceConfig
- Check service logs with `docker logs`
- Verify dependencies are healthy

## Future Enhancements

1. **Kubernetes Support**: Deploy test environments to K8s
2. **Cloud Testing**: Spin up environments in GCP/AWS
3. **Test Result Analytics**: Track performance over time
4. **Auto-scaling**: Dynamic resource allocation based on load
5. **Test Parallelization**: Distribute tests across multiple environments

## Summary

The Docker test orchestration system provides:
- ✅ Complete test isolation
- ✅ Fresh builds with latest code  
- ✅ Alpine-based optimization
- ✅ Parallel test execution
- ✅ Development service refresh
- ✅ Real services instead of mocks
- ✅ Resource efficiency
- ✅ Reproducible environments

This ensures tests are reliable, fast, and accurately reflect production behavior.