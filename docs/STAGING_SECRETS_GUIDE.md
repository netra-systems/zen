# Staging Environment Secrets Configuration Guide

## Required GitHub Secrets

The following secrets must be configured in your GitHub repository for the staging environment to work properly:

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

## Cost Optimization

The staging setup is optimized for cost:
- **Shared Resources**: Single PostgreSQL and Redis instance for all PRs
- **Scale to Zero**: Cloud Run services scale to 0 when idle
- **PR Isolation**: Each PR gets its own database and Redis namespace
- **Automatic Cleanup**: Environments destroyed when PR is closed

Estimated cost per PR: ~$2-5/day when active, $0 when idle.