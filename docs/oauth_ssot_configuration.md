# OAuth SSOT Configuration System

**Document Version:** 1.0  
**Date:** September 5, 2025  
**Status:** Implemented  

## Overview

This document describes the modern Single Source of Truth (SSOT) OAuth configuration system that replaces previous fallback-based patterns. The new system provides explicit, named environment configurations that eliminate ambiguity and follow SSOT principles.

## Business Value

**Segment:** Platform/Internal  
**Business Goal:** Risk Reduction & Platform Stability  
**Value Impact:** Eliminates OAuth configuration failures and test environment issues  
**Strategic Impact:** Enables reliable authentication testing and deployment across all environments  

## Problem Solved

**Previous Issues:**
- OAuth configuration was failing because it looked for test-specific variables like `GOOGLE_OAUTH_CLIENT_ID_TEST`
- The system had no proper development environment configurations
- Tests were failing because OAuth credentials weren't set
- Used "fallback" patterns that violated SSOT principles

**Root Cause:**
- Missing explicit test environment OAuth configurations
- No SSOT OAuth configuration management
- Inconsistent environment variable naming across environments

## Architecture

### SSOT Configuration Structure

The OAuth configuration is now managed through the Central Configuration Validator (`shared.configuration.central_config_validator`) with explicit rules for each environment:

```python
# Environment-specific OAuth variables (NO fallbacks)
GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT     # for development
GOOGLE_OAUTH_CLIENT_ID_TEST            # for test  
GOOGLE_OAUTH_CLIENT_ID_STAGING         # for staging
GOOGLE_OAUTH_CLIENT_ID_PRODUCTION      # for production

GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT # for development
GOOGLE_OAUTH_CLIENT_SECRET_TEST        # for test
GOOGLE_OAUTH_CLIENT_SECRET_STAGING     # for staging  
GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION  # for production
```

### Central Validator Integration

The auth service now uses the central configuration validator for OAuth credentials:

```python
# Before (fallback-based, prone to failures)
def get_google_client_id() -> str:
    if env in ["development", "test"]:
        client_id = env_manager.get("GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT")
        if client_id:
            return client_id
    # ... complex fallback logic

# After (SSOT-based, reliable)
def get_google_client_id() -> str:
    validator = get_central_validator()
    return validator.get_oauth_client_id()  # Handles environment detection
```

## Environment Configurations

### Development Environment (`config/development.env`)
```bash
ENVIRONMENT=development
GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT=dev-oauth-client-id
GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT=dev-oauth-client-secret
OAUTH_REDIRECT_URI=http://localhost:8081/oauth/callback
```

### Test Environment (`config/test.env`)
```bash
ENVIRONMENT=test
GOOGLE_OAUTH_CLIENT_ID_TEST=test-oauth-client-id-for-automated-testing
GOOGLE_OAUTH_CLIENT_SECRET_TEST=test-oauth-client-secret-for-automated-testing
OAUTH_REDIRECT_URI=http://localhost:8081/oauth/callback
TEST_MODE=true
```

### Staging Environment (`config/staging.env`)
```bash
ENVIRONMENT=staging
# GOOGLE_OAUTH_CLIENT_ID_STAGING=<set-via-secrets-manager>
# GOOGLE_OAUTH_CLIENT_SECRET_STAGING=<set-via-secrets-manager>
```

### Production Environment (`config/production.env`)
```bash
ENVIRONMENT=production
# GOOGLE_OAUTH_CLIENT_ID_PRODUCTION=<set-via-secrets-manager>
# GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION=<set-via-secrets-manager>
```

## Implementation Details

### Central Configuration Validator Rules

The SSOT OAuth rules are defined in `shared.configuration.central_config_validator.CentralConfigurationValidator`:

```python
# OAuth Configuration Rules for ALL environments
CONFIGURATION_RULES = [
    # Development
    ConfigRule(
        env_var="GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT",
        requirement=ConfigRequirement.REQUIRED,
        environments={Environment.DEVELOPMENT},
        forbidden_values={"", "your-client-id", "REPLACE_WITH"},
        error_message="GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT required in development environment."
    ),
    # Test
    ConfigRule(
        env_var="GOOGLE_OAUTH_CLIENT_ID_TEST", 
        requirement=ConfigRequirement.REQUIRED,
        environments={Environment.TEST},
        forbidden_values={"", "your-client-id", "REPLACE_WITH"},
        error_message="GOOGLE_OAUTH_CLIENT_ID_TEST required in test environment."
    ),
    # ... staging and production rules
]
```

### SSOT OAuth Methods

The central validator provides SSOT methods for OAuth access:

```python
def get_oauth_credentials() -> Dict[str, str]:
    """Get OAuth credentials for current environment."""
    validator = get_central_validator()
    return validator.get_oauth_credentials()

def get_oauth_client_id() -> str:
    """Get OAuth client ID for current environment.""" 
    validator = get_central_validator()
    return validator.get_oauth_client_id()

def get_oauth_client_secret() -> str:
    """Get OAuth client secret for current environment."""
    validator = get_central_validator()
    return validator.get_oauth_client_secret()
```

### Auth Service Integration

The auth service's `secret_loader.py` now delegates to the SSOT system:

```python
@staticmethod
def get_google_client_id() -> str:
    """Get Google OAuth client ID using SSOT central configuration validator."""
    if get_central_validator is not None:
        try:
            validator = get_central_validator(lambda key, default=None: get_env().get(key, default))
            client_id = validator.get_oauth_client_id()
            return client_id
        except Exception as e:
            raise ValueError(f"OAuth client ID configuration failed via SSOT: {e}")
    
    raise ValueError("Central configuration validator not available for OAuth configuration")
```

