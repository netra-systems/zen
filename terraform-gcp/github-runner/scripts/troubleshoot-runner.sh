#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
INSTANCE_NAME="${1:-gcp-runner-1}"
ZONE="${2:-us-central1-a}"
PROJECT_ID="${3:-304612253870}"

echo "========================================="
echo "GitHub Runner Troubleshooting Script"
echo "Instance: $INSTANCE_NAME"
echo "Zone: $ZONE"
echo "Project: $PROJECT_ID"
echo "========================================="

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "error")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "success")
            echo -e "${GREEN}[OK]${NC} $message"
            ;;
        "warning")
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        *)
            echo "$message"
            ;;
    esac
}

# Check if gcloud is configured
echo -e "\n1. Checking gcloud configuration..."
if gcloud config get-value project &>/dev/null; then
    print_status "success" "gcloud is configured for project: $(gcloud config get-value project)"
else
    print_status "error" "gcloud is not configured"
    exit 1
fi

# Check instance status
echo -e "\n2. Checking instance status..."
INSTANCE_STATUS=$(gcloud compute instances describe $INSTANCE_NAME \
    --zone=$ZONE \
    --project=$PROJECT_ID \
    --format="value(status)" 2>/dev/null || echo "NOT_FOUND")

if [ "$INSTANCE_STATUS" == "RUNNING" ]; then
    print_status "success" "Instance is running"
elif [ "$INSTANCE_STATUS" == "NOT_FOUND" ]; then
    print_status "error" "Instance not found"
    exit 1
else
    print_status "warning" "Instance status: $INSTANCE_STATUS"
fi

# SSH into instance and check runner status
echo -e "\n3. Checking runner service status on VM..."
gcloud compute ssh $INSTANCE_NAME \
    --zone=$ZONE \
    --project=$PROJECT_ID \
    --command="sudo systemctl status actions.runner.* --no-pager" 2>/dev/null || {
    print_status "error" "Failed to check runner service status"
}

# Check startup script logs
echo -e "\n4. Checking startup script logs..."
gcloud compute ssh $INSTANCE_NAME \
    --zone=$ZONE \
    --project=$PROJECT_ID \
    --command="sudo journalctl -u google-startup-scripts.service --no-pager -n 50" 2>/dev/null || {
    print_status "error" "Failed to retrieve startup script logs"
}

# Check if runner is configured
echo -e "\n5. Checking runner configuration..."
gcloud compute ssh $INSTANCE_NAME \
    --zone=$ZONE \
    --project=$PROJECT_ID \
    --command="sudo ls -la /home/runner/actions-runner/.runner 2>/dev/null && echo 'Runner is configured' || echo 'Runner is NOT configured'" || {
    print_status "error" "Failed to check runner configuration"
}

# Check runner logs
echo -e "\n6. Checking runner logs..."
gcloud compute ssh $INSTANCE_NAME \
    --zone=$ZONE \
    --project=$PROJECT_ID \
    --command="sudo tail -n 30 /home/runner/actions-runner/_diag/Runner_*.log 2>/dev/null" || {
    print_status "warning" "No runner logs found"
}

# Check if token is accessible
echo -e "\n7. Checking GitHub token access..."
gcloud compute ssh $INSTANCE_NAME \
    --zone=$ZONE \
    --project=$PROJECT_ID \
    --command="gcloud secrets versions access latest --secret='github-runner-token' --project='$PROJECT_ID' &>/dev/null && echo 'Token is accessible' || echo 'Token is NOT accessible'" || {
    print_status "error" "Failed to check token access"
}

# Check network connectivity
echo -e "\n8. Checking network connectivity to GitHub..."
gcloud compute ssh $INSTANCE_NAME \
    --zone=$ZONE \
    --project=$PROJECT_ID \
    --command="curl -s -o /dev/null -w '%{http_code}' https://api.github.com/meta" | {
    read http_code
    if [ "$http_code" == "200" ]; then
        print_status "success" "Can reach GitHub API"
    else
        print_status "error" "Cannot reach GitHub API (HTTP $http_code)"
    fi
}

# Check if runner is registered in GitHub
echo -e "\n9. Checking GitHub runner registration..."
echo "To verify runner registration:"
echo "1. Go to https://github.com/netra-systems/netra-apex/settings/actions/runners"
echo "2. Look for runner named: $INSTANCE_NAME-<hostname>"
echo "3. Check if status is 'Idle' or 'Offline'"

# Get instance logs from Cloud Logging
echo -e "\n10. Recent logs from Cloud Logging..."
gcloud logging read "resource.type=gce_instance AND resource.labels.instance_id=$(gcloud compute instances describe $INSTANCE_NAME --zone=$ZONE --project=$PROJECT_ID --format='value(id)')" \
    --limit=20 \
    --project=$PROJECT_ID \
    --format="table(timestamp,jsonPayload.message)" || {
    print_status "warning" "Could not retrieve Cloud Logging entries"
}

echo -e "\n========================================="
echo "Troubleshooting complete!"
echo "========================================="