# Issue #620 SSOT ExecutionEngine Migration Test Suite

This comprehensive test suite validates the SSOT ExecutionEngine migration from multiple deprecated implementations to UserExecutionEngine, protecting $500K+ ARR during the critical migration process.

## Test Categories

### 1. 🔍 Reproduction Tests (MUST FAIL before migration)
- **Purpose**: Demonstrate SSOT violations and security issues
- **Files**: `test_ssot_namespace_conflicts.py`, `test_user_context_contamination.py`
- **Expected**: FAIL before migration, PASS after migration
- **Business Impact**: Proves the security vulnerability exists

### 2. 🌟 Golden Path Protection (MUST ALWAYS PASS)
- **Purpose**: Protect core business value during migration
- **Files**: `test_golden_path_protection.py`
- **Expected**: PASS throughout migration process
- **Business Impact**: Protects $500K+ ARR chat functionality

### 3. 📡 WebSocket Event Integrity (MUST ALWAYS PASS)  
- **Purpose**: Ensure real-time events work during migration
- **Files**: `test_websocket_event_integrity.py`
- **Expected**: PASS throughout migration process
- **Business Impact**: Protects real-time chat experience

### 4. ✅ Migration Validation (MUST PASS after migration)
- **Purpose**: Validate successful SSOT consolidation
- **Files**: `test_ssot_migration_validation.py`
- **Expected**: FAIL before migration, PASS after migration
- **Business Impact**: Confirms security fixes implemented

## Quick Start

### Run All Tests
```bash
# Run complete test suite
python tests/issue_620/run_issue_620_tests.py --phase all

# Run with verbose output
python tests/issue_620/run_issue_620_tests.py --phase all --verbose

# Run with coverage report
python tests/issue_620/run_issue_620_tests.py --phase all --coverage
```

### Run Specific Test Phases
```bash
# Test reproduction (should FAIL before migration)
python tests/issue_620/run_issue_620_tests.py --phase reproduction

# Test golden path protection (should ALWAYS PASS)
python tests/issue_620/run_issue_620_tests.py --phase golden-path

# Test WebSocket integrity (should ALWAYS PASS)  
python tests/issue_620/run_issue_620_tests.py --phase websocket

# Test migration validation (should PASS after migration)
python tests/issue_620/run_issue_620_tests.py --phase validation
```

### Check Migration State
```bash
# Check current migration state
python tests/issue_620/run_issue_620_tests.py --check-state
```

### Individual Test Files
```bash
# Run specific test files
python -m pytest tests/issue_620/test_ssot_namespace_conflicts.py -v
python -m pytest tests/issue_620/test_golden_path_protection.py -v
python -m pytest tests/issue_620/test_websocket_event_integrity.py -v
python -m pytest tests/issue_620/test_ssot_migration_validation.py -v
```

## Test Execution Strategy

### NON-DOCKER FOCUSED
All tests are designed to run **without Docker dependencies**:
- ✅ **Unit Tests**: No Docker required
- ✅ **Integration Tests**: Non-Docker execution with mocks
- ✅ **E2E Tests**: Staging GCP remote (no local Docker)
- ❌ **Docker Tests**: Explicitly excluded with `-m "not docker"`

### Test Execution Hierarchy
```
Priority 1: Unit Tests (No Docker)
├── Namespace conflict reproduction 
├── Import resolution validation
├── Constructor compatibility tests
└── SSOT compliance verification

Priority 2: Integration Tests (Non-Docker)
├── Agent execution flow validation
├── WebSocket event delivery
├── User context isolation
└── Factory pattern compliance  

Priority 3: E2E Tests (Staging GCP)
├── Golden path user flow
├── Multi-user concurrency
├── WebSocket events end-to-end
└── Production-like validation
```

## Expected Test Results

### Before Migration (Pre-Migration State)
| Test Phase | Expected Result | Reason |
|------------|----------------|---------|
| Reproduction | ❌ FAIL | Demonstrates SSOT violations exist |
| Golden Path | ✅ PASS | Business value must be protected |
| WebSocket | ✅ PASS | Real-time chat must work |
| Validation | ❌ FAIL | Migration not yet complete |

### During Migration (Transition State)
| Test Phase | Expected Result | Reason |
|------------|----------------|---------|
| Reproduction | ❌ FAIL → ✅ PASS | Issues being resolved |
| Golden Path | ✅ PASS | Business value continuously protected |
| WebSocket | ✅ PASS | Real-time chat continuously working |
| Validation | ❌ FAIL → ✅ PASS | Migration progress validation |

