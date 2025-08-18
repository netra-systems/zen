# CRITICAL: Cloud Run Service Naming Convention

## ⚠️ BREAKING CHANGE - Service Names Updated

### Summary
All Cloud Run services have been renamed to follow exact naming conventions required for domain mapping. **Using incorrect names will break domain routing.**

## Service Names (EXACT - NO VARIATIONS)

### Staging Environment

| Service | Old Name (WRONG) | New Name (CORRECT) | URL | Domain |
|---------|-----------------|-------------------|-----|--------|
| Backend | `netra-backend` | **`netra-backend-staging`** | https://netra-backend-staging-701982941522.us-central1.run.app | api.staging.netrasystems.ai |
| Frontend | `netra-frontend` | **`netra-frontend-staging`** | https://netra-frontend-staging-701982941522.us-central1.run.app | staging.netrasystems.ai |
| Auth | `netra-auth-service` | **`netra-auth-service`** | https://netra-auth-service-701982941522.us-central1.run.app | auth.staging.netrasystems.ai |

### Production Environment (Future)

| Service | Name | Domain |
|---------|------|--------|
| Backend | **`netra-backend-prod`** | api.netrasystems.ai |
| Frontend | **`netra-frontend-prod`** | netrasystems.ai |
| Auth | **`netra-auth-service`** | auth.netrasystems.ai |

## Files Updated

The following files have been updated with the correct service names:

1. **`deploy-staging-reliable.ps1`** - Main deployment script
2. **`terraform-gcp/main.tf`** - Terraform configuration
3. **`docs/deployment/GCP_STAGING_DEPLOYMENT.md`** - Deployment documentation
4. **`SPEC/cloud_run_service_naming.xml`** - Naming specification (NEW)

## Deployment Commands

### Deploy Backend (Staging)
```bash
gcloud run deploy netra-backend-staging \
  --image us-central1-docker.pkg.dev/netra-staging/netra-containers/backend:staging \
  --platform managed \
  --region us-central1 \
  --project netra-staging
```

### Deploy Frontend (Staging)
```bash
gcloud run deploy netra-frontend-staging \
  --image us-central1-docker.pkg.dev/netra-staging/netra-containers/frontend:staging \
  --platform managed \
  --region us-central1 \
  --project netra-staging
```

### Deploy Auth Service
```bash
gcloud run deploy netra-auth-service \
  --image us-central1-docker.pkg.dev/netra-staging/netra-containers/auth:staging \
  --platform managed \
  --region us-central1 \
  --project netra-staging
```

## Verification

Run this command to verify services are deployed with correct names:
```bash
gcloud run services list --platform managed --region us-central1 --project netra-staging
```

Expected output should show:
- `netra-backend-staging`
- `netra-frontend-staging`
- `netra-auth-service`

## Common Mistakes to Avoid

❌ **WRONG**: `gcloud run deploy netra-backend ...`  
✅ **CORRECT**: `gcloud run deploy netra-backend-staging ...`

❌ **WRONG**: `gcloud run deploy netra-frontend ...`  
✅ **CORRECT**: `gcloud run deploy netra-frontend-staging ...`

❌ **WRONG**: `gcloud run deploy netra-auth-staging ...`  
✅ **CORRECT**: `gcloud run deploy netra-auth-service ...`

## Impact on Other Systems

### GitHub Actions
- Update workflows to use correct service names
- Check `.github/workflows/*.yml` files

### Environment Variables
- Backend URL remains: `https://api.staging.netrasystems.ai`
- Frontend URL remains: `https://staging.netrasystems.ai`
- These map to the correctly named services via domain configuration

### Docker Images
- Image names in registry remain unchanged
- Only the Cloud Run service names change

## Database Connection Note

The backend service requires proper database configuration. Ensure the following environment variables or secrets are set:
- PostgreSQL connection URL
- Database credentials (via Secret Manager)

## Current Deployment Status (as of 2025-08-18)

✅ **Deployed with correct names:**
- `netra-backend-staging` - Deployed at 22:36:14 UTC
- `netra-frontend-staging` - Deployed at 22:36:31 UTC  
- `netra-auth-service` - Deployed at 22:32:32 UTC

## Next Steps

1. Configure domain mapping for the correctly named services
2. Set up database connection for backend service
3. Update any CI/CD pipelines to use correct service names
4. Test all services with their domain URLs

## Support

If you encounter issues with service naming or domain routing, check:
1. Service names match exactly as specified
2. Domain mapping configuration in GCP Console
3. DNS records point to correct Cloud Run services