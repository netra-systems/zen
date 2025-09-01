@echo off
REM Staging Test Runner for Windows
REM Sets environment variables before Python starts

echo Setting up staging environment...

REM Set core environment variables
set ENVIRONMENT=staging
set PYTHONPATH=%CD%
set E2E_OAUTH_SIMULATION_KEY=25006a4abd79f48e8e7a62c2b1b87245a449348ac0a01ac69a18521c7e140444

REM Load additional settings from .env.staging if exists
if exist .env.staging (
    echo Loading .env.staging file...
    for /f "tokens=1,2 delims==" %%a in (.env.staging) do (
        REM Skip comments and empty lines
        echo %%a | findstr /r "^#" >nul
        if errorlevel 1 (
            if not "%%a"=="" (
                set %%a=%%b
            )
        )
    )
)

REM Set critical staging URLs
set API_BASE_URL=https://api.staging.netrasystems.ai
set AUTH_SERVICE_URL=https://auth.staging.netrasystems.ai
set FRONTEND_URL=https://app.staging.netrasystems.ai
set WS_BASE_URL=wss://api.staging.netrasystems.ai/ws

REM Redis configuration for staging
set REDIS_REQUIRED=false
set REDIS_FALLBACK_ENABLED=true
set REDIS_PASSWORD=

REM UTF-8 encoding for Windows
set PYTHONIOENCODING=utf-8

echo.
echo Environment configured:
echo   ENVIRONMENT=%ENVIRONMENT%
echo   PYTHONPATH=%PYTHONPATH%
echo   E2E_OAUTH_SIMULATION_KEY=...configured
echo   API_BASE_URL=%API_BASE_URL%
echo.

REM Check if specific test path was provided
if "%1"=="" (
    echo Running all staging E2E tests...
    python -m pytest tests/e2e/test_staging_e2e_comprehensive.py -v --tb=short
) else (
    echo Running specific test: %*
    python -m pytest %* -v --tb=short
)

echo.
echo Test execution completed with exit code: %ERRORLEVEL%
exit /b %ERRORLEVEL%