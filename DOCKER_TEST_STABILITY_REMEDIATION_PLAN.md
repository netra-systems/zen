# Docker Test Environment Stability - Remediation Plan
## Date: 2025-09-02
## Priority: CRITICAL

---

## Problem Summary

The test Docker environment is unstable due to:
1. **Resource exhaustion** from tmpfs volumes consuming 3GB+ RAM
2. **Orphaned resources** - 9 test networks found lingering
3. **Configuration divergence** between dev (stable) and test (crashes)
4. **No cleanup mechanisms** leading to resource accumulation

---

## Immediate Actions (P0 - Do Now)

### 1. Clean Orphaned Resources
```bash
# EXECUTE NOW to free resources
# Remove orphaned test networks
docker network ls --filter "name=netra-test-" -q | xargs -r docker network rm

# Remove orphaned test containers
docker ps -aq --filter "name=test-" | xargs -r docker rm -f

# Prune system
docker system prune -f --volumes
```

### 2. Fix Test Environment Resource Usage

**File**: `docker-compose.test.yml`

**Changes Required**:
1. Replace tmpfs with limited volumes
2. Add strict resource limits
3. Fix health check timing

```yaml
# REPLACE tmpfs volumes with size-limited volumes
test-postgres:
  volumes:
    - test_postgres_data:/var/lib/postgresql/data  # Remove tmpfs
    
  deploy:
    resources:
      limits:
        memory: 512M  # Add strict limit
        cpus: '0.3'
      reservations:
        memory: 256M

# REDUCE PostgreSQL aggressive settings
  command: |
    postgres
      -c shared_buffers=128MB      # Reduced from 256MB
      -c effective_cache_size=512MB # Reduced from 1GB
      -c fsync=on                   # Changed from off
      -c synchronous_commit=on      # Changed from off

# Similar changes for redis and clickhouse
```

### 3. Add Mandatory Cleanup to Test Runner

**File**: `tests/unified_test_runner.py`

**Add at line ~500 (in run_tests function)**:
```python
def cleanup_test_environment():
    """Mandatory cleanup before and after tests"""
    logger.info("Cleaning up test environment...")
    
    # Stop test containers
    subprocess.run([
        "docker", "compose", "-f", "docker-compose.test.yml",
        "down", "--volumes", "--remove-orphans"
    ], capture_output=True)
    
    # Remove orphaned containers
    result = subprocess.run([
        "docker", "ps", "-aq", "--filter", "name=test-"
    ], capture_output=True, text=True)
    
    if result.stdout.strip():
        container_ids = result.stdout.strip().split('\n')
        subprocess.run(["docker", "rm", "-f"] + container_ids)
    
    # Remove orphaned networks
    result = subprocess.run([
        "docker", "network", "ls", "--filter", "name=netra-test-", "-q"
    ], capture_output=True, text=True)
    
    if result.stdout.strip():
        network_ids = result.stdout.strip().split('\n')
        subprocess.run(["docker", "network", "rm"] + network_ids)

# Call before and after test execution
cleanup_test_environment()  # Before
try:
    # ... run tests ...
finally:
    cleanup_test_environment()  # After
```

---

## Short-term Fixes (P1 - This Week)

### 1. Create Base Configuration

**New File**: `docker-compose.base.yml`
```yaml
version: '3.8'

# Shared configurations
x-default-healthcheck: &default-healthcheck
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 20s

x-default-resources: &default-resources
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: '0.25'
      reservations:
        memory: 256M

x-default-logging: &default-logging
  logging:
    driver: json-file
    options:
      max-size: "10m"
      max-file: "3"
```

### 2. Implement Environment Lock

**New File**: `test_framework/environment_lock.py`
```python
import fcntl
import os
from pathlib import Path

class EnvironmentLock:
    """Prevent concurrent environment usage"""
    
    LOCK_DIR = Path.home() / ".netra" / "locks"
    
    def __init__(self):
        self.LOCK_DIR.mkdir(parents=True, exist_ok=True)
        self.dev_lock = None
        self.test_lock = None
    
    def acquire_dev(self, timeout=60):
        """Acquire dev environment lock"""
        lock_file = self.LOCK_DIR / "dev.lock"
        self.dev_lock = open(lock_file, 'w')
        try:
            fcntl.flock(self.dev_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except IOError:
            return False
    
    def acquire_test(self, timeout=60):
        """Acquire test environment lock"""
        lock_file = self.LOCK_DIR / "test.lock"
        self.test_lock = open(lock_file, 'w')
        try:
            fcntl.flock(self.test_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except IOError:
            return False
    
    def release_all(self):
        """Release all locks"""
        if self.dev_lock:
            fcntl.flock(self.dev_lock, fcntl.LOCK_UN)
            self.dev_lock.close()
        if self.test_lock:
            fcntl.flock(self.test_lock, fcntl.LOCK_UN)
            self.test_lock.close()
```

