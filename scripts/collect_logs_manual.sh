#!/bin/bash

# GCP Log Collection Script for Manual Execution
# Target: netra-backend-staging service logs from last hour
# Time: Sept 17, 2025 - 00:30 UTC to current time (approximately 01:30 UTC)

set -e

# Configuration
PROJECT="netra-staging"
SERVICE_NAME="netra-backend-staging"
START_TIME="2025-09-17T00:30:00Z"
OUTPUT_FILE="/Users/anthony/Desktop/netra-apex/gcp_logs_backend.json"

echo "=========================================="
echo "GCP Backend Log Collection - Last Hour"
echo "=========================================="
echo "Project: $PROJECT"
echo "Service: $SERVICE_NAME"
echo "Start Time: $START_TIME"
echo "Output File: $OUTPUT_FILE"
echo "Current Time: $(date)"
echo "=========================================="

# Check authentication
echo "🔐 Checking GCP authentication..."
CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || echo "NONE")
if [ "$CURRENT_ACCOUNT" = "NONE" ]; then
    echo "❌ ERROR: No active GCP account found."
    echo "Please authenticate with:"
    echo "  gcloud auth login"
    echo "  gcloud config set project $PROJECT"
    exit 1
fi

echo "✅ Authenticated as: $CURRENT_ACCOUNT"

# Set project if needed
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "NONE")
if [ "$CURRENT_PROJECT" != "$PROJECT" ]; then
    echo "⚠️ Setting project to $PROJECT"
    gcloud config set project $PROJECT
fi

# Execute the exact command as requested
echo "📊 Collecting logs from $SERVICE_NAME service..."
echo "Query: resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND severity>=WARNING AND timestamp>=\"$START_TIME\""
echo ""

gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND severity>=WARNING AND timestamp>=\"$START_TIME\"" \
  --limit=500 \
  --format=json \
  --project=$PROJECT > "$OUTPUT_FILE"

# Check results
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
            echo "🔍 SEVERITY BREAKDOWN:"
            
            # Count by severity
            CRITICAL_COUNT=$(jq '[.[] | select(.severity=="CRITICAL")] | length' "$OUTPUT_FILE" 2>/dev/null || echo "0")
            ERROR_COUNT=$(jq '[.[] | select(.severity=="ERROR")] | length' "$OUTPUT_FILE" 2>/dev/null || echo "0")
            WARNING_COUNT=$(jq '[.[] | select(.severity=="WARNING")] | length' "$OUTPUT_FILE" 2>/dev/null || echo "0")
            
            echo "  CRITICAL: $CRITICAL_COUNT"
            echo "  ERROR:    $ERROR_COUNT"
            echo "  WARNING:  $WARNING_COUNT"
            
            # Timestamp range
            echo ""
            echo "📅 TIMESTAMP RANGE:"
            EARLIEST=$(jq -r '.[0].timestamp // "N/A"' "$OUTPUT_FILE" 2>/dev/null)
            LATEST=$(jq -r '.[-1].timestamp // "N/A"' "$OUTPUT_FILE" 2>/dev/null)
            echo "  Earliest: $EARLIEST"
            echo "  Latest:   $LATEST"
            
            # Show critical errors if any
            if [ "$CRITICAL_COUNT" -gt 0 ] || [ "$ERROR_COUNT" -gt 0 ]; then
                echo ""
                echo "🚨 CRITICAL/ERROR PATTERNS:"
                jq -r '.[] | select(.severity=="CRITICAL" or .severity=="ERROR") | "[\(.severity)] \(.timestamp): \(.jsonPayload.message // .textPayload // "No message")"' "$OUTPUT_FILE" 2>/dev/null | head -5
            fi
            
        else
            echo "✅ No WARNING+ logs found in the specified time range."
            echo "This indicates the backend service was healthy during this period."
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
    echo "3. Check permissions: gcloud logging read --limit=1 --project=$PROJECT"
    exit 1
fi

echo ""
echo "✅ Log collection completed successfully!"
echo "File location: $OUTPUT_FILE"