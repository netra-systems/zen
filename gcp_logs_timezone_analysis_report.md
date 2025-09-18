# GCP Logs Timezone and Timing Analysis Report

**Generated:** 2025-09-16
**Project:** netra-staging
**Service:** netra-backend-staging
**Analysis Source:** Recent log files from 2025-09-15 18:44 - 20:03

## 🕐 Timezone and Timestamp Information

### Timestamp Format Analysis

Based on analysis of recent GCP logs from the Netra Apex backend service:

**Primary Timestamp Format:**
```
"timestamp": "2025-09-16T01:42:58.995733Z"
```

**Key Findings:**
- ✅ **Timezone:** UTC (indicated by 'Z' suffix)
- ✅ **Format:** ISO 8601 standard with microsecond precision
- ✅ **Consistency:** All GCP Cloud Logging timestamps are in UTC
- ✅ **Precision:** Microsecond level (6 decimal places)

### Additional Time Fields

**Receive Timestamp:**
```
"receiveTimestamp": "2025-09-16T01:43:05.967637095Z"
```
- Nanosecond precision (9 decimal places)
- Also in UTC timezone

**Application-Level Timestamps (in JSON payloads):**
```json
"jsonPayload": {
  "timestamp": "2025-09-16T01:42:58.220787+00:00"
}
```
- Uses `+00:00` UTC offset notation instead of `Z`
- Same timezone (UTC) but different notation

## 📋 Log Structure Analysis

### Complete Log Entry Structure

```json
{
  "timestamp": "2025-09-16T01:42:58.995733Z",
  "receiveTimestamp": "2025-09-16T01:43:05.967637095Z",
  "severity": "ERROR",
  "insertId": "68c8c0a9000bf7222eab06a3",
  "resource": {
    "type": "cloud_run_revision",
    "labels": {
      "project_id": "netra-staging",
      "service_name": "netra-backend-staging",
      "configuration_name": "netra-backend-staging",
      "revision_name": "netra-backend-staging-00750-69k",
      "location": "us-central1"
    }
  },
  "labels": {
    "instanceId": "0069c7a9889334f2abf231795ba9fd119df...",
    "migration-run": "1757350810",
    "vpc-connectivity": "enabled"
  },
  "logName": "projects/netra-staging/logs/run.googleapis.com%2Frequests",
  "trace": "projects/netra-staging/traces/bc37fd4d64cefc05745037f87ab79384",
  "spanId": "f3f576a33323a516",
  "textPayload": "Error message text...",
  "jsonPayload": {
    "message": "Structured log message",
    "error": {
      "type": "ModuleNotFoundError",
      "value": "No module named 'netra_backend.app.services.monitoring'"
    },
    "labels": {
      "function": "callHandlers",
      "line": "1706",
      "module": "logging"
    },
    "timestamp": "2025-09-16T01:42:58.220787+00:00"
  },
  "httpRequest": {
    "method": "GET",
    "url": "https://api.staging.netrasystems.ai/health",
    "status": 503,
    "userAgent": "python-httpx/0.28.1",
    "remoteIp": "68.5.230.82",
    "latency": "3.786648988s",
    "responseSize": "67",
    "requestSize": "327",
    "serverIp": "34.54.41.44",
    "protocol": "HTTP/1.1"
  },
  "errorGroups": [
    {
      "id": "CJmUvoHgqq23pAE"
    }
  ]
}
```

## 🚨 Recent Error Analysis

### Critical Issues Found (Last Hour)

**1. Module Import Error (Critical)**
```
ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
```
- **Impact:** Prevents application startup
- **Location:** middleware_setup.py line 836
- **Frequency:** Multiple occurrences across instances
- **Severity:** ERROR

**2. Worker Boot Failures**
```
[2025-09-16 01:42:58 +0000] [13] [ERROR] Reason: Worker failed to boot.
```
- **Impact:** Service unavailability
- **Root Cause:** Missing monitoring module
- **Severity:** ERROR

**3. Health Check Failures**
```
HTTP 503 errors on /health endpoint
Response time: 3.786648988s (very slow)
```
- **Impact:** Load balancer health checks failing
- **Status:** 503 Service Unavailable
- **User Agent:** python-httpx/0.28.1 (monitoring system)

### Log Severity Distribution

From recent samples:
- **ERROR:** ~60 entries (critical issues)
- **WARNING:** ~124 entries
- **INFO:** ~4815 entries (mostly empty/system logs)
- **NOTICE:** ~2 entries

## 🔧 Service Configuration

### Backend Service Details
- **Service Name:** netra-backend-staging
- **Project:** netra-staging
- **Location:** us-central1
- **Current Revision:** netra-backend-staging-00750-69k
- **VPC Connectivity:** Enabled
- **Migration Run:** 1757350810

### Infrastructure Labels
- **Instance IDs:** Long hex strings (rotating)
- **vpc-connectivity:** enabled
- **migration-run:** 1757350810

## 📊 Log Sources

### Primary Log Streams
1. **requests** - HTTP request/response logs
2. **stderr** - Application error output
3. **system** - Cloud Run system events

### Key Log Names
- `projects/netra-staging/logs/run.googleapis.com%2Frequests`
- `projects/netra-staging/logs/run.googleapis.com%2Fstderr`
- `projects/netra-staging/logs/run.googleapis.com%2Fvarlog%2Fsystem`

## 🎯 Recommendations

### Immediate Actions Required
1. **Fix Missing Module:** Create or restore `netra_backend.app.services.monitoring`
2. **Monitor Service Health:** Address 503 errors on health endpoints
3. **Review Middleware Setup:** Fix import failures in middleware_setup.py

### Monitoring Setup
- All timestamps are in UTC (confirmed)
- Log collection should filter for severity >= WARNING for actionable issues
- Focus on stderr logs for application errors
- Monitor health endpoint response times and status codes

### Time Conversion Notes
- GCP logs are in UTC
- For PDT (Pacific Daylight Time): UTC - 7 hours
- For PST (Pacific Standard Time): UTC - 8 hours
- Example: `2025-09-16T01:42:58Z` UTC = `2025-09-15T18:42:58` PDT

## 🔍 Log Query Examples

### Get Recent Errors (Last 15 minutes)
```bash
gcloud logging read 'timestamp>="{start_time}Z" AND resource.type="cloud_run_revision" AND resource.labels.service_name="netra-backend-staging" AND severity>=ERROR' --project netra-staging --format json --limit 100
```

### Monitor Health Check Failures
```bash
gcloud logging read 'httpRequest.url="https://api.staging.netrasystems.ai/health" AND httpRequest.status>=500' --project netra-staging --format json
```

### Application-Level Errors
```bash
gcloud logging read 'resource.labels.service_name="netra-backend-staging" AND logName="projects/netra-staging/logs/run.googleapis.com%2Fstderr" AND severity>=ERROR' --project netra-staging --format json
```

---

**Summary:** GCP logs are consistently in UTC timezone with microsecond precision. The main issue currently is a missing monitoring module causing application startup failures and resulting in 503 health check failures. All log analysis should be done with UTC timestamps.