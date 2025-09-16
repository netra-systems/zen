# System Startup Tests Documentation

## Overview
Comprehensive test suite for validating system startup, initialization, and end-to-end user journeys for the Netra AI Optimization Platform.

## Test Structure

### 1. System Startup Specification
- **Location**: `SPEC/system_startup.xml`
- **Purpose**: Defines complete startup sequence for backend and frontend
- **Contents**: 
  - Startup steps and order
  - Health check requirements
  - Error handling procedures
  - Performance thresholds

### 2. Backend Startup Tests
- **File**: `tests/test_system_startup.py`
- **Purpose**: Test backend initialization sequence
- **Coverage**:
  - Environment validation
  - Configuration loading
  - Database connections
  - Service initialization
  - Agent system setup
  - WebSocket manager
  - Health checks

### 3. Frontend Startup Tests  
- **File**: `frontend/__tests__/system/startup.test.tsx`
- **Purpose**: Test frontend initialization
- **Coverage**:
  - Environment variables
  - API connectivity
  - WebSocket connections
  - Store initialization
  - Router setup
  - Error boundaries

### 4. Super E2E Tests
- **File**: `tests/test_super_e2e.py`
- **Purpose**: Complete user journey testing
- **Test Flow**:
  1. System startup
  2. User registration/login
  3. WebSocket connection
  4. Navigate to demo
  5. Send agent request
  6. Receive agent responses
  7. View reports
  8. Check thread history
  9. Test optimization tools
  10. Performance metrics
  11. Error recovery
  12. Concurrent users
  13. Graceful shutdown

### 5. Basic Startup Tests (merged into comprehensive tests)
- **File**: `tests/test_system_startup.py`
- **Purpose**: Comprehensive startup tests including basic functionality
- **Coverage**:
  - Import validation
  - Directory structure
  - Critical files
  - Basic performance
  - Error handling fix validation

## Running Tests

### Quick Test (Minimal)
```bash
# Run basic startup tests only
python scripts/test_system_startup.py --mode minimal
```

### Standard Test Suite
```bash
# Run backend, frontend, and E2E tests
python scripts/test_system_startup.py --mode standard
```

### Full Test Suite with Coverage
```bash
# Run all tests including performance benchmarks
python scripts/test_system_startup.py --mode full --coverage
```

### Individual Test Files
```bash
# Backend startup tests
pytest tests/test_system_startup.py -v

# Frontend startup tests (from frontend directory)
cd frontend
npm test -- startup.test

# E2E tests (requires running services)
pytest tests/test_super_e2e.py -v
```

## Test Modes

| Mode | Description | Duration | Requirements |
|------|-------------|----------|--------------|
| minimal | Basic startup tests only | ~1 min | Python |
| quick | Backend + Frontend tests | ~3 min | Python, Node.js |
| standard | All tests except performance | ~5 min | Python, Node.js, Redis |
| full | All tests including performance | ~10 min | All services |
| performance | Performance benchmarks only | ~2 min | Python |

## Prerequisites

### Required Software
- Python 3.8+
- Node.js 16+
- Redis (for non-minimal tests)
- PostgreSQL or SQLite

### Python Dependencies
```bash
pip install -r requirements.txt
pip install psutil  # For performance metrics
```

### Frontend Dependencies
```bash
cd frontend
npm install
```

## Environment Setup

### Test Environment Variables
```bash
# Required
export DATABASE_URL="sqlite+aiosqlite:///:memory:"
export SECRET_KEY="test-secret-key"
export TESTING="1"

# Optional
export REDIS_URL="redis://localhost:6379/1"
export LOG_LEVEL="DEBUG"
```

### First-Time Setup
1. Install dependencies
2. Set environment variables
3. Run minimal test to verify setup
4. Progressively run more comprehensive tests

## Test Reports

Reports are generated in `reports/system-startup/`:
- `test_report_YYYYMMDD_HHMMSS.json` - Detailed JSON report
- `test_report_YYYYMMDD_HHMMSS.md` - Markdown summary

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure all dependencies installed
   - Check Python path includes project root
   - Verify virtual environment activated

2. **Database Connection Failures**
   - Use in-memory SQLite for testing
   - Check #removed-legacyenvironment variable
   - Ensure database server running (if using PostgreSQL)

3. **WebSocket Test Hangs**
   - May indicate connection issues
   - Check WebSocket URL configuration
   - Use --timeout flag with pytest

4. **Frontend Test Failures**
   - Run `npm install` in frontend directory
   - Check Node.js version compatibility
   - Clear Jest cache: `npm test -- --clearCache`

### Debug Commands
```bash
# Run with verbose output
python scripts/test_system_startup.py --verbose

# Run specific test with debugging
pytest tests/test_system_startup.py::TestBasicStartup::test_config_manager_import -vv

# Check environment
python -c "import sys; print(sys.path)"
python -c "import app.config; print('Config OK')"
```

## Performance Thresholds

Default performance requirements:
- Startup time: < 10 seconds
- Memory usage: < 500 MB
- API response time: < 1000 ms
- WebSocket latency: < 500 ms

## CI/CD Integration

For CI/CD pipelines:
```yaml
# Example GitHub Actions workflow
- name: Run System Startup Tests
  run: |
    python scripts/test_system_startup.py --mode standard --force
```

## Development Workflow

1. Make changes to code
2. Run minimal tests: `python scripts/test_system_startup.py --mode minimal`
3. If passes, run standard tests
4. Before commit, run full test suite
5. Check test reports for any issues

## Extending Tests

To add new startup tests:
1. Update `SPEC/system_startup.xml` with new requirements
2. Add test methods to appropriate test file
3. Update test runner if needed
4. Document new tests in this README

## Contact

For issues or questions about system startup tests, refer to the main project documentation or create an issue in the repository.