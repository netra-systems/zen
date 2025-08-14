# GitHub Runner Failure - Root Cause Analysis & Fix

## Executive Summary
The GitHub runner fails immediately after creating the runner user due to Secret Manager access issues. The failure occurs at the exact point where the script attempts to retrieve the GitHub PAT from Google Secret Manager.

## Root Cause
**Failure Point:** Line 656 in `install-runner.sh` - `get_github_pat()` function

The script successfully creates the runner user, then immediately fails when attempting to:
1. Install gcloud SDK (if missing)
2. Access the secret `github-runner-token` from Google Secret Manager
3. Authenticate with the metadata service

## Common Failure Scenarios

### 1. Missing Secret
- **Error:** Secret 'github-runner-token' not found
- **Fix:** Create the secret with your GitHub PAT
```bash
echo -n 'YOUR_GITHUB_PAT' | gcloud secrets create github-runner-token \
  --data-file=- --project=YOUR_PROJECT_ID
```

### 2. IAM Permission Denied
- **Error:** PERMISSION_DENIED accessing secret
- **Fix:** Grant the service account proper permissions
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-runner-sa@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 3. gcloud SDK Installation Failure
- **Error:** Failed to install Google Cloud SDK
- **Fix:** The enhanced script now includes fallback installation methods

## Implemented Fixes

### 1. Enhanced Error Handling (`install-runner.sh`)
- Added comprehensive debugging output
- Improved error detection with specific error messages
- Added service account and scope validation
- Implemented fallback gcloud installation methods
- Added detailed troubleshooting instructions in error messages

### 2. Diagnostic Script (`diagnose-runner-enhanced.sh`)
- Comprehensive system checks
- Secret Manager access validation
- IAM permission verification
- Docker status checks
- Log analysis with error pattern detection

### 3. Quick Fix Script (`fix-runner-quick.sh`)
- Automated gcloud SDK installation
- Secret existence validation
- IAM permission auto-fix
- Docker permission fixes
- Service restart capabilities

## Usage Instructions

### To Diagnose Issues
```bash
# SSH into the failing instance
gcloud compute ssh github-runner-1 --zone=YOUR_ZONE

# Run enhanced diagnostics
sudo bash /opt/github-runner/scripts/diagnose-runner-enhanced.sh
```

### To Apply Quick Fixes
```bash
# Set your project ID
export PROJECT_ID=your-project-id

# Run the quick fix script
sudo bash /opt/github-runner/scripts/fix-runner-quick.sh
```

### To Re-run Installation
```bash
# After fixing Secret Manager access
sudo bash /opt/github-runner/scripts/install-runner.sh
```

## Verification Steps

1. **Check Secret Exists:**
```bash
gcloud secrets describe github-runner-token --project=YOUR_PROJECT_ID
```

2. **Verify IAM Permissions:**
```bash
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:github-runner-sa@YOUR_PROJECT.iam.gserviceaccount.com"
```

3. **Test Secret Access:**
```bash
gcloud secrets versions access latest \
  --secret="github-runner-token" \
  --project=YOUR_PROJECT_ID
```

## Prevention Measures

1. **Pre-deployment Checklist:**
   - Ensure GitHub PAT is created with proper scopes (repo, workflow, admin:org)
   - Create the secret before deploying runners
   - Verify IAM permissions are properly configured in Terraform

2. **Terraform Validation:**
   - Add validation to ensure the secret exists
   - Include IAM permission checks in Terraform plan
   - Add output variables to display critical configuration

3. **Monitoring:**
   - Set up Cloud Logging alerts for runner failures
   - Monitor Secret Manager access denied errors
   - Track runner registration status

## Key Files Modified

1. **`scripts/install-runner.sh`**
   - Enhanced `get_github_pat()` function with detailed debugging
   - Added metadata service validation
   - Improved error messages with fix instructions

2. **`scripts/diagnose-runner-enhanced.sh`** (NEW)
   - Comprehensive diagnostic tool
   - Checks all critical components
   - Provides specific remediation steps

3. **`scripts/fix-runner-quick.sh`** (NEW)
   - Automated fix for common issues
   - Interactive troubleshooting
   - Service recovery capabilities

## Next Steps

1. **Immediate Actions:**
   - Create the GitHub PAT secret if missing
   - Apply IAM permissions
   - Run the quick fix script

2. **Long-term Improvements:**
   - Add pre-flight checks to Terraform
   - Implement automated secret rotation
   - Add health check endpoints

## Contact for Issues
If problems persist after applying these fixes:
1. Check logs: `/var/log/github-runner-install.log`
2. Review error log: `/var/log/github-runner-errors.log`
3. Run enhanced diagnostics for detailed analysis