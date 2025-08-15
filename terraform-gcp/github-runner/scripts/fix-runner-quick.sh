#!/bin/bash
# Quick Fix Script for GitHub Runner Issues
# Run this script to automatically fix common runner problems

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get project ID from metadata or environment
PROJECT_ID="${PROJECT_ID:-$(curl -s -H "Metadata-Flavor: Google" \
    "http://metadata.google.internal/computeMetadata/v1/project/project-id" 2>/dev/null || echo "")}"

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}GitHub Runner Quick Fix Script${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# 1. Fix gcloud SDK if missing
log "Checking gcloud SDK..."
if ! command -v gcloud &>/dev/null; then
    warning "gcloud SDK not found, installing..."
    
    # Method 1: APT repository
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | \
        sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
    
    sudo apt-get install -y apt-transport-https ca-certificates gnupg
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
        sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
    
    sudo apt-get update && sudo apt-get install -y google-cloud-sdk
    
    if command -v gcloud &>/dev/null; then
        success "gcloud SDK installed successfully"
    else
        # Method 2: Direct download
        warning "APT installation failed, trying direct download..."
        curl https://sdk.cloud.google.com | bash
        export PATH=$PATH:$HOME/google-cloud-sdk/bin
        source $HOME/google-cloud-sdk/path.bash.inc
    fi
else
    success "gcloud SDK is installed"
fi

# 2. Check and fix Secret Manager access
log "Checking Secret Manager configuration..."
if [[ -z "$PROJECT_ID" ]]; then
    error "PROJECT_ID not set. Please set it:"
    echo "  export PROJECT_ID=your-project-id"
    exit 1
fi

echo "Project ID: $PROJECT_ID"

# Get service account
SA_EMAIL=$(curl -s -H "Metadata-Flavor: Google" \
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email" 2>/dev/null)
echo "Service Account: $SA_EMAIL"

# Check if secret exists
log "Checking if secret 'github-runner-token' exists..."
if ! gcloud secrets describe "github-runner-token" --project="$PROJECT_ID" &>/dev/null 2>&1; then
    error "Secret 'github-runner-token' not found!"
    echo ""
    echo "Please create the secret with your GitHub Personal Access Token:"
    echo ""
    echo "  echo -n 'YOUR_GITHUB_PAT' | gcloud secrets create github-runner-token \\"
    echo "    --data-file=- --project=$PROJECT_ID"
    echo ""
    echo "To create a GitHub PAT:"
    echo "  1. Go to https://github.com/settings/tokens"
    echo "  2. Click 'Generate new token (classic)'"
    echo "  3. Select scopes: repo, workflow, admin:org (for org runners)"
    echo "  4. Generate and copy the token"
    echo ""
    exit 1
else
    success "Secret 'github-runner-token' exists"
fi

# Check IAM permissions
log "Checking IAM permissions..."
if ! gcloud secrets versions access latest \
    --secret="github-runner-token" \
    --project="$PROJECT_ID" &>/dev/null 2>&1; then
    
    warning "Cannot access secret. Adding IAM permission..."
    
    # Try to add the permission
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="roles/secretmanager.secretAccessor" 2>&1 || {
        error "Failed to add IAM permission. Please run manually:"
        echo ""
        echo "  gcloud projects add-iam-policy-binding $PROJECT_ID \\"
        echo "    --member=\"serviceAccount:$SA_EMAIL\" \\"
        echo "    --role=\"roles/secretmanager.secretAccessor\""
        echo ""
        exit 1
    }
    
    success "IAM permission added"
else
    success "Secret is accessible"
fi

# 3. Fix Docker permissions
log "Checking Docker..."
if command -v docker &>/dev/null; then
    # Fix Docker socket permissions
    if [[ -S /var/run/docker.sock ]]; then
        sudo chmod 666 /var/run/docker.sock
        success "Docker socket permissions fixed"
    fi
    
    # Add runner user to docker group
    if id runner &>/dev/null; then
        sudo usermod -aG docker runner 2>/dev/null || true
        success "Runner user added to docker group"
    fi
    
    # Restart Docker if needed
    if ! docker version &>/dev/null 2>&1; then
        warning "Docker not responding, restarting..."
        sudo systemctl stop docker
        sudo rm -f /var/run/docker.pid /var/run/docker.sock 2>/dev/null || true
        sudo systemctl start docker
        sleep 5
        
        if docker version &>/dev/null 2>&1; then
            success "Docker restarted successfully"
        else
            error "Docker still not working"
        fi
    else
        success "Docker is working"
    fi
else
    warning "Docker not installed"
fi

# 4. Restart runner service if it exists
log "Checking runner service..."
SERVICE_NAME=$(systemctl list-units --all 2>/dev/null | grep -o "actions\.runner\..*\.service" | head -1 || true)
if [[ -n "$SERVICE_NAME" ]]; then
    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        warning "Runner service not active, restarting..."
        sudo systemctl restart "$SERVICE_NAME" || {
            error "Failed to restart runner service"
        }
    else
        success "Runner service is active"
    fi
else
    warning "No runner service found. You may need to re-run the installation."
fi

# 5. Test secret access
log "Testing secret access..."
if TOKEN=$(gcloud secrets versions access latest \
    --secret="github-runner-token" \
    --project="$PROJECT_ID" 2>&1); then
    
    if [[ -n "$TOKEN" ]] && [[ "$TOKEN" != *"ERROR"* ]]; then
        success "Successfully retrieved GitHub token from Secret Manager!"
        echo ""
        echo -e "${GREEN}✓ All checks passed!${NC}"
        echo ""
        echo "If the runner still isn't working, try:"
        echo "  1. Reboot the instance: sudo reboot"
        echo "  2. Re-run the installation: sudo /opt/github-runner/scripts/install-runner.sh"
        echo "  3. Check logs: sudo tail -f /var/log/github-runner-install.log"
    else
        error "Token retrieval returned an error: ${TOKEN:0:100}"
    fi
else
    error "Failed to retrieve token"
fi

echo ""
echo -e "${BLUE}=========================================${NC}"
echo "Quick fix complete."
echo "Run diagnostics: sudo /opt/github-runner/scripts/diagnose-runner-enhanced.sh"
echo -e "${BLUE}=========================================${NC}"