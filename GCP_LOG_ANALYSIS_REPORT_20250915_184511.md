# GCP Log Analysis Report
**Generated:** 2025-09-15 18:45:11
**Log File:** gcp_logs_last_hour_20250915_184401.json
**Total Logs:** 1000
**Error/Warning Logs:** 125

## Cluster Summary

### Cluster 1: P0 P0 - Missing Monitoring Module Exports (45 incidents)
**Category:** `CRITICAL_MISSING_MONITORING_MODULE`
**Priority:** P0
**Incident Count:** 45

**Sample Error:**
```json
{
  "timestamp": "2025-09-16T01:42:58.227763Z",
  "severity": "ERROR",
  "message": "Middleware setup failure details: ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'..."
}
```

**Full Sample Log:**
```json
{
  "insertId": "68c8c0a2000379b301da2c12",
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
    "timestamp": "2025-09-16T01:42:58.220787+00:00"
  },
  "labels": {
    "instanceId": "0069c7a9882bdf09983888d3c0e309f04ad3f0c7cec93d4ef191773d4e97b5e7d9a26519dd106bb88622cb12e700b067398635acace02691d55787ed56286990da9a97728798a62bc7ff7c4b3533e6",
    "migration-run": "1757350810",
    "vpc-connectivity": "enabled"
  },
  "logName": "projects/netra-staging/logs/run.googleapis.com%2Fstderr",
  "receiveTimestamp": "2025-09-16T01:42:58.452663634Z",
  "resource": {
    "labels": {
      "configuration_name": "netra-backend-staging",
      "l...
```

---

### Cluster 2: P0 P0 - Container Exit Failures (9 incidents)
**Category:** `CRITICAL_CONTAINER_EXIT`
**Priority:** P0
**Incident Count:** 9

**Sample Error:**
```json
{
  "timestamp": "2025-09-16T01:42:17.868096Z",
  "severity": "WARNING",
  "message": "Container called exit(3)...."
}
```

**Full Sample Log:**
```json
{
  "insertId": "68c8c079000d3f33d5b1a727",
  "labels": {
    "container_name": "netra-backend-staging-1",
    "instanceId": "0069c7a98824795ed4cca76950d82f38b005d1f6faae180462eb5c736860f476e381f153ee39b01b8bc5afdebe971b31be5ce4325c8451be5e3e448ef8c4c2768590d114c3eed9dd4264ee1df686d1",
    "migration-run": "1757350810",
    "vpc-connectivity": "enabled"
  },
  "logName": "projects/netra-staging/logs/run.googleapis.com%2Fvarlog%2Fsystem",
  "receiveTimestamp": "2025-09-16T01:42:18.168986681Z",
  "resource": {
    "labels": {
      "configuration_name": "netra-backend-staging",
      "location": "us-central1",
      "project_id": "netra-staging",
      "revision_name": "netra-backend-staging-00742-b95",
      "service_name": "netra-backend-staging"
    },
    "type": "cloud_run_revision"
  },
  "severity": "WARNING",
  "textPayload": "Container called exit(3).",
  "timestamp": "2025-09-16T01:42:17.868096Z"
}...
```

---

### Cluster 3: P0 P0 - Middleware Setup Failures (15 incidents)
**Category:** `CRITICAL_MIDDLEWARE_SETUP_FAILURE`
**Priority:** P0
**Incident Count:** 15

**Sample Error:**
```json
{
  "timestamp": "2025-09-16T01:42:58.221621Z",
  "severity": "ERROR",
  "message": "CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'..."
}
```

