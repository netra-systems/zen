#!/bin/bash
# deploy-staging-complete.sh - Complete staging deployment with Docker builds
# This script handles the full staging deployment including Docker image builds with correct API URLs

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Staging environment banner
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  NETRA COMPLETE STAGING DEPLOYMENT SCRIPT     ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Default staging API URLs
STAGING_API_URL="https://api.staging.netrasystems.ai"
STAGING_WS_URL="wss://api.staging.netrasystems.ai/ws"

print_info "Default Staging API Configuration:"
print_info "  API URL: $STAGING_API_URL"
print_info "  WebSocket URL: $STAGING_WS_URL"
echo ""

# Force use of staging configuration
export TF_VAR_FILE="terraform.staging.tfvars"

# Check if staging tfvars exists
if [ ! -f "$TF_VAR_FILE" ]; then
    print_error "$TF_VAR_FILE not found!"
    exit 1
fi

# Load variables from terraform.staging.tfvars
source <(grep project_id $TF_VAR_FILE | sed 's/ //g')
source <(grep region $TF_VAR_FILE | sed 's/ //g')
source <(grep environment $TF_VAR_FILE | sed 's/ //g')

# Remove quotes from variables
project_id=$(echo $project_id | tr -d '"')
region=$(echo $region | tr -d '"')
environment=$(echo $environment | tr -d '"')

# Verify this is staging
if [[ "$environment" != "staging" ]]; then
    print_error "Environment is not set to 'staging' in $TF_VAR_FILE"
    exit 1
fi

print_info "Deploying to STAGING environment"
print_info "Project: $project_id"
print_info "Region: $region"
echo ""

# Step 1: Check prerequisites
print_status "Checking prerequisites..."

if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found"
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    print_error "Terraform not found"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    print_error "Docker not found"
    exit 1
fi

# Step 2: Set GCP project
print_status "Setting GCP project to: $project_id"
gcloud config set project $project_id

# Step 3: Configure Docker
print_status "Configuring Docker for Artifact Registry..."
gcloud auth configure-docker ${region}-docker.pkg.dev --quiet

# Step 4: Build and push backend image
print_status "Building backend Docker image..."
cd ..  # Move to project root
docker build -f Dockerfile.backend \
    -t ${region}-docker.pkg.dev/${project_id}/netra-containers/backend:latest .

print_status "Pushing backend image..."
docker push ${region}-docker.pkg.dev/${project_id}/netra-containers/backend:latest

# Step 5: Build and push frontend image with staging API URLs
print_status "Building frontend Docker image with staging API configuration..."
docker build -f Dockerfile.frontend.staging \
    --build-arg NEXT_PUBLIC_API_URL=${STAGING_API_URL} \
    --build-arg NEXT_PUBLIC_WS_URL=${STAGING_WS_URL} \
    -t ${region}-docker.pkg.dev/${project_id}/netra-containers/frontend:latest .

print_status "Pushing frontend image..."
docker push ${region}-docker.pkg.dev/${project_id}/netra-containers/frontend:latest

cd terraform-gcp  # Return to terraform directory

# Step 6: Initialize Terraform
print_status "Initializing Terraform..."
STAGING_STATE_BUCKET="${project_id}-terraform-state"

# Check if state bucket exists
if ! gsutil ls -b gs://$STAGING_STATE_BUCKET &> /dev/null; then
    print_status "Creating Terraform state bucket: $STAGING_STATE_BUCKET"
    gsutil mb -p $project_id -l $region gs://$STAGING_STATE_BUCKET
    gsutil versioning set on gs://$STAGING_STATE_BUCKET
fi

terraform init \
    -backend-config="bucket=$STAGING_STATE_BUCKET" \
    -backend-config="prefix=staging" \
    -reconfigure

# Step 7: Select workspace
print_status "Setting Terraform workspace to staging..."
terraform workspace select staging 2>/dev/null || terraform workspace new staging

# Step 8: Plan deployment
print_status "Planning staging deployment..."
terraform plan -var-file="$TF_VAR_FILE" -out=staging.tfplan

# Step 9: Apply deployment
print_status "Applying Terraform configuration..."
terraform apply staging.tfplan

# Step 10: Deploy services to Cloud Run
print_status "Deploying services to Cloud Run..."

# Get the registry URL from terraform output
REGISTRY=$(terraform output -raw artifact_registry 2>/dev/null || echo "${region}-docker.pkg.dev/${project_id}/netra-containers")

# Deploy backend
print_status "Deploying backend service..."
gcloud run deploy netra-backend \
    --image ${REGISTRY}/backend:latest \
    --region ${region} \
    --platform managed \
    --port 8080 \
    --quiet

# Deploy frontend
print_status "Deploying frontend service..."
gcloud run deploy netra-frontend \
    --image ${REGISTRY}/frontend:latest \
    --region ${region} \
    --platform managed \
    --port 3000 \
    --quiet

# Step 11: Get deployment URLs
print_status "Retrieving deployment information..."
echo ""
echo -e "${GREEN}=== STAGING Deployment Complete ===${NC}"
echo ""

BACKEND_URL=$(gcloud run services describe netra-backend --region=${region} --format='value(status.url)')
FRONTEND_URL=$(gcloud run services describe netra-frontend --region=${region} --format='value(status.url)')

echo -e "${BLUE}STAGING Environment URLs:${NC}"
echo -e "  Frontend: ${GREEN}$FRONTEND_URL${NC}"
echo -e "  Backend:  ${GREEN}$BACKEND_URL${NC}"
echo -e "  API Config: ${GREEN}$STAGING_API_URL${NC}"
echo ""

# Step 12: Verify deployment
print_status "Verifying deployment..."

# Check backend health
if curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health" | grep -q "200"; then
    print_status "✓ Backend is healthy"
else
    print_warning "Backend health check failed - service may still be starting"
fi

# Check frontend
if curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" | grep -q "200"; then
    print_status "✓ Frontend is accessible"
else
    print_warning "Frontend check failed - service may still be starting"
fi

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   STAGING DEPLOYMENT COMPLETED SUCCESSFULLY   ${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
print_info "Frontend configured to use: $STAGING_API_URL"
print_info "To destroy: terraform destroy -var-file=$TF_VAR_FILE"