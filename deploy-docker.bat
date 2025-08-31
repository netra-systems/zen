@echo off
REM Netra Docker Deployment Script for Windows
REM Manages Docker deployment for development and test environments

setlocal enabledelayedexpansion

REM Default values
set PROFILE=dev
set ACTION=up
set BUILD=
set CLEAN=
set LOGS=

REM Colors (using ANSI escape codes - requires Windows 10+)
set RED=[31m
set GREEN=[32m
set YELLOW=[33m
set BLUE=[34m
set NC=[0m

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :main
if /i "%~1"=="-p" set PROFILE=%~2& shift & shift & goto :parse_args
if /i "%~1"=="--profile" set PROFILE=%~2& shift & shift & goto :parse_args
if /i "%~1"=="-a" set ACTION=%~2& shift & shift & goto :parse_args
if /i "%~1"=="--action" set ACTION=%~2& shift & shift & goto :parse_args
if /i "%~1"=="-b" set BUILD=--build& shift & goto :parse_args
if /i "%~1"=="--build" set BUILD=--build& shift & goto :parse_args
if /i "%~1"=="-c" set CLEAN=true& shift & goto :parse_args
if /i "%~1"=="--clean" set CLEAN=true& shift & goto :parse_args
if /i "%~1"=="-l" set LOGS=true& shift & goto :parse_args
if /i "%~1"=="--logs" set LOGS=true& shift & goto :parse_args
if /i "%~1"=="-h" goto :show_usage
if /i "%~1"=="--help" goto :show_usage
echo Unknown option: %~1
goto :show_usage

:show_usage
echo Usage: %0 [OPTIONS]
echo.
echo Options:
echo   -p, --profile PROFILE    Profile to use (dev^|test) [default: dev]
echo   -a, --action ACTION      Action to perform (up^|down^|restart^|status^|logs) [default: up]
echo   -b, --build             Force rebuild of images
echo   -c, --clean             Clean volumes and rebuild
echo   -l, --logs              Follow logs after starting
echo   -h, --help              Show this help message
echo.
echo Examples:
echo   %0                      # Start dev environment
echo   %0 -p test              # Start test environment
echo   %0 -a down              # Stop all services
echo   %0 -b -c                # Clean rebuild dev environment
echo   %0 -p dev -l            # Start dev and follow logs
exit /b 0

:main
echo %BLUE%🚀 Netra Docker Deployment Manager%NC%
echo %BLUE%==================================%NC%
echo.

REM Validate profile
if not "%PROFILE%"=="dev" if not "%PROFILE%"=="test" (
    echo %RED%Error: Invalid profile '%PROFILE%'. Must be 'dev' or 'test'%NC%
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo %RED%Error: Docker is not running. Please start Docker Desktop.%NC%
    exit /b 1
)

REM Check environment files
if "%PROFILE%"=="dev" (
    if not exist ".env.development" (
        echo %YELLOW%Warning: .env.development not found. Creating from .env...%NC%
        if exist ".env" (
            copy .env .env.development >nul 2>&1
        ) else (
            type nul > .env.development
        )
    )
)

REM Execute action
if /i "%ACTION%"=="up" goto :action_up
if /i "%ACTION%"=="down" goto :action_down
if /i "%ACTION%"=="restart" goto :action_restart
if /i "%ACTION%"=="status" goto :action_status
if /i "%ACTION%"=="logs" goto :action_logs
echo %RED%Error: Invalid action '%ACTION%'%NC%
goto :show_usage

:action_up
if "%CLEAN%"=="true" (
    echo %YELLOW%Cleaning Docker volumes for %PROFILE% environment...%NC%
    docker-compose --profile %PROFILE% down -v
    echo %GREEN%Volumes cleaned successfully%NC%
)

echo %BLUE%Starting %PROFILE% environment...%NC%
docker-compose --profile %PROFILE% up -d %BUILD%

echo %YELLOW%Waiting for services to become healthy...%NC%
timeout /t 5 /nobreak >nul

call :check_health

if "%LOGS%"=="true" (
    docker-compose --profile %PROFILE% logs -f
)
goto :end

:action_down
echo %YELLOW%Stopping %PROFILE% environment...%NC%
docker-compose --profile %PROFILE% down
echo %GREEN%Services stopped%NC%
goto :end

:action_restart
call :action_down
call :action_up
goto :end

:action_status
echo %BLUE%Service status for %PROFILE% environment:%NC%
echo.
docker-compose --profile %PROFILE% ps
echo.
call :check_health
goto :end

:action_logs
echo %BLUE%Showing logs for %PROFILE% environment...%NC%
docker-compose --profile %PROFILE% logs -f
goto :end

:check_health
echo %BLUE%Checking service health...%NC%
echo.

REM Check each service based on profile
if "%PROFILE%"=="dev" (
    call :check_service dev-postgres 5433
    call :check_service dev-redis 6380
    call :check_service dev-clickhouse 8124
    call :check_service dev-auth 8081
    call :check_service dev-analytics 8090
    call :check_service dev-backend 8000
    call :check_service dev-frontend 3000
) else (
    call :check_service test-postgres 5434
    call :check_service test-redis 6381
    call :check_service test-clickhouse 8123
    call :check_service test-auth 8082
    call :check_service test-analytics 8091
    call :check_service test-backend 8001
    call :check_service test-frontend 3001
)

echo.
echo %GREEN%✅ Service check complete!%NC%
call :print_urls
goto :eof

:check_service
set service=%1
set port=%2
docker ps --format "{{.Names}}" | findstr /i "netra-%PROFILE%-%service%" >nul 2>&1
if errorlevel 1 (
    echo %RED%✗ %service% is not running%NC%
) else (
    echo %GREEN%✓ %service% is running on port %port%%NC%
)
goto :eof

:print_urls
echo.
echo %BLUE%📌 Service URLs:%NC%
echo.
if "%PROFILE%"=="dev" (
    echo   Frontend:    http://localhost:3000
    echo   Backend API: http://localhost:8000
    echo   Auth API:    http://localhost:8081
    echo   Analytics:   http://localhost:8090
    echo   WebSocket:   ws://localhost:8000/ws
    echo.
    echo   PostgreSQL:  localhost:5433
    echo   Redis:       localhost:6380
    echo   ClickHouse:  http://localhost:8124
) else (
    echo   Frontend:    http://localhost:3001
    echo   Backend API: http://localhost:8001
    echo   Auth API:    http://localhost:8082
    echo   Analytics:   http://localhost:8091
    echo   WebSocket:   ws://localhost:8001/ws
    echo.
    echo   PostgreSQL:  localhost:5434
    echo   Redis:       localhost:6381
    echo   ClickHouse:  http://localhost:8123
)
goto :eof

:end
endlocal
exit /b 0