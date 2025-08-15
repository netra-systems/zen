#!/bin/bash
# Enhanced GitHub Runner Startup Script for GCE Instances
# This script is designed to be run as the startup script for GCE instances
# It includes comprehensive error handling, logging, and automatic recovery

set -euo pipefail

# Configuration from Terraform variables
GITHUB_ORG="${github_org}"
GITHUB_REPO="${github_repo}"
RUNNER_NAME="${runner_name}"
RUNNER_LABELS="${runner_labels}"
RUNNER_GROUP="${runner_group}"
PROJECT_ID="${project_id}"
RUNNER_VERSION="${runner_version:-2.317.0}"

# Script configuration
RUNNER_USER="runner"
RUNNER_HOME="/home/$RUNNER_USER"
RUNNER_DIR="$RUNNER_HOME/actions-runner"
LOG_FILE="/var/log/github-runner-startup.log"
SCRIPTS_DIR="/opt/github-runner/scripts"

# Redirect output to log file
exec > >(tee -a "$LOG_FILE") 2>&1

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Error handler
error_handler() {
    local exit_code=$?
    log "ERROR: Script failed at line $1 with exit code $exit_code"
    log "ERROR: Call stack:"
    local frame=0
    while caller $frame; do
        ((frame++))
    done
    exit $exit_code
}
trap 'error_handler $LINENO' ERR

log "========================================="
log "GitHub Runner Startup Script v2.0"
log "========================================="

