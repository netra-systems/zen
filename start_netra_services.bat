@echo off
REM Windows batch wrapper for Netra services startup script
REM This script runs the bash script inside the podman WSL instance

setlocal

REM Set default command
set "COMMAND=%1"
if "%COMMAND%"=="" set "COMMAND=start"

REM Set default service for logs command
set "SERVICE=%2"

echo Starting Netra services using podman in WSL...
echo Command: %COMMAND%

REM Execute the bash script in podman WSL instance
wsl -d podman-machine-default -- bash -c "cd /mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1 && chmod +x start_netra_services.sh && ./start_netra_services.sh %COMMAND% %SERVICE%"

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Failed to execute command. Check the output above for details.
    echo.
    echo Available commands:
    echo   start     Start all services ^(default^)
    echo   stop      Stop all services
    echo   restart   Restart all services
    echo   status    Show service status
    echo   logs      Show logs for a service ^(requires service name^)
    echo   cleanup   Remove all containers and volumes
    echo   help      Show help
    echo.
    echo Examples:
    echo   %~nx0 start
    echo   %~nx0 status
    echo   %~nx0 logs auth
    echo   %~nx0 stop
    exit /b 1
)

endlocal