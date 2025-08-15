#!/bin/bash
# Complete deployment script for GitHub Runner on Cloud Run

set -e

# Configuration
PROJECT_ID="cryptic-net-466001-n0"
REGION="us-central1"
IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/github-runners/runner:latest"

echo "GitHub Runner Cloud Run Deployment - Final Steps"
echo "================================================"
echo ""

# Step 1: Authenticate
echo "Step 1: Authenticating with Google Cloud..."
echo "Please complete the authentication flow if prompted:"
gcloud auth login

# Step 2: Set project
echo ""
echo "Step 2: Setting project to ${PROJECT_ID}..."
gcloud config set project ${PROJECT_ID}

# Step 3: Configure Docker authentication
echo ""
echo "Step 3: Configuring Docker authentication..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Step 4: Build and push Docker image
echo ""
echo "Step 4: Building and pushing Docker image..."
cd "$(dirname "$0")"

# Option A: Use Cloud Build (recommended)
echo "Submitting build to Cloud Build..."
gcloud builds submit --config cloudbuild.yaml --project ${PROJECT_ID} .

# Option B: Build locally (if Cloud Build fails)
# echo "Building locally..."
# docker build -t ${IMAGE_URL} .
# docker push ${IMAGE_URL}

# Step 5: Complete Terraform deployment
echo ""
echo "Step 5: Completing Terraform deployment..."
echo "Please set your GitHub token:"
read -sp "Enter GitHub PAT (ghp_...): " GITHUB_TOKEN
echo ""

export TF_VAR_github_token="${GITHUB_TOKEN}"
terraform init
terraform apply -auto-approve

# Step 6: Show results
echo ""
echo "================================================"
echo "Deployment Complete!"
echo "================================================"
echo ""
echo "Outputs:"
terraform output

echo ""
echo "To view logs:"
echo "  gcloud run services logs read github-runner --region=${REGION}"

echo ""
echo "To check runner status:"
echo "  Visit: https://github.com/netra-systems/netra-apex/settings/actions/runners"