@echo off
REM DEPRECATION WARNING: This Docker deployment script is deprecated.
REM
REM WEEK 1 SSOT REMEDIATION (GitHub Issue #245): 
REM This script is deprecated in favor of canonical Docker Compose usage.
REM
REM CANONICAL SOURCES:
REM   - Development: docker-compose --profile dev up
REM   - Testing: docker-compose --profile test up  
REM   - Staging GCP: python scripts/deploy_to_gcp_actual.py --project netra-staging
REM
REM Migration Paths:
REM   OLD: scripts\deploy-docker.bat -p dev -a up
REM   NEW: docker-compose --profile dev up
REM
REM   OLD: scripts\deploy-docker.bat -p test -a up --build
REM   NEW: docker-compose --profile test up --build
REM
REM This wrapper will be removed in Week 2 after validation of the transition.

setlocal enabledelayedexpansion

REM Default values
set PROFILE=dev
set ACTION=up
set BUILD=
set EXTRA_ARGS=

REM Colors (using ANSI escape codes - requires Windows 10+)
set RED=[31m
set GREEN=[32m
set YELLOW=[33m
set BLUE=[34m
set NC=[0m

REM Show deprecation warning
echo %YELLOW%================================================================================%NC%
echo %RED%🚨 DEPRECATION WARNING - WEEK 1 SSOT REMEDIATION%NC%
echo %YELLOW%================================================================================%NC%
echo %YELLOW%GitHub Issue #245: Deployment canonical source conflicts%NC%
echo.
echo %YELLOW%This Docker deployment script is deprecated.%NC%
echo.
echo %GREEN%For local Docker development:%NC%
echo %BLUE%  CANONICAL: docker-compose --profile dev up%NC%
echo.
echo %GREEN%For local Docker testing:%NC%
echo %BLUE%  CANONICAL: docker-compose --profile test up%NC%
echo.
echo %GREEN%For GCP staging deployment:%NC%
echo %BLUE%  CANONICAL: python scripts/deploy_to_gcp_actual.py --project netra-staging%NC%
echo.
echo %YELLOW%================================================================================%NC%
echo.

REM Parse command line arguments to maintain compatibility
:parse_args
if "%~1"=="" goto :redirect
if /i "%~1"=="-p" set PROFILE=%~2& shift & shift & goto :parse_args
if /i "%~1"=="--profile" set PROFILE=%~2& shift & shift & goto :parse_args
if /i "%~1"=="-a" set ACTION=%~2& shift & shift & goto :parse_args
if /i "%~1"=="--action" set ACTION=%~2& shift & shift & goto :parse_args
if /i "%~1"=="-b" set BUILD=--build& shift & goto :parse_args
if /i "%~1"=="--build" set BUILD=--build& shift & goto :parse_args
if /i "%~1"=="-d" set EXTRA_ARGS=%EXTRA_ARGS% -d& shift & goto :parse_args
if /i "%~1"=="--detach" set EXTRA_ARGS=%EXTRA_ARGS% -d& shift & goto :parse_args
set EXTRA_ARGS=%EXTRA_ARGS% %~1& shift & goto :parse_args

:redirect
echo %YELLOW%💡 HINT: For GCP staging deployment:%NC%
echo %BLUE%   python scripts/deploy_to_gcp_actual.py --project netra-staging --build-local%NC%
echo.

REM Build the canonical docker-compose command
if "%ACTION%"=="up" (
    set CMD=docker-compose --profile %PROFILE% up %BUILD% %EXTRA_ARGS%
) else if "%ACTION%"=="down" (
    set CMD=docker-compose down -v
) else if "%ACTION%"=="build" (
    set CMD=docker-compose --profile %PROFILE% build
) else if "%ACTION%"=="logs" (
    set CMD=docker-compose logs --tail=50
) else (
    set CMD=docker-compose --profile %PROFILE% %ACTION% %EXTRA_ARGS%
)

echo %BLUE%🔄 Redirecting to Docker Compose:%NC%
echo %GREEN%   !CMD!%NC%
echo.

REM Execute the canonical command
call !CMD!
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE%==0 if "%ACTION%"=="up" (
    echo.
    echo %GREEN%✅ Services started successfully!%NC%
    echo %BLUE%   Frontend: http://localhost:3000%NC%
    echo %BLUE%   Backend API: http://localhost:8080%NC%
    echo %BLUE%   API Docs: http://localhost:8080/docs%NC%
)

exit /b %EXIT_CODE%