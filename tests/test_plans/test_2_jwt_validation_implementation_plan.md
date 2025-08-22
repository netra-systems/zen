# Test Suite 2: JWT Cross-Service Validation - Implementation Plan

## Test Overview
**File**: `tests/unified/test_jwt_cross_service_validation_simple.py`
**Priority**: CRITICAL
**Business Impact**: $150K+ MRR
**Performance Target**: < 50ms validation per service

## Test Requirements

### Core Functionality to Test
1. Create JWT in Auth service
2. Validate same JWT in Backend service
3. Validate same JWT in WebSocket service
4. Verify identical claims extraction
5. Test invalid JWT rejection consistency
6. Performance: <50ms validation per service

### Test Cases (minimum 5 required)

#### Test 1: Basic JWT Creation and Validation
- Create JWT with standard claims in Auth service
- Validate token accepted by Backend service
- Validate token accepted by WebSocket service
- Verify all services extract same user_id and claims
- Measure validation time < 50ms per service

#### Test 2: Invalid Token Consistent Rejection
- Test malformed JWT (invalid format)
- Test expired JWT token
- Test JWT with invalid signature
- Verify all services reject with 401
- Consistent error messages across services

#### Test 3: Claims Extraction Consistency
- Create JWT with complex claims (roles, permissions, metadata)
- Verify Auth service extracts all claims correctly
- Verify Backend service extracts same claims
- Verify WebSocket gets identical user context
- No data loss or corruption

#### Test 4: Token Expiry Handling
- Create token with short expiry (1 minute)
- Validate accepted before expiry
- Wait for expiry
- Verify all services reject after expiry
- Consistent expiry behavior

#### Test 5: Performance Under Load
- Create 10 different JWTs
- Validate each across all services
- Measure p95 validation time
- Ensure < 50ms even under load
- No performance degradation

#### Test 6: Secret Key Synchronization
- Verify all services use same JWT secret
- Test token created by Auth works everywhere
- Test rotation scenario (if supported)
- Verify no secret mismatches

#### Test 7: Edge Cases and Boundaries
- Test maximum token size
- Test minimum valid token
- Test tokens with missing optional claims
- Test tokens with extra claims
- Verify consistent handling

## Implementation Guidelines

### Test Structure
```python
import pytest
import time
from tests.harness import UnifiedTestHarness
from tests.jwt_helper import JWTTestHelper

class TestJWTCrossServiceValidation:
    """
    Business Value: $150K+ MRR protection
    Coverage: JWT validation consistency across all services
    Performance: < 50ms per validation
    """
    
    async def test_basic_jwt_validation(self):
        # Implementation here
        pass
    
    async def test_invalid_token_rejection(self):
        # Implementation here
        pass
    
    # Additional tests...
```

### Key Utilities to Use
- `UnifiedTestHarness` for service orchestration
- `JWTTestHelper` for token creation/validation
- `time.perf_counter()` for precise timing
- Real service endpoints

### Success Criteria
- All tests pass consistently
- Validation < 50ms per service
- Identical claims extraction
- Consistent error handling
- No flaky tests

## Agent Responsibilities

### Agent 1: Test Suite Writer
- Implement all 7 test cases
- Follow Netra engineering principles
- Ensure < 300 lines per test file
- Add proper performance assertions

### Agent 2: Test Suite Reviewer
- Review code quality and standards
- Verify business value alignment
- Check performance requirements
- Ensure proper error handling

### Agent 3: Test Runner & System Fixer
- Run the test suite
- Fix JWT validation issues in services
- Ensure consistent validation logic
- Optimize performance if needed

### Agent 4: Final Reviewer
- Triple-check all work
- Verify business requirements met
- Ensure code quality standards
- Confirm performance targets achieved