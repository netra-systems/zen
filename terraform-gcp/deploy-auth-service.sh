#!/bin/bash
# deploy-auth-service.sh - Deploy Auth Service to GCP

set -e

echo "==================================="
echo "Deploying Netra Auth Service"
echo "==================================="

# Configuration
PROJECT_ID=${1:-"netra-project"}
REGION=${2:-"us-central1"}
ENVIRONMENT=${3:-"staging"}

echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed"
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

# Set project
echo "Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    compute.googleapis.com \
    certificatemanager.googleapis.com

# Build and push auth service image
echo "Building Auth Service Docker image..."
cd ..
docker build -f Dockerfile.auth -t auth-service:latest .

# Tag for Artifact Registry
echo "Tagging image for Artifact Registry..."
docker tag auth-service:latest \
    ${REGION}-docker.pkg.dev/${PROJECT_ID}/netra-containers/auth-service:latest

# Configure docker for Artifact Registry
echo "Configuring Docker for Artifact Registry..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Push image
echo "Pushing image to Artifact Registry..."
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/netra-containers/auth-service:latest

# Deploy with Terraform
echo "Deploying infrastructure with Terraform..."
cd terraform-gcp

# Initialize Terraform
terraform init \
    -backend-config="bucket=netra-terraform-state-${PROJECT_ID}" \
    -backend-config="prefix=terraform/state/${ENVIRONMENT}"

# Create/update infrastructure
terraform apply \
    -var="project_id=${PROJECT_ID}" \
    -var="region=${REGION}" \
    -var="environment=${ENVIRONMENT}" \
    -target=google_cloud_run_service.auth \
    -target=google_service_account.auth_service \
    -target=google_project_iam_member.auth_service_sql \
    -target=google_project_iam_member.auth_service_secrets \
    -target=google_project_iam_member.auth_service_logging \
    -target=google_cloud_run_service_iam_member.auth_public \
    -target=google_secret_manager_secret.session_secret \
    -target=google_secret_manager_secret_version.session_secret \
    -auto-approve

# Deploy Load Balancer components
echo "Deploying Load Balancer for Auth Service..."
terraform apply \
    -var="project_id=${PROJECT_ID}" \
    -var="region=${REGION}" \
    -var="environment=${ENVIRONMENT}" \
    -target=google_compute_region_network_endpoint_group.auth_neg \
    -target=google_compute_backend_service.auth \
    -target=google_compute_url_map.auth \
    -target=google_compute_managed_ssl_certificate.auth \
    -target=google_compute_target_https_proxy.auth \
    -target=google_compute_global_address.auth \
    -target=google_compute_global_forwarding_rule.auth \
    -target=google_compute_url_map.auth_http_redirect \
    -target=google_compute_target_http_proxy.auth_http \
    -target=google_compute_global_forwarding_rule.auth_http \
    -auto-approve

# Get outputs
echo "==================================="
echo "Deployment Complete!"
echo "==================================="
terraform output -json > auth-deployment-info.json

# Display URLs
AUTH_SERVICE_URL=$(terraform output -raw auth_service_url)
AUTH_SERVICE_DOMAIN=$(terraform output -raw auth_service_domain)
AUTH_SERVICE_IP=$(terraform output -raw auth_service_ip)

echo "Auth Service URL: $AUTH_SERVICE_URL"
echo "Auth Service Domain: $AUTH_SERVICE_DOMAIN"
echo "Auth Service IP: $AUTH_SERVICE_IP"
echo ""
echo "Next steps:"
echo "1. Update DNS records to point $AUTH_SERVICE_DOMAIN to $AUTH_SERVICE_IP"
echo "2. Update OAuth redirect URIs in Google Cloud Console:"
echo "   - https://$AUTH_SERVICE_DOMAIN/api/auth/callback"
echo "   - $AUTH_SERVICE_URL/api/auth/callback"
echo "3. Update frontend configuration to use the auth service"
echo "4. Test OAuth flow at https://$AUTH_SERVICE_DOMAIN/api/auth/login"