**Full Sample Log:**
```json
{
  "insertId": "68c8c0a2000361b59b29276c",
  "jsonPayload": {
    "labels": {
      "function": "callHandlers",
      "line": "1706",
      "module": "logging"
    },
    "message": "CRITICAL: Enhanced middleware setup failed: No module named 'netra_backend.app.services.monitoring'",
    "timestamp": "2025-09-16T01:42:58.220652+00:00"
  },
  "labels": {
    "instanceId": "0069c7a9882bdf09983888d3c0e309f04ad3f0c7cec93d4ef191773d4e97b5e7d9a26519dd106bb88622cb12e700b067398635acace02691d55787ed56286990da9a97728798a62bc7ff7c4b3533e6",
    "migration-run": "1757350810",
    "vpc-connectivity": "enabled"
  },
  "logName": "projects/netra-staging/logs/run.googleapis.com%2Fstderr",
  "receiveTimestamp": "2025-09-16T01:42:58.452663634Z",
  "resource": {
    "labels": {
      "configuration_name": "netra-backend-staging",
      "location": "us-central1",
      "project_id": "netra-staging",
      "revision_name": "netra-backend-staging-00742-b95",
      "service_name": "netra-backend-staging"
  ...
```

---

### Cluster 4: P1 P1 - WebSocket Connectivity Issues (15 incidents)
**Category:** `HIGH_WEBSOCKET_CONNECTIVITY`
**Priority:** P1
**Incident Count:** 15

**Sample Error:**
```json
{
  "timestamp": "2025-09-16T01:42:58.227343Z",
  "severity": "ERROR",
  "message": "Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/gunicorn/arbiter.py", line 608, in spawn_worker
    worker.init_process()
  File "/usr/local/lib/python3.11/site-pack..."
}
```

**Full Sample Log:**
```json
{
  "errorGroups": [
    {
      "id": "CJmUvoHgqq23pAE"
    }
  ],
  "insertId": "68c8c0a20003780f35b3eb6f",
  "labels": {
    "instanceId": "0069c7a9882bdf09983888d3c0e309f04ad3f0c7cec93d4ef191773d4e97b5e7d9a26519dd106bb88622cb12e700b067398635acace02691d55787ed56286990da9a97728798a62bc7ff7c4b3533e6",
    "migration-run": "1757350810",
    "vpc-connectivity": "enabled"
  },
  "logName": "projects/netra-staging/logs/run.googleapis.com%2Fstderr",
  "receiveTimestamp": "2025-09-16T01:42:58.452663634Z",
  "resource": {
    "labels": {
      "configuration_name": "netra-backend-staging",
      "location": "us-central1",
      "project_id": "netra-staging",
      "revision_name": "netra-backend-staging-00742-b95",
      "service_name": "netra-backend-staging"
    },
    "type": "cloud_run_revision"
  },
  "severity": "ERROR",
  "textPayload": "Traceback (most recent call last):\n  File \"/usr/local/lib/python3.11/site-packages/gunicorn/arbiter.py\", line 608, in spawn_worker\n    worker.ini...
```

---

### Cluster 5: P2 P2 - Generic Application Errors (11 incidents)
**Category:** `MEDIUM_GENERIC_ERRORS`
**Priority:** P2
**Incident Count:** 11

**Sample Error:**
```json
{
  "timestamp": "2025-09-16T01:42:58.995733Z",
  "severity": "ERROR",
  "message": "The request failed because either the HTTP response was malformed or connection to the instance had an error. Additional troubleshooting documentation can be found at: https://cloud.google.com/run/doc..."
}
```

**Full Sample Log:**
```json
{
  "httpRequest": {
    "latency": "3.786648988s",
    "protocol": "HTTP/1.1",
    "remoteIp": "68.5.230.82",
    "requestMethod": "GET",
    "requestSize": "327",
    "requestUrl": "https://api.staging.netrasystems.ai/health",
    "responseSize": "67",
    "serverIp": "34.54.41.44",
    "status": 503,
    "userAgent": "python-httpx/0.28.1"
  },
  "insertId": "68c8c0a9000bf7222eab06a3",
  "labels": {
    "instanceId": "0069c7a9887544eefac3a648639e78fce573cf3ef4ce1929c7758a2c196cb71d4fc6344c2fded440ca5d3d197c947ab48e5d9c1df5a76700fb08d5b827c54efd6373c4944a98c6af37774c04b6f7f1",
    "migration-run": "1757350810",
    "vpc-connectivity": "enabled"
  },
  "logName": "projects/netra-staging/logs/run.googleapis.com%2Frequests",
  "receiveTimestamp": "2025-09-16T01:43:05.967637095Z",
  "resource": {
    "labels": {
      "configuration_name": "netra-backend-staging",
      "location": "us-central1",
      "project_id": "netra-staging",
      "revision_name": "netra-backend-staging-00742-b95"...
```

