# GCP Staging Deployment Commands

## Quick Deployment Steps

### 1. Authenticate with GCP
```bash
# Login to GCP
gcloud auth login

# Set application default credentials (for Terraform)
gcloud auth application-default login

# Set the project
gcloud config set project netra-staging
```

### 2. Enable Required APIs
```bash
# Enable all required APIs at once
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  compute.googleapis.com \
  artifactregistry.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  storage.googleapis.com \
  sqladmin.googleapis.com \
  --project=netra-staging
```

### 3. Option A: Deploy Using PowerShell Script (Recommended for Windows)
```powershell
# Run the complete deployment script
.\deploy-all-staging.ps1
```

### 3. Option B: Deploy Using Terraform (Infrastructure as Code)
```powershell
# Run the Terraform deployment script
.\deploy-staging-terraform.ps1
```

### 3. Option C: Manual Deployment Steps

#### Configure Docker
```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

#### Create Artifact Registry (if not exists)
```bash
gcloud artifacts repositories create netra-containers \
  --repository-format=docker \
  --location=us-central1 \
  --project=netra-staging
```

#### Build and Push Docker Images
```bash
# Backend
docker build -f Dockerfile.backend \
  -t us-central1-docker.pkg.dev/netra-staging/netra-containers/backend:staging .
docker push us-central1-docker.pkg.dev/netra-staging/netra-containers/backend:staging

# Frontend
docker build -f Dockerfile.frontend.staging \
  --build-arg NEXT_PUBLIC_API_URL=https://api.staging.netrasystems.ai \
  --build-arg NEXT_PUBLIC_WS_URL=wss://api.staging.netrasystems.ai/ws \
  -t us-central1-docker.pkg.dev/netra-staging/netra-containers/frontend:staging .
docker push us-central1-docker.pkg.dev/netra-staging/netra-containers/frontend:staging

# Auth Service
docker build -f Dockerfile.auth \
  -t us-central1-docker.pkg.dev/netra-staging/netra-containers/auth:staging .
docker push us-central1-docker.pkg.dev/netra-staging/netra-containers/auth:staging
```

#### Create Secrets
```bash
# JWT Secret
echo -n "your-secure-jwt-secret-here" | \
  gcloud secrets create jwt-secret --data-file=- --project=netra-staging

# Database URL
echo -n "postgresql://user:pass@host:5432/auth_db" | \
  gcloud secrets create auth-database-url --data-file=- --project=netra-staging

# Redis URL
echo -n "redis://redis-host:6379/0" | \
  gcloud secrets create redis-url --data-file=- --project=netra-staging
```

#### Deploy Services to Cloud Run
```bash
# Backend Service
gcloud run deploy netra-backend \
  --image us-central1-docker.pkg.dev/netra-staging/netra-containers/backend:staging \
  --platform managed \
  --region us-central1 \
  --project netra-staging \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 0.5 \
  --min-instances 0 \
  --max-instances 2 \
  --set-env-vars="ENVIRONMENT=staging,SERVICE_NAME=backend,LOG_LEVEL=INFO"

# Frontend Service
gcloud run deploy netra-frontend \
  --image us-central1-docker.pkg.dev/netra-staging/netra-containers/frontend:staging \
  --platform managed \
  --region us-central1 \
  --project netra-staging \
  --allow-unauthenticated \
  --port 3000 \
  --memory 512Mi \
  --cpu 0.25 \
  --min-instances 0 \
  --max-instances 2 \
  --set-env-vars="NODE_ENV=production,NEXT_PUBLIC_API_URL=https://api.staging.netrasystems.ai"

# Auth Service
gcloud run deploy netra-auth-service \
  --image us-central1-docker.pkg.dev/netra-staging/netra-containers/auth:staging \
  --platform managed \
  --region us-central1 \
  --project netra-staging \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --set-secrets="JWT_SECRET=jwt-secret:latest,DATABASE_URL=auth-database-url:latest" \
  --set-env-vars="ENVIRONMENT=staging,SERVICE_NAME=auth-service,LOG_LEVEL=INFO"
```

### 4. Verify Deployment

#### Get Service URLs
```bash
# List all Cloud Run services
gcloud run services list --platform=managed --region=us-central1 --project=netra-staging

# Get specific service URLs
gcloud run services describe netra-backend --platform=managed --region=us-central1 --project=netra-staging --format="value(status.url)"
gcloud run services describe netra-frontend --platform=managed --region=us-central1 --project=netra-staging --format="value(status.url)"
gcloud run services describe netra-auth-service --platform=managed --region=us-central1 --project=netra-staging --format="value(status.url)"
```

#### Test Services
```bash
# Test backend health
curl https://netra-backend-xxxxx.run.app/health

# Test frontend
curl https://netra-frontend-xxxxx.run.app

# Test auth service
curl https://netra-auth-service-xxxxx.run.app/health
```

### 5. Using Terraform (Alternative)

#### Initialize Terraform
```bash
cd terraform-gcp
terraform init \
  -backend-config="bucket=netra-staging-terraform-state" \
  -backend-config="prefix=staging" \
  -reconfigure

# Select staging workspace
terraform workspace select staging || terraform workspace new staging
```

#### Deploy with Terraform
```bash
# Set environment variables
export TF_VAR_project_id="netra-staging"
export TF_VAR_jwt_secret="your-secure-jwt-secret"
export TF_VAR_auth_database_url="postgresql://user:pass@host:5432/auth_db"

# Plan and apply
terraform plan -var-file="terraform.staging.tfvars" -out=staging.tfplan
terraform apply staging.tfplan

# Get outputs
terraform output
```

### 6. Cleanup (When Needed)

#### Destroy with Terraform
```bash
cd terraform-gcp
terraform destroy -var-file="terraform.staging.tfvars"
```

#### Manual Cleanup
```bash
# Delete Cloud Run services
gcloud run services delete netra-backend --region=us-central1 --project=netra-staging --quiet
gcloud run services delete netra-frontend --region=us-central1 --project=netra-staging --quiet
gcloud run services delete netra-auth-service --region=us-central1 --project=netra-staging --quiet

# Delete container images
gcloud artifacts docker images delete \
  us-central1-docker.pkg.dev/netra-staging/netra-containers/backend:staging --quiet
gcloud artifacts docker images delete \
  us-central1-docker.pkg.dev/netra-staging/netra-containers/frontend:staging --quiet
gcloud artifacts docker images delete \
  us-central1-docker.pkg.dev/netra-staging/netra-containers/auth:staging --quiet
```

## Troubleshooting

### Authentication Issues
```bash
# Re-authenticate
gcloud auth revoke --all
gcloud auth login
gcloud auth application-default login
```

### Docker Issues
```bash
# Re-configure Docker
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
```

### Service Account Permissions
```bash
# Grant necessary permissions to Cloud Run service account
PROJECT_NUMBER=$(gcloud projects describe netra-staging --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant Secret Manager access
gcloud secrets add-iam-policy-binding jwt-secret \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=netra-staging
```

## Summary

The deployment process creates:
1. **Backend Service** - FastAPI application at Cloud Run
2. **Frontend Service** - Next.js application at Cloud Run
3. **Auth Service** - Authentication service at Cloud Run
4. **Artifact Registry** - Container registry for Docker images
5. **Secret Manager** - Secure storage for sensitive data
6. **Terraform State** - Infrastructure state management

All services are configured to:
- Scale to zero when not in use (cost optimization)
- Use staging-specific configurations
- Have health check endpoints
- Support WebSocket connections (backend)
- Use proper CORS settings