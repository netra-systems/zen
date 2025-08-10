# Netra AI Platform - Testing Infrastructure

## Overview

The Netra AI Platform has a comprehensive testing infrastructure designed to make it easy for developers and Claude Code to run tests effectively. The testing system supports both backend (Python/FastAPI) and frontend (Next.js/React) testing with full coverage reporting.

## Quick Start

### Run Tests in 10 Seconds

```bash
# Quick smoke tests (< 1 minute)
python test_runner.py --mode quick

# Standard test suite (~ 5 minutes)
python test_runner.py --mode standard

# Comprehensive with coverage (~ 10 minutes) 
python test_runner.py --mode comprehensive
```

## Test Infrastructure Components

### 1. Unified Test Runner (`test_runner.py`)
- **Purpose**: Single entry point for all testing needs
- **Features**:
  - Predefined test modes (quick, standard, comprehensive, ci, critical)
  - Parallel execution support
  - Automatic report generation
  - Backend and frontend coordination

### 2. Backend Test Runner (`scripts/test_backend.py`)
- **Purpose**: Comprehensive backend testing with pytest
- **Features**:
  - Category-based test organization
  - Parallel test execution
  - Coverage reporting with minimum thresholds
  - HTML and JSON report generation
  - Dependency checking
- **Categories**:
  - `smoke`: Quick health checks
  - `unit`: Service and utility tests
  - `integration`: API endpoint tests
  - `agent`: Agent system tests
  - `websocket`: WebSocket tests
  - `auth`: Authentication tests
  - `database`: Repository tests
  - `critical`: Critical path tests

### 3. Frontend Test Runner (`scripts/test_frontend.py`)
- **Purpose**: Comprehensive frontend testing with Jest and Cypress
- **Features**:
  - Jest unit/integration testing
  - Cypress E2E testing
  - ESLint integration
  - TypeScript type checking
  - Coverage reporting
  - Watch mode for development
- **Categories**:
  - `smoke`: Critical tests
  - `unit`: Unit tests
  - `components`: Component tests
  - `hooks`: React hooks tests
  - `store`: State management tests
  - `websocket`: WebSocket provider tests
  - `auth`: Auth flow tests
  - `e2e`: End-to-end tests

## Test Modes

### Quick Mode
```bash
python test_runner.py --mode quick
```
- Runs smoke tests only
- Fails fast on first error
- Perfect for pre-commit checks
- Duration: < 1 minute

### Standard Mode
```bash
python test_runner.py --mode standard
```
- Runs unit tests with parallel execution
- Good balance of speed and coverage
- Duration: ~ 5 minutes

### Comprehensive Mode
```bash
python test_runner.py --mode comprehensive
```
- Full test suite with coverage
- Includes linting and type checking
- Generates detailed reports
- Duration: ~ 10 minutes

### CI Mode
```bash
python test_runner.py --mode ci --parallel
```
- Complete CI/CD pipeline
- All tests with strict coverage requirements
- HTML and JSON reports
- Build verification
- Duration: ~ 15 minutes

### Critical Mode
```bash
python test_runner.py --mode critical
```
- Only critical path tests
- Auth and WebSocket focus
- Quick validation of core features
- Duration: ~ 2 minutes

## Coverage Configuration

### Backend Coverage
- **Configuration**: `.coveragerc`
- **Minimum threshold**: 70%
- **Reports**: `reports/coverage/html/index.html`
- **Excluded**: tests, migrations, config files

### Frontend Coverage
- **Configuration**: `jest.config.cjs`
- **Minimum threshold**: 60%
- **Reports**: `reports/frontend-coverage/lcov-report/index.html`

## Test Reports

After running tests, find detailed reports in:

```
reports/
├── test_report.json          # Machine-readable results
├── test_report.md            # Human-readable summary
├── coverage/                 # Backend coverage
│   ├── html/                # HTML coverage report
│   ├── coverage.json        # JSON coverage data
│   └── coverage.xml         # XML for CI tools
├── frontend-coverage/        # Frontend coverage
│   └── lcov-report/         # HTML coverage report
└── tests/                    # Detailed test reports
    ├── report.html          # HTML test report
    └── report.json          # JSON test data
```

