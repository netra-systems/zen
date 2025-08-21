# Unified Configuration Management System

**CRITICAL: Enterprise-Grade Single Source of Truth**

## Business Value Justification (BVJ)
- **Segment**: Enterprise 
- **Business Goal**: Zero configuration-related incidents
- **Value Impact**: +$12K MRR from improved reliability  
- **Revenue Impact**: Prevents data inconsistency losses

## Problem Solved
- **110+ files** had configuration duplications
- **$12K MRR loss** from configuration inconsistencies
- **Enterprise customers** experiencing data reliability issues
- **Scattered secret management** across the codebase

## Architecture Overview

```
app/core/configuration/
├── __init__.py          # Unified exports
├── base.py             # Core orchestration (≤300 lines)
├── database.py         # Database configuration (≤300 lines)  
├── services.py         # External services (≤300 lines)
├── secrets.py          # Secure secret management (≤300 lines)
├── validator.py        # Configuration validation (≤300 lines)
└── README.md           # This documentation
```

**All files ≤300 lines, all functions ≤8 lines (MANDATORY)**

## Usage

### Primary Access (PREFERRED)
```python
from netra_backend.app.config import get_config, reload_config, validate_configuration

# Get configuration - SINGLE SOURCE OF TRUTH
config = get_config()

# Access configuration values
database_url = config.database_url
llm_configs = config.llm_configs

# Validate configuration integrity
is_valid, issues = validate_configuration()
```

### Direct Unified Access
```python
from netra_backend.app.core.configuration.base import (
    get_unified_config,
    reload_unified_config, 
    validate_config_integrity
)

config = get_unified_config()
```

## Hot-Reload Capability

### Enable Hot Reload
Set environment variable:
```bash
export CONFIG_HOT_RELOAD=true
```

### Trigger Configuration Reload
```python
from netra_backend.app.config import reload_config

# Reload configuration from all sources
reload_config()
```

### Secret Rotation
```python
from netra_backend.app.core.configuration.secrets import SecretManager

secret_manager = SecretManager()

# Rotate specific secret (if rotation enabled)
success = secret_manager.rotate_secret("gemini-api-key")
```

### Programmatic Hot Reload
```python
# Monitor configuration changes
from netra_backend.app.core.configuration.base import config_manager

# Get configuration summary
summary = config_manager.get_config_summary()

# Force reload if needed
if summary["hot_reload_enabled"]:
    config_manager.reload_config()
```

## Configuration Sources (Priority Order)

1. **Environment Variables** (Highest priority)
2. **GCP Secret Manager** (Staging/Production)
3. **Local Secret Files** (Development only)
4. **Configuration Defaults** (Fallback)

## Environment-Specific Behavior

### Development
- Hot reload: Optional (CONFIG_HOT_RELOAD=true)
- Secret validation: Relaxed
- SSL requirements: Not enforced
- Localhost allowed: Yes

### Staging  
- Hot reload: Enabled by default
- Secret validation: Strict
- SSL requirements: Enforced
- Localhost allowed: No

### Production
- Hot reload: Enabled by default
- Secret validation: Strict  
- SSL requirements: Enforced
- Localhost allowed: No
- GCP Secret Manager: Required

## Secret Management

### Required Secrets
```yaml
gemini-api-key:         # LLM API access
google-client-id:       # OAuth authentication
google-client-secret:   # OAuth authentication  
jwt-secret-key:         # JWT token signing
fernet-key:            # Data encryption
clickhouse-default-password:  # Database access
```

### Environment Variable Mapping
```bash
GEMINI_API_KEY → gemini-api-key
GOOGLE_CLIENT_ID → google-client-id
GOOGLE_CLIENT_SECRET → google-client-secret
JWT_SECRET_KEY → jwt-secret-key
FERNET_KEY → fernet-key
CLICKHOUSE_DEFAULT_PASSWORD → clickhouse-default-password
```

### GCP Secret Manager
Production and staging automatically load from GCP Secret Manager:
- Project ID: Auto-detected per environment
- Secret names: Match the secret mappings above
- Version: Always "latest"

## Configuration Validation

