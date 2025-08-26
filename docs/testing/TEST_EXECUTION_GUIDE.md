# Test Execution Guide

## Quick Start
```bash
# Fast feedback loop (recommended for development)
python unified_test_runner.py --category integration --no-coverage --fast-fail

# Full test suite
python unified_test_runner.py --categories smoke unit integration api --real-llm

# Environment-specific testing
python unified_test_runner.py --env staging
python unified_test_runner.py --env prod --allow-prod
```

## Test Categories
- **smoke**: Critical path verification
- **unit**: Individual component tests
- **integration**: Service interaction tests
- **api**: HTTP endpoint tests
- **agent**: AI agent functionality tests

## Environment Markers
- `@env("staging")`: Staging environment only
- `@env("prod")`: Production environment (requires --allow-prod)
- `@dev_and_staging`: Development and staging environments

## Performance Options
- `--fast-fail`: Stop on first failure (faster feedback)
- `--no-coverage`: Skip coverage calculation (faster execution)
- `--parallel`: Run tests in parallel (when supported)