## Common Testing Workflows

### Before Committing Code
```bash
# Quick validation
python test_runner.py --mode quick

# If you modified backend
python scripts/test_backend.py --category unit --fail-fast

# If you modified frontend
python scripts/test_frontend.py --category components --lint
```

### After Fixing Bugs
```bash
# Run previously failed tests first
python scripts/test_backend.py --failed-first

# Run specific test that was failing
pytest app/tests/test_main.py::test_specific_function -vv
```

### During Development
```bash
# Backend watch mode (using watchfiles)
python run_server.py  # Server auto-reloads on changes

# Frontend watch mode
python scripts/test_frontend.py --watch

# Run specific category while developing
python scripts/test_backend.py --category agent --verbose
```

### Full Validation
```bash
# Complete test suite with all checks
python test_runner.py --mode ci --parallel

# Generate comprehensive reports
python scripts/test_backend.py --coverage --html-output --json-output
python scripts/test_frontend.py --coverage --lint --type-check --build
```

## Environment Setup

### Test Environment Variables
Tests automatically configure:
- `TESTING=1`
- `DATABASE_URL=sqlite+aiosqlite:///:memory:`
- `REDIS_URL=redis://localhost:6379/1`
- `SECRET_KEY=test-secret-key-for-testing-only`
- `LOG_LEVEL=WARNING`

### Prerequisites

#### Backend
- Python 3.11+
- Virtual environment activated
- Dependencies: `pip install -r requirements.txt`
- Required packages: pytest, pytest-asyncio, pytest-mock, pytest-cov, pytest-xdist

#### Frontend
- Node.js 18+
- Dependencies: `cd frontend && npm install`
- Required packages: jest, @testing-library/react, cypress, eslint

## Troubleshooting

### Common Issues

1. **Import errors in tests**
   - Ensure virtual environment is activated
   - Run: `pip install -r requirements.txt`

2. **Frontend tests fail to start**
   - Install dependencies: `cd frontend && npm install`
   - Clear cache: `npm cache clean --force`

3. **Coverage reports not generating**
   - Install coverage tools: `pip install pytest-cov`
   - For frontend: Ensure `@testing-library/jest-dom` is installed

4. **Parallel tests failing**
   - Install pytest-xdist: `pip install pytest-xdist`
   - Reduce workers: `--parallel 2` instead of `auto`

5. **WebSocket tests timing out**
   - Ensure Redis is running: `redis-cli ping`
   - Check backend server is accessible

### Debugging Tests

```bash
# Run with maximum verbosity
pytest -vvv app/tests/test_main.py

# Run with debugging output
pytest --capture=no app/tests/test_main.py

# Run single test with breakpoint
pytest -s app/tests/test_main.py::test_function

# Frontend debugging
npm test -- --verbose --no-coverage
```

## Best Practices

1. **Run quick tests frequently**: Use `--mode quick` before commits
2. **Use categories**: Target specific areas with `--category`
3. **Leverage parallel execution**: Use `--parallel auto` for speed
4. **Check coverage regularly**: Maintain minimum coverage thresholds
5. **Fix failures immediately**: Use `--failed-first` to focus on issues
6. **Keep tests isolated**: Each test should be independent
7. **Use mocks appropriately**: Mock external services and APIs
8. **Write descriptive test names**: Make failures easy to understand

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Tests
  run: |
    python test_runner.py --mode ci --parallel
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./reports/coverage/coverage.xml
```

### Pre-commit Hook
```bash
#!/bin/sh
python test_runner.py --mode quick
```

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure tests pass locally
3. Check coverage doesn't decrease
4. Run comprehensive suite before PR
5. Update test categories if needed

---

For more details, see the main documentation in `CLAUDE.md`.