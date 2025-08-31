@echo off
REM Docker Cleanup Batch Script for Windows
REM Wrapper for docker_cleanup.py with common presets

setlocal enabledelayedexpansion

echo ========================================
echo Docker Cleanup Utility for Windows
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

REM Check if Docker is running
docker version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not installed or not running
    echo Please start Docker Desktop and try again
    exit /b 1
)

REM Parse arguments
set MODE=normal
set DRY_RUN=
set FORCE=
set DAYS_OLD=30

:parse_args
if "%~1"=="" goto :run_cleanup
if /i "%~1"=="--safe" (
    set MODE=safe
    shift
    goto :parse_args
)
if /i "%~1"=="--aggressive" (
    set MODE=aggressive
    shift
    goto :parse_args
)
if /i "%~1"=="--dry-run" (
    set DRY_RUN=--dry-run
    shift
    goto :parse_args
)
if /i "%~1"=="--force" (
    set FORCE=--force
    shift
    goto :parse_args
)
if /i "%~1"=="--help" (
    goto :show_help
)
if /i "%~1"=="-h" (
    goto :show_help
)
if /i "%~1"=="/?" (
    goto :show_help
)
shift
goto :parse_args

:run_cleanup
echo Running cleanup in %MODE% mode...
if defined DRY_RUN echo [DRY RUN MODE - No changes will be made]
echo.

python "%~dp0docker_cleanup.py" --mode %MODE% %DRY_RUN% %FORCE% --days-old %DAYS_OLD%

if errorlevel 1 (
    echo.
    echo Cleanup failed with errors
    exit /b 1
)

echo.
echo Cleanup completed successfully
exit /b 0

:show_help
echo Usage: docker_cleanup.bat [options]
echo.
echo Options:
echo   --safe          Safe mode - only remove dangling resources
echo   --aggressive    Aggressive mode - remove all unused resources
echo   --dry-run       Show what would be removed without removing
echo   --force         Skip confirmation prompts
echo   --help, -h, /?  Show this help message
echo.
echo Examples:
echo   docker_cleanup.bat                    Run normal cleanup
echo   docker_cleanup.bat --safe             Run safe cleanup
echo   docker_cleanup.bat --aggressive       Run aggressive cleanup
echo   docker_cleanup.bat --dry-run          See what would be removed
echo   docker_cleanup.bat --aggressive --force   Force aggressive cleanup
echo.
exit /b 0