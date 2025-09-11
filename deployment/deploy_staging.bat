@echo off
REM UTF-8 Safe Deployment Script for Windows
REM This bypasses Python subprocess encoding issues

echo Setting UTF-8 mode...
chcp 65001 >nul 2>&1

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONLEGACYWINDOWSSTDIO=0

echo.
echo ========================================
echo Deploying to GCP Staging
echo ========================================
echo.

if "%1"=="" (
    echo Deploying ALL services...
    
    echo.
    echo [1/2] Deploying Backend...
    python scripts\deploy_to_gcp.py --project netra-staging --build-local --alpine --service backend
    if errorlevel 1 (
        echo Backend deployment failed!
        exit /b 1
    )
    
    echo.
    echo [2/2] Deploying Frontend...
    python scripts\deploy_to_gcp.py --project netra-staging --build-local --alpine --service frontend
    if errorlevel 1 (
        echo Frontend deployment failed!
        exit /b 1
    )
    
    echo.
    echo ========================================
    echo SUCCESS: All services deployed!
    echo ========================================
) else (
    echo Deploying %1 service...
    python scripts\deploy_to_gcp.py --project netra-staging --build-local --alpine --service %1
)