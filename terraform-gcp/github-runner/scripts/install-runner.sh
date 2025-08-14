#!/bin/bash
set -e

# Variables from Terraform
GITHUB_ORG="${github_org}"
GITHUB_REPO="${github_repo}"
RUNNER_NAME="${runner_name}"
RUNNER_LABELS="${runner_labels}"
RUNNER_GROUP="${runner_group}"
PROJECT_ID="${project_id}"

# Runner configuration
RUNNER_VERSION="${runner_version}"
RUNNER_USER="runner"
RUNNER_HOME="/home/$RUNNER_USER"
RUNNER_DIR="$RUNNER_HOME/actions-runner"

# Log file for debugging
LOG_FILE="/var/log/github-runner-install.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

# Logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Install dependencies
install_dependencies() {
    log "Installing dependencies..."
    apt-get update || { log "ERROR: apt-get update failed"; exit 1; }
    
    # Install packages one by one to identify failures
    PACKAGES="curl jq git build-essential libssl-dev libffi-dev python3 python3-venv python3-dev python3-pip"
    for pkg in $PACKAGES; do
        log "Installing $pkg..."
        apt-get install -y $pkg || log "WARNING: Failed to install $pkg"
    done
    
    # Install Docker separately with retry
    log "Installing Docker..."
    local max_retries=3
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        if apt-get install -y docker.io docker-compose; then
            log "Docker installed successfully"
            break
        fi
        retry_count=$((retry_count + 1))
        log "Docker installation attempt $retry_count failed, retrying..."
        sleep 5
    done
    
    if [ $retry_count -eq $max_retries ]; then
        log "ERROR: Failed to install Docker after $max_retries attempts"
        exit 1
    fi
    
    # Enable and start Docker with verification
    log "Starting Docker service..."
    systemctl daemon-reload
    systemctl enable docker
    systemctl start docker
    
    # Wait for Docker to be ready
    local docker_ready=false
    for i in {1..30}; do
        if docker version &>/dev/null; then
            docker_ready=true
            log "Docker is ready"
            break
        fi
        log "Waiting for Docker to start... ($i/30)"
        sleep 2
    done
    
    if [ "$docker_ready" = false ]; then
        log "ERROR: Docker failed to start properly"
        systemctl status docker --no-pager
        journalctl -xe -u docker --no-pager | tail -50
        exit 1
    fi
    
    # Install Docker buildx
    log "Installing Docker buildx..."
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -L "https://github.com/docker/buildx/releases/download/v0.11.2/buildx-v0.11.2.linux-amd64" \
        -o /usr/local/lib/docker/cli-plugins/docker-buildx
    chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
    
    # Create default buildx builder
    docker buildx create --name runner-builder --use || log "Buildx builder already exists"
    docker buildx inspect --bootstrap || log "Failed to bootstrap buildx"
}

# Create runner user
create_runner_user() {
    if ! id "$RUNNER_USER" &>/dev/null; then
        log "Creating runner user..."
        useradd -m -s /bin/bash $RUNNER_USER
        usermod -aG docker $RUNNER_USER
    else
        log "Runner user exists, adding to docker group..."
        usermod -aG docker $RUNNER_USER
    fi
}

# Get GitHub token from Secret Manager
get_github_token() {
    log "Retrieving GitHub token from Secret Manager..."
    TOKEN=$(gcloud secrets versions access latest --secret="github-runner-token" --project="$PROJECT_ID")
    if [ -z "$TOKEN" ]; then
        log "ERROR: Failed to retrieve GitHub token"
        exit 1
    fi
    echo "$TOKEN"
}

