# Test Execution Guide

**Last Updated:** 2025-09-12
**Total Tests:** 16,000+ tests across 21 categories

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
- **unit**: 9,761+ individual component tests
- **database**: Data persistence tests
- **security**: Authentication and authorization tests
- **e2e_critical**: Critical end-to-end flows

### MEDIUM Priority
- **integration**: 4,504+ service interaction tests
- **api**: HTTP endpoint tests
- **websocket**: Real-time communication tests
- **agent**: AI agent functionality tests
- **cypress**: Full service E2E tests

### LOW Priority
- **e2e**: 1,909+ complete user journey tests
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
