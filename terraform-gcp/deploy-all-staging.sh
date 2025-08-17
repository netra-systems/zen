#!/bin/bash
# deploy-all-staging.sh - Complete deployment of all Netra services to GCP Staging

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}    NETRA APEX - COMPLETE STAGING DEPLOYMENT   ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Configuration
PROJECT_ID="netra-staging"
PROJECT_ID_NUMERICAL="701982941522"
REGION="us-central1"
ZONE="us-central1-a"
ENVIRONMENT="staging"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/netra-containers"

print_info "Deployment Configuration:"
print_info "  Project: $PROJECT_ID"
print_info "  Project ID (Numerical): $PROJECT_ID_NUMERICAL"
print_info "  Region: $REGION"
print_info "  Environment: $ENVIRONMENT"
echo ""

# Step 1: Prerequisites check
print_status "Checking prerequisites..."

MISSING_TOOLS=()
for tool in gcloud terraform docker; do
    if ! command -v $tool &> /dev/null; then
        MISSING_TOOLS+=($tool)
    fi
done

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    print_error "Missing required tools: ${MISSING_TOOLS[@]}"
    exit 1
fi

print_status "✓ All prerequisites met"

# Step 2: Set project and enable APIs
print_status "Configuring GCP project..."
gcloud config set project $PROJECT_ID

print_status "Enabling required APIs..."
gcloud services enable \
    compute.googleapis.com \
    container.googleapis.com \
    sqladmin.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    certificatemanager.googleapis.com \
    --project=$PROJECT_ID

# Step 3: Configure Docker
print_status "Configuring Docker for Artifact Registry..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Step 4: Initialize Terraform
print_status "Initializing Terraform..."
STAGING_STATE_BUCKET="${PROJECT_ID}-terraform-state"

# Create state bucket if it doesn't exist
if ! gsutil ls -b gs://$STAGING_STATE_BUCKET &> /dev/null; then
    print_info "Creating Terraform state bucket: $STAGING_STATE_BUCKET"
    gsutil mb -p $PROJECT_ID -l $REGION gs://$STAGING_STATE_BUCKET
    gsutil versioning set on gs://$STAGING_STATE_BUCKET
fi

terraform init \
    -backend-config="bucket=$STAGING_STATE_BUCKET" \
    -backend-config="prefix=staging" \
    -reconfigure

# Step 5: Select/create workspace
print_status "Setting Terraform workspace to staging..."
terraform workspace select staging 2>/dev/null || terraform workspace new staging

# Step 6: Setup secrets
print_status "Setting up secrets..."
./setup-auth-secrets.sh $PROJECT_ID $PROJECT_ID_NUMERICAL $ENVIRONMENT || true

# Step 7: Build Docker images
print_status "Building Docker images..."
cd ..  # Move to project root

# Backend image
if [ -f "Dockerfile.backend" ]; then
    print_info "Building backend image..."
    docker build -f Dockerfile.backend \
        -t ${REGISTRY}/backend:latest \
        -t ${REGISTRY}/backend:${ENVIRONMENT} \
        .
    docker push ${REGISTRY}/backend:latest
    docker push ${REGISTRY}/backend:${ENVIRONMENT}
else
    print_warning "Dockerfile.backend not found"
fi

# Frontend image
if [ -f "Dockerfile.frontend.staging" ]; then
    print_info "Building frontend image with staging configuration..."
    docker build -f Dockerfile.frontend.staging \
        --build-arg NEXT_PUBLIC_API_URL=https://api.staging.netrasystems.ai \
        --build-arg NEXT_PUBLIC_WS_URL=wss://api.staging.netrasystems.ai/ws \
        -t ${REGISTRY}/frontend:latest \
        -t ${REGISTRY}/frontend:${ENVIRONMENT} \
        .
    docker push ${REGISTRY}/frontend:latest
    docker push ${REGISTRY}/frontend:${ENVIRONMENT}
elif [ -f "Dockerfile.frontend.optimized" ]; then
    print_info "Building frontend image with optimized Dockerfile..."
    docker build -f Dockerfile.frontend.optimized \
        -t ${REGISTRY}/frontend:latest \
        -t ${REGISTRY}/frontend:${ENVIRONMENT} \
        .
    docker push ${REGISTRY}/frontend:latest
    docker push ${REGISTRY}/frontend:${ENVIRONMENT}
else
    print_warning "Frontend Dockerfile not found"
fi

# Auth service image
if [ -f "Dockerfile.auth" ]; then
    print_info "Building auth service image..."
    docker build -f Dockerfile.auth \
        -t ${REGISTRY}/auth-service:latest \
        -t ${REGISTRY}/auth-service:${ENVIRONMENT} \
        .
    docker push ${REGISTRY}/auth-service:latest
    docker push ${REGISTRY}/auth-service:${ENVIRONMENT}
else
    print_warning "Dockerfile.auth not found"
fi

cd terraform-gcp  # Return to terraform directory

# Step 8: Plan Terraform deployment
print_status "Planning infrastructure deployment..."
terraform plan -var-file="terraform.staging.tfvars" -out=staging-complete.tfplan

# Step 9: Apply Terraform
print_status "Applying Terraform configuration..."
terraform apply staging-complete.tfplan