# Get runner registration token
get_registration_token() {
    local github_token=$1
    log "Getting runner registration token..."
    
    # Add retry logic
    local max_retries=3
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        if [ -n "$GITHUB_REPO" ]; then
            # Repository runner
            RESPONSE=$(curl -sX POST \
                -H "Authorization: token $github_token" \
                -H "Accept: application/vnd.github.v3+json" \
                "https://api.github.com/repos/$GITHUB_ORG/$GITHUB_REPO/actions/runners/registration-token")
        else
            # Organization runner
            RESPONSE=$(curl -sX POST \
                -H "Authorization: token $github_token" \
                -H "Accept: application/vnd.github.v3+json" \
                "https://api.github.com/orgs/$GITHUB_ORG/actions/runners/registration-token")
        fi
        
        REG_TOKEN=$(echo "$RESPONSE" | jq -r .token)
        if [ "$REG_TOKEN" != "null" ] && [ -n "$REG_TOKEN" ]; then
            log "Successfully obtained registration token"
            echo "$REG_TOKEN"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        log "Attempt $retry_count failed. Response: $RESPONSE"
        [ $retry_count -lt $max_retries ] && sleep 5
    done
    
    log "ERROR: Failed to get registration token after $max_retries attempts"
    exit 1
}

# Download and install runner
install_runner() {
    log "Installing GitHub Actions runner..."
    
    # Download runner
    su - $RUNNER_USER -c "
        mkdir -p $RUNNER_DIR
        cd $RUNNER_DIR
        curl -o actions-runner-linux-x64-$RUNNER_VERSION.tar.gz -L \
            https://github.com/actions/runner/releases/download/v$RUNNER_VERSION/actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
        tar xzf actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
        rm actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
    "
}

# Configure runner
configure_runner() {
    local reg_token=$1
    log "Configuring runner..."
    
    # Determine URL
    if [ -n "$GITHUB_REPO" ]; then
        RUNNER_URL="https://github.com/$GITHUB_ORG/$GITHUB_REPO"
    else
        RUNNER_URL="https://github.com/$GITHUB_ORG"
    fi
    
    # Configure runner
    CONFIG_CMD="./config.sh --url $RUNNER_URL --token $reg_token --name $RUNNER_NAME-$(hostname) --unattended --replace"
    
    if [ -n "$RUNNER_LABELS" ]; then
        CONFIG_CMD="$CONFIG_CMD --labels $RUNNER_LABELS"
    fi
    
    if [ -n "$RUNNER_GROUP" ]; then
        CONFIG_CMD="$CONFIG_CMD --runnergroup $RUNNER_GROUP"
    fi
    
    su - $RUNNER_USER -c "cd $RUNNER_DIR && $CONFIG_CMD"
}

