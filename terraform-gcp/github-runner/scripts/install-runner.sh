#!/bin/bash
# Enhanced GitHub Actions self-hosted runner installation script with comprehensive error handling
# Version: 2.0 - Fixes Docker permissions, resource constraints, and improves error recovery

# Exit immediately if a command exits with a non-zero status.
set -e
# Treat unset variables as an error when substituting.
set -u
# Pipelines return the exit status of the last command to exit with a non-zero status,
# or zero if no command exited with a non-zero status.
set -o pipefail

# Enable debug mode if DEBUG environment variable is set
[[ "${DEBUG:-}" == "true" ]] && set -x

# --- Configuration Variables ---
# These variables are expected to be templated by a tool like Terraform.
GITHUB_ORG="${github_org}"
GITHUB_REPO="${github_repo}"
RUNNER_NAME="${runner_name}"
RUNNER_LABELS="${runner_labels}"
RUNNER_GROUP="${runner_group}"
PROJECT_ID="${project_id}"
RUNNER_VERSION="${runner_version:-"2.317.0"}" # Default version if not provided

# --- Script Variables ---
RUNNER_USER="runner"
RUNNER_HOME="/home/$RUNNER_USER"
RUNNER_DIR="$RUNNER_HOME/actions-runner"
LOG_FILE="/var/log/github-runner-install.log"
ERROR_LOG="/var/log/github-runner-errors.log"
DOCKER_REQUIRED="${DOCKER_REQUIRED:-false}"
MAX_RETRIES=5
RETRY_DELAY=10

# --- Logging Setup ---
# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$ERROR_LOG")"

# Redirect stdout and stderr to log files and console
exec > >(tee -a "$LOG_FILE") 2> >(tee -a "$ERROR_LOG" >&2)

# --- Helper Functions ---

