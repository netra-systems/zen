# ClickHouse SSOT Compliance Tests

This directory contains compliance tests to ensure Single Source of Truth (SSOT) adherence for ClickHouse implementations in the analytics service.

## Overview

The analytics service currently has SSOT violations with multiple competing ClickHouse implementations. These tests detect violations and enforce the architectural requirement that `clickhouse_manager.py` should be the only ClickHouse implementation.

## Current Status: FAILING ❌

These tests are **designed to fail** until SSOT compliance is achieved. The current violations include:

1. **Multiple Implementations**: 3 ClickHouse implementations found (should be 1)
2. **Legacy Imports**: Files importing from deprecated `clickhouse.py` 
3. **Incomplete Initialization**: Service initialization contains TODO items
4. **Non-SSOT Usage**: Direct clickhouse_driver imports outside SSOT

## Running the Tests

### Quick Run
```bash
# From analytics_service directory
python3 run_ssot_compliance_tests.py
```

### Detailed Run
```bash
# From analytics_service directory  
python3 run_ssot_compliance_tests.py --verbose
```

### Individual Test Categories
```bash
# Test for duplicate implementations
python3 -m pytest tests/compliance/test_clickhouse_ssot_violations.py::TestClickHouseSSotViolations::test_only_one_clickhouse_implementation_exists -v

# Test for legacy imports
python3 -m pytest tests/compliance/test_clickhouse_ssot_violations.py::TestClickHouseSSotViolations::test_no_imports_of_legacy_clickhouse_module -v

# Full compliance report
python3 -m pytest tests/compliance/test_clickhouse_ssot_violations.py::TestClickHouseSSotViolations::test_compliance_summary_report -v
```

## Test Categories

### 1. Implementation Count Tests
- `test_only_one_clickhouse_implementation_exists`: Ensures only `clickhouse_manager.py` exists
- `test_clickhouse_manager_has_required_features`: Validates SSOT has all required features

### 2. Import Compliance Tests
- `test_no_imports_of_legacy_clickhouse_module`: Detects imports from legacy `clickhouse.py`
- `test_all_files_use_ssot_implementation`: Ensures all files use the SSOT
- `test_no_direct_clickhouse_driver_imports_outside_ssot`: Prevents bypassing SSOT abstraction

### 3. Model Usage Tests
- `test_no_deprecated_model_imports`: Detects usage of deprecated event models
- `test_ast_analysis_for_clickhouse_class_usage`: AST-based detection of legacy class usage

### 4. Service Quality Tests
- `test_service_initialization_is_complete`: Ensures no TODOs in service initialization
- `test_connection_pooling_functionality`: Validates connection pooling works
- `test_health_check_loop_functionality`: Validates health monitoring
- `test_retry_logic_with_exponential_backoff`: Validates retry mechanisms

### 5. Performance Tests
- `test_performance_single_vs_pooled_connections`: Validates performance benefits

### 6. Comprehensive Reporting
- `test_compliance_summary_report`: Generates detailed compliance status report

## Fixing SSOT Violations

To achieve SSOT compliance:

### Step 1: Remove Duplicate Implementations
```bash
# Remove the legacy implementation
rm analytics_service/analytics_core/database/clickhouse.py
```

### Step 2: Update All Imports
Find and replace all imports:
```bash
# Find legacy imports
grep -r "from.*clickhouse import" analytics_service/

# Replace with SSOT imports
# OLD: from analytics_service.analytics_core.database.clickhouse import ClickHouseManager
# NEW: from analytics_service.analytics_core.database.clickhouse_manager import ClickHouseManager
```

### Step 3: Complete Service Initialization
Edit `analytics_service/main.py` and replace the TODO at line 47 with proper initialization.

### Step 4: Validate Changes
```bash
python3 run_ssot_compliance_tests.py
```

## Expected Final State

When SSOT compliance is achieved:
- ✅ Only `clickhouse_manager.py` exists as ClickHouse implementation
- ✅ All imports use `clickhouse_manager` 
- ✅ Service initialization is complete
- ✅ All tests pass
- ✅ Compliance score: 100%

## Business Value

Achieving SSOT compliance provides:
- **Reduced Maintenance**: Single codebase to maintain
- **Consistent Behavior**: Unified connection pooling, retry logic, health checks
- **Performance**: Optimized connection management
- **Reliability**: Proven enterprise-grade features in one place
- **Developer Velocity**: Clear patterns for database interactions

## Integration with CI/CD

Add to your CI pipeline:
```yaml
- name: Run ClickHouse SSOT Compliance Tests
  run: |
    cd analytics_service
    python3 run_ssot_compliance_tests.py
```

The tests will fail CI until SSOT compliance is achieved, preventing deployment of non-compliant code.