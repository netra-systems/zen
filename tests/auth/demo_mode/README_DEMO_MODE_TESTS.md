# Demo Mode Authentication Test Suite

## Overview

This test suite validates the implementation of permissive authentication for demo environments. These tests are designed to **INITIALLY FAIL**, demonstrating the current restrictive authentication behavior. Once demo mode features are implemented, these tests should pass.

## Business Justification

**BUSINESS VALUE**: Free Segment - Demo Environment Usability  
**GOAL**: Conversion - Eliminate authentication friction for potential customers  
**VALUE IMPACT**: Higher demo completion rates leading to increased customer conversion  
**REVENUE IMPACT**: Estimated 20-30% improvement in demo-to-customer conversion rates

## Test Structure

### 1. Configuration Tests (`test_demo_mode_configuration.py`)
**Purpose**: Verify demo mode detection and configuration management
- DEMO_MODE environment variable detection
- Configuration adaptation based on mode
- Feature flag integration
- Validation and logging

### 2. JWT Validation Tests (`test_jwt_validation_permissive.py`) 
**Purpose**: Verify relaxed JWT validation in demo mode
- Extended JWT expiration (48 hours vs 15 minutes)
- Broader audience acceptance
- Disabled replay protection
- Auto-token refresh
- Relaxed signature validation

### 3. User Creation Tests (`test_user_creation_flexible.py`)
**Purpose**: Verify simplified user registration in demo mode
- Simple password requirements (4 chars vs complex)
- Simple email validation (test@test allowed)
- Auto-user creation from JWT claims
- Default demo users availability
- Bypassed email verification

### 4. Circuit Breaker Tests (`test_circuit_breaker_relaxed.py`)
**Purpose**: Verify relaxed circuit breaker behavior in demo mode
- Higher failure threshold (10 vs 5 failures)
- Shorter timeout duration (30s vs 60s)
- Demo user bypass capabilities
- Gradual degradation vs hard cutoff

### 5. Integration Tests (`../integration/test_demo_mode_auth_integration.py`)
**Purpose**: End-to-end demo authentication flow validation
- Complete registration and login flow
- WebSocket authentication
- Agent execution with demo users
- Cross-service JWT consistency
- Graceful degradation handling

## Expected Test Results (Initial State)

### ❌ FAILING TESTS (Current State)
All demo mode tests should initially **FAIL** with these expected error patterns:

```
ImportError: No module named 'netra_backend.app.core.configuration.demo'
AttributeError: 'AuthService' object has no attribute 'create_user'
ValidationError: Password does not meet complexity requirements
JWT signature verification failed
Circuit breaker opened after 5 failures (not 10)
User not found: demo@demo.com
```

### ✅ PASSING TESTS (After Implementation)
Once demo mode is implemented, tests should pass with these behaviors:

```
Demo mode detected: True
Simple password 'demo' accepted
JWT valid for 48 hours
Circuit breaker allows 10 failures
Default user demo@demo.com authenticated
Auto-created user from JWT claims
```

## Test Execution

### Run All Demo Mode Tests
```bash
# Run all demo mode tests (will initially fail)
python tests/unified_test_runner.py --category demo_mode

# Run specific test modules
python -m pytest tests/auth/demo_mode/test_demo_mode_configuration.py -v
python -m pytest tests/auth/demo_mode/test_jwt_validation_permissive.py -v
python -m pytest tests/auth/demo_mode/test_user_creation_flexible.py -v
python -m pytest tests/auth/demo_mode/test_circuit_breaker_relaxed.py -v
python -m pytest tests/integration/test_demo_mode_auth_integration.py -v
```

### Environment Setup
```bash
# Set demo mode for testing
export DEMO_MODE=true
export ENVIRONMENT=demo
export JWT_SECRET_KEY=demo_test_secret

# Run with demo environment
DEMO_MODE=true python -m pytest tests/auth/demo_mode/ -v
```

## Implementation Guidance

These tests serve as **executable specifications** for implementing demo mode features:

### Phase 1: Configuration Infrastructure
1. Create `netra_backend/app/core/configuration/demo.py`
2. Implement `is_demo_mode()` function
3. Add demo-specific feature flags
4. Implement configuration validation

### Phase 2: Authentication Relaxation
1. Modify JWT validation for extended expiration
2. Implement simple password requirements
3. Add simple email validation patterns
4. Create default demo users

### Phase 3: Circuit Breaker Relaxation
1. Implement demo-specific circuit breaker configuration
2. Add demo user bypass functionality
3. Implement gradual degradation
4. Add demo-specific logging

### Phase 4: Integration & Polish
1. Ensure cross-service JWT consistency
2. Implement auto-user creation
3. Add WebSocket demo authentication
4. Implement graceful degradation

## Test Categories by Priority

### P0 - Critical (Must Work)
- Demo mode detection and configuration
- Simple user registration flow
- Basic JWT validation with extended expiration
- Default demo user login

### P1 - Important (Should Work)
- Circuit breaker relaxation
- Auto-user creation from JWT
- WebSocket authentication
- Cross-service consistency

### P2 - Nice to Have (Could Work)
- Advanced JWT debugging
- Graceful service degradation
- Bulk user creation
- Advanced circuit breaker features

## Success Metrics

### Development Success
- [ ] All demo mode tests pass
- [ ] Zero breaking changes to production mode
- [ ] Complete test coverage for demo features
- [ ] Performance impact < 5% overhead

### Business Success
- [ ] Demo completion rate improvement (target: +25%)
- [ ] Reduced support tickets for demo authentication issues
- [ ] Faster time-to-value for demo users
- [ ] Higher demo-to-customer conversion rate

## Security Considerations

### Production Safety
- Demo mode features **MUST** be completely disabled in production
- Environment-based feature flags prevent accidental activation
- All demo relaxations explicitly logged and monitored
- Separate demo user accounts with limited permissions

### Demo Security
- Demo mode still maintains basic security (HTTPS, basic validation)
- Demo users clearly identified and isolated
- Demo data cleanup and expiration
- Rate limiting still applied (but more generous)

## Monitoring and Observability

### Demo Mode Metrics
- Demo user registration rates
- Demo session duration
- Demo feature usage patterns
- Demo-to-production conversion rates

### Error Tracking
- Demo authentication failures
- Configuration validation errors
- Cross-service integration issues
- Performance impact measurements

---

**Last Updated**: 2025-09-11  
**Status**: Tests Created - Ready for Implementation  
**Next Steps**: Begin Phase 1 implementation and validate tests begin passing