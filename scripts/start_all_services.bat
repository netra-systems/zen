@echo off
REM Start all Netra services (12 containers total)
REM Test: PostgreSQL, Redis, ClickHouse, Backend, Auth, Frontend
REM Dev: PostgreSQL, Redis, ClickHouse, Backend, Auth, Frontend

echo ========================================
echo Starting All Netra Services (12 Total)
echo ========================================
echo.

echo Stopping any existing containers...
docker-compose -f docker-compose.all.yml down 2>nul

echo.
echo Starting 12 services (6 test + 6 dev):
echo   TEST Environment:
echo     - PostgreSQL (5432), Redis (6379), ClickHouse (8123)
echo     - Backend (8000), Auth (8081), Frontend (3000)
echo   DEV Environment:
echo     - PostgreSQL (5433), Redis (6380), ClickHouse (8124)  
echo     - Backend (8001), Auth (8082), Frontend (3001)
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