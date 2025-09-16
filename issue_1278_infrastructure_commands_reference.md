# Issue #1278 Infrastructure Commands Reference

**Quick Reference for Infrastructure Team**

## Immediate Investigation Commands

### VPC Connector Health Check
```bash
gcloud compute networks vpc-access connectors describe staging-connector \
  --region=us-central1 --project=netra-staging
```

### Cloud SQL Instance Analysis
```bash
gcloud sql instances describe staging-shared-postgres \
  --project=netra-staging
```

### VPC Connector Status
```bash
gcloud compute networks vpc-access connectors list \
  --region=us-central1 --project=netra-staging
```

### Cloud SQL Connection Info
```bash
gcloud sql instances describe staging-shared-postgres \
  --project=netra-staging --format="table(connectionName,ipAddresses,state)"
```

## Test Execution Commands

### Run Issue #1278 Test Suite
```bash
# All Issue #1278 tests
python tests/unified_test_runner.py --marker issue_1278 --env staging

# Unit tests (should PASS)
python tests/unified_test_runner.py --test-file tests/unit/issue_1278_database_connectivity_timeout_validation.py

# Integration tests (should FAIL until fixed)
python tests/unified_test_runner.py --test-file tests/integration/issue_1278_database_connectivity_integration.py

# Post-fix validation (run after infrastructure fix)
python tests/unified_test_runner.py --test-file tests/validation/issue_1278_post_fix_validation.py --env staging
```

## Monitoring Commands

### Check VPC Connector Metrics
```bash
gcloud logging read "resource.type=vpc_access_connector AND resource.labels.connector_name=staging-connector" \
  --project=netra-staging --limit=50 --format=json
```

### Cloud SQL Error Logs
```bash
gcloud logging read "resource.type=cloudsql_database AND resource.labels.database_id=netra-staging:staging-shared-postgres" \
  --project=netra-staging --limit=50 --format=json
```

### Container Startup Logs
```bash
gcloud logging read "resource.type=cloud_run_revision AND labels.service_name=backend" \
  --project=netra-staging --limit=50 --format=json
```

---

**Priority**: Use these commands to diagnose VPC connector capacity and Cloud SQL connectivity issues causing Issue #1278.