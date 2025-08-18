# GCP Staging Deployment Guide

## Overview
This guide covers the complete setup and deployment process for Netra Apex to GCP Staging environment.

## Prerequisites

### 1. GCP Project Setup
- Project ID: `netra-staging`
- Region: `us-central1`
- Ensure you have Owner or Editor role on the project

### 2. Service Account Setup
The staging deployment uses a dedicated service account for CI/CD operations.

#### Create Service Account (if not exists)
```bash
# Run the setup script to create service account and resources
.\setup-gcp-staging-resources.ps1
```

#### Store Service Account Key
1. Generate a service account key (if needed):
   ```bash
   gcloud iam service-accounts keys create gcp-staging-sa-key.json \
     --iam-account=netra-staging-deploy@netra-staging.iam.gserviceaccount.com
   ```

2. Store the key securely:
   - For local development: Save as `gcp-staging-sa-key.json` in project root
   - For CI/CD: Add to GitHub Secrets as `GCP_STAGING_SA_KEY`
   - Add to `.gitignore`: `gcp-staging-sa-key.json`

### 3. Required Permissions
The service account needs these roles:
- `roles/run.admin` - Deploy to Cloud Run
- `roles/artifactregistry.admin` - Manage container images
- `roles/secretmanager.admin` - Manage secrets
- `roles/iam.serviceAccountUser` - Use service accounts
- `roles/cloudbuild.builds.editor` - Cloud Build operations
- `roles/storage.admin` - Storage bucket access

## Deployment Methods

### Method 1: Automated PowerShell Script (Recommended)

#### Basic Deployment
```powershell
# Using environment variable
$env:GCP_STAGING_SA_KEY_PATH = ".\gcp-staging-sa-key.json"
.\deploy-staging-automated.ps1

# Or specify directly
.\deploy-staging-automated.ps1 -ServiceAccountKeyPath ".\gcp-staging-sa-key.json"
```

#### Advanced Options
```powershell
# Pre-create all resources before deployment
.\deploy-staging-automated.ps1 -PreCreateResources

# Skip health checks (faster deployment)
.\deploy-staging-automated.ps1 -SkipHealthChecks

# Full deployment with all options
.\deploy-staging-automated.ps1 `
  -ServiceAccountKeyPath ".\gcp-staging-sa-key.json" `
  -PreCreateResources `
  -SkipHealthChecks
```

### Method 2: GitHub Actions (CI/CD)

The deployment automatically triggers on:
- Push to `staging` branch
- Push to `main` branch  
- Manual workflow dispatch

#### Manual Trigger
1. Go to GitHub Actions tab
2. Select "Deploy to GCP Staging" workflow
3. Click "Run workflow"
4. Choose options:
   - Branch to deploy
   - Skip tests (optional)

#### Required GitHub Secrets
Add these secrets to your repository:
- `GCP_STAGING_SA_KEY` - Service account JSON key
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `GEMINI_API_KEY` - Google Gemini API key

### Method 3: Manual Deployment

#### Step 1: Authenticate
```bash
# Using service account
gcloud auth activate-service-account --key-file=gcp-staging-sa-key.json

# Or using user account
gcloud auth login
```

#### Step 2: Set Project
```bash
gcloud config set project netra-staging
```

#### Step 3: Build and Push Images
```bash
# Configure Docker
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build images
docker build -f Dockerfile.backend -t us-central1-docker.pkg.dev/netra-staging/netra-containers/backend:staging .
docker build -f Dockerfile.frontend -t us-central1-docker.pkg.dev/netra-staging/netra-containers/frontend:staging .

# Push images
docker push us-central1-docker.pkg.dev/netra-staging/netra-containers/backend:staging
docker push us-central1-docker.pkg.dev/netra-staging/netra-containers/frontend:staging
```

#### Step 4: Deploy to Cloud Run
```bash
# Deploy backend
gcloud run deploy netra-backend \
  --image us-central1-docker.pkg.dev/netra-staging/netra-containers/backend:staging \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

# Deploy frontend  
gcloud run deploy netra-frontend \
  --image us-central1-docker.pkg.dev/netra-staging/netra-containers/frontend:staging \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## Resource Pre-Creation

Run this before first deployment to ensure all resources exist:

```powershell
.\setup-gcp-staging-resources.ps1
```

This script will:
1. Enable required GCP APIs
2. Create service account with proper permissions
3. Create Artifact Registry for container images
4. Create secrets in Secret Manager
5. Create Cloud Storage bucket for backups
6. Generate service account key (optional)

## Health Checks

All services implement comprehensive health check endpoints:

### Backend Health Endpoints
- `/health` - Basic health check
- `/health/live` - Kubernetes liveness probe
- `/health/ready` - Kubernetes readiness probe  
- `/health/detailed` - Detailed health with metrics
- `/health/metrics` - Prometheus-compatible metrics

### Frontend Health Check
- `/` - Basic accessibility check
- `/api/health` - API connectivity check

### Auth Service Health
- `/health` - Basic health check
- `/health/ready` - Readiness with database check

