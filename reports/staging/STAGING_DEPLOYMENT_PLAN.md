# Staging Deployment Plan: Authentication Regression Fix

## Issue Summary
**Critical**: 401 Unauthorized errors in staging environment preventing user access.

**Root Cause**: Auth service was only looking for `JWT_SECRET_KEY` but staging config provides `JWT_SECRET_STAGING`.

**Fix Applied**: Updated `auth_service/auth_core/auth_environment.py` to support environment-specific JWT secrets.

## Deployment Requirements

### Pre-Deployment Checklist
- [x] Root cause identified and documented
- [x] Fix implemented and tested locally 
- [x] Code changes verified to work with staging configuration
- [x] No breaking changes introduced
- [x] Backward compatibility maintained

### Files Modified
- `auth_service/auth_core/auth_environment.py` (lines 46-103)
- Added environment-specific JWT secret loading priority chain

### Deployment Command
```bash
python scripts/deploy_to_gcp.py --project netra-staging --build-local
```

### Expected Outcome
- ✅ Auth service will load JWT_SECRET_STAGING correctly
- ✅ Frontend authentication will work  
- ✅ 401 errors will be resolved
- ✅ Users can access staging environment

### Rollback Plan
If deployment causes issues:
1. Revert `auth_service/auth_core/auth_environment.py` to previous version
2. Redeploy with: `python scripts/deploy_to_gcp.py --project netra-staging --build-local`

### Post-Deployment Verification
1. Test frontend login flow works
2. Verify API endpoints respond with valid tokens
3. Check auth service logs for JWT secret loading
4. Monitor for any new authentication errors

## Business Impact
- **High Priority**: Staging environment is currently unusable
- **User Impact**: Developers and QA cannot test features
- **Risk**: Low - fix is targeted and tested
- **Downtime**: Minimal - Cloud Run deployment is zero-downtime

## Communication
- Notify team when deployment starts
- Confirm resolution once verification complete
- Document lessons learned for future prevention