# Step 1: Deploy helper scripts
deploy_helper_scripts() {
    log "Deploying helper scripts..."
    
    mkdir -p "$SCRIPTS_DIR"
    
    # Create diagnostic script
    cat > "$SCRIPTS_DIR/diagnose-runner.sh" << 'DIAG_EOF'
#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== GitHub Runner Diagnostics ==="
echo "Date: $(date)"
echo ""

# Check runner user
if id runner &>/dev/null; then
    echo -e "${GREEN}✓${NC} Runner user exists"
else
    echo -e "${RED}✗${NC} Runner user missing"
fi

# Check Docker
if command -v docker &>/dev/null; then
    if docker version &>/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Docker is working"
        if su - runner -c "docker version" &>/dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Runner can access Docker"
        else
            echo -e "${RED}✗${NC} Runner cannot access Docker"
            echo "  Fix: sudo chmod 666 /var/run/docker.sock"
        fi
    else
        echo -e "${YELLOW}⚠${NC} Docker daemon not responding"
    fi
else
    echo -e "${YELLOW}⚠${NC} Docker not installed"
fi

# Check runner service
service_name=$(systemctl list-units --all 2>/dev/null | grep -o "actions\.runner\..*\.service" | head -1)
if [[ -n "$service_name" ]]; then
    if systemctl is-active --quiet "$service_name"; then
        echo -e "${GREEN}✓${NC} Runner service active: $service_name"
    else
        echo -e "${RED}✗${NC} Runner service not active: $service_name"
        echo "  Fix: sudo systemctl start $service_name"
    fi
else
    echo -e "${RED}✗${NC} No runner service found"
fi

# Check GitHub connectivity
if curl -sSf --max-time 5 https://api.github.com >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} GitHub API accessible"
else
    echo -e "${RED}✗${NC} Cannot reach GitHub API"
fi

# Check runner configuration
if [[ -f "/home/runner/actions-runner/.runner" ]]; then
    echo -e "${GREEN}✓${NC} Runner is configured"
    echo "  Name: $(jq -r .agentName /home/runner/actions-runner/.runner 2>/dev/null || echo 'Unknown')"
else
    echo -e "${YELLOW}⚠${NC} Runner not configured"
fi

# System resources
echo ""
echo "System Resources:"
echo "  Memory: $(free -h | grep Mem: | awk '{print "Used: " $3 " / Total: " $2}')"
echo "  Disk: $(df -h / | tail -1 | awk '{print "Used: " $3 " / Total: " $2 " (" $5 " used)"}')"
echo "  Load: $(uptime | awk -F'load average:' '{print $2}')"

echo "==================================="
DIAG_EOF

    # Create fix script
    cat > "$SCRIPTS_DIR/fix-runner.sh" << 'FIX_EOF'
#!/bin/bash
set -euo pipefail

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting automatic fixes..."

# Fix Docker permissions
if command -v docker &>/dev/null; then
    log "Fixing Docker permissions..."
    groupadd docker 2>/dev/null || true
    usermod -aG docker runner 2>/dev/null || true
    chmod 666 /var/run/docker.sock 2>/dev/null || true
    
    # Restart Docker if needed
    if ! docker version &>/dev/null 2>&1; then
        log "Restarting Docker..."
        systemctl stop docker || true
        rm -f /var/run/docker.pid /var/run/docker.sock 2>/dev/null || true
        systemctl start docker || true
        sleep 5
    fi
    
    if docker version &>/dev/null 2>&1; then
        log "✓ Docker is working"
    else
        log "✗ Docker still not working"
    fi
fi

# Fix runner service
service_name=$(systemctl list-units --all | grep -o "actions\.runner\..*\.service" | head -1)
if [[ -n "$service_name" ]]; then
    if ! systemctl is-active --quiet "$service_name"; then
        log "Restarting runner service: $service_name"
        systemctl restart "$service_name" || {
            log "Failed to restart, trying to reinstall..."
            cd /home/runner/actions-runner
            ./svc.sh stop 2>/dev/null || true
            ./svc.sh uninstall 2>/dev/null || true
            ./svc.sh install runner
            ./svc.sh start
        }
    fi
    
    if systemctl is-active --quiet "$service_name"; then
        log "✓ Runner service is active"
    else
        log "✗ Runner service still not active"
    fi
else
    log "No runner service found to fix"
fi

# Fix file permissions
if [[ -d "/home/runner" ]]; then
    chown -R runner:runner /home/runner 2>/dev/null || true
    log "✓ File permissions fixed"
fi

log "Automatic fixes completed"
FIX_EOF

    chmod +x "$SCRIPTS_DIR"/*.sh
    
    # Create convenience commands
    ln -sf "$SCRIPTS_DIR/diagnose-runner.sh" /usr/local/bin/runner-status 2>/dev/null || true
    ln -sf "$SCRIPTS_DIR/fix-runner.sh" /usr/local/bin/runner-fix 2>/dev/null || true
    
    log "Helper scripts deployed to $SCRIPTS_DIR"
}

# Step 2: System prerequisites check
check_system() {
    log "Checking system prerequisites..."
    
    # Check memory
    local mem_total=$(free -b | awk '/^Mem:/{print $2}')
    local mem_gb=$((mem_total / 1024 / 1024 / 1024))
    if [[ $mem_gb -lt 2 ]]; then
        log "WARNING: System has only ${mem_gb}GB RAM (recommended: 2GB+)"
    fi
    
    # Check disk space
    local disk_available=$(df / | awk 'NR==2 {print int($4/1024/1024)}')
    if [[ $disk_available -lt 10 ]]; then
        log "WARNING: Only ${disk_available}GB disk space available (recommended: 10GB+)"
    fi
    
    # Ensure we're running as root
    if [[ "$EUID" -ne 0 ]]; then
        log "ERROR: This script must be run as root"
        exit 1
    fi
}

# Step 3: Install dependencies
install_dependencies() {
    log "Installing dependencies..."
    
    # Update package lists
    apt-get update || log "WARNING: apt-get update failed"
    
    # Essential packages
    apt-get install -y curl jq git || {
        log "ERROR: Failed to install essential packages"
        exit 1
    }
    
    # Development packages
    apt-get install -y build-essential libssl-dev libffi-dev python3 python3-venv python3-dev python3-pip || {
        log "WARNING: Some development packages failed to install"
    }
    
    # Install Docker (optional)
    install_docker
}

# Step 4: Install Docker
install_docker() {
    log "Installing Docker..."
    
    if command -v docker &>/dev/null; then
        log "Docker already installed"
        return 0
    fi
    
    # Try Docker CE first
    apt-get install -y ca-certificates gnupg lsb-release || true
    
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null || true
    
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    apt-get update
    
    if apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin; then
        log "Docker CE installed successfully"
    else
        log "Docker CE installation failed, trying docker.io..."
        apt-get install -y docker.io docker-compose || {
            log "WARNING: Docker installation failed completely"
            return 1
        }
    fi
    
    # Start Docker
    systemctl enable docker
    systemctl start docker || {
        log "WARNING: Docker failed to start"
        return 1
    }
    
    # Fix permissions
    chmod 666 /var/run/docker.sock 2>/dev/null || true
    
    return 0
}

# Step 5: Create runner user
create_runner_user() {
    log "Creating runner user..."
    
    if ! id "$RUNNER_USER" &>/dev/null; then
        useradd -m -s /bin/bash "$RUNNER_USER" || {
            log "ERROR: Failed to create runner user"
            exit 1
        }
    fi
    
    # Add to docker group if Docker is installed
    if command -v docker &>/dev/null; then
        usermod -aG docker "$RUNNER_USER" || true
    fi
    
    log "Runner user configured"
}

# Step 6: Get GitHub token
get_github_token() {
    log "Retrieving GitHub token from Secret Manager..."
    
    # Install gcloud if needed
    if ! command -v gcloud &>/dev/null; then
        log "Installing Google Cloud SDK..."
        echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | \
            tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
        
        apt-get install -y apt-transport-https ca-certificates gnupg
        curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
            apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
        
        apt-get update && apt-get install -y google-cloud-sdk
    fi
    
    # Retrieve token with retries
    local max_retries=10
    local retry_count=0
    local token=""
    
    while [[ $retry_count -lt $max_retries ]]; do
        if gcloud secrets describe "github-runner-token" --project="$PROJECT_ID" &>/dev/null; then
            token=$(gcloud secrets versions access latest --secret="github-runner-token" --project="$PROJECT_ID" 2>&1)
            
            if [[ $? -eq 0 && -n "$token" ]]; then
                log "Successfully retrieved GitHub token"
                echo "$token"
                return 0
            fi
        fi
        
        retry_count=$((retry_count + 1))
        log "Token retrieval attempt $retry_count/$max_retries failed, retrying..."
        sleep 10
    done
    
    log "ERROR: Failed to retrieve GitHub token"
    exit 1
}

# Step 7: Get registration token
get_registration_token() {
    local github_token=$1
    log "Getting runner registration token..."
    
    local api_url
    if [[ -n "$GITHUB_REPO" ]]; then
        api_url="https://api.github.com/repos/$GITHUB_ORG/$GITHUB_REPO/actions/runners/registration-token"
    else
        api_url="https://api.github.com/orgs/$GITHUB_ORG/actions/runners/registration-token"
    fi
    
    local response=$(curl -sX POST \
        -H "Authorization: token $github_token" \
        -H "Accept: application/vnd.github.v3+json" \
        "$api_url")
    
    local reg_token=$(echo "$response" | jq -r .token)
    
    if [[ "$reg_token" != "null" && -n "$reg_token" ]]; then
        log "Successfully obtained registration token"
        echo "$reg_token"
    else
        log "ERROR: Failed to get registration token"
        log "Response: $response"
        exit 1
    fi
}

# Step 8: Install runner
install_runner() {
    log "Installing GitHub runner..."
    
    su - "$RUNNER_USER" -c "
        mkdir -p $RUNNER_DIR
        cd $RUNNER_DIR
        curl -o actions-runner-linux-x64-$RUNNER_VERSION.tar.gz -L \
            https://github.com/actions/runner/releases/download/v$RUNNER_VERSION/actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
        tar xzf actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
        rm actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
    "
    
    log "Runner software installed"
}

# Step 9: Configure runner
configure_runner() {
    local reg_token=$1
    log "Configuring runner..."
    
    local runner_url
    if [[ -n "$GITHUB_REPO" ]]; then
        runner_url="https://github.com/$GITHUB_ORG/$GITHUB_REPO"
    else
        runner_url="https://github.com/$GITHUB_ORG"
    fi
    
    local unique_name="$RUNNER_NAME-$(hostname)-$(date +%s)"
    
    local config_cmd="./config.sh --url $runner_url --token $reg_token --name $unique_name --unattended --replace"
    
    if [[ -n "$RUNNER_LABELS" ]]; then
        config_cmd="$config_cmd --labels $RUNNER_LABELS"
    fi
    
    if [[ -n "$RUNNER_GROUP" ]]; then
        config_cmd="$config_cmd --runnergroup $RUNNER_GROUP"
    fi
    
    su - "$RUNNER_USER" -c "cd $RUNNER_DIR && $config_cmd"
    
    log "Runner configured successfully"
}

# Step 10: Install as service
install_service() {
    log "Installing runner as service..."
    
    cd "$RUNNER_DIR"
    ./svc.sh install "$RUNNER_USER"
    ./svc.sh start
    
    systemctl enable "actions.runner.*"
    
    log "Runner service installed and started"
}

# Step 11: Setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create cron job for automatic recovery
    cat > /etc/cron.d/github-runner-autofix << 'EOF'
# Automatic GitHub Runner recovery
*/5 * * * * root if ! systemctl is-active --quiet "actions.runner.*"; then /opt/github-runner/scripts/fix-runner.sh >/dev/null 2>&1; fi
EOF
    
    # Install Google Cloud Ops Agent (optional)
    curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
    bash add-google-cloud-ops-agent-repo.sh --also-install 2>/dev/null || true
    
    log "Monitoring configured"
}