# Log messages with a timestamp.
log() {
    # Note: Ensure this is a standard space, not a non-breaking space.
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Enhanced error handler with detailed diagnostics
error_handler() {
    local exit_code=$?
    local line_no=$1
    local bash_lineno=$2
    local last_command=$3
    
    log "ERROR: Script failed at line $line_no (BASH_LINENO: $bash_lineno)"
    log "ERROR: Exit code: $exit_code"
    log "ERROR: Failed command: $last_command"
    log "ERROR: Call stack:"
    
    local frame=0
    while caller $frame; do
        ((frame++))
    done
    
    # Collect diagnostic information
    log "ERROR: System diagnostics:"
    log "  - Memory: $(free -h 2>/dev/null | grep Mem: || echo 'Unable to get memory info')"
    log "  - Disk: $(df -h / 2>/dev/null | tail -1 || echo 'Unable to get disk info')"
    log "  - Docker status: $(systemctl is-active docker 2>/dev/null || echo 'not running')"
    
    # Save full error context
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Full error context:" >> "$ERROR_LOG"
    echo "Line: $line_no, Exit: $exit_code, Command: $last_command" >> "$ERROR_LOG"
    
    exit $exit_code
}

trap 'error_handler $LINENO ${BASH_LINENO[0]} "$BASH_COMMAND"' ERR

# Check system requirements
check_system_requirements() {
    log "Checking system requirements..."
    
    # Check root privileges
    if [[ "$EUID" -ne 0 ]]; then
        log "ERROR: This script must be run as root."
        exit 1
    fi
    
    # Check minimum memory (2GB recommended)
    local total_mem=$(free -b | awk '/^Mem:/{print $2}')
    local min_mem=$((2 * 1024 * 1024 * 1024)) # 2GB in bytes
    
    if [[ $total_mem -lt $min_mem ]]; then
        log "WARNING: System has less than 2GB RAM. Runner may experience issues."
        log "  Current memory: $(free -h | grep Mem:)"
    fi
    
    # Check disk space (10GB recommended)
    local available_space=$(df / | awk 'NR==2 {print $4}')
    local min_space=$((10 * 1024 * 1024)) # 10GB in KB
    
    if [[ $available_space -lt $min_space ]]; then
        log "WARNING: Less than 10GB disk space available."
        log "  Current disk usage: $(df -h /)"
    fi
    
    # Check CPU count
    local cpu_count=$(nproc)
    if [[ $cpu_count -lt 2 ]]; then
        log "WARNING: System has only $cpu_count CPU(s). Performance may be limited."
    fi
    
    log "System requirements check completed."
}

# Install all necessary system dependencies with better error handling
install_dependencies() {
    log "Installing system dependencies..."
    
    # Update package lists with retry
    local retry_count=0
    while [[ $retry_count -lt $MAX_RETRIES ]]; do
        if apt-get update; then
            log "Package lists updated successfully."
            break
        fi
        retry_count=$((retry_count + 1))
        log "Package update failed (attempt $retry_count/$MAX_RETRIES). Retrying..."
        sleep $RETRY_DELAY
    done
    
    # Essential packages (required)
    local ESSENTIAL_PACKAGES="curl jq git"
    log "Installing essential packages: $ESSENTIAL_PACKAGES"
    apt-get install -y --no-install-recommends $ESSENTIAL_PACKAGES || {
        log "ERROR: Failed to install essential packages."
        exit 1
    }
    
    # Development packages (recommended)
    local DEV_PACKAGES="build-essential libssl-dev libffi-dev python3 python3-venv python3-dev python3-pip"
    log "Installing development packages: $DEV_PACKAGES"
    apt-get install -y --no-install-recommends $DEV_PACKAGES || {
        log "WARNING: Some development packages failed to install. Continuing..."
    }
    
    # Docker installation (optional but recommended)
    install_docker_properly

}

# Separate function for Docker installation with proper error handling
install_docker_properly() {
    log "Attempting Docker installation..."
    
    # Check if Docker is already installed
    if command -v docker &>/dev/null; then
        log "Docker is already installed."
        fix_docker_permissions
        return 0
    fi
    
    # Try to install Docker CE (preferred)
    if install_docker_ce; then
        log "Docker CE installed successfully."
    elif install_docker_io; then
        log "Docker.io installed successfully."
    else
        if [[ "$DOCKER_REQUIRED" == "true" ]]; then
            log "ERROR: Docker installation failed and DOCKER_REQUIRED is true."
            exit 1
        else
            log "WARNING: Docker installation failed. Runner will work without Docker support."
            return 1
        fi
    fi
    
    fix_docker_permissions
    verify_docker_installation
}

install_docker_ce() {
    log "Installing Docker CE..."
    
    # Install prerequisites
    apt-get install -y ca-certificates gnupg lsb-release || return 1
    
    # Add Docker's official GPG key
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /etc/apt/keyrings/docker.gpg || return 1
    
    # Set up repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Update and install
    apt-get update || return 1
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin || return 1
    
    return 0
}

install_docker_io() {
    log "Installing Docker.io (fallback)..."
    apt-get install -y docker.io docker-compose || return 1
    return 0
}

fix_docker_permissions() {
    log "Fixing Docker permissions..."
    
    # Ensure Docker group exists
    groupadd docker 2>/dev/null || true
    
    # Fix socket permissions
    if [[ -S /var/run/docker.sock ]]; then
        chmod 666 /var/run/docker.sock || {
            log "WARNING: Could not set Docker socket permissions."
        }
    fi
    
    # Enable and start Docker
    systemctl daemon-reload
    systemctl enable docker || true
    
    # Clean stale files
    rm -f /var/run/docker.pid 2>/dev/null || true
    
    # Start Docker with retries
    local retry_count=0
    while [[ $retry_count -lt $MAX_RETRIES ]]; do
        if systemctl start docker; then
            log "Docker service started successfully."
            break
        fi
        retry_count=$((retry_count + 1))
        log "Docker start failed (attempt $retry_count/$MAX_RETRIES). Cleaning and retrying..."
        
        # Clean and retry
        systemctl stop docker 2>/dev/null || true
        rm -f /var/run/docker.sock /var/run/docker.pid 2>/dev/null || true
        sleep $RETRY_DELAY
    done
}

verify_docker_installation() {
    log "Verifying Docker installation..."
    
    local max_wait=60
    local count=0
    
    while [[ $count -lt $max_wait ]]; do
        # Check if Docker daemon is responsive
        if docker version &>/dev/null; then
            log "Docker daemon is responsive."
            
            # Try to run hello-world
            if docker run --rm hello-world &>/dev/null; then
                log "Docker verified: Can run containers successfully."
                return 0
            else
                log "WARNING: Docker installed but cannot run containers."
            fi
            break
        fi
        
        count=$((count + 2))
        log "Waiting for Docker daemon... ($count/$max_wait seconds)"
        sleep 2
    done
    
    if [[ $count -ge $max_wait ]]; then
        log "WARNING: Docker daemon not responsive after $max_wait seconds."
        log "Docker status: $(systemctl is-active docker 2>/dev/null || echo 'unknown')"
        
        # Show Docker logs for debugging
        log "Recent Docker logs:"
        journalctl -u docker -n 20 --no-pager 2>/dev/null || true
    fi

    
    # Install buildx if Docker is working
    if docker version &>/dev/null; then
        install_docker_buildx
    fi
}

install_docker_buildx() {
    log "Installing Docker buildx plugin..."
    
    local buildx_version="0.11.2"
    local buildx_dir="/usr/local/lib/docker/cli-plugins"
    
    mkdir -p "$buildx_dir"
    
    if curl -fsSL "https://github.com/docker/buildx/releases/download/v${buildx_version}/buildx-v${buildx_version}.linux-amd64" \
        -o "$buildx_dir/docker-buildx"; then
        chmod +x "$buildx_dir/docker-buildx"
        log "Docker buildx plugin installed successfully."
        
        # Create symlink for compatibility
        mkdir -p /usr/libexec/docker/cli-plugins
        ln -sf "$buildx_dir/docker-buildx" /usr/libexec/docker/cli-plugins/docker-buildx 2>/dev/null || true
    else
        log "WARNING: Failed to install Docker buildx plugin."
    fi
}

# Create a dedicated user for running the GitHub Actions runner.
create_runner_user() {
    if ! id "$RUNNER_USER" &>/dev/null; then
        log "Creating runner user '$RUNNER_USER'..."
        
        # Try useradd first
        if ! useradd -m -s /bin/bash "$RUNNER_USER" 2>/dev/null; then
            # Fallback to adduser
            log "useradd failed, trying adduser..."
            adduser --disabled-password --gecos "" --shell /bin/bash "$RUNNER_USER" || {
                log "ERROR: Failed to create user '$RUNNER_USER'."
                exit 1
            }
        fi
    else
        log "Runner user '$RUNNER_USER' already exists."
    fi
    
    # Add to docker group if Docker is installed
    if command -v docker &>/dev/null; then
        log "Adding runner user to the 'docker' group..."
        usermod -aG docker "$RUNNER_USER" || {
            log "WARNING: Failed to add user to docker group."
        }
        
        # Force group membership to take effect
        newgrp docker 2>/dev/null || true
    fi
    
    # Verify user was created successfully
    if ! id "$RUNNER_USER" &>/dev/null; then
        log "ERROR: User '$RUNNER_USER' verification failed."
        exit 1
    fi
    
    log "User '$RUNNER_USER' setup completed."
}

# Retrieve the GitHub Personal Access Token (PAT) from Google Secret Manager.
get_github_pat() {
    log "Retrieving GitHub PAT from Secret Manager..."
    
    # Ensure gcloud is available
    if ! command -v gcloud &>/dev/null; then
        log "Installing Google Cloud SDK..."
        install_gcloud_sdk
    fi
    
    local token=""
    local retry_count=0
    
    while [[ $retry_count -lt $MAX_RETRIES ]]; do
        # Check if secret exists
        if gcloud secrets describe "github-runner-token" --project="$PROJECT_ID" &>/dev/null; then
            # Try to access the secret
            token=$(gcloud secrets versions access latest --secret="github-runner-token" --project="$PROJECT_ID" 2>&1)
            
            if [[ $? -eq 0 && -n "$token" && "$token" != *"ERROR"* ]]; then
                log "Successfully retrieved GitHub PAT."
                echo "$token"
                return 0
            else
                log "Failed to access secret (attempt $((retry_count + 1))/$MAX_RETRIES)."
                log "Response: ${token:0:100}..." # Log first 100 chars for debugging
            fi
        else
            log "Secret 'github-runner-token' not found (attempt $((retry_count + 1))/$MAX_RETRIES)."
        fi
        
        retry_count=$((retry_count + 1))
        if [[ $retry_count -lt $MAX_RETRIES ]]; then
            log "Waiting ${RETRY_DELAY} seconds before retry..."
            sleep $RETRY_DELAY
        fi
    done
    
    log "ERROR: Failed to retrieve GitHub PAT after $MAX_RETRIES attempts."
    log "Debug info:"
    log "  Project ID: $PROJECT_ID"
    log "  Service Account: $(gcloud config get-value account 2>/dev/null || echo 'unknown')"
    gcloud secrets list --project="$PROJECT_ID" 2>&1 | head -5 || true
    exit 1
}

install_gcloud_sdk() {
    log "Installing Google Cloud SDK..."
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | \
        tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
    
    apt-get install -y apt-transport-https ca-certificates gnupg
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
        apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
    
    apt-get update && apt-get install -y google-cloud-sdk
}

# Use the GitHub PAT to get a temporary runner registration token.
get_registration_token() {
    local github_pat="$1"
    local api_url
    local response
    local reg_token

    if [[ -n "$GITHUB_REPO" ]]; then
        log "Getting registration token for repo runner: $GITHUB_ORG/$GITHUB_REPO"
        api_url="https://api.github.com/repos/$GITHUB_ORG/$GITHUB_REPO/actions/runners/registration-token"
    else
        log "Getting registration token for organization runner: $GITHUB_ORG"
        api_url="https://api.github.com/orgs/$GITHUB_ORG/actions/runners/registration-token"
    fi

    response=$(curl -sS -X POST \
        -H "Authorization: token $github_pat" \
        -H "Accept: application/vnd.github.v3+json" \
        "$api_url")

    reg_token=$(echo "$response" | jq -r .token)

    if [[ "$reg_token" == "null" || -z "$reg_token" ]]; then
        log "ERROR: Failed to get registration token."
        log "API Response: $response"
        exit 1
    fi

    log "Successfully obtained registration token."
    echo "$reg_token"
}

# Download and extract the GitHub Actions runner software.
install_runner() {
    log "Downloading and installing GitHub Actions runner v$RUNNER_VERSION..."
    su - "$RUNNER_USER" -c "
        mkdir -p '$RUNNER_DIR'
        cd '$RUNNER_DIR'
        curl -sSL -o actions-runner.tar.gz https://github.com/actions/runner/releases/download/v$RUNNER_VERSION/actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
        tar xzf actions-runner.tar.gz
        rm actions-runner.tar.gz
    "
}

# Configure the runner with the registration token and other settings.
configure_runner() {
    local reg_token="$1"
    local runner_url
    local config_cmd

    if [[ -n "$GITHUB_REPO" ]]; then
        runner_url="https://github.com/$GITHUB_ORG/$GITHUB_REPO"
    else
        runner_url="https://github.com/$GITHUB_ORG"
    fi

    # Append a unique suffix to the runner name to avoid conflicts.
    local unique_runner_name="$RUNNER_NAME-$(hostname)-$(head -c 4 /dev/urandom | od -An -t x1 | tr -d ' ')"

    log "Configuring runner '$unique_runner_name'..."

    # Build the configuration command.
    config_cmd=("./config.sh --url \"$runner_url\" --token \"$reg_token\" --name \"$unique_runner_name\" --unattended --replace")

    if [[ -n "$RUNNER_LABELS" ]]; then
        config_cmd+=("--labels \"$RUNNER_LABELS\"")
    fi

    if [[ -n "$RUNNER_GROUP" ]]; then
        config_cmd+=("--runnergroup \"$RUNNER_GROUP\"")
    fi

    su - "$RUNNER_USER" -c "cd '$RUNNER_DIR' && ${config_cmd[*]}"
}

# Install and start the runner as a systemd service.
install_service() {
    log "Installing runner as a systemd service..."
    cd "$RUNNER_DIR"
    ./svc.sh install "$RUNNER_USER"
    ./svc.sh start

    log "Verifying runner service status..."
    if systemctl is-active --quiet "actions.runner.*"; then
        log "✓ Runner service is active."
    else
        log "✗ Runner service failed to start."
        systemctl status "actions.runner.*" --no-pager || true
        exit 1
    fi
}

# Verify runner user can access Docker
verify_docker_access_for_runner() {
    log "Verifying Docker access for '$RUNNER_USER'..."
    
    # First ensure Docker socket has correct permissions
    if [[ -S /var/run/docker.sock ]]; then
        chmod 666 /var/run/docker.sock 2>/dev/null || true
    fi
    
    # Test Docker access with retry
    local retry_count=0
    while [[ $retry_count -lt 3 ]]; do
        if su - "$RUNNER_USER" -c "docker version" &>/dev/null; then
            log "✓ Docker access confirmed for '$RUNNER_USER'."
            
            # Try to setup buildx for runner
            setup_buildx_for_runner
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        log "Docker access check failed (attempt $retry_count/3). Fixing permissions..."
        
        # Fix permissions and retry
        usermod -aG docker "$RUNNER_USER" 2>/dev/null || true
        chmod 666 /var/run/docker.sock 2>/dev/null || true
        sleep 2
    done
    
    log "WARNING: User '$RUNNER_USER' cannot access Docker after 3 attempts."
    log "Runner will work but Docker builds may fail."
}

deploy_helper_scripts() {
    log "Deploying helper scripts..."
    
    local scripts_dir="/opt/github-runner/scripts"
    mkdir -p "$scripts_dir"
    
    # Check if scripts are available in the current directory or a known location
    local source_dir="${SCRIPT_SOURCE_DIR:-$(dirname "$0")}"
    
    if [[ -d "$source_dir" ]]; then
        for script in diagnose-runner.sh fix-runner-issues.sh monitor-runner.sh; do
            if [[ -f "$source_dir/$script" ]]; then
                cp "$source_dir/$script" "$scripts_dir/" 2>/dev/null || true
                chmod +x "$scripts_dir/$script" 2>/dev/null || true
                log "Deployed $script"
            fi
        done
        
        # Create convenience commands
        if [[ -f "$scripts_dir/diagnose-runner.sh" ]]; then
            cat > /usr/local/bin/runner-status << 'EOF'
#!/bin/bash
/opt/github-runner/scripts/diagnose-runner.sh | grep -E "✓|✗|⚠" | tail -20
EOF
            chmod +x /usr/local/bin/runner-status
            log "Created runner-status command"
        fi
        
        if [[ -f "$scripts_dir/fix-runner-issues.sh" ]]; then
            cat > /usr/local/bin/runner-fix << 'EOF'
#!/bin/bash
/opt/github-runner/scripts/fix-runner-issues.sh
EOF
            chmod +x /usr/local/bin/runner-fix
            log "Created runner-fix command"
        fi
        
        # Setup monitoring service (optional)
        if [[ -f "$scripts_dir/monitor-runner.sh" ]]; then
            setup_monitoring_service
        fi
    else
        log "Helper scripts not found in $source_dir, skipping deployment"
    fi
}

setup_monitoring_service() {
    log "Setting up monitoring service..."
    
    cat > /etc/systemd/system/github-runner-monitor.service << 'EOF'
[Unit]
Description=GitHub Runner Health Monitor
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
ExecStart=/opt/github-runner/scripts/monitor-runner.sh --interval 60
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
User=root

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable github-runner-monitor.service 2>/dev/null || true
    log "Monitoring service configured (start with: systemctl start github-runner-monitor)"
}

setup_buildx_for_runner() {
    log "Setting up Docker buildx for runner user..."
    
    if [[ -f /usr/local/lib/docker/cli-plugins/docker-buildx ]]; then
        # Copy buildx to runner's home
        local runner_docker_dir="$RUNNER_HOME/.docker/cli-plugins"
        su - "$RUNNER_USER" -c "mkdir -p '$runner_docker_dir'"
        
        cp /usr/local/lib/docker/cli-plugins/docker-buildx "$runner_docker_dir/" 2>/dev/null || true
        chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_HOME/.docker" 2>/dev/null || true
        chmod +x "$runner_docker_dir/docker-buildx" 2>/dev/null || true
        
        # Try to create builder
        if su - "$RUNNER_USER" -c "docker buildx create --name runner-builder --driver docker-container --use" 2>/dev/null; then
            log "Docker buildx configured for runner."
        else
            log "WARNING: Could not setup buildx builder."
        fi
    fi
}

# --- Main Execution ---
main() {
    log "========================================"
    log "GitHub Actions Runner Installation v2.0"
    log "========================================"
    log "Starting at: $(date)"
    log "Hostname: $(hostname)"
    log "System: $(uname -a)"
    log "========================================"
    
    check_system_requirements
    
    install_dependencies
    
    create_runner_user
    
    # Verify Docker access if Docker is installed
    if command -v docker &>/dev/null; then
        verify_docker_access_for_runner
    else
        log "Docker not installed, skipping Docker access verification."
    fi

    local github_pat
    github_pat=$(get_github_pat)
    
    local reg_token
    reg_token=$(get_registration_token "$github_pat")

    install_runner
    
    configure_runner "$reg_token"
    
    install_service
    
    # Deploy helper scripts if available
    deploy_helper_scripts
    
    # Final verification and summary
    log "========================================"
    log "Installation Summary"
    log "======================================="
    
    # Check runner service
    if systemctl is-active --quiet "actions.runner.*"; then
        log "✓ Runner service: ACTIVE"
    else
        log "✗ Runner service: FAILED"
        systemctl status "actions.runner.*" --no-pager 2>/dev/null | head -10 || true
    fi
    
    # Check Docker (if installed)
    if command -v docker &>/dev/null; then
        if su - "$RUNNER_USER" -c "docker version" &>/dev/null; then
            log "✓ Docker access: WORKING"
        else
            log "⚠ Docker access: LIMITED"
        fi
    else
        log "ℹ Docker: NOT INSTALLED"
    fi
    
    # Log file locations
    log "========================================"
    log "Log files:"
    log "  - Installation: $LOG_FILE"
    log "  - Errors: $ERROR_LOG"
    log "  - Runner: $RUNNER_DIR/_diag/"
    log "========================================"
    log "GitHub Actions Runner Installation Completed"
    log "========================================"
    
    # Run initial diagnostic if script is available
    if [[ -x "/opt/github-runner/scripts/diagnose-runner.sh" ]]; then
        log "\nRunning initial diagnostic check..."
        /opt/github-runner/scripts/diagnose-runner.sh | tail -30 || true
    fi
    
    # Show available commands
    if [[ -x "/usr/local/bin/runner-status" ]]; then
        log "\nAvailable commands:"
        log "  runner-status - Quick health check"
        log "  runner-fix    - Fix common issues"
    fi
}

# Run the main function
main "$@"