@echo off
REM Architecture Pre-commit Hooks Setup Script (Windows)
REM Sets up git hooks for enforcing CLAUDE.md architectural rules

setlocal enabledelayedexpansion

echo 🔧 Setting up architecture enforcement pre-commit hooks...

REM Get the script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\"
set "GITHOOKS_DIR=%PROJECT_ROOT%.githooks"

echo 📁 Project root: %PROJECT_ROOT%

REM Verify we're in a git repository
if not exist "%PROJECT_ROOT%.git" (
    echo ❌ Error: Not in a git repository
    exit /b 1
)

REM Verify .githooks directory exists
if not exist "%GITHOOKS_DIR%" (
    echo ❌ Error: .githooks directory not found
    echo    Expected at: %GITHOOKS_DIR%
    exit /b 1
)

REM Verify pre-commit hook exists
if not exist "%GITHOOKS_DIR%\pre-commit" (
    echo ❌ Error: pre-commit hook not found
    echo    Expected at: %GITHOOKS_DIR%\pre-commit
    exit /b 1
)

echo ✅ Found pre-commit hook

REM Configure git to use custom hooks directory
cd /d "%PROJECT_ROOT%"
git config core.hooksPath .githooks
if errorlevel 1 (
    echo ❌ Error: Failed to configure git hooks path
    exit /b 1
)
echo ✅ Configured git to use .githooks directory

REM Verify configuration
for /f "tokens=*" %%i in ('git config core.hooksPath') do set "HOOKS_PATH=%%i"
if not "%HOOKS_PATH%"==".githooks" (
    echo ❌ Error: Failed to configure hooks path
    echo    Expected: .githooks
    echo    Got: %HOOKS_PATH%
    exit /b 1
)

echo.
echo 🧪 Testing hook functionality...

REM Create a temporary test file that violates rules
set "TEST_FILE=test_hook_violation.py"
(
echo def test_function^(^):
echo     # This function intentionally violates the 25-line rule
echo     line1 = 1
echo     line2 = 2
echo     line3 = 3
echo     line4 = 4
echo     line5 = 5
echo     line6 = 6
echo     line7 = 7
echo     line8 = 8
echo     line9 = 9  # This line makes it 9 lines, violating the rule
echo     return line9
) > "%TEST_FILE%"

REM Add the test file to git staging
git add "%TEST_FILE%" 2>nul

REM Test the pre-commit hook (using python to run the hook)
echo 📋 Running pre-commit hook test...
python "%GITHOOKS_DIR%\pre-commit"
if errorlevel 1 (
    echo ✅ Hook correctly detected violations
    set "HOOK_TEST_RESULT=expected_fail"
) else (
    echo ⚠️  Warning: Hook should have failed but didn't
    set "HOOK_TEST_RESULT=unexpected_pass"
)

REM Clean up test file
git reset HEAD "%TEST_FILE%" 2>nul
del /f "%TEST_FILE%" 2>nul

echo.
echo ============================================================
echo 🎉 SETUP COMPLETE!
echo ============================================================
echo.
echo 📋 Architecture rules enforced:
echo    • Files must be ≤300 lines
echo    • Functions must be ≤8 lines
echo    • No test stubs in production code
echo.
echo 🔧 Hook configuration:
echo    • Hooks directory: .githooks
echo    • Pre-commit hook: ✅ Active
echo    • Hook test result: !HOOK_TEST_RESULT!
echo.
echo 💡 Usage:
echo    • Hooks run automatically on 'git commit'
echo    • Manual check: python scripts\check_architecture_compliance.py
echo    • Bypass (emergency): git commit --no-verify
echo.
echo ⚡ Performance: Hooks only check staged files for fast commits

if "!HOOK_TEST_RESULT!"=="unexpected_pass" (
    echo.
    echo ⚠️  Warning: Hook test had unexpected result. Manual verification recommended:
    echo    1. Create a file with ^>300 lines or ^>8 line functions
    echo    2. Stage it with 'git add'
    echo    3. Try 'git commit' - it should be blocked
    exit /b 1
)

echo.
echo ✅ All systems ready! Your commits are now architecture-protected.

endlocal