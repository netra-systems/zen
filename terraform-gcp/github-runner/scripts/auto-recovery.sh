#!/bin/bash
# GitHub Runner Auto-Recovery System
# Automatically diagnoses and fixes issues when runner installation fails

set -euo pipefail

# Configuration
SCRIPTS_DIR="/opt/github-runner/scripts"
LOG_FILE="/var/log/github-runner-install.log"
ERROR_LOG="/var/log/github-runner-errors.log"
RECOVERY_LOG="/var/log/github-runner-recovery.log"
MAX_RECOVERY_ATTEMPTS=3
RECOVERY_DELAY=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Redirect output to recovery log
exec > >(tee -a "$RECOVERY_LOG") 2>&1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
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

# Function to detect failure type
detect_failure_type() {
    local failure_type="unknown"
    
    if [[ -f "$LOG_FILE" ]]; then
        # Check for specific failure patterns
        if grep -q "Failed to retrieve GitHub PAT" "$LOG_FILE"; then
            failure_type="secret_access"
        elif grep -q "PERMISSION_DENIED" "$LOG_FILE"; then
            failure_type="iam_permission"
        elif grep -q "Secret 'github-runner-token' not found" "$LOG_FILE"; then
            failure_type="secret_missing"
        elif grep -q "Failed to install gcloud SDK" "$LOG_FILE"; then
            failure_type="gcloud_install"
        elif grep -q "Docker installation failed" "$LOG_FILE"; then
            failure_type="docker_install"
        elif grep -q "Failed to create runner user" "$LOG_FILE"; then
            failure_type="user_creation"
        elif grep -q "GitHub API rate limit" "$LOG_FILE"; then
            failure_type="rate_limit"
        elif grep -q "Connection refused" "$LOG_FILE"; then
            failure_type="network"
        fi
    fi
    
    echo "$failure_type"
}

# Function to fix specific issues
fix_issue() {
    local issue_type="$1"
    local fixed=false
    
    case "$issue_type" in
        secret_access|iam_permission)
            log "Attempting to fix Secret Manager access issues..."
            
            # Get project ID and service account
            PROJECT_ID=$(curl -s -H "Metadata-Flavor: Google" \
                "http://metadata.google.internal/computeMetadata/v1/project/project-id" 2>/dev/null || echo "")
            SA_EMAIL=$(curl -s -H "Metadata-Flavor: Google" \
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email" 2>/dev/null || echo "")
            
            if [[ -n "$PROJECT_ID" ]] && [[ -n "$SA_EMAIL" ]]; then
                # Try to add IAM permission
                if gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                    --member="serviceAccount:$SA_EMAIL" \
                    --role="roles/secretmanager.secretAccessor" 2>&1; then
                    success "Added Secret Manager access permission"
                    fixed=true
                else
                    error "Failed to add IAM permission automatically"
                    log "Manual fix required:"
                    log "  gcloud projects add-iam-policy-binding $PROJECT_ID \\"
                    log "    --member=\"serviceAccount:$SA_EMAIL\" \\"
                    log "    --role=\"roles/secretmanager.secretAccessor\""
                fi
            fi
            ;;
            
        secret_missing)
            error "Secret 'github-runner-token' is missing"
            log "This requires manual intervention:"
            log "  1. Create a GitHub Personal Access Token at https://github.com/settings/tokens"
            log "  2. Run: echo -n 'YOUR_TOKEN' | gcloud secrets create github-runner-token --data-file=- --project=PROJECT_ID"
            
            # Send notification if possible
            send_notification "GitHub runner secret missing - manual intervention required"
            ;;
            
        gcloud_install)
            log "Attempting to install gcloud SDK..."
            
            # Try multiple installation methods
            if install_gcloud_sdk_method1 || install_gcloud_sdk_method2 || install_gcloud_sdk_method3; then
                success "gcloud SDK installed"
                fixed=true
            else
                error "Failed to install gcloud SDK"
            fi
            ;;
            
        docker_install)
            log "Attempting to fix Docker installation..."
            
            # Clean up and retry Docker installation
            systemctl stop docker 2>/dev/null || true
            apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
            rm -rf /var/lib/docker /etc/docker
            
            if install_docker; then
                success "Docker installed successfully"
                fixed=true
            else
                warning "Docker installation failed - runner will work without Docker support"
                fixed=true  # Continue anyway
            fi
            ;;
            
        user_creation)
            log "Attempting to create runner user..."
            
            # Remove existing user if partially created
            userdel -r runner 2>/dev/null || true
            
            # Create user
            if useradd -m -s /bin/bash runner; then
                success "Runner user created"
                fixed=true
            else
                error "Failed to create runner user"
            fi
            ;;
            
        rate_limit)
            warning "GitHub API rate limit hit - waiting 60 seconds..."
            sleep 60
            fixed=true
            ;;
            
        network)
            log "Network connectivity issue detected..."
            
            # Wait for network to stabilize
            local retries=0
            while [[ $retries -lt 5 ]]; do
                if curl -sSf --max-time 5 https://api.github.com >/dev/null 2>&1; then
                    success "Network connectivity restored"
                    fixed=true
                    break
                fi
                retries=$((retries + 1))
                log "Waiting for network (attempt $retries/5)..."
                sleep 10
            done
            ;;
            
        unknown)
            warning "Unknown failure type - running general diagnostics..."
            if [[ -x "$SCRIPTS_DIR/diagnose-runner-enhanced.sh" ]]; then
                "$SCRIPTS_DIR/diagnose-runner-enhanced.sh"
            fi
            ;;
    esac
    
    echo "$fixed"
}

