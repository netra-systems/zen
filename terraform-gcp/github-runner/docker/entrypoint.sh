#!/bin/bash
set -e

# Configuration
RUNNER_DIR="/home/runner/actions-runner"

# Function to get registration token
get_registration_token() {
    if [[ -z "$GITHUB_TOKEN" ]]; then
        echo "ERROR: GITHUB_TOKEN environment variable is required"
        exit 1
    fi
    
    local api_url
    if [[ -n "$GITHUB_REPO" ]]; then
        api_url="https://api.github.com/repos/$GITHUB_ORG/$GITHUB_REPO/actions/runners/registration-token"
    else
        api_url="https://api.github.com/orgs/$GITHUB_ORG/actions/runners/registration-token"
    fi
    
    local response=$(curl -sX POST -H "Authorization: token $GITHUB_TOKEN" -H "Accept: application/vnd.github.v3+json" "$api_url")
    local token=$(echo "$response" | jq -r .token)
    
    if [[ "$token" == "null" || -z "$token" ]]; then
        echo "ERROR: Failed to get registration token"
        echo "Response: $response"
        exit 1
    fi
    
    echo "$token"
}

# Function to deregister runner on exit
cleanup() {
    echo "Caught signal, deregistering runner..."
    cd "$RUNNER_DIR"
    
    if [[ -n "$GITHUB_TOKEN" ]]; then
        local remove_token=$(curl -sX POST \
            -H "Authorization: token $GITHUB_TOKEN" \
            -H "Accept: application/vnd.github.v3+json" \
            "https://api.github.com/repos/$GITHUB_ORG/$GITHUB_REPO/actions/runners/remove-token" | jq -r .token)
        
        if [[ "$remove_token" != "null" && -n "$remove_token" ]]; then
            ./config.sh remove --token "$remove_token" || true
        fi
    fi
    
    exit 0
}

# Trap signals for cleanup
trap cleanup SIGTERM SIGINT

# Main execution
main() {
    echo "Starting GitHub Actions Runner..."
    echo "Organization: $GITHUB_ORG"
    echo "Repository: ${GITHUB_REPO:-'organization-level'}"
    echo "Runner Name: $RUNNER_NAME-$(hostname)"
    
    cd "$RUNNER_DIR"
    
    # Get registration token
    REG_TOKEN=$(get_registration_token)
    
    # Configure runner
    local runner_url
    if [[ -n "$GITHUB_REPO" ]]; then
        runner_url="https://github.com/$GITHUB_ORG/$GITHUB_REPO"
    else
        runner_url="https://github.com/$GITHUB_ORG"
    fi
    
    local unique_name="$RUNNER_NAME-$(hostname)-$(date +%s)"
    
    ./config.sh \
        --url "$runner_url" \
        --token "$REG_TOKEN" \
        --name "$unique_name" \
        --labels "$RUNNER_LABELS" \
        --unattended \
        --replace \
        ${RUNNER_GROUP:+--runnergroup "$RUNNER_GROUP"}
    
    # Run the runner (foreground)
    ./run.sh &
    
    # Wait for runner process
    wait $!
}

# Run main function
main