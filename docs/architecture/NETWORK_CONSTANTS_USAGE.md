# Network Constants Consolidation

## Overview

The new `app.core.network_constants` module provides a centralized configuration for all network-related constants, replacing hardcoded ports and URLs throughout the codebase.

**Business Value:** Platform/Internal - Deployment Flexibility - Centralizing network configuration enables easier deployment across different environments and reduces configuration errors.

## Key Components

### ServicePorts
Defines all default service ports and provides environment-aware port selection.

```python
from netra_backend.app.core.network_constants import ServicePorts

# Default ports
ServicePorts.POSTGRES_DEFAULT      # 5432
ServicePorts.REDIS_DEFAULT         # 6379
ServicePorts.CLICKHOUSE_HTTP       # 8123
ServicePorts.CLICKHOUSE_NATIVE     # 9000
ServicePorts.BACKEND_DEFAULT       # 8000
ServicePorts.FRONTEND_DEFAULT      # 3000
ServicePorts.AUTH_SERVICE_DEFAULT  # 8081

# Environment-aware port selection
postgres_port = ServicePorts.get_postgres_port(is_test=True)  # Returns 5433 for testing
redis_port = ServicePorts.get_redis_port(is_test=False)       # Returns 6379 for production
```

### HostConstants
Provides standardized host configurations.

```python
from netra_backend.app.core.network_constants import HostConstants

HostConstants.LOCALHOST         # "localhost"
HostConstants.LOCALHOST_IP      # "127.0.0.1"
HostConstants.ANY_HOST         # "0.0.0.0"

# Helper methods
default_host = HostConstants.get_default_host(use_localhost_ip=True)  # "127.0.0.1"
```

### DatabaseConstants
Builds database connection URLs consistently.

```python
from netra_backend.app.core.network_constants import DatabaseConstants

# PostgreSQL URL
pg_url = DatabaseConstants.build_postgres_url(
    user="test_user",
    password="test_pass",
    host="localhost",
    port=5432,
    database="test_db",
    async_driver=True
)
# Result: "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"

# Redis URL
redis_url = DatabaseConstants.build_redis_url(
    host="localhost",
    port=6379,
    database=1,
    password="optional_password"
)
# Result: "redis://:optional_password@localhost:6379/1"

# ClickHouse URL
ch_url = DatabaseConstants.build_clickhouse_url(
    host="localhost",
    port=9000,
    database="default"
)
# Result: "clickhouse://default@localhost:9000/default"
```

### URLConstants
Builds HTTP and WebSocket URLs with proper formatting.

```python
from netra_backend.app.core.network_constants import URLConstants

# HTTP URL
api_url = URLConstants.build_http_url(
    host="localhost",
    port=8000,
    path="/api/health",
    secure=False
)
# Result: "http://localhost:8000/api/health"

# WebSocket URL
ws_url = URLConstants.build_websocket_url(
    host="localhost",
    port=8000,
    path="/ws",
    secure=False
)
# Result: "ws://localhost:8000/ws"

# CORS origins by environment
dev_origins = URLConstants.get_cors_origins("development")
# Result: ["http://localhost:3000", "http://localhost:8000"]
```

### ServiceEndpoints
Provides service-specific endpoint builders and external service URLs.

```python
from netra_backend.app.core.network_constants import ServiceEndpoints

# Service URL builders
auth_url = ServiceEndpoints.build_auth_service_url()
# Result: "http://localhost:8081"

backend_url = ServiceEndpoints.build_backend_service_url()
# Result: "http://localhost:8000"

frontend_url = ServiceEndpoints.build_frontend_url()
# Result: "http://localhost:3000"

# External service endpoints
ServiceEndpoints.GOOGLE_TOKEN_URI      # Google OAuth token endpoint
ServiceEndpoints.GOOGLE_AUTH_URI       # Google OAuth authorization endpoint
ServiceEndpoints.GOOGLE_USERINFO_ENDPOINT  # Google userinfo endpoint
```

### NetworkEnvironmentHelper
Provides environment-aware configuration helpers.

```python
from netra_backend.app.core.network_constants import NetworkEnvironmentHelper

# Environment detection
env = NetworkEnvironmentHelper.get_environment()           # "development", "staging", "production"
is_test = NetworkEnvironmentHelper.is_test_environment()   # Boolean
is_cloud = NetworkEnvironmentHelper.is_cloud_environment()  # Boolean

# Environment-specific URLs
db_urls = NetworkEnvironmentHelper.get_database_urls_for_environment()
# Result: {"postgres": "postgresql+asyncpg://...", "redis": "redis://...", "clickhouse": "clickhouse://..."}

service_urls = NetworkEnvironmentHelper.get_service_urls_for_environment()
# Result: {"frontend": "http://localhost:3000", "backend": "http://localhost:8000", "auth_service": "http://localhost:8081"}
```

