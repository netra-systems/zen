#!/bin/bash
set -e

# Configuration
PROJECT_ID="304612253870"
REGION="us-central1"
ZONE="us-central1-a"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Terraform Teardown and Redeploy Script${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "This script will:"
echo "1. Destroy existing Terraform resources"
echo "2. Clean up any orphaned resources"
echo "3. Reset Terraform state"
echo "4. Redeploy everything correctly"
echo ""
echo -e "${YELLOW}WARNING: This will DELETE all GitHub runner infrastructure!${NC}"
echo -n "Continue? (yes/no): "
read CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# Function to print status
print_status() {
    local status=$1
    local message=$2
    case $status in
        "info")
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
        "success")
            echo -e "${GREEN}[OK]${NC} $message"
            ;;
        "warning")
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        "error")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
    esac
}

# Step 1: Set correct project
print_status "info" "Setting up environment..."
gcloud config set project $PROJECT_ID
export GOOGLE_PROJECT=$PROJECT_ID
export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
export GCP_PROJECT=$PROJECT_ID
print_status "success" "Environment configured for project: $PROJECT_ID"

# Step 2: Terraform destroy (if state exists)
if [ -f "terraform.tfstate" ] || [ -f ".terraform/terraform.tfstate" ]; then
    print_status "info" "Running terraform destroy..."
    
    # Initialize if needed
    if [ ! -d ".terraform" ]; then
        terraform init
    fi
    
    # Destroy with auto-approve
    terraform destroy -auto-approve || {
        print_status "warning" "Terraform destroy failed, will clean up manually"
    }
else
    print_status "warning" "No Terraform state found, skipping terraform destroy"
fi

# Step 3: Manual cleanup of resources
print_status "info" "Cleaning up any remaining resources..."

# Delete compute instances
print_status "info" "Checking for GitHub runner instances..."
INSTANCES=$(gcloud compute instances list \
    --filter="name:gcp-runner-*" \
    --format="value(name,zone)" \
    --project=$PROJECT_ID)

if [ -n "$INSTANCES" ]; then
    while IFS= read -r line; do
        INSTANCE_NAME=$(echo $line | awk '{print $1}')
        INSTANCE_ZONE=$(echo $line | awk '{print $2}')
        print_status "info" "Deleting instance: $INSTANCE_NAME"
        gcloud compute instances delete $INSTANCE_NAME \
            --zone=$INSTANCE_ZONE \
            --project=$PROJECT_ID \
            --quiet
    done <<< "$INSTANCES"
    print_status "success" "Instances deleted"
else
    print_status "info" "No runner instances found"
fi

# Delete firewall rules
print_status "info" "Checking for firewall rules..."
FIREWALL_RULES=$(gcloud compute firewall-rules list \
    --filter="name:github-runner-*" \
    --format="value(name)" \
    --project=$PROJECT_ID)

if [ -n "$FIREWALL_RULES" ]; then
    for RULE in $FIREWALL_RULES; do
        print_status "info" "Deleting firewall rule: $RULE"
        gcloud compute firewall-rules delete $RULE \
            --project=$PROJECT_ID \
            --quiet
    done
    print_status "success" "Firewall rules deleted"
else
    print_status "info" "No firewall rules found"
fi

# Delete service account
print_status "info" "Checking for service account..."
if gcloud iam service-accounts describe github-runner-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --project=$PROJECT_ID &>/dev/null; then
    print_status "info" "Deleting service account..."
    gcloud iam service-accounts delete github-runner-sa@$PROJECT_ID.iam.gserviceaccount.com \
        --project=$PROJECT_ID \
        --quiet
    print_status "success" "Service account deleted"
else
    print_status "info" "Service account not found"
fi

# Delete secrets
print_status "info" "Checking for secrets..."
if gcloud secrets describe github-runner-token --project=$PROJECT_ID &>/dev/null; then
    print_status "info" "Deleting secret..."
    gcloud secrets delete github-runner-token \
        --project=$PROJECT_ID \
        --quiet
    print_status "success" "Secret deleted"
else
    print_status "info" "Secret not found in correct project"
fi

# Check for secret in wrong project (if you know which one)
if [ -n "$WRONG_PROJECT_ID" ]; then
    print_status "info" "Checking for secret in wrong project: $WRONG_PROJECT_ID"
    if gcloud secrets describe github-runner-token --project=$WRONG_PROJECT_ID &>/dev/null; then
        print_status "warning" "Found secret in wrong project"
        echo -n "Delete secret from wrong project? (yes/no): "
        read DELETE_WRONG
        if [ "$DELETE_WRONG" == "yes" ]; then
            gcloud secrets delete github-runner-token \
                --project=$WRONG_PROJECT_ID \
                --quiet
            print_status "success" "Secret deleted from wrong project"
        fi
    fi
fi

# Delete storage bucket
print_status "info" "Checking for storage bucket..."
BUCKET_NAME="${PROJECT_ID}-github-runner-artifacts"
if gsutil ls -b gs://$BUCKET_NAME &>/dev/null; then
    print_status "info" "Deleting storage bucket..."
    gsutil rm -r gs://$BUCKET_NAME
    print_status "success" "Storage bucket deleted"
else
    print_status "info" "Storage bucket not found"
fi

# Step 4: Clean Terraform state
print_status "info" "Cleaning Terraform state..."
rm -rf .terraform
rm -f terraform.tfstate*
rm -f .terraform.lock.hcl
rm -f .terraform.tfstate.lock.info
print_status "success" "Terraform state cleaned"

# Step 5: Prepare for redeployment
print_status "info" "Preparing for redeployment..."

# Create secret in correct project
if [ -z "$TF_VAR_github_token" ]; then
    echo ""
    echo -e "${YELLOW}GitHub Personal Access Token required${NC}"
    echo "Create a token at: https://github.com/settings/tokens"
    echo "Required scopes: repo (for repository runners)"
    echo -n "Enter your GitHub token: "
    read -s GITHUB_TOKEN
    echo ""
    export TF_VAR_github_token=$GITHUB_TOKEN
fi

# Step 6: Redeploy
echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Ready to Redeploy${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "Environment is configured correctly."
echo -n "Proceed with deployment? (yes/no): "
read DEPLOY

if [ "$DEPLOY" == "yes" ]; then
    print_status "info" "Initializing Terraform..."
    terraform init
    
    print_status "info" "Planning deployment..."
    terraform plan
    
    echo ""
    echo -n "Apply the plan? (yes/no): "
    read APPLY
    
    if [ "$APPLY" == "yes" ]; then
        print_status "info" "Applying Terraform configuration..."
        terraform apply -auto-approve
        
        print_status "success" "Deployment complete!"
        echo ""
        echo "Next steps:"
        echo "1. Wait 2-3 minutes for runners to initialize"
        echo "2. Check runners at: https://github.com/netra-systems/netra-apex/settings/actions/runners"
        echo "3. Run troubleshooting if needed: ./scripts/troubleshoot-runner.sh"
    else
        print_status "info" "Deployment cancelled. Run 'terraform apply' when ready."
    fi
else
    print_status "info" "Redeployment cancelled."
    echo ""
    echo "To deploy later, run:"
    echo "  terraform init"
    echo "  terraform apply"
fi

echo ""
echo -e "${GREEN}Teardown complete!${NC}"