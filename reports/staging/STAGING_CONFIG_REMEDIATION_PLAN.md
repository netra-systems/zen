# Staging Configuration Remediation Plan
Date: 2025-09-05
Priority: P0 CRITICAL - Execute IMMEDIATELY

## Current State: SERVICE DOWN
- 19 critical environment variables MISSING
- Cloud Run service in crash loop
- All requests returning 503
- No database connectivity
- No authentication possible

## IMMEDIATE ACTION REQUIRED (Do This NOW)

### Step 1: Gather Required Values
You need these values BEFORE proceeding:

```bash
# From your GCP Console or documentation:
PROJECT_ID: netra-staging
REGION: us-central1
CLOUD_SQL_INSTANCE: [Get from Cloud SQL console]
CLOUD_SQL_CONNECTION: [Format: PROJECT:REGION:INSTANCE]
MEMORYSTORE_IP: [Get from Memorystore/Redis console]
SERVICE_URL: [Get from Cloud Run console]

# Generate secure secrets (use strong random values):
JWT_SECRET_KEY: [Generate 64+ character random string]
SECRET_KEY: [Generate 64+ character random string]
DB_PASSWORD: [Your PostgreSQL password]

# OAuth (if using Google OAuth):
GOOGLE_CLIENT_ID: [From Google Cloud Console]
GOOGLE_CLIENT_SECRET: [From Google Cloud Console]
```

### Step 2: Create Configuration File
Save as `staging-env-vars.yaml`:

```yaml
ENV: staging
# Database Configuration
DATABASE_URL: postgresql://netra_user:YOUR_PASSWORD@/netra_staging?host=/cloudsql/PROJECT:REGION:INSTANCE
POSTGRES_HOST: /cloudsql/PROJECT:REGION:INSTANCE
POSTGRES_PORT: "5432"
POSTGRES_DB: netra_staging
POSTGRES_USER: netra_user
POSTGRES_PASSWORD: YOUR_PASSWORD

# Security Keys (MUST be unique, secure values)
JWT_SECRET_KEY: YOUR_GENERATED_JWT_SECRET
SECRET_KEY: YOUR_GENERATED_SECRET_KEY
JWT_ALGORITHM: HS256
JWT_EXPIRATION_MINUTES: "1440"

# Redis Configuration
REDIS_HOST: YOUR_MEMORYSTORE_IP
REDIS_PORT: "6379"

# Application URLs
BACKEND_URL: https://YOUR-SERVICE-URL.run.app
FRONTEND_URL: https://YOUR-FRONTEND-URL
API_BASE_URL: https://YOUR-SERVICE-URL.run.app

# OAuth (Optional)
GOOGLE_CLIENT_ID: YOUR_GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET: YOUR_GOOGLE_CLIENT_SECRET

# Logging
LOG_LEVEL: INFO
```

### Step 3: Apply Configuration to Cloud Run

```bash
# Option A: Using env-vars file
gcloud run services update netra-backend \
  --env-vars-file=staging-env-vars.yaml \
  --region=us-central1 \
  --project=netra-staging

# Option B: Set individually (replace placeholders)
gcloud run services update netra-backend \
  --set-env-vars="ENV=staging" \
  --set-env-vars="DATABASE_URL=postgresql://netra_user:PASS@/netra_staging?host=/cloudsql/netra-staging:us-central1:postgres" \
  --set-env-vars="POSTGRES_HOST=/cloudsql/netra-staging:us-central1:postgres" \
  --set-env-vars="POSTGRES_PORT=5432" \
  --set-env-vars="POSTGRES_DB=netra_staging" \
  --set-env-vars="POSTGRES_USER=netra_user" \
  --set-env-vars="POSTGRES_PASSWORD=YOUR_REAL_PASSWORD" \
  --set-env-vars="JWT_SECRET_KEY=YOUR_REAL_JWT_SECRET" \
  --set-env-vars="SECRET_KEY=YOUR_REAL_SECRET_KEY" \
  --set-env-vars="REDIS_HOST=10.0.0.3" \
  --set-env-vars="REDIS_PORT=6379" \
  --set-env-vars="BACKEND_URL=https://netra-backend-xyz.run.app" \
  --set-env-vars="FRONTEND_URL=https://netra-frontend.web.app" \
  --set-env-vars="API_BASE_URL=https://netra-backend-xyz.run.app" \
  --region=us-central1 \
  --project=netra-staging
```

### Step 4: Verify Configuration Applied

```bash
# Check env vars are set
gcloud run services describe netra-backend \
  --region=us-central1 \
  --project=netra-staging \
  --format="json" | jq '.spec.template.spec.containers[0].env'

# Should see all 19+ environment variables listed
```

### Step 5: Monitor Service Health

```bash
# Watch for service to become healthy
watch -n 5 'gcloud run services describe netra-backend \
  --region=us-central1 \
  --project=netra-staging \
  --format="table(status.conditions.type,status.conditions.status,status.conditions.message)"'

# Check logs for startup
gcloud run logs read \
  --service=netra-backend \
  --region=us-central1 \
  --project=netra-staging \
  --limit=50
```

### Step 6: Test Service Endpoints

```bash
# Test health check
curl https://YOUR-SERVICE-URL.run.app/health

# Test API root
curl https://YOUR-SERVICE-URL.run.app/api/v1/

# If using authentication, test login
curl -X POST https://YOUR-SERVICE-URL.run.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
```

## Configuration Validation Checklist

Before declaring success, verify ALL of these:

