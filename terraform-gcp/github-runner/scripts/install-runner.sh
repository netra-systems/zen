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

# Logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Install dependencies
install_dependencies() {
    log "Installing dependencies..."
    apt-get update
    apt-get install -y \
        curl \
        jq \
        git \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3 \
        python3-venv \
        python3-dev \
        python3-pip \
        docker.io \
        docker-compose
    
    # Enable Docker
    systemctl enable docker
    systemctl start docker
}

# Create runner user
create_runner_user() {
    if ! id "$RUNNER_USER" &>/dev/null; then
        log "Creating runner user..."
        useradd -m -s /bin/bash $RUNNER_USER
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
    if [ "$REG_TOKEN" == "null" ] || [ -z "$REG_TOKEN" ]; then
        log "ERROR: Failed to get registration token"
        log "Response: $RESPONSE"
        exit 1
    fi
    echo "$REG_TOKEN"
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
    
    install_dependencies
    create_runner_user
    
    GITHUB_TOKEN=$(get_github_token)
    REG_TOKEN=$(get_registration_token "$GITHUB_TOKEN")
    
    install_runner
    configure_runner "$REG_TOKEN"
    install_service
    setup_monitoring
    setup_auto_update
    cleanup_runner
    
    log "GitHub Actions runner installation completed successfully!"
    log "Runner status:"
    systemctl status actions.runner.* --no-pager || true
}

# Run main function
main