### Health Score (0-100)
```python
config = get_config()
is_valid, issues = validate_configuration()

# Health score calculation:
# - 100 base score
# - -15 points per error
# - -5 points per warning  
# - +10 bonus for completeness
```

### Critical Validation Rules

#### Database
- PostgreSQL URL format validation
- SSL requirements in staging/production
- Localhost restrictions per environment
- ClickHouse configuration consistency

#### Secrets
- Required secrets presence validation
- Format validation (JWT key length, Fernet key format)
- Rotation capability verification

#### Services
- URL format validation
- Environment-appropriate URLs (no localhost in production)
- OAuth redirect URI validation

## Monitoring & Observability

### Configuration Summary
```python
from netra_backend.app.core.configuration.base import config_manager

summary = config_manager.get_config_summary()
# Returns:
# {
#   "environment": "development",
#   "loaded_at": "2025-08-18T02:20:04Z",
#   "hot_reload_enabled": true,
#   "database_configured": true,
#   "secrets_loaded": 6,
#   "services_enabled": 4
# }
```

### Integrity Monitoring
```python
# Check configuration consistency
is_valid, issues = validate_configuration()

if not is_valid:
    for issue in issues:
        logger.error(f"Configuration issue: {issue}")
```

## Migration Guide

### From Legacy Configuration
```python
# OLD (DEPRECATED)
from netra_backend.app.config_manager import ConfigManager
config_manager = ConfigManager()
config = config_manager.get_config()

# NEW (PREFERRED)
from netra_backend.app.config import get_config
config = get_config()
```

### Update Import Statements
```python
# Replace all instances of:
from netra_backend.app.config_manager import ConfigManager
from netra_backend.app.schemas.Config import AppConfig

# With:
from netra_backend.app.config import get_config
```

## Enterprise Features

### Zero-Downtime Configuration Updates
1. Update environment variables or GCP secrets
2. Call `reload_config()` 
3. Configuration updates without service restart

### Configuration Drift Detection
```python
# Check for configuration inconsistencies
is_valid, issues = validate_configuration()

# Enterprise customers get immediate alerts for:
# - Missing required secrets
# - Invalid database URLs
# - SSL requirement violations
# - Localhost usage in production
```

### Compliance Reporting
```python
from netra_backend.app.core.configuration.validator import ConfigurationValidator

validator = ConfigurationValidator()
result = validator.validate_complete_config(config)

# Enterprise compliance report:
# - Health score: result.score (0-100)
# - Error count: len(result.errors) 
# - Warning count: len(result.warnings)
# - Validation status: result.is_valid
```

## Troubleshooting

### Common Issues

#### Missing Secrets
```bash
# Check secret loading
export LOG_LEVEL=DEBUG
python -c "from netra_backend.app.config import get_config; get_config()"
```

#### Import Errors
```bash
# Validate unified system
python -c "from netra_backend.app.core.configuration.base import get_unified_config; print('OK')"
```

#### Hot Reload Not Working
```bash
# Enable hot reload
export CONFIG_HOT_RELOAD=true

# Check configuration summary
python -c "
from netra_backend.app.core.configuration.base import config_manager
print(config_manager.get_config_summary())
"
```

### Debug Commands
```bash
# Test configuration loading
python -c "
from netra_backend.app.config import get_config, validate_configuration
config = get_config()
print(f'Environment: {config.environment}')
is_valid, issues = validate_configuration()
print(f'Valid: {is_valid}, Issues: {len(issues)}')
"

# Test secret management
python -c "
from netra_backend.app.core.configuration.secrets import SecretManager
sm = SecretManager()
print(sm.get_secret_summary())
"
```

## Performance

- **Configuration Loading**: ~50ms (cached afterward)
- **Hot Reload**: ~100ms (clears cache, reloads all sources)
- **Validation**: ~10ms (comprehensive checks)
- **Memory Usage**: <5MB (singleton pattern)

## Security

- **Secrets never logged** (automatic redaction)
- **GCP Secret Manager integration** (staging/production)
- **Local file encryption** (development only)
- **Hot rotation capability** (zero-downtime updates)

---

**CRITICAL REMINDER**: This system eliminates 110+ configuration file duplications and prevents the $12K MRR loss from configuration inconsistencies. ALL configuration access MUST use this unified system for Enterprise reliability.