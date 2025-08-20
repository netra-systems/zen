# Developer Deployment Guide

## 🚨 IMPORTANT: Local vs Staging vs Production

| Environment | Command | Where It Runs | URL |
|------------|---------|---------------|-----|
| **Local Dev** | `python scripts/dev_launcher.py` | Your machine | `http://localhost:8000` |
| **GCP Staging** | `python deploy_staging_automated.py` | Google Cloud | `https://netra-*.run.app` |
| **Production** | Via GitHub Actions only | Google Cloud | `https://api.netrasystems.ai` |

## 🚀 Quick Commands

### Local Development
```bash
# Start local dev environment
python scripts/dev_launcher.py

# Run tests locally
python test_runner.py --level integration --no-coverage --fast-fail
```

### Deploy to GCP Staging (REAL CLOUD)
```bash
# One-time setup (first deployment only)
python setup_gcp_staging_resources.py

# Deploy to GCP staging environment
python deploy_staging_automated.py

# Fast deploy (skip health checks)
python deploy_staging_automated.py -SkipHealthChecks

# Pre-create all required resources
python deploy_staging_automated.py -PreCreateResources

# Deploy with custom service account key
python deploy_staging_automated.py -ServiceAccountKeyPath "./path/to/key.json"
```

## 📋 Prerequisites

### For Local Development
- Python 3.11+
- Node.js 18+
- PostgreSQL (or Docker)
- `.env` file with API keys

### For GCP Staging Deployment
- GCP CLI (`gcloud`) installed
- Docker Desktop running
- Service account key file
- Access to `netra-staging` GCP project
- PowerShell 5.1+ (Windows) or pwsh (Linux/Mac)

## 🔑 Service Account Setup

### Option 1: Use Existing Key
If you received a `gcp-staging-sa-key.json` file:
```bash
# Place it in project root
cp /path/to/gcp-staging-sa-key.json ./

# Set environment variable
$env:GCP_STAGING_SA_KEY_PATH = ".\gcp-staging-sa-key.json"
```

### Option 2: Generate New Key
```bash
# Run setup script - it will prompt to generate a key
python setup_gcp_staging_resources.py

# Or manually create one
gcloud iam service-accounts keys create gcp-staging-sa-key.json \
  --iam-account=netra-staging-deploy@netra-staging.iam.gserviceaccount.com
```

### ⚠️ SECURITY WARNING
```
NEVER COMMIT SERVICE ACCOUNT KEYS TO GIT!
Add to .gitignore: gcp-staging-sa-key.json
```

## 📦 Deployment Process

### What Happens When You Deploy to Staging

1. **Authentication**: Uses service account to authenticate with GCP
2. **API Enablement**: Automatically enables required GCP APIs
3. **Resource Creation**: Pre-creates Artifact Registry and secrets if needed
4. **Docker Configuration**: Configures Docker for GCP Artifact Registry
5. **Build**: Creates Docker images locally with staging-specific configurations
6. **Push**: Uploads images to GCP Artifact Registry with versioning
7. **Deploy**: Creates/updates Cloud Run services with auto-scaling
8. **Health Check**: Verifies services are running (optional)
9. **Output**: Shows public URLs for services

### Deployment Output Example
```
================================================
   STAGING DEPLOYMENT COMPLETED SUCCESSFULLY   
================================================

Service URLs:
  Frontend: https://netra-frontend-xxxxx-uc.a.run.app
  Backend:  https://netra-backend-xxxxx-uc.a.run.app
  Auth:     https://netra-auth-service-xxxxx-uc.a.run.app
```

## 🌟 New Staging Features

### Auto-Scaling Configuration
All services are deployed with intelligent auto-scaling:
- **Min Instances**: 0 (scales to zero when idle)
- **Max Instances**: 10 (handles traffic spikes)
- **Memory**: 1Gi per instance
- **CPU**: 1 vCPU per instance

### Environment-Specific Builds
The deployment script automatically detects and uses environment-specific Dockerfiles:
- `Dockerfile.frontend.staging` - Staging-specific frontend build
- `Dockerfile.backend` - Standard backend build
- `Dockerfile.auth` - Auth service build (if exists)

### Automatic Resource Management
- **Artifact Registry**: Automatically created if missing
- **Secrets**: JWT secrets and database URLs created if needed
- **Service Accounts**: Automatic permission grants
- **API Enablement**: All required APIs enabled automatically

### Versioning Strategy
Each deployment creates two tags:
- `:latest` - Always points to newest staging build
- `:staging` - Specific staging environment tag

