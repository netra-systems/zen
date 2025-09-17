#!/bin/bash

# GCP Log Collection Script for Latest Hour
# Target: netra-backend-staging service in netra-staging project
# Generated: 2025-09-15 22:47:00 UTC
# Time Range: Last 1 hour (approximately 21:47-22:47 UTC)

set -e

# Configuration
PROJECT="netra-staging"
OUTPUT_FILE="/tmp/gcp_logs_latest_$(date +%Y%m%d_%H%M%S).json"

# Calculate timestamps for the requested time range
# Current time is 2025-09-15 22:47 UTC
# Requested range: 21:47:00 to 22:47:00 UTC
START_TIME="2025-09-15T21:47:00.000Z"
END_TIME="2025-09-15T22:47:00.000Z"

echo "=========================================="
echo "GCP Log Collection - Latest Hour"
echo "=========================================="
echo "Project: $PROJECT"
echo "Time Range: $START_TIME to $END_TIME"
echo "Output File: $OUTPUT_FILE"
echo "Current Time: $(date)"
echo "=========================================="

# Check authentication
echo "Checking GCP authentication..."
CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || echo "NONE")
if [ "$CURRENT_ACCOUNT" = "NONE" ]; then
    echo "❌ ERROR: No active GCP account found."
    echo "Please authenticate with:"
    echo "  gcloud auth login"
    echo "  gcloud config set project $PROJECT"
    exit 1
fi

echo "✅ Authenticated as: $CURRENT_ACCOUNT"

# Verify project access
echo "Verifying project access..."
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "NONE")
if [ "$CURRENT_PROJECT" != "$PROJECT" ]; then
    echo "⚠️  Setting project to $PROJECT"
    gcloud config set project $PROJECT
fi

# Main log collection command
echo "🔍 Collecting logs from netra-backend-staging service..."
echo "Query parameters:"
echo "  - Service names: netra-backend-staging, netra-service, backend-staging"
echo "  - Severity: NOTICE, WARNING, ERROR, CRITICAL"
echo "  - Time range: $START_TIME to $END_TIME"
echo ""

# Execute the log collection with broader filter to capture all relevant logs
gcloud logging read \
  --project="$PROJECT" \
  --format=json \
  --limit=2000 \
  'resource.type="cloud_run_revision" AND 
   (resource.labels.service_name="netra-backend-staging" OR 
    resource.labels.service_name="netra-service" OR 
    resource.labels.service_name="backend-staging") AND 
   (severity="NOTICE" OR severity="WARNING" OR severity="ERROR" OR severity="CRITICAL") AND 
   timestamp>="'"$START_TIME"'" AND 
   timestamp<="'"$END_TIME"'"' > "$OUTPUT_FILE"

# Check if command succeeded
if [ $? -eq 0 ]; then
    echo "✅ Logs successfully collected to: $OUTPUT_FILE"
    
    # Analyze the results
    if [ -f "$OUTPUT_FILE" ]; then
        LOG_COUNT=$(jq '. | length' "$OUTPUT_FILE" 2>/dev/null || echo "0")
        echo ""
        echo "📊 COLLECTION SUMMARY:"
        echo "==============================="
        echo "Total log entries: $LOG_COUNT"
        
        if [ "$LOG_COUNT" -gt 0 ]; then
            echo ""
            echo "🔍 LOG TYPE BREAKDOWN:"
            
            # Count by severity
            CRITICAL_COUNT=$(jq '[.[] | select(.severity=="CRITICAL")] | length' "$OUTPUT_FILE" 2>/dev/null || echo "0")
            ERROR_COUNT=$(jq '[.[] | select(.severity=="ERROR")] | length' "$OUTPUT_FILE" 2>/dev/null || echo "0")
            WARNING_COUNT=$(jq '[.[] | select(.severity=="WARNING")] | length' "$OUTPUT_FILE" 2>/dev/null || echo "0")
            NOTICE_COUNT=$(jq '[.[] | select(.severity=="NOTICE")] | length' "$OUTPUT_FILE" 2>/dev/null || echo "0")
            
            echo "  CRITICAL: $CRITICAL_COUNT"
            echo "  ERROR:    $ERROR_COUNT"
            echo "  WARNING:  $WARNING_COUNT"
            echo "  NOTICE:   $NOTICE_COUNT"
            
            # Service name breakdown
            echo ""
            echo "🏷️  SERVICE BREAKDOWN:"
            jq -r '[.[] | .resource.labels.service_name] | sort | group_by(.) | map({service: .[0], count: length}) | .[] | "  \(.service): \(.count)"' "$OUTPUT_FILE" 2>/dev/null || echo "  Unable to parse service breakdown"
            
            # Show sample entries
            echo ""
            echo "📋 SAMPLE LOG ENTRIES (First 3):"
            echo "================================="
            jq -r '.[0:3] | .[] | "Timestamp: \(.timestamp)\nSeverity: \(.severity)\nService: \(.resource.labels.service_name)\nMessage: \(.jsonPayload.message // .textPayload // "No message")\n---"' "$OUTPUT_FILE" 2>/dev/null || echo "Unable to parse sample entries"
            
        else
            echo "✅ No warning/error/critical logs found in the specified time range."
            echo "This indicates the service was healthy during this period."
        fi
        
        echo ""
        echo "📁 Full log data saved to: $OUTPUT_FILE"
        
    else
        echo "❌ ERROR: Output file was not created"
        exit 1
    fi
else
    echo "❌ ERROR: Failed to collect logs"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Verify authentication: gcloud auth list"
    echo "2. Set correct project: gcloud config set project $PROJECT"
    echo "3. Check permissions: gcloud projects get-iam-policy $PROJECT"
    echo "4. Test basic access: gcloud logging read --limit=1 --project=$PROJECT"
    exit 1
fi

echo ""
echo "✅ Log collection completed successfully!"
echo "File location: $OUTPUT_FILE"