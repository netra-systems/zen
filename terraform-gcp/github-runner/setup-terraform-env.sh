#!/bin/bash
# A simplified script to install and configure a GitHub Actions self-hosted runner.

# Exit immediately if a command exits with a non-zero status.
set -e
# Treat unset variables as an error when substituting.
set -u
# Pipelines return the exit status of the last command to exit with a non-zero status.
set -o pipefail

# --- Configuration Variables (from Terraform) ---
GITHUB_ORG="${github_org}"
GITHUB_REPO="${github_repo}"
RUNNER_NAME="${runner_name}"
RUNNER_LABELS="${runner_labels}"
RUNNER_GROUP="${runner_group}"
PROJECT_ID="${project_id}"
# This syntax is escaped with $$ to be compatible with Terraform's templatefile function.
RUNNER_VERSION="$${runner_version:-"2.317.0"}"

# --- Script Variables ---
RUNNER_USER="runner"
RUNNER_HOME="/home/$RUNNER_USER"
RUNNER_DIR="$RUNNER_HOME/actions-runner"
LOG_FILE="/var/log/github-runner-install.log"

# --- Logging Setup ---
exec > >(tee -a "$LOG_FILE") 2>&1

# --- Helper Functions ---
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error_handler() {
    log "ERROR: Script failed on line $1."
}
trap 'error_handler $LINENO' ERR

# --- Main Functions ---

install_dependencies() {
    log "Updating package lists and installing dependencies..."
    apt-get update
    apt-get install -y --no-install-recommends \
        curl \
        jq \
        git \
        docker.io

    log "Starting and enabling Docker service..."
    systemctl enable --now docker
}

setup_runner_user() {
    if ! id "$RUNNER_USER" &>/dev/null; then
        log "Creating runner user '$RUNNER_USER'..."
        useradd -m -s /bin/bash "$RUNNER_USER"
    fi
    log "Adding runner user to the 'docker' group..."
    usermod -aG docker "$RUNNER_USER"
}

get_registration_token() {
    log "Retrieving GitHub PAT from Secret Manager..."
    local github_pat
    github_pat=$(gcloud secrets versions access latest --secret="github-runner-token" --project="$PROJECT_ID")
    if [[ -z "$github_pat" ]]; then
        log "ERROR: Failed to retrieve GitHub PAT."
        exit 1
    fi

    local api_url="https://api.github.com/orgs/$GITHUB_ORG/actions/runners/registration-token"
    if [[ -n "$GITHUB_REPO" ]]; then
        api_url="https://api.github.com/repos/$GITHUB_ORG/$GITHUB_REPO/actions/runners/registration-token"
    fi

    log "Requesting runner registration token..."
    local response
    response=$(curl -sS -X POST \
        -H "Authorization: token $github_pat" \
        -H "Accept: application/vnd.github.v3+json" \
        "$api_url")

    local reg_token
    reg_token=$(echo "$response" | jq -r .token)

    if [[ "$reg_token" == "null" || -z "$reg_token" ]]; then
        log "ERROR: Failed to get registration token. API Response: $response"
        exit 1
    fi
    echo "$reg_token"
}

install_and_configure_runner() {
    local reg_token="$1"
    local runner_url="https://github.com/$GITHUB_ORG"
    if [[ -n "$GITHUB_REPO" ]]; then
        runner_url+="/$GITHUB_REPO"
    fi

    log "Downloading and installing GitHub Actions runner v$RUNNER_VERSION..."
    su - "$RUNNER_USER" -c "
        mkdir -p '$RUNNER_DIR'
        cd '$RUNNER_DIR'
        curl -sSL -o actions-runner.tar.gz https://github.com/actions/runner/releases/download/v$RUNNER_VERSION/actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
        tar xzf actions-runner.tar.gz
        rm actions-runner.tar.gz

        log 'Configuring the runner...'
        ./config.sh \
            --url '$runner_url' \
            --token '$reg_token' \
            --name '$RUNNER_NAME-$(hostname)' \
            --labels '$RUNNER_LABELS' \
            --runnergroup '$RUNNER_GROUP' \
            --unattended \
            --replace
    "
}

install_service() {
    log "Installing and starting the runner service..."
    cd "$RUNNER_DIR"
    ./svc.sh install "$RUNNER_USER"
    ./svc.sh start

    log "Verifying runner service status..."
    if ! systemctl is-active --quiet "actions.runner.*"; then
        log "✗ Runner service failed to start."
        systemctl status "actions.runner.*" --no-pager || true
        exit 1
    fi
    log "✓ Runner service is active."
}

# --- Main Execution ---
main() {
    log "--- Starting GitHub Actions Runner Installation ---"
    
    install_dependencies
    setup_runner_user
    
    # Verify the runner user can access the Docker daemon.
    log "Verifying Docker access for '$RUNNER_USER'..."
    if ! su - "$RUNNER_USER" -c "docker version" > /dev/null 2>&1; then
        log "ERROR: User '$RUNNER_USER' cannot access the Docker daemon."
        exit 1
    fi
    log "✓ Docker access confirmed."

    local reg_token
    reg_token=$(get_registration_token)

    install_and_configure_runner "$reg_token"
    install_service
    
    log "--- GitHub Actions Runner Installation Completed Successfully ---"
}

main
