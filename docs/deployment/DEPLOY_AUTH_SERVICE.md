# Auth Service Deployment Instructions

The auth service has been fully prepared for deployment. Follow these steps to deploy to GCP:

## Prerequisites

1. Authenticate with GCP:
```bash
gcloud auth login
gcloud config set project netra-staging
```

2. Enable required APIs:
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

## Step 1: Create Secrets in Secret Manager

```bash
# Create JWT secret
echo -n "your-secure-jwt-secret-here" | gcloud secrets create jwt-secret --data-file=-

# Create database URL secret
echo -n "postgresql://user:pass@host:5432/auth_db" | gcloud secrets create auth-database-url --data-file=-

# Create Redis URL secret  
echo -n "redis://redis-host:6379/0" | gcloud secrets create redis-url --data-file=-
```

## Step 2: Deploy Using Docker Image (Recommended)

The Docker image has been built locally. Push it to GCR and deploy:

```bash
# Push the Docker image
docker push gcr.io/netra-staging/auth-service:latest
docker push gcr.io/netra-staging/auth-service:staging

# Deploy to Cloud Run
gcloud run deploy netra-auth-service \
  --image gcr.io/netra-staging/auth-service:latest \
  --platform managed \
  --region us-central1 \
  --project netra-staging \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 10 \
  --set-secrets="JWT_SECRET=jwt-secret:latest,DATABASE_URL=auth-database-url:latest,REDIS_URL=redis-url:latest" \
  --set-env-vars="ENVIRONMENT=staging,SERVICE_NAME=auth-service,LOG_LEVEL=INFO" \
  --update-env-vars="CORS_ORIGINS=https://staging.netrasystems.ai"
```

## Step 3: Alternative - Deploy from Source

If you can't push the Docker image, deploy directly from source:

```bash
# Create a .gcloudignore file
cat > .gcloudignore << EOF
.git
.venv
venv
__pycache__
*.pyc
.env
.env.*
frontend/
scripts/
tests/
docs/
terraform-gcp/
EOF

# Deploy from source
gcloud run deploy netra-auth-service \
  --source auth_service \
  --project netra-staging \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 10 \
  --env-vars-file auth-service-env.yaml
```

## Step 4: Using Terraform (Infrastructure as Code)

```bash
cd terraform-gcp

# Initialize Terraform
terraform init

# Set variables
export TF_VAR_project_id="netra-staging"
export TF_VAR_jwt_secret="your-secure-jwt-secret"
export TF_VAR_DATABASE_URL="postgresql://user:pass@host:5432/auth_db"
export TF_VAR_redis_url="redis://redis-host:6379/0"

# Apply the auth service configuration
terraform apply -target=module.auth_service
```

## Step 5: Verify Deployment

Once deployed, get the service URL:

```bash
gcloud run services describe netra-auth-service \
  --platform managed \
  --region us-central1 \
  --project netra-staging \
  --format 'value(status.url)'
```

Test the service:

```bash
# Check health
curl https://netra-auth-service-xxxxx.run.app/health

# Check API docs
curl https://netra-auth-service-xxxxx.run.app/docs
```

## Step 6: Update Backend and Frontend

1. Update backend environment:
```bash
# Add to backend .env
AUTH_SERVICE_URL=https://netra-auth-service-xxxxx.run.app
AUTH_SERVICE_ENABLED=true
```

2. Update frontend environment:
```bash
# Add to frontend .env
NEXT_PUBLIC_AUTH_SERVICE_URL=https://netra-auth-service-xxxxx.run.app
```

## Step 7: Using GitHub Actions (CI/CD)

The GitHub Actions workflow is configured at `.github/workflows/deploy-auth-service.yml`

To trigger deployment:
1. Push to `main` branch for production deployment
2. Push to `staging` branch for staging deployment
3. Or manually trigger the workflow from GitHub Actions tab

## Troubleshooting

### Authentication Issues
```bash
# Re-authenticate
gcloud auth login
gcloud auth configure-docker
```

### Build Issues
```bash
# Build locally first
docker build -f Dockerfile.auth -t test-auth .
docker run -p 8081:8080 test-auth
```

### Secret Access Issues
```bash
# Grant service account access to secrets
SERVICE_ACCOUNT="auth-service-sa@netra-staging.iam.gserviceaccount.com"

gcloud secrets add-iam-policy-binding jwt-secret \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

## Files Created

- `Dockerfile.auth` - Optimized Docker configuration
- `docker-compose.auth.yml` - Local development setup
- `auth-service-env.yaml` - Environment variables for deployment
- `terraform-gcp/auth_service.tf` - Terraform configuration
- `.github/workflows/deploy-auth-service.yml` - CI/CD pipeline
- `scripts/start_auth_service.py` - Local development script
- `scripts/test_auth_integration.py` - Integration tests

## Next Steps

1. Set up proper secrets in GCP Secret Manager
2. Configure Redis instance (Cloud Memorystore or Redis Labs)
3. Set up Cloud SQL for PostgreSQL if needed
4. Configure monitoring and alerting
5. Set up custom domain if needed

The auth service is fully prepared and ready for deployment!