---

### Cluster 6: P3 P3 - Sentry SDK Configuration (15 incidents)
**Category:** `LOW_SENTRY_CONFIGURATION`
**Priority:** P3
**Incident Count:** 15

**Sample Error:**
```json
{
  "timestamp": "2025-09-16T01:42:58.141775Z",
  "severity": "WARNING",
  "message": "Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking..."
}
```

**Full Sample Log:**
```json
{
  "insertId": "68c8c0a2000229cf714d3355",
  "jsonPayload": {
    "labels": {
      "function": "callHandlers",
      "line": "1706",
      "module": "logging"
    },
    "message": "Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking",
    "timestamp": "2025-09-16T01:42:58.139130+00:00"
  },
  "labels": {
    "instanceId": "0069c7a9882bdf09983888d3c0e309f04ad3f0c7cec93d4ef191773d4e97b5e7d9a26519dd106bb88622cb12e700b067398635acace02691d55787ed56286990da9a97728798a62bc7ff7c4b3533e6",
    "migration-run": "1757350810",
    "vpc-connectivity": "enabled"
  },
  "logName": "projects/netra-staging/logs/run.googleapis.com%2Fstderr",
  "receiveTimestamp": "2025-09-16T01:42:58.452663634Z",
  "resource": {
    "labels": {
      "configuration_name": "netra-backend-staging",
      "location": "us-central1",
      "project_id": "netra-staging",
      "revision_name": "netra-backend-staging-00742-b95",
      "service_name": "netra-backend-staging"
    },
    "type": "cl...
```

---

### Cluster 7: P3 P3 - Service ID Whitespace Issues (15 incidents)
**Category:** `LOW_SERVICE_ID_WHITESPACE`
**Priority:** P3
**Incident Count:** 15

**Sample Error:**
```json
{
  "timestamp": "2025-09-16T01:42:57.338443Z",
  "severity": "WARNING",
  "message": "SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'..."
}
```

**Full Sample Log:**
```json
{
  "insertId": "68c8c0a100052a0b316977e2",
  "jsonPayload": {
    "error": {
      "message": "Missing field",
      "severity": "ERROR",
      "timestamp": "2025-09-16T01:42:57.338273Z",
      "traceback": "",
      "type": "str"
    },
    "logger": "shared.logging.unified_logging_ssot",
    "message": "SERVICE_ID contained whitespace - sanitized from 'netra-backend\\n' to 'netra-backend'",
    "service": "netra-service",
    "textPayload": "SERVICE_ID contained whitespace - sanitized from 'netra-backend\\n' to 'netra-backend'",
    "timestamp": "2025-09-16T01:42:57.338265Z",
    "validation": {
      "message_length": 85,
      "severity": "WARNING",
      "validated_at": "2025-09-16T01:42:57.338278Z",
      "zero_empty_guarantee": true
    }
  },
  "labels": {
    "instanceId": "0069c7a9882bdf09983888d3c0e309f04ad3f0c7cec93d4ef191773d4e97b5e7d9a26519dd106bb88622cb12e700b067398635acace02691d55787ed56286990da9a97728798a62bc7ff7c4b3533e6",
    "migration-run": "1757350810",
    "vpc-...
```

---

## Recommended Actions

### P0 URGENT: Missing Monitoring Module Exports
- **Action Required:** Immediate investigation and fix
- **Business Impact:** Service availability at risk
- **Incidents:** 45 in last hour

### P0 URGENT: Container Exit Failures
- **Action Required:** Immediate investigation and fix
- **Business Impact:** Service availability at risk
- **Incidents:** 9 in last hour

### P0 URGENT: Middleware Setup Failures
- **Action Required:** Immediate investigation and fix
- **Business Impact:** Service availability at risk
- **Incidents:** 15 in last hour

### P1 URGENT: WebSocket Connectivity Issues
- **Action Required:** Immediate investigation and fix
- **Business Impact:** Service availability at risk
- **Incidents:** 15 in last hour