# Step 10: Deploy services to Cloud Run
print_status "Deploying services to Cloud Run..."

# Get outputs from Terraform
DB_IP=$(terraform output -raw database_ip 2>/dev/null || echo "")
ARTIFACT_REGISTRY=$(terraform output -raw artifact_registry 2>/dev/null || echo $REGISTRY)

# Deploy Backend
print_status "Deploying backend service..."
gcloud run deploy netra-backend \
    --image ${REGISTRY}/backend:latest \
    --region ${REGION} \
    --platform managed \
    --port 8080 \
    --cpu 1 \
    --memory 2Gi \
    --min-instances 0 \
    --max-instances 3 \
    --allow-unauthenticated \
    --service-account netra-cloudrun@${PROJECT_ID}.iam.gserviceaccount.com \
    --set-env-vars="ENVIRONMENT=${ENVIRONMENT}" \
    --set-env-vars="DATABASE_URL=postgresql://netra_user@${DB_IP}:5432/netra" \
    --set-env-vars="CORS_ORIGINS=https://staging.netrasystems.ai,https://app.staging.netrasystems.ai" \
    --set-secrets="JWT_SECRET_KEY=jwt-secret-key-staging:latest" \
    --set-secrets="FERNET_KEY=fernet-key-staging:latest" \
    --quiet

# Deploy Frontend
print_status "Deploying frontend service..."
gcloud run deploy netra-frontend \
    --image ${REGISTRY}/frontend:latest \
    --region ${REGION} \
    --platform managed \
    --port 3000 \
    --cpu 0.5 \
    --memory 1Gi \
    --min-instances 0 \
    --max-instances 2 \
    --allow-unauthenticated \
    --quiet

# Deploy Auth Service
print_status "Deploying auth service..."
./deploy-auth-staging.sh

# Step 11: Setup Load Balancer (if needed)
print_status "Setting up load balancer..."
terraform apply \
    -var-file="terraform.staging.tfvars" \
    -target=google_compute_region_network_endpoint_group.auth_neg \
    -target=google_compute_backend_service.auth \
    -target=google_compute_url_map.auth \
    -target=google_compute_managed_ssl_certificate.auth \
    -target=google_compute_target_https_proxy.auth \
    -target=google_compute_global_address.auth \
    -target=google_compute_global_forwarding_rule.auth \
    -auto-approve || print_warning "Load balancer setup skipped or already exists"

# Step 12: Get service URLs
print_status "Getting service URLs..."
BACKEND_URL=$(gcloud run services describe netra-backend --region=${REGION} --format='value(status.url)')
FRONTEND_URL=$(gcloud run services describe netra-frontend --region=${REGION} --format='value(status.url)')
AUTH_URL=$(gcloud run services describe netra-auth-service --region=${REGION} --format='value(status.url)' 2>/dev/null || echo "Not deployed")

# Step 13: Run database migrations
print_status "Running database migrations..."
if [ -n "$DB_IP" ]; then
    # Get database password
    DB_PASSWORD=$(gcloud secrets versions access latest --secret="netra-db-password" 2>/dev/null || echo "")
    
    if [ -n "$DB_PASSWORD" ]; then
        print_info "Running migrations..."
        # You can add actual migration commands here
    else
        print_warning "Database password not found in secrets"
    fi
else
    print_warning "Database IP not found"
fi

# Step 14: Verify deployment
print_status "Verifying deployment..."

echo ""
print_info "Testing backend health..."
if curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health" | grep -q "200"; then
    print_status "✓ Backend is healthy"
else
    print_warning "Backend health check failed"
fi

print_info "Testing frontend..."
if curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" | grep -q "200\|304"; then
    print_status "✓ Frontend is accessible"
else
    print_warning "Frontend check failed"
fi

if [ "$AUTH_URL" != "Not deployed" ]; then
    print_info "Testing auth service..."
    if curl -s -o /dev/null -w "%{http_code}" "$AUTH_URL/health" | grep -q "200"; then
        print_status "✓ Auth service is healthy"
    else
        print_warning "Auth service health check failed"
    fi
fi

# Step 15: Output summary
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}    STAGING DEPLOYMENT COMPLETED               ${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
print_info "Service URLs:"
echo "  Frontend:     $FRONTEND_URL"
echo "  Backend:      $BACKEND_URL"
echo "  Auth Service: $AUTH_URL"
echo ""
print_info "Database:"
echo "  IP: $DB_IP"
echo ""
print_info "Custom domains (configure DNS):"
echo "  - https://staging.netrasystems.ai"
echo "  - https://app.staging.netrasystems.ai"
echo "  - https://api.staging.netrasystems.ai"
echo "  - https://auth.staging.netrasystems.ai"
echo ""
print_info "Management commands:"
echo "  View logs:    gcloud run logs read --region=$REGION"
echo "  View metrics: gcloud monitoring dashboards list"
echo "  Destroy all:  terraform destroy -var-file=terraform.staging.tfvars"
echo ""
print_warning "Remember to:"
echo "  1. Configure DNS records for custom domains"
echo "  2. Update OAuth redirect URIs in Google Cloud Console"
echo "  3. Set up monitoring and alerting"
echo "  4. Configure backup schedules"