# Netra Staging Deployment Guide

## Overview
This guide provides clear instructions for deploying Netra Apex to the GCP staging environment.

## Staging Environment Details
- **Project ID**: `netra-staging`
- **Region**: `us-central1`
- **Frontend URL**: https://netra-frontend-701982941522.us-central1.run.app/
- **Backend URL**: https://netra-backend-701982941522.us-central1.run.app/

## Prerequisites
1. GCP CLI (`gcloud`) installed and configured
2. Docker installed and running
3. Terraform installed (v1.0+)
4. Access to the `netra-staging` GCP project

## Quick Deployment Steps

### 1. Authenticate with GCP
```bash
# Login to GCP
gcloud auth login

# Set application default credentials
gcloud auth application-default login

# Set project to staging
gcloud config set project netra-staging
```

### 2. Build and Push Docker Images
```bash
# Configure Docker for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

# Build backend image
docker build -t us-central1-docker.pkg.dev/netra-staging/netra-containers/backend:latest -f Dockerfile.backend .

# Push backend image
docker push us-central1-docker.pkg.dev/netra-staging/netra-containers/backend:latest

# Build frontend image (using staging-optimized Dockerfile)
docker build -t us-central1-docker.pkg.dev/netra-staging/netra-containers/frontend:latest -f Dockerfile.frontend.staging .

# Push frontend image
docker push us-central1-docker.pkg.dev/netra-staging/netra-containers/frontend:latest
```

### 3. Deploy Infrastructure with Terraform
```bash
cd terraform-gcp

# Initialize Terraform with GCS backend
terraform init \
  -backend-config="bucket=netra-staging-terraform-state" \
  -backend-config="prefix=staging" \
  -reconfigure

# Select staging workspace
terraform workspace select staging || terraform workspace new staging

# Plan deployment with staging variables
terraform plan -var-file="terraform.staging.tfvars" -out=staging.tfplan

# Apply deployment
terraform apply staging.tfplan
```

### 4. Deploy Services to Cloud Run
```bash
# Deploy backend service
gcloud run deploy netra-backend \
  --image us-central1-docker.pkg.dev/netra-staging/netra-containers/backend:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --quiet

# Deploy frontend service
gcloud run deploy netra-frontend \
  --image us-central1-docker.pkg.dev/netra-staging/netra-containers/frontend:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --quiet
```

## Automated Deployment Script
For convenience, use the provided deployment script:
```bash
cd terraform-gcp
./deploy-staging.sh
```

## Staging Configuration
The staging environment uses resource-optimized settings defined in `terraform.staging.tfvars`:
- **Database**: `db-f1-micro` (smallest tier)
- **Backend**: 0.5 vCPU, 1GB RAM, scales to zero
- **Frontend**: 0.25 vCPU, 512MB RAM, scales to zero

## Troubleshooting

### IAM Policy Errors
If you encounter IAM policy errors when deploying:
```bash
# For backend
gcloud beta run services add-iam-policy-binding \
  --region=us-central1 \
  --member=allUsers \
  --role=roles/run.invoker \
  netra-backend

# For frontend
gcloud beta run services add-iam-policy-binding \
  --region=us-central1 \
  --member=allUsers \
  --role=roles/run.invoker \
  netra-frontend
```

### Cloud Armor Issues
The `cloud-armor-ip-blocking.tf` file may cause issues if not properly configured. It's currently disabled for staging deployments. To re-enable:
1. Rename `cloud-armor-ip-blocking.tf.disabled` back to `cloud-armor-ip-blocking.tf`
2. Update the service reference from `google_cloud_run_service.app` to `google_cloud_run_service.backend`

### State Bucket Creation
The deployment script automatically creates the state bucket if it doesn't exist. Manual creation:
```bash
gsutil mb -p netra-staging -l us-central1 gs://netra-staging-terraform-state
gsutil versioning set on gs://netra-staging-terraform-state
```

## Verification
After deployment, verify the services:
```bash
# Check frontend
curl -I https://netra-frontend-701982941522.us-central1.run.app/

# Check backend (may return 403 due to IAM restrictions)
curl -I https://netra-backend-701982941522.us-central1.run.app/health
```

## Teardown
To destroy the staging environment:
```bash
cd terraform-gcp
terraform destroy -var-file="terraform.staging.tfvars"
```

## Important Notes
- The staging environment is configured to minimize costs with auto-scaling to zero
- Services may take a few seconds to cold-start after being idle
- Always use `terraform.staging.tfvars` for staging deployments
- Never use production credentials or resources in staging