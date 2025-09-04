---
allowed-tools: ["Bash", "Task"]
description: "Audit GCP Cloud Run logs with automatic Five Whys debugging"
argument-hint: "<service> [hours]"
---

# 🌐 GCP Logs Audit with Auto-Debug

Audit Google Cloud Platform logs for staging/production services with automatic error debugging.

## Configuration
- **Service:** ${1:-all}
- **Time Range:** ${2:-1} hours
- **Project:** netra-staging
- **Region:** us-central1
- **Auto-Debug:** Enabled with Five Whys

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

### 4. Error Collection & Analysis
!echo "\n⚠️ ERROR ANALYSIS & COLLECTION:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Collect critical errors
!echo "\n🔴 Critical/Emergency Errors:"
!gcloud logging read "resource.type=cloud_run_revision AND (severity>=CRITICAL)" --limit 20 --format="value(textPayload)" --freshness=${2:-1}h > /tmp/gcp_critical_errors.log 2>/dev/null
!if [ -s /tmp/gcp_critical_errors.log ]; then
    cat /tmp/gcp_critical_errors.log | head -10
    echo "CRITICAL_ERRORS_FOUND=true" > /tmp/gcp_error_status.env
else
    echo "✅ No critical errors"
    echo "CRITICAL_ERRORS_FOUND=false" > /tmp/gcp_error_status.env
fi

# Collect standard errors
!echo "\n🟠 Standard Errors:"
!gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" --limit 50 --format="value(textPayload)" --freshness=${2:-1}h > /tmp/gcp_standard_errors.log 2>/dev/null
!if [ -s /tmp/gcp_standard_errors.log ]; then
    cat /tmp/gcp_standard_errors.log | head -10
    echo "STANDARD_ERRORS_FOUND=true" >> /tmp/gcp_error_status.env
else
    echo "✅ No standard errors"
    echo "STANDARD_ERRORS_FOUND=false" >> /tmp/gcp_error_status.env
fi

# Collect warnings
!echo "\n🟡 Warnings:"
!gcloud logging read "resource.type=cloud_run_revision AND severity=WARNING" --limit 20 --format="value(textPayload)" --freshness=${2:-1}h > /tmp/gcp_warnings.log 2>/dev/null
!if [ -s /tmp/gcp_warnings.log ]; then
    cat /tmp/gcp_warnings.log | head -5
    echo "WARNINGS_FOUND=true" >> /tmp/gcp_error_status.env
else
    echo "✅ No warnings"
    echo "WARNINGS_FOUND=false" >> /tmp/gcp_error_status.env
fi

### 5. Performance & HTTP Error Analysis
!echo "\n📈 PERFORMANCE & HTTP ERRORS:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Collect 5xx errors
!echo "\n🔄 5xx Status Codes:"
!gcloud logging read "resource.type=cloud_run_revision AND httpRequest.status>=500" --limit 20 --format="value(timestamp,httpRequest.status,httpRequest.requestUrl,textPayload)" --freshness=${2:-1}h > /tmp/gcp_5xx_errors.log 2>/dev/null
!if [ -s /tmp/gcp_5xx_errors.log ]; then
    cat /tmp/gcp_5xx_errors.log | head -10
    echo "HTTP_5XX_ERRORS_FOUND=true" >> /tmp/gcp_error_status.env
else
    echo "✅ No 5xx errors"
    echo "HTTP_5XX_ERRORS_FOUND=false" >> /tmp/gcp_error_status.env
fi

!echo "\n⏱️ Request Latencies (>1s):"
!gcloud logging read "resource.type=cloud_run_revision AND httpRequest.latency>\"1s\"" --limit 10 --format="table(timestamp,resource.labels.service_name,httpRequest.latency,httpRequest.requestUrl)" --freshness=${2:-1}h || echo "✅ No slow requests"

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

