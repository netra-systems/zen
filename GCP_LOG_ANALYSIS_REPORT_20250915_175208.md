# GCP Log Analysis Report - Last 1 Hour
**Generated:** 2025-09-15 17:52:08 PDT
**Time Range:** 4:43 PM PDT to 5:43 PM PDT (Sept 15, 2025)
**Service:** netra-backend-staging
**Total Logs:** 1000
**Error/Warning Logs:** 119

## Executive Summary

### Severity Breakdown:
- **ERROR:** 75 incidents
- **WARNING:** 44 incidents

## Clustered Issue Analysis

### 🚨 CLUSTER 1: Missing Monitoring Module (P0 CRITICAL)
**Issue Count:** 75 incidents
**Severity:** P0 CRITICAL

#### Key Log Patterns:
```
ERROR [2025-09-16T00:42:53.583841Z] - Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'
ERROR [2025-09-16T00:42:53.579453Z] - CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'
ERROR [2025-09-16T00:42:53.579428Z] - Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/usr/local/lib/python3.11/site-pack
... and 72 more similar incidents
```

#### Business Impact:
- Service startup failures preventing chat functionality
- Revenue impact: Complete service unavailability
- User experience: Chat interface inaccessible

#### Sample Full JSON Log:
```json
{
  "insertId": "68c8b28d0008e8a1b1cde96c",
  "jsonPayload": {
    "error": {
      "traceback": null,
      "type": "ModuleNotFoundError",
      "value": "No module named 'netra_backend.app.services.monitoring'"
    },
    "labels": {
      "function": "callHandlers",
      "line": "1706",
      "module": "logging"
    },
    "message": "Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'",
    "timestamp": "2025-09-16T00:42:53.575433+00:00"
  },
  "labels": {
    "instanceId": "0069c7a98884f72f87842f75fd12d4cec7d548492b26d9a256dae317529a408cbec0687a105bde74e50bfd89abd6779de27de65b4638b3f3eb7ba1f7abf852ea149628d2deb5c2b8f4db17399bc9",
    "migration-run": "1757350810",
    "vpc-connectivity": "enabled"
  },
  "logName": "projects/netra-staging/logs/run.googleapis.com%2Fstderr",
  "receiveTimestamp": "2025-09-16T00:42:53.643374230Z",
  "resource": {
    "labels": {
      "configuration_name": "netra-backend-staging",
      "location": "us-central1",
      "project_id": "netra-staging",
      "revision_name": "netra-backend-staging-00734-fvm",
      "service_name": "netra-backend-staging"
    },
    "type": "cloud_run_revision"
  },
  "severity": "ERROR",
  "timestamp": "2025-09-16T00:42:53.583841Z"
}
```

---

### 🚨 CLUSTER 2: Container Exit Issues (P0 CRITICAL)
**Issue Count:** 15 incidents
**Severity:** P0 CRITICAL

#### Key Log Patterns:
```
WARNING [2025-09-16T00:42:54.053646Z] - Container called exit(3).
WARNING [2025-09-16T00:42:46.827412Z] - Container called exit(3).
WARNING [2025-09-16T00:42:39.962851Z] - Container called exit(3).
... and 12 more similar incidents
```

#### Business Impact:
- Service containers crashing, causing intermittent outages
- Load balancer routing issues
- User experience degradation during container restarts

#### Sample Full JSON Log:
```json
{
  "insertId": "68c8b28e0000d1b6dd8a748b",
  "labels": {
    "container_name": "netra-backend-staging-1",
    "instanceId": "0069c7a98884f72f87842f75fd12d4cec7d548492b26d9a256dae317529a408cbec0687a105bde74e50bfd89abd6779de27de65b4638b3f3eb7ba1f7abf852ea149628d2deb5c2b8f4db17399bc9",
    "migration-run": "1757350810",
    "vpc-connectivity": "enabled"
  },
  "logName": "projects/netra-staging/logs/run.googleapis.com%2Fvarlog%2Fsystem",
  "receiveTimestamp": "2025-09-16T00:42:54.201992106Z",
  "resource": {
    "labels": {
      "configuration_name": "netra-backend-staging",
      "location": "us-central1",
      "project_id": "netra-staging",
      "revision_name": "netra-backend-staging-00734-fvm",
      "service_name": "netra-backend-staging"
    },
    "type": "cloud_run_revision"
  },
  "severity": "WARNING",
  "textPayload": "Container called exit(3).",
  "timestamp": "2025-09-16T00:42:54.053646Z"
}
```

---

### 🟢 CLUSTER 3: Sentry SDK Issues (P3 LOW)
**Issue Count:** 15 incidents
**Severity:** P3 LOW

#### Key Log Patterns:
```
WARNING [2025-09-16T00:42:53.525896Z] - Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
WARNING [2025-09-16T00:42:46.295520Z] - Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
WARNING [2025-09-16T00:42:39.437037Z] - Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking
... and 12 more similar incidents
```

