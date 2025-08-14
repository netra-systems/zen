# Single GitHub Runner Instance with Docker Fixes
# This creates one new runner instance with all fixes preloaded

resource "google_compute_instance" "github_runner_fixed" {
  name         = "${var.runner_name}-fixed-${formatdate("YYYYMMDD-hhmmss", timestamp())}"
  machine_type = var.machine_type
  zone         = var.zone

  tags = ["github-runner", "docker-fixed"]

  boot_disk {
    initialize_params {
      image = var.boot_disk_image
      size  = var.boot_disk_size
      type  = var.boot_disk_type
    }
  }

  network_interface {
    network = "default"
    
    access_config {
      # Ephemeral public IP
    }
  }

  service_account {
    email  = google_service_account.github_runner.email
    scopes = ["cloud-platform"]
  }

  # Combined startup script with all fixes
  metadata_startup_script = <<-EOT
#!/bin/bash
set -e

# Comprehensive startup script with Docker fixes
LOG_FILE="/var/log/github-runner-install.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Variables
GITHUB_ORG="${var.github_org}"
GITHUB_REPO="${var.github_repo}"
RUNNER_NAME="${var.runner_name}"
RUNNER_LABELS="${join(",", var.runner_labels)}"
RUNNER_GROUP="${var.runner_group}"
PROJECT_ID="${var.project_id}"
RUNNER_VERSION="${var.runner_version}"
RUNNER_USER="runner"
RUNNER_HOME="/home/$RUNNER_USER"
RUNNER_DIR="$RUNNER_HOME/actions-runner"

log "Starting enhanced GitHub runner installation with Docker fixes..."

# Step 1: Install all dependencies with retry logic
install_dependencies() {
    log "Installing dependencies..."
    
    # Update package lists
    apt-get update || { log "ERROR: apt-get update failed"; exit 1; }
    
    # Install basic packages
    PACKAGES="curl jq git build-essential libssl-dev libffi-dev python3 python3-venv python3-dev python3-pip"
    for pkg in $PACKAGES; do
        log "Installing $pkg..."
        apt-get install -y $pkg || log "WARNING: Failed to install $pkg"
    done
    
    # Install Docker with special handling
    log "Installing Docker..."
    apt-get install -y docker.io docker-compose || {
        log "First Docker install attempt failed, retrying..."
        apt-get update
        apt-get install -y --fix-missing docker.io docker-compose
    }
    
    # Setup Docker daemon properly
    log "Configuring Docker daemon..."
    systemctl daemon-reload
    systemctl enable docker
    systemctl stop docker || true
    
    # Clean any stale Docker files
    rm -f /var/run/docker.pid
    rm -f /var/run/docker.sock
    
    # Start Docker
    systemctl start docker
    
    # Wait for Docker to be ready
    log "Waiting for Docker daemon..."
    local max_wait=60
    local count=0
    while [ $count -lt $max_wait ]; do
        if docker version &>/dev/null; then
            log "Docker daemon is ready"
            break
        fi
        sleep 2
        count=$((count + 1))
        [ $((count % 10)) -eq 0 ] && log "Still waiting for Docker... ($count/$max_wait)"
    done
    
    if [ $count -eq $max_wait ]; then
        log "ERROR: Docker failed to start"
        systemctl status docker --no-pager
        exit 1
    fi
    
    # Install Docker buildx
    log "Installing Docker buildx..."
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -L "https://github.com/docker/buildx/releases/download/v0.11.2/buildx-v0.11.2.linux-amd64" \
        -o /usr/local/lib/docker/cli-plugins/docker-buildx
    chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
    
    # Create buildx builder
    docker buildx create --name runner-builder --use --bootstrap || {
        log "Buildx builder exists, using it"
        docker buildx use runner-builder
    }
    
    log "Dependencies installed successfully"
}

# Step 2: Create and configure runner user
create_runner_user() {
    log "Creating runner user..."
    
    if ! id "$RUNNER_USER" &>/dev/null; then
        useradd -m -s /bin/bash $RUNNER_USER
    fi
    
    # Add to docker group
    usermod -aG docker $RUNNER_USER
    
    # Fix Docker permissions
    chgrp docker /var/run/docker.sock || true
    chmod 660 /var/run/docker.sock || true
    
    # Verify Docker access
    log "Verifying runner Docker access..."
    systemctl restart docker
    sleep 5
    
    if su - $RUNNER_USER -c "docker version" &>/dev/null; then
        log "Runner user has Docker access"
    else
        log "WARNING: Runner user Docker access needs fixing"
        chmod 666 /var/run/docker.sock
    fi
}

# Step 3: Get GitHub token from Secret Manager
get_github_token() {
    log "Retrieving GitHub token..."
    local token=$(gcloud secrets versions access latest --secret="github-runner-token" --project="$PROJECT_ID" 2>/dev/null)
    if [ -z "$token" ]; then
        log "ERROR: Failed to retrieve GitHub token"
        exit 1
    fi
    echo "$token"
}

# Step 4: Get registration token
get_registration_token() {
    local github_token=$1
    log "Getting runner registration token..."
    
    local max_retries=5
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        if [ -n "$GITHUB_REPO" ]; then
            RESPONSE=$(curl -sX POST \
                -H "Authorization: token $github_token" \
                -H "Accept: application/vnd.github.v3+json" \
                "https://api.github.com/repos/$GITHUB_ORG/$GITHUB_REPO/actions/runners/registration-token")
        else
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
    
    log "ERROR: Failed to get registration token"
    exit 1
}

# Step 5: Install GitHub runner
install_runner() {
    log "Installing GitHub runner..."
    
    su - $RUNNER_USER -c "
        mkdir -p $RUNNER_DIR
        cd $RUNNER_DIR
        curl -o actions-runner-linux-x64-$RUNNER_VERSION.tar.gz -L \
            https://github.com/actions/runner/releases/download/v$RUNNER_VERSION/actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
        tar xzf actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
        rm actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
    "
}

# Step 6: Configure runner
configure_runner() {
    local reg_token=$1
    log "Configuring runner..."
    
    if [ -n "$GITHUB_REPO" ]; then
        RUNNER_URL="https://github.com/$GITHUB_ORG/$GITHUB_REPO"
    else
        RUNNER_URL="https://github.com/$GITHUB_ORG"
    fi
    
    CONFIG_CMD="./config.sh --url $RUNNER_URL --token $reg_token --name $RUNNER_NAME-$(hostname) --unattended --replace"
    
    if [ -n "$RUNNER_LABELS" ]; then
        CONFIG_CMD="$CONFIG_CMD --labels $RUNNER_LABELS"
    fi
    
    if [ -n "$RUNNER_GROUP" ]; then
        CONFIG_CMD="$CONFIG_CMD --runnergroup $RUNNER_GROUP"
    fi
    
    su - $RUNNER_USER -c "cd $RUNNER_DIR && $CONFIG_CMD"
}

# Step 7: Install as service with Docker verification
install_service() {
    log "Installing runner as service..."
    
    # Final Docker check before starting service
    log "Final Docker verification..."
    if ! su - $RUNNER_USER -c "docker version" &>/dev/null; then
        log "Applying final Docker fixes..."
        systemctl restart docker
        chmod 666 /var/run/docker.sock
        sleep 5
    fi
    
    # Verify buildx for runner
    su - $RUNNER_USER -c "docker buildx ls" || {
        log "Setting up buildx for runner..."
        su - $RUNNER_USER -c "docker buildx create --name runner-builder --use" || true
    }
    
    cd $RUNNER_DIR
    ./svc.sh install $RUNNER_USER
    ./svc.sh start
    
    systemctl enable actions.runner.*
}

# Step 8: Setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
    bash add-google-cloud-ops-agent-repo.sh --also-install || log "Monitoring agent install failed"
    
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
    
    systemctl restart google-cloud-ops-agent || true
}

