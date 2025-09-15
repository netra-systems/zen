#!/bin/bash

# GCP Log Collection Script for Last 1 Hour
# Target: netra-backend-staging service in netra-staging project
# Generated: 2025-09-15 14:17:29 PDT
# Time Range: Last 1 hour from current time

set -e

# Configuration
PROJECT="netra-staging"
OUTPUT_FILE="/tmp/gcp_logs_last_hour_$(date +%Y%m%d_%H%M%S).json"

# Calculate timestamps
# Current time is 2025-09-15 14:17:12 PDT = 2025-09-15 21:17:12 UTC
# Last 1 hour: 20:17:12 to 21:17:12 UTC
START_TIME="2025-09-15T20:17:00.000Z"
END_TIME="2025-09-15T21:17:00.000Z"

echo "=========================================="
echo "GCP Log Collection - Last 1 Hour"
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

# Main log collection command based on existing patterns
echo "🔍 Collecting logs from netra-backend-staging service..."
echo "Query parameters:"
echo "  - Service names: netra-backend-staging, netra-service, backend-staging"
echo "  - Severity: WARNING, ERROR, CRITICAL"
echo "  - Time range: $START_TIME to $END_TIME"
echo ""

# Execute the log collection (following patterns from fetch_and_analyze_logs.sh)
gcloud logging read \
  --project="$PROJECT" \
  --format=json \
  --limit=1000 \
  'resource.type="cloud_run_revision" AND 
   (resource.labels.service_name="netra-backend-staging" OR 
    resource.labels.service_name="netra-service" OR 
    resource.labels.service_name="backend-staging") AND 
   (severity="WARNING" OR severity="ERROR" OR severity="CRITICAL") AND 
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
            
            echo "  CRITICAL: $CRITICAL_COUNT"
            echo "  ERROR:    $ERROR_COUNT"
            echo "  WARNING:  $WARNING_COUNT"
            
            # Service name breakdown
            echo ""
            echo "🏷️  SERVICE BREAKDOWN:"
            jq -r '[.[] | .resource.labels.service_name] | sort | group_by(.) | map({service: .[0], count: length}) | .[] | "  \(.service): \(.count)"' "$OUTPUT_FILE" 2>/dev/null || echo "  Unable to parse service breakdown"
            
            # Show sample entries
            echo ""
            echo "📋 SAMPLE LOG ENTRIES (First 2):"
            echo "================================="
            jq -r '.[0:2] | .[] | "Timestamp: \(.timestamp)\nSeverity: \(.severity)\nService: \(.resource.labels.service_name)\nMessage: \(.jsonPayload.message // .textPayload // "No message")\n---"' "$OUTPUT_FILE" 2>/dev/null || echo "Unable to parse sample entries"
            
        else
            echo "✅ No warning/error/critical logs found in the specified time range."
            echo "This indicates the service was healthy during this period."
        fi
        
        echo ""
        echo "📁 Full log data saved to: $OUTPUT_FILE"
        echo ""
        echo "🔧 COMMANDS USED:"
        echo "================"
        echo "gcloud logging read \\"
        echo "  --project=\"$PROJECT\" \\"
        echo "  --format=json \\"
        echo "  --limit=1000 \\"
        echo "  'resource.type=\"cloud_run_revision\" AND"
        echo "   (resource.labels.service_name=\"netra-backend-staging\" OR"
        echo "    resource.labels.service_name=\"netra-service\" OR"
        echo "    resource.labels.service_name=\"backend-staging\") AND"
        echo "   (severity=\"WARNING\" OR severity=\"ERROR\" OR severity=\"CRITICAL\") AND"
        echo "   timestamp>=\"$START_TIME\" AND"
        echo "   timestamp<=\"$END_TIME\"'"
        
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