### Service Discovery
Deployed services use predictable URLs:
- Backend: `https://netra-backend-xxxxx-uc.a.run.app`
- Frontend: `https://netra-frontend-xxxxx-uc.a.run.app`
- Auth: `https://netra-auth-service-xxxxx-uc.a.run.app`

## 🔍 Verify Deployment

### Check Service Status
```bash
# List all deployed services
gcloud run services list --platform managed --region us-central1

# Check specific service
gcloud run services describe netra-backend --platform managed --region us-central1
```

### Test Endpoints
```bash
# Test backend health
curl https://netra-backend-xxxxx-uc.a.run.app/health

# Test frontend
curl https://netra-frontend-xxxxx-uc.a.run.app/

# Check logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=netra-backend" --limit 50
```

## 🐛 Troubleshooting

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| **"Docker daemon not running"** | Start Docker Desktop |
| **"Authentication failed"** | Check service account key path and permissions |
| **"Artifact Registry not found"** | Use `-PreCreateResources` flag to auto-create |
| **"Health check failed"** | Use `--skip-health-checks` for faster deployment |
| **"Permission denied"** | Ensure you have access to `netra-staging` project |
| **"Service account key not found"** | Set `$env:GCP_STAGING_SA_KEY_PATH` or use `-ServiceAccountKeyPath` |
| **"APIs not enabled"** | Script auto-enables APIs, wait for propagation |
| **"Out of memory during build"** | Increase Docker Desktop memory allocation |

### Debug Commands
```bash
# Check your current GCP account
gcloud config get-value account

# Check current project
gcloud config get-value project

# List your roles in the project
gcloud projects get-iam-policy netra-staging --flatten="bindings[].members" --format="table(bindings.role)" --filter="bindings.members:YOUR_EMAIL"

# View recent errors
gcloud logging read "severity>=ERROR" --limit 20 --project netra-staging
```

## 🔄 Rollback

### Quick Rollback to Previous Version
```bash
# List all revisions
gcloud run revisions list --service=netra-backend --platform managed --region us-central1

# Rollback to specific revision
gcloud run services update-traffic netra-backend \
  --to-revisions=netra-backend-00001-abc=100 \
  --platform managed --region us-central1
```

### Emergency Shutdown
```bash
# Delete services (use with caution!)
gcloud run services delete netra-backend --platform managed --region us-central1 --quiet
gcloud run services delete netra-frontend --platform managed --region us-central1 --quiet
```

## 📊 Monitoring

### View Metrics
1. Go to [Cloud Console](https://console.cloud.google.com)
2. Navigate to Cloud Run
3. Select your service
4. View Metrics, Logs, and Revisions tabs

### Cost Monitoring
```bash
# Check current month's cost
gcloud billing accounts list
gcloud alpha billing accounts budgets list --billing-account=YOUR_BILLING_ACCOUNT_ID
```

## 🚀 CI/CD Pipeline

### Automatic Deployment
Pushing to these branches triggers automatic deployment:
- `main` → Staging
- `staging` → Staging
- `production` → Production (requires approval)

### Manual Deployment via GitHub
1. Go to GitHub Actions tab
2. Select "Deploy to GCP Staging"
3. Click "Run workflow"
4. Select branch and options

## 📚 Additional Resources

- [GCP Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Docker Documentation](https://docs.docker.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- Full deployment details: `docs/GCP_STAGING_DEPLOYMENT.md`

## 🆘 Need Help?

1. Check this guide first
2. Review error messages in logs
3. Ask in #dev-deployment Slack channel
4. Contact DevOps team for GCP access issues

## ⚡ Quick Reference Card

```bash
# LOCAL DEV (your machine)
python scripts/dev_launcher.py         # Start local dev
python test_runner.py --level smoke    # Quick test

# GCP STAGING (real cloud)
python deploy_staging_automated.py         # Deploy to staging
python deploy_staging_automated.py -SkipHealthChecks  # Fast deploy
python deploy_staging_automated.py -PreCreateResources  # With resource creation
$env:GCP_STAGING_SA_KEY_PATH="./key.json"; python deploy_staging_automated.py  # Custom key

# DEBUGGING
gcloud run services list               # List services
gcloud logging read --limit 50         # View logs

# ROLLBACK
gcloud run services update-traffic SERVICE --to-revisions=OLD_REVISION=100
```

---
**Remember**: 
- `dev_launcher.py` = LOCAL (localhost)
- `deploy-staging-automated.ps1` = CLOUD (GCP)
- Never commit service account keys!
- Always test locally before deploying to staging