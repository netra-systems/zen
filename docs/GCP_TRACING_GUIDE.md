# GCP Cloud Trace Guide for Netra Apex Staging

## Overview
This guide explains how to use OpenTelemetry with GCP Cloud Trace for observability in the staging environment.

## Setup Steps

### 1. Enable Cloud Trace
```bash
# Run the setup script
./scripts/enable_gcp_tracing_staging.sh
```

### 2. Verify Configuration
```bash
# Check environment variables
gcloud run services describe netra-backend-staging \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env[].name,spec.template.spec.containers[0].env[].value)" | grep OTEL
```

## Viewing Traces

### GCP Console
1. **Cloud Trace Console**: https://console.cloud.google.com/traces/list?project=netra-staging
2. **Trace Explorer**: Filter by service name `netra-backend-staging`
3. **Latency Analysis**: View P50, P95, P99 latencies

### Command Line

#### List Recent Traces
```bash
gcloud trace traces list \
  --project=netra-staging \
  --limit=10
```

#### View Specific Trace
```bash
gcloud trace traces describe TRACE_ID \
  --project=netra-staging
```

#### Query Logs with Trace Correlation
```bash
# View logs with trace IDs
gcloud logging read \
  "resource.type=cloud_run_revision AND 
   resource.labels.service_name=netra-backend-staging AND
   trace!=''" \
  --project=netra-staging \
  --limit=20 \
  --format=json | jq '.[] | {timestamp: .timestamp, trace: .trace, message: .textPayload}'
```

## Trace Correlation

### Finding Traces for Specific Requests

1. **By Request ID**:
```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND 
   jsonPayload.request_id='YOUR_REQUEST_ID'" \
  --project=netra-staging \
  --format="value(trace)"
```

2. **By User ID**:
```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND 
   jsonPayload.user_id='USER_ID'" \
  --project=netra-staging \
  --format="value(trace)"
```

3. **By Error**:
```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND 
   severity>=ERROR" \
  --project=netra-staging \
  --limit=10 \
  --format="table(timestamp,trace,jsonPayload.error)"
```

## Analyzing Agent Execution

### View Agent Traces
```bash
# Find agent execution traces
gcloud logging read \
  "resource.type=cloud_run_revision AND 
   jsonPayload.agent_name!=''" \
  --project=netra-staging \
  --limit=10 \
  --format="table(timestamp,trace,jsonPayload.agent_name,jsonPayload.operation)"
```

### WebSocket Event Traces
```bash
# Track WebSocket events
gcloud logging read \
  "resource.type=cloud_run_revision AND 
   (jsonPayload.event_type='agent_started' OR 
    jsonPayload.event_type='agent_completed')" \
  --project=netra-staging \
  --limit=20
```

## Performance Analysis

### Slow Request Analysis
```bash
# Find requests taking >1 second
gcloud logging read \
  "resource.type=cloud_run_revision AND 
   httpRequest.latency>'1s'" \
  --project=netra-staging \
  --limit=10 \
  --format="table(timestamp,httpRequest.latency,httpRequest.requestUrl,trace)"
```

### Database Query Performance
```bash
# View database query traces
gcloud trace traces list \
  --project=netra-staging \
  --filter="root_span.name:*database*" \
  --limit=10
```

## Sampling Configuration

Current staging configuration:
- **Sampling Rate**: 10% (0.1)
- **Strategy**: Trace ID ratio-based sampling

To adjust sampling:
```bash
gcloud run services update netra-backend-staging \
  --update-env-vars="OTEL_SAMPLING_RATE=0.25" \
  --region=us-central1
```

## Custom Trace Attributes

The system automatically adds:
- `user.id` - User identifier
- `thread.id` - Conversation thread
- `agent.name` - Agent being executed
- `agent.operation` - Operation being performed
- `http.request_id` - Request correlation ID

## Troubleshooting

### Traces Not Appearing
1. Check if Cloud Trace API is enabled:
```bash
gcloud services list --enabled | grep cloudtrace
```

2. Verify environment variables:
```bash
gcloud run services describe netra-backend-staging \
  --region=us-central1 \
  --format=yaml | grep OTEL
```

3. Check application logs for telemetry initialization:
```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND 
   textPayload:'Cloud Trace initialized'" \
  --project=netra-staging \
  --limit=5
```

### Missing Spans
- Ensure sampling rate is not too low
- Check if auto-instrumentation is working
- Verify trace context propagation between services

## Best Practices

1. **Sampling Rate**:
   - Staging: 10% (0.1)
   - Production: 1% (0.01) or lower

2. **Custom Spans**:
   - Add spans for critical business operations
   - Include relevant attributes for debugging

3. **Performance**:
   - Monitor trace export latency
   - Adjust batch processor settings if needed

4. **Cost Management**:
   - Monitor Cloud Trace usage in billing
   - Adjust sampling rate to control costs

## Integration with Other GCP Services

### Cloud Logging
Traces are automatically correlated with logs using the `trace` field.

### Cloud Monitoring
Create alerts based on trace metrics:
```bash
# Example: Alert on high latency
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Latency Alert" \
  --condition-display-name="P95 > 2s" \
  --condition-expression='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_latencies" AND metric.label.percentile="95" > 2000'
```

### Error Reporting
Exceptions in traces automatically appear in Error Reporting.

## References
- [GCP Cloud Trace Documentation](https://cloud.google.com/trace/docs)
- [OpenTelemetry Python Documentation](https://opentelemetry-python.readthedocs.io/)
- [Cloud Run Observability](https://cloud.google.com/run/docs/monitoring)