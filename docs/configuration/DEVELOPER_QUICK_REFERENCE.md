# Configuration Quick Reference for Developers

## 🚨 CRITICAL RULE

**NEVER use `os.environ.get()`, `os.environ[]`, or `os.getenv()` directly.**

This causes $12K MRR loss from configuration inconsistencies.

## ✅ The ONLY Way to Access Configuration

```python
from netra_backend.app.core.configuration.base import get_unified_config

config = get_unified_config()
# Now access any configuration value through config
```

## 🔥 Common Configuration Patterns

### Database Configuration
```python
config = get_unified_config()

# PostgreSQL
database_url = config.database.url
pool_size = config.database.pool_size
max_overflow = config.database.max_overflow

# ClickHouse
clickhouse_host = config.clickhouse_native.host
clickhouse_port = config.clickhouse_native.port

# Redis
redis_url = config.redis.url
redis_host = config.redis.host
```

### LLM Provider Configuration
```python
config = get_unified_config()

# Gemini (Primary)
gemini_key = config.llm_configs.gemini.api_key
gemini_model = config.llm_configs.gemini.model

# OpenAI (Optional)
openai_key = config.llm_configs.openai.api_key

# Provider defaults
default_provider = config.llm_configs.default.provider
```

### Server & CORS Configuration
```python
config = get_unified_config()

# Server settings
host = config.server.host
port = config.server.port
debug = config.server.debug

# CORS settings
allowed_origins = config.server.allowed_origins
cors_methods = config.server.cors_methods
```

### Environment Detection
```python
config = get_unified_config()

environment = config.environment  # "development", "staging", "production", "testing"

# Environment checks
if config.environment == "production":
    use_production_service()
elif config.environment == "development":
    use_development_service()

is_production = config.environment == "production"
is_staging = config.environment == "staging"
```

### Service Feature Flags
```python
config = get_unified_config()

# Service availability
use_real_llm = config.services.use_real_llm
use_real_database = config.services.use_real_database
use_real_redis = config.services.use_real_redis

# LLM specific
llm_enabled = config.services.llm_enabled
mock_llm = config.services.mock_llm
```

### OAuth & Google Cloud
```python
config = get_unified_config()

# OAuth configuration
client_id = config.oauth_config.client_id
client_secret = config.oauth_config.client_secret
redirect_uri = config.oauth_config.redirect_uri

# Google Cloud
project_id = config.google_cloud.project_id
```

## 📋 Quick Migration Checklist

When you see legacy configuration code:

1. ❌ Remove `import os` (if only used for environment access)
2. ✅ Add `from netra_backend.app.core.configuration.base import get_unified_config`
3. ❌ Replace `os.environ.get("KEY")` with `config.field_name`
4. ✅ Get config object: `config = get_unified_config()`
5. ✅ Test that the field exists in AppConfig schema
6. ✅ Remove hardcoded fallback values

## 🔍 Debugging Configuration

### Check if Configuration Loads
```python
try:
    from netra_backend.app.core.configuration.base import get_unified_config
    config = get_unified_config()
    print("✅ Configuration loaded successfully")
    print(f"Environment: {config.environment}")
except Exception as e:
    print(f"❌ Configuration error: {e}")
```

### Validate Specific Fields
```python
config = get_unified_config()

print(f"Database URL configured: {bool(config.database.url)}")
print(f"Gemini API key configured: {bool(config.llm_configs.gemini.api_key)}")
print(f"Environment: {config.environment}")
print(f"Debug mode: {config.server.debug}")
```

### Enable Debug Logging
```python
import logging
logging.getLogger('netra_backend.app.core.configuration').setLevel(logging.DEBUG)

from netra_backend.app.core.configuration.base import get_unified_config
config = get_unified_config()
```

## 🛠️ Validation Commands

### Check for Violations (Should Return Nothing)
```bash
grep -r "os\.environ\|os\.getenv" netra_backend/app/ --include="*.py" | grep -v "base.py"
```

### Run Configuration Tests
```bash
# All configuration tests
python -m pytest -k "config" --no-cov -v

# Configuration migration validation
python -m pytest tests/validation/test_config_migration_validation.py -v

# Configuration integrity
python scripts/validate_configuration.py
```

### Pre-commit Validation
```bash
# Run before committing any code
python -m pytest -k "config" --no-cov -v
python scripts/check_architecture_compliance.py
```

## ❌ Common Mistakes to Avoid

### DON'T: Direct Environment Access
```python
# ❌ WRONG - Causes $12K MRR loss
import os
port = os.environ.get("PORT", 8080)
api_key = os.getenv("API_KEY")
if os.environ["TESTING"]:
    pass
```

### DON'T: Module-Level Configuration
```python
# ❌ WRONG - Timing issues
# At module level:
config = get_unified_config()  # DON'T DO THIS
#removed-legacy= config.database.url  # DON'T DO THIS
```

### DON'T: Configuration Mutation
```python
# ❌ WRONG - Breaks consistency
config = get_unified_config()
config.database.url = "modified://url"  # DON'T DO THIS
```

### DON'T: Hardcoded Fallbacks
```python
# ❌ WRONG - Inconsistent defaults
config = get_unified_config()
timeout = config.timeout or 30  # DON'T DO THIS
```

## ✅ Correct Patterns

### DO: Function-Level Access
```python
# ✅ CORRECT
def create_database_connection():
    config = get_unified_config()
    return connect(config.database.url)

def get_llm_client():
    config = get_unified_config()
    return LLMClient(api_key=config.llm_configs.gemini.api_key)
```

### DO: Environment-Aware Logic
```python
# ✅ CORRECT
def get_service_client():
    config = get_unified_config()
    if config.services.use_real_llm:
        return RealLLMClient(config.llm_configs.gemini.api_key)
    else:
        return MockLLMClient()
```

### DO: Type-Safe Access
```python
# ✅ CORRECT - Let Pydantic handle validation
config = get_unified_config()
port: int = config.server.port  # Type-safe
debug: bool = config.server.debug  # Type-safe
origins: List[str] = config.server.allowed_origins  # Type-safe
```

## 📖 Schema Reference

All configuration fields are defined in:
- **Primary Schema**: `netra_backend/app/schemas/Config.py`
- **Configuration Managers**: `netra_backend/app/core/configuration/`

### Adding New Configuration Fields

1. Add field to `AppConfig` in `app/schemas/Config.py`:
```python
class AppConfig(BaseModel):
    new_field: str = Field(default="default_value", description="Field description")
```

2. Use the field in your code:
```python
config = get_unified_config()
value = config.new_field
```

3. Add validation if needed (in appropriate validator)
4. Test in all environments

## 🆘 Emergency Recovery

If configuration system fails:

1. **Check environment variables**:
```bash
echo $ENVIRONMENT
echo $TESTING
echo $K_SERVICE
```

2. **Test basic loading**:
```python
from netra_backend.app.core.configuration.base import get_unified_config
config = get_unified_config()
```

3. **Check Secret Manager access**:
```bash
gcloud auth application-default login
gcloud secrets list --filter="name:netra OR name:gemini"
```

## 📞 Support

If you encounter configuration issues:

1. Run validation commands above
2. Check the [Configuration Guide](./CONFIGURATION_GUIDE.md)
3. Review the [Migration Guide](./CONFIGURATION_MIGRATION_GUIDE.md)
4. Contact the development team with:
   - Environment details
   - Error logs
   - Configuration validation results

---

**Remember**: Every `os.environ` call is a potential $12K MRR loss. Use the unified configuration system.

**The rule is simple**: `get_unified_config()` for everything. No exceptions.