### After Migration (Post-Migration State)
| Test Phase | Expected Result | Reason |
|------------|----------------|---------|
| Reproduction | ✅ PASS | SSOT violations resolved |
| Golden Path | ✅ PASS | Business value maintained |
| WebSocket | ✅ PASS | Real-time chat maintained |
| Validation | ✅ PASS | Migration successfully complete |

## Business Impact Monitoring

### Success Criteria
- ✅ **$500K+ ARR Protected**: Golden path tests pass
- ✅ **User Data Security**: No contamination between sessions  
- ✅ **Real-time Chat**: All 5 WebSocket events delivered
- ✅ **SSOT Compliance**: Single ExecutionEngine implementation
- ✅ **Zero Downtime**: Continuous functionality during migration

### Risk Indicators
- 🚨 **Golden Path Failure**: Core business value at risk
- 🚨 **User Contamination**: Security vulnerability active
- 🚨 **WebSocket Failures**: Chat experience degraded
- 🚨 **Multiple Implementations**: SSOT violations persist

## Test Files Overview

### `test_ssot_namespace_conflicts.py`
- Tests multiple ExecutionEngine implementations
- Validates import resolution consistency  
- Checks for factory pattern violations
- **Must FAIL** before migration to prove issue exists

### `test_user_context_contamination.py`
- Tests user data isolation between sessions
- Validates no cross-user data leakage
- Checks WebSocket event delivery isolation
- **Must FAIL** before migration to prove security risk

### `test_golden_path_protection.py`
- Tests complete user flow: login → get AI responses
- Validates core business functionality (90% platform value)
- Tests multi-user concurrent access
- Tests error recovery and data integrity
- **Must ALWAYS PASS** to protect business value

### `test_websocket_event_integrity.py`
- Tests all 5 critical WebSocket events delivered
- Validates event sequence and timing
- Tests per-user event isolation
- Tests error recovery and performance
- **Must ALWAYS PASS** to protect chat experience

### `test_ssot_migration_validation.py`
- Tests successful migration to UserExecutionEngine
- Validates single execution engine import source
- Tests legacy constructor compatibility
- Tests execution functionality equivalence
- **Must PASS** after migration to confirm success

### `test_utilities.py`
- Utility functions for all test categories
- Mock factories and test data generators
- Non-Docker test environment setup
- Migration progress tracking
- E2E staging test helpers

### `run_issue_620_tests.py`
- Comprehensive test runner with phase management
- Migration state detection
- Business impact assessment
- Progress tracking and reporting

## Integration with Existing Test Infrastructure

### SSOT Test Framework Integration
```python
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

class TestExample(SSotAsyncTestCase):
    """All tests inherit from SSOT base classes"""
```

### Mock Factory Usage
```python
from tests.issue_620.test_utilities import MockExecutionEngineFactory

# Create mocks using SSOT factory
mock_registry = MockExecutionEngineFactory.create_mock_agent_registry()
mock_bridge = MockExecutionEngineFactory.create_mock_websocket_bridge()
```

### Non-Docker Execution
```python
from tests.issue_620.test_utilities import NonDockerTestEnvironment

# Setup non-Docker test environment
env_config = NonDockerTestEnvironment.setup_test_environment()
```

## Troubleshooting

### Common Issues

**Test Import Errors**
```bash
# Ensure you're in the project root
cd /path/to/netra-core-generation-1
python tests/issue_620/run_issue_620_tests.py --phase all
```

**Docker-related Failures**
```bash
# Tests are designed to run without Docker
# Use --no-docker or -m "not docker" flags
python -m pytest tests/issue_620/ -m "not docker" -v
```

**Permission Issues**
```bash
# Make test runner executable
chmod +x tests/issue_620/run_issue_620_tests.py
```

### Debugging Test Failures

**Verbose Output**
```bash
python tests/issue_620/run_issue_620_tests.py --phase all --verbose
```

**Individual Test Debugging**
```bash
python -m pytest tests/issue_620/test_golden_path_protection.py::TestGoldenPathProtection::test_golden_path_login_to_ai_response -v -s
```

**Check Migration State**
```bash
python tests/issue_620/run_issue_620_tests.py --check-state
```

## Business Value Statement

This test suite protects **$500K+ ARR** by ensuring:

1. **Core Chat Functionality (90% platform value)** continues working during migration
2. **User Data Security** prevents contamination between sessions
3. **Real-time Experience** maintains WebSocket event delivery
4. **Migration Success** validates SSOT consolidation
5. **Zero Downtime** ensures continuous business operation

The comprehensive test strategy enables confident migration from multiple ExecutionEngine implementations to a single UserExecutionEngine SSOT while protecting all critical business functionality.