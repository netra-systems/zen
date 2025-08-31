@echo off
echo ======================================
echo Validating Netra Development Environment
echo ======================================
echo.

REM Check Docker
docker version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Docker Desktop is not running
    set DOCKER_OK=0
) else (
    echo [OK] Docker Desktop is running
    set DOCKER_OK=1
)

if %DOCKER_OK%==0 (
    echo.
    echo Please start Docker Desktop first!
    pause
    exit /b 1
)

echo.
echo Checking containers...
echo ----------------------------------------

REM Check each service
for %%s in (postgres redis clickhouse auth analytics backend frontend) do (
    docker ps | findstr netra-%%s >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo [OK] netra-%%s is running
    ) else (
        echo [FAIL] netra-%%s is not running
    )
)

echo.
echo Testing service connectivity...
echo ----------------------------------------

REM Test PostgreSQL
docker exec netra-postgres psql -U netra -d netra_dev -c "SELECT 1" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] PostgreSQL is accessible
) else (
    echo [FAIL] PostgreSQL connection failed
)

REM Test Redis
docker exec netra-redis redis-cli ping >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Redis is accessible
) else (
    echo [FAIL] Redis connection failed
)

REM Test ClickHouse
docker exec netra-clickhouse clickhouse-client --query "SELECT 1" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] ClickHouse is accessible
) else (
    echo [FAIL] ClickHouse connection failed
)

echo.
echo Testing HTTP endpoints...
echo ----------------------------------------

REM Test Auth Service
curl -s -o nul -w "%%{http_code}" http://localhost:8081/health | findstr 200 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Auth service health check passed
) else (
    echo [FAIL] Auth service not responding
)

REM Test Backend
curl -s -o nul -w "%%{http_code}" http://localhost:8000/health | findstr 200 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Backend health check passed
) else (
    echo [FAIL] Backend not responding
)

REM Test Frontend
curl -s -o nul -w "%%{http_code}" http://localhost:3000 | findstr /r "200 304" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Frontend is accessible
) else (
    echo [FAIL] Frontend not responding
)

REM Test Analytics
curl -s -o nul -w "%%{http_code}" http://localhost:8090/health | findstr 200 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Analytics service health check passed
) else (
    echo [WARN] Analytics service not responding (may still be starting)
)

echo.
echo ======================================
echo Validation Complete
echo ======================================
echo.
pause