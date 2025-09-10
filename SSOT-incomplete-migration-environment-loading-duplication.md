# SSOT-incomplete-migration-environment-loading-duplication

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/189
**Progress Tracker:** SSOT-incomplete-migration-environment-loading-duplication.md
**Status:** Step 0 Complete - Issue Created

## Critical SSOT Violation Discovered

**Problem:** Environment loading patterns duplicated across backend and auth service causing staging configuration failures that prevent users from logging in and getting AI responses.

## Key Files Affected
- `netra_backend/app/main.py:22-98` - Backend environment loading
- `auth_service/main.py:30-52` - Auth service environment loading  
- `netra_backend/app/core/lifespan_manager.py` - Backend startup management
- Various staging configuration files

## SSOT Violations Identified
1. **Environment Loading Duplication**: Each service has different logic for loading .env files and detecting staging environment
2. **Staging Detection Inconsistency**: Different staging environment detection patterns
3. **Startup Sequence Duplication**: Different lifespan management approaches
4. **Configuration Source Inconsistency**: Services may use different config sources in staging

## Business Impact
- JWT secret mismatches between services
- Database connection inconsistencies
- Authentication failures due to credential inconsistencies
- Staging deployment reliability issues
- **Directly blocks $500K+ ARR chat functionality**

## Proposed SSOT Solution
Create unified shared modules:
- `/shared/startup_environment_manager.py` - Centralized environment loading
- `/shared/service_startup_coordinator.py` - Unified service startup coordination
- `/shared/staging_configuration.py` - Staging-specific configuration management

## Process Progress
- [x] Step 0: Discover Next SSOT Issue (SSOT AUDIT) - COMPLETE
- [ ] Step 1: Discover and Plan Test
- [ ] Step 2: Execute Test Plan  
- [ ] Step 3: Plan Remediation
- [ ] Step 4: Execute Remediation
- [ ] Step 5: Test Fix Loop
- [ ] Step 6: PR and Closure

## Next Actions
1. Discover existing tests protecting startup/staging functionality
2. Plan new tests to validate SSOT refactor
3. Execute test plan
4. Plan and execute SSOT remediation
5. Validate all tests pass
6. Create PR for closure