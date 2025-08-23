# Hot Reload Configuration System

## 🚨 CRITICAL UPDATE: This Document Needs Update

**This document describes the hot reload system but should be updated to reflect the unified configuration system.**

**Please also see the NEW documentation:**

- **[Configuration Management Guide](./configuration/CONFIGURATION_GUIDE.md)** - Complete guide with unified system
- **[Developer Quick Reference](./configuration/DEVELOPER_QUICK_REFERENCE.md)** - Quick patterns and examples

**The information below may be partially outdated. Use the unified configuration system:**

```python
# NEW UNIFIED WAY
from netra_backend.app.core.configuration.base import get_unified_config

config = get_unified_config()
# Hot reload capabilities are built into the unified system
```

---

## Overview (Legacy Documentation)

The Hot Reload Configuration System enables **zero-downtime configuration updates** for the Netra Apex platform. This enterprise-grade feature allows configuration changes without service restarts, protecting **$12K MRR** from downtime-related losses.

## Business Value Justification (BVJ)

- **Segment**: Enterprise
- **Business Goal**: Zero-downtime configuration updates
- **Value Impact**: Prevents service interruptions during configuration changes
- **Revenue Impact**: Protects $12K MRR from configuration-related downtime

## How It Works

### Architecture

```
Configuration Sources (Priority Order)
├── 1. Environment Variables (Highest)
├── 2. GCP Secret Manager (Staging/Production)
├── 3. Local Secret Files (Development)
└── 4. Configuration Defaults (Fallback)

Hot Reload Process
├── 1. Detect configuration change trigger
├── 2. Clear configuration cache
├── 3. Reload from all sources (in priority order)
├── 4. Validate new configuration
├── 5. Apply atomic update
└── 6. Log reload event
```

### Key Components

1. **ConfigurationManager** (`base.py`): Orchestrates hot reload
2. **SecretManager** (`secrets.py`): Handles secret rotation
3. **ConfigurationValidator** (`validator.py`): Ensures configuration integrity
4. **Cache Layer**: In-memory configuration cache (cleared on reload)

## Enabling Hot Reload

### Method 1: Environment Variable (Recommended)

```bash
# Enable hot reload for your environment
export CONFIG_HOT_RELOAD=true

# Start your application
python scripts/dev_launcher.py
```

### Method 2: Runtime Configuration

```python
from netra_backend.app.config import get_config

# Check if hot reload is enabled
config = get_config()
print(f"Hot reload enabled: {config.hot_reload_enabled}")
```

### Method 3: Per-Environment Defaults

- **Development**: Optional (set CONFIG_HOT_RELOAD=true to enable)
- **Staging**: Enabled by default
- **Production**: Enabled by default

## Using Hot Reload

### Basic Usage

```python
from netra_backend.app.config import reload_config, get_config

# Get current configuration
config = get_config()
print(f"Current DB URL: {config.database_url}")

# Make changes to configuration sources
# (e.g., update environment variables, GCP secrets, etc.)

# Trigger hot reload
reload_config()

# Get updated configuration
config = get_config()
print(f"Updated DB URL: {config.database_url}")
```

### Advanced Usage with Validation

```python
from netra_backend.app.config import (
    reload_config, 
    get_config, 
    validate_configuration
)

# Before reload - check current state
config = get_config()
is_valid, issues = validate_configuration()
print(f"Pre-reload valid: {is_valid}")

# Trigger reload with validation
try:
    reload_config()
    
    # Validate new configuration
    is_valid, issues = validate_configuration()
    if not is_valid:
        print(f"Configuration issues after reload:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Configuration reloaded successfully")
        
except Exception as e:
    print(f"Reload failed: {e}")
    # Configuration remains unchanged on failure
```

### Monitoring Hot Reload

```python
from netra_backend.app.core.configuration.base import config_manager

# Get configuration summary
summary = config_manager.get_config_summary()
print(f"""
Configuration Status:
- Environment: {summary['environment']}
- Loaded at: {summary['loaded_at']}
- Hot reload enabled: {summary['hot_reload_enabled']}
- Secrets loaded: {summary['secrets_loaded']}
- Database configured: {summary['database_configured']}
- Services enabled: {summary['services_enabled']}
""")

# Check reload history (if tracking enabled)
if hasattr(config_manager, 'reload_history'):
    print(f"Reload count: {len(config_manager.reload_history)}")
    print(f"Last reload: {config_manager.reload_history[-1] if config_manager.reload_history else 'Never'}")
```

## Secret Rotation

### Automatic Secret Rotation