### Database Connectivity
- [ ] Cloud SQL instance is running
- [ ] Cloud SQL Admin API is enabled
- [ ] Cloud Run service account has Cloud SQL Client role
- [ ] #removed-legacyuses Unix socket format (/cloudsql/...)
- [ ] Database exists and is initialized

### Redis/Memorystore
- [ ] Memorystore instance is running
- [ ] VPC connector is configured for Cloud Run
- [ ] REDIS_HOST is internal IP (e.g., 10.x.x.x)
- [ ] Network connectivity verified

### Authentication
- [ ] JWT_SECRET_KEY is set and secure (64+ chars)
- [ ] SECRET_KEY is different from JWT_SECRET_KEY
- [ ] Both keys are stored securely

### URLs
- [ ] BACKEND_URL matches actual Cloud Run URL
- [ ] FRONTEND_URL points to deployed frontend
- [ ] No localhost URLs in staging config

### Service Health
- [ ] Health check endpoint returns 200
- [ ] No crash loops in logs
- [ ] TCP probes passing
- [ ] Memory/CPU usage normal

## Troubleshooting Guide

### If Service Still Failing After Config

1. **Check Cloud SQL Connection**
```bash
# Verify Cloud SQL proxy is accessible
gcloud sql instances describe YOUR_INSTANCE --project=netra-staging

# Check service account permissions
gcloud projects get-iam-policy netra-staging \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/cloudsql.client"
```

2. **Check VPC Connector (for Redis)**
```bash
# List VPC connectors
gcloud compute networks vpc-access connectors list \
  --region=us-central1 \
  --project=netra-staging

# Verify Cloud Run uses connector
gcloud run services describe netra-backend \
  --region=us-central1 \
  --project=netra-staging \
  --format="value(spec.template.metadata.annotations.'run.googleapis.com/vpc-access-connector')"
```

3. **Check Container Logs**
```bash
# Get detailed error logs
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=netra-backend \
  AND severity>=ERROR" \
  --project=netra-staging \
  --limit=50 \
  --format=json
```

## Long-term Fixes to Implement

### 1. Update Deployment Script
Add to `scripts/deploy_to_gcp.py`:

```python
def validate_required_env_vars(service_name, project, region):
    """Ensure all required env vars are set"""
    required = [
        'DATABASE_URL', 'JWT_SECRET_KEY', 'SECRET_KEY',
        'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB',
        'POSTGRES_USER', 'POSTGRES_PASSWORD', 'ENV',
        'REDIS_HOST', 'REDIS_PORT', 'BACKEND_URL',
        'FRONTEND_URL', 'API_BASE_URL'
    ]
    
    result = subprocess.run([
        'gcloud', 'run', 'services', 'describe', service_name,
        '--region', region, '--project', project,
        '--format', 'value(spec.template.spec.containers[0].env[].name)'
    ], capture_output=True, text=True)
    
    set_vars = set(result.stdout.strip().split('\n'))
    missing = set(required) - set_vars
    
    if missing:
        raise ValueError(f"Missing required env vars: {missing}")
    
    print(f"✓ All {len(required)} required env vars configured")
```

### 2. Create Environment Template
Create `deployment/staging/.env.template`:

```bash
# Staging Environment Configuration Template
# Copy to .env and fill in actual values

# Environment
ENV=staging

# Database (Cloud SQL)
DATABASE_URL=postgresql://USER:PASS@/DB?host=/cloudsql/INSTANCE
POSTGRES_HOST=/cloudsql/PROJECT:REGION:INSTANCE
POSTGRES_PORT=5432
POSTGRES_DB=netra_staging
POSTGRES_USER=
POSTGRES_PASSWORD=

# Security
JWT_SECRET_KEY=  # Generate with: openssl rand -hex 32
SECRET_KEY=      # Generate with: openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# Redis (Cloud Memorystore)
REDIS_HOST=  # Internal IP from Memorystore
REDIS_PORT=6379

# Application URLs
BACKEND_URL=  # https://SERVICE-NAME.run.app
FRONTEND_URL= # Frontend deployment URL
API_BASE_URL= # Same as BACKEND_URL

# OAuth (Optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Logging
LOG_LEVEL=INFO
```

### 3. Add Pre-deployment Validation
Create `scripts/validate_staging_config.py`:

```python
#!/usr/bin/env python3
"""Validate staging configuration before deployment"""

import os
import sys
import subprocess
import json

def check_cloud_sql():
    """Verify Cloud SQL is accessible"""
    # Implementation here
    pass

def check_memorystore():
    """Verify Redis/Memorystore is accessible"""
    # Implementation here
    pass

def check_env_vars():
    """Verify all required env vars are set"""
    # Implementation here
    pass

if __name__ == "__main__":
    if not all([check_cloud_sql(), check_memorystore(), check_env_vars()]):
        print("❌ Staging validation failed")
        sys.exit(1)
    print("✅ Staging configuration valid")
```

## Success Criteria

Service is considered FIXED when:
1. ✅ All 19 environment variables are configured
2. ✅ Cloud Run service status shows "Ready"
3. ✅ Health check endpoint returns 200
4. ✅ No error logs in past 5 minutes
5. ✅ Can successfully make API calls
6. ✅ Database queries working
7. ✅ Redis caching operational

## Contact for Help

If you need values for any of these configs:
1. Check GCP Console for Cloud SQL and Memorystore details
2. Review previous deployment logs for URLs
3. Check with DevOps team for sensitive values
4. Use Secret Manager for production secrets

## Final Notes

**Remember:** This is a CONFIGURATION issue, not a code issue. Once the environment variables are properly set, the service will start working immediately. The application code is correct and waiting for its configuration.

**Priority:** Set these configs NOW to restore service. Everything else can wait.