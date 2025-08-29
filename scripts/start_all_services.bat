@echo off
REM Start all Netra infrastructure services (6 containers)
REM PostgreSQL, Redis, ClickHouse for both test and dev environments

echo ========================================
echo Starting Netra Infrastructure Services
echo ========================================
echo.

echo Stopping any existing containers...
docker-compose -f docker-compose.all.yml down 2>nul

echo.
echo Starting 6 infrastructure services:
echo   - Test: PostgreSQL (5432), Redis (6379), ClickHouse (8123)
echo   - Dev:  PostgreSQL (5433), Redis (6380), ClickHouse (8124)
echo.

docker-compose -f docker-compose.all.yml up -d

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] All infrastructure services started!
    echo.
    echo To check status:
    echo   python scripts\check_docker_services.py
    echo.
    echo To run application services locally:
    echo   Backend: cd netra_backend ^&^& uvicorn app.main:app --reload --port 8000
    echo   Auth:    cd auth_service ^&^& uvicorn main:app --reload --port 8081
    echo   Frontend: cd frontend ^&^& npm run dev
) else (
    echo.
    echo [ERROR] Failed to start services. Check Docker Desktop is running.
)

pause