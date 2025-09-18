# GCP Log Analysis Report - Last 1 Hour
**Generated:** 2025-09-15 20:05:26 PDT
**Time Range:** 4:43 PM PDT to 5:43 PM PDT (Sept 15, 2025)
**Service:** netra-backend-staging
**Total Logs:** 5000
**Error/Warning Logs:** 183

## Executive Summary

### Severity Breakdown:
- **WARNING:** 124 incidents
- **ERROR:** 59 incidents

## Clustered Issue Analysis

### 🟡 CLUSTER 1: Other Errors (P2 MEDIUM)
**Issue Count:** 179 incidents
**Severity:** P2 MEDIUM

#### Key Log Patterns:
```
WARNING [2025-09-16T03:03:31.730924+00:00] - WARNING log with empty content at 2025-09-16T03:03:31.730924+00:00
WARNING [2025-09-16T03:03:30.817140+00:00] - WARNING log with empty content at 2025-09-16T03:03:30.817140+00:00
WARNING [2025-09-16T03:03:18.946934+00:00] - WARNING log with empty content at 2025-09-16T03:03:18.946934+00:00
... and 176 more similar incidents
```

#### Sample Full JSON Log:
```json
{
  "timestamp": "2025-09-16T03:03:31.730924+00:00",
  "severity": "WARNING",
  "resource": {
    "type": "cloud_run_revision",
    "labels": {
      "project_id": "netra-staging",
      "configuration_name": "netra-backend-staging",
      "location": "us-central1",
      "service_name": "netra-backend-staging",
      "revision_name": "netra-backend-staging-00750-69k"
    }
  },
  "labels": {
    "migration-run": "1757350810",
    "instanceId": "0069c7a9889334f2abf231795ba9fd119df905c13ba8380ca3528cfc365a275a68ac5b83da0f74e0d6f2199776c66548e812cc8467d8def6105ac8bf96273d5a8f3d352c856a53b837df0e4d301382",
    "vpc-connectivity": "enabled"
  },
  "insert_id": "68c8d383000b272ca28469f4",
  "trace": null,
  "span_id": null,
  "text_payload": null,
  "json_payload": {},
  "http_request": {},
  "source_location": {}
}
```

---

### 🟠 CLUSTER 2: WebSocket Connection Issues (P1 HIGH)
**Issue Count:** 4 incidents
**Severity:** P1 HIGH

#### Key Log Patterns:
```
ERROR [2025-09-16T02:54:45.416300+00:00] - HTTP GET https://api.staging.netrasystems.ai/ws returned 503 (latency: 2.212449s)
ERROR [2025-09-16T02:54:06.732070+00:00] - HTTP GET https://api.staging.netrasystems.ai/ws returned 503 (latency: 6.273844s)
ERROR [2025-09-16T02:53:48.675765+00:00] - HTTP GET https://api.staging.netrasystems.ai/ws returned 503 (latency: 1.910887s)
... and 1 more similar incidents
```

#### Sample Full JSON Log:
```json
{
  "timestamp": "2025-09-16T02:54:45.416300+00:00",
  "severity": "ERROR",
  "resource": {
    "type": "cloud_run_revision",
    "labels": {
      "revision_name": "netra-backend-staging-00749-6tr",
      "configuration_name": "netra-backend-staging",
      "service_name": "netra-backend-staging",
      "location": "us-central1",
      "project_id": "netra-staging"
    }
  },
  "labels": {
    "vpc-connectivity": "enabled",
    "migration-run": "1757350810",
    "instanceId": "0069c7a9889f0fb364abfae1214e014e3b63b30af110550e17bc3d36066d1a4309f9c49a164f440130066972af35d9ebf4f4ef0f979b2efa9504a6ea01b709875523fb6e7beccad0a13b56fde0d45e"
  },
  "insert_id": "68c8d1770009ce19a6b33067",
  "trace": "projects/netra-staging/traces/14e3aa8933d242a63ba95c6d80336be2",
  "span_id": "894653c0ee44185b",
  "text_payload": null,
  "json_payload": {},
  "http_request": {
    "method": "GET",
    "url": "https://api.staging.netrasystems.ai/ws",
    "status": 503,
    "user_agent": "Python/3.13 websockets/15.0.1",
    "remote_ip": "68.5.230.82",
    "referer": null,
    "latency": "2.212449s",
    "cache_hit": null,
    "cache_lookup": null,
    "response_size": "162",
    "request_size": "918"
  },
  "source_location": {}
}
```

---

## Timeline Analysis

### Error Timeline (Last 1 Hour):
```
732693+0 - ERROR - Other Errors
702314+0 - ERROR - WebSocket Connection Issues
363063+0 - WARNING - Other Errors
900909+0 - WARNING - Other Errors
520577+0 - ERROR - Other Errors
371221+0 - WARNING - Other Errors
941118+0 - WARNING - Other Errors
675765+0 - ERROR - WebSocket Connection Issues
712998+0 - ERROR - Other Errors
471143+0 - WARNING - Other Errors
064401+0 - WARNING - Other Errors
086624+0 - ERROR - Other Errors
011399+0 - WARNING - Other Errors
732070+0 - ERROR - WebSocket Connection Issues
565444+0 - WARNING - Other Errors
215596+0 - WARNING - Other Errors
117818+0 - ERROR - Other Errors
781909+0 - WARNING - Other Errors
506545+0 - WARNING - Other Errors
123721+0 - ERROR - Other Errors
... and 163 more events
```

## Immediate Action Items

### P0 CRITICAL (Fix Immediately):

### P1 HIGH (Fix Today):
- **WebSocket Connection Issues** (4 incidents)

## Raw Data Access

**Full log file:** `gcp_logs_raw_20250915_200344.json`
**Total entries:** 5000
**Error entries:** 183

### GCloud Command Used:
```bash
gcloud logging read "resource.type=cloud_run_revision AND
  resource.labels.service_name=netra-backend-staging AND
  timestamp>=\"2025-09-15T23:43:00.000Z\" AND
  timestamp<=\"2025-09-16T00:43:00.000Z\""
  --limit=1000 --format=json --project=netra-staging
```