# Main execution
main() {
    log "==================================================="
    log "Enhanced GitHub Runner Installation - Docker Fixed"
    log "==================================================="
    
    install_dependencies
    create_runner_user
    
    GITHUB_TOKEN=$(get_github_token)
    REG_TOKEN=$(get_registration_token "$GITHUB_TOKEN")
    
    install_runner
    configure_runner "$REG_TOKEN"
    install_service
    setup_monitoring
    
    # Final verification
    log "==================================================="
    log "Installation Complete - Verifying..."
    
    if systemctl is-active --quiet actions.runner.*; then
        log "✓ GitHub runner service is running"
    else
        log "✗ GitHub runner service failed to start"
        systemctl status actions.runner.* --no-pager
    fi
    
    if su - $RUNNER_USER -c "docker version" &>/dev/null; then
        log "✓ Docker is accessible by runner"
    else
        log "✗ Docker access issue detected"
    fi
    
    if su - $RUNNER_USER -c "docker buildx version" &>/dev/null; then
        log "✓ Docker buildx is available"
    else
        log "✗ Docker buildx not available"
    fi
    
    log "==================================================="
    log "GitHub runner installation completed!"
    log "Instance: $(hostname)"
    log "Logs: $LOG_FILE"
}

# Run main
main
EOT

  metadata = {
    enable-oslogin = "TRUE"
    github-org     = var.github_org
    github-repo    = var.github_repo
    runner-type    = "docker-fixed"
  }

  scheduling {
    preemptible       = var.use_preemptible
    automatic_restart = !var.use_preemptible
    on_host_maintenance = var.use_preemptible ? "TERMINATE" : "MIGRATE"
  }

  labels = {
    environment = var.environment
    purpose     = "github-runner"
    managed-by  = "terraform"
    docker-fix  = "applied"
  }

  depends_on = [
    google_project_service.compute,
    google_secret_manager_secret_version.github_token,
    google_secret_manager_secret_iam_member.github_token_access
  ]
}

# Output the instance details
output "fixed_runner_instance" {
  value = {
    name       = google_compute_instance.github_runner_fixed.name
    ip         = google_compute_instance.github_runner_fixed.network_interface[0].access_config[0].nat_ip
    self_link  = google_compute_instance.github_runner_fixed.self_link
    status     = google_compute_instance.github_runner_fixed.current_status
  }
  description = "Details of the newly created runner instance with Docker fixes"
}