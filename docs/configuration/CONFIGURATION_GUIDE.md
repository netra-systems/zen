# Netra Apex - Configuration Management Guide

## Overview

This comprehensive guide covers all environment configuration for Netra Apex, from local development to production deployment. It consolidates all environment variables, configuration files, and secrets management procedures.

## Table of Contents

- [Configuration Architecture](#configuration-architecture)
- [Environment Variables Reference](#environment-variables-reference)
- [Environment-Specific Configurations](#environment-specific-configurations)
- [Secrets Management](#secrets-management)
- [Database Configuration](#database-configuration)
- [Service Configuration](#service-configuration)
- [Security Configuration](#security-configuration)
- [Configuration Validation](#configuration-validation)

## Configuration Architecture

### Configuration Hierarchy

```
Environment Configuration Priority (highest to lowest):
1. Environment Variables (runtime)
2. .env.local (environment-specific, not tracked)
3. .env.{environment} (staging, production, etc.)
4. .env (default environment file)
5. config/defaults.py (hardcoded defaults)
```

### Configuration Files Structure

```
netra-core-generation-1/
├── .env                           # Primary environment file
├── .env.example                   # Template for new environments
├── .env.development               # Development overrides
├── .env.development.local         # Local development (Terraform-generated)
├── .env.staging                   # Staging environment
├── .env.staging.local             # Staging local overrides
├── .env.production               # Production environment
├── .env.testing                  # Testing environment
├── config/
│   └── .env.example              # Legacy example file
└── app/configuration/
    ├── schemas.py                # Configuration validation schemas
    ├── services.py               # Configuration loading logic
    └── validator.py              # Configuration validation
```

### Configuration Loading Process

```python
# Configuration loading priority
class ConfigurationLoader:
    """Load configuration from multiple sources with proper precedence."""
    
    def load_configuration(self, environment: str = "development") -> dict:
        """
        Load configuration with proper precedence:
        1. Environment variables (highest priority)
        2. .env.local files
        3. Environment-specific .env files
        4. Base .env file
        5. Default values (lowest priority)
        """
        config = self._load_defaults()
        
        # Load base .env file
        config.update(self._load_env_file('.env'))
        
        # Load environment-specific file
        config.update(self._load_env_file(f'.env.{environment}'))
        
        # Load local overrides
        config.update(self._load_env_file(f'.env.{environment}.local'))
        
        # Environment variables override everything
        config.update(self._load_environment_variables())
        
        return self._validate_configuration(config)
```

## Environment Variables Reference

### Core Application Settings

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| **`ENVIRONMENT`** | Deployment environment | `development` | ✅ | `production`, `staging`, `development` |
| **`DEBUG`** | Enable debug mode | `false` | ❌ | `true`, `false` |
| **`LOG_LEVEL`** | Logging level | `INFO` | ❌ | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| **`HOST`** | Application host | `0.0.0.0` | ❌ | `0.0.0.0`, `localhost` |
| **`PORT`** | Application port | `8000` | ❌ | `8000`, `8080` |

### Database Configuration

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| **`DATABASE_URL`** | PostgreSQL connection URL | SQLite fallback | ✅ | `postgresql+asyncpg://user:pass@host:5432/db` |
| **`DATABASE_POOL_SIZE`** | Connection pool size | `5` | ❌ | `10`, `20` |
| **`DATABASE_MAX_OVERFLOW`** | Max pool overflow | `10` | ❌ | `20`, `40` |
| **`DATABASE_POOL_TIMEOUT`** | Pool checkout timeout (seconds) | `30` | ❌ | `60` |
| **`DATABASE_POOL_RECYCLE`** | Connection recycle time (seconds) | `3600` | ❌ | `7200` |

### ClickHouse Configuration

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| **`CLICKHOUSE_URL`** | ClickHouse connection URL | None | ❌ | `clickhouse://user:pass@host:9000/db` |
| **`CLICKHOUSE_HOST`** | ClickHouse host | `localhost` | ❌ | `clickhouse.company.com` |
| **`CLICKHOUSE_PORT`** | ClickHouse port | `9440` (native), `8443` (HTTPS) | ❌ | `9000`, `8123` |
| **`CLICKHOUSE_USER`** | ClickHouse username | `default` | ❌ | `netra_user` |
| **`CLICKHOUSE_PASSWORD`** | ClickHouse password | None | ❌ | `secure_password` |
| **`CLICKHOUSE_DB`** | ClickHouse database | `default` | ❌ | `netra_analytics` |

### Redis Configuration

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| **`REDIS_URL`** | Redis connection URL | None | ❌ | `redis://user:pass@host:6379/0` |
| **`REDIS_HOST`** | Redis host | `localhost` | ❌ | `redis.company.com` |
| **`REDIS_PORT`** | Redis port | `6379` | ❌ | `6379`, `6380` |
| **`REDIS_PASSWORD`** | Redis password | None | ❌ | `secure_password` |
| **`REDIS_DB`** | Redis database number | `0` | ❌ | `0`, `1`, `2` |
| **`REDIS_MAX_CONNECTIONS`** | Max connection pool | `20` | ❌ | `50`, `100` |

### Authentication & Security

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| **`JWT_SECRET_KEY`** | JWT signing secret | None | ✅ | Generate with `secrets.token_urlsafe(32)` |
| **`FERNET_KEY`** | Encryption key for sensitive data | None | ✅ | Generate with `Fernet.generate_key()` |
| **`SECRET_KEY`** | General application secret | None | ✅ | Generate with `secrets.token_urlsafe(64)` |
| **`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`** | JWT token expiry (minutes) | `30` | ❌ | `60`, `120` |
| **`JWT_REFRESH_TOKEN_EXPIRE_DAYS`** | Refresh token expiry (days) | `7` | ❌ | `14`, `30` |

### OAuth Configuration

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| **`GOOGLE_CLIENT_ID`** | Google OAuth client ID | None | ✅ | `123456-abcdef.apps.googleusercontent.com` |
| **`GOOGLE_CLIENT_SECRET`** | Google OAuth client secret | None | ✅ | `GOCSPX-abc123def456...` |
| **`OAUTH_REDIRECT_URI`** | OAuth callback URL | Auto-generated | ❌ | `https://api.yourdomain.com/api/auth/callback` |

### LLM Provider Configuration

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| **`GEMINI_API_KEY`** | Google Gemini API key (primary) | None | ✅ | `AIzaSyC...` |
| **`OPENAI_API_KEY`** | OpenAI API key (optional) | None | ❌ | `sk-proj-...` |
| **`ANTHROPIC_API_KEY`** | Anthropic API key (optional) | None | ❌ | `sk-ant-...` |
| **`LLM_DEFAULT_PROVIDER`** | Default LLM provider | `gemini` | ❌ | `gemini`, `openai`, `anthropic` |
| **`LLM_FALLBACK_ENABLED`** | Enable provider fallback | `true` | ❌ | `true`, `false` |

### Frontend & CORS Configuration

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| **`FRONTEND_URL`** | Frontend application URL | `http://localhost:3000` | ✅ | `https://app.yourdomain.com` |
| **`API_URL`** | Backend API URL | `http://localhost:8000` | ✅ | `https://api.yourdomain.com` |
| **`ALLOWED_ORIGINS`** | CORS allowed origins | Frontend URL | ❌ | `https://app.yourdomain.com,https://admin.yourdomain.com` |

### Development Mode Switches

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| **`DEV_MODE_DISABLE_LLM`** | Disable LLM providers in dev | `false` | ❌ | `true` |
| **`DEV_MODE_DISABLE_REDIS`** | Disable Redis in dev | `false` | ❌ | `true` |
| **`DEV_MODE_DISABLE_CLICKHOUSE`** | Disable ClickHouse in dev | `false` | ❌ | `true` |
| **`LLM_MOCK_MODE`** | Mock LLM responses | `false` | ❌ | `true` |

### Monitoring & Observability

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| **`SENTRY_DSN`** | Sentry error tracking DSN | None | ❌ | `https://...@sentry.io/...` |
| **`PROMETHEUS_METRICS_ENABLED`** | Enable Prometheus metrics | `true` | ❌ | `true`, `false` |
| **`GRAFANA_API_KEY`** | Grafana API key | None | ❌ | `eyJrIjoi...` |
| **`LANGFUSE_PUBLIC_KEY`** | LangFuse public key | None | ❌ | `pk-lf-...` |
| **`LANGFUSE_SECRET_KEY`** | LangFuse secret key | None | ❌ | `sk-lf-...` |

### Google Cloud Configuration

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| **`GCP_PROJECT_ID`** | Google Cloud Project ID | None | ❌ | `netra-production-123456` |
| **`GCP_PROJECT_ID_NUMERICAL_STAGING`** | Numerical project ID for staging | `701982941522` | ❌ | `701982941522` |
| **`SECRET_MANAGER_PROJECT_ID`** | Secret Manager project ID | Auto-detected | ❌ | `304612253870` |
| **`GOOGLE_CLOUD_PROJECT`** | GCP project (alternative) | None | ❌ | `netra-production-123456` |

## Environment-Specific Configurations

### Development Environment

**File: `.env.development`**
```env
# Development Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Local services (use Terraform-managed or local)
DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/netra_dev
REDIS_URL=redis://localhost:6379/0
CLICKHOUSE_URL=clickhouse://localhost:9000/netra_analytics

# Development-specific settings
DEV_MODE_DISABLE_LLM=false
LLM_MOCK_MODE=false

# Frontend URLs for development
FRONTEND_URL=http://localhost:3000
API_URL=http://localhost:8000
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000

# OAuth for development (use test credentials)
GOOGLE_CLIENT_ID=your-dev-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-dev-client-secret

# Required secrets (use development values)
JWT_SECRET_KEY=dev-jwt-secret-change-in-production
FERNET_KEY=your-dev-fernet-key-base64-encoded=
SECRET_KEY=dev-secret-key-change-in-production

# LLM providers (use development keys with rate limits)
GEMINI_API_KEY=your-dev-gemini-key
```

**Auto-Generated Local Override: `.env.development.local`** (Created by Terraform)
```env
# Auto-generated by Terraform dev environment
# DO NOT EDIT MANUALLY

DATABASE_URL=postgresql+asyncpg://postgres:secure_random_password@localhost:5432/netra_dev
REDIS_URL=redis://:secure_random_password@localhost:6379/0
CLICKHOUSE_URL=clickhouse://default:secure_random_password@localhost:9000/netra_analytics

# Secure generated keys
JWT_SECRET_KEY=auto-generated-secure-jwt-key
FERNET_KEY=auto-generated-secure-fernet-key=
SECRET_KEY=auto-generated-secure-secret-key
```

### Staging Environment

**File: `.env.staging`**
```env
# Staging Configuration
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# Google Cloud staging resources
DATABASE_URL=postgresql+asyncpg://netra_staging@staging-postgres:5432/netra_staging
REDIS_URL=redis://:staging-password@staging-redis:6379/0
CLICKHOUSE_URL=clickhouse://default:staging-password@staging-clickhouse:9000/netra_analytics

# Staging URLs
FRONTEND_URL=https://staging-app.netrasystems.ai
API_URL=https://staging-api.netrasystems.ai
ALLOWED_ORIGINS=https://staging-app.netrasystems.ai

# Google Cloud configuration
GCP_PROJECT_ID_NUMERICAL_STAGING=701982941522
SECRET_MANAGER_PROJECT_ID=701982941522

# Secrets loaded from Google Secret Manager (with -staging suffix)
# These are automatically loaded by the configuration system
```

### Production Environment

**File: `.env.production`**
```env
# Production Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Production URLs (these must match your domain)
FRONTEND_URL=https://app.yourdomain.com
API_URL=https://api.yourdomain.com
ALLOWED_ORIGINS=https://app.yourdomain.com

# Google Cloud production configuration
GCP_PROJECT_ID_NUMERICAL_STAGING=304612253870
SECRET_MANAGER_PROJECT_ID=304612253870

# High-performance production settings
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

REDIS_MAX_CONNECTIONS=50

# Enhanced security settings
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Monitoring enabled
PROMETHEUS_METRICS_ENABLED=true
SENTRY_DSN=your-production-sentry-dsn

# All secrets loaded from Google Secret Manager
# Never put production secrets in .env files!
```

### Testing Environment

**File: `.env.testing`**
```env
# Testing Configuration
ENVIRONMENT=testing
DEBUG=true
LOG_LEVEL=DEBUG

# Use in-memory/temporary databases for testing
DATABASE_URL=sqlite+aiosqlite:///:memory:
REDIS_URL=fakeredis://localhost

# Disable external services during testing
DEV_MODE_DISABLE_LLM=true
DEV_MODE_DISABLE_CLICKHOUSE=true
LLM_MOCK_MODE=true

# Testing-specific settings
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=5  # Short expiry for tests
FRONTEND_URL=http://localhost:3001
API_URL=http://localhost:8001

# Test secrets (not real)
JWT_SECRET_KEY=test-jwt-secret
FERNET_KEY=test-fernet-key-base64-encoded=
SECRET_KEY=test-secret-key
```

## Secrets Management

### Google Secret Manager Integration

Netra automatically loads secrets from Google Secret Manager based on environment:

**Secret Naming Convention:**
- **Development**: Use plain secret names
- **Staging**: Automatically append `-staging` suffix
- **Production**: Use plain secret names (separate project)

**Configured Secrets:**
```python
SECRET_CONFIG = [
    # LLM providers
    SecretReference(name="gemini-api-key", target_field="GEMINI_API_KEY"),
    SecretReference(name="openai-api-key", target_field="OPENAI_API_KEY"),
    SecretReference(name="anthropic-api-key", target_field="ANTHROPIC_API_KEY"),
    
    # Authentication
    SecretReference(name="google-client-id", target_field="GOOGLE_CLIENT_ID"),
    SecretReference(name="google-client-secret", target_field="GOOGLE_CLIENT_SECRET"),
    
    # Security keys
    SecretReference(name="jwt-secret-key", target_field="JWT_SECRET_KEY"),
    SecretReference(name="fernet-key", target_field="FERNET_KEY"),
    SecretReference(name="secret-key", target_field="SECRET_KEY"),
    
    # Database passwords
    SecretReference(name="clickhouse-default-password", target_field="CLICKHOUSE_PASSWORD"),
    SecretReference(name="redis-default", target_field="REDIS_PASSWORD"),
    
    # Monitoring
    SecretReference(name="langfuse-secret-key", target_field="LANGFUSE_SECRET_KEY"),
    SecretReference(name="langfuse-public-key", target_field="LANGFUSE_PUBLIC_KEY"),
    
    # Development tools
    SecretReference(name="github-token", target_field="GITHUB_TOKEN"),
]
```

### Secret Management Commands

```bash
# Fetch all secrets to .env file
python scripts/fetch_secrets_to_env.py

# Fetch secrets for specific environment
python scripts/fetch_secrets_to_env.py --environment staging

# Create new secret in Google Secret Manager
gcloud secrets create secret-name --data-file=secret-value.txt

# Update existing secret
echo "new-secret-value" | gcloud secrets versions add secret-name --data-file=-

# List all secrets
gcloud secrets list --filter="name:netra OR name:gemini OR name:jwt"

# Create staging-specific secret
gcloud secrets create secret-name-staging --data-file=staging-value.txt
```

### Local Secret Generation

For development environments, generate secure secrets locally:

```bash
# Generate JWT secret
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate Fernet key
python -c "from cryptography.fernet import Fernet; print('FERNET_KEY=' + Fernet.generate_key().decode())"

# Generate general secret
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(64))"
```

## Database Configuration

### PostgreSQL Configuration

**Connection URL Format:**
```
postgresql+asyncpg://user:password@host:port/database
```

**Performance Settings:**
```env
# Connection pool settings
DATABASE_POOL_SIZE=5          # Base connection pool size
DATABASE_MAX_OVERFLOW=10      # Additional connections when pool exhausted
DATABASE_POOL_TIMEOUT=30      # Seconds to wait for connection
DATABASE_POOL_RECYCLE=3600    # Seconds before connection refresh

# Query settings
DATABASE_ECHO=false           # Log all SQL queries (development only)
DATABASE_ECHO_POOL=false      # Log connection pool events
```

**Production PostgreSQL Optimization:**
```sql
-- Recommended PostgreSQL settings for production
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.7;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
SELECT pg_reload_conf();
```

### ClickHouse Configuration

**Connection Options:**
```env
# Native protocol (faster, binary)
CLICKHOUSE_URL=clickhouse://user:password@host:9000/database

# HTTPS protocol (for cloud/managed instances)
CLICKHOUSE_URL=clickhousehttps://user:password@host:8443/database
```

**Production ClickHouse Settings:**
```xml
<!-- config/clickhouse-config.xml -->
<yandex>
    <max_connections>100</max_connections>
    <max_concurrent_queries>50</max_concurrent_queries>
    <max_memory_usage>10000000000</max_memory_usage>
    <max_bytes_before_external_group_by>20000000000</max_bytes_before_external_group_by>
</yandex>
```

### Redis Configuration

**Connection Options:**
```env
# Basic Redis connection
REDIS_URL=redis://host:6379/0

# Redis with authentication
REDIS_URL=redis://:password@host:6379/0

# Redis with username and password
REDIS_URL=redis://username:password@host:6379/0
```

**Redis Performance Settings:**
```env
REDIS_MAX_CONNECTIONS=20      # Connection pool size
REDIS_SOCKET_TIMEOUT=5        # Socket timeout in seconds
REDIS_SOCKET_CONNECT_TIMEOUT=5 # Connection timeout in seconds
REDIS_RETRY_ON_TIMEOUT=true   # Retry on timeout
REDIS_HEALTH_CHECK_INTERVAL=30 # Health check interval in seconds
```

## Service Configuration

### LLM Provider Configuration

```env
# Primary provider (required)
GEMINI_API_KEY=your-gemini-api-key
LLM_DEFAULT_PROVIDER=gemini

# Optional providers (for fallback and comparison)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
COHERE_API_KEY=your-cohere-api-key

# Provider behavior
LLM_FALLBACK_ENABLED=true     # Enable fallback to secondary providers
LLM_TIMEOUT_SECONDS=30        # Request timeout
LLM_MAX_RETRIES=3             # Maximum retry attempts
LLM_RETRY_DELAY_SECONDS=2     # Delay between retries

# Rate limiting
LLM_RATE_LIMIT_PER_MINUTE=60  # Requests per minute per provider
LLM_CONCURRENT_REQUESTS=10    # Maximum concurrent requests
```

### Agent Configuration

```env
# Agent execution settings
AGENT_TIMEOUT_SECONDS=300     # Maximum agent execution time
AGENT_MAX_CONCURRENT=5        # Maximum concurrent agent executions
AGENT_RETRY_ATTEMPTS=2        # Retry attempts for failed agents

# Agent-specific LLM configuration
AGENT_TRIAGE_MODEL=gemini-1.5-pro
AGENT_DATA_MODEL=gemini-1.5-flash
AGENT_OPTIMIZATION_MODEL=gemini-1.5-pro
AGENT_ACTIONS_MODEL=gemini-1.5-flash
AGENT_REPORTING_MODEL=gemini-1.5-pro
```

### WebSocket Configuration

```env
# WebSocket settings
WEBSOCKET_HEARTBEAT_INTERVAL=30  # Heartbeat interval in seconds
WEBSOCKET_TIMEOUT=60            # Connection timeout
WEBSOCKET_MAX_CONNECTIONS=1000   # Maximum concurrent connections
WEBSOCKET_MESSAGE_MAX_SIZE=1048576 # Maximum message size (1MB)
```

## Security Configuration

### Encryption & Hashing

```env
# Encryption settings
FERNET_KEY=your-base64-encoded-fernet-key    # For symmetric encryption
ENCRYPTION_ALGORITHM=HS256                    # JWT signing algorithm

# Password hashing
PASSWORD_HASH_ALGORITHM=bcrypt               # Password hashing algorithm
PASSWORD_HASH_ROUNDS=12                      # Bcrypt rounds (higher = more secure)

# Session security
SESSION_COOKIE_SECURE=true                   # Require HTTPS for cookies
SESSION_COOKIE_HTTPONLY=true                 # Prevent XSS access to cookies
SESSION_COOKIE_SAMESITE=strict              # CSRF protection
```

### CORS Configuration

```env
# CORS settings
ALLOWED_ORIGINS=https://app.yourdomain.com,https://admin.yourdomain.com
ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS
ALLOWED_HEADERS=Content-Type,Authorization,X-Requested-With
ALLOW_CREDENTIALS=true                       # Allow credentials in CORS requests
MAX_AGE=86400                               # Preflight cache time (seconds)
```

### Rate Limiting

```env
# Rate limiting settings
RATE_LIMIT_ENABLED=true                     # Enable rate limiting
RATE_LIMIT_PER_MINUTE=60                   # Requests per minute per IP
RATE_LIMIT_BURST=10                        # Burst requests allowed
RATE_LIMIT_REDIS_KEY_PREFIX=rate_limit:    # Redis key prefix
```

## Configuration Validation

### Validation Schema

The application validates all configuration at startup:

```python
class ConfigurationValidator:
    """Validate configuration completeness and correctness."""
    
    def validate_configuration(self, config: dict) -> ValidationResult:
        """Comprehensive configuration validation."""
        
        errors = []
        warnings = []
        
        # Required settings validation
        required_settings = [
            'JWT_SECRET_KEY', 'FERNET_KEY', 'SECRET_KEY',
            'GEMINI_API_KEY', 'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET'
        ]
        
        for setting in required_settings:
            if not config.get(setting):
                errors.append(f"Missing required setting: {setting}")
        
        # Database URL validation
        if not self._validate_database_url(config.get('DATABASE_URL')):
            errors.append("Invalid DATABASE_URL format")
        
        # Security validation
        if config.get('ENVIRONMENT') == 'production':
            if config.get('DEBUG', '').lower() == 'true':
                errors.append("DEBUG must be false in production")
            
            if 'localhost' in config.get('ALLOWED_ORIGINS', ''):
                warnings.append("localhost in ALLOWED_ORIGINS for production")
        
        # LLM provider validation
        if not any(config.get(key) for key in ['GEMINI_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY']):
            errors.append("At least one LLM provider API key is required")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

### Configuration Validation Commands

```bash
# Validate current configuration
python scripts/validate_configuration.py

# Validate specific environment
python scripts/validate_configuration.py --environment production

# Check configuration completeness
python scripts/configuration_health_check.py

# Test database connections
python scripts/test_database_connections.py

# Validate secrets access
python scripts/test_secrets_access.py --environment staging
```

### Common Configuration Issues & Solutions

**Issue: Database Connection Fails**
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection manually
psql "postgresql+asyncpg://user:pass@host:5432/db"

# Check connection string format
python -c "from sqlalchemy import create_engine; engine = create_engine('your-database-url'); print('Valid URL')"
```

**Issue: Secret Manager Access Denied**
```bash
# Check authentication
gcloud auth application-default print-access-token

# Check project permissions
gcloud projects get-iam-policy PROJECT_ID

# Test secret access
gcloud secrets access latest --secret="jwt-secret-key"
```

**Issue: LLM API Authentication Fails**
```bash
# Test Gemini API key
curl -H "x-goog-api-key: YOUR_API_KEY" \
  "https://generativelanguage.googleapis.com/v1/models"

# Test OpenAI API key
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.openai.com/v1/models"
```

**Issue: CORS Errors in Browser**
```env
# Ensure frontend URL is in allowed origins
ALLOWED_ORIGINS=https://app.yourdomain.com,http://localhost:3000

# Check protocol consistency (http/https)
FRONTEND_URL=https://app.yourdomain.com
API_URL=https://api.yourdomain.com
```

## Configuration Best Practices

### Development Best Practices

1. **Use `.env.development.local`** for local overrides (not tracked in git)
2. **Never commit real secrets** to version control
3. **Use the Terraform dev environment** for consistent local setup
4. **Validate configuration** before starting development
5. **Document environment-specific requirements** in team documentation

### Production Best Practices

1. **Use Google Secret Manager** for all production secrets
2. **Rotate secrets regularly** (quarterly recommended)
3. **Monitor configuration drift** with validation scripts
4. **Use environment-specific configurations** consistently
5. **Implement configuration backup procedures**
6. **Test configuration changes** in staging first
7. **Use infrastructure as code** for consistency

### Security Best Practices

1. **Generate strong secrets** using cryptographic libraries
2. **Use different secrets** for each environment
3. **Implement proper access controls** on secret management
4. **Audit secret access** regularly
5. **Use HTTPS everywhere** in production
6. **Enable security headers** and CORS properly
7. **Monitor for security configuration issues**

---

**Configuration Philosophy**: "Configuration should be environment-aware, secure by default, and validatable. Every configuration option should have a clear purpose and proper validation to prevent runtime errors."

**Related Documentation:**
- [Getting Started Guide](../development/CUSTOMER_GETTING_STARTED.md) - Development setup
- [Production Deployment](../deployment/PRODUCTION_DEPLOYMENT.md) - Production configuration
- [Secrets Management Guide](../deployment/STAGING_SECRETS_GUIDE.md) - Google Secret Manager setup
- [Monitoring Guide](../operations/MONITORING_GUIDE.md) - Monitoring configuration