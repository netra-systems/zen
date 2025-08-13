# Staging Environment Workflow Setup

## Required GitHub Secrets

Configure these secrets in your GitHub repository settings:

### Required Secrets
- `GCP_SA_KEY`: Service account JSON key with permissions for Terraform and GCS
- `GCP_PROJECT_ID`: Default GCP project ID (production)
- `GCP_STAGING_PROJECT_ID`: Staging-specific GCP project ID (optional, falls back to GCP_PROJECT_ID)

### Optional Secrets
- `TF_STATE_BUCKET`: Terraform state bucket name (default: 'netra-staging-terraform-state')
- `TF_STAGING_STATE_BUCKET`: Staging-specific state bucket (falls back to TF_STATE_BUCKET)

## GCP Permissions Required

The service account in `GCP_SA_KEY` needs:
- Storage Admin (for Terraform state bucket)
- Compute Admin (for infrastructure)
- Service Account User
- Container Admin (if using GKE)
- Cloud Run Admin (if using Cloud Run)

## Bucket Configuration

The workflow will:
1. Check if the configured bucket exists
2. Create it if missing (requires Storage Admin permission)
3. Use it for Terraform state storage

## Environment Variables

The workflow automatically sets:
- `GCP_PROJECT`: Uses GCP_STAGING_PROJECT_ID or GCP_PROJECT_ID
- `GOOGLE_CLOUD_PROJECT`: Same as above
- `CLOUDSDK_CORE_PROJECT`: Same as above

## Troubleshooting

### Bucket doesn't exist error
- Ensure GCP_STAGING_PROJECT_ID is set correctly
- Verify service account has Storage Admin permissions
- Check bucket name is valid (lowercase, no underscores)

### Permission denied errors
- Verify service account JSON is valid
- Check project ID matches the service account's project
- Ensure all required permissions are granted