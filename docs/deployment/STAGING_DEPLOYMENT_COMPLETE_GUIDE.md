# Complete Staging Deployment Guide for Netra Platform

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Environment Detection](#environment-detection)
5. [Secret Management](#secret-management)
6. [Deployment Process](#deployment-process)
7. [Configuration Details](#configuration-details)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

## Overview

The Netra staging environment provides isolated PR-based deployments with automatic provisioning, secret management, and comprehensive testing capabilities.

### Key Features
- **Automatic PR Deployments**: Each PR gets its own isolated environment
- **Secret Isolation**: Staging secrets are completely separate from production
- **Fast Provisioning**: ~2-3 minutes deployment time
- **Automatic Cleanup**: Environments are destroyed when PRs close
- **Shared Infrastructure**: Uses shared VPC, Redis, and SQL instances for efficiency

## Architecture

### Staging Infrastructure Components

```
┌─────────────────────────────────────────────────────┐
│                 Google Cloud Platform                │
│                   (netra-staging)                    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │            Shared Infrastructure             │   │
│  ├──────────────────────────────────────────────┤   │
│  │ • VPC Network                                │   │
│  │ • Cloud SQL (PostgreSQL)                     │   │
│  │ • Redis Instance                             │   │
│  │ • VPC Connector                              │   │
│  │ • SSL Certificate                            │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │         PR-Specific Resources (pr-N)         │   │
│  ├──────────────────────────────────────────────┤   │
│  │ • Cloud Run Services:                        │   │
│  │   - backend-pr-N                             │   │
│  │   - frontend-pr-N                            │   │
│  │ • Database: netra_pr_N                       │   │
│  │ • Redis DB: N % 16                           │   │
│  │ • URLs:                                      │   │
│  │   - https://pr-N.staging.netrasystems.ai     │   │
│  │   - https://pr-N-api.staging.netrasystems.ai │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │            Secret Manager                     │   │
│  ├──────────────────────────────────────────────┤   │
│  │ All secrets with -staging suffix:            │   │
│  │ • gemini-api-key-staging (REQUIRED)          │   │
│  │ • jwt-secret-key-staging                     │   │
│  │ • fernet-key-staging                         │   │
│  │ • google-client-id-staging                   │   │
│  │ • google-client-secret-staging               │   │
│  │ • [optional-llm-keys]-staging                │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. GCP Setup
```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud auth application-default login

# Set project
gcloud config set project netra-staging
```

### 2. Required Permissions
- `roles/secretmanager.admin` - For secret management
- `roles/run.admin` - For Cloud Run deployments
- `roles/cloudsql.admin` - For database management
- `roles/compute.networkAdmin` - For VPC access

### 3. GitHub Secrets Required
These must be set in the repository settings:
- `GCP_STAGING_SA_KEY` - Service account key for staging deployments
- `STAGING_DB_PASSWORD` - PostgreSQL password for staging databases

## Environment Detection

The application automatically detects staging environment through multiple signals:

### Detection Logic (app/config.py)
```python
def _get_environment(self) -> str:
    if os.environ.get("TESTING"):
        return "testing"
    
    # Cloud Run detection
    if os.environ.get("K_SERVICE") or os.environ.get("K_REVISION"):
        # We're in Cloud Run - check for staging indicators
        if "staging" in os.environ.get("K_SERVICE", "").lower():
            return "staging"
        if os.environ.get("PR_NUMBER"):
            return "staging"  # PR deployments are staging
    
    return os.environ.get("ENVIRONMENT", "development").lower()
```

### Environment Variables Set by Deployment
- `ENVIRONMENT=staging`
- `K_SERVICE=backend-pr-N` (Cloud Run service name)
- `PR_NUMBER=N` (Pull request number)
- `GCP_PROJECT_ID=netra-staging`
- `GCP_PROJECT_ID_NUMERICAL=<project-number>`

## Secret Management

### Naming Convention
**CRITICAL**: All staging secrets use a `-staging` suffix!

| Configuration Expects | Secret Manager Name | Required |
|--------------------|---------------------|----------|
| `gemini-api-key` | `gemini-api-key-staging` | ✅ Yes |
| `jwt-secret-key` | `jwt-secret-key-staging` | ✅ Yes |
| `fernet-key` | `fernet-key-staging` | ✅ Yes |
| `google-client-id` | `google-client-id-staging` | ✅ Yes |
| `google-client-secret` | `google-client-secret-staging` | ✅ Yes |
| `anthropic-api-key` | `anthropic-api-key-staging` | ❌ Optional |
| `openai-api-key` | `openai-api-key-staging` | ❌ Optional |

### Creating Secrets

#### Quick Setup Script
```bash
#!/bin/bash
PROJECT_NAME="netra-staging"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_NAME --format="value(projectNumber)")

# Function to create staging secret
create_staging_secret() {
    SECRET_NAME="${1}-staging"  # Add -staging suffix
    SECRET_VALUE="$2"
    
    echo "Creating $SECRET_NAME..."
    echo -n "$SECRET_VALUE" | gcloud secrets create "$SECRET_NAME" \
        --project="$PROJECT_NAME" \
        --data-file=- \
        --replication-policy="automatic"
    
    # Grant access to service account
    gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
        --project="$PROJECT_NAME" \
        --member="serviceAccount:staging-environments@$PROJECT_NAME.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"
}

# Create required secrets
create_staging_secret "gemini-api-key" "YOUR_GEMINI_KEY"
create_staging_secret "jwt-secret-key" "$(openssl rand -hex 32)"
create_staging_secret "fernet-key" "$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
```

### How Secret Loading Works

1. **Configuration expects**: `gemini-api-key` (no suffix)
2. **Secret Manager check**: In staging, automatically looks for `gemini-api-key-staging`
3. **Fallback**: If Secret Manager fails, falls back to environment variables

```python
# app/core/secret_manager.py
def _load_from_secret_manager(self):
    # Check if staging
    is_staging = environment == "staging" or os.environ.get("K_SERVICE")
    
    for secret_name in secret_names:
        # Append -staging suffix in staging environment
        actual_secret_name = f"{secret_name}-staging" if is_staging else secret_name
        secret_value = self._fetch_secret(client, actual_secret_name)
```

## Deployment Process

### Automatic PR Deployment

When a PR is opened or updated:

1. **GitHub Actions Trigger** (`.github/workflows/staging-environment.yml`)
2. **Build Docker Images**
   - Backend: ~2-3 minutes
   - Frontend: ~1-2 minutes
3. **Terraform Provisioning**
   - Create database and user
   - Deploy Cloud Run services
   - Configure networking
4. **Database Migrations**
   - Run Alembic migrations
   - Seed test data
5. **Health Checks**
   - Wait for services to be ready
   - Run smoke tests

### Manual Deployment
```bash
# Trigger manually via GitHub Actions
gh workflow run staging-environment.yml \
  --ref your-branch \
  -f action=deploy \
  -f pr_number=123
```

### Teardown Process
```bash
# Manual teardown
gh workflow run staging-environment.yml \
  --ref main \
  -f action=destroy \
  -f pr_number=123
```

## Configuration Details

### Database Configuration
Each PR gets its own database:
- **Database Name**: `netra_pr_${PR_NUMBER}`
- **User**: `user_pr_${PR_NUMBER}`
- **Connection**: Via Cloud SQL Proxy socket

### Redis Configuration
- **Shared Redis Instance**: All PRs share one Redis
- **Database Isolation**: Each PR uses `DB ${PR_NUMBER % 16}`
- **Connection**: Via VPC connector

### ClickHouse Configuration
```env
CLICKHOUSE_URL=clickhouse://default:@clickhouse_host_url_placeholder:8443/default?secure=1
CLICKHOUSE_TIMEOUT=30
```

### Service URLs
- **Frontend**: `https://pr-${PR_NUMBER}.staging.netrasystems.ai`
- **Backend API**: `https://pr-${PR_NUMBER}-api.staging.netrasystems.ai`

### Resource Limits
```yaml
Backend:
  CPU: 2 cores
  Memory: 4Gi
  Min Instances: 0
  Max Instances: 3

Frontend:
  CPU: 1 core
  Memory: 512Mi
  Min Instances: 0
  Max Instances: 3
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Secret Not Found
**Error**: `Failed to fetch secret gemini-api-key`

**Solution**:
```bash
# Check if secret exists with -staging suffix
gcloud secrets list --project=netra-staging | grep gemini

# Should show: gemini-api-key-staging (NOT gemini-api-key)
```

#### 2. Database Connection Failed
**Error**: `connection to server at "localhost" (127.0.0.1), port 5432 failed`

**Solution**:
- Ensure `DATABASE_URL` uses Cloud SQL socket path
- Check Cloud SQL proxy is configured in Terraform
- Verify service account has `cloudsql.client` role

#### 3. LLM API Key Missing
**Error**: `LLM 'default': Gemini API key is required`

**Solution**:
```bash
# Create Gemini API key
# Visit: https://aistudio.google.com/app/apikey
# Then add to Secret Manager:
echo -n "YOUR_KEY" | gcloud secrets create gemini-api-key-staging \
  --data-file=- --project=netra-staging
```

#### 4. Startup Check Failures
**Non-Critical in Staging**:
- Redis connection failures
- ClickHouse connection timeouts
- Optional LLM provider failures

These are logged but don't prevent deployment in staging.

#### 5. Numerical Project ID Issues
**Error**: `Invalid project ID in Secret Manager`

**Solution**:
```bash
# Get numerical project ID
PROJECT_NUMBER=$(gcloud projects describe netra-staging --format="value(projectNumber)")
echo "Numerical ID: $PROJECT_NUMBER"

# Ensure it's set in environment
export GCP_PROJECT_ID_NUMERICAL=$PROJECT_NUMBER
```

### Debugging Commands

```bash
# View Cloud Run logs
gcloud run services logs read backend-pr-4 --project=netra-staging

# Check secret access
gcloud secrets versions access latest \
  --secret=gemini-api-key-staging \
  --project=netra-staging

# Test database connection
gcloud sql connect staging-shared-postgres \
  --user=user_pr_4 \
  --database=netra_pr_4 \
  --project=netra-staging

# Check service status
gcloud run services describe backend-pr-4 \
  --region=us-central1 \
  --project=netra-staging
```

## Best Practices

### 1. Secret Management
- ✅ Always use `-staging` suffix for staging secrets
- ✅ Never share secrets between production and staging
- ✅ Rotate secrets regularly
- ✅ Use least privilege access

### 2. Resource Management
- ✅ Set appropriate resource limits
- ✅ Use min_instances=0 to save costs
- ✅ Enable auto-scaling for traffic spikes
- ✅ Clean up stale environments

### 3. Testing
- ✅ Run smoke tests on every deployment
- ✅ Test with realistic data volumes
- ✅ Verify WebSocket connections
- ✅ Check authentication flows

### 4. Monitoring
- ✅ Enable Cloud Logging
- ✅ Set up error alerting
- ✅ Monitor resource usage
- ✅ Track deployment times

### 5. Cost Optimization
- ✅ Use shared infrastructure
- ✅ Set TTL for environments (7 days default)
- ✅ Scale to zero when idle
- ✅ Use spot instances where possible

## Environment Variables Reference

### Required
```env
ENVIRONMENT=staging
DATABASE_URL=postgresql://user:pass@/db?host=/cloudsql/...
REDIS_URL=redis://host:6379/N
SECRET_KEY=<from-secret-manager>
GCP_PROJECT_ID=netra-staging
GCP_PROJECT_ID_NUMERICAL=<project-number>
LOAD_SECRETS=true
```

### Optional
```env
CLICKHOUSE_URL=clickhouse://...
LANGFUSE_SECRET_KEY=<from-secret-manager>
SENTRY_DSN=<from-secret-manager>
LOG_LEVEL=INFO
SKIP_MIGRATION_ON_STARTUP=false
```

## GitHub Actions Workflow

The staging deployment is managed by `.github/workflows/staging-environment.yml`:

### Triggers
- `pull_request`: [opened, synchronize, closed]
- `workflow_dispatch`: Manual trigger

### Key Steps
1. Check eligibility (labels, branch protection)
2. Build and push Docker images
3. Run Terraform to provision resources
4. Execute database migrations
5. Run health checks and tests
6. Post deployment URL to PR

### Performance Optimizations
- Docker layer caching
- Parallel builds for frontend/backend
- Shared infrastructure (no provisioning wait)
- Conditional rebuilds based on file changes

## Next Steps

1. **For Developers**:
   - Read [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md)
   - Review [TESTING_GUIDE.md](TESTING_GUIDE.md)
   - Check [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

2. **For DevOps**:
   - Review [terraform/staging/](../terraform/staging/)
   - Check [.github/workflows/](../.github/workflows/)
   - Monitor [Cloud Console](https://console.cloud.google.com/home/dashboard?project=netra-staging)

3. **For Security**:
   - Audit [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=netra-staging)
   - Review [IAM Policies](https://console.cloud.google.com/iam-admin/iam?project=netra-staging)
   - Check [Security Command Center](https://console.cloud.google.com/security/command-center?project=netra-staging)

---

**Last Updated**: August 2025
**Maintained By**: Netra Platform Team
**Questions**: Contact DevOps Team or create an issue in the repository