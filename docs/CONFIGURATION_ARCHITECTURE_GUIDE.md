# Configuration Architecture Guide - Issue #558 Resolution

**Created:** 2025-09-12  
**Purpose:** Prevent configuration debt and maintain SSOT compliance  
**Related Issue:** #558 - Missing pytest.ini configuration files

## Architecture Decision: Centralized Configuration SSOT

### Problem Solved
Issue #558 identified configuration management architectural debt where the unified test runner expected service-specific pytest.ini files that were deleted during configuration consolidation. This created a broken hybrid configuration model.

### Solution: SSOT Configuration Architecture

**Primary Configuration**: All pytest configuration consolidated in `/pyproject.toml`

```toml
[tool.pytest.ini_options]
# Centralized pytest configuration for all services
testpaths = [
    "tests",
    "netra_backend/tests", 
    "auth_service/tests"
]
# 200+ markers consolidated in one location
markers = [
    "unit: Unit tests (fast, isolated)",
    "integration: Integration tests (component interaction)",
    # ... complete marker definitions
]
```

**Service Integration**: Unified test runner updated to use centralized config:

```python
self.test_configs = {
    "backend": {
        "config": "pyproject.toml",  # SSOT config
        "test_dir": "netra_backend/tests"
    },
    "auth": {
        "config": "pyproject.toml",  # SSOT config  
        "test_dir": "auth_service/tests"
    }
}
```

### Benefits

1. **SSOT Compliance**: Single configuration source prevents drift
2. **Maintenance Reduction**: No duplicate configurations to maintain
3. **Modern Best Practices**: Aligns with pytest 6.0+ recommendations
4. **Future-Proof**: Prevents similar configuration debt

### Migration Guidelines

#### For New Services
- **DO**: Add service test paths to `pyproject.toml` testpaths
- **DO**: Use centralized marker definitions
- **DON'T**: Create service-specific pytest.ini files

#### For Test Infrastructure  
- **DO**: Reference `pyproject.toml` for all pytest configuration
- **DON'T**: Hardcode references to service-specific config files
- **VALIDATE**: Check for missing configuration files before deployment

### Service-Specific Overrides (If Needed)

**Option 1: Environment Variables**
```python
# In service conftest.py
import os
import pytest

def pytest_configure(config):
    if os.getenv('SERVICE_NAME') == 'backend':
        # Service-specific configuration
        config.option.timeout = 60
```

**Option 2: Dynamic Markers**
```python
# In conftest.py
def pytest_collection_modifyitems(config, items):
    for item in items:
        if "netra_backend" in str(item.fspath):
            item.add_marker(pytest.mark.backend)
```

### Validation Commands

```bash
# Verify centralized config works
python -m pytest -c pyproject.toml --collect-only

# Test service-specific execution
python -m pytest -c pyproject.toml netra_backend/tests/unit
python -m pytest -c pyproject.toml auth_service/tests

# Validate marker definitions
python -m pytest -c pyproject.toml --markers
```

### Anti-Patterns to Avoid

❌ **Service-Specific pytest.ini Files**
```ini
# DON'T CREATE: netra_backend/pytest.ini
[pytest]
addopts = --tb=short
```

❌ **Hardcoded Config Paths**
```python
# DON'T DO THIS:
config_path = f"{service_name}/pytest.ini"  # File may not exist
```

❌ **Configuration Duplication**
```toml
# DON'T DUPLICATE markers across files
```

### Monitoring and Maintenance

1. **Configuration Drift Prevention**: Regular audits of configuration references
2. **Documentation Updates**: Keep all docs aligned with centralized approach  
3. **Developer Education**: Ensure new team members understand SSOT principles

### Related Architecture Documents

- `/CLAUDE.md` - SSOT compliance requirements
- `/pyproject.toml` - Primary configuration file
- `/tests/unified_test_runner.py` - Configuration consumption

---

*This guide prevents configuration debt like Issue #558 from recurring*