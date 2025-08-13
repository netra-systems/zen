# Staging Environment Troubleshooting Guide

## Common Issues and Solutions

### 1. Deployment Failures

#### Issue: Build Timeout
**Symptoms**: Docker build exceeds 10-minute timeout
```
Frontend Docker build timed out after 10 minutes
```

**Solutions**:
1. Check for infinite loops in build scripts
2. Optimize Docker layers:
   ```dockerfile
   # Bad - causes cache invalidation
   COPY . .
   RUN npm install
   
   # Good - leverages layer caching
   COPY package*.json ./
   RUN npm install
   COPY . .
   ```
3. Use multi-stage builds to reduce image size

#### Issue: Terraform State Lock
**Symptoms**: Terraform stuck with state lock error
```
Error acquiring the state lock
```

**Solutions**:
```bash
# Check for stale locks
LOCK_FILE="gs://netra-staging-terraform-state/staging/pr-123/default.tflock"
gsutil stat "$LOCK_FILE"

# Remove stale lock (if > 30 minutes old)
gsutil rm "$LOCK_FILE"

# Force unlock (use carefully)
terraform force-unlock <LOCK_ID>
```

### 2. Secret Manager Issues

#### Issue: Secret Not Found
**Symptoms**: 
```
Failed to fetch secret gemini-api-key: 404 Secret not found
```

**Root Causes**:
1. Missing `-staging` suffix
2. Wrong project ID (using name instead of number)
3. Secret doesn't exist

**Solutions**:
```bash
# Verify secret exists with correct name
gcloud secrets list --project=netra-staging | grep gemini
# Should show: gemini-api-key-staging

# Create missing secret
echo -n "YOUR_KEY" | gcloud secrets create gemini-api-key-staging \
  --data-file=- --project=netra-staging

# Check numerical project ID
gcloud projects describe netra-staging --format="value(projectNumber)"
```

#### Issue: Permission Denied
**Symptoms**:
```
Permission 'secretmanager.versions.access' denied
```

**Solutions**:
```bash
# Grant access to service account
gcloud secrets add-iam-policy-binding gemini-api-key-staging \
  --member="serviceAccount:staging-environments@netra-staging.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=netra-staging

# Verify IAM policy
gcloud secrets get-iam-policy gemini-api-key-staging --project=netra-staging
```

### 3. Database Connection Issues

#### Issue: Connection to localhost Failed
**Symptoms**:
```
connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused
```

**Root Cause**: DATABASE_URL not using Cloud SQL socket

**Solutions**:
1. Verify DATABASE_URL format:
   ```
   postgresql://user_pr_4:password@/netra_pr_4?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres
   ```

2. Check Cloud SQL proxy annotation in Terraform:
   ```hcl
   annotations = {
     "run.googleapis.com/cloudsql-instances" = local.sql_instance_connection
   }
   ```

3. Verify service account has Cloud SQL Client role:
   ```bash
   gcloud projects add-iam-policy-binding netra-staging \
     --member="serviceAccount:staging-environments@netra-staging.iam.gserviceaccount.com" \
     --role="roles/cloudsql.client"
   ```

#### Issue: Database Does Not Exist
**Symptoms**:
```
FATAL: database "netra_pr_123" does not exist
```

**Solutions**:
```bash
# Connect to Cloud SQL as admin
gcloud sql connect staging-shared-postgres --user=postgres --project=netra-staging

# Create database manually
CREATE DATABASE netra_pr_123;
CREATE USER user_pr_123 WITH PASSWORD 'staging-password';
GRANT ALL PRIVILEGES ON DATABASE netra_pr_123 TO user_pr_123;
```

### 4. Service Startup Issues

#### Issue: Health Check Failed
**Symptoms**:
```
The user-provided container failed the configured startup probe checks
```

**Root Causes**:
1. Application crash on startup
2. Missing required environment variables
3. Port mismatch

**Solutions**:
1. Check application logs:
   ```bash
   gcloud run services logs read backend-pr-123 --project=netra-staging --limit=100
   ```

2. Verify environment variables:
   ```bash
   gcloud run services describe backend-pr-123 \
     --region=us-central1 \
     --project=netra-staging \
     --format="yaml(spec.template.spec.containers[0].env)"
   ```

3. Test locally with same config:
   ```bash
   export ENVIRONMENT=staging
   export K_SERVICE=backend-pr-123
   python -m app.main
   ```

#### Issue: LLM Provider Not Available
**Symptoms**:
```
LLM 'default': Gemini API key is required for Google provider
```

**Solutions**:
1. Ensure gemini-api-key-staging exists
2. Check environment detection:
   ```python
   # Should return "staging"
   os.getenv("ENVIRONMENT")
   ```
3. Verify secret loading logs:
   ```
   Fetching secret: gemini-api-key-staging (original: gemini-api-key)
   ```

### 5. Networking Issues

#### Issue: VPC Connector Not Found
**Symptoms**:
```
VPC connector projects/netra-staging/locations/us-central1/connectors/staging-connector does not exist
```

**Solutions**:
```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create staging-connector \
  --network=staging-vpc \
  --region=us-central1 \
  --range=10.8.0.0/28 \
  --project=netra-staging
```

