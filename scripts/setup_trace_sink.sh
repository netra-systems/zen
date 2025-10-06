#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <gcp-project> <bigquery-dataset>" >&2
  exit 1
fi

PROJECT_ID="$1"
DATASET="$2"
SINK_NAME="zen-community-trace-sink"

echo "Creating BigQuery dataset ${PROJECT_ID}:${DATASET} (if not present)..."
bq --location=US mk --dataset "${PROJECT_ID}:${DATASET}" || true

echo "Creating Cloud Trace sink '${SINK_NAME}'..."
gcloud logging sinks create "${SINK_NAME}" \
  "bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/${DATASET}" \
  --log-filter='resource.type="cloud_trace_span" AND jsonPayload.name="zen.instance"' \
  --project="${PROJECT_ID}" || true

echo "Granting writer role to sink service account..."
SVC_ACCOUNT=$(gcloud logging sinks describe "${SINK_NAME}" --project="${PROJECT_ID}" --format='value(writerIdentity)')
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="${SVC_ACCOUNT}" \
  --role="roles/bigquery.dataEditor"

echo "Sink setup complete."