## Key Principles

### 1. Named Environments (Not Fallbacks)
- Each environment has explicit, properly named configurations
- NO fallback patterns that can cause ambiguity
- Environment detection is handled by the central validator

### 2. Single Source of Truth  
- All OAuth configuration logic is centralized in `central_config_validator.py`
- Service-specific OAuth loading delegates to the SSOT
- Consistent validation rules across all services

### 3. Explicit Error Handling
- Clear error messages when OAuth credentials are missing
- No silent failures or unexpected fallbacks
- Hard stop on configuration issues to prevent runtime failures

### 4. Test Environment Support
- Dedicated test environment OAuth configurations
- Test-specific variable names that don't conflict with development
- Proper test isolation without production credential requirements

## Migration from Legacy System

### Before (Legacy Fallback System)
```python
# Complex fallback logic with potential failures
if env in ["development", "test"]:
    client_id = env_manager.get("GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT")
    if client_id:
        return client_id
elif env == "staging":
    client_id = env_manager.get("GOOGLE_OAUTH_CLIENT_ID_STAGING") 
    if client_id:
        return client_id
# ... more fallback logic
return ""  # Silent failure
```

### After (SSOT System)
```python
# Simple, reliable SSOT access
validator = get_central_validator()
return validator.get_oauth_client_id()  # Handles all environments
```

## Testing and Validation

### Validation Scripts
- `scripts/validate_oauth_ssot_simple.py` - Tests SSOT configuration structure
- `scripts/test_auth_oauth_integration.py` - Tests auth service integration
- Both scripts validate all four environments (development, test, staging, production)

### Test Results
All OAuth SSOT configurations have been validated and are working correctly:

```
OAuth SSOT Configuration Validation (Simple)
OAuth Rules Definition: PASSED
Environment Detection: PASSED
Overall: 2/2 tests passed

Auth Service OAuth SSOT Integration Test  
Auth Service OAuth Integration: PASSED
Auth Service OAuth Integration (Development): PASSED
Overall: 2/2 tests passed
```

## Configuration Requirements by Environment

### Development
- **Required**: `GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT`, `GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT`
- **Purpose**: Local development OAuth functionality
- **Security**: Lower security requirements, can use development credentials

### Test
- **Required**: `GOOGLE_OAUTH_CLIENT_ID_TEST`, `GOOGLE_OAUTH_CLIENT_SECRET_TEST` 
- **Purpose**: Automated testing without production credentials
- **Security**: Test-specific credentials that don't impact production

### Staging
- **Required**: `GOOGLE_OAUTH_CLIENT_ID_STAGING`, `GOOGLE_OAUTH_CLIENT_SECRET_STAGING`
- **Purpose**: Production-like testing environment
- **Security**: Secure credentials from Secret Manager or environment variables

### Production  
- **Required**: `GOOGLE_OAUTH_CLIENT_ID_PRODUCTION`, `GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION`
- **Purpose**: Live production OAuth functionality
- **Security**: Highly secure credentials from Secret Manager

## Benefits Achieved

### 1. Reliability
- Eliminates OAuth configuration failures in test environments
- Predictable behavior across all environments
- No more silent failures or unexpected fallbacks

### 2. Maintainability  
- Single source of truth for all OAuth configuration logic
- Clear environment-specific variable naming
- Centralized validation and error handling

### 3. Security
- Explicit configuration requirements prevent accidental credential leakage
- Each environment uses appropriate security measures  
- Clear separation between development and production credentials

### 4. Developer Experience
- Clear error messages when configuration is missing
- Consistent behavior across all environments
- Easy testing with dedicated test credentials

## Troubleshooting

### Common Issues

**Error**: `GOOGLE_OAUTH_CLIENT_ID_TEST required in test environment`
- **Solution**: Set the `GOOGLE_OAUTH_CLIENT_ID_TEST` environment variable
- **Check**: Verify `ENVIRONMENT=test` is set correctly

**Error**: `OAuth client ID configuration failed via SSOT`  
- **Solution**: Check that the central configuration validator is available
- **Check**: Verify all required OAuth environment variables are set

**Error**: `Central configuration validator not available`
- **Solution**: Ensure `shared.configuration` module is properly imported
- **Check**: Verify project paths and module dependencies

### Debug Commands

```bash
# Test OAuth SSOT configuration structure
python scripts/validate_oauth_ssot_simple.py

# Test auth service OAuth integration  
python scripts/test_auth_oauth_integration.py

# Validate specific environment configuration
ENVIRONMENT=test python -c "from shared.configuration.central_config_validator import get_oauth_client_id; print(get_oauth_client_id())"
```

## Future Enhancements

1. **Additional OAuth Providers**: Extend SSOT system to support GitHub, Microsoft, etc.
2. **Dynamic Configuration**: Support for runtime OAuth configuration updates
3. **OAuth Token Management**: Integrate token refresh and management into SSOT system
4. **Configuration Templates**: Generate environment-specific config files automatically

## References

- [CLAUDE.md](../CLAUDE.md) - Core architectural principles
- [Central Configuration Validator](../shared/configuration/central_config_validator.py) - SSOT implementation
- [Auth Service Secret Loader](../auth_service/auth_core/secret_loader.py) - Service integration
- [Test Environment Config](../config/test.env) - Test environment configuration example

---
**Implementation Complete**: September 5, 2025  
**Status**: Production Ready  
**Next Review**: As needed for additional OAuth providers