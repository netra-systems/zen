#!/bin/bash
# Deploy to Remote GCP Staging Environment from Local Machine
# This script mimics the GitHub Actions staging workflow but runs locally

set -e

# Default values
ACTION="${1:-deploy}"
PR_NUMBER="${2:-}"
BRANCH="${3:-}"
FORCE="${4:-false}"
SKIP_BUILD="${5:-false}"
SKIP_TESTS="${6:-false}"

# Configuration
PROJECT_NAME="netra-staging"
GCP_REGION="us-central1"
TERRAFORM_VERSION="1.5.0"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Output functions
log_info() { echo -e "${CYAN}$1${NC}"; }
log_success() { echo -e "${GREEN}$1${NC}"; }
log_warning() { echo -e "${YELLOW}$1${NC}"; }
log_error() { echo -e "${RED}$1${NC}"; }

# Setup environment configuration
setup_environment() {
    local config=""
    
    # Determine PR number
    if [ -n "$PR_NUMBER" ]; then
        PR_NUM="$PR_NUMBER"
    else
        CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
        PR_NUM="branch-${CURRENT_BRANCH//\//-}"
    fi
    
    # Get branch name
    if [ -n "$BRANCH" ]; then
        BRANCH_NAME="$BRANCH"
    else
        BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)
    fi
    
    # Get commit SHA
    COMMIT_SHA=$(git rev-parse HEAD)
    SHORT_SHA=${COMMIT_SHA:0:7}
    
    # Sanitize environment name
    ENV_NAME="${PROJECT_NAME}-${PR_NUM//[^a-zA-Z0-9-]/-}"
    ENV_NAME="${ENV_NAME,,}"
    ENV_NAME="${ENV_NAME:0:63}"
    
    # Get GCP project ID
    PROJECT_ID="${GCP_STAGING_PROJECT_ID:-${GCP_PROJECT_ID:-$(gcloud config get-value project)}}"
    
    log_info "Environment Configuration:"
    log_info "  Environment Name: $ENV_NAME"
    log_info "  PR Number: $PR_NUM"
    log_info "  Branch: $BRANCH_NAME"
    log_info "  Commit SHA: $SHORT_SHA"
    log_info "  GCP Project: $PROJECT_ID"
    echo ""
}

# Check GCP authentication
check_gcp_auth() {
    local account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null)
    
    if [ -n "$account" ]; then
        log_success "✓ Authenticated as: $account"
        
        # Set project
        local project="${GCP_STAGING_PROJECT_ID:-${GCP_PROJECT_ID:-}}"
        if [ -n "$project" ]; then
            gcloud config set project "$project" 2>/dev/null
            log_success "✓ Project set to: $project"
        fi
        
        # Configure Docker for GCR
        log_info "Configuring Docker for GCR..."
        gcloud auth configure-docker gcr.io --quiet
        
        return 0
    else
        log_error "GCP authentication failed. Please run: gcloud auth login"
        return 1
    fi
}

