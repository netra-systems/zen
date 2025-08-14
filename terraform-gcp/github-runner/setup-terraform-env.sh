#!/bin/bash
# Setup script to ensure Terraform uses the correct project

PROJECT_ID="304612253870"

echo "Setting up Terraform environment for GitHub Runner"
echo "=================================================="

# Set gcloud project
echo "Setting gcloud project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Set application default credentials
echo "Setting application default credentials..."
gcloud auth application-default login --project=$PROJECT_ID

# Set quota project
gcloud auth application-default set-quota-project $PROJECT_ID

# Export environment variables
export GOOGLE_PROJECT=$PROJECT_ID
export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
export GCP_PROJECT=$PROJECT_ID

# Verify settings
echo ""
echo "Verification:"
echo "-------------"
echo "gcloud project: $(gcloud config get-value project)"
echo "ADC project: $(gcloud auth application-default print-project 2>/dev/null || echo 'Not set')"
echo "GOOGLE_PROJECT: $GOOGLE_PROJECT"

echo ""
echo "Environment is ready. Run 'terraform init' and 'terraform apply' now."