#!/bin/bash
# Deploy GitHub Runner to Cloud Run using Terraform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID="${GCP_PROJECT_ID:-}"
GITHUB_TOKEN="${TF_VAR_github_token:-}"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

check_requirements() {
    log "Checking requirements..."
    
    # Check for required tools
    command -v terraform >/dev/null 2>&1 || error "terraform is required but not installed"
    command -v gcloud >/dev/null 2>&1 || error "gcloud is required but not installed"
    command -v docker >/dev/null 2>&1 || warn "docker is recommended for local testing"
    
    # Check for required environment variables
    if [[ -z "$GITHUB_TOKEN" ]]; then
        error "TF_VAR_github_token environment variable is required"
    fi
    
    if [[ -z "$PROJECT_ID" ]]; then
        error "GCP_PROJECT_ID environment variable is required"
    fi
    
    log "Requirements check passed"
}

authenticate_gcp() {
    log "Authenticating with GCP..."
    
    # Check if already authenticated
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log "Already authenticated with GCP"
    else
        log "Please authenticate with GCP"
        gcloud auth login
    fi
    
    # Set project
    gcloud config set project "$PROJECT_ID"
    
    # Enable required APIs
    log "Enabling required APIs..."
    gcloud services enable \
        run.googleapis.com \
        artifactregistry.googleapis.com \
        cloudbuild.googleapis.com \
        secretmanager.googleapis.com \
        cloudscheduler.googleapis.com \
        --project="$PROJECT_ID"
}

build_and_push_image() {
    log "Building and pushing Docker image..."
    
    local IMAGE_URL="${REGION:-us-central1}-docker.pkg.dev/${PROJECT_ID}/github-runners/runner"
    
    # Create Artifact Registry repository if it doesn't exist
    if ! gcloud artifacts repositories describe github-runners \
        --location="${REGION:-us-central1}" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
        log "Creating Artifact Registry repository..."
        gcloud artifacts repositories create github-runners \
            --repository-format=docker \
            --location="${REGION:-us-central1}" \
            --project="$PROJECT_ID"
    fi
    
    # Configure Docker authentication
    gcloud auth configure-docker "${REGION:-us-central1}-docker.pkg.dev"
    
    # Build image
    cd "$SCRIPT_DIR"
    docker build -t "$IMAGE_URL:latest" .
    
    # Push image
    docker push "$IMAGE_URL:latest"
    
    log "Image pushed to $IMAGE_URL:latest"
}

deploy_with_terraform() {
    log "Deploying with Terraform..."
    
    cd "$SCRIPT_DIR"
    
    # Initialize Terraform
    terraform init
    
    # Create terraform.tfvars if it doesn't exist
    if [[ ! -f terraform.tfvars ]]; then
        log "Creating terraform.tfvars from example..."
        cp terraform.tfvars.example terraform.tfvars
        warn "Please edit terraform.tfvars with your configuration"
        exit 0
    fi
    
    # Plan deployment
    log "Planning Terraform deployment..."
    terraform plan -out=tfplan
    
    # Apply deployment
    read -p "Do you want to apply this plan? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy]es$ ]]; then
        terraform apply tfplan
        log "Deployment complete!"
        
        # Show outputs
        echo ""
        log "Deployment outputs:"
        terraform output
    else
        log "Deployment cancelled"
    fi
}

cleanup() {
    read -p "Do you want to destroy the deployment? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy]es$ ]]; then
        cd "$SCRIPT_DIR"
        terraform destroy -auto-approve
        log "Resources destroyed"
    fi
}

# Main execution
main() {
    log "GitHub Runner Cloud Run Deployment Script"
    log "========================================="
    
    case "${1:-deploy}" in
        deploy)
            check_requirements
            authenticate_gcp
            build_and_push_image
            deploy_with_terraform
            ;;
        build)
            check_requirements
            authenticate_gcp
            build_and_push_image
            ;;
        terraform)
            check_requirements
            deploy_with_terraform
            ;;
        destroy)
            cleanup
            ;;
        *)
            echo "Usage: $0 [deploy|build|terraform|destroy]"
            echo "  deploy    - Build image and deploy with Terraform (default)"
            echo "  build     - Build and push Docker image only"
            echo "  terraform - Deploy with Terraform only (assumes image exists)"
            echo "  destroy   - Destroy all resources"
            exit 1
            ;;
    esac
}

main "$@"