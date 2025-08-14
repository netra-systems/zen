@echo off
REM Windows wrapper for pre-commit hook
REM Handles Python path resolution

REM Try conda python first (most reliable in this environment)
where conda >nul 2>nul
if %ERRORLEVEL% == 0 (
    conda run python "%~dp0pre-commit"
    exit /b %ERRORLEVEL%
)

REM Try python3 
where python3 >nul 2>nul
if %ERRORLEVEL% == 0 (
    python3 "%~dp0pre-commit"
    exit /b %ERRORLEVEL%
)

REM Try python
where python >nul 2>nul
if %ERRORLEVEL% == 0 (
    python "%~dp0pre-commit"
    exit /b %ERRORLEVEL%
)

REM Try py launcher
where py >nul 2>nul
if %ERRORLEVEL% == 0 (
    py "%~dp0pre-commit"
    exit /b %ERRORLEVEL%
)

echo [ERROR] Python not found in PATH
echo Please ensure Python is installed and accessible
exit /b 1