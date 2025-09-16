@echo off
REM Standardized test runner for staging E2E tests
REM Ensures proper PYTHONPATH and working directory

echo Starting Netra Staging E2E Tests...
echo Working Directory: %CD%
echo PYTHONPATH: %PYTHONPATH%

REM Change to project root
cd /d "C:\GitHub\netra-apex"

REM Set proper PYTHONPATH for test framework imports
set PYTHONPATH=C:\GitHub\netra-apex

REM Validate environment
echo [INFO] Validating test environment...
if not exist "tests\e2e\staging" (
    echo [ERROR] Staging test directory not found
    exit /b 1
)

if not exist "test_framework" (
    echo [ERROR] Test framework directory not found
    exit /b 1
)

echo [INFO] Environment validation complete
echo [INFO] Running staging E2E tests with pytest...

REM Run staging tests with standardized configuration
python -m pytest tests/e2e/staging/ %*

REM Capture exit code
set TEST_EXIT_CODE=%ERRORLEVEL%

echo [INFO] Test execution completed with exit code: %TEST_EXIT_CODE%

REM Return exit code for CI/CD integration
exit /b %TEST_EXIT_CODE%