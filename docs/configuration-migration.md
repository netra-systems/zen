# Configuration Migration Guide

## Overview

This guide helps you migrate from the legacy configuration system to the new unified configuration system in Netra Apex.

## Migration Timeline

- **v1.x**: Both systems supported (with deprecation warnings)
- **v2.0**: Legacy system removed completely

## Quick Migration

### Before (Legacy System)
```python
# Old way - DEPRECATED
from netra_backend.app.config_manager import ConfigManager
from netra_backend.app.config_loader import load_env_var
from netra_backend.app.config_environment import ConfigEnvironment

config_manager = ConfigManager()
config = config_manager.get_config()
```

### After (Unified System)
```python
# New way - RECOMMENDED
from netra_backend.app.core.configuration import ConfigurationLoader, get_configuration

# Simple usage
config = get_configuration()

# Or with the loader class
loader = ConfigurationLoader()
config = loader.load()
```

## Detailed Migration Steps

### 1. Update Imports

Replace all legacy imports with unified system imports:

```python
# Replace these:
from netra_backend.app.config import get_config
from netra_backend.app.config_manager import ConfigManager
from netra_backend.app.config_loader import load_env_var
from netra_backend.app.config_environment import ConfigEnvironment
from netra_backend.app.config_secrets_manager import ConfigSecretsManager

# With these:
from netra_backend.app.core.configuration import (
    ConfigurationLoader,
    EnvironmentDetector,
    UnifiedSecretManager,
    get_configuration,
    get_environment,
    get_secret
)
```

### 2. Update Configuration Access

#### Getting Configuration

**Old:**
```python
from netra_backend.app.config import get_config
config = get_config()
```

**New:**
```python
from netra_backend.app.core.configuration import get_configuration
config = get_configuration()
```

#### Environment Detection

**Old:**
```python
from netra_backend.app.config_environment import ConfigEnvironment
env = ConfigEnvironment()
environment = env.get_environment()
```

**New:**
```python
from netra_backend.app.core.configuration import EnvironmentDetector
detector = EnvironmentDetector()
environment = detector.detect()

# Or use the helper function
from netra_backend.app.core.configuration import get_environment
environment = get_environment()
```

#### Secret Management

**Old:**
```python
from netra_backend.app.config_secrets_manager import ConfigSecretsManager
secrets_manager = ConfigSecretsManager()
secrets_manager.load_secrets_into_config(config)
```

**New:**
```python
from netra_backend.app.core.configuration import UnifiedSecretManager
secret_manager = UnifiedSecretManager()
secrets = secret_manager.load_all_secrets()

# Or get a specific secret
from netra_backend.app.core.configuration import get_secret
api_key = get_secret("OPENAI_API_KEY")
```

### 3. Update Service-Specific Configuration

#### Database Configuration

**Old:**
```python
config = get_config()
db_url = config.get_database_url()
```

**New:**
```python
loader = ConfigurationLoader()
db_url = loader.get_database_url("postgres")
clickhouse_url = loader.get_database_url("clickhouse")
```

#### Service Configuration

**Old:**
```python
config = get_config()
redis_host = config.REDIS_HOST
redis_port = config.REDIS_PORT
```

**New:**
```python
loader = ConfigurationLoader()
redis_config = loader.get_service_config("redis")
# Returns: {"host": "...", "port": ..., "password": "...", "db": ...}
```

### 4. Update Test Files

Replace test configuration mocks:

**Old:**
```python
from netra_backend.app.config_manager import ConfigManager
with patch.object(ConfigManager, 'get_config') as mock:
    mock.return_value = test_config
```

**New:**
```python
from netra_backend.app.core.configuration import ConfigurationLoader
loader = ConfigurationLoader()
with patch.object(loader._manager, 'get_config') as mock:
    mock.return_value = test_config
```

## Common Patterns

### Pattern 1: Initialization

**Old:**
```python
class MyService:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
```

**New:**
```python
class MyService:
    def __init__(self):
        self.config = get_configuration()
```

### Pattern 2: Environment Checks

**Old:**
```python
import os
if os.environ.get("ENVIRONMENT") == "production":
    # production logic
```

**New:**
```python
from netra_backend.app.core.configuration import is_production
if is_production():
    # production logic
```

### Pattern 3: Hot Reload

**Old:**
```python
config_manager.reload_config()
```

**New:**
```python
from netra_backend.app.core.configuration import reload_configuration
config = reload_configuration(force=True)
```

## Validation

After migration, verify your changes:

1. **Run Tests:**
   ```bash
   python test_runner.py --level integration
   ```

2. **Check for Deprecation Warnings:**
   Look for deprecation warnings in logs when starting the application.

3. **Validate Configuration:**
   ```python
   loader = ConfigurationLoader()
   assert loader.validate()
   ```

## Benefits of Migration

1. **Single Source of Truth**: One unified system instead of 3 competing systems
2. **Better Type Safety**: Full Pydantic validation
3. **Cleaner API**: Simpler, more intuitive methods
4. **Better Testing**: Easier to mock and test
5. **Performance**: Optimized loading with caching
6. **Cloud-Ready**: Built-in support for cloud platforms

## Support

If you encounter issues during migration:

1. Check the deprecation warnings for specific guidance
2. Review test files for migration examples
3. Consult `SPEC/configuration.xml` for architectural details

## Rollback

If you need to temporarily rollback:

1. The legacy system remains available until v2.0
2. You'll see deprecation warnings but functionality is preserved
3. Both systems can coexist during migration

## Final Checklist

- [ ] Updated all imports to use `app.core.configuration`
- [ ] Replaced `get_config()` with `get_configuration()`
- [ ] Updated environment detection code
- [ ] Migrated secret management code
- [ ] Updated all test files
- [ ] Ran full test suite
- [ ] Removed any unused legacy imports
- [ ] Updated CI/CD scripts if needed