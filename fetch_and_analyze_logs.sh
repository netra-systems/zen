#!/bin/bash

# Script to fetch GCP logs and analyze them
# Run this script after ensuring you're authenticated with gcloud

echo "Fetching GCP logs for backend-staging service..."

# Fetch the logs
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="backend-staging" AND (severity="WARNING" OR severity="ERROR" OR severity="CRITICAL") AND timestamp>="2025-09-15T05:56:50.000Z"' --limit=500 --format=json --project=netra-staging > /tmp/backend_logs_last_hour.json

if [ $? -eq 0 ]; then
    echo "Logs successfully saved to /tmp/backend_logs_last_hour.json"
    echo "Number of log entries: $(cat /tmp/backend_logs_last_hour.json | jq '. | length')"
    echo ""
    echo "Log analysis will be performed next..."
else
    echo "Failed to fetch logs. Please ensure you're authenticated with:"
    echo "  gcloud auth login"
    echo "  gcloud config set project netra-staging"
    exit 1
fi