#### Sample Full JSON Log:
```json
{
  "insertId": "68c8b28d000806483f39b3ea",
  "jsonPayload": {
    "labels": {
      "function": "callHandlers",
      "line": "1706",
      "module": "logging"
    },
    "message": "Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking",
    "timestamp": "2025-09-16T00:42:53.524229+00:00"
  },
  "labels": {
    "instanceId": "0069c7a98884f72f87842f75fd12d4cec7d548492b26d9a256dae317529a408cbec0687a105bde74e50bfd89abd6779de27de65b4638b3f3eb7ba1f7abf852ea149628d2deb5c2b8f4db17399bc9",
    "migration-run": "1757350810",
    "vpc-connectivity": "enabled"
  },
  "logName": "projects/netra-staging/logs/run.googleapis.com%2Fstderr",
  "receiveTimestamp": "2025-09-16T00:42:53.643374230Z",
  "resource": {
    "labels": {
      "configuration_name": "netra-backend-staging",
      "location": "us-central1",
      "project_id": "netra-staging",
      "revision_name": "netra-backend-staging-00734-fvm",
      "service_name": "netra-backend-staging"
    },
    "type": "cloud_run_revision"
  },
  "severity": "WARNING",
  "timestamp": "2025-09-16T00:42:53.525896Z"
}
```

---

### 🟡 CLUSTER 4: Service ID Configuration Issues (P2 MEDIUM)
**Issue Count:** 14 incidents
**Severity:** P2 MEDIUM

#### Key Log Patterns:
```
WARNING [2025-09-16T00:42:52.984106Z] - SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
WARNING [2025-09-16T00:42:45.706796Z] - SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
WARNING [2025-09-16T00:42:38.880313Z] - SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
... and 11 more similar incidents
```

#### Sample Full JSON Log:
```json
{
  "insertId": "68c8b28c000f042a61bd2e23",
  "jsonPayload": {
    "error": {
      "message": "Missing field",
      "severity": "ERROR",
      "timestamp": "2025-09-16T00:42:52.983593Z",
      "traceback": "",
      "type": "str"
    },
    "logger": "shared.logging.unified_logging_ssot",
    "message": "SERVICE_ID contained whitespace - sanitized from 'netra-backend\\n' to 'netra-backend'",
    "service": "netra-service",
    "textPayload": "SERVICE_ID contained whitespace - sanitized from 'netra-backend\\n' to 'netra-backend'",
    "timestamp": "2025-09-16T00:42:52.983580Z",
    "validation": {
      "message_length": 85,
      "severity": "WARNING",
      "validated_at": "2025-09-16T00:42:52.983599Z",
      "zero_empty_guarantee": true
    }
  },
  "labels": {
    "instanceId": "0069c7a98884f72f87842f75fd12d4cec7d548492b26d9a256dae317529a408cbec0687a105bde74e50bfd89abd6779de27de65b4638b3f3eb7ba1f7abf852ea149628d2deb5c2b8f4db17399bc9",
    "migration-run": "1757350810",
    "vpc-connectivity": "enabled"
  },
  "logName": "projects/netra-staging/logs/run.googleapis.com%2Fstdout",
  "receiveTimestamp": "2025-09-16T00:42:53.048698044Z",
  "resource": {
    "labels": {
      "configuration_name": "netra-backend-staging",
      "location": "us-central1",
      "project_id": "netra-staging",
      "revision_name": "netra-backend-staging-00734-fvm",
      "service_name": "netra-backend-staging"
    },
    "type": "cloud_run_revision"
  },
  "severity": "WARNING",
  "timestamp": "2025-09-16T00:42:52.984106Z"
}
```

---

## Timeline Analysis

### Error Timeline (Last 1 Hour):
```
1:13.023 - WARNING - Sentry SDK Issues
1:13.081 - ERROR - Missing Monitoring Module
1:13.083 - ERROR - Missing Monitoring Module
1:13.084 - ERROR - Missing Monitoring Module
1:13.084 - ERROR - Missing Monitoring Module
1:13.084 - ERROR - Missing Monitoring Module
1:13.548 - WARNING - Container Exit Issues
1:19.506 - WARNING - Service ID Configuration Issue
1:20.013 - WARNING - Sentry SDK Issues
1:20.065 - ERROR - Missing Monitoring Module
1:20.065 - ERROR - Missing Monitoring Module
1:20.070 - ERROR - Missing Monitoring Module
1:20.070 - ERROR - Missing Monitoring Module
1:20.071 - ERROR - Missing Monitoring Module
1:20.509 - WARNING - Container Exit Issues
1:26.466 - WARNING - Service ID Configuration Issue
1:27.000 - WARNING - Sentry SDK Issues
1:27.054 - ERROR - Missing Monitoring Module
1:27.056 - ERROR - Missing Monitoring Module
1:27.057 - ERROR - Missing Monitoring Module
... and 99 more events
```

## Immediate Action Items

### P0 CRITICAL (Fix Immediately):
- **Missing Monitoring Module** (75 incidents) - Service startup failures
- **Container Exit Issues** (15 incidents) - Service startup failures

### P1 HIGH (Fix Today):

## Raw Data Access

**Full log file:** `gcp_logs_last_hour_20250915_175001.json`
**Total entries:** 1000
**Error entries:** 119

### GCloud Command Used:
```bash
gcloud logging read "resource.type=cloud_run_revision AND
  resource.labels.service_name=netra-backend-staging AND
  timestamp>=\"2025-09-15T23:43:00.000Z\" AND
  timestamp<=\"2025-09-16T00:43:00.000Z\""
  --limit=1000 --format=json --project=netra-staging
```