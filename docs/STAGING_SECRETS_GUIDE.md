# Secrets Configuration Guide

This guide covers secrets management for Development, Staging, and Production environments following the security architecture defined in `SPEC/PRODUCTION_SECRETS_ISOLATION.xml`.

## Environment Isolation Architecture

### Security Zones
The platform uses three isolated security zones:

1. **Production Zone** (RESTRICTED)
   - Zero-trust access model
   - Service Account with Workload Identity required
   - Complete isolation from development credentials
   - Project: `netra-prod-{suffix}`

2. **Staging Zone** (CONTROLLED)  
   - Least-privilege access model
   - Service Account with limited scope
   - Isolated databases and namespaces per PR
   - Project: `netra-staging-{suffix}`

3. **Development Zone** (INTERNAL)
   - Default-deny access model
   - Google Cloud Application Default Credentials
   - Local development with `.env` files
   - Project: `netra-dev-{suffix}`

### Critical Security Boundary
**IMPORTANT**: Development accounts using Google Cloud Application Default Credentials are COMPLETELY ISOLATED from production secrets through:
- Organization Policy Enforcement
- IAM Deny Policies
- VPC Service Controls
- Conditional Access Policies

## Development Environment Secrets

### IAM Permission Requirements

**CRITICAL**: Before accessing secrets, developers MUST have the `roles/secretmanager.secretAccessor` permission in addition to any project-level permissions (Editor, Viewer, etc.).

#### Required Permissions for Developers
1. **Project Editor/Viewer** - General project access
2. **Secret Manager Secret Accessor** (`roles/secretmanager.secretAccessor`) - **ESSENTIAL for reading secrets**
   - ⚠️ **This is NOT included in Editor or Viewer roles**
   - ⚠️ **Without this, you will get "Permission Denied" errors**

#### Granting Secret Accessor Permission
```bash
# For your own account
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="user:your-email@example.com" \
    --role="roles/secretmanager.secretAccessor"

# Verify you have the permission
gcloud projects get-iam-policy YOUR_PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:$(gcloud config get-value account)" \
    --format="table(bindings.role)" | grep secretAccessor
```

### Local Development Setup

#### Option 1: Automatic Secret Fetching (Recommended)
```bash
# Requires Google Cloud authentication AND Secret Accessor permission
gcloud auth application-default login

# Verify you have secret access permission first!
gcloud projects get-iam-policy YOUR_PROJECT_ID \
    --filter="bindings.members:$(gcloud config get-value account)" \
    --format="table(bindings.role)" | grep secretAccessor

# If missing, request Secret Accessor permission from your admin
# Then fetch development secrets
python scripts/fetch_secrets_to_env.py
```

This fetches the following secrets from Google Secret Manager:
- `gemini-api-key` → `GEMINI_API_KEY` (Required)
- `google-client-id` → `GOOGLE_CLIENT_ID`
- `google-client-secret` → `GOOGLE_CLIENT_SECRET`
- `jwt-secret-key` → `JWT_SECRET_KEY`
- `fernet-key` → `FERNET_KEY`
- `clickhouse-default-password` → `CLICKHOUSE_DEFAULT_PASSWORD`
- `langfuse-secret-key` → `LANGFUSE_SECRET_KEY`
- `langfuse-public-key` → `LANGFUSE_PUBLIC_KEY`

#### Option 2: Manual `.env` Configuration
Create a `.env` file in the project root:

