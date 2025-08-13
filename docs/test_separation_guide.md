# Test Separation Guide

## Overview
The test suite has been reorganized to better separate "real" tests (requiring external services) from "plumbing" tests (using only mocks). This enables faster CI/CD pipelines and more reliable test execution.

## Test Categories

### Real Service Tests (114 tests)
Tests that require actual external services:
- **real_llm**: Tests requiring LLM API calls (Anthropic, OpenAI, Gemini)
- **real_database**: Tests requiring PostgreSQL connections
- **real_redis**: Tests requiring Redis connections
- **real_clickhouse**: Tests requiring ClickHouse connections
- **real_services**: General marker for any real service dependency

### Mock/Plumbing Tests (2574 tests)
Tests using only mocks and no external dependencies:
- **mock_only**: Explicitly mock-only tests
- **unit**: Isolated component tests
- **integration**: Component interaction tests (with mocks)
- **e2e**: End-to-end flow tests (with mocks)

## Running Tests

### Quick CI/CD Testing (No External Dependencies)
```bash
# Run all tests except those requiring real services
pytest -m "not real_services"

# Run only mock tests
python test_runner.py --level mock_only

# Run smoke tests (excludes real services by default)
python test_runner.py --level smoke
```

### Real Service Testing
```bash
# Enable and run real LLM tests
ENABLE_REAL_LLM_TESTING=true pytest -m real_llm

# Run all real service tests
python test_runner.py --level real_services

# Run specific real service category
pytest -m real_database
pytest -m real_redis
pytest -m real_clickhouse
```

### Development Testing
```bash
# Run unit tests (fast, no external deps)
python test_runner.py --level unit

# Run integration tests (component interaction with mocks)
python test_runner.py --level integration
```

## Test Organization

### Files Requiring Real Services (16 files)
- `test_categories.py` - Uses all services (LLM, DB, Redis, ClickHouse)
- `agents/test_example_prompts_e2e_real.py` - Real LLM E2E tests (90 tests)
- `test_realistic_data_integration.py` - LLM integration
- `services/test_synthetic_data_service_v3.py` - ClickHouse operations
- `clickhouse/test_realistic_clickhouse_operations.py` - ClickHouse + LLM
- Plus 11 more specialized service tests

### Pure Mock Tests (89 files)
Well-isolated tests suitable for CI/CD:
- `test_agents_comprehensive.py`
- `test_api_endpoints_critical.py`
- `test_auth_critical.py`
- `test_business_value_critical.py`
- Plus 85 more mock-only test files

## Configuration

### pytest.ini Markers
All test markers are defined in both:
- `/pytest.ini` (root)
- `/app/pytest.ini` (app directory)

### Test Runner Levels
New levels added to `test_runner.py`:
- **real_services**: Run tests requiring external services
- **mock_only**: Run only mock tests for fast CI/CD

## Tools and Scripts

### Test Categorization
```bash
# Analyze and categorize all tests
python scripts/categorize_tests.py
```
Output: `test_categorization.json` with detailed test analysis

### Add Test Markers
```bash
# Preview marker additions
python scripts/add_test_markers.py --dry-run

# Add markers to test files
python scripts/add_test_markers.py
```

## Best Practices

1. **New Tests**: Always add appropriate markers
   - Use `@pytest.mark.mock_only` for tests with only mocks
   - Use `@pytest.mark.real_llm` for tests needing LLM APIs
   - Use `@pytest.mark.real_services` for any external dependency

2. **CI/CD Pipeline**: Use `pytest -m "not real_services"` for fast, reliable builds

3. **Staging/Production**: Run real service tests with proper API keys configured

4. **Development**: Use mock_only tests for rapid iteration

## Example Test with Markers

```python
import pytest
import os

@pytest.mark.real_llm
@pytest.mark.real_services
@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("ENABLE_REAL_LLM_TESTING") != "true",
    reason="Real LLM tests disabled. Set ENABLE_REAL_LLM_TESTING=true to run"
)
class TestRealLLMIntegration:
    """Tests requiring actual LLM API calls"""
    pass

@pytest.mark.mock_only
@pytest.mark.unit
class TestComponentLogic:
    """Fast unit tests using only mocks"""
    pass
```

## Summary Statistics

- **Total Test Files**: 139
- **Tests Requiring Real Services**: 114 tests across 16 files
- **Mock-Only Tests**: 2574 tests across 89 files
- **Uncategorized**: 30 files (need review)

This separation enables:
- ✅ Faster CI/CD builds (2574 tests without external deps)
- ✅ Reliable test execution (no flaky external service dependencies)
- ✅ Clear distinction between unit/integration and real E2E tests
- ✅ Flexibility to run real service tests when needed