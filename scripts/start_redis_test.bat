@echo off
REM Start Redis for integration testing (port 6381)
REM For use with no-Docker integration tests

echo Starting Redis server for integration testing...
cd /d "%~dp0..\redis-local\Redis-8.2.1-Windows-x64-msys2"

if not exist "redis-server.exe" (
    echo ERROR: Redis not found. Please run the setup first.
    echo Download from: https://github.com/redis-windows/redis-windows/releases
    pause
    exit /b 1
)

echo Starting Redis on port 6381 for integration tests...
start /b redis-server.exe --port 6381

timeout /t 3 /nobreak >nul

echo Testing Redis connection...
redis-cli.exe -p 6381 ping
if %ERRORLEVEL% equ 0 (
    echo ✓ Redis server started successfully on port 6381
    echo ✓ Ready for integration tests without Docker
) else (
    echo ✗ Failed to start Redis server
    exit /b 1
)

echo.
echo Redis server is running in the background.
echo To stop Redis, close this window or use Ctrl+C
echo.
pause