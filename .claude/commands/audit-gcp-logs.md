---
allowed-tools: ["Bash", "Task"]
description: "Audit GCP Cloud Run logs for staging services"
argument-hint: "<service> [hours]"
---

# 🌐 GCP Logs Audit

Audit Google Cloud Platform logs for staging/production services.

## Configuration
- **Service:** ${1:-all}
- **Time Range:** ${2:-1} hours
- **Project:** netra-staging
- **Region:** us-central1

## Authentication Check

### 1. Verify GCP Authentication
!echo "🔐 GCP Authentication Status:"
!gcloud auth list --filter=status:ACTIVE --format="value(account)" || echo "❌ Not authenticated - run: gcloud auth login"
!echo ""
!gcloud config get-value project || echo "No project set"

## Log Collection & Analysis

### 2. Service Status Overview
!echo "\n📡 Cloud Run Services Status:"
!gcloud run services list --region us-central1 --format="table(SERVICE,REGION,LAST_DEPLOYED_AT,SERVING_REVISION)"

### 3. Collect Logs by Service
if [[ "${1:-all}" == "all" ]]; then
    !echo "\n🔍 Collecting logs from ALL services (last ${2:-1} hours)..."
    !for service in backend-staging auth-staging frontend-staging; do
        echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🌐 Service: $service"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$service" --limit 50 --format="table(timestamp,severity,textPayload)" --freshness=${2:-1}h 2>/dev/null || echo "No logs or service not found"
    done
else
    !echo "\n🔍 Collecting logs from $1 (last ${2:-1} hours)..."
    !gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$1" --limit 100 --format="table(timestamp,severity,textPayload)" --freshness=${2:-1}h
fi

### 4. Error Analysis
!echo "\n⚠️ ERROR ANALYSIS:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

!echo "\n🔴 Critical/Emergency Errors:"
!gcloud logging read "resource.type=cloud_run_revision AND (severity>=CRITICAL)" --limit 20 --format="table(timestamp,resource.labels.service_name,textPayload)" --freshness=${2:-1}h || echo "✅ No critical errors"

!echo "\n🟠 Standard Errors:"
!gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" --limit 20 --format="table(timestamp,resource.labels.service_name,textPayload[first=100])" --freshness=${2:-1}h || echo "✅ No errors"

!echo "\n🟡 Warnings:"
!gcloud logging read "resource.type=cloud_run_revision AND severity=WARNING" --limit 10 --format="table(timestamp,resource.labels.service_name,textPayload[first=100])" --freshness=${2:-1}h || echo "✅ No warnings"

### 5. Performance Metrics
!echo "\n📈 PERFORMANCE METRICS:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

!echo "\n⏱️ Request Latencies (>1s):"
!gcloud logging read "resource.type=cloud_run_revision AND httpRequest.latency>\"1s\"" --limit 10 --format="table(timestamp,resource.labels.service_name,httpRequest.latency,httpRequest.requestUrl)" --freshness=${2:-1}h || echo "✅ No slow requests"

!echo "\n🔄 5xx Status Codes:"
!gcloud logging read "resource.type=cloud_run_revision AND httpRequest.status>=500" --limit 10 --format="table(timestamp,resource.labels.service_name,httpRequest.status,httpRequest.requestUrl)" --freshness=${2:-1}h || echo "✅ No 5xx errors"

### 6. Memory & Resource Issues
!echo "\n💾 RESOURCE ANALYSIS:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

!echo "\n📊 Memory Usage Warnings:"
!gcloud logging read "resource.type=cloud_run_revision AND textPayload:(\"memory\" OR \"heap\" OR \"OOM\")" --limit 10 --format="table(timestamp,resource.labels.service_name,textPayload[first=100])" --freshness=${2:-1}h || echo "✅ No memory issues"

!echo "\n🌡️ Cold Start Events:"
!gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"Cold start\"" --limit 10 --format="table(timestamp,resource.labels.service_name)" --freshness=${2:-1}h || echo "✅ No recent cold starts"

### 7. Security & Authentication
!echo "\n🔒 SECURITY ANALYSIS:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

!echo "\n🚫 Authentication Failures:"
!gcloud logging read "resource.type=cloud_run_revision AND (httpRequest.status=401 OR httpRequest.status=403)" --limit 10 --format="table(timestamp,resource.labels.service_name,httpRequest.status,httpRequest.requestUrl)" --freshness=${2:-1}h || echo "✅ No auth failures"

### 8. Audit Summary
!echo "\n📋 AUDIT SUMMARY:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
!echo "Timestamp: $(date)"
!echo "Services Audited: ${1:-all}"
!echo "Time Range: Last ${2:-1} hours"
!echo "Project: $(gcloud config get-value project)"

### 9. Export Options
!echo "\n💾 To export full logs, use:"
!echo "gcloud logging read 'resource.type=cloud_run_revision' --format=json --freshness=${2:-1}h > gcp_logs_$(date +%Y%m%d_%H%M%S).json"

## Usage Examples
- `/audit-gcp-logs` - Audit all services (last 1 hour)
- `/audit-gcp-logs backend-staging 24` - Audit backend (last 24 hours)
- `/audit-gcp-logs auth-staging 3` - Audit auth service (last 3 hours)

## Notes
- Requires `gcloud auth login` first
- Default time range: 1 hour
- Automatically filters by severity
- Focuses on errors, performance, and security