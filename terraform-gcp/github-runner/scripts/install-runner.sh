#!/bin/bash
# A robust script to install and configure a GitHub Actions self-hosted runner.

# Exit immediately if a command exits with a non-zero status.
set -e
# Treat unset variables as an error when substituting.
set -u
# Pipelines return the exit status of the last command to exit with a non-zero status,
# or zero if no command exited with a non-zero status.
set -o pipefail

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

# --- Logging Setup ---
# Redirect stdout and stderr to a log file and the console.
exec > >(tee -a "$LOG_FILE") 2>&1

# --- Helper Functions ---

# Log messages with a timestamp.
log() {
    # Note: Ensure this is a standard space, not a non-breaking space.
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Trap errors to log them before exiting.
error_handler() {
    local exit_code=$?
    log "ERROR: Script failed on line $1 with exit code $exit_code."
}
trap 'error_handler $LINENO' ERR

# Check for root privileges.
check_root() {
    if [[ "$EUID" -ne 0 ]]; then
        log "ERROR: This script must be run as root."
        exit 1
    fi
}

# Install all necessary system dependencies.
install_dependencies() {
    log "Updating package lists..."
    apt-get update

    log "Installing dependencies..."
    PACKAGES="curl jq git build-essential libssl-dev libffi-dev python3 python3-venv python3-dev python3-pip docker.io docker-compose"
    apt-get install -y --no-install-recommends $PACKAGES

    log "Starting and enabling Docker service..."
    systemctl enable --now docker

    # Wait for Docker to become active.
    log "Verifying Docker service status..."
    local retries=15
    for ((i=1; i<=retries; i++)); do
        if systemctl is-active --quiet docker && docker info > /dev/null 2>&1; then
            log "Docker is active and running."
            break
        fi
        log "Waiting for Docker to start... (attempt $i/$retries)"
        sleep 4
        if [[ "$i" -eq "$retries" ]]; then
            log "ERROR: Docker failed to start properly."
            systemctl status docker --no-pager || true
            journalctl -u docker -n 50 --no-pager || true
            exit 1
        fi
    done

    log "Installing Docker buildx plugin..."
    local buildx_dir="/usr/local/lib/docker/cli-plugins"
    mkdir -p "$buildx_dir"
    curl -sSL "https://github.com/docker/buildx/releases/download/v0.11.2/buildx-v0.11.2.linux-amd64" \
        -o "$buildx_dir/docker-buildx"
    chmod +x "$buildx_dir/docker-buildx"
}

# Create a dedicated user for running the GitHub Actions runner.
create_runner_user() {
    if ! id "$RUNNER_USER" &>/dev/null; then
        log "Creating runner user '$RUNNER_USER'..."
        useradd -m -s /bin/bash "$RUNNER_USER"
    else
        log "Runner user '$RUNNER_USER' already exists."
    fi
    log "Adding runner user to the 'docker' group..."
    usermod -aG docker "$RUNNER_USER"
}

# Retrieve the GitHub Personal Access Token (PAT) from Google Secret Manager.
get_github_pat() {
    log "Retrieving GitHub PAT from Secret Manager..."
    local token
    token=$(gcloud secrets versions access latest --secret="github-runner-token" --project="$PROJECT_ID")
    if [[ -z "$token" ]]; then
        log "ERROR: Failed to retrieve GitHub PAT. The token is empty."
        exit 1
    fi
    echo "$token"
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

# --- Main Execution ---
main() {
    log "--- Starting GitHub Actions Runner Installation ---"
    
    check_root
    
    install_dependencies
    
    create_runner_user
    
    # Verify the runner user can access the Docker daemon.
    # `su -` simulates a login, which correctly applies the new group membership.
    log "Verifying Docker access for '$RUNNER_USER'..."
    if ! su - "$RUNNER_USER" -c "docker version" > /dev/null 2>&1; then
        log "ERROR: User '$RUNNER_USER' cannot access the Docker daemon. Check permissions."
        exit 1
    fi
    log "✓ Docker access confirmed."

    local github_pat
    github_pat=$(get_github_pat)
    
    local reg_token
    reg_token=$(get_registration_token "$github_pat")

    install_runner
    
    configure_runner "$reg_token"
    
    install_service
    
    log "--- GitHub Actions Runner Installation Completed Successfully ---"
}

# Run the main function.
main