# GCP Cloud Services Deletion Audit Report

## Executive Summary
Critical services in the `netra-staging` project were deleted on September 5, 2025. Both the backend and auth services were removed, leaving only the frontend service operational.

## Deletion Events

### 1. Backend Service Deletion
- **Service Name**: `netra-backend-staging`
- **Deletion Time**: 2025-09-05T05:08:11.284305Z (UTC)
- **Initiated By**: `netra-staging-deploy@netra-staging.iam.gserviceaccount.com` (Service Account)
- **Source IP**: 68.5.230.82
- **User Agent**: gcloud SDK 534.0.0 on Windows 10.0.26100
- **Region**: us-central1

### 2. Auth Service Deletion  
- **Service Name**: `netra-auth-service`
- **Deletion Time**: 2025-09-05T05:08:16.213921Z (UTC)
- **Initiated By**: `netra-staging-deploy@netra-staging.iam.gserviceaccount.com` (Service Account)
- **Source IP**: 68.5.230.82
- **User Agent**: gcloud SDK 534.0.0 on Windows 10.0.26100
- **Region**: us-central1

## Timeline of Events (Leading to Deletion)

| Time (UTC) | Action | Service | Actor |
|------------|--------|---------|-------|
| 04:45:32 | Deploy/Update | netra-frontend-staging | Service Account |
| 04:46:03 | Deploy/Update | netra-frontend-staging | Service Account |
| 04:54:03 | Deploy/Update | netra-backend-staging | Service Account |
| 04:56:14 | Deploy/Update | netra-backend-staging | Service Account |
| 04:57:31 | Deploy/Update | netra-backend-staging | Service Account |
| 05:02:17 | Deploy/Update | netra-backend-staging | Service Account |
| 05:07:42 | Deploy/Update | netra-backend-staging | Service Account |
| **05:08:11** | **DELETE** | **netra-backend-staging** | **Service Account** |
| **05:08:16** | **DELETE** | **netra-auth-service** | **Service Account** |

## Key Findings

1. **Automated Deletion**: Both deletions were executed via the service account `netra-staging-deploy@netra-staging.iam.gserviceaccount.com`, suggesting this was done through automation/CI/CD rather than manual intervention.

2. **Same Origin**: Both deletions originated from IP address 68.5.230.82 using gcloud SDK on Windows, indicating they were executed from the same machine/session.

3. **Sequential Deletion**: The auth service was deleted 5 seconds after the backend service, suggesting a deliberate sequential removal.

4. **Deployment Activity Before Deletion**: There were multiple deployment attempts to the backend service in the hour leading up to the deletion, suggesting possible deployment issues.

5. **Domain Mappings**: No domain mappings currently exist in the project. No deletion logs were found for domain mappings in the audit trail.

## Current State

### Active Services
- `netra-frontend-staging`: Running (Last deployed: 2025-09-05T04:45:56)

### Deleted Services
- `netra-backend-staging`: Deleted at 05:08:11 UTC
- `netra-auth-service`: Deleted at 05:08:16 UTC

### Domain Mappings
- None currently configured

## Recommendations

1. **Investigate CI/CD Pipeline**: Check the deployment scripts or GitHub Actions that use the `netra-staging-deploy` service account to understand why services were deleted.

2. **Review Service Account Permissions**: Audit the permissions granted to the service account to ensure it has appropriate but not excessive permissions.

3. **Check Deployment Logs**: Review the deployment logs from the Windows machine (IP: 68.5.230.82) to understand what triggered the deletion commands.

4. **Restore Services**: If these deletions were unintended, redeploy the backend and auth services using:
   ```bash
   python scripts/deploy_to_gcp.py --project netra-staging --build-local
   ```

5. **Implement Safeguards**: 
   - Add deletion protection to critical services
   - Implement approval workflows for production deletions
   - Set up alerts for service deletions

## Next Steps

1. Check local deployment scripts for any cleanup or deletion commands
2. Review recent commits to deployment scripts
3. Verify if this was an intended cleanup or accidental deletion
4. Redeploy services if needed
5. Configure domain mappings after services are restored

---

*Report Generated: 2025-09-05*
*Auditor: Cloud Audit Analysis via GCP Logging*