```python
from netra_backend.app.core.configuration.secrets import SecretManager

secret_manager = SecretManager()

# Check if rotation is supported
if secret_manager.supports_rotation():
    # Rotate specific secret
    success = secret_manager.rotate_secret("gemini-api-key")
    if success:
        print("Secret rotated successfully")
        
        # Trigger configuration reload to apply new secret
        reload_config()
```

### Manual Secret Update

```bash
# Update secret in GCP Secret Manager (staging/production)
gcloud secrets versions add gemini-api-key --data-file=new_key.txt

# Or update environment variable (development)
export GEMINI_API_KEY="new-api-key-value"

# Trigger reload in your application
curl -X POST http://localhost:8000/admin/reload-config
```

## API Endpoints

### Admin Reload Endpoint

```python
# In your FastAPI app
from fastapi import APIRouter, Depends
from netra_backend.app.config import reload_config
from netra_backend.app.auth_integration import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/reload-config")
async def reload_configuration(
    current_user = Depends(get_current_user)
):
    """
    Trigger hot reload of configuration.
    Requires admin privileges.
    """
    if not current_user.is_admin:
        raise HTTPException(403, "Admin access required")
    
    try:
        reload_config()
        return {"status": "success", "message": "Configuration reloaded"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

## Use Cases

### 1. Database Connection Update

```python
# Scenario: Database migration to new server

# Step 1: Update database URL in environment
os.environ['DATABASE_URL'] = 'postgresql://new-server/db'

# Step 2: Trigger hot reload
reload_config()

# Step 3: Verify new connection
config = get_config()
assert 'new-server' in config.database_url
```

### 2. API Key Rotation

```python
# Scenario: Regular API key rotation for security

# Step 1: Generate new API key
new_key = generate_new_api_key()

# Step 2: Update in GCP Secret Manager
update_secret("gemini-api-key", new_key)

# Step 3: Hot reload to apply
reload_config()

# Step 4: Verify services using new key
config = get_config()
llm_service = LLMService(config.gemini_api_key)
assert llm_service.test_connection()
```

### 3. Feature Flag Toggle

```python
# Scenario: Enable/disable features without restart

# Step 1: Update feature flags
os.environ['FEATURE_NEW_UI'] = 'true'
os.environ['FEATURE_BETA_API'] = 'false'

# Step 2: Hot reload
reload_config()

# Step 3: Features automatically adjust
config = get_config()
if config.feature_new_ui:
    enable_new_ui()
if not config.feature_beta_api:
    disable_beta_api()
```

## Performance Characteristics

### Timing

- **Initial Load**: ~50ms (with caching)
- **Hot Reload**: ~100ms (clears cache, reloads all sources)
- **Validation**: ~10ms (comprehensive checks)
- **Memory Impact**: <5MB (singleton pattern)

### Optimization Tips

1. **Batch Updates**: Update multiple configuration values before reloading
2. **Validate First**: Check configuration validity before applying
3. **Monitor Frequency**: Avoid excessive reloads (recommended: max 1 per minute)
4. **Use Caching**: Configuration is cached between reloads for performance

## Error Handling

### Reload Failures

```python
from netra_backend.app.config import reload_config
import logging

logger = logging.getLogger(__name__)

def safe_reload():
    """
    Safely reload configuration with error handling
    """
    try:
        # Attempt reload
        reload_config()
        logger.info("Configuration reloaded successfully")
        return True
        
    except ValueError as e:
        # Configuration validation failed
        logger.error(f"Invalid configuration: {e}")
        # Configuration remains unchanged
        return False
        
    except ConnectionError as e:
        # Could not connect to GCP Secret Manager
        logger.error(f"Secret Manager connection failed: {e}")
        # Retry with exponential backoff
        return retry_reload_with_backoff()
        
    except Exception as e:
        # Unexpected error
        logger.critical(f"Unexpected reload error: {e}")
        # Alert operations team
        send_critical_alert(f"Config reload failed: {e}")
        return False
```

### Rollback on Failure

```python
from netra_backend.app.config import get_config, reload_config

# Save current configuration
original_config = get_config().dict()

try:
    # Attempt configuration change
    os.environ['DATABASE_URL'] = new_database_url
    reload_config()
    
    # Test new configuration
    if not test_database_connection():
        raise ConnectionError("New database connection failed")
        
except Exception as e:
    # Rollback to original configuration
    for key, value in original_config.items():
        os.environ[key] = str(value)
    reload_config()
    
    logger.error(f"Configuration rollback triggered: {e}")
```

## Monitoring & Observability

### Metrics

```python
from prometheus_client import Counter, Histogram

