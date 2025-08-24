# Environment Variable Conflicts Solution

## Problem Summary

The dev launcher had multiple components setting and resetting environment variables causing conflicts:

1. **Secret loader** (line 172): Sets ALL loaded secrets to os.environ
2. **Auth starter** (lines 209-210): Sets AUTH_SERVICE_PORT and AUTH_SERVICE_URL  
3. **Service startup** (lines 289-290): Sets the SAME AUTH_SERVICE_PORT/URL (duplicate!)
4. **Database connector** (line 120): Sets database connection vars
5. **Launcher** (multiple places): Sets defaults, CROSS_SERVICE_AUTH_TOKEN, NETRA_SECRETS_LOADING
6. **Environment validator** (line 430): Sets fallback values

This caused:
- Race conditions where values get overwritten
- Duplicate setting of the same variables
- Temporary flags being set/deleted causing timing issues
- Environment pollution in tests

## Solution: EnvironmentManager

### 1. Created EnvironmentManager Class (`dev_launcher/environment_manager.py`)

A singleton environment manager that:

- **Prevents conflicts**: First setter wins unless explicit override allowed
- **Tracks sources**: Knows which component set each variable
- **Isolation mode**: In development, variables don't pollute `os.environ`
- **Thread-safe**: Safe for concurrent access
- **Temporary flags**: Context manager for flags that auto-cleanup

Key features:
```python
class EnvironmentManager:
    def set_environment(self, key, value, source, allow_override=False) -> bool
    def get_environment(self, key, default=None) -> Optional[str]
    def has_variable(self, key) -> bool
    def set_temporary_flag(self, key, value, source) -> TemporaryFlag
    def bulk_set_environment(self, variables, source) -> Dict[str, bool]
    def get_conflicts_report() -> Dict[str, Any]
```

### 2. Updated Components to Use EnvironmentManager

#### secret_loader.py
```python
# BEFORE: Direct os.environ setting
for key, value in secrets.items():
    os.environ[key] = value
    self.loaded_secrets[key] = value

# AFTER: Uses EnvironmentManager
for key, value in secrets.items():
    if self.env_manager.set_environment(key, value, source="secret_loader"):
        self.loaded_secrets[key] = value
    else:
        logger.warning(f"Failed to set {key} due to conflict prevention")
```

#### auth_starter.py
```python
# BEFORE: Direct os.environ setting
os.environ["AUTH_SERVICE_PORT"] = str(port)
os.environ["AUTH_SERVICE_URL"] = f"http://localhost:{port}"

# AFTER: Uses EnvironmentManager with allow_override
self.env_manager.set_environment("AUTH_SERVICE_PORT", str(port), 
                               source="auth_starter", allow_override=True)
self.env_manager.set_environment("AUTH_SERVICE_URL", f"http://localhost:{port}", 
                               source="auth_starter", allow_override=True)
```

#### service_startup.py
```python
# BEFORE: Duplicate AUTH_SERVICE setting
def _update_backend_auth_config(self, auth_port: int):
    os.environ["AUTH_SERVICE_PORT"] = str(auth_port)
    os.environ["AUTH_SERVICE_URL"] = f"http://localhost:{auth_port}"

# AFTER: Removed duplicate setting, auth_starter handles it
def _update_backend_auth_config(self, auth_port: int):
    """NOTE: This method is now redundant as auth_starter.py handles
    setting AUTH_SERVICE_PORT/URL directly via EnvironmentManager."""
    logger.debug(f"Auth port {auth_port} configuration handled by auth_starter")
```

#### launcher.py
```python
# BEFORE: Direct os.environ manipulation
os.environ['NETRA_SECRETS_LOADING'] = 'true'
# ... do work ...
if 'NETRA_SECRETS_LOADING' in os.environ:
    del os.environ['NETRA_SECRETS_LOADING']

# AFTER: Uses temporary flag context manager
with self.env_manager.set_temporary_flag('NETRA_SECRETS_LOADING', 'true', 'launcher_early_load'):
    # ... do work ...
    # Flag automatically cleaned up when exiting context
```

### 3. Isolation Mode for Development/Testing

In development mode (ENVIRONMENT=development), the manager uses **isolation mode**:

- Variables are stored internally but NOT set in `os.environ`
- Prevents test pollution of global environment
- Components can still access variables through the manager
- Production mode (`ENVIRONMENT=production`) sets variables in `os.environ` normally

### 4. Comprehensive Testing

Created two test files:

#### test_environment_conflicts.py (23 tests)
- Unit tests for EnvironmentManager functionality
- Conflict prevention, isolation mode, temporary flags
- Thread safety, bulk operations, source tracking

#### test_env_loading_regression.py (8 tests)  
- Integration tests simulating real dev launcher scenarios
- AUTH_SERVICE_PORT conflict prevention
- NETRA_SECRETS_LOADING temporary flag cleanup
- Environment isolation in development vs production
- Component precedence and conflict tracking

All 31 tests pass, verifying the solution works correctly.

## Results

### Problems Fixed

✅ **No more duplicate AUTH_SERVICE_PORT setting**: auth_starter sets it once, service_startup skips duplicate setting

✅ **Race conditions eliminated**: Temporary flags use context managers for automatic cleanup

✅ **Environment isolation in tests**: Development mode doesn't pollute `os.environ`

✅ **Conflict tracking**: Detailed reporting of which components tried to set conflicting values

✅ **Source tracking**: Always know which component set each variable

✅ **Thread safety**: Concurrent access is properly handled

### Backward Compatibility

✅ **Production unchanged**: In production mode, variables still set in `os.environ` normally

✅ **Component interfaces preserved**: Components can still access variables as before

✅ **Fallback behavior**: If EnvironmentManager unavailable, graceful degradation

### Performance Impact

✅ **Minimal overhead**: Manager operations are O(1) with threading locks only where needed

✅ **Singleton pattern**: Single instance shared across all components

✅ **Lazy evaluation**: Manager only created when first accessed

## Usage Examples

```python
from dev_launcher.environment_manager import get_environment_manager

# Get the global manager (auto-detects isolation mode)
manager = get_environment_manager()

# Set a variable (prevents conflicts)
if manager.set_environment("MY_VAR", "value", source="my_component"):
    print("Variable set successfully")
else:
    print("Conflict prevented - variable already set by another component")

# Use temporary flag that auto-cleans up
with manager.set_temporary_flag("LOADING", "true", source="loader"):
    # Flag is available during this block
    do_loading_work()
# Flag automatically removed when exiting block

# Check conflict report
conflicts = manager.get_conflicts_report()
print(f"Prevented {conflicts['total_conflicts']} conflicts")
```

## Monitoring

The EnvironmentManager provides detailed reporting:

```python
status = manager.get_status()
# Returns:
{
    "isolation_mode": True,
    "total_variables": 15,
    "sources": {"secret_loader": 8, "auth_starter": 2, "launcher": 5},
    "conflicts_prevented": 2,
    "variables_by_source": {
        "secret_loader": ["DATABASE_URL", "JWT_SECRET", ...],
        "auth_starter": ["AUTH_SERVICE_PORT", "AUTH_SERVICE_URL"],
        ...
    }
}
```

This solution ensures predictable, conflict-free environment variable management across the entire dev launcher system.