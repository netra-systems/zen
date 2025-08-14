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
  # Using chomp and replace to ensure Unix line endings
  metadata_startup_script = replace(chomp(<<-EOT
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

# Step 1: Install all dependencies (Docker is optional)
install_dependencies() {
    log "Installing dependencies..."
    
    # Update package lists
    apt-get update || log "WARNING: apt-get update failed, continuing..."
    
    # Install basic packages
    PACKAGES="curl jq git build-essential libssl-dev libffi-dev python3 python3-venv python3-dev python3-pip"
    for pkg in $PACKAGES; do
        log "Installing $pkg..."
        apt-get install -y $pkg || log "WARNING: Failed to install $pkg"
    done
    
    # Try to install Docker (non-critical)
    log "Attempting to install Docker (optional)..."
    
    install_docker() {
        # Install prerequisites
        apt-get install -y \
            ca-certificates \
            gnupg \
            lsb-release || return 1
        
        # Add Docker's official GPG key
        mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg || return 1
        
        # Set up the repository
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
          $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        
        # Update and install Docker
        apt-get update
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin || {
            log "Failed to install Docker CE, trying docker.io..."
            apt-get install -y docker.io docker-compose || return 1
        }
        return 0
    }
    
    if install_docker; then
        log "Docker installation successful"
    else
        log "WARNING: Docker installation failed, runner will work without Docker support"
        return 0  # Don't fail the entire script
    fi
    
    # Only configure Docker if it was installed
    if command -v docker &>/dev/null; then
        log "Configuring Docker daemon..."
        systemctl daemon-reload
        systemctl enable docker || true
        systemctl stop docker || true
        
        # Clean any stale Docker files
        rm -f /var/run/docker.pid
        rm -f /var/run/docker.sock
        
        # Start Docker with proper initialization sequence
        log "Starting Docker services..."
        
        # Ensure containerd is running first
        if systemctl list-units --all | grep -q containerd; then
            systemctl start containerd || true
            sleep 2
        fi
        
        # Start Docker daemon
        systemctl start docker || {
            log "Initial Docker start failed, retrying with cleanup..."
            rm -f /var/run/docker.pid /var/run/docker.sock
            systemctl daemon-reload
            systemctl start docker || log "WARNING: Docker failed to start"
        }
    
    # Wait for Docker to be ready
    log "Waiting for Docker daemon to be fully ready..."
    local max_wait=90
    local count=0
    local docker_ready=false
    
    while [ $count -lt $max_wait ]; do
        # Check if Docker socket exists
        if [ -S /var/run/docker.sock ]; then
            # Try to run a simple Docker command
            if docker version &>/dev/null 2>&1; then
                log "Docker API is responding"
                # Final verification with actual container run
                if docker run --rm hello-world &>/dev/null 2>&1; then
                    log "Docker daemon is fully operational"
                    docker_ready=true
                    break
                else
                    log "Docker API responds but cannot run containers yet"
                fi
            fi
        fi
        
        # Check service status
        if [ $((count % 15)) -eq 0 ] && [ $count -gt 0 ]; then
            log "Docker service status check..."
            if systemctl is-active --quiet docker; then
                log "Docker service is active, waiting for full initialization..."
                # Try restarting docker socket
                systemctl restart docker.socket 2>/dev/null || true
            else
                log "Docker service not active, attempting restart..."
                systemctl restart docker
            fi
        fi
        
        sleep 2
        count=$((count + 1))
        [ $((count % 10)) -eq 0 ] && log "Still waiting for Docker... ($count/$max_wait)"
    done
    
    if [ "$docker_ready" != "true" ]; then
        log "WARNING: Docker not fully ready after $max_wait seconds"
        systemctl status docker --no-pager
        
        # Final attempt - full Docker restart
        log "Attempting final Docker restart..."
        systemctl stop docker
        sleep 2
        rm -f /var/run/docker.pid /var/run/docker.sock
        systemctl start docker
        sleep 10
        
        if docker run --rm hello-world &>/dev/null 2>&1; then
            log "Docker is now working after final restart"
            docker_ready=true
        else
            log "WARNING: Docker still having issues, continuing with installation"
            log "Manual intervention may be required"
        fi
    fi
    
    # Install Docker buildx plugin
    log "Installing Docker buildx plugin..."
    mkdir -p /usr/local/lib/docker/cli-plugins
    BUILDX_VERSION="0.11.2"
    curl -L "https://github.com/docker/buildx/releases/download/v$${BUILDX_VERSION}/buildx-v$${BUILDX_VERSION}.linux-amd64" \
        -o /usr/local/lib/docker/cli-plugins/docker-buildx
    chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
    
    # Create symlink for all users
    ln -sf /usr/local/lib/docker/cli-plugins/docker-buildx /usr/libexec/docker/cli-plugins/docker-buildx 2>/dev/null || true
    
    # Verify Docker is fully operational before creating buildx builder
    log "Verifying Docker readiness before buildx setup..."
    if docker run --rm hello-world &>/dev/null; then
        log "Docker confirmed working with hello-world test"
        
        # Setup buildx with proper initialization
        log "Setting up Docker buildx..."
        
        # Remove any existing builders first
        docker buildx rm runner-builder 2>/dev/null || true
        docker buildx rm default 2>/dev/null || true
        
        # Create new builder with retry logic
        local buildx_retries=3
        local buildx_success=false
        
        for i in $(seq 1 $buildx_retries); do
            log "Attempting to create buildx builder (attempt $i/$buildx_retries)..."
            
            if docker buildx create --name runner-builder --driver docker-container --use; then
                # Bootstrap the builder to ensure it's ready
                if docker buildx inspect runner-builder --bootstrap; then
                    log "Buildx builder created and bootstrapped successfully"
                    buildx_success=true
                    break
                else
                    log "Builder created but bootstrap failed, retrying..."
                    docker buildx rm runner-builder 2>/dev/null || true
                fi
            fi
            
            [ $i -lt $buildx_retries ] && sleep 5
        done
        
        if [ "$buildx_success" != "true" ]; then
            log "WARNING: Could not fully setup buildx builder, will be configured later"
            # Use default builder as fallback
            docker buildx use default 2>/dev/null || true
        fi
    else
        log "WARNING: Docker not fully ready, skipping buildx builder creation"
    fi
    
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
    
    # Setup buildx for runner user with proper error handling
    log "Setting up Docker buildx for runner user..."
    
    # First ensure buildx is available to runner user
    if ! su - $RUNNER_USER -c "docker buildx version" &>/dev/null; then
        log "Installing buildx for runner user..."
        mkdir -p $RUNNER_HOME/.docker/cli-plugins
        cp /usr/local/lib/docker/cli-plugins/docker-buildx $RUNNER_HOME/.docker/cli-plugins/
        chown -R $RUNNER_USER:$RUNNER_USER $RUNNER_HOME/.docker
        chmod +x $RUNNER_HOME/.docker/cli-plugins/docker-buildx
    fi
    
    # Setup buildx builder for runner
    if su - $RUNNER_USER -c "docker buildx version" &>/dev/null; then
        log "Docker buildx is accessible by runner"
        
        # Check and setup builder
        if su - $RUNNER_USER -c "docker buildx ls | grep -q runner-builder" 2>/dev/null; then
            log "Using existing runner-builder"
            su - $RUNNER_USER -c "docker buildx use runner-builder" 2>/dev/null || {
                log "Could not use existing builder, recreating..."
                su - $RUNNER_USER -c "docker buildx rm runner-builder" 2>/dev/null || true
                su - $RUNNER_USER -c "docker buildx create --name runner-builder --driver docker-container --use" 2>/dev/null || true
            }
        else
            log "Creating buildx builder for runner user..."
            su - $RUNNER_USER -c "docker buildx create --name runner-builder --driver docker-container --use" 2>/dev/null || {
                log "WARNING: Buildx builder creation failed, using default"
                su - $RUNNER_USER -c "docker buildx use default" 2>/dev/null || true
            }
        fi
        
        # Verify builder is working
        if su - $RUNNER_USER -c "docker buildx inspect --bootstrap" &>/dev/null; then
            log "Buildx builder verified and ready"
        else
            log "WARNING: Buildx builder may need manual configuration"
        fi
    else
        log "WARNING: Docker buildx still not accessible by runner user"
    fi
    
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
    log "GitHub Runner Installation with Docker Support"
    log "==================================================="
    
    # Install GitHub runner first
    log "Phase 1: Installing GitHub Runner..."
    
    # Create runner user first
    log "Creating runner user..."
    if ! id "$RUNNER_USER" &>/dev/null; then
        useradd -m -s /bin/bash $RUNNER_USER
    fi
    
    # Get tokens and install runner
    GITHUB_TOKEN=$(get_github_token)
    REG_TOKEN=$(get_registration_token "$GITHUB_TOKEN")
    
    install_runner
    configure_runner "$REG_TOKEN"
    
    # Install dependencies including Docker (non-critical)
    log "Phase 2: Installing Docker and dependencies (non-critical)..."
    install_dependencies || log "WARNING: Some dependencies failed to install, continuing..."
    
    # Update runner user for Docker if available
    if command -v docker &>/dev/null; then
        usermod -aG docker $RUNNER_USER || true
        chmod 666 /var/run/docker.sock 2>/dev/null || true
    fi
    
    # Install runner service
    install_service
    
    # Setup monitoring (optional)
    setup_monitoring || log "WARNING: Monitoring setup failed, continuing..."
    
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
  ), "\r\n", "\n")

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