# Define metrics
config_reload_total = Counter(
    'config_reload_total',
    'Total number of configuration reloads'
)

config_reload_duration = Histogram(
    'config_reload_duration_seconds',
    'Duration of configuration reload'
)

config_reload_errors = Counter(
    'config_reload_errors_total',
    'Total number of configuration reload errors'
)

# Track reload metrics
def monitored_reload():
    with config_reload_duration.time():
        try:
            reload_config()
            config_reload_total.inc()
        except Exception as e:
            config_reload_errors.inc()
            raise
```

### Logging

```python
import structlog

logger = structlog.get_logger()

def logged_reload():
    """Reload with structured logging"""
    logger.info("config_reload_started")
    
    start_time = time.time()
    try:
        reload_config()
        duration = time.time() - start_time
        
        logger.info(
            "config_reload_completed",
            duration_seconds=duration,
            environment=config.environment,
            secrets_loaded=len(config.secrets),
        )
    except Exception as e:
        logger.error(
            "config_reload_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise
```

## Security Considerations

### Access Control

1. **Admin-Only Reload**: Only administrators should trigger reloads
2. **Audit Logging**: All reload events must be logged
3. **Rate Limiting**: Prevent reload abuse (max 1 per minute)
4. **Validation**: Always validate configuration before applying

### Secret Protection

1. **Never Log Secrets**: Automatic redaction in logs
2. **Encryption at Rest**: Secrets encrypted in GCP Secret Manager
3. **Rotation Support**: Regular key rotation capability
4. **Access Logging**: Track who accesses secrets

## Testing Hot Reload

### Unit Test

```python
import pytest
from unittest.mock import patch
from netra_backend.app.config import reload_config, get_config

def test_hot_reload():
    """Test configuration hot reload"""
    # Get initial config
    config = get_config()
    original_value = config.some_setting
    
    # Mock environment change
    with patch.dict('os.environ', {'SOME_SETTING': 'new_value'}):
        # Trigger reload
        reload_config()
        
        # Verify change applied
        config = get_config()
        assert config.some_setting == 'new_value'
    
    # After context, original value restored
    reload_config()
    config = get_config()
    assert config.some_setting == original_value
```

### Integration Test

```python
@pytest.mark.integration
async def test_hot_reload_api(client, admin_token):
    """Test hot reload via API"""
    # Make configuration change
    os.environ['TEST_SETTING'] = 'updated'
    
    # Trigger reload via API
    response = await client.post(
        "/admin/reload-config",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    
    # Verify configuration updated
    config = get_config()
    assert config.test_setting == 'updated'
```

## Troubleshooting

### Common Issues

1. **Hot Reload Not Working**
   - Check: Is CONFIG_HOT_RELOAD=true?
   - Check: Are you in the right environment?
   - Check: Do you have proper permissions?

2. **Configuration Not Updating**
   - Check: Are changes in the right priority source?
   - Check: Is validation passing?
   - Check: Are there any error logs?

3. **Reload Taking Too Long**
   - Check: GCP Secret Manager latency
   - Check: Number of secrets being loaded
   - Check: Network connectivity

### Debug Commands

```bash
# Check if hot reload is enabled
python -c "
from netra_backend.app.config import get_config
config = get_config()
print(f'Hot reload enabled: {hasattr(config, \"hot_reload_enabled\") and config.hot_reload_enabled}')
"

# Test reload functionality
python -c "
from netra_backend.app.config import reload_config
try:
    reload_config()
    print('Reload successful')
except Exception as e:
    print(f'Reload failed: {e}')
"

# Monitor configuration state
python -c "
from netra_backend.app.core.configuration.base import config_manager
import json
summary = config_manager.get_config_summary()
print(json.dumps(summary, indent=2))
"
```

## Best Practices

1. **Always Validate**: Check configuration validity before and after reload
2. **Monitor Reloads**: Track reload frequency and success rate
3. **Test Changes**: Verify services work with new configuration
4. **Document Changes**: Log why configuration was reloaded
5. **Gradual Rollout**: Test configuration changes in staging first
6. **Backup Config**: Keep backup of working configuration
7. **Alert on Failure**: Set up alerts for reload failures
8. **Rate Limit**: Prevent excessive reloads (max 1 per minute)

## References

- **Configuration System**: `/netra_backend/app/core/configuration/README.md`
- **Migration Guide**: `/docs/configuration-migration.md`
- **SPEC**: `/SPEC/unified_configuration_management.xml`
- **LLM Index**: `/LLM_MASTER_INDEX.md`