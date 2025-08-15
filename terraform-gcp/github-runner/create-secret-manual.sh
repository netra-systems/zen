#!/bin/bash
# Quick script to create GitHub token secret in the correct GCP project

PROJECT_ID="304612253870"
SECRET_NAME="github-runner-token"

echo "Creating GitHub Runner Token Secret"
echo "===================================="
echo "Project: $PROJECT_ID"
echo ""

# Set the correct project
gcloud config set project $PROJECT_ID

# Enable Secret Manager API
echo "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com

# Create the secret
echo "Creating secret..."
gcloud secrets create $SECRET_NAME \
    --replication-policy="automatic" \
    --project=$PROJECT_ID 2>/dev/null || echo "Secret already exists"

# Add the token
echo ""
echo "Enter your GitHub Personal Access Token:"
echo "(Required scopes: 'repo' for repository runners)"
read -s GITHUB_TOKEN

echo "$GITHUB_TOKEN" | gcloud secrets versions add $SECRET_NAME \
    --data-file=- \
    --project=$PROJECT_ID

# Grant access to service account
echo "Granting access to service account..."
gcloud secrets add-iam-policy-binding $SECRET_NAME \
    --member="serviceAccount:github-runner-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

echo ""
echo "Secret created successfully!"
echo "Now restart your runner instances or re-run terraform apply"