# Install runner as service
install_service() {
    log "Installing runner as service..."
    
    # Ensure Docker is accessible before starting runner
    log "Verifying Docker access for runner user..."
    su - $RUNNER_USER -c "docker version" || {
        log "Docker not accessible, fixing permissions..."
        systemctl restart docker
        sleep 5
        # Force group membership update
        newgrp docker || true
    }
    
    cd $RUNNER_DIR
    ./svc.sh install $RUNNER_USER
    ./svc.sh start
    
    # Enable service to start on boot
    systemctl enable actions.runner.*
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Install monitoring agent
    curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
    bash add-google-cloud-ops-agent-repo.sh --also-install
    
    # Configure logging
    cat > /etc/google-cloud-ops-agent/config.yaml <<EOF
logging:
  receivers:
    syslog:
      type: files
      include_paths:
      - /var/log/syslog
      - /var/log/messages
    github_runner:
      type: files
      include_paths:
      - $RUNNER_DIR/_diag/*.log
  processors:
    parse_json:
      type: parse_json
  service:
    pipelines:
      default_pipeline:
        receivers: [syslog, github_runner]
        processors: [parse_json]
metrics:
  receivers:
    hostmetrics:
      type: hostmetrics
      collection_interval: 60s
  service:
    pipelines:
      default_pipeline:
        receivers: [hostmetrics]
EOF
    
    # Restart monitoring agent
    systemctl restart google-cloud-ops-agent
}

# Setup auto-update
setup_auto_update() {
    log "Setting up auto-update..."
    
    cat > /etc/cron.daily/update-runner <<EOF
#!/bin/bash
apt-get update
apt-get upgrade -y
systemctl restart actions.runner.*
EOF
    
    chmod +x /etc/cron.daily/update-runner
}

# Cleanup function for removal token
cleanup_runner() {
    log "Setting up cleanup hook..."
    
    cat > /usr/local/bin/cleanup-runner.sh <<EOF
#!/bin/bash
GITHUB_TOKEN=\$(gcloud secrets versions access latest --secret="github-runner-token" --project="$PROJECT_ID")

if [ -n "$GITHUB_REPO" ]; then
    REMOVE_TOKEN=\$(curl -sX POST \\
        -H "Authorization: token \$GITHUB_TOKEN" \\
        -H "Accept: application/vnd.github.v3+json" \\
        "https://api.github.com/repos/$GITHUB_ORG/$GITHUB_REPO/actions/runners/remove-token" | jq -r .token)
else
    REMOVE_TOKEN=\$(curl -sX POST \\
        -H "Authorization: token \$GITHUB_TOKEN" \\
        -H "Accept: application/vnd.github.v3+json" \\
        "https://api.github.com/orgs/$GITHUB_ORG/actions/runners/remove-token" | jq -r .token)
fi

if [ -n "\$REMOVE_TOKEN" ] && [ "\$REMOVE_TOKEN" != "null" ]; then
    cd $RUNNER_DIR
    ./config.sh remove --token \$REMOVE_TOKEN
fi
EOF
    
    chmod +x /usr/local/bin/cleanup-runner.sh
    
    # Add shutdown script
    cat > /etc/systemd/system/cleanup-runner.service <<EOF
[Unit]
Description=Cleanup GitHub Runner on shutdown
DefaultDependencies=no
Before=shutdown.target reboot.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/cleanup-runner.sh
TimeoutStartSec=0

[Install]
WantedBy=shutdown.target reboot.target
EOF
    
    systemctl enable cleanup-runner.service
}

# Main installation flow
main() {
    log "Starting GitHub Actions runner installation..."
    log "Script version: Enhanced with Docker fixes"
    
    # Trap errors to log them
    trap 'log "ERROR: Script failed at line $LINENO"' ERR
    
    # Step 1: Install dependencies
    install_dependencies || { log "ERROR: Failed to install dependencies"; exit 1; }
    
    # Step 2: Create runner user
    create_runner_user || { log "ERROR: Failed to create runner user"; exit 1; }
    
    # Step 3: Verify Docker is accessible by runner user
    log "Verifying Docker access for runner user..."
    if ! su - $RUNNER_USER -c "docker version" &>/dev/null; then
        log "Fixing Docker permissions for runner user..."
        # Force group reload
        systemctl restart docker
        sleep 3
        # Try again
        if ! su - $RUNNER_USER -c "docker version" &>/dev/null; then
            log "WARNING: Runner user still cannot access Docker"
        fi
    fi
    
    # Step 4: Get GitHub tokens
    log "Getting GitHub tokens..."
    GITHUB_TOKEN=$(get_github_token) || { log "ERROR: Failed to get GitHub token"; exit 1; }
    REG_TOKEN=$(get_registration_token "$GITHUB_TOKEN") || { log "ERROR: Failed to get registration token"; exit 1; }
    
    # Step 5: Install and configure runner
    install_runner || { log "ERROR: Failed to install runner"; exit 1; }
    configure_runner "$REG_TOKEN" || { log "ERROR: Failed to configure runner"; exit 1; }
    
    # Step 6: Install as service
    install_service || { log "ERROR: Failed to install service"; exit 1; }
    
    # Step 7: Setup additional features
    setup_monitoring || log "WARNING: Failed to setup monitoring"
    setup_auto_update || log "WARNING: Failed to setup auto-update"
    cleanup_runner || log "WARNING: Failed to setup cleanup"
    
    # Final verification
    log "Performing final verification..."
    if systemctl is-active --quiet actions.runner.*; then
        log "✓ GitHub Actions runner is running"
    else
        log "✗ GitHub Actions runner is not running"
        systemctl status actions.runner.* --no-pager || true
    fi
    
    if su - $RUNNER_USER -c "docker version" &>/dev/null; then
        log "✓ Docker is accessible by runner user"
    else
        log "✗ Docker is not accessible by runner user"
    fi
    
    log "GitHub Actions runner installation completed!"
    log "Check /var/log/github-runner-install.log for details"
}

# Run main function
main