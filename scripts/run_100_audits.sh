#!/bin/bash

# Run 100 iterations of GCP audit and fix loop
echo "Starting 100 iteration GCP audit loop"
echo "======================================="
echo "Project: netra-staging"
echo "Region: us-central1"
echo "Start time: $(date)"
echo ""

ITERATION=1
MAX_ITERATIONS=100

while [ $ITERATION -le $MAX_ITERATIONS ]; do
    echo "----------------------------------------"
    echo "ITERATION $ITERATION / $MAX_ITERATIONS"
    echo "Time: $(date)"
    echo "----------------------------------------"
    
    # Check for errors
    echo "Checking for errors..."
    ERROR_COUNT=$(gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
        --limit 10 \
        --format="value(timestamp)" \
        --freshness=15m \
        --project=netra-staging 2>/dev/null | wc -l)
    
    echo "Found $ERROR_COUNT errors in last 15 minutes"
    
    if [ $ERROR_COUNT -gt 0 ]; then
        echo "Collecting error details..."
        gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
            --limit 3 \
            --format="table(timestamp,resource.labels.service_name,textPayload[first=80])" \
            --freshness=15m \
            --project=netra-staging 2>/dev/null
        
        # Here you would trigger fixes
        echo "Would trigger auto-fix for these errors"
    else
        echo "No errors found - system healthy"
    fi
    
    # Wait before next iteration
    if [ $ERROR_COUNT -gt 0 ]; then
        echo "Waiting 60 seconds..."
        sleep 60
    else
        echo "Waiting 180 seconds..."
        sleep 180
    fi
    
    ITERATION=$((ITERATION + 1))
done

echo ""
echo "======================================="
echo "COMPLETED 100 ITERATIONS"
echo "End time: $(date)"
echo "======================================="