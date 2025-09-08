#!/bin/bash

# GCP Logs Audit Loop with Auto-Debug
# This script runs continuous monitoring of GCP staging services

set -e

# Configuration
SERVICE="${1:-all}"
TIME_RANGE="${2:-15}"
PROJECT="netra-staging"
REGION="us-central1"
ITERATIONS=100

echo "🚀 Starting GCP Audit Loop - $ITERATIONS iterations"
echo "Project: $PROJECT"
echo "Region: $REGION"
echo "Service: $SERVICE"
echo "Time Range: Last $TIME_RANGE minutes"
echo ""

# Main audit loop
for i in $(seq 1 $ITERATIONS); do
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "🔄 AUDIT ITERATION $i/$ITERATIONS - $(date)"
    echo "════════════════════════════════════════════════════════════════"
    
    # Step 1: Service Status Overview
    echo ""
    echo "📡 Cloud Run Services Status:"
    gcloud run services list --region $REGION --format="table(SERVICE,REGION,LAST_DEPLOYED_AT,SERVING_REVISION)" 2>/dev/null || echo "Error fetching service list"
    
    # Step 2: Collect Logs by Service
    if [[ "$SERVICE" == "all" ]]; then
        echo ""
        echo "🔍 Collecting logs from ALL services (last ${TIME_RANGE} minutes)..."
        for service in backend-staging auth-staging frontend-staging; do
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "🌐 Service: $service"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$service" \
                --limit 50 \
                --format="table(timestamp,severity,textPayload[first=100])" \
                --freshness="${TIME_RANGE}m" 2>/dev/null || echo "No logs or service not found"
        done
    else
        echo ""
        echo "🔍 Collecting logs from $SERVICE (last ${TIME_RANGE} minutes)..."
        gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE" \
            --limit 100 \
            --format="table(timestamp,severity,textPayload[first=100])" \
            --freshness="${TIME_RANGE}m"
    fi
    
    # Step 3: Error Collection & Analysis
    echo ""
    echo "⚠️ ERROR ANALYSIS & COLLECTION:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Collect critical errors
    echo ""
    echo "🔴 Critical/Emergency Errors:"
    gcloud logging read "resource.type=cloud_run_revision AND (severity>=CRITICAL)" \
        --limit 20 \
        --format="value(textPayload)" \
        --freshness="${TIME_RANGE}m" > /tmp/gcp_critical_errors.log 2>/dev/null
    
    if [ -s /tmp/gcp_critical_errors.log ]; then
        cat /tmp/gcp_critical_errors.log | head -10
        echo "CRITICAL_ERRORS_FOUND=true" > /tmp/gcp_error_status.env
    else
        echo "✅ No critical errors"
        echo "CRITICAL_ERRORS_FOUND=false" > /tmp/gcp_error_status.env
    fi
    
    # Collect standard errors
    echo ""
    echo "🟠 Standard Errors:"
    gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" \
        --limit 50 \
        --format="value(textPayload)" \
        --freshness="${TIME_RANGE}m" > /tmp/gcp_standard_errors.log 2>/dev/null
    
    if [ -s /tmp/gcp_standard_errors.log ]; then
        cat /tmp/gcp_standard_errors.log | head -10
        echo "STANDARD_ERRORS_FOUND=true" >> /tmp/gcp_error_status.env
    else
        echo "✅ No standard errors"
        echo "STANDARD_ERRORS_FOUND=false" >> /tmp/gcp_error_status.env
    fi
    
    # Collect warnings
    echo ""
    echo "🟡 Warnings:"
    gcloud logging read "resource.type=cloud_run_revision AND severity=WARNING" \
        --limit 20 \
        --format="value(textPayload)" \
        --freshness="${TIME_RANGE}m" > /tmp/gcp_warnings.log 2>/dev/null
    
    if [ -s /tmp/gcp_warnings.log ]; then
        cat /tmp/gcp_warnings.log | head -5
        echo "WARNINGS_FOUND=true" >> /tmp/gcp_error_status.env
    else
        echo "✅ No warnings"
        echo "WARNINGS_FOUND=false" >> /tmp/gcp_error_status.env
    fi
    
    # Step 4: Performance & HTTP Error Analysis
    echo ""
    echo "📈 PERFORMANCE & HTTP ERRORS:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Collect 5xx errors
    echo ""
    echo "🔄 5xx Status Codes:"
    gcloud logging read "resource.type=cloud_run_revision AND httpRequest.status>=500" \
        --limit 20 \
        --format="value(timestamp,httpRequest.status,httpRequest.requestUrl,textPayload[first=100])" \
        --freshness="${TIME_RANGE}m" > /tmp/gcp_5xx_errors.log 2>/dev/null
    
    if [ -s /tmp/gcp_5xx_errors.log ]; then
        cat /tmp/gcp_5xx_errors.log | head -10
        echo "HTTP_5XX_ERRORS_FOUND=true" >> /tmp/gcp_error_status.env
    else
        echo "✅ No 5xx errors"
        echo "HTTP_5XX_ERRORS_FOUND=false" >> /tmp/gcp_error_status.env
    fi
    
    echo ""
    echo "⏱️ Request Latencies (>1s):"
    gcloud logging read "resource.type=cloud_run_revision AND httpRequest.latency>\"1s\"" \
        --limit 10 \
        --format="table(timestamp,resource.labels.service_name,httpRequest.latency,httpRequest.requestUrl)" \
        --freshness="${TIME_RANGE}m" || echo "✅ No slow requests"
    
    # Step 5: Memory & Resource Issues
    echo ""
    echo "💾 RESOURCE ANALYSIS:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo ""
    echo "📊 Memory Usage Warnings:"
    gcloud logging read "resource.type=cloud_run_revision AND textPayload:(\"memory\" OR \"heap\" OR \"OOM\")" \
        --limit 10 \
        --format="table(timestamp,resource.labels.service_name,textPayload[first=100])" \
        --freshness="${TIME_RANGE}m" || echo "✅ No memory issues"
    
    echo ""
    echo "🌡️ Cold Start Events:"
    gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"Cold start\"" \
        --limit 10 \
        --format="table(timestamp,resource.labels.service_name)" \
        --freshness="${TIME_RANGE}m" || echo "✅ No recent cold starts"
    
    # Step 6: Error Prioritization & Selection
    echo ""
    echo "🎯 ERROR PRIORITIZATION:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Analyze and prioritize errors for debugging
    if [ -s /tmp/gcp_critical_errors.log ] || [ -s /tmp/gcp_standard_errors.log ] || [ -s /tmp/gcp_5xx_errors.log ]; then
        echo "🔍 Analyzing GCP error patterns for debugging..."
        
        # Priority 1: Critical errors
        if [ -s /tmp/gcp_critical_errors.log ]; then
            GCP_PRIMARY_ERROR=$(head -1 /tmp/gcp_critical_errors.log)
            ERROR_PRIORITY="CRITICAL"
            ERROR_SOURCE="Cloud Run Critical Error"
        # Priority 2: 5xx HTTP errors
        elif [ -s /tmp/gcp_5xx_errors.log ]; then
            GCP_PRIMARY_ERROR=$(head -1 /tmp/gcp_5xx_errors.log | cut -d' ' -f3-)
            ERROR_PRIORITY="HTTP_5XX"
            ERROR_SOURCE="Cloud Run HTTP 500 Error"
        # Priority 3: Standard errors
        elif [ -s /tmp/gcp_standard_errors.log ]; then
            GCP_PRIMARY_ERROR=$(head -1 /tmp/gcp_standard_errors.log)
            ERROR_PRIORITY="STANDARD"
            ERROR_SOURCE="Cloud Run Standard Error"
        fi
        
        echo ""
        echo "📍 Primary GCP error selected for debugging ($ERROR_PRIORITY):"
        echo "Source: $ERROR_SOURCE"
        echo "Error: $GCP_PRIMARY_ERROR"
        echo "$ERROR_SOURCE: $GCP_PRIMARY_ERROR" > /tmp/gcp_primary_error.txt
        echo "GCP_ERRORS_FOUND=true" > /tmp/gcp_debug_trigger.env
    else
        echo "✅ No GCP errors requiring immediate debugging"
        echo "GCP_ERRORS_FOUND=false" > /tmp/gcp_debug_trigger.env
    fi
    
    # Step 7: Automatic Error Debugging Trigger
    source /tmp/gcp_debug_trigger.env 2>/dev/null || true
    if [ "$GCP_ERRORS_FOUND" = "true" ]; then
        echo ""
        echo "🚨 INITIATING AUTOMATIC GCP ERROR DEBUGGING:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        GCP_ERROR=$(cat /tmp/gcp_primary_error.txt 2>/dev/null || echo "Unknown GCP Cloud Run error")
        echo "Error being debugged: $GCP_ERROR"
        echo ""
        echo "🤖 Would invoke /debug-error command for deep analysis..."
        echo "Note: Manual intervention required for debug-error command"
        
        # Create a marker file for manual intervention
        echo "$GCP_ERROR" > /tmp/gcp_error_for_debug_$i.txt
        echo "Created error file: /tmp/gcp_error_for_debug_$i.txt"
    fi
    
    # Step 8: Audit Summary & Recommendations
    echo ""
    echo "📋 AUDIT SUMMARY:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Iteration: $i/$ITERATIONS"
    echo "Timestamp: $(date)"
    echo "Services Audited: $SERVICE"
    echo "Time Range: Last $TIME_RANGE minutes"
    echo "Project: $PROJECT"
    
    echo ""
    echo "📊 POST-AUDIT RECOMMENDATIONS:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ "$GCP_ERRORS_FOUND" = "true" ]; then
        echo "⚠️ Critical issues detected in GCP Cloud Run"
        echo "1. ⏳ Error file created for debugging: /tmp/gcp_error_for_debug_$i.txt"
        echo "2. 📝 Manual intervention required for /debug-error command"
        echo "3. 🔧 Deploy fix to staging after resolution"
        echo "4. 🚀 Monitor deployment for resolution"
    else
        echo "✅ GCP services appear healthy"
        echo "1. 📊 Continue monitoring"
        echo "2. 🔄 Next audit in progress"
        echo "3. 📈 Review performance metrics"
    fi
    
    # Step 9: Export Options
    echo ""
    echo "💾 Full logs exported to: gcp_logs_iteration_${i}_$(date +%Y%m%d_%H%M%S).json"
    gcloud logging read 'resource.type=cloud_run_revision' \
        --format=json \
        --freshness="${TIME_RANGE}m" > "gcp_logs_iteration_${i}_$(date +%Y%m%d_%H%M%S).json" 2>/dev/null
    
    # Step 10: Consider redeployment (manual step)
    echo ""
    echo "🚀 REDEPLOYMENT CHECK:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ "$GCP_ERRORS_FOUND" = "true" ]; then
        echo "⚠️ Errors detected - redeployment may be needed after fixes"
        echo "To redeploy staging, run:"
        echo "python scripts/deploy_to_gcp.py --project netra-staging --build-local"
    else
        echo "✅ No immediate redeployment needed"
    fi
    
    # Wait before next iteration (5 minutes)
    if [ $i -lt $ITERATIONS ]; then
        echo ""
        echo "⏳ Waiting 5 minutes before next audit cycle..."
        echo "Next audit at: $(date -d '+5 minutes' 2>/dev/null || date)"
        sleep 300
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ AUDIT LOOP COMPLETE - $ITERATIONS iterations finished"
echo "Final timestamp: $(date)"
echo "════════════════════════════════════════════════════════════════"