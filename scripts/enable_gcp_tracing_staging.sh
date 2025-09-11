#!/bin/bash

# Enable GCP Cloud Trace for Netra Backend Staging
# This script configures OpenTelemetry to export traces to GCP Cloud Trace

set -e

PROJECT_ID="netra-staging"
SERVICE_NAME="netra-backend-staging"
REGION="us-central1"

echo "🔍 Enabling GCP Cloud Trace for $SERVICE_NAME in project $PROJECT_ID"

# Enable Cloud Trace API
echo "📡 Enabling Cloud Trace API..."
gcloud services enable cloudtrace.googleapis.com --project=$PROJECT_ID

# Update Cloud Run service with OpenTelemetry environment variables
echo "🔧 Configuring OpenTelemetry environment variables..."
gcloud run services update $SERVICE_NAME \
  --project=$PROJECT_ID \
  --region=$REGION \
  --update-env-vars="OTEL_ENABLED=true" \
  --update-env-vars="OTEL_SERVICE_NAME=$SERVICE_NAME" \
  --update-env-vars="OTEL_EXPORTER_GCP_TRACE=true" \
  --update-env-vars="OTEL_SAMPLING_STRATEGY=trace_id_ratio" \
  --update-env-vars="OTEL_SAMPLING_RATE=0.1" \
  --update-env-vars="OTEL_RESOURCE_ATTRIBUTES=environment=staging,service.namespace=netra,deployment.environment=staging" \
  --update-env-vars="GCP_PROJECT_ID=$PROJECT_ID" \
  --update-env-vars="CLOUD_REGION=$REGION"

echo "✅ OpenTelemetry configuration complete!"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --project=$PROJECT_ID \
  --region=$REGION \
  --format="value(status.url)")

echo ""
echo "📊 View traces in GCP Console:"
echo "   https://console.cloud.google.com/traces/list?project=$PROJECT_ID"
echo ""
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "🔍 Testing trace generation..."
echo "   Making a test request to generate traces:"
curl -s "$SERVICE_URL/health" > /dev/null && echo "   ✅ Health check successful"

echo ""
echo "⏱️  Wait 1-2 minutes for traces to appear in Cloud Trace console"
echo ""
echo "📝 To view logs with trace correlation:"
echo "   gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --project=$PROJECT_ID --limit=10"