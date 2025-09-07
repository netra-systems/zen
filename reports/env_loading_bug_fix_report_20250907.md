# Environment Loading Bug Fix Report - September 7, 2025

## Executive Summary

**Business Value Justification (BVJ):**
- **Segment:** Platform/Internal 
- **Business Goal:** System Stability and Test Infrastructure
- **Value Impact:** Fixes critical test failures blocking development velocity
- **Strategic Impact:** Ensures configuration system works correctly across all environments

## Problem Statement

Five tests in `tests/unit/test_unified_env_loading.py` are failing with environment variables not being properly loaded from the test environment. The specific failures are:

1. `test_load_from_dotenv_file_in_development` - LLM API key is None instead of expected value
2. `test_env_vars_override_dotenv_file` - Same issue with LLM API key  
3. `test_no_dotenv_loading_in_production` - Same issue with LLM API key
4. `test_all_required_secrets_populated_from_env` - LLM API key is None instead of 'test_gemini'
5. `test_service_modes_from_env` - llm_mode is 'shared' instead of 'mock'

All tests are showing validation errors for missing JWT_SECRET_KEY and OAuth credentials.

## FIVE WHYS Analysis

**WHY #1**: Why are the LLM API keys showing as None instead of the expected test values?
- The LLM configs are being created with None API keys instead of the environment variable values.

**WHY #2**: Why are LLM configs not getting the API keys from environment variables?
- Looking at the code, the NetraTestingConfig (which is used in pytest context) does load API keys in `_load_api_keys_from_environment()` and properly sets up `llm_configs` if `GEMINI_API_KEY` is found.

**WHY #3**: Why is the `_load_api_keys_from_environment()` method not being called or not finding the environment variables?
- The method is called in `__init__()`, but the issue is that the tests are setting values in `IsolatedEnvironment` using `env.set()`, but when the config classes are created, they're using a fresh `get_env()` instance that may not see the test values.

**WHY #4**: Why is the IsolatedEnvironment not persisting the values set in tests?
- Looking at the test setup, the tests are using `env.set(var, value, "test")` to set values, but when the configuration classes call `get_env()` in their `__init__` methods, they may be getting a different instance or the values are not being properly stored.

**WHY #5**: Why are the test-scoped environment variables not being seen by the configuration system?
- **ROOT CAUSE**: The issue is in the environment isolation between test setup and config loading. The test uses `env.set()` with a "test" scope, but the config classes create their own `get_env()` instances that may not see the test-scoped values. There's an environment isolation bug where test-scoped variables aren't being propagated to the config loading process.

## Mermaid Diagrams

### Ideal Working State

```mermaid
graph TD
    A[Test Setup: env.set('GEMINI_API_KEY', 'test_gemini_key', 'test')] --> B[IsolatedEnvironment Singleton]
    B --> C[Config Manager Creates NetraTestingConfig]
    C --> D[NetraTestingConfig.__init__ calls get_env()]
    D --> E[get_env() Returns Same Singleton Instance]
    E --> F[_load_api_keys_from_environment() gets GEMINI_API_KEY]
    F --> G[Creates LLMConfig with api_key='test_gemini_key']
    G --> H[Test Assertion Passes: config.llm_configs['default'].api_key == 'test_gemini_key']
```

### Current Failure State

```mermaid
graph TD
    A[Test Setup: env.set('GEMINI_API_KEY', 'test_gemini_key', 'test')] --> B[IsolatedEnvironment Instance 1]
    B --> |Isolation Bug| C[Config Manager Creates NetraTestingConfig]
    C --> D[NetraTestingConfig.__init__ calls get_env()]
    D --> E[get_env() Returns Different Instance/Missing Values]
    E --> F[_load_api_keys_from_environment() gets None for GEMINI_API_KEY]
    F --> G[Creates LLMConfig with api_key=None]
    G --> H[Test Assertion Fails: config.llm_configs['default'].api_key is None != 'test_gemini_key']
```

## Technical Analysis

### Root Cause Identified

The issue is in the singleton consistency and test isolation. Looking at the `IsolatedEnvironment` code, there are several potential issues:

1. **Singleton Consistency Issues**: The code has both `_env_instance` (module-level) and `IsolatedEnvironment._instance` (class-level) singletons that may become inconsistent.

2. **Test Context Detection**: The `_is_test_context()` method has complex logic that may not properly detect pytest execution in all cases.

3. **Environment Isolation**: When tests set variables using `env.set()`, these may not be visible to config classes that create new `get_env()` instances.

### Key Issues Found

1. **Test Context Detection Flaw**: The `_is_test_context()` method checks for `'pytest' in sys.modules` but also requires `hasattr(sys.modules['pytest'], 'main')` and other conditions that may fail.

2. **Singleton Inconsistency**: Multiple singleton instances may exist, causing environment variables set in one instance not to be visible in another.

3. **Environment Variable Propagation**: Test-scoped variables may not be properly propagated to config loading contexts.

## Planned Solution

### 1. Fix Singleton Consistency
- Ensure `get_env()` always returns the same instance
- Fix the singleton pattern to be truly thread-safe and consistent

### 2. Improve Test Context Detection
- Simplify and make more robust the test context detection
- Ensure test variables are always visible during config loading

### 3. Fix Environment Variable Propagation
- Ensure that variables set via `env.set()` are immediately visible to all subsequent `get_env()` calls
- Fix isolation mode behavior during testing

### 4. Add Test Reproduction
- Create a simple test that reproduces the bug
- Verify the fix resolves the issue

## Implementation Plan

1. **Phase 1**: Fix IsolatedEnvironment singleton consistency
2. **Phase 2**: Improve test context detection and variable propagation  
3. **Phase 3**: Update configuration classes to ensure proper environment access
4. **Phase 4**: Add comprehensive tests and verification

## Files to be Modified

1. `shared/isolated_environment.py` - Fix singleton and test context issues
2. `netra_backend/app/schemas/config.py` - Ensure proper environment access in config classes
3. `tests/unit/test_unified_env_loading.py` - Add reproduction test
4. Potentially other config-related files if needed

## Success Criteria

- All 5 failing tests in `test_unified_env_loading.py` pass
- Test environment variables are properly propagated to config classes
- No regression in other environment-related functionality
- Singleton consistency maintained across all contexts

## Next Steps

1. Implement the fixes identified above
2. Run the failing tests to verify resolution
3. Run full test suite to ensure no regressions
4. Document the changes and update any related documentation

---

*Report generated as part of mandatory bug fixing process following CLAUDE.md requirements*