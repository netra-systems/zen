# Test Execution Guide

**Last Updated:** 2025-09-14  
**Document Version:** 2.2  
**Total Tests:** 14,567+ test files with 16,000+ individual tests across 21 categories  
**Test Infrastructure Status:** OPERATIONAL - SSOT Compliance Achieved, Mock Factory SSOT Discovery Phase 1 Complete

## Quick Start
```bash
# Mission critical tests (MUST PASS for deployment)
python tests/unified_test_runner.py --category mission_critical

# Fast feedback loop (recommended for development)
python tests/unified_test_runner.py --category integration --no-coverage --fast-fail

# Full test suite with real services
python tests/unified_test_runner.py --categories smoke unit integration api --real-services

# Environment-specific testing
python tests/unified_test_runner.py --env staging
python tests/unified_test_runner.py --env prod --allow-prod
```

## Test Categories (21 Available)

### CRITICAL Priority
- **mission_critical**: 169 tests protecting core business functionality ($500K+ ARR)
- **golden_path**: Critical user flow validation (login → AI response)
- **smoke**: Critical path verification (pre-commit checks)
- **startup**: System initialization tests

### HIGH Priority
- **unit**: 11,325 individual component tests
- **database**: Data persistence tests
- **security**: Authentication and authorization tests
- **e2e_critical**: Critical end-to-end flows

### MEDIUM Priority
- **integration**: 757 service interaction tests
- **api**: HTTP endpoint tests
- **websocket**: Real-time communication tests
- **agent**: AI agent functionality tests
- **cypress**: Full service E2E tests

### LOW Priority
- **e2e**: 1,570 complete user journey tests
- **frontend**: React component tests
- **performance**: Load and performance tests

## Environment Markers
- `@env("staging")`: Staging environment only
- `@env("prod")`: Production environment (requires --allow-prod)
- `@dev_and_staging`: Development and staging environments

## Performance Options
- `--fast-fail`: Stop on first failure (faster feedback)
- `--no-coverage`: Skip coverage calculation (faster execution)
- `--parallel`: Run tests in parallel (when supported)

---

## Current Test Infrastructure Health (2025-09-14)

- **Mission Critical Tests**: ✅ 169 tests protecting $500K+ ARR functionality
- **SSOT Compliance**: ✅ Test infrastructure fully consolidated 
- **Real Service Testing**: ✅ Integration tests use real databases/LLMs
- **E2E Authentication**: ✅ All tests use real auth (JWT/OAuth)
- **Test Discovery**: ✅ 14,621+ tests discovered across 21 categories
- **Golden Path Protection**: ✅ Critical user flow validation operational
- **WebSocket Testing**: ✅ Real-time communication validation complete
- **Business Value Testing**: ✅ Revenue and savings tracking validated

## Test Categories by Business Impact

| Priority | Tests | Purpose | Business Impact |
|----------|-------|---------|-----------------|
| **CRITICAL** | 169 mission_critical | Core business protection | $500K+ ARR |
| **HIGH** | 11,325 unit + 757 integration | System reliability | Customer trust |
| **MEDIUM** | 1,570 e2e + websocket/api | User experience | Feature quality |
| **LOW** | Performance + frontend | Optimization | Development velocity |
