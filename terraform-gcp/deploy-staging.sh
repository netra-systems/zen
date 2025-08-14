#!/bin/bash
# deploy-staging.sh - Automated deployment script for Netra STAGING environment
# This script ensures staging deployments use staging resources only

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
echo -e "${BLUE}     NETRA STAGING ENVIRONMENT DEPLOYMENT      ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Force use of staging configuration
export TF_VAR_FILE="terraform.staging.tfvars"

# Check if staging tfvars exists
if [ ! -f "$TF_VAR_FILE" ]; then
    print_error "$TF_VAR_FILE not found!"
    print_status "Please ensure terraform.staging.tfvars exists with staging configuration."
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
    print_error "Current environment: $environment"
    exit 1
fi

if [[ "$project_id" == *"production"* ]]; then
    print_error "Project ID contains 'production': $project_id"
    print_error "This appears to be a production project. Aborting staging deployment."
    exit 1
fi

print_info "Deploying to STAGING environment"
print_info "Project: $project_id"
print_info "Region: $region"
print_info "Environment: $environment"
echo ""

# Step 1: Check prerequisites
print_status "Checking prerequisites..."

if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    print_error "Terraform not found. Please install Terraform."
    exit 1
fi

# Step 2: Set the correct GCP project
print_status "Setting GCP project to staging: $project_id"
gcloud config set project $project_id

# Verify we're using the right project
CURRENT_PROJECT=$(gcloud config get-value project)
if [[ "$CURRENT_PROJECT" != "$project_id" ]]; then
    print_error "Failed to set project to $project_id"
    exit 1
fi

# Step 3: Check authentication
print_status "Checking GCP authentication..."
if ! gcloud auth application-default print-access-token &> /dev/null; then
    print_warning "Not authenticated. Running gcloud auth login..."
    gcloud auth application-default login
fi

# Step 4: Enable required APIs for staging
print_status "Enabling required APIs for staging project..."
APIS=(
    "cloudresourcemanager.googleapis.com"
    "compute.googleapis.com"
    "run.googleapis.com"
    "sqladmin.googleapis.com"
    "secretmanager.googleapis.com"
    "cloudbuild.googleapis.com"
    "artifactregistry.googleapis.com"
    "redis.googleapis.com"
    "dns.googleapis.com"
    "iam.googleapis.com"
    "iamcredentials.googleapis.com"
    "cloudkms.googleapis.com"
    "logging.googleapis.com"
    "monitoring.googleapis.com"
)

for api in "${APIS[@]}"; do
    print_status "  Enabling $api..."
    gcloud services enable $api --project=$project_id --quiet || true
done

# Step 5: Initialize Terraform with staging backend
print_status "Initializing Terraform for staging..."

# Use staging-specific state bucket
STAGING_STATE_BUCKET="${project_id}-terraform-state"

# Check if state bucket exists, create if not
if ! gsutil ls -b gs://$STAGING_STATE_BUCKET &> /dev/null; then
    print_status "Creating Terraform state bucket for staging: $STAGING_STATE_BUCKET"
    gsutil mb -p $project_id -l $region gs://$STAGING_STATE_BUCKET
    gsutil versioning set on gs://$STAGING_STATE_BUCKET
    gsutil lifecycle set /dev/stdin gs://$STAGING_STATE_BUCKET <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 30,
          "isLive": false
        }
      }
    ]
  }
}
EOF
fi

# Initialize with staging backend
terraform init \
    -backend-config="bucket=$STAGING_STATE_BUCKET" \
    -backend-config="prefix=staging" \
    -reconfigure

# Step 6: Create workspace for staging
print_status "Setting Terraform workspace to staging..."
terraform workspace select staging 2>/dev/null || terraform workspace new staging

# Step 7: Validate configuration
print_status "Validating Terraform configuration..."
terraform validate

# Step 8: Plan deployment with staging variables
print_status "Planning staging deployment..."
terraform plan -var-file="$TF_VAR_FILE" -out=staging.tfplan

# Step 9: Confirm deployment
echo ""
print_warning "About to deploy to STAGING environment: $project_id"
read -p "Do you want to proceed with the staging deployment? (yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    print_warning "Deployment cancelled."
    exit 0
fi

# Step 10: Apply Terraform configuration
print_status "Applying Terraform configuration for staging..."
terraform apply staging.tfplan

# Step 11: Get outputs
print_status "Retrieving deployment outputs..."
echo ""
echo -e "${GREEN}=== STAGING Deployment Complete ===${NC}"
echo ""

# Display staging URLs
BACKEND_URL=$(terraform output -raw backend_url 2>/dev/null || echo "Not available")
FRONTEND_URL=$(terraform output -raw frontend_url 2>/dev/null || echo "Not available")
DB_CONNECTION=$(terraform output -raw database_connection_name 2>/dev/null || echo "Not available")

echo -e "${BLUE}STAGING Environment URLs:${NC}"
echo -e "  Frontend: ${GREEN}$FRONTEND_URL${NC}"
echo -e "  Backend:  ${GREEN}$BACKEND_URL${NC}"
echo -e "  Database: ${GREEN}$DB_CONNECTION${NC}"
echo ""

# Step 12: Post-deployment verification
print_status "Running post-deployment checks..."

# Check if backend is responding
if [[ "$BACKEND_URL" != "Not available" ]]; then
    print_status "Checking backend health..."
    if curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health" | grep -q "200\|404"; then
        print_status "Backend is responding"
    else
        print_warning "Backend health check failed - this is normal if the service is still starting"
    fi
fi

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   STAGING DEPLOYMENT COMPLETED SUCCESSFULLY   ${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
print_info "Environment: STAGING"
print_info "Project: $project_id"
print_info "To destroy this staging deployment, run: terraform destroy -var-file=$TF_VAR_FILE"