# Installation methods for gcloud SDK
install_gcloud_sdk_method1() {
    log "Installing gcloud SDK via APT..."
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | \
        tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
    
    apt-get install -y apt-transport-https ca-certificates gnupg
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
        apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
    
    apt-get update && apt-get install -y google-cloud-sdk
    command -v gcloud &>/dev/null
}

install_gcloud_sdk_method2() {
    log "Installing gcloud SDK via snap..."
    snap install google-cloud-sdk --classic 2>/dev/null
    command -v gcloud &>/dev/null
}

install_gcloud_sdk_method3() {
    log "Installing gcloud SDK via direct download..."
    curl https://sdk.cloud.google.com | bash
    export PATH=$PATH:$HOME/google-cloud-sdk/bin
    source $HOME/google-cloud-sdk/path.bash.inc 2>/dev/null || true
    command -v gcloud &>/dev/null
}

install_docker() {
    log "Installing Docker..."
    
    # Try Docker CE
    apt-get update
    apt-get install -y ca-certificates curl gnupg lsb-release
    
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    apt-get update
    if apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin; then
        systemctl enable docker
        systemctl start docker
        chmod 666 /var/run/docker.sock 2>/dev/null || true
        return 0
    fi
    
    # Fallback to docker.io
    apt-get install -y docker.io docker-compose
    systemctl enable docker
    systemctl start docker
    chmod 666 /var/run/docker.sock 2>/dev/null || true
}

# Function to send notifications (if configured)
send_notification() {
    local message="$1"
    
    # Try to send to Cloud Logging
    if command -v gcloud &>/dev/null; then
        gcloud logging write github-runner-recovery "$message" --severity=ERROR 2>/dev/null || true
    fi
    
    # Could add other notification methods here (email, Slack, etc.)
}

# Main recovery function
perform_recovery() {
    local attempt="$1"
    
    log "========================================="
    log "Starting Auto-Recovery (Attempt $attempt/$MAX_RECOVERY_ATTEMPTS)"
    log "========================================="
    
    # Detect what went wrong
    local failure_type=$(detect_failure_type)
    log "Detected failure type: $failure_type"
    
    # Try to fix the issue
    local fixed=$(fix_issue "$failure_type")
    
    if [[ "$fixed" == "true" ]]; then
        success "Issue potentially fixed, retrying installation..."
        
        # Clean up previous installation attempt
        rm -f /var/run/github-runner.lock 2>/dev/null || true
        
        # Retry the installation
        if [[ -x "$SCRIPTS_DIR/install-runner.sh" ]]; then
            if "$SCRIPTS_DIR/install-runner.sh"; then
                success "Runner installation succeeded after recovery!"
                return 0
            else
                error "Installation still failing after fix attempt"
            fi
        fi
    else
        warning "Unable to automatically fix the issue"
    fi
    
    return 1
}

# Main execution
main() {
    log "GitHub Runner Auto-Recovery System Started"
    
    # Check if we should run recovery
    if [[ -f "/var/run/github-runner-recovery.lock" ]]; then
        warning "Recovery already in progress, exiting..."
        exit 0
    fi
    
    # Create lock file
    touch /var/run/github-runner-recovery.lock
    trap "rm -f /var/run/github-runner-recovery.lock" EXIT
    
    # Check if runner is already working
    SERVICE_NAME=$(systemctl list-units --all 2>/dev/null | grep -o "actions\.runner\..*\.service" | head -1 || true)
    if [[ -n "$SERVICE_NAME" ]] && systemctl is-active --quiet "$SERVICE_NAME"; then
        success "Runner service is already active, no recovery needed"
        exit 0
    fi
    
    # Perform recovery attempts
    local recovery_attempt=1
    while [[ $recovery_attempt -le $MAX_RECOVERY_ATTEMPTS ]]; do
        if perform_recovery "$recovery_attempt"; then
            success "Recovery successful!"
            
            # Run final diagnostics
            if [[ -x "$SCRIPTS_DIR/diagnose-runner-enhanced.sh" ]]; then
                "$SCRIPTS_DIR/diagnose-runner-enhanced.sh"
            fi
            
            exit 0
        fi
        
        recovery_attempt=$((recovery_attempt + 1))
        
        if [[ $recovery_attempt -le $MAX_RECOVERY_ATTEMPTS ]]; then
            log "Waiting $RECOVERY_DELAY seconds before next attempt..."
            sleep $RECOVERY_DELAY
        fi
    done
    
    error "Recovery failed after $MAX_RECOVERY_ATTEMPTS attempts"
    log "Manual intervention required. Check logs:"
    log "  - Installation log: $LOG_FILE"
    log "  - Error log: $ERROR_LOG"
    log "  - Recovery log: $RECOVERY_LOG"
    
    # Send final notification
    send_notification "GitHub runner auto-recovery failed after $MAX_RECOVERY_ATTEMPTS attempts - manual intervention required"
    
    exit 1
}

# Run main function
main "$@"