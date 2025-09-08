#!/bin/bash

# GCP Audit Loop with Auto-Debug
# This script runs 100 iterations of GCP log analysis and debugging

PROJECT="netra-staging"
REGION="us-central1"
ITERATIONS=100
CURRENT=1

echo "=========================================================="
echo "           GCP AUDIT LOOP WITH AUTO-DEBUG"
echo "=========================================================="
echo "  Project: $PROJECT"
echo "  Region: $REGION"
echo "  Iterations: $ITERATIONS"
echo "=========================================================="

while [ $CURRENT -le $ITERATIONS ]; do
    echo ""
    echo "=============================================="
    echo "ITERATION $CURRENT/$ITERATIONS"
    echo "Time: $(date)"
    echo "=============================================="
    
    # Step 1: Check service status
    echo ""
    echo "📡 Cloud Run Services Status:"
    gcloud run services list --region $REGION --format="table(SERVICE,REGION,LAST_DEPLOYED_AT)" 2>/dev/null
    
    # Step 2: Collect errors
    echo ""
    echo "🔍 Collecting errors from last hour..."
    
    # Critical errors
    echo "Critical errors:"
    gcloud logging read "resource.type=cloud_run_revision AND severity=CRITICAL" \
        --limit 5 \
        --format="value(timestamp,resource.labels.service_name,textPayload[first=100])" \
        --freshness=1h \
        --project=$PROJECT 2>/dev/null | head -5
    
    # Standard errors
    echo ""
    echo "Recent errors:"
    ERROR_COUNT=$(gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" \
        --limit 10 \
        --format="value(timestamp)" \
        --freshness=1h \
        --project=$PROJECT 2>/dev/null | wc -l)
    
    echo "Found $ERROR_COUNT errors in last hour"
    
    if [ $ERROR_COUNT -gt 0 ]; then
        echo "Top error:"
        gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" \
            --limit 1 \
            --format="value(textPayload)" \
            --freshness=1h \
            --project=$PROJECT 2>/dev/null | head -5
        
        # Save error for debugging
        gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" \
            --limit 1 \
            --format="value(resource.labels.service_name,textPayload)" \
            --freshness=1h \
            --project=$PROJECT 2>/dev/null > /tmp/gcp_current_error.txt
        
        echo ""
        echo "🚨 AUTO-DEBUGGING ERROR..."
        echo "Service: $(head -1 /tmp/gcp_current_error.txt | cut -d' ' -f1)"
        
        # Here we would trigger the debug command
        # For now, just log that we would debug
        echo "Would execute: /debug-error \"$(cat /tmp/gcp_current_error.txt)\""
        
        # Simulate deployment
        echo ""
        echo "🚀 Deploying fix to staging..."
        echo "Would execute: python scripts/deploy_to_gcp.py --project netra-staging --build-local"
        
        # Short wait before next iteration
        echo ""
        echo "⏳ Waiting 60 seconds before next iteration..."
        sleep 60
    else
        echo "✅ No errors found"
        echo ""
        echo "⏳ Waiting 180 seconds before next iteration..."
        sleep 180
    fi
    
    # Increment counter
    CURRENT=$((CURRENT + 1))
done

echo ""
echo "=========================================================="
echo "                  FINAL SUMMARY"
echo "=========================================================="
echo "  Completed $ITERATIONS iterations"
echo "  End time: $(date)"
echo "=========================================================="