```bash
# Core Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database URLs
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/netra_db
# Fallback: DATABASE_URL=sqlite+aiosqlite:///./netra.db

# Optional Services
REDIS_URL=redis://localhost:6379
CLICKHOUSE_URL=clickhouse://localhost:9000/netra_analytics

# Security Keys (generate secure keys)
JWT_SECRET_KEY=your-super-secret-jwt-key
FERNET_KEY=generate-with-python-cryptography-fernet
SECRET_KEY=your-application-secret-key

# OAuth Configuration
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
FRONTEND_URL=http://localhost:3000

# LLM API Keys (Required: at least one)
GEMINI_API_KEY=your-gemini-api-key  # Primary LLM
OPENAI_API_KEY=your-openai-key      # Optional
ANTHROPIC_API_KEY=your-anthropic-key # Optional

# Development Options
DEV_MODE_DISABLE_REDIS=false
DEV_MODE_DISABLE_CLICKHOUSE=false
DEV_MODE_DISABLE_LLM=false
```

### Generating Security Keys
```python
# Generate JWT Secret
import secrets
print(secrets.token_urlsafe(64))

# Generate Fernet Key
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())

# Generate Secret Key
import secrets
print(secrets.token_hex(32))
```

### Using Dev Launcher with Secrets
```bash
# Load secrets from Google Secret Manager during startup
python dev_launcher.py --dynamic --no-backend-reload --load-secrets

# Or specify a project ID
python dev_launcher.py --dynamic --load-secrets --project-id your-project-id
```

## Staging Environment Secrets

### Required GitHub Secrets

### 1. Google Cloud Platform
- **`GCP_STAGING_SA_KEY`**: Service account JSON key for GCP staging project
  - Required permissions: Cloud Run Admin, Cloud SQL Admin, Secret Manager Admin
  - Create via: `gcloud iam service-accounts keys create key.json --iam-account=staging-sa@PROJECT_ID.iam.gserviceaccount.com`

### 2. Database Credentials
- **`STAGING_DB_PASSWORD`**: PostgreSQL password for PR-specific databases
  - Used for all PR staging databases
  - Should be a strong, randomly generated password
  - Example: `openssl rand -base64 32`

### 3. ClickHouse Configuration
- **`CLICKHOUSE_PASSWORD`**: Password for ClickHouse Cloud connection
  - Required for metrics and analytics storage
  - Get from ClickHouse Cloud console
  - Used to prevent connection timeouts
  
  **Note**: The application may also look for this secret in Google Secret Manager as:
  - `clickhouse-default-password-staging` (for staging environments)
  - `clickhouse-default-password` (for production)
  - The GitHub Actions secret `CLICKHOUSE_PASSWORD` is passed to both environment variables

### 4. OAuth Configuration (Optional)
- **`GOOGLE_OAUTH_CLIENT_ID_STAGING`**: OAuth client ID for staging
- **`GOOGLE_OAUTH_CLIENT_SECRET_STAGING`**: OAuth client secret for staging

## Setting Secrets in GitHub

### Via GitHub UI:
1. Go to your repository on GitHub
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret with the appropriate name and value

### Via GitHub CLI:
```bash
# Install GitHub CLI if not already installed
# brew install gh (macOS) or see https://cli.github.com/

# Authenticate
gh auth login

# Set secrets
gh secret set GCP_STAGING_SA_KEY < path/to/service-account-key.json
gh secret set STAGING_DB_PASSWORD -b "your-secure-password"
gh secret set CLICKHOUSE_PASSWORD -b "your-clickhouse-password"
```

## Terraform Variables

The staging Terraform configuration now accepts these additional variables:

```hcl
variable "clickhouse_password" {
  description = "ClickHouse password for authentication"
  type        = string
  sensitive   = true
}

variable "clickhouse_url" {
  description = "Full ClickHouse URL with credentials (optional)"
  type        = string
  default     = ""
  sensitive   = true
}
```

## Environment Variables Set in Cloud Run

The following environment variables are automatically configured for each PR staging environment:

### Database Connection
- `DATABASE_URL`: Full PostgreSQL connection string with PR-specific database
- `POSTGRES_HOST`: Cloud SQL instance connection name
- `POSTGRES_DB`: PR-specific database name (e.g., `netra_pr_123`)
- `POSTGRES_USER`: PR-specific user (e.g., `user_pr_123`)
- `POSTGRES_PASSWORD`: From `STAGING_DB_PASSWORD` secret

