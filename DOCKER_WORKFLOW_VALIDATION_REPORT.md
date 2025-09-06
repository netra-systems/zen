# Docker Workflow Validation Report

**Generated:** 2025-09-05T09:51:07.712976  
**Status:** ❌ FAILED

## Summary
- **total_validations**: 5
- **passed**: 4
- **failed**: 1
- **warnings**: 2
- **success_rate**: 80.0%
- **total_time**: 57.32s

## Performance Metrics
- **ssot_compliance_duration**: 0.01s
- **refresh_dev_service_duration**: 0.16s
- **e2e_test_integration_duration**: 6.60s
- **no_fallback_logic_duration**: 0.01s
- **build_performance_duration**: 50.55s
- **total_validation_time**: 57.32s

## Validation Results

### SSOT Compliance - ✅ PASSED

**Message:** All Docker configurations comply with SSOT matrix  
**Duration:** 0.01s

**Details:**
- `compose_files`: 3
- `dockerfiles`: 9


### Refresh Dev Service - ✅ PASSED

**Message:** Refresh dev service validation passed  
**Duration:** 0.16s

**Details:**
- `dry_run_output_lines`: 11
- `expected_steps_found`: 4


### E2E Test Integration - ✅ PASSED

**Message:** E2E Docker integration validated successfully  
**Duration:** 6.60s

**Details:**
- `categories_found`: 56


### No Fallback Logic - ❌ FAILED

**Message:** Found 4 critical fallback violations  
**Duration:** 0.01s

**Warnings:**
- ⚠️ 2 platform-specific fallbacks documented as technical debt

**Details:**
- `critical_violations`: ['test_framework/unified_docker_manager.py:403 - logger.warning(f"No credentials found for environm', 'test_framework/unified_docker_manager.py:2094 - logger.warning("⚠️ Podman build failed, falling ba', 'test_framework/unified_docker_manager.py:2112 - logger.warning("⚠️ Podman build failed, falling ba', 'test_framework/unified_docker_manager.py:2619 - logger.warning("Docker not available, falling back']
- `platform_specific`: ['test_framework/unified_docker_manager.py:2094 - falling back to docker-compose', 'test_framework/unified_docker_manager.py:2112 - falling back to docker-compose']


### Build Performance - ✅ PASSED

**Message:** Build performance validated (auth: 50.4s)  
**Duration:** 50.55s

**Warnings:**
- ⚠️ Auth Alpine build took 50.4s (target: <5s)

**Details:**
- `auth_alpine_build`: 50.37024116516113


## Recommendations
1. Fix 1 failed validations before deployment
1. Remove fallback logic - use hard fails instead
1. Address 2 warnings for optimal performance