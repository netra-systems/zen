#!/bin/bash
# Quick teardown script for GitHub runner infrastructure

PROJECT_ID="304612253870"

echo "Quick Teardown of GitHub Runner Infrastructure"
echo "=============================================="
echo "This will destroy all GitHub runner resources"
echo ""

# Set correct project
gcloud config set project $PROJECT_ID
export GOOGLE_PROJECT=$PROJECT_ID

# Method 1: Try Terraform destroy first
echo "1. Attempting Terraform destroy..."
terraform destroy -auto-approve 2>/dev/null || echo "Terraform destroy failed or no state"

# Method 2: Manual cleanup
echo ""
echo "2. Manual cleanup of remaining resources..."

# Delete all runner instances
gcloud compute instances delete $(gcloud compute instances list --filter="name:gcp-runner-*" --format="value(name)") \
    --zone=$ZONE --quiet 2>/dev/null || echo "No instances to delete"

# Delete firewall rules
gcloud compute firewall-rules delete github-runner-ssh --quiet 2>/dev/null || true

# Delete service account
gcloud iam service-accounts delete github-runner-sa@$PROJECT_ID.iam.gserviceaccount.com --quiet 2>/dev/null || true

# Delete secret
gcloud secrets delete github-runner-token --project=$PROJECT_ID --quiet 2>/dev/null || true

# Delete bucket
gsutil rm -r gs://${PROJECT_ID}-github-runner-artifacts 2>/dev/null || true

# Clean Terraform files
echo ""
echo "3. Cleaning Terraform state..."
rm -rf .terraform terraform.tfstate* .terraform.lock.hcl .terraform.tfstate.lock.info

echo ""
echo "Teardown complete!"
echo ""
echo "To redeploy:"
echo "  export TF_VAR_github_token='your-github-token'"
echo "  terraform init"
echo "  terraform apply"