# Main execution
main() {
    # Wait for system initialization
    log "Waiting for system initialization..."
    sleep 20
    
    # Run all steps
    check_system
    deploy_helper_scripts
    install_dependencies
    create_runner_user
    
    # Get tokens
    GITHUB_TOKEN=$(get_github_token)
    REG_TOKEN=$(get_registration_token "$GITHUB_TOKEN")
    
    # Install and configure runner
    install_runner
    configure_runner "$REG_TOKEN"
    
    # Verify Docker access for runner
    if command -v docker &>/dev/null; then
        chmod 666 /var/run/docker.sock 2>/dev/null || true
        if su - "$RUNNER_USER" -c "docker version" &>/dev/null; then
            log "✓ Runner can access Docker"
        else
            log "⚠ Runner cannot access Docker"
        fi
    fi
    
    # Install service
    install_service
    
    # Setup monitoring
    setup_monitoring
    
    # Final diagnostics
    log ""
    log "========================================="
    log "Installation Complete - Running Diagnostics"
    log "========================================="
    
    if [[ -x "$SCRIPTS_DIR/diagnose-runner.sh" ]]; then
        "$SCRIPTS_DIR/diagnose-runner.sh" || true
    fi
    
    log ""
    log "========================================="
    log "GitHub Runner Installation Completed!"
    log "Available commands:"
    log "  runner-status - Check runner health"
    log "  runner-fix    - Fix common issues"
    log "Logs: $LOG_FILE"
    log "========================================="
}

# Run main function
main