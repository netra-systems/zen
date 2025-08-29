# JWT_SECRET_KEY Documentation Index
**Last Updated:** 2025-08-29  
**Status:** ✅ STANDARDIZED

## Quick Reference
- **Variable Name:** `JWT_SECRET_KEY` (ONLY - no alternatives)
- **Deprecated:** `JWT_SECRET` (removed from all active code)
- **Minimum Length:** 32 characters (staging/production)
- **Both Services:** MUST use identical values

## Core Documentation

### Standards & Specifications
1. **[JWT Configuration Standard](../SPEC/jwt_configuration_standard.xml)**
   - Canonical specification for JWT configuration
   - Defines rules JWT-001 through JWT-005
   - Implementation details for each service

2. **[JWT Secret Standardization Learning](../SPEC/learnings/jwt_secret_standardization.xml)**
   - Historical context of the standardization
   - Problem/solution documentation
   - Validation steps

3. **[Learnings Index](../SPEC/learnings/index.xml)**
   - Critical takeaway: "Use JWT_SECRET_KEY exclusively"
   - Crosslinked with authentication category

### Implementation Files

#### Auth Service
- **Secret Loader:** `auth_service/auth_core/secret_loader.py`
  - Method: `AuthSecretLoader.get_jwt_secret()`
  - Priority: ENV_SPECIFIC → GSM → JWT_SECRET_KEY → Error

- **Configuration:** `auth_service/auth_core/config.py`
  - Method: `AuthConfig.get_jwt_secret()`
  - Validates minimum length in staging/production

#### Backend Service
- **Secret Manager:** `netra_backend/app/core/configuration/secrets.py`
  - Mapping: `JWT_SECRET_KEY` → `jwt_secret_key`
  - Required: true, Rotation: enabled

### Configuration Guides

1. **[Main Configuration Guide](configuration/CONFIGURATION_GUIDE.md)**
   - Line 362: JWT_SECRET_KEY documentation
   - Links to JWT Standard specification

2. **[Development Setup](development/DEVELOPMENT_SETUP.md)**
   - Lines 261-262: JWT_SECRET_KEY example

3. **[Environment Loader](development/ENVIRONMENT_LOADER.md)**
   - Line 111: JWT_SECRET_KEY configuration

### Environment Templates

| File | Purpose | JWT_SECRET_KEY Line |
|------|---------|-------------------|
| `.env.unified.template` | Unified template | Line 5 |
| `.env.staging.template` | Staging template | Line 94 (comment) |
| `.env.mock` | Mock/test values | Line 48 |
| `.env` | Development | Line 41 |

### Docker Configuration

All docker-compose files use `JWT_SECRET_KEY`:
- `docker-compose.yml`: Lines 136, 209
- `docker-compose.dev.yml`: Lines 114, 195
- `docker-compose.test.yml`: Lines 110, 188

### Test Configuration

| Test Type | Location | Usage |
|-----------|----------|-------|
| Unit Tests | `auth_service/tests/conftest.py` | Line 35 |
| Integration | `auth_service/tests/test_auth_comprehensive.py` | Lines 58, 124 |
| E2E | `tests/e2e/README.md` | Line 69 |

## Environment-Specific Secrets

### Hierarchy (Priority Order)
1. **Staging:** `JWT_SECRET_STAGING` → GSM → `JWT_SECRET_KEY`
2. **Production:** `JWT_SECRET_PRODUCTION` → GSM → `JWT_SECRET_KEY`
3. **Development:** `JWT_SECRET_KEY` only

### Google Secret Manager
- **Staging:** `jwt-secret-key-staging`
- **Production:** `jwt-secret-key`

## Validation Commands

```bash
# Check for legacy JWT_SECRET references
rg "JWT_SECRET[^_]|JWT_SECRET$"

# Verify JWT_SECRET_KEY is set
echo $JWT_SECRET_KEY

# Generate secure JWT secret
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"

# Test token validation between services
curl -X POST http://localhost:8081/auth/validate \
  -H "Authorization: Bearer <token>"
```

## Common Issues & Solutions

### Issue: "JWT secret not configured for staging environment"
**Solution:** Ensure `JWT_SECRET_KEY` is set in environment or GSM

### Issue: Token validation fails between services
**Solution:** Verify both services use identical `JWT_SECRET_KEY` value

### Issue: "JWT_SECRET_KEY must be at least 32 characters"
**Solution:** Generate longer secret with `secrets.token_urlsafe(32)`

## Migration Status

| Component | Status | Date |
|-----------|--------|------|
| Auth Service Code | ✅ Completed | 2025-08-29 |
| Backend Service Code | ✅ Completed | 2025-08-29 |
| Test Files | ✅ Completed | 2025-08-29 |
| Environment Files | ✅ Completed | 2025-08-29 |
| Documentation | ✅ Completed | 2025-08-29 |
| Staging Deployment | ✅ Completed | 2025-08-29 |

## Reports & Audits
- [JWT Secret Standardization Report](../JWT_SECRET_STANDARDIZATION_REPORT.md)
- [Master Index Entry](../LLM_MASTER_INDEX.md#configuration-files-unified-system---critical-change)

## Next Steps
All standardization complete. System is using JWT_SECRET_KEY consistently across all services and environments.