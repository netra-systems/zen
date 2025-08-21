# CRITICAL: NEVER Use Direct os.environ Access

## Business Impact
Direct `os.environ` calls cause $12K MRR loss from configuration inconsistencies.
Enterprise customers require absolute configuration reliability.

## The Rule
**NEVER use `os.environ.get()`, `os.environ[]`, or `os.getenv()` directly.**

## The ONLY Way to Access Configuration

```python
from netra_backend.app.core.configuration import unified_config_manager

# Get the singleton instance
config_manager = unified_config_manager
config = config_manager.get_config()

# Access any configuration value
database_url = config.database_url
api_key = config.api_key
environment = config.environment
```

## Why This Matters

1. **Consistency**: All configuration goes through validation
2. **Type Safety**: Pydantic models ensure correct types
3. **Caching**: Configuration is loaded once and cached
4. **Hot Reload**: Configuration can be reloaded without restart
5. **Secret Management**: Secrets are properly loaded from Secret Manager
6. **Environment Detection**: Proper staging/production detection

## The ONLY Exceptions

Bootstrap methods in `base.py` that run BEFORE configuration is loaded:
- `_detect_environment()` - Initial environment detection
- `_check_hot_reload_enabled()` - Initial hot reload check

These are clearly marked with CRITICAL comments explaining why.

## Common Mistakes to Avoid

```python
# WRONG - Direct environment access
import os
port = os.environ.get("PORT", 8080)

# WRONG - Direct getenv
import os
api_key = os.getenv("API_KEY")

# WRONG - Direct environ dictionary
import os
if os.environ["TESTING"]:
    ...
```

## Correct Approach

```python
# RIGHT - Use unified config manager
from netra_backend.app.core.configuration import unified_config_manager

config = unified_config_manager.get_config()
port = config.port
api_key = config.api_key
if config.testing:
    ...
```

## Migration Checklist

When you find direct `os.environ` usage:

1. Import the unified config manager
2. Get the config object
3. Replace `os.environ.get("KEY")` with `config.key`
4. Remove the `import os` if no longer needed
5. Test that the value is still accessible

## Validation

Run this command to find violations:
```bash
grep -r "os\.environ\|os\.getenv" app/ --include="*.py" | grep -v "base.py"
```

Any results (except in base.py bootstrap methods) are violations that must be fixed.

## Enforcement

- Code reviews MUST reject any PR with direct env access
- Tests MUST verify configuration comes from unified manager
- CI/CD MUST fail on direct env access patterns

Remember: Configuration inconsistencies directly impact revenue. 
Every direct `os.environ` call is a potential $12K MRR loss.