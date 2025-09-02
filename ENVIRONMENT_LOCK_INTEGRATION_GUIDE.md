# Environment Lock Integration Guide

## Overview
The `test_framework/environment_lock.py` module provides standalone environment locking functionality extracted and enhanced from `UnifiedDockerManager`. This addresses the critical remediation requirement to prevent concurrent environment usage across development and test processes.

## Key Features Implemented

### ✅ Core Requirements Met
- **Prevent concurrent environment usage** - Dev vs Test isolation 
- **Cross-platform support** - Windows (msvcrt) and Unix (fcntl) file locking
- **Timeout-based lock acquisition** - Configurable timeout with exponential backoff
- **Multiple environment types** - Dev, Test, Staging, Production support
- **File-based persistence** - Locks survive process restarts
- **State tracking** - Full metadata on who holds locks when and why

### ✅ Enhanced Capabilities
- **Lock metadata tracking** - Who, when, why, hostname, PID
- **Automatic stale lock cleanup** - Configurable staleness detection
- **Thread-safe operations** - RLock protection for concurrent access
- **Force release capabilities** - Admin override for stuck locks
- **Context manager support** - Automatic cleanup on exit
- **Comprehensive logging** - Full audit trail of lock operations

## Integration with Existing Systems

### Docker Testing Integration
```python
# In your test setup
from test_framework.environment_lock import EnvironmentLock

# Prevent test/dev conflicts
with EnvironmentLock() as env_lock:
    # Acquire appropriate environment lock
    env_lock.acquire_test(timeout=60, purpose="E2E test suite execution")
    
    # Now safe to start Docker services for testing
    docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
    docker_manager.start_services()
    
    # Run tests...
    
    # Lock automatically released on context exit
```

### Test Runner Integration
```python
# In unified_test_runner.py or similar
class TestRunner:
    def __init__(self):
        self.env_lock = EnvironmentLock()
    
    def run_tests_with_real_services(self):
        try:
            # Acquire test environment lock
            self.env_lock.acquire_test(
                timeout=120, 
                purpose="Automated test execution with real services"
            )
            
            # Proceed with Docker service startup
            self.start_docker_services()
            self.run_test_suite()
            
        finally:
            # Always cleanup
            self.env_lock.release_all()
```

### Development Workflow Integration
```python
# In development scripts
def start_dev_environment():
    env_lock = EnvironmentLock()
    
    try:
        env_lock.acquire_dev(timeout=30, purpose="Local development session")
        print("✓ Dev environment locked - safe to start services")
        
        # Start development services
        start_dev_services()
        
    except LockAcquisitionTimeout:
        print("✗ Dev environment in use - check running processes")
        status = env_lock.check_lock_status("dev")
        print(f"Current holder: {status}")
```

## API Reference

### Primary Methods
```python
# Acquisition (with specific environment methods)
lock.acquire_dev(timeout=60, purpose="Development work")
lock.acquire_test(timeout=60, purpose="Testing")  
lock.acquire_staging(timeout=60, purpose="Staging deployment")
lock.acquire_production(timeout=60, purpose="Production deployment")

# Generic acquisition
lock.acquire(env_name, timeout=60, purpose="Custom environment")

# Release operations
lock.release(env_name)  # Release specific environment
lock.release_all()      # Release all held locks

# Status checking
status = lock.check_lock_status(env_name)
all_locks = lock.list_all_locks()

# Administrative operations
lock.force_release(env_name, reason="Admin override")
lock.cleanup_stale_locks(force=False)
```

### Lock Status Information
```python
# LockStatusInfo properties
status.environment     # Environment name
status.status          # LockStatus enum (AVAILABLE, LOCKED, STALE, ERROR)
status.metadata        # LockMetadata with holder info
status.error_message   # Error details if status is ERROR

# LockMetadata properties  
metadata.holder_id     # Unique process identifier
metadata.hostname      # Machine holding the lock
metadata.acquired_at   # Timestamp when acquired
metadata.purpose       # Human-readable purpose
metadata.timeout       # Lock timeout in seconds
metadata.pid           # Process ID
```

## Configuration Options

### Lock Directory
```python
# Default: Platform-specific temp directory
# Unix: /tmp/netra_env_locks
# Windows: %TEMP%/netra_env_locks

# Custom location
lock = EnvironmentLock(lock_dir=Path("/custom/lock/dir"))
```

### Stale Lock Detection
```python
# Configure staleness threshold and cleanup interval
lock = EnvironmentLock(
    stale_threshold=300,    # Locks stale after 5 minutes past timeout
    cleanup_interval=60     # Check for stale locks every minute
)
```

