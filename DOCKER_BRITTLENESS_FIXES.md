# Docker Compose Brittleness Fixes

## Problem Analysis

The Docker Compose infrastructure was crashing frequently due to several brittleness issues:

### Root Causes Identified:

1. **`--remove-orphans` flag** - Indiscriminately killed unrelated containers
2. **`restart: unless-stopped` policy** - Caused containers to auto-restart even when intentionally stopped
3. **No container reuse logic** - Tests always tried to recreate containers instead of reusing healthy ones
4. **Multiple competing Docker managers** - Different parts of the codebase managed Docker differently
5. **Poor error handling** - Scripts didn't gracefully handle Docker being unavailable

## Fixes Implemented

### 1. Smart Container Management (`scripts/docker_health_manager.py`)

- **Container reuse**: Checks if containers are already healthy before starting
- **Graceful fallbacks**: Handles Docker being unavailable or containers not existing
- **Intelligent restart policies**: Only restarts containers when actually needed
- **Health monitoring**: Proper health check validation before considering services ready

### 2. Unified Docker Interface (`scripts/test_docker_manager.py`)

- **Environment-aware**: Supports both test and dev environments with `--env` flag
- **Service discovery**: Automatically discovers correct service names per environment
- **Data reset without restart**: Can reset database/cache data without killing containers
- **URL discovery**: Provides correct connection URLs based on actual port mappings

### 3. Updated Docker Compose Configs

#### Changes to `docker-compose.yml` and `docker-compose.test.yml`:
```diff
- restart: unless-stopped
+ restart: no  # Changed from unless-stopped to prevent unwanted auto-restarts
```

This prevents containers from automatically restarting when they're intentionally stopped during testing.

### 4. Enhanced Test Framework (`test_framework/docker_test_manager.py`)

#### Key improvements:
- **Container reuse check** before starting services
- **Removed `--remove-orphans` flag** to prevent killing unrelated containers
- **Better error handling** for Docker unavailable scenarios

```python
# Before: Always used --remove-orphans
cmd.extend(["up", "-d", "--remove-orphans"])

# After: Check existing containers first, no orphan removal
existing_check = subprocess.run([...])
running_services = set(existing_check.stdout.strip().split('\n'))
services_to_start = requested_services - running_services

if not services_to_start:
    print("All requested services already running, reusing containers")
    return True

cmd.extend(["up", "-d"])  # No --remove-orphans
```

## Usage Examples

### Test Environment Management
```bash
# Check status
python scripts/test_docker_manager.py status --env test

# Start test services (only starts what's needed)
python scripts/test_docker_manager.py start --env test

# Reset data without restarting containers
python scripts/test_docker_manager.py reset --env test

# Cleanup when needed
python scripts/test_docker_manager.py cleanup --env test --force
```

### Dev Environment Management
```bash
# Check dev environment status
python scripts/test_docker_manager.py status --env dev

# Start dev services
python scripts/test_docker_manager.py start --env dev

# Get connection URLs
python scripts/test_docker_manager.py urls --env dev
```

### Low-level Health Management
```bash
# Check container health
python scripts/docker_health_manager.py status -f docker-compose.test.yml

# Smart restart (only if needed)
python scripts/docker_health_manager.py restart test-postgres test-redis

# Start with health waiting
python scripts/docker_health_manager.py start test-postgres test-redis
```

## Benefits

### Performance Improvements:
- **Faster test startup**: Reuses existing healthy containers instead of recreating
- **Reduced CI/CD time**: No unnecessary container recreation
- **Better resource usage**: Containers stay alive between test runs

### Stability Improvements:
- **No accidental container kills**: Removed `--remove-orphans` flag
- **Graceful degradation**: Handles Docker being unavailable
- **Predictable behavior**: No auto-restarts from `unless-stopped` policy

### Developer Experience:
- **Clear status reporting**: Easy to see what's running and what's not
- **Environment isolation**: Dev and test environments properly separated
- **Smart defaults**: Sensible service combinations for different use cases

## Migration Guide

### For Test Scripts:
```python
# Before:
subprocess.run(["docker-compose", "-f", "docker-compose.test.yml", "up", "-d", "--remove-orphans"])

# After:  
from scripts.test_docker_manager import TestDockerManager
manager = TestDockerManager("test")
manager.ensure_services(["test-postgres", "test-redis"])
```

### For Dev Environment:
```python
# Before:
subprocess.run(["docker-compose", "up", "-d"])

# After:
from scripts.test_docker_manager import TestDockerManager  
manager = TestDockerManager("dev")
manager.ensure_services(["dev-postgres", "dev-redis"])
```

## Monitoring

The new system provides better observability:

- **Health status**: Clear indication of container health
- **Reuse notifications**: Shows when containers are reused vs recreated  
- **Environment separation**: Distinct logging for test vs dev
- **Error context**: Better error messages when things go wrong

## Rollback Plan

If issues arise, the changes can be easily reverted:

1. Restore `restart: unless-stopped` in compose files
2. Add back `--remove-orphans` in test_framework/docker_test_manager.py:162
3. Use original subprocess calls instead of new manager classes

The new scripts are additive and don't break existing workflows.