### Redis Connection
- `REDIS_URL`: Redis connection string with PR-specific database index
- `REDIS_HOST`: Shared Redis instance host
- `REDIS_PORT`: Redis port (default: 6379)
- `REDIS_DB`: PR-specific database index (PR number % 16)

### ClickHouse Connection
- `CLICKHOUSE_URL`: Full ClickHouse connection URL with credentials
- `CLICKHOUSE_HOST`: ClickHouse Cloud host
- `CLICKHOUSE_PORT`: ClickHouse port (8443 for secure connections)
- `CLICKHOUSE_USER`: ClickHouse username (default: "default")
- `CLICKHOUSE_PASSWORD`: From `CLICKHOUSE_PASSWORD` secret
- `CLICKHOUSE_SECURE`: Set to "true" for SSL connections
- `CLICKHOUSE_TIMEOUT`: Connection timeout in seconds (default: 60)

### Other Configuration
- `PR_NUMBER`: The pull request number
- `ENVIRONMENT`: Set to "staging"
- `GCP_PROJECT_ID`: GCP project ID
- `SECRET_MANAGER_PROJECT`: Project ID for Secret Manager access
- `LOAD_SECRETS`: Set to "true" to load additional secrets from Secret Manager

## Troubleshooting

### PostgreSQL Connection Issues
If you see "FATAL: password authentication failed":
1. Verify `STAGING_DB_PASSWORD` secret is set correctly
2. Check that the PR-specific user was created in Terraform
3. Ensure Cloud SQL proxy is running for migrations

### Redis Connection Issues
If Redis is not available:
1. Check that the shared Redis instance exists in `terraform/staging/shared-infrastructure`
2. Verify VPC connector is configured correctly
3. Ensure the PR uses a unique database index (0-15)

### ClickHouse Timeout Issues
If you see "Connection to xedvrr4c3r.us-central1.gcp.clickhouse.cloud timed out":
1. Verify `CLICKHOUSE_PASSWORD` secret is set
2. Check ClickHouse Cloud service is active
3. Increase `CLICKHOUSE_TIMEOUT` if needed
4. Verify network connectivity from Cloud Run

### Staging Secret Manager Configuration

**IMPORTANT**: Staging uses Google Secret Manager with `-staging` suffix to maintain isolation:

| Production Secret | Staging Secret | Purpose |
|------------------|----------------|----------|
| `gemini-api-key` | `gemini-api-key-staging` | LLM API access |
| `jwt-secret-key` | `jwt-secret-key-staging` | JWT token signing |
| `fernet-key` | `fernet-key-staging` | Encryption key |
| `openai-api-key` | `openai-api-key-staging` | OpenAI API (optional) |
| `clickhouse-default-password` | `clickhouse-default-password-staging` | ClickHouse access |

### Creating Staging Secrets in Secret Manager
```bash
# Set staging project
export PROJECT_ID=netra-staging-xxxxx

# Create staging secrets
echo -n "your-staging-gemini-key" | gcloud secrets create gemini-api-key-staging \
  --data-file=- --project=$PROJECT_ID

echo -n "your-staging-jwt-key" | gcloud secrets create jwt-secret-key-staging \
  --data-file=- --project=$PROJECT_ID

echo -n "your-staging-fernet-key" | gcloud secrets create fernet-key-staging \
  --data-file=- --project=$PROJECT_ID
```

## Production Environment Secrets

### Zero-Trust Production Access

**CRITICAL**: Production secrets are completely isolated from development credentials:

1. **Never Accessible Via**:
   - Google Cloud Application Default Credentials
   - Personal developer accounts
   - Development or staging service accounts
   - Cross-project access from dev/staging

