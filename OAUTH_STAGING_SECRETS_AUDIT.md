# OAuth Staging Secrets Audit Report

## Issue Summary
There are incorrectly named OAuth secrets in GCP Secret Manager with double "CLIENT" in their names that need to be deleted.

## Problem Analysis

### Incorrect Secrets (TO BE DELETED)
```
GOOGLE_OAUTH_CLIENT_CLIENT_ID_STAGING      (Created: 2025-08-19)
GOOGLE_OAUTH_CLIENT_CLIENT_SECRET_STAGING  (Created: 2025-08-19)
```

These secrets have malformed names with double "CLIENT" and are causing confusion. They should be deleted.

### Correct Secrets (IN USE)
```
google-client-id-staging      (Created: 2025-08-12)
google-client-secret-staging  (Created: 2025-08-12)
```

These are the correct secrets that the deployment script uses:
- `deploy_to_gcp.py` correctly maps environment variables to these secrets:
  - `GOOGLE_OAUTH_CLIENT_ID_STAGING=google-client-id-staging:latest`
  - `GOOGLE_OAUTH_CLIENT_SECRET_STAGING=google-client-secret-staging:latest`

## Root Cause

The incorrect secrets were likely created manually or by a misconfigured script. The deployment pipeline is functioning correctly and uses the right secret names.

## How OAuth Configuration Works

1. **Auth Service Expects**: Environment variables named `GOOGLE_OAUTH_CLIENT_ID_STAGING` and `GOOGLE_OAUTH_CLIENT_SECRET_STAGING`
2. **GCP Secret Manager Has**: Secrets named `google-client-id-staging` and `google-client-secret-staging`
3. **Deployment Script Maps**: The environment variables to the GCP secrets correctly

The issue is that there are EXTRA secrets with incorrect names that should not exist.

## Remediation Actions

### Immediate Actions

1. **Delete the incorrect secrets from GCP**:
```bash
gcloud secrets delete GOOGLE_OAUTH_CLIENT_CLIENT_ID_STAGING --project=netra-staging --quiet
gcloud secrets delete GOOGLE_OAUTH_CLIENT_CLIENT_SECRET_STAGING --project=netra-staging --quiet
```

2. **Verify correct secrets are still in place**:
```bash
gcloud secrets list --project=netra-staging --filter="name:google-client"
```

### Code Changes Made
- Fixed `scripts/fix_staging_secrets.py` to remove incorrect references to the malformed secret names

## Verification Steps

After deletion, verify that:
1. Auth service still works correctly with OAuth
2. No code references the deleted secrets
3. Deployment continues to use the correct secret names

## Conclusion

The staging OAuth configuration is correctly set up in the deployment script. The issue is the presence of incorrectly named duplicate secrets in GCP that should be deleted. The deployment pipeline itself is functioning correctly.