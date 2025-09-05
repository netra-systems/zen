# GCP Staging Deployment Configuration Reference

## 🚨 CRITICAL: Working Configuration - DO NOT MODIFY WITHOUT TESTING

This document captures the **PROVEN WORKING** GCP staging deployment configuration from the successful deployment `netra-backend-staging-00035-fnj`.

**Last Successful Deployment**: netra-backend-staging-00035-fnj
**Environment**: staging
**Status**: ✅ FULLY OPERATIONAL

## Environment Variables Configuration

### Core Settings
```yaml
ENVIRONMENT: staging
PYTHONUNBUFFERED: "1"
```

### Service URLs (Public)
```yaml
AUTH_SERVICE_URL: https://auth.staging.netrasystems.ai
AUTH_SERVICE_ENABLED: "true"
FRONTEND_URL: https://app.staging.netrasystems.ai
FORCE_HTTPS: "true"
GCP_PROJECT_ID: netra-staging
```

### ClickHouse Configuration (Mixed)
```yaml
CLICKHOUSE_HOST: xedvrr4c3r.us-central1.gcp.clickhouse.cloud
CLICKHOUSE_PORT: "8443"
CLICKHOUSE_USER: default
CLICKHOUSE_DB: default
CLICKHOUSE_SECURE: "true"
CLICKHOUSE_PASSWORD: Secret: clickhouse-password-staging:latest
```

### WebSocket Configuration
```yaml
WEBSOCKET_CONNECTION_TIMEOUT: "900"
WEBSOCKET_HEARTBEAT_INTERVAL: "25"
WEBSOCKET_HEARTBEAT_TIMEOUT: "75"
WEBSOCKET_CLEANUP_INTERVAL: "180"
WEBSOCKET_STALE_TIMEOUT: "900"
```

## Secret Manager References

### Database Secrets
```yaml
POSTGRES_HOST: Secret: postgres-host-staging:latest
POSTGRES_PORT: Secret: postgres-port-staging:latest
POSTGRES_DB: Secret: postgres-db-staging:latest
POSTGRES_USER: Secret: postgres-user-staging:latest
POSTGRES_PASSWORD: Secret: postgres-password-staging:latest
```

### Redis Secrets
```yaml
REDIS_HOST: Secret: redis-host-staging:latest
REDIS_PORT: Secret: redis-port-staging:latest
REDIS_URL: Secret: redis-url-staging:latest
REDIS_PASSWORD: Secret: redis-password-staging:latest
```

### Security Secrets
```yaml
JWT_SECRET_STAGING: Secret: jwt-secret-staging:latest
JWT_SECRET_KEY: Secret: jwt-secret-key-staging:latest
SECRET_KEY: Secret: secret-key-staging:latest
SERVICE_SECRET: Secret: service-secret-staging:latest
SERVICE_ID: Secret: service-id-staging:latest
FERNET_KEY: Secret: fernet-key-staging:latest
```

### API Keys
```yaml
OPENAI_API_KEY: Secret: openai-api-key-staging:latest
ANTHROPIC_API_KEY: Secret: anthropic-api-key-staging:latest
GEMINI_API_KEY: Secret: gemini-api-key-staging:latest
```

## Critical Configuration Rules

### 1. Secret Management Pattern
- **ALWAYS** use GCP Secret Manager for sensitive values
- **NEVER** hardcode secrets in deployment files
- **USE** the format `Secret: <secret-name>:latest` for secret references
- **MAINTAIN** separate secrets per environment (e.g., `jwt-secret-staging` vs `jwt-secret-production`)

### 2. Environment Isolation
- **STAGING** must use `*-staging` secrets exclusively
- **PRODUCTION** must use `*-production` secrets exclusively
- **NEVER** mix environment secrets

### 3. Required Secrets List
The following secrets MUST exist in GCP Secret Manager for staging:
- `postgres-host-staging`
- `postgres-port-staging`
- `postgres-db-staging`
- `postgres-user-staging`
- `postgres-password-staging`
- `redis-host-staging`
- `redis-port-staging`
- `redis-url-staging`
- `redis-password-staging`
- `jwt-secret-staging`
- `jwt-secret-key-staging`
- `secret-key-staging`
- `service-secret-staging`
- `service-id-staging`
- `fernet-key-staging`
- `openai-api-key-staging`
- `anthropic-api-key-staging`
- `gemini-api-key-staging`
- `clickhouse-password-staging`

### 4. Deployment Command Reference

#### Default Deployment (with automatic validation) ✅
```bash
# RECOMMENDED - Validates configuration automatically before deployment
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# The deployment script now automatically:
# 1. Validates configuration against proven working setup (netra-backend-staging-00035-fnj)
# 2. Checks all required environment variables match
# 3. Verifies all secret mappings are correct
# 4. Only proceeds if validation passes
```

#### Manual Validation Check
```bash
# To validate configuration without deploying:
python scripts/validate_deployment_config.py --environment staging

# To also check if secrets exist in GCP:
python scripts/validate_deployment_config.py --environment staging --check-secrets
```

#### Emergency Deployment (skip validation) ⚠️
```bash
# NOT RECOMMENDED - Use only in emergencies when you need to bypass validation
python scripts/deploy_to_gcp.py --project netra-staging --build-local --skip-validation
```

### 5. Health Check URLs
- Backend: https://api.staging.netrasystems.ai/health
- Auth: https://auth.staging.netrasystems.ai/health
- Frontend: https://app.staging.netrasystems.ai

## Validation Checklist

Before any deployment:
- [ ] Verify all secrets exist in GCP Secret Manager
- [ ] Confirm environment variable names match exactly (case-sensitive)
- [ ] Check that secret references use `:latest` suffix
- [ ] Validate that URLs use proper HTTPS scheme
- [ ] Ensure WebSocket timeouts are configured
- [ ] Verify ClickHouse configuration is complete

## Common Issues to Avoid

1. **Missing Secrets**: Deployment will fail if any referenced secret doesn't exist
2. **Wrong Environment**: Using production secrets in staging or vice versa
3. **Hardcoded Values**: Never hardcode passwords or API keys
4. **Missing Ports**: Always specify ports as strings in environment variables
5. **URL Schemes**: Always use HTTPS for staging/production URLs

## Rollback Procedure

If a deployment fails:
1. Check Cloud Run revision history
2. Rollback to the last known working revision (e.g., `netra-backend-staging-00035-fnj`)
3. Review logs for secret access errors
4. Verify secret manager permissions

## Related Documentation
- [Configuration Architecture](./configuration_architecture.md)
- [OAuth Regression Analysis](../OAUTH_REGRESSION_ANALYSIS_20250905.md)
- [Config Regression Prevention Plan](../CONFIG_REGRESSION_PREVENTION_PLAN.md)