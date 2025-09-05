@echo off
REM Start Backend in Resource-Aware Mode (Windows)
REM This script starts the backend with minimal resource usage

echo Starting Netra Backend in resource-aware mode...

REM Set environment variables for local development
set ENVIRONMENT=development
set BUILD_ENV=development
set LOG_LEVEL=INFO
set WORKERS=1
set PORT=8000

REM Database configuration (using lightweight SQLite for local dev)
set USE_SQLITE=true
set DATABASE_URL=sqlite:///./netra_local.db

REM Disable heavy features for resource efficiency
set ENABLE_MONITORING=false
set ENABLE_TRACING=false
set ENABLE_METRICS=false

REM Start uvicorn with resource-aware settings
echo Starting backend server on http://localhost:%PORT%
python -m uvicorn netra_backend.app.main:app ^
    --host 0.0.0.0 ^
    --port %PORT% ^
    --workers %WORKERS% ^
    --limit-concurrency 10 ^
    --limit-max-requests 1000 ^
    --log-level %LOG_LEVEL%