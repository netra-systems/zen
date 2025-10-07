#!/usr/bin/env bash
# Setup Cloud Trace export to BigQuery
# This requires billing to be enabled on the GCP project

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <gcp-project> <bigquery-dataset>" >&2
  echo "Example: $0 netra-telemetry-public zen_community_raw" >&2
  exit 1
fi

PROJECT_ID="$1"
DATASET="$2"
TRACE_SINK_NAME="cloud-trace-to-bigquery"

echo "==================================================================="
echo "Setting up Cloud Trace → BigQuery Export"
echo "==================================================================="
echo "Project: ${PROJECT_ID}"
echo "Dataset: ${DATASET}"
echo ""
echo "⚠️  IMPORTANT: This requires billing to be enabled on ${PROJECT_ID}"
echo "==================================================================="
echo ""

# Check if billing is enabled
echo "Checking billing status..."
BILLING_ENABLED=$(gcloud beta billing projects describe "${PROJECT_ID}" --format='value(billingEnabled)' 2>/dev/null || echo "false")

if [[ "${BILLING_ENABLED}" != "True" ]]; then
  echo "❌ ERROR: Billing is not enabled on project ${PROJECT_ID}"
  echo ""
  echo "Enable billing at:"
  echo "https://console.cloud.google.com/billing/linkedaccount?project=${PROJECT_ID}"
  echo ""
  exit 1
fi

echo "✅ Billing is enabled"
echo ""

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable cloudtrace.googleapis.com --project="${PROJECT_ID}"
gcloud services enable bigquery.googleapis.com --project="${PROJECT_ID}"
echo "✅ APIs enabled"
echo ""

# Create BigQuery dataset if it doesn't exist
echo "Creating BigQuery dataset (if needed)..."
bq --location=US mk --dataset "${PROJECT_ID}:${DATASET}" 2>/dev/null || echo "Dataset already exists"
echo "✅ Dataset ready"
echo ""

# Create the export sink using Cloud Trace API
echo "Setting up Cloud Trace export to BigQuery..."
echo ""
echo "NOTE: Cloud Trace doesn't have a native 'sink' like Cloud Logging."
echo "You have two options:"
echo ""
echo "Option 1: Use Cloud Trace Console UI"
echo "  1. Go to https://console.cloud.google.com/traces/traces?project=${PROJECT_ID}"
echo "  2. Click 'Export' → 'Configure export'"
echo "  3. Select BigQuery as destination"
echo "  4. Choose dataset: ${DATASET}"
echo "  5. Enable continuous export"
echo ""
echo "Option 2: Use scheduled export script"
echo "  - Run scripts/export_cloud_trace_batch.sh periodically"
echo "  - Set up Cloud Scheduler to automate this"
echo ""
echo "==================================================================="
echo "Setup instructions displayed above"
echo "==================================================================="
