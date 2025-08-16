# Architecture Compliance Fix Plan - Top 50 Critical Violations

## Executive Summary
- **Total Violations**: 4,702
- **Critical File Size**: 170 files > 400 lines
- **Critical Functions**: 1,445 functions > 20 lines  
- **Test Stubs**: 43 in production code
- **Duplicate Types**: 322 instances

## Priority 1: CRITICAL FILES (Must Fix Immediately)

### Files Over 1000 Lines - SPLIT INTO MODULES
1. **test_supervisor_consolidated_comprehensive.py** (1212 lines)
   - Split into: test_routing.py, test_orchestration.py, test_error_handling.py
   - Isolated work: YES - Can be done independently

2. **architecture_health.py** (1186 lines)
   - Split into: violation_scanner.py, report_generator.py, dashboard_builder.py
   - Isolated work: YES

3. **test_tool_permission_service_comprehensive.py** (1146 lines)
   - Split into: test_permissions.py, test_rate_limiting.py, test_business_rules.py
   - Isolated work: YES

4. **test_quality_gate_service_comprehensive.py** (1123 lines)
   - Split into: test_validation.py, test_scoring.py, test_thresholds.py
   - Isolated work: YES

5. **test_async_utils.py** (1033 lines)
   - Split into: test_connection_pool.py, test_rate_limiter.py, test_retry_logic.py
   - Isolated work: YES

## Priority 2: CRITICAL FUNCTIONS (>100 lines)

### Functions to Decompose
1. **architecture_health.py::_build_html_dashboard** (326 lines)
   - Decompose into: generate_header(), generate_metrics(), generate_violations_table()
   - Isolated work: YES

2. **test_database_repositories.py::unit_of_work** (240 lines)
   - Decompose into: setup_repositories(), configure_transactions(), cleanup_resources()
   - Isolated work: YES

3. **test_frontend.py::main** (219 lines)
   - Decompose into: setup_test_env(), run_tests(), generate_report()
   - Isolated work: YES

4. **alembic migration::upgrade** (190 lines)
   - Decompose into: create_tables(), add_indexes(), add_constraints()
   - Isolated work: YES

5. **test_business_value_critical.py::setup_test_infrastructure** (186 lines)
   - Decompose into: setup_database(), setup_services(), setup_mocks()
   - Isolated work: YES

## Priority 3: TEST STUBS IN PRODUCTION

### Remove All Test Stubs (43 total)
1. **redis_manager.py** - Remove stub functions
2. **ws_manager.py** - Replace with real implementations
3. **synthetic_data_generator.py** - Complete implementations
4. **tool_dispatcher.py** - Replace placeholders
5. **async_utils.py** - Implement real utilities

## Priority 4: CORE APPLICATION FILES

### Split Core Files (300-500 lines)
1. **app/main.py** (389 lines)
   - Split lifespan function (130 lines) into: startup.py, shutdown.py
   - Isolated work: YES

2. **app/agents/tool_dispatcher.py** (494 lines)
   - Split into: dispatcher_core.py, tool_registry.py, execution_engine.py
   - Isolated work: YES

3. **app/core/async_utils.py** (482 lines)
   - Split into: connection_management.py, retry_logic.py, rate_limiting.py
   - Isolated work: YES

4. **app/core/exceptions.py** (515 lines)
   - Split into: base_exceptions.py, agent_exceptions.py, service_exceptions.py
   - Isolated work: YES

5. **app/core/service_interfaces.py** (469 lines)
   - Split into: agent_interfaces.py, service_interfaces.py, repository_interfaces.py
   - Isolated work: YES

## Priority 5: TYPE DEDUPLICATION

### Consolidate Duplicate Types (322 instances)
1. Identify all duplicate type definitions
2. Create single source of truth in app/schemas/
3. Update all imports to use centralized types
4. Remove duplicates

## Implementation Strategy

### Phase 1: Immediate Actions (Day 1-3)
- Fix test stubs (43 files) - HIGH RISK
- Split files > 1000 lines (10 files)
- Decompose functions > 100 lines (10 functions)

### Phase 2: Core Refactoring (Day 4-7)
- Split core application files (15 files)
- Decompose functions 50-100 lines (20 functions)
- Start type deduplication

### Phase 3: Comprehensive Cleanup (Day 8-14)
- Complete all file splits (remaining 145 files)
- Fix all function complexity issues
- Complete type deduplication

## Sub-Agent Task Allocation

### Isolated Tasks for Sub-Agents:
1. **Test File Splitter Agent** - Handle all test file splits
2. **Function Decomposer Agent** - Break down large functions
3. **Test Stub Remover Agent** - Remove and replace stubs
4. **Type Consolidator Agent** - Fix duplicate types
5. **Core Module Splitter Agent** - Split core application files

## Success Metrics
- Compliance score from 0% to 95%+
- All files under 300 lines
- All functions under 8 lines
- Zero test stubs in production
- Single source of truth for all types

## Verification Steps
1. Run `python scripts/check_architecture_compliance.py` after each fix
2. Ensure all tests pass: `python test_runner.py --level unit`
3. Review module boundaries for single responsibility
4. Validate type imports point to schemas/