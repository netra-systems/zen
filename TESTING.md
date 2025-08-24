# 🧪 Netra Apex Testing Guide

> **Quick Start:** `python unified_test_runner.py --level smoke` 

This guide covers everything you need to know about testing in the Netra Apex platform.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Test Architecture](#test-architecture)
- [Running Tests](#running-tests)
- [Test Levels](#test-levels)
- [Service-Specific Testing](#service-specific-testing)
- [Advanced Features](#advanced-features)
- [Test Organization](#test-organization)
- [Writing Tests](#writing-tests)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)
- [Related Documentation](#related-documentation)

## Quick Start

### 🎯 Recommended Defaults

```bash
# DEFAULT for development (fast feedback)
python unified_test_runner.py --level integration --no-coverage --fast-fail

# Pre-commit validation (<30s)
python unified_test_runner.py --level smoke --fast-fail

# Agent changes
python unified_test_runner.py --level agents --real-llm --fast-fail

# Before releases
python unified_test_runner.py --level integration --real-llm --env staging
```

### Run Your First Test

```bash
# Run smoke tests (fastest, <30s)
python unified_test_runner.py --level smoke --fast-fail

# Run all tests for a specific service
python unified_test_runner.py --service backend --fast-fail

# Run with coverage report
python unified_test_runner.py --coverage

# Use real LLMs instead of mocks
python unified_test_runner.py --real-llm
```

### Essential Commands

| What You Want | Command |
|--------------|---------|
| **Quick pre-commit check** | `python unified_test_runner.py --level smoke --fast-fail` |
| **Test backend changes** | `python unified_test_runner.py --service backend --level unit --fast-fail --no-coverage` |
| **Test frontend changes** | `python unified_test_runner.py --service frontend --fast-fail` |
| **Full validation before merge** | `python unified_test_runner.py --level integration --no-coverage --fast-fail` |
| **Test with real services** | `python unified_test_runner.py --real-llm --env staging` |

## Test Architecture

### Unified Testing Infrastructure

```
📁 Root Directory
├── 🎯 unified_test_runner.py      # Single entry point for ALL tests
├── ⚙️  unified_test_config.py      # Central test configuration
├── 📦 test_framework/              # Test utilities and plumbing
│   ├── test_discovery.py          # Automatic test discovery
│   ├── test_executor.py           # Test execution engine
│   ├── test_optimizer.py          # Performance optimization
│   └── test_isolation.py          # Test isolation utilities
│
├── 📂 netra_backend/tests/        # Backend tests (stay here)
├── 📂 auth_service/tests/         # Auth tests (stay here)
└── 📂 frontend/__tests__/         # Frontend tests (stay here)
```

**Key Principle:** Test infrastructure is centralized, but test files remain with their code.

## Running Tests

### Basic Usage

```bash
python unified_test_runner.py [OPTIONS]
```

### Common Options

| Option | Description | Example |
|--------|-------------|---------|
| `--level` | Test level to run | `--level integration` |
| `--service` | Service to test | `--service backend` |
| `--env` | Environment | `--env staging` |
| `--real-llm` | Use real LLMs | `--real-llm` |
| `--coverage` | Generate coverage | `--coverage` |
| `--parallel` | Run in parallel | `--parallel` |
| `--pattern` | Match pattern | `--pattern test_auth` |
| **`--fast-fail`** | **Stop on first failure (recommended)** | `--fast-fail` |
| `--no-coverage` | Skip coverage for speed | `--no-coverage` |
| `--max-failures` | Stop after N failures | `--max-failures 5` |

### Examples

```bash
# Backend unit tests with coverage
python unified_test_runner.py --service backend --level unit --coverage

# Frontend integration tests
python unified_test_runner.py --service frontend --level integration

# All auth service tests in parallel
python unified_test_runner.py --service auth --parallel

# Tests matching a pattern
python unified_test_runner.py --pattern "test_websocket"

# Quick smoke test before commit
python unified_test_runner.py --level smoke --fast-fail

# Full comprehensive test suite
python unified_test_runner.py --level comprehensive --coverage
```

## Test Levels

Tests are organized into levels based on speed and scope:

### 🚀 Smoke Tests (`--level smoke`)
- **Duration:** <30 seconds
- **Purpose:** Basic health checks
- **When:** Before every commit
- **Coverage:** Critical paths only

```bash
python unified_test_runner.py --level smoke
```

### 🔧 Unit Tests (`--level unit`)
- **Duration:** 1-2 minutes
- **Purpose:** Component isolation testing
- **When:** During development
- **Coverage:** Individual components

```bash
python unified_test_runner.py --level unit
```

### 🔗 Integration Tests (`--level integration`)
- **Duration:** 3-5 minutes
- **Purpose:** Feature integration testing
- **When:** Before merging PRs
- **Coverage:** Component interactions

```bash
python unified_test_runner.py --level integration
```

### 📊 Comprehensive Tests (`--level comprehensive`)
- **Duration:** 30-45 minutes
- **Purpose:** Full system validation
- **When:** Before releases
- **Coverage:** Everything

```bash
python unified_test_runner.py --level comprehensive
```

### ⚡ Critical Tests (`--level critical`)
- **Duration:** 1-2 minutes
- **Purpose:** Revenue-critical paths
- **When:** Hotfixes, emergency deployments
- **Coverage:** Business-critical only

```bash
python unified_test_runner.py --level critical
```

### 🤖 Agent Tests (`--level agents`)
- **Duration:** 2-3 minutes
- **Purpose:** AI agent testing with real LLMs
- **When:** After agent changes
- **Coverage:** Agent functionality

```bash
python unified_test_runner.py --level agents --real-llm
```

## Service-Specific Testing

### Backend Testing

```bash
# All backend tests
python unified_test_runner.py --service backend

# Specific category
python unified_test_runner.py --service backend --level unit

# With coverage requirements
python unified_test_runner.py --service backend --coverage --min-coverage 80
```

**Test Categories:**
- `unit`: Service and core logic tests
- `integration`: API and route tests
- `agents`: AI agent tests
- `websocket`: WebSocket functionality
- `database`: Database operations

### Frontend Testing

```bash
# All frontend tests
python unified_test_runner.py --service frontend

# Component tests only
python unified_test_runner.py --service frontend --level unit

# E2E tests with Cypress
python unified_test_runner.py --service frontend --e2e
```

**Test Categories:**
- `components`: React component tests
- `hooks`: Custom hook tests
- `store`: State management tests
- `integration`: Frontend integration tests

### Auth Service Testing

```bash
# All auth tests
python unified_test_runner.py --service auth

# OAuth flow tests
python unified_test_runner.py --service auth --pattern oauth

# Security tests
python unified_test_runner.py --service auth --pattern security
```

## Advanced Features

### Real Service Testing

Test against real services instead of mocks:

```bash
# Use real LLMs
python unified_test_runner.py --real-llm

# Test against staging environment
python unified_test_runner.py --env staging

# Full staging validation
python unified_test_runner.py --env staging --real-llm --level integration
```

### ⚡ Speed Optimizations

Maximize test execution speed with these options:

```bash
# RECOMMENDED: Fast-fail with no coverage
python unified_test_runner.py --level integration --fast-fail --no-coverage

# Stop after first failure (saves time)
python unified_test_runner.py --fast-fail

# Stop after N failures
python unified_test_runner.py --max-failures 5

# Skip coverage collection (30-50% faster)
python unified_test_runner.py --no-coverage

# Suppress warnings for cleaner output
python unified_test_runner.py --no-warnings

# CI mode (combines optimizations)
python unified_test_runner.py --ci
```

### Parallel Execution

Speed up test execution with parallelization:

```bash
# Auto-detect optimal workers (default)
python unified_test_runner.py --parallel

# Specify worker count
python unified_test_runner.py --parallel --workers 8

# Run serially for debugging
python unified_test_runner.py --parallel 1
```

### Coverage Reports

Generate detailed coverage reports:

```bash
# With HTML report
python unified_test_runner.py --coverage

# With minimum coverage enforcement
python unified_test_runner.py --coverage --min-coverage 85

# Service-specific coverage
python unified_test_runner.py --service backend --coverage
```

### Test Discovery

List available tests without running:

```bash
# List all tests
python unified_test_runner.py --list

# Validate test structure
python unified_test_runner.py --validate
```

## Test Organization

### File Structure

```
service/
├── tests/
│   ├── unit/           # Isolated component tests
│   ├── integration/    # Integration tests
│   ├── e2e/           # End-to-end tests
│   ├── performance/   # Performance tests
│   └── conftest.py    # Pytest configuration
```

### Test Naming Conventions

- **Files:** `test_*.py` or `*_test.py`
- **Classes:** `TestClassName`
- **Functions:** `test_function_name`
- **Fixtures:** `fixture_name`

### Test Markers

Use pytest markers to categorize tests:

```python
import pytest

@pytest.mark.unit
def test_user_creation():
    """Unit test for user creation"""
    pass

@pytest.mark.integration
@pytest.mark.real_database
def test_user_persistence():
    """Integration test with real database"""
    pass

@pytest.mark.critical
@pytest.mark.smoke
def test_critical_auth_flow():
    """Critical path test"""
    pass
```

## Writing Tests

### Best Practices

1. **Test Real Functionality, Not Mocks**
   ```python
   # ❌ Bad: Testing the mock
   def test_with_mock():
       mock_service = Mock()
       mock_service.get_user.return_value = {"id": 1}
       assert mock_service.get_user()["id"] == 1
   
   # ✅ Good: Testing real behavior
   def test_with_real_service():
       service = UserService()
       user = service.get_user(1)
       assert user.id == 1
   ```

2. **Use Descriptive Names**
   ```python
   # ❌ Bad
   def test_1():
       pass
   
   # ✅ Good
   def test_user_creation_with_valid_email_succeeds():
       pass
   ```

3. **Keep Tests Focused**
   ```python
   # One assertion per test when possible
   def test_user_email_validation():
       user = User(email="test@example.com")
       assert user.is_email_valid()
   ```

### Using Fixtures

```python
import pytest
from netra_backend.app.db import SessionLocal

@pytest.fixture
def db_session():
    """Provide a transactional database session"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

def test_create_user(db_session):
    """Test user creation with database session"""
    user = User(email="test@example.com")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
```

## CI/CD Integration

### GitHub Actions

The unified test runner integrates with CI/CD pipelines:

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Run smoke tests
        run: python unified_test_runner.py --level smoke
      
      - name: Run unit tests with coverage
        run: python unified_test_runner.py --level unit --coverage
      
      - name: Run integration tests
        if: github.event_name == 'pull_request'
        run: python unified_test_runner.py --level integration
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: smoke-tests
        name: Run smoke tests
        entry: python unified_test_runner.py --level smoke --fast-fail
        language: system
        pass_filenames: false
        always_run: true
```

## Troubleshooting

### Common Issues

#### Import Errors

```bash
# If you see: ModuleNotFoundError
# Solution: Ensure PROJECT_ROOT is in path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### Test Discovery Issues

```bash
# List all discovered tests
python unified_test_runner.py --list

# Validate test structure
python unified_test_runner.py --validate
```

#### Coverage Not Generated

```bash
# Ensure coverage is installed
pip install pytest-cov

# Run with explicit coverage
python unified_test_runner.py --coverage --cov-report=html
```

#### Parallel Execution Failures

```bash
# Disable parallel execution for debugging
python unified_test_runner.py --no-parallel --verbose
```

### Debug Mode

Run tests with maximum verbosity for debugging:

```bash
python unified_test_runner.py --verbose --no-parallel --fast-fail
```

## Environment Variables

Key environment variables for test configuration:

```bash
# Test environment
export TEST_ENV=local|dev|staging|prod

# Use real services
export REAL_LLM=true
export USE_MOCKS=false

# Database URLs
export TEST_DATABASE_URL=postgresql://test:test@localhost/test_db
export TEST_REDIS_URL=redis://localhost:6379/1

# Coverage settings
export COVERAGE_ENABLED=true
export MIN_COVERAGE=80
```

## Performance Optimization

### Tips for Faster Tests

1. **Use Parallel Execution**
   ```bash
   python unified_test_runner.py --parallel --workers auto
   ```

2. **Run Only Affected Tests**
   ```bash
   python unified_test_runner.py --pattern "changed_module"
   ```

3. **Use Test Levels Appropriately**
   - Development: `--level unit`
   - Pre-commit: `--level smoke`
   - Pre-merge: `--level integration`

4. **Skip Coverage During Development**
   ```bash
   python unified_test_runner.py --no-coverage
   ```

## Related Documentation

### Testing Specifications
- [📖 Test Runner Guide](SPEC/test_runner_guide.xml) - Detailed runner specification
- [📖 Testing Strategy](SPEC/testing.xml) - Comprehensive testing strategy
- [📖 Coverage Requirements](SPEC/coverage_requirements.xml) - Coverage targets

### Testing Guides
- [📖 E2E Testing Guide](docs/testing/TESTING_GUIDE.md) - End-to-end testing
- [📖 CI/CD Testing](docs/testing/CICD_TESTING_GUIDE.md) - CI/CD integration
- [📖 Real Service Testing](docs/testing/real_service_testing_guide.md) - Testing with real services
- [📖 Test Operations Runbook](docs/testing/TEST_OPERATIONS_RUNBOOK.md) - Operational procedures

### Implementation Reports
- [📊 Test Organization Audit](TEST_ORGANIZATION_AUDIT.md) - Current test structure
- [📊 Test Index](MASTER_TEST_INDEX.md) - Complete test inventory
- [📊 Test Reports](test_reports/) - Historical test results

### Learnings
- [💡 Test Unification](SPEC/learnings/test_unification.xml) - Infrastructure unification insights
- [💡 Testing Learnings](SPEC/learnings/testing.xml) - General testing insights
- [💡 Test Environment Fixes](SPEC/learnings/test_environment_fixes.xml) - Environment setup

## Getting Help

### Quick Commands Reference

```bash
# Show help
python unified_test_runner.py --help

# List available tests
python unified_test_runner.py --list

# Validate test configuration
python unified_test_runner.py --validate
```

### Support Channels

- **Documentation:** This guide and linked resources
- **Specs:** Check `SPEC/` directory for detailed specifications
- **Learnings:** Review `SPEC/learnings/` for common solutions

---

## Summary

The Netra Apex testing infrastructure provides:

✅ **Single Entry Point:** `unified_test_runner.py` for all tests  
✅ **Service Agnostic:** Same interface for backend, frontend, and auth  
✅ **Multiple Test Levels:** From smoke to comprehensive  
✅ **Flexible Execution:** Parallel, coverage, real services  
✅ **Clear Organization:** Infrastructure centralized, tests stay with code  

**Remember:** Always run `python unified_test_runner.py --level smoke` before committing!

---

*Last Updated: August 24, 2025*  
*Version: 1.1*