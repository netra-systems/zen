# GCP Service Account Authentication Documentation

## Overview
This document describes the centralized GCP service account authentication system for the Netra Apex Platform. All GCP operations MUST use the standardized authentication configuration to ensure consistency and security.

## Service Account Key Location
**Primary Key File:** `config/netra-staging-7a1059b7cf26.json`
- Service Account Email: `netra-staging-deploy@netra-staging.iam.gserviceaccount.com`
- Project ID: `netra-staging`

## Centralized Authentication Module
The `scripts/gcp_auth_config.py` module provides centralized authentication for all GCP operations.

### Key Features:
1. **Automatic Key Discovery** - Searches predefined locations for service account keys
2. **Environment Setup** - Sets `GOOGLE_APPLICATION_CREDENTIALS` automatically
3. **gcloud CLI Integration** - Activates service account in gcloud CLI
4. **Validation** - Verifies key file structure and permissions

### Usage in Scripts

#### Basic Usage
```python
from gcp_auth_config import GCPAuthConfig

# Ensure authentication is set up
if not GCPAuthConfig.ensure_authentication():
    print("Authentication failed")
    sys.exit(1)

# Now you can use any GCP client library
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
```

#### Custom Key Path
```python
from pathlib import Path
from gcp_auth_config import GCPAuthConfig

# Use a specific service account key
key_path = Path("path/to/custom-key.json")
if not GCPAuthConfig.setup_authentication(key_path):
    print("Authentication failed")
    sys.exit(1)
```

## Updated GCP Scripts

### 1. **deploy_to_gcp.py** - Main Deployment Script
- **Purpose:** Deploy services to Google Cloud Run
- **Authentication:** Uses centralized `GCPAuthConfig` module
- **Usage:**
  ```bash
  # Uses default service account from config/
  python scripts/deploy_to_gcp.py --project netra-staging --build-local
  
  # Or specify custom key
  python scripts/deploy_to_gcp.py --project netra-staging --service-account path/to/key.json
  ```

### 2. **fetch_secrets_to_env.py** - Secret Manager Access
- **Purpose:** Fetch secrets from Google Secret Manager
- **Authentication:** Automatically uses `GCPAuthConfig.ensure_authentication()`
- **New Features:**
  - Lists all available secrets with `--list`
  - Comprehensive secret mappings for all services
  - Environment-specific configurations
- **Usage:**
  ```bash
  # List all secrets in Secret Manager
  python scripts/fetch_secrets_to_env.py --list
  
  # Fetch secrets for staging
  python scripts/fetch_secrets_to_env.py --environment staging
  
  # Force overwrite existing .env
  python scripts/fetch_secrets_to_env.py --force
  ```

### 3. **audit_oauth_gcp_logs.py** - Cloud Logging Access
- **Purpose:** Analyze OAuth logs in GCP Cloud Logging
- **Authentication:** Uses `GCPAuthConfig` for client initialization
- **Usage:**
  ```bash
  python scripts/audit_oauth_gcp_logs.py --project netra-staging --hours 24
  ```

### 4. **setup_gcp_service_account.py** - Service Account Management
- **Purpose:** Create and configure service accounts
- **Authentication:** Uses existing gcloud authentication
- **Usage:**
  ```bash
  python scripts/setup_gcp_service_account.py --project netra-staging
  ```

## Environment Variables

### Automatically Set
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account key file

### Required for Specific Environments
- `ENVIRONMENT` - development/staging/production
- `GCP_PROJECT_ID` - Override default project ID

## Secret Manager Mappings

The `fetch_secrets_to_env.py` script now includes comprehensive mappings for:

### API Keys
- `gemini-api-key` → `GEMINI_API_KEY`
- `openai-api-key` → `OPENAI_API_KEY`
- `anthropic-api-key` → `ANTHROPIC_API_KEY`
- `groq-api-key` → `GROQ_API_KEY`
- `replicate-api-key` → `REPLICATE_API_KEY`
- `perplexity-api-key` → `PERPLEXITY_API_KEY`
- `netra-api-key` → `NETRA_API_KEY`

### OAuth Configuration
- `google-client-id` → `GOOGLE_CLIENT_ID`
- `google-client-secret` → `GOOGLE_CLIENT_SECRET`

### Database Credentials
- `clickhouse-*-password` → `CLICKHOUSE_*_PASSWORD`
- `postgres-*-password` → `POSTGRES_*_PASSWORD`
- `redis-*-password` → `REDIS_*_PASSWORD`

### Security Keys
- `jwt-secret-key` → `JWT_SECRET_KEY`
- `fernet-key` → `FERNET_KEY`
- `encryption-key` → `ENCRYPTION_KEY`
- `session-secret-key` → `SESSION_SECRET_KEY`

### Monitoring & Analytics
- `langfuse-*` → `LANGFUSE_*`
- `sentry-dsn` → `SENTRY_DSN`
- `mixpanel-token` → `MIXPANEL_TOKEN`
- `posthog-api-key` → `POSTHOG_API_KEY`

### Communication Services
- `sendgrid-api-key` → `SENDGRID_API_KEY`
- `twilio-*` → `TWILIO_*`

### Payment Processing
- `stripe-*` → `STRIPE_*`

## Troubleshooting

### Authentication Fails
1. Check key file exists: `config/netra-staging-7a1059b7cf26.json`
2. Verify key file is valid JSON with required fields
3. Run diagnostic: `python scripts/gcp_auth_config.py`

### Missing Secrets
1. List all secrets: `python scripts/fetch_secrets_to_env.py --list`
2. Check if secret exists in Secret Manager
3. Verify secret name mapping in `_get_secret_mappings()`

### Permission Errors
Ensure service account has required roles:
- `roles/secretmanager.secretAccessor` - For reading secrets
- `roles/logging.viewer` - For reading logs
- `roles/run.admin` - For Cloud Run deployments
- `roles/storage.admin` - For container registry

## Best Practices

1. **Never commit service account keys** to version control
2. **Use centralized authentication** - Always import `GCPAuthConfig`
3. **Handle authentication failures** gracefully with proper error messages
4. **Test authentication** before running operations
5. **Document new secrets** when adding to Secret Manager

## Testing Authentication

Run the authentication test:
```bash
python scripts/gcp_auth_config.py
```

Expected output:
```
✅ Found service account key: config/netra-staging-7a1059b7cf26.json
✅ Set GOOGLE_APPLICATION_CREDENTIALS
✅ Service account activated in gcloud
✅ Authentication setup successful!
```

## Security Considerations

1. **Key Rotation:** Service account keys should be rotated regularly
2. **Least Privilege:** Grant only necessary permissions to service accounts
3. **Audit Logging:** Monitor service account usage in Cloud Audit Logs
4. **Key Storage:** Store keys securely, never in public repositories

## Future Improvements

1. **Workload Identity:** Migrate to Workload Identity for GKE deployments
2. **Key Rotation Automation:** Implement automatic key rotation
3. **Multi-Environment Support:** Enhanced support for multiple GCP projects
4. **Secret Versioning:** Track and manage secret versions

## Contact

For issues or questions about GCP authentication:
1. Check this documentation
2. Run diagnostics: `python scripts/gcp_auth_config.py`
3. Review Cloud Console IAM permissions
4. Contact the DevOps team

---
*Last Updated: 2025-08-23*
*Document Version: 1.0*