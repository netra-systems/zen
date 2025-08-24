# Logging Migration Guide - Eliminating 489+ Duplicate Patterns

This guide shows how to migrate from duplicate logging patterns to the unified logging system.

## Quick Migration Examples

### Pattern 1: Basic logging.getLogger() (Most Common - 481 files)

**OLD (DUPLICATE):**
```python
import logging

# This pattern appears 481+ times across the codebase
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

**NEW (UNIFIED):**
```python
from shared.logging import get_logger

# Single line replaces all the above
logger = get_logger(__name__)
```

### Pattern 2: Auth Service Logging (auth_service/main.py and others)

**OLD (DUPLICATE):**
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

**NEW (UNIFIED):**
```python
from shared.logging import get_logger, configure_service_logging

# Configure service-specific settings once at startup
configure_service_logging({
    'service_name': 'auth-service',
    'enable_file_logging': True
})

logger = get_logger(__name__)
```

### Pattern 3: Dev Launcher Logging (Multiple files)

**OLD (DUPLICATE):**
```python
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
```

**NEW (UNIFIED):**
```python
from shared.logging import get_logger

logger = get_logger(__name__)
```

### Pattern 4: Central Logger Import (netra_backend)

**OLD (DUPLICATE):**
```python
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)
```

**NEW (UNIFIED):**
```python
from shared.logging import get_logger

logger = get_logger(__name__)
```

### Pattern 5: Test Files Logging

**OLD (DUPLICATE):**
```python
import logging

class TestSomething:
    def setup_method(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
```

**NEW (UNIFIED):**
```python
from shared.logging import get_logger

class TestSomething:
    def setup_method(self):
        self.logger = get_logger(__name__)
```

## Service-Specific Configuration

### Auth Service (auth_service/main.py)

```python
from shared.logging import get_logger, configure_service_logging

# Configure once at startup
configure_service_logging({
    'service_name': 'auth-service',
    'enable_file_logging': True,
    'level': logging.INFO
})

logger = get_logger(__name__)
```

### Dev Launcher (dev_launcher/launcher.py)

```python
from shared.logging import get_logger, configure_service_logging

# Configure for development mode
configure_service_logging({
    'service_name': 'dev-launcher',
    'level': logging.DEBUG,  # More verbose for development
    'enable_file_logging': False  # Console only for dev
})

logger = get_logger(__name__)
```

### Backend Service (netra_backend/app/main.py)

```python
from shared.logging import get_logger, configure_service_logging

# Configure for backend service
configure_service_logging({
    'service_name': 'netra-backend',
    'enable_file_logging': True
})

logger = get_logger(__name__)
```

## Migration Script Pattern

To automatically migrate files, use this pattern:

```bash
# Find and replace import logging + basicConfig + getLogger patterns
grep -r "import logging" --include="*.py" . | while read file; do
    # Replace the patterns with unified imports
    sed -i 's/import logging/from shared.logging import get_logger/' "$file"
    sed -i '/logging.basicConfig/d' "$file" 
    sed -i 's/logger = logging.getLogger(__name__)/logger = get_logger(__name__)/' "$file"
done
```

## Benefits of Migration

1. **Eliminates 489+ Duplicate Patterns**: Single source of truth for logging
2. **Consistent Formatting**: All logs follow the same format automatically
3. **Service-Aware**: Logs include service name for better debugging
4. **Environment-Aware**: Automatically adapts to development vs production
5. **File Logging**: Optional file logging with automatic directory creation
6. **Performance**: Cached loggers avoid repeated configuration

## Backward Compatibility

The unified system maintains backward compatibility with existing log calls:
- `logger.info()`, `logger.error()`, etc. work unchanged
- Log levels and formatting are handled automatically
- Existing error handling and exception logging continues to work

## Testing

Test files can use the same pattern:

```python
from shared.logging import get_logger, reset_logging
import pytest

@pytest.fixture(autouse=True)
def reset_logging_for_tests():
    """Reset logging state between tests."""
    reset_logging()
    yield
    reset_logging()

def test_something():
    logger = get_logger(__name__)
    logger.info("Test log message")
    # Test continues as normal
```

## Complete File Migration Example

**Before (auth_service/auth_core/config.py):**
```python
import logging
import os

# Configure logging - DUPLICATE PATTERN
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AuthConfig:
    def __init__(self):
        logger.info("Initializing auth config")
```

**After:**
```python
import os
from shared.logging import get_logger

logger = get_logger(__name__)

class AuthConfig:
    def __init__(self):
        logger.info("Initializing auth config")
```

This migration eliminates 3 lines of duplicate code per file across 481+ files, removing approximately **1,443+ lines of duplicate code**.