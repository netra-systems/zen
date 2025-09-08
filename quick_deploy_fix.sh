#!/bin/bash
# Quick deployment of DatabaseSessionManager fix to staging

set -e

echo "🔧 EMERGENCY FIX: Deploying DatabaseSessionManager import fix to staging"
echo "   Issue: Agent startup failing due to missing DatabaseSessionManager import"
echo "   Fix: Added proper import to goals_triage_sub_agent.py"

# Build using Cloud Build with staging dockerfile  
echo "📦 Building image using Cloud Build..."
gcloud builds submit \
    --config=cloudbuild.staging.yaml \
    --project=netra-staging \
    --substitutions=_ENVIRONMENT=staging \
    --verbosity=error

# Deploy the built image
echo "🚀 Deploying to Cloud Run staging..."
gcloud run services update netra-backend-staging \
    --region=us-central1 \
    --project=netra-staging \
    --image=gcr.io/netra-staging/netra-backend-staging:latest \
    --verbosity=error

echo "✅ Emergency fix deployed successfully!"
echo "   Testing WebSocket connections now..."