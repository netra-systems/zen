# Windows Safe E2E Testing Guide

## Problem Summary
Running E2E tests on Windows can crash Docker Desktop due to resource exhaustion during pytest collection phase. This is caused by heavy module imports with side effects combined with Windows/WSL2 file descriptor limitations.

## Root Cause (Five Whys Analysis)
1. **Why did Docker crash?** → File descriptor exhaustion during pytest collection
2. **Why file descriptor exhaustion?** → Heavy imports with connection attempts at module level
3. **Why imports cause exhaustion?** → conftest.py chain performs environment checks and imports
4. **Why does this overwhelm Docker?** → Windows/WSL2 doubles file descriptors for each connection
5. **Why can't system handle it?** → pytest parallel collection + WSL2 bridge = connection storm

## Solutions Implemented

### 1. Lazy Initialization
- Modified `test_real_chat_output_validation.py` to use lazy imports
- Connections only established when fixtures are used, not at import time
- Environment checks moved from module level to fixture scope

### 2. Docker Health Checks
- Added `_check_docker_health()` method to verify services before testing
- Tests skip gracefully if Docker is not available
- Prevents connection attempts to non-existent services

### 3. Pytest Marks
- Added `@pytest.mark.requires_docker` to Docker-dependent tests
- Tests can be skipped with `SKIP_DOCKER_TESTS=true` environment variable
- Automatic skip on Windows when Docker is unavailable

### 4. Safe Runner Script
- Created `run_safe_windows.py` for safe E2E test execution
- Implements all safety measures automatically
- Performs collection check before running tests

## How to Run E2E Tests Safely on Windows

### Option 1: Use the Safe Runner (Recommended)
```bash
# Run all E2E tests safely
python tests/e2e/run_safe_windows.py

# Run specific test file
python tests/e2e/run_safe_windows.py test_real_chat_output_validation.py

# Skip Docker check (if you know it's running)
python tests/e2e/run_safe_windows.py --skip-docker-check
```

### Option 2: Manual Safety Measures
```bash
# Set environment variables
set PYTEST_XDIST_WORKER_COUNT=1
set SKIP_DOCKER_TESTS=false

# Run with safety flags
pytest tests/e2e/test_real_chat_output_validation.py -p no:xdist --maxfail=1 -x -v
```

### Option 3: Run Without Pytest Collection
```python
# Direct execution bypasses collection phase
python -c "import asyncio; from tests.e2e.test_real_chat_output_validation import test_simple_question_full_flow; asyncio.run(test_simple_question_full_flow())"
```

## Prevention Guidelines

1. **NEVER** initialize connections, clients, or resources at module import time
2. **ALWAYS** use lazy initialization within fixtures or test functions
3. **CHECK** Docker health before attempting connections
4. **USE** connection pooling and rate limiting on Windows
5. **AVOID** parallel test collection when testing with Docker on Windows

## Files Modified

- `tests/e2e/test_real_chat_output_validation.py` - Lazy initialization
- `tests/conftest.py` - Removed module-level environment checks
- `tests/e2e/run_safe_windows.py` - Safe runner script (new)
- `SPEC/learnings/docker_crash_pytest_collection_windows_20250107.xml` - Learning documentation
- `SPEC/learnings/index.xml` - Updated with new learning

## Testing the Fix

1. Ensure Docker Desktop is running
2. Start backend services: `python scripts/docker_manual.py start`
3. Run safe test: `python tests/e2e/run_safe_windows.py`
4. Verify no crash occurs

## Monitoring

Watch for these warning signs:
- `ValueError('I/O operation on closed file.')` 
- Docker Desktop service stopping unexpectedly
- Tests hanging during collection phase
- Excessive memory usage during pytest startup

If any occur, immediately stop testing and use the safe runner script.