## Error Handling

### Common Exceptions
- `LockAcquisitionTimeout` - Cannot acquire lock within timeout
- `LockNotHeldError` - Attempting to release lock not held by current process
- `EnvironmentLockError` - Base exception for all lock-related errors

### Best Practices
```python
try:
    with EnvironmentLock() as lock:
        lock.acquire_test(timeout=60, purpose="Test execution")
        # Do work...
        
except LockAcquisitionTimeout as e:
    # Handle timeout - maybe retry or fail gracefully
    logger.error(f"Could not acquire environment lock: {e}")
    
except Exception as e:
    # Handle other errors
    logger.error(f"Unexpected error in environment locking: {e}")
```

## Monitoring and Debugging

### Logging
```python
import logging

# Enable detailed logging
logging.getLogger("EnvironmentLock").setLevel(logging.DEBUG)

# Logs include:
# - Lock acquisition attempts and results
# - Lock release operations  
# - Stale lock cleanup activities
# - Error conditions and failures
```

### Status Checking
```python
# Check all environment locks
lock = EnvironmentLock()
all_locks = lock.list_all_locks()

for lock_info in all_locks:
    print(f"{lock_info.environment}: {lock_info.status.value}")
    if lock_info.metadata:
        print(f"  Held by: {lock_info.metadata.hostname} (PID: {lock_info.metadata.pid})")
        print(f"  Since: {lock_info.metadata.acquired_at}")
        print(f"  Purpose: {lock_info.metadata.purpose}")
```

### Force Cleanup
```python
# Clean up all stale locks (careful in production!)
lock = EnvironmentLock()
cleaned = lock.cleanup_stale_locks(force=True)
print(f"Cleaned up locks: {cleaned}")

# Force release specific environment (admin use)
lock.force_release("dev", reason="Manual intervention required")
```

## Migration from UnifiedDockerManager

### Before (UnifiedDockerManager internal locking)
```python
# Locking was internal and not reusable
docker_manager = UnifiedDockerManager()
with docker_manager._file_lock("environment", timeout=30):
    # Limited to Docker operations only
    pass
```

### After (Standalone EnvironmentLock)
```python
# Reusable across all systems
from test_framework.environment_lock import EnvironmentLock

with EnvironmentLock() as env_lock:
    env_lock.acquire_dev(timeout=60, purpose="Multi-system coordination")
    # Use for Docker, tests, deployments, etc.
```

## Testing the Module

### Quick Verification
```python
from test_framework.environment_lock import EnvironmentLock

# Test basic functionality
with EnvironmentLock() as lock:
    success = lock.acquire_dev(timeout=5, purpose="Quick test")
    print(f"Lock acquired: {success}")
    
    status = lock.check_lock_status("dev")
    print(f"Status: {status}")
```

### Run Full Test Suite
```bash
# Run pytest tests (if pytest available)
cd test_framework
python -m pytest tests/test_environment_lock.py -v

# Or run manual test
python tests/test_environment_lock.py
```

## Security Considerations

### File Permissions
- Lock files created in temp directories with standard permissions
- Metadata files contain no sensitive information
- Cross-platform file locking respects OS security models

### Process Identification
- Uses hostname + PID + timestamp for unique holder identification
- Stale lock detection based on process existence and timeouts
- Force release requires administrative decision

## Performance Characteristics

### Lock Acquisition
- **Typical time**: <10ms for available locks
- **Timeout behavior**: 100ms retry intervals with configurable timeout
- **Concurrent access**: Thread-safe with RLock protection

### Storage Overhead
- **Lock files**: <1KB per environment 
- **Metadata file**: <5KB for all environments combined
- **Cleanup frequency**: Configurable, default 60s intervals

## Production Deployment Notes

### Environment Separation
```python
# Use different lock directories per environment
prod_lock = EnvironmentLock(lock_dir=Path("/var/lock/netra/production"))
staging_lock = EnvironmentLock(lock_dir=Path("/var/lock/netra/staging"))
```

### Monitoring Integration
```python
# Add monitoring hooks
class MonitoredEnvironmentLock(EnvironmentLock):
    def acquire(self, env_name, timeout=60, purpose=""):
        start_time = time.time()
        try:
            result = super().acquire(env_name, timeout, purpose)
            # Report success metric
            self.metrics.record_acquisition_success(env_name, time.time() - start_time)
            return result
        except LockAcquisitionTimeout:
            # Report timeout metric
            self.metrics.record_acquisition_timeout(env_name, timeout)
            raise
```

This module provides a robust foundation for preventing environment conflicts while maintaining the flexibility and reliability required for the Netra development and testing infrastructure.