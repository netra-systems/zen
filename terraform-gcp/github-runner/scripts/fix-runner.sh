#!/bin/bash
set -e

# Variables
GITHUB_ORG="netra-systems"
GITHUB_REPO="netra-apex"
PROJECT_ID="304612253870"
RUNNER_USER="runner"
RUNNER_DIR="/home/$RUNNER_USER/actions-runner"
RUNNER_VERSION="2.311.0"

echo "GitHub Runner Fix Script"
echo "========================"

# Function to print colored output
print_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Stop existing runner service if running
print_msg "Stopping existing runner service..."
sudo systemctl stop actions.runner.*.service 2>/dev/null || true

# Remove existing runner configuration
print_msg "Removing existing runner configuration..."
if [ -f "$RUNNER_DIR/.runner" ]; then
    # Get removal token
    GITHUB_TOKEN=$(gcloud secrets versions access latest --secret="github-runner-token" --project="$PROJECT_ID")
    
    if [ -n "$GITHUB_TOKEN" ]; then
        REMOVE_TOKEN=$(curl -sX POST \
            -H "Authorization: token $GITHUB_TOKEN" \
            -H "Accept: application/vnd.github.v3+json" \
            "https://api.github.com/repos/$GITHUB_ORG/$GITHUB_REPO/actions/runners/remove-token" | jq -r .token)
        
        if [ -n "$REMOVE_TOKEN" ] && [ "$REMOVE_TOKEN" != "null" ]; then
            cd $RUNNER_DIR
            sudo -u $RUNNER_USER ./config.sh remove --token "$REMOVE_TOKEN" || true
        fi
    fi
fi

# Ensure runner user exists and has correct permissions
print_msg "Checking runner user..."
if ! id "$RUNNER_USER" &>/dev/null; then
    print_msg "Creating runner user..."
    useradd -m -s /bin/bash $RUNNER_USER
fi

# Add runner to docker group
usermod -aG docker $RUNNER_USER 2>/dev/null || true

# Re-download runner if needed
if [ ! -f "$RUNNER_DIR/config.sh" ]; then
    print_msg "Downloading GitHub Actions runner..."
    sudo -u $RUNNER_USER mkdir -p $RUNNER_DIR
    cd $RUNNER_DIR
    sudo -u $RUNNER_USER curl -o actions-runner-linux-x64-$RUNNER_VERSION.tar.gz -L \
        https://github.com/actions/runner/releases/download/v$RUNNER_VERSION/actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
    sudo -u $RUNNER_USER tar xzf actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
    sudo rm -f actions-runner-linux-x64-$RUNNER_VERSION.tar.gz
fi

# Get new registration token
print_msg "Getting new registration token..."
GITHUB_TOKEN=$(gcloud secrets versions access latest --secret="github-runner-token" --project="$PROJECT_ID")

if [ -z "$GITHUB_TOKEN" ]; then
    echo "ERROR: Cannot access GitHub token from Secret Manager"
    echo "Please ensure the token is stored in Secret Manager"
    exit 1
fi

REG_TOKEN=$(curl -sX POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$GITHUB_ORG/$GITHUB_REPO/actions/runners/registration-token" | jq -r .token)

if [ -z "$REG_TOKEN" ] || [ "$REG_TOKEN" == "null" ]; then
    echo "ERROR: Failed to get registration token"
    echo "Please check:"
    echo "1. The GitHub token has 'repo' scope for repository runners"
    echo "2. The repository exists: $GITHUB_ORG/$GITHUB_REPO"
    echo "3. The token is not expired"
    exit 1
fi

print_msg "Registration token obtained successfully"

# Configure runner
print_msg "Configuring runner..."
cd $RUNNER_DIR
RUNNER_NAME="gcp-runner-$(hostname)"
sudo -u $RUNNER_USER ./config.sh \
    --url "https://github.com/$GITHUB_ORG/$GITHUB_REPO" \
    --token "$REG_TOKEN" \
    --name "$RUNNER_NAME" \
    --labels "self-hosted,linux,x64,gcp,netra" \
    --unattended \
    --replace

# Install and start service
print_msg "Installing runner service..."
sudo ./svc.sh install $RUNNER_USER
sudo ./svc.sh start

# Enable service
sudo systemctl enable actions.runner.*.service

# Check status
print_msg "Checking runner status..."
sleep 5
sudo systemctl status actions.runner.*.service --no-pager

print_msg "Runner fix complete!"
print_msg "Runner name: $RUNNER_NAME"
print_msg "Check https://github.com/$GITHUB_ORG/$GITHUB_REPO/settings/actions/runners"