### 3. Add Resource Monitor

**New File**: `test_framework/resource_monitor.py`
```python
import psutil
import docker
import logging

logger = logging.getLogger(__name__)

class DockerResourceMonitor:
    """Monitor Docker resource usage"""
    
    MAX_MEMORY_GB = 4  # Maximum allowed for test environment
    MAX_CONTAINERS = 20  # Maximum concurrent containers
    
    def __init__(self):
        self.client = docker.from_env()
    
    def check_system_resources(self):
        """Check if system has enough resources"""
        mem = psutil.virtual_memory()
        available_gb = mem.available / (1024**3)
        
        if available_gb < self.MAX_MEMORY_GB:
            raise ResourceError(
                f"Insufficient memory: {available_gb:.1f}GB available, "
                f"need {self.MAX_MEMORY_GB}GB"
            )
        
        # Check Docker daemon responsive
        try:
            self.client.ping()
        except Exception as e:
            raise ResourceError(f"Docker daemon not responsive: {e}")
    
    def cleanup_if_needed(self):
        """Clean up if approaching limits"""
        containers = self.client.containers.list(all=True)
        test_containers = [c for c in containers if 'test-' in c.name]
        
        if len(test_containers) > self.MAX_CONTAINERS:
            logger.warning(f"Too many test containers: {len(test_containers)}")
            # Stop oldest containers
            test_containers.sort(key=lambda c: c.attrs['Created'])
            for container in test_containers[:-10]:  # Keep last 10
                logger.info(f"Removing old container: {container.name}")
                container.remove(force=True)
```

---

## Long-term Solutions (P2 - Next Sprint)

### 1. Unified Test Orchestration

Create a single entry point for all test execution that enforces:
- Resource limits
- Cleanup procedures  
- Environment locking
- Health monitoring

### 2. Alpine-based Test Images

Reduce memory footprint by 40%:
- postgres:15-alpine (already using)
- redis:7-alpine (already using)
- clickhouse/clickhouse-server:23-alpine (need to switch)

### 3. Automated Cleanup Cron

Run every 30 minutes:
```python
# scripts/docker_cleanup_cron.py
#!/usr/bin/env python3

import subprocess
import time
import logging

def cleanup():
    """Periodic cleanup of Docker resources"""
    # Clean test resources older than 1 hour
    subprocess.run([
        "docker", "container", "prune", 
        "--filter", "label=netra.env=test",
        "--filter", "until=1h",
        "-f"
    ])
    
    # Prune networks
    subprocess.run(["docker", "network", "prune", "-f"])
    
    # Prune volumes (carefully)
    subprocess.run([
        "docker", "volume", "prune",
        "--filter", "label=netra.env=test",
        "-f"
    ])

if __name__ == "__main__":
    while True:
        cleanup()
        time.sleep(1800)  # 30 minutes
```

---

## Validation Checklist

- [ ] No orphaned test networks after test run
- [ ] Memory usage stays below 4GB during tests
- [ ] Test environment starts in < 30 seconds
- [ ] 10 parallel test runs complete without crashes
- [ ] Dev and test environments can run simultaneously
- [ ] All test categories pass with --real-services flag

---

## Expected Outcomes

After implementing these changes:

1. **Stability**: Test environment as stable as dev
2. **Performance**: 50% reduction in memory usage
3. **Reliability**: Zero Docker daemon crashes
4. **Cleanup**: Automatic resource management
5. **Monitoring**: Proactive issue detection

---

## Implementation Order

1. **NOW**: Execute immediate cleanup commands
2. **TODAY**: Modify docker-compose.test.yml 
3. **TODAY**: Add cleanup to unified_test_runner.py
4. **THIS WEEK**: Implement environment locking
5. **THIS WEEK**: Add resource monitoring
6. **NEXT SPRINT**: Full orchestration refactor

---

## Success Metrics

Track for 7 days after implementation:
- Docker daemon crashes: Target 0 (currently 5-10/day)
- Orphaned containers: Target 0 (currently 50+)
- Test execution time: Target < 5 min (currently 10+ min)
- Memory usage: Target < 4GB peak (currently 6GB+)
- Parallel test success: Target 100% (currently 60%)