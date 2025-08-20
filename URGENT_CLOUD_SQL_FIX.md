# URGENT: Fix Cloud SQL Permissions for Staging Auth Service

## Problem
The auth service in staging cannot connect to Cloud SQL due to missing permissions. The service is getting:
```
Error 403: boss::NOT_AUTHORIZED: Not authorized to access resource. 
Possibly missing permission cloudsql.instances.get on resource instances/staging-shared-postgres
```

## Root Cause
The Cloud Run default service account (`701982941522-compute@developer.gserviceaccount.com`) is missing the required Cloud SQL permissions.

## Required Fix
Someone with **Owner** or **IAM Admin** permissions on the `netra-staging` project needs to run these commands:

```bash
# Add Cloud SQL Client role
gcloud projects add-iam-policy-binding netra-staging \
  --member="serviceAccount:701982941522-compute@developer.gserviceaccount.com" \
  --role="roles/cloudsql.client"

# Add Cloud SQL Instance User role (optional but recommended)
gcloud projects add-iam-policy-binding netra-staging \
  --member="serviceAccount:701982941522-compute@developer.gserviceaccount.com" \
  --role="roles/cloudsql.instanceUser"
```

## Alternative: Grant via Console
1. Go to https://console.cloud.google.com/iam-admin/iam?project=netra-staging
2. Find the service account: `701982941522-compute@developer.gserviceaccount.com`
3. Click "Edit" (pencil icon)
4. Add these roles:
   - Cloud SQL Client
   - Cloud SQL Instance User (optional)
5. Click "Save"

## After Fix
Once permissions are granted, the auth service will automatically connect to Cloud SQL on the next deployment or restart.

## Current Missing Roles
The service account currently has:
- ✅ roles/artifactregistry.writer
- ✅ roles/iam.serviceAccountUser
- ✅ roles/logging.logWriter
- ✅ roles/run.developer
- ✅ roles/secretmanager.secretAccessor
- ✅ roles/storage.admin
- ❌ **roles/cloudsql.client** (MISSING - REQUIRED)
- ❌ roles/cloudsql.instanceUser (MISSING - recommended)

## Impact
Until this is fixed:
- Auth service cannot start in staging
- All staging deployments will fail
- No authentication functionality in staging environment