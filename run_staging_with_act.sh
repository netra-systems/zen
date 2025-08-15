#!/bin/bash
# Run staging deployment using ACT (GitHub Actions locally)

echo "🚀 Running staging deployment with ACT..."

# Set environment variables for ACT
export ACT=true
export LOCAL_DEPLOY=true

# Run the staging workflow with ACT
# Use --env-file to load secrets if available
if [ -f .env.act ]; then
    echo "Loading environment from .env.act"
    act -W .github/workflows/staging-environment.yml \
        --env-file .env.act \
        --container-architecture linux/amd64 \
        -e event.json \
        workflow_dispatch
else
    echo "No .env.act found, running with minimal environment"
    act -W .github/workflows/staging-environment.yml \
        --container-architecture linux/amd64 \
        -e event.json \
        workflow_dispatch
fi

echo "✅ ACT deployment complete!"