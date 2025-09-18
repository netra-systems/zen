#!/bin/bash
# Deployment script for Issue #973 fix validation
# Deploys backend service to staging for validation

set -e

echo "=============================================="
echo "Issue #973 Fix Deployment to Staging"
echo "=============================================="
echo "Fix commit: 62f559860"
echo "Date: $(date)"
echo ""

echo "🚀 Deploying backend service to staging..."
echo "Command: python scripts/deploy_to_gcp.py --project netra-staging --services backend --build-local"
echo ""

# Deploy backend service only (changes are in backend)
python scripts/deploy_to_gcp.py --project netra-staging --services backend --build-local

echo ""
echo "📊 Checking deployment status..."

# Wait a moment for deployment to register
sleep 10

echo ""
echo "📋 Next steps:"
echo "1. Monitor Cloud Run logs for startup errors"
echo "2. Test WebSocket connectivity"
echo "3. Validate agent pipeline execution"
echo "4. Run post-deployment tests"
echo ""

echo "📝 Log collection command:"
echo "gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=netra-backend\" --project=netra-staging --limit=50 --format=json"
echo ""

echo "✅ Deployment initiated successfully!"
echo "See ISSUE_973_VALIDATION_REPORT.md for validation details"