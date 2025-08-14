#!/bin/bash
# Script to restart all GitHub runners after fixing the secret

PROJECT_ID="304612253870"
ZONE="us-central1-a"

echo "Restarting all GitHub Runner instances"
echo "======================================="

# Find all runner instances
INSTANCES=$(gcloud compute instances list \
    --filter="name:gcp-runner-*" \
    --format="value(name)" \
    --project=$PROJECT_ID)

if [ -z "$INSTANCES" ]; then
    echo "No GitHub runner instances found"
    exit 1
fi

echo "Found instances:"
echo "$INSTANCES"
echo ""

for INSTANCE in $INSTANCES; do
    echo "Processing $INSTANCE..."
    
    # Option 1: Reset the instance (full restart)
    echo "  Resetting instance..."
    gcloud compute instances reset $INSTANCE \
        --zone=$ZONE \
        --project=$PROJECT_ID
    
    echo "  Waiting for instance to come back online..."
    sleep 30
    
    # Wait for SSH to be available
    MAX_RETRIES=10
    RETRY_COUNT=0
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if gcloud compute ssh $INSTANCE \
            --zone=$ZONE \
            --project=$PROJECT_ID \
            --command="echo 'SSH ready'" &>/dev/null; then
            echo "  Instance is back online"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "  Waiting for SSH... (attempt $RETRY_COUNT/$MAX_RETRIES)"
        sleep 10
    done
    
    # Check runner status
    echo "  Checking runner status..."
    gcloud compute ssh $INSTANCE \
        --zone=$ZONE \
        --project=$PROJECT_ID \
        --command="sudo systemctl status actions.runner.*.service --no-pager | head -10" 2>/dev/null || echo "  Could not check status"
    
    echo "  Done with $INSTANCE"
    echo ""
done

echo "All instances have been restarted"
echo "Check the runners at: https://github.com/netra-systems/netra-apex/settings/actions/runners"