# Build and push Docker images
build_docker_images() {
    log_info "🔨 Building Docker Images..."
    local start_time=$(date +%s)
    
    # Enable BuildKit
    export DOCKER_BUILDKIT=1
    export BUILDKIT_PROGRESS=plain
    
    # Build Backend
    log_info "Building backend image..."
    BACKEND_IMAGE="gcr.io/${PROJECT_ID}/backend:${COMMIT_SHA}"
    BACKEND_LATEST="gcr.io/${PROJECT_ID}/backend:latest"
    
    # Check if image exists
    if gcloud container images describe "$BACKEND_IMAGE" 2>/dev/null; then
        log_info "Backend image already exists, skipping build"
    else
        docker build \
            --platform linux/amd64 \
            --build-arg "COMMIT_SHA=${COMMIT_SHA}" \
            --build-arg "BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
            -t "$BACKEND_IMAGE" \
            -t "$BACKEND_LATEST" \
            -f Dockerfile.backend \
            .
        
        if [ $? -ne 0 ]; then
            log_error "Backend build failed!"
            exit 1
        fi
        
        # Push to GCR
        log_info "Pushing backend image to GCR..."
        docker push "$BACKEND_IMAGE"
        docker push "$BACKEND_LATEST"
    fi
    
    # Build Frontend
    log_info "Building frontend image..."
    FRONTEND_IMAGE="gcr.io/${PROJECT_ID}/frontend:${COMMIT_SHA}"
    FRONTEND_LATEST="gcr.io/${PROJECT_ID}/frontend:latest"
    
    # Check if image exists
    if gcloud container images describe "$FRONTEND_IMAGE" 2>/dev/null; then
        log_info "Frontend image already exists, skipping build"
    else
        docker build \
            --platform linux/amd64 \
            --build-arg "COMMIT_SHA=${COMMIT_SHA}" \
            --build-arg "BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
            -t "$FRONTEND_IMAGE" \
            -t "$FRONTEND_LATEST" \
            -f Dockerfile.frontend.staging \
            .
        
        if [ $? -ne 0 ]; then
            log_error "Frontend build failed!"
            exit 1
        fi
        
        # Push to GCR
        log_info "Pushing frontend image to GCR..."
        docker push "$FRONTEND_IMAGE"
        docker push "$FRONTEND_LATEST"
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    log_success "✓ Images built and pushed in ${duration} seconds"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    log_info "🏗️ Deploying Infrastructure with Terraform..."
    local start_time=$(date +%s)
    
    cd terraform/staging
    
    # Setup state bucket
    BUCKET="${TF_STAGING_STATE_BUCKET:-${TF_STATE_BUCKET:-netra-staging-terraform-state}}"
    
    # Create bucket if it doesn't exist
    if ! gsutil ls "gs://${BUCKET}" 2>/dev/null; then
        log_info "Creating Terraform state bucket..."
        gsutil mb -p "${PROJECT_ID}" -l "${GCP_REGION}" "gs://${BUCKET}"
    fi
    
    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init \
        -backend-config="bucket=${BUCKET}" \
        -backend-config="prefix=${ENV_NAME}" \
        -upgrade=false \
        -reconfigure \
        -input=false
    
    if [ $? -ne 0 ]; then
        log_error "Terraform init failed!"
        exit 1
    fi
    
    # Create tfvars file
    log_info "Creating terraform.tfvars..."
    cat > terraform.tfvars <<EOF
environment_name = "${ENV_NAME}"
pr_number = "${PR_NUM}"
branch_name = "${BRANCH_NAME}"
commit_sha = "${COMMIT_SHA}"
project_id = "${PROJECT_ID}"
backend_image = "${BACKEND_IMAGE}"
frontend_image = "${FRONTEND_IMAGE}"
postgres_password = "${POSTGRES_PASSWORD_STAGING:-staging-password}"
clickhouse_password = "${CLICKHOUSE_PASSWORD_STAGING:-staging-clickhouse}"
jwt_secret_key = "${JWT_SECRET_KEY_STAGING:-}"
fernet_key = "${FERNET_KEY_STAGING:-}"
gemini_api_key = "${GEMINI_API_KEY_STAGING:-}"
EOF
    
    # Apply deployment
    log_info "Applying deployment..."
    terraform apply -auto-approve
    
    if [ $? -ne 0 ]; then
        log_error "Terraform apply failed!"
        exit 1
    fi
    
    # Get outputs
    BACKEND_URL=$(terraform output -raw backend_url 2>/dev/null)
    FRONTEND_URL=$(terraform output -raw frontend_url 2>/dev/null)
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_success "✓ Infrastructure deployed in ${duration} seconds"
    log_success "Frontend URL: ${FRONTEND_URL}"
    log_success "Backend URL: ${BACKEND_URL}"
    
    cd ../..
}

# Destroy infrastructure
destroy_infrastructure() {
    log_warning "🗑️ Destroying Infrastructure..."
    
    cd terraform/staging
    
    # Setup state bucket
    BUCKET="${TF_STAGING_STATE_BUCKET:-${TF_STATE_BUCKET:-netra-staging-terraform-state}}"
    
    # Initialize Terraform
    terraform init \
        -backend-config="bucket=${BUCKET}" \
        -backend-config="prefix=${ENV_NAME}" \
        -upgrade=false \
        -reconfigure \
        -input=false
    
    # Destroy
    terraform destroy \
        -auto-approve \
        -var="environment_name=${ENV_NAME}" \
        -var="pr_number=${PR_NUM}" \
        -var="project_id=${PROJECT_ID}"
    
    log_success "✓ Infrastructure destroyed"
    
    cd ../..
}