## Migration Strategy

### Phase 1: Core Infrastructure ✅
- [x] Created centralized network constants module
- [x] Added validation script for testing
- [x] Updated dev launcher configuration
- [x] Updated core configuration services
- [x] Updated test configuration files

### Phase 2: Application Layer (Recommended Next Steps)
- [ ] Update environment files (.env.testing, .env.example, etc.)
- [ ] Update GitHub Actions workflows to use constants
- [ ] Update deployment scripts
- [ ] Update WebSocket configuration
- [ ] Update frontend service configuration

### Phase 3: Test Infrastructure
- [ ] Update e2e test configurations
- [ ] Update Docker configuration files
- [ ] Update CI/CD pipeline configurations

## Best Practices

### 1. Import Pattern
```python
# Good - Import specific components
from netra_backend.app.core.network_constants import ServicePorts, HostConstants, DatabaseConstants

# Better - Use in functions to avoid circular imports
def get_database_config():
    from netra_backend.app.core.network_constants import DatabaseConstants, ServicePorts
    return DatabaseConstants.build_postgres_url(port=ServicePorts.POSTGRES_DEFAULT)
```

### 2. Environment-Aware Configuration
```python
# Good - Use environment helpers
from netra_backend.app.core.network_constants import NetworkEnvironmentHelper

db_urls = NetworkEnvironmentHelper.get_database_urls_for_environment()
postgres_url = db_urls["postgres"]

# Better - Use with error handling
try:
    db_urls = NetworkEnvironmentHelper.get_database_urls_for_environment()
    postgres_url = db_urls.get("postgres", "fallback_url")
except Exception as e:
    logger.warning(f"Failed to get environment URLs: {e}")
    postgres_url = "fallback_url"
```

### 3. Testing Configuration
```python
# Use test-specific ports and configurations
from netra_backend.app.core.network_constants import ServicePorts, DatabaseConstants

if os.environ.get("TESTING"):
    postgres_port = ServicePorts.get_postgres_port(is_test=True)  # 5433
    redis_port = ServicePorts.get_redis_port(is_test=True)        # 6380
else:
    postgres_port = ServicePorts.get_postgres_port(is_test=False) # 5432
    redis_port = ServicePorts.get_redis_port(is_test=False)       # 6379
```

## Validation

The network constants module can be validated using the provided script:

```bash
# Validate for development environment
python scripts/validate_network_constants.py --verbose

# Validate for production environment  
python scripts/validate_network_constants.py --environment production --verbose

# Validate for staging environment
python scripts/validate_network_constants.py --environment staging --verbose
```

## Files Updated

### Core Infrastructure
- ✅ `app/core/network_constants.py` - New centralized constants module
- ✅ `app/core/configuration/services.py` - Updated to use network constants
- ✅ `dev_launcher/config.py` - Updated port configurations
- ✅ `app/tests/conftest.py` - Updated test database URLs
- ✅ `scripts/validate_network_constants.py` - Validation script

### Configuration Files (Remaining)
- `app/configuration/schemas.py` - Configuration schema updates (planned)
- `.env.testing` - Test environment URLs (planned)
- `.env.example` - Example configuration (planned)
- GitHub Actions workflows (planned)
- Docker configurations (planned)

## Impact Analysis

### Before Consolidation
- **151 locations** with "port" string literals
- **100 locations** with "localhost" string literals  
- **94 locations** with "DATABASE_URL" string literals
- **8 hardcoded occurrences** of port 9000
- **6 hardcoded occurrences** of port 5432
- **4 hardcoded occurrences** of port 8123

### After Consolidation
- ✅ **Centralized port management** in `ServicePorts` class
- ✅ **Environment-aware configuration** via `NetworkEnvironmentHelper`
- ✅ **Consistent URL building** through builder methods
- ✅ **Type-safe constants** with Final annotations
- ✅ **Test isolation support** with test-specific ports

### Business Benefits
1. **Deployment Flexibility:** Easy configuration changes across environments
2. **Error Reduction:** Eliminates hardcoded port conflicts
3. **Maintenance Efficiency:** Single source of truth for network configuration
4. **Test Isolation:** Proper test environment configuration
5. **Development Velocity:** Faster environment setup and debugging

## Support and Troubleshooting

### Common Issues

1. **Circular Import Errors**
   - Solution: Use local imports within functions instead of module-level imports

2. **Environment Detection Issues**
   - Solution: Set `ENVIRONMENT` environment variable explicitly

3. **Port Conflicts**
   - Solution: Use `NetworkEnvironmentHelper.is_test_environment()` for proper port selection

### Getting Help

Run the validation script to check for configuration issues:
```bash
python scripts/validate_network_constants.py --verbose
```

Check the logs for network-related configuration errors:
```bash
grep -i "network\|port\|host" logs/*.log
```