### Automated Health Verification
The deployment scripts automatically verify health after deployment:
```powershell
# Check manually
curl https://your-backend-url/health
curl https://your-frontend-url/
curl https://your-auth-url/health
```

## Secrets Management

### Required Secrets
Create these secrets in GCP Secret Manager:
```bash
# JWT Secret
echo "your-jwt-secret" | gcloud secrets create jwt-secret --data-file=-

# Database URL
echo "postgresql://user:pass@host:5432/db" | gcloud secrets create auth-database-url --data-file=-

# API Keys
echo "sk-..." | gcloud secrets create openai-api-key --data-file=-
echo "sk-ant-..." | gcloud secrets create anthropic-api-key --data-file=-
echo "..." | gcloud secrets create gemini-api-key --data-file=-
```

### Update Existing Secrets
```bash
echo "new-value" | gcloud secrets versions add secret-name --data-file=-
```

## Monitoring & Troubleshooting

### View Logs
```bash
# Backend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=netra-backend" --limit 50

# Frontend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=netra-frontend" --limit 50
```

### Check Service Status
```bash
# List services
gcloud run services list --platform managed --region us-central1

# Describe service
gcloud run services describe netra-backend --platform managed --region us-central1
```

### Common Issues

#### 1. Authentication Failed
- Ensure service account key is valid
- Check if APIs are enabled
- Verify service account permissions

#### 2. Build Failed
- Check Docker is installed and running
- Verify Dockerfiles exist
- Check for syntax errors in Dockerfiles

#### 3. Deployment Failed
- Check if Artifact Registry exists
- Verify images were pushed successfully
- Check Cloud Run quotas

#### 4. Health Check Failed
- Wait 2-3 minutes for services to start
- Check service logs for errors
- Verify environment variables are set

## Rollback

### Quick Rollback
```bash
# List revisions
gcloud run revisions list --service=netra-backend --platform managed --region us-central1

# Rollback to previous revision
gcloud run services update-traffic netra-backend \
  --to-revisions=netra-backend-00001-abc=100 \
  --platform managed --region us-central1
```

### Full Cleanup
```bash
# Delete services
gcloud run services delete netra-backend --platform managed --region us-central1 --quiet
gcloud run services delete netra-frontend --platform managed --region us-central1 --quiet
gcloud run services delete netra-auth-service --platform managed --region us-central1 --quiet

# Delete images (optional)
gcloud artifacts docker images delete us-central1-docker.pkg.dev/netra-staging/netra-containers/backend --quiet
gcloud artifacts docker images delete us-central1-docker.pkg.dev/netra-staging/netra-containers/frontend --quiet
```

## Environment Variables

### Backend
- `ENVIRONMENT=staging`
- `SERVICE_NAME=backend`
- `LOG_LEVEL=INFO`
- `DATABASE_URL` (from secret)
- `OPENAI_API_KEY` (from secret)
- `ANTHROPIC_API_KEY` (from secret)

### Frontend
- `NODE_ENV=production`
- `NEXT_PUBLIC_API_URL=https://api.staging.netrasystems.ai`
- `NEXT_PUBLIC_WS_URL=wss://api.staging.netrasystems.ai/ws`

### Auth Service
- `ENVIRONMENT=staging`
- `SERVICE_NAME=auth-service`
- `JWT_SECRET` (from secret)
- `DATABASE_URL` (from secret)
- `CORS_ORIGINS=https://staging.netrasystems.ai`

## Security Best Practices

1. **Never commit service account keys**
   - Add to `.gitignore`
   - Use environment variables
   - Store in secure secret management

2. **Rotate keys regularly**
   ```bash
   gcloud iam service-accounts keys list \
     --iam-account=netra-staging-deploy@netra-staging.iam.gserviceaccount.com
   ```

3. **Use least privilege**
   - Only grant necessary permissions
   - Use separate service accounts for different environments

4. **Enable audit logging**
   ```bash
   gcloud logging read "protoPayload.authenticationInfo.principalEmail=\"netra-staging-deploy@netra-staging.iam.gserviceaccount.com\""
   ```

## Performance Optimization

1. **Container Image Size**
   - Use multi-stage builds
   - Minimize layers
   - Use slim base images

2. **Cloud Run Configuration**
   - Adjust memory and CPU based on usage
   - Configure min/max instances appropriately
   - Use concurrency settings

3. **Caching**
   - Enable CDN for static assets
   - Use Cloud CDN for frontend
   - Implement application-level caching

## Cost Management

1. **Monitor Usage**
   ```bash
   gcloud billing accounts list
   gcloud billing projects describe netra-staging
   ```

2. **Set Budgets**
   - Configure billing alerts
   - Set spending limits
   - Review costs regularly

3. **Optimize Resources**
   - Scale down during off-hours
   - Use minimum instances = 0 for dev/staging
   - Clean up unused resources

## Support

For issues or questions:
1. Check deployment logs in GitHub Actions
2. Review Cloud Run logs in GCP Console
3. Verify all prerequisites are met
4. Contact the DevOps team