# Run smoke tests
test_deployment() {
    log_info "🧪 Running Smoke Tests..."
    
    # Wait for services
    sleep 15
    
    # Test backend health
    log_info "Testing backend health..."
    MAX_RETRIES=10
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -f "${BACKEND_URL}/health" --max-time 10 --retry 3 --retry-delay 2 2>/dev/null; then
            log_success "✓ Backend is healthy"
            break
        fi
        
        RETRY_COUNT=$((RETRY_COUNT + 1))
        log_warning "Backend not ready, retry ${RETRY_COUNT}/${MAX_RETRIES}"
        sleep 5
    done
    
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        log_error "Backend health check failed after ${MAX_RETRIES} retries"
        exit 1
    fi
    
    # Test frontend
    log_info "Testing frontend..."
    if curl -f "${FRONTEND_URL}" --max-time 10 --retry 3 --retry-delay 2 -o /dev/null -s; then
        log_success "✓ Frontend is accessible"
    else
        log_warning "Frontend may not be fully ready yet"
    fi
}

# Get deployment status
get_deployment_status() {
    log_info "📊 Getting Deployment Status..."
    
    cd terraform/staging
    
    # Setup state bucket
    BUCKET="${TF_STAGING_STATE_BUCKET:-${TF_STATE_BUCKET:-netra-staging-terraform-state}}"
    
    # Initialize Terraform
    terraform init \
        -backend-config="bucket=${BUCKET}" \
        -backend-config="prefix=${ENV_NAME}" \
        -upgrade=false \
        -reconfigure \
        -input=false 2>/dev/null
    
    # Get outputs
    local backend_url=$(terraform output -raw backend_url 2>/dev/null)
    local frontend_url=$(terraform output -raw frontend_url 2>/dev/null)
    
    if [ -n "$backend_url" ] && [ -n "$frontend_url" ]; then
        log_success "Deployment is active"
        log_info "Frontend URL: $frontend_url"
        log_info "Backend URL: $backend_url"
        
        # Test health
        if curl -f "${backend_url}/health" --max-time 5 2>/dev/null; then
            log_success "Backend: Healthy"
        else
            log_warning "Backend: Not responding"
        fi
        
        if curl -f "$frontend_url" --max-time 5 -o /dev/null -s 2>/dev/null; then
            log_success "Frontend: Accessible"
        else
            log_warning "Frontend: Not responding"
        fi
    else
        log_warning "No active deployment found for ${ENV_NAME}"
    fi
    
    cd ../..
}

# Restart services
restart_services() {
    log_info "🔄 Restarting Services..."
    
    # Restart backend
    log_info "Restarting backend service..."
    gcloud run services update "backend-${PR_NUM}" \
        --region="${GCP_REGION}" \
        --project="${PROJECT_ID}" \
        --update-env-vars="RESTART_TIME=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    
    # Restart frontend
    log_info "Restarting frontend service..."
    gcloud run services update "frontend-${PR_NUM}" \
        --region="${GCP_REGION}" \
        --project="${PROJECT_ID}" \
        --update-env-vars="RESTART_TIME=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    
    log_success "✓ Services restarted"
}

# Check prerequisites
check_prerequisites() {
    local missing=()
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing+=("Docker")
    else
        if ! docker info &> /dev/null; then
            log_error "Docker is not running. Please start Docker."
            exit 1
        fi
    fi
    
    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        missing+=("Google Cloud SDK (gcloud)")
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        missing+=("Terraform")
    fi
    
    # Check git
    if ! command -v git &> /dev/null; then
        missing+=("Git")
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing prerequisites: ${missing[*]}"
        log_info "Please install the missing tools and try again."
        exit 1
    fi
    
    log_success "✓ All prerequisites met"
}

# Main deployment function
main() {
    log_info "🚀 Starting Remote Staging Deployment"
    log_info "========================================"
    log_info "Action: $ACTION"
    echo ""
    
    check_prerequisites
    setup_environment
    
    if ! check_gcp_auth; then
        exit 1
    fi
    
    case "$ACTION" in
        deploy|rebuild)
            if [ "$SKIP_BUILD" != "true" ]; then
                build_docker_images
            fi
            deploy_infrastructure
            if [ "$SKIP_TESTS" != "true" ]; then
                test_deployment
            fi
            ;;
        destroy)
            destroy_infrastructure
            ;;
        status)
            get_deployment_status
            ;;
        restart)
            restart_services
            ;;
        *)
            log_error "Invalid action: $ACTION"
            echo "Usage: $0 [deploy|destroy|restart|status|rebuild] [pr_number] [branch] [force] [skip_build] [skip_tests]"
            exit 1
            ;;
    esac
    
    log_success "✅ Deployment Complete!"
}

# Run main function
main