2. **Only Accessible Via**:
   - Service accounts with Workload Identity
   - From within production VPC (10.0.0.0/16)
   - With verified principal.workloadIdentity
   - Through VPC Service Controls perimeter

### Production Secret Management

Production secrets are managed exclusively through:

1. **Terraform/IaC**: Infrastructure as Code deployment
2. **CI/CD Pipeline**: Automated deployment with service accounts
3. **Break-Glass Access**: Emergency access with audit logging

```bash
# Production secrets are NOT directly accessible
# They must be deployed through CI/CD or Terraform

# Example: Terraform variable for production
variable "gemini_api_key" {
  description = "Production Gemini API Key"
  type        = string
  sensitive   = true
}

# Applied through CI/CD with:
terraform apply -var="gemini_api_key=$PROD_GEMINI_KEY"
```

## Shared Infrastructure Setup

Before PR staging environments can work, the shared infrastructure must be deployed once:

```bash
cd terraform/staging/shared-infrastructure
terraform init
terraform apply \
  -var="project_id=your-staging-project" \
  -var="region=us-central1" \
  -var="staging_domain=staging.yourdomain.com"
```

This creates:
- Shared VPC and subnets
- Shared PostgreSQL instance (PR environments create databases)
- Shared Redis instance (PR environments use different database indices)
- VPC connector for Cloud Run
- Service account with necessary permissions

## Security Best Practices

### Do's
- ✅ Use separate API keys for each environment
- ✅ Rotate secrets regularly (90 days for production)
- ✅ Use Google Secret Manager for cloud environments
- ✅ Keep development secrets in `.env` files (git-ignored)
- ✅ Use service accounts for production access
- ✅ Enable audit logging for all secret access

### Don'ts
- ❌ Never commit secrets to git
- ❌ Never use production secrets in development
- ❌ Never share secrets between environments
- ❌ Never use personal credentials in production
- ❌ Never bypass VPC Service Controls
- ❌ Never disable security monitoring

## Monitoring and Alerts

### Security Event Monitoring
The following events trigger immediate alerts:

1. **Unauthorized Production Access Attempt**
   - Developer account attempting production secret access
   - Cross-project access attempts
   - VPC Service Control violations

2. **Suspicious Secret Access Patterns**
   - High-frequency secret access
   - Access from unknown IPs
   - Failed authentication attempts

### Audit Logging
All secret access is logged with:
- Principal identity
- Access timestamp
- Secret name and version
- Source IP and location
- Success/failure status

## Cost Optimization

The staging setup is optimized for cost:
- **Shared Resources**: Single PostgreSQL and Redis instance for all PRs
- **Scale to Zero**: Cloud Run services scale to 0 when idle
- **PR Isolation**: Each PR gets its own database and Redis namespace
- **Automatic Cleanup**: Environments destroyed when PR is closed
- **Secret Rotation**: Automated rotation reduces manual overhead

Estimated cost per PR: ~$2-5/day when active, $0 when idle.

## Quick Reference

### Environment Detection in Code
```python
# The app automatically detects environment
if os.getenv('ENVIRONMENT') == 'production':
    # Production: Use Workload Identity
    # Secrets from Secret Manager (no suffix)
    pass
elif os.getenv('ENVIRONMENT') == 'staging':
    # Staging: Use service account
    # Secrets from Secret Manager with -staging suffix
    pass
else:
    # Development: Use .env file or 
    # fetch_secrets_to_env.py for development secrets
    pass
```

### Secret Loading Priority
1. Environment variables (highest priority)
2. `.env` file (development only)
3. Google Secret Manager (cloud environments)
4. Default values (lowest priority)

### Emergency Procedures

#### Secret Compromise
1. Immediately rotate the compromised secret
2. Update all affected services
3. Review audit logs for unauthorized access
4. File security incident report

#### Lost Access to Secrets
1. Use break-glass procedure (production only)
2. Contact security team for temporary access
3. Document reason for access
4. Restore normal access ASAP