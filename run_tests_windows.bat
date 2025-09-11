@echo off
REM Windows UTF-8 Test Runner for Netra Apex
REM This script ensures proper UTF-8 encoding before running tests

echo Setting UTF-8 environment...

REM Set UTF-8 environment variables
set PYTHONIOENCODING=utf-8:replace
set PYTHONUTF8=1
set PYTHONLEGACYWINDOWSIOENCODING=utf-8
set LC_ALL=en_US.UTF-8
set LANG=en_US.UTF-8
set CONSOLE_OUTPUT_ENCODING=utf-8

REM Set console code page to UTF-8
chcp 65001 >nul 2>&1

echo Environment configured for UTF-8
echo Running unified test runner...

REM Run the Python test runner with UTF-8 environment
python tests\unified_test_runner.py %*

echo Test execution completed.