#### Issue: Redis Connection Timeout
**Symptoms**:
```
Redis connection failed: Timeout connecting to server
```

**Solutions**:
1. Verify Redis host is accessible from VPC
2. Check Redis URL format:
   ```
   redis://10.107.0.3:6379/{PR_NUMBER % 16}
   ```
3. Test connectivity:
   ```bash
   # From a Cloud Run service
   redis-cli -h 10.107.0.3 ping
   ```

### 6. ClickHouse Issues

#### Issue: Connection Timeout
**Symptoms**:
```
ClickHouse check failed: Connection to xedvrr4c3r.us-central1.gcp.clickhouse.cloud timed out
```

**Note**: ClickHouse failures are non-critical in staging

**Solutions**:
1. Increase timeout:
   ```env
   CLICKHOUSE_TIMEOUT=30
   ```
2. Skip ClickHouse in staging:
   ```env
   DEV_MODE_DISABLE_CLICKHOUSE=true
   ```

### 7. Performance Issues

#### Issue: Slow Cold Starts
**Symptoms**: First request takes 30+ seconds

**Solutions**:
1. Enable startup CPU boost:
   ```hcl
   annotations = {
     "run.googleapis.com/startup-cpu-boost" = "true"
   }
   ```

2. Set minimum instances:
   ```hcl
   annotations = {
     "autoscaling.knative.dev/minScale" = "1"
   }
   ```

3. Optimize imports:
   ```python
   # Lazy import heavy libraries
   def get_llm():
       from langchain_google_genai import ChatGoogleGenerativeAI
       return ChatGoogleGenerativeAI(...)
   ```

### 8. Cleanup Issues

#### Issue: Resources Not Deleted
**Symptoms**: Orphaned resources after PR close

**Solutions**:
```bash
# Manual cleanup
terraform destroy \
  -var="project_id=netra-staging" \
  -var="pr_number=123" \
  -auto-approve

# Delete database
gcloud sql databases delete netra_pr_123 \
  --instance=staging-shared-postgres \
  --project=netra-staging

# Delete Cloud Run services
gcloud run services delete backend-pr-123 \
  --region=us-central1 \
  --project=netra-staging
```

## Debugging Commands

### View Logs
```bash
# Cloud Run logs
gcloud run services logs read backend-pr-123 \
  --project=netra-staging \
  --region=us-central1 \
  --limit=50

# Filter by severity
gcloud logging read "resource.labels.service_name=backend-pr-123 AND severity>=ERROR" \
  --project=netra-staging \
  --limit=10
```

### Check Service Status
```bash
# Service details
gcloud run services describe backend-pr-123 \
  --region=us-central1 \
  --project=netra-staging

# List all PR services
gcloud run services list \
  --project=netra-staging \
  --filter="metadata.name:backend-pr-*"
```

### Database Operations
```bash
# Connect to database
gcloud sql connect staging-shared-postgres \
  --user=user_pr_123 \
  --database=netra_pr_123 \
  --project=netra-staging

# List databases
gcloud sql databases list \
  --instance=staging-shared-postgres \
  --project=netra-staging
```

### Secret Operations
```bash
# List all staging secrets
gcloud secrets list --project=netra-staging --filter="name:*-staging"

# View secret versions
gcloud secrets versions list gemini-api-key-staging --project=netra-staging

# Access secret value
gcloud secrets versions access latest \
  --secret=gemini-api-key-staging \
  --project=netra-staging
```

## Environment Variable Reference

### Required in Staging
```env
ENVIRONMENT=staging
DATABASE_URL=postgresql://user:pass@/db?host=/cloudsql/...
REDIS_URL=redis://host:6379/N
GCP_PROJECT_ID=netra-staging
GCP_PROJECT_ID_NUMERICAL_STAGING=<number>
SECRET_MANAGER_PROJECT=netra-staging
LOAD_SECRETS=true
PR_NUMBER=123
K_SERVICE=backend-pr-123
```

### Optional/Debug
```env
LOG_LEVEL=DEBUG
SKIP_MIGRATION_ON_STARTUP=false
DEV_MODE_DISABLE_REDIS=false
DEV_MODE_DISABLE_CLICKHOUSE=false
HEALTH_CHECK_GRACE_PERIOD=60
```

## Getting Help

### Check Documentation
1. [STAGING_DEPLOYMENT_COMPLETE_GUIDE.md](STAGING_DEPLOYMENT_COMPLETE_GUIDE.md)
2. [GOOGLE_SECRET_MANAGER_SETUP.md](GOOGLE_SECRET_MANAGER_SETUP.md)
3. [CREATE_GEMINI_KEY_STAGING.md](CREATE_GEMINI_KEY_STAGING.md)

### Contact Support
- **Slack**: #platform-support
- **GitHub Issues**: Label with `staging-environment`
- **Emergency**: Page on-call engineer

### Useful Links
- [Cloud Run Console](https://console.cloud.google.com/run?project=netra-staging)
- [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=netra-staging)
- [Cloud SQL](https://console.cloud.google.com/sql/instances?project=netra-staging)
- [Logs Explorer](https://console.cloud.google.com/logs/query?project=netra-staging)

---

**Last Updated**: August 2025
**Version**: 1.0.0