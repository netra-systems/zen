# GCP-other | P2 | Configuration drift: Missing Sentry SDK and staging environment issues

## Impact
Service configuration warnings indicate operational hygiene issues that may affect service discovery, monitoring, and deployment reliability. While not blocking core functionality, these issues create maintenance overhead and potential operational risks. Recent escalation to P2 due to increased frequency and staging environment configuration drift.

## Current Behavior
Staging environment logs show configuration hygiene warnings during service startup:

### Service ID Whitespace Issues:
```json
{
  "timestamp": "2025-09-15T20:03:04.073864+00:00",
  "severity": "WARNING",
  "message": "SERVICE_ID contained whitespace - sanitized from 'netra-backend\\n' to 'netra-backend'"
}
```

### Missing Monitoring Dependencies:
```json
{
  "timestamp": "2025-09-15T21:37:25.934207+00:00",
  "severity": "WARNING",
  "message": "Sentry SDK not available. Error tracking disabled.",
  "context": {
    "service": "netra-service"
  }
}
```

### OAuth URI Configuration Drift:
```json
{
  "timestamp": "2025-09-15T21:37:07.419756+00:00",
  "severity": "WARNING",
  "message": "OAuth URI mismatch in staging environment - non-critical configuration drift detected",
  "context": {
    "service": "netra-service"
  }
}
```

**Count:** 20+ configuration warning entries detected in last hour
**Module:** netra_backend.app.logging_config
**Function:** configure_logging
**Line:** 89

## Expected Behavior
Clean service configuration without warnings:
- Service ID properly formatted without trailing whitespace
- All monitoring dependencies available (Sentry SDK)
- OAuth URI configuration properly aligned between staging and production environments
- Configuration validation passing without sanitization
- Clean startup logs without configuration warnings

## Reproduction Steps
1. Deploy staging environment with current configuration
2. Monitor service startup logs
3. Observe configuration warnings during logging setup
4. Note service ID sanitization and missing SDK warnings

## Technical Details
- **Primary Issue:** Service ID contains trailing newline/whitespace characters
- **Secondary Issue:** Missing Sentry SDK dependency for error tracking
- **Tertiary Issue:** OAuth URI mismatch between staging and production configuration
- **Environment:** staging
- **Timestamp:** 2025-09-15T21:37:25 UTC (latest)
- **Count:** 20+ occurrences in last hour
- **Log Severity:** WARNING

## Root Cause Analysis

### Service ID Configuration Issue
1. **Source:** Environment variable or configuration file contains trailing whitespace
2. **Impact:** Requires runtime sanitization, potential service discovery confusion
3. **Pattern:** `'netra-backend\n'` being sanitized to `'netra-backend'`

### Missing Sentry SDK Dependency
1. **Source:** Optional monitoring dependency not installed in staging environment
2. **Impact:** No error tracking/alerting for production issues
3. **Missing Package:** `sentry-sdk[fastapi]`

### OAuth URI Configuration Drift
1. **Source:** Inconsistent OAuth redirect URI configuration between environments
2. **Impact:** Potential authentication issues and configuration drift alerts
3. **Pattern:** `https://app.staging.netrasystems.ai/auth/callback vs https://app.staging.netrasystems.ai`

## Business Risk Assessment
- **Priority:** P2 (Warning) - Configuration drift affecting multiple environments
- **Service Discovery:** Potential confusion from malformed service IDs
- **Error Monitoring:** Missing error tracking reduces incident response capability
- **Authentication:** OAuth configuration drift may cause authentication issues
- **Deployment Hygiene:** Configuration warnings indicate process gaps

## Proposed Resolution Strategy

### Phase 1: Service ID Configuration Fix (30 minutes)
1. **Identify configuration source**
   ```bash
   # Check environment variables
   echo "$SERVICE_ID" | cat -A
   # Check configuration files for whitespace
   ```

2. **Clean configuration**
   - Remove trailing whitespace from SERVICE_ID environment variable
   - Update deployment scripts to validate configuration format
   - Add configuration validation to startup process

### Phase 2: Monitoring Dependencies (1 hour)
1. **Install Sentry SDK**
   ```bash
   pip install sentry-sdk[fastapi]
   ```

2. **Update requirements**
   ```python
   # requirements.txt
   sentry-sdk[fastapi]>=1.x.x
   ```

3. **Configure Sentry integration**
   - Add Sentry DSN configuration
   - Enable error tracking for staging environment
   - Test error reporting functionality

### Phase 3: OAuth URI Configuration Alignment (1 hour)
1. **Review OAuth configuration**
   ```bash
   # Check current OAuth redirect URIs
   grep -r "app.staging.netra" auth_service/
   grep -r "app.staging.netrasystems" auth_service/
   ```

2. **Standardize OAuth URLs**
   - Align staging environment OAuth URIs
   - Update configuration files consistently
   - Verify redirect URI registration

### Phase 4: Configuration Validation (2 hours)
1. **Add startup validation**
   ```python
   def validate_service_configuration():
       """Validate service configuration before startup"""
       service_id = os.getenv('SERVICE_ID', '').strip()
       if service_id != os.getenv('SERVICE_ID', ''):
           raise ConfigurationError("SERVICE_ID contains whitespace")
   ```

2. **Pre-deployment checks**
   - Configuration linting in CI/CD
   - Environment variable validation
   - Dependency verification
   - OAuth URI consistency validation

## Files to Update
1. **Environment Configuration**
   - `.env.staging.tests`
   - Deployment scripts
   - Docker environment files
   - OAuth provider configuration

2. **Dependencies**
   - `requirements.txt`
   - `pyproject.toml`
   - Docker image dependencies

3. **Validation Code**
   - `netra_backend/app/logging_config.py`
   - `auth_service/auth_core/routes/auth_routes.py`
   - Service startup validation
   - Configuration management modules

4. **OAuth Configuration**
   - Google OAuth Console settings
   - Auth service configuration files
   - Environment-specific OAuth redirect URIs

## Validation Testing
Success criteria:
- No configuration warnings in staging startup logs
- SERVICE_ID validation passes without sanitization
- Sentry SDK available and configured
- OAuth URI configuration consistent across environments
- Error tracking functional in staging environment
- Authentication flows working without configuration warnings

## Long-term Configuration Management
1. **Configuration as Code:** Standardize all environment configuration
2. **Validation Pipeline:** Automated configuration validation in CI/CD
3. **Monitoring Integration:** Complete observability stack deployment
4. **Documentation:** Service configuration management runbook

---

## Latest Log Analysis (2025-09-15T21:37:47)
Updated with CLUSTER 4 analysis from GCP log monitoring:
- **20+ Sentry SDK warnings** in last hour
- **SERVICE_ID sanitization** ongoing issues
- **OAuth URI mismatches** between staging environments
- **Priority escalated to P2** due to configuration drift frequency

---
🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>