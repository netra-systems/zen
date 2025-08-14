#!/bin/bash
set -e

# Configuration
CORRECT_PROJECT_ID="304612253870"  # The project where VMs are located
SECRET_NAME="github-runner-token"
SERVICE_ACCOUNT="github-runner-sa@${CORRECT_PROJECT_ID}.iam.gserviceaccount.com"

echo "========================================="
echo "GitHub Runner Secret Fix Script"
echo "Project: $CORRECT_PROJECT_ID"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

# Check if we're in the right project
echo -e "\n1. Checking current GCP project..."
CURRENT_PROJECT=$(gcloud config get-value project)
if [ "$CURRENT_PROJECT" != "$CORRECT_PROJECT_ID" ]; then
    print_status "warning" "Current project is $CURRENT_PROJECT, switching to $CORRECT_PROJECT_ID"
    gcloud config set project $CORRECT_PROJECT_ID
else
    print_status "success" "Already in correct project: $CORRECT_PROJECT_ID"
fi

# Enable Secret Manager API
echo -e "\n2. Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project=$CORRECT_PROJECT_ID
print_status "success" "Secret Manager API enabled"

# Check if secret already exists in correct project
echo -e "\n3. Checking if secret exists in correct project..."
if gcloud secrets describe $SECRET_NAME --project=$CORRECT_PROJECT_ID &>/dev/null; then
    print_status "warning" "Secret already exists in project. Will update the version."
    SECRET_EXISTS=true
else
    print_status "warning" "Secret does not exist. Will create it."
    SECRET_EXISTS=false
fi

# Get the GitHub token
echo -e "\n4. Enter your GitHub Personal Access Token (PAT):"
echo "   Required scopes: repo (for repository runners) or admin:org (for org runners)"
echo -n "   Token: "
read -s GITHUB_TOKEN
echo

if [ -z "$GITHUB_TOKEN" ]; then
    print_status "error" "No token provided"
    exit 1
fi

# Create or update the secret
echo -e "\n5. Creating/updating secret in correct project..."
if [ "$SECRET_EXISTS" = false ]; then
    # Create new secret
    gcloud secrets create $SECRET_NAME \
        --replication-policy="automatic" \
        --project=$CORRECT_PROJECT_ID
    print_status "success" "Secret created"
fi

# Add new version with the token
echo "$GITHUB_TOKEN" | gcloud secrets versions add $SECRET_NAME \
    --data-file=- \
    --project=$CORRECT_PROJECT_ID
print_status "success" "Secret version added"

# Grant access to the service account
echo -e "\n6. Granting access to service account..."
gcloud secrets add-iam-policy-binding $SECRET_NAME \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$CORRECT_PROJECT_ID
print_status "success" "Service account granted access"

# Verify the secret is accessible
echo -e "\n7. Verifying secret access..."
if gcloud secrets versions access latest --secret=$SECRET_NAME --project=$CORRECT_PROJECT_ID &>/dev/null; then
    print_status "success" "Secret is accessible"
else
    print_status "error" "Cannot access secret"
    exit 1
fi

# List running instances
echo -e "\n8. Finding GitHub runner instances..."
INSTANCES=$(gcloud compute instances list \
    --filter="name:gcp-runner-* AND status:RUNNING" \
    --format="value(name,zone)" \
    --project=$CORRECT_PROJECT_ID)

if [ -z "$INSTANCES" ]; then
    print_status "warning" "No running GitHub runner instances found"
else
    echo "Found instances:"
    echo "$INSTANCES"
    
    echo -e "\n9. Do you want to restart the runner service on all instances? (y/n)"
    read -r RESTART_CHOICE
    
    if [ "$RESTART_CHOICE" = "y" ]; then
        while IFS= read -r line; do
            INSTANCE_NAME=$(echo $line | awk '{print $1}')
            INSTANCE_ZONE=$(echo $line | awk '{print $2}')
            
            echo -e "\nRestarting runner on $INSTANCE_NAME in $INSTANCE_ZONE..."
            
            # SSH and restart the runner service
            gcloud compute ssh $INSTANCE_NAME \
                --zone=$INSTANCE_ZONE \
                --project=$CORRECT_PROJECT_ID \
                --command="sudo systemctl restart actions.runner.*.service" 2>/dev/null || {
                print_status "warning" "Could not restart service on $INSTANCE_NAME"
            }
            
            # Check status
            gcloud compute ssh $INSTANCE_NAME \
                --zone=$INSTANCE_ZONE \
                --project=$CORRECT_PROJECT_ID \
                --command="sudo systemctl status actions.runner.*.service --no-pager | head -3" 2>/dev/null || {
                print_status "warning" "Could not check status on $INSTANCE_NAME"
            }
        done <<< "$INSTANCES"
        
        print_status "success" "Runner services restarted"
    fi
fi

echo -e "\n========================================="
echo "Secret fix complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. If runners were already deployed, you may need to:"
echo "   - Restart the instances: gcloud compute instances reset <instance-name> --zone=<zone>"
echo "   - Or SSH and run: sudo /path/to/fix-runner.sh"
echo "2. For new deployments, run: terraform apply"
echo "3. Check runners at: https://github.com/netra-systems/netra-apex/settings/actions/runners"