### 8. Error Prioritization & Selection
!echo "\n🎯 ERROR PRIORITIZATION:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Analyze and prioritize errors for debugging
!if [ -s /tmp/gcp_critical_errors.log ] || [ -s /tmp/gcp_standard_errors.log ] || [ -s /tmp/gcp_5xx_errors.log ]; then
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
    
    echo "\n📍 Primary GCP error selected for debugging ($ERROR_PRIORITY):"
    echo "Source: $ERROR_SOURCE"
    echo "Error: $GCP_PRIMARY_ERROR"
    echo "$ERROR_SOURCE: $GCP_PRIMARY_ERROR" > /tmp/gcp_primary_error.txt
    echo "GCP_ERRORS_FOUND=true" > /tmp/gcp_debug_trigger.env
else
    echo "✅ No GCP errors requiring immediate debugging"
    echo "GCP_ERRORS_FOUND=false" > /tmp/gcp_debug_trigger.env
fi

### 9. Automatic Error Debugging Trigger

# Check if errors need debugging
!source /tmp/gcp_debug_trigger.env 2>/dev/null || true
!if [ "$GCP_ERRORS_FOUND" = "true" ]; then
    echo "\n🚨 INITIATING AUTOMATIC GCP ERROR DEBUGGING:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    GCP_ERROR=$(cat /tmp/gcp_primary_error.txt 2>/dev/null || echo "Unknown GCP Cloud Run error")
    echo "Launching Five Whys analysis with dynamic agent allocation..."
    echo ""
    echo "Error being debugged: $GCP_ERROR"
    echo ""
    echo "🤖 Invoking /debug-error command for deep analysis..."
fi

### 10. Conditional Debug-Error Invocation

@Task: Automatically debug GCP Cloud Run errors if found
If critical errors, 5xx errors, or frequent errors were detected in GCP logs:
1. Read /tmp/gcp_primary_error.txt to get the error description
2. Invoke the /debug-error slash command with that error
3. Use Five Whys methodology to find root cause
4. Dynamically allocate specialist agents based on error type:
   - For 5xx errors: HTTPErrorSpecialist agent
   - For async errors: AsyncPythonExpert agent
   - For memory issues: PerformanceEngineer agent
   - For auth failures: SecurityAuditor agent
   - For deployment issues: DevOpsSpecialist agent
5. Implement fix with 80% consensus threshold

The debug-error command should be invoked as:
/debug-error "GCP_ERROR_FROM_LOGS"

Where GCP_ERROR_FROM_LOGS is the content from /tmp/gcp_primary_error.txt

### 11. Audit Summary & Recommendations
!echo "\n📋 AUDIT SUMMARY:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
!echo "Timestamp: $(date)"
!echo "Services Audited: ${1:-all}"
!echo "Time Range: Last ${2:-1} hours"
!echo "Project: $(gcloud config get-value project)"

!echo "\n📊 POST-AUDIT RECOMMENDATIONS:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

!if [ "$GCP_ERRORS_FOUND" = "true" ]; then
    echo "⚠️ Critical issues detected in GCP Cloud Run"
    echo "1. ⏳ Automatic debugging in progress via /debug-error"
    echo "2. 📝 Review Five Whys analysis when complete"
    echo "3. 🔧 Deploy fix to staging after consensus"
    echo "4. 🚀 Monitor deployment for resolution"
else
    echo "✅ GCP services appear healthy"
    echo "1. 📊 Continue monitoring"
    echo "2. 🔄 Schedule regular audits"
    echo "3. 📈 Review performance metrics"
fi

### 12. Export Options
!echo "\n💾 To export full logs for analysis:"
!echo "gcloud logging read 'resource.type=cloud_run_revision' --format=json --freshness=${2:-1}h > gcp_logs_$(date +%Y%m%d_%H%M%S).json"

## Usage Examples
- `/audit-gcp-logs` - Audit all services with auto-debug
- `/audit-gcp-logs backend-staging 24` - Audit backend (last 24 hours)
- `/audit-gcp-logs auth-staging 3` - Audit auth service (last 3 hours)

## Features
- **Comprehensive GCP Analysis** - Errors, performance, security, resources
- **Auto-Debug Trigger** - Automatically invokes /debug-error for critical issues
- **Error Prioritization** - Selects most important GCP error for debugging
- **Five Whys Integration** - Deep root cause analysis when errors found
- **Dynamic Agent Allocation** - Cloud/deployment expertise for GCP issues
- **Production-Ready** - Safe for staging/production environments