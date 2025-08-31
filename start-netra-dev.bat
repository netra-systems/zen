@echo off
echo ======================================
echo Starting Netra Development Environment
echo ======================================
echo.

REM Check if Docker is running
docker version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker Desktop is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Cleaning up any existing containers...
docker-compose -f docker-compose.dev.yml down 2>nul

echo.
echo Starting all Netra services...
docker-compose -f docker-compose.dev.yml up -d

echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo Checking service status...
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo ======================================
echo Netra Dev Environment Status:
echo ======================================
echo.
echo Frontend:  http://localhost:3000
echo Backend:   http://localhost:8000
echo Auth:      http://localhost:8081
echo Analytics: http://localhost:8090
echo.
echo PostgreSQL: localhost:5433
echo Redis:      localhost:6380
echo ClickHouse: localhost:8124
echo.
echo ======================================
echo.
echo To view logs: docker-compose -f docker-compose.dev.yml logs -f [service-name]
echo To stop:      docker-compose -f docker-compose.dev.yml down
echo.
pause