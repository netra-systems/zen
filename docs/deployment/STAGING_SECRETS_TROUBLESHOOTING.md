# Staging Secrets Loading Troubleshooting Guide

## Problem Description
The staging environment fails to load secrets from Google Secret Manager with the error:
```
File "/app/app/config.py", line 448, in <module>
settings = get_config()
```

## Root Cause
The staging deployment was missing critical environment variables needed for the SecretManager to:
1. Know which GCP project to use for Secret Manager API calls
2. Know that it should load secrets with the `-staging` suffix
3. Have the correct environment variable names matching what the application expects

## Solution

### 1. Terraform Configuration Updates

The following changes were made to `terraform-gcp/main.tf`:

#### Added Environment Variables:
```hcl
env {
  name  = "GCP_PROJECT_ID_NUMERICAL_STAGING"
  value = var.project_id_numerical != "" ? var.project_id_numerical : var.project_id
}

env {
  name  = "SECRET_MANAGER_PROJECT_ID"
  value = var.project_id_numerical != "" ? var.project_id_numerical : var.project_id
}

env {
  name  = "LOAD_SECRETS"
  value = "true"
}
```

#### Fixed Environment Variable Names:
- Changed `GOOGLE_GEMINI_API_KEY` to `GEMINI_API_KEY`
- Changed `SECRET_KEY` to `JWT_SECRET_KEY`
- Changed `GOOGLE_OAUTH_CLIENT_ID` to `GOOGLE_CLIENT_ID`
- Changed `GOOGLE_OAUTH_CLIENT_SECRET` to `GOOGLE_CLIENT_SECRET`

#### Updated Secret References:
All secrets now properly reference the staging versions with Cloud Run Secret Manager integration:
```hcl
env {
  name  = "GEMINI_API_KEY"
  value_from {
    secret_key_ref {
      name = "gemini-api-key-staging"
      key  = "latest"
    }
  }
}
```

### 2. Variable Configuration

Added to `terraform-gcp/variables.tf`:
```hcl
variable "project_id_numerical" {
  description = "GCP Project ID in numerical format for Secret Manager API"
  type        = string
  default     = ""
}
```

### 3. Required Secrets in GCP Secret Manager

The following secrets must exist in the staging project with the `-staging` suffix:

**Critical (Required):**
- `gemini-api-key-staging`
- `google-client-id-staging`
- `google-client-secret-staging`
- `jwt-secret-key-staging`
- `fernet-key-staging`

**Optional:**
- `anthropic-api-key-staging`
- `openai-api-key-staging`
- `langfuse-secret-key-staging`
- `langfuse-public-key-staging`
- `clickhouse-default-password-staging`

## Deployment Steps

### 1. Create Secrets in Secret Manager
```bash
# Use the provided script
python scripts/create_staging_secrets.py <project-id>

# Or manually create each secret
echo "your-secret-value" | gcloud secrets create gemini-api-key-staging \
  --data-file=- --project=<project-id>
```

### 2. Apply Terraform Changes
```bash
cd terraform-gcp
terraform apply -var="project_id=netra-staging" \
                -var="project_id_numerical=<numerical-project-id>"
```

### 3. Verify Deployment
Check Cloud Run logs to ensure secrets are loading:
```bash
gcloud run services logs read netra-backend --project=<project-id>
```

## How SecretManager Works in Staging

1. **Environment Detection**: The `SecretManager` class checks the `ENVIRONMENT` variable
2. **Project ID Resolution**: Uses `GCP_PROJECT_ID_NUMERICAL_STAGING` first, then falls back to `SECRET_MANAGER_PROJECT_ID`
3. **Secret Name Resolution**: In staging, appends `-staging` suffix to all secret names
4. **Loading Process**:
   - First loads from environment variables as base
   - Then loads from Google Secret Manager (these override env vars)
   - Merges both sources with Google Secrets taking precedence

## Common Issues and Solutions

### Issue 1: Permission Denied (403)
**Solution**: Ensure the Cloud Run service account has the `secretmanager.secretAccessor` role:
```bash
gcloud projects add-iam-policy-binding <project-id> \
  --member="serviceAccount:netra-cloudrun@<project-id>.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Issue 2: Secret Not Found (404)
**Solution**: Verify the secret exists with the correct name:
```bash
gcloud secrets list --project=<project-id> | grep staging
```

### Issue 3: Wrong Project ID
**Solution**: Verify the numerical project ID is correct:
```bash
gcloud projects describe <project-id> --format="value(projectNumber)"
```

### Issue 4: Secrets Not Loading Despite Being Present
**Solution**: Check that `LOAD_SECRETS=true` is set in the Cloud Run environment

## Testing Locally

To test the secret loading locally:
```bash
export ENVIRONMENT=staging
export GCP_PROJECT_ID_NUMERICAL_STAGING=<numerical-project-id>
export LOAD_SECRETS=true
export K_SERVICE=backend-staging-test
python scripts/test_staging_config.py
```

## Monitoring

Monitor secret loading in the application logs:
```python
# The SecretManager logs detailed information:
self._logger.info(f"Secret Manager initialized with project ID: {self._project_id}")
self._logger.info(f"Successfully loaded: {len(successful_secrets)} secrets")
```

## Key Files
- `app/core/secret_manager.py` - Secret loading logic
- `app/config.py` - Configuration management
- `terraform-gcp/main.tf` - Infrastructure definition
- `scripts/create_staging_secrets.py` - Secret creation helper