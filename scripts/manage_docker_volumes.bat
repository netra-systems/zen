@echo off
REM Docker Volume Management Script for Windows
REM This script helps manage Docker volumes for the Netra platform

setlocal enabledelayedexpansion

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not running. Please start Docker Desktop.
    exit /b 1
)

:menu
cls
echo.
echo === Docker Volume Management for Netra ===
echo.
echo 1. List all Netra volumes
echo 2. Show volume sizes
echo 3. Initialize code volumes (first time setup)
echo 4. Sync code TO volumes (host -^> volume)
echo 5. Sync code FROM volumes (volume -^> host)
echo 6. Backup a volume
echo 7. Restore a volume
echo 8. Clean unused volumes
echo 9. Reset all volumes (DANGEROUS)
echo 0. Exit
echo.
set /p choice="Select an option: "

if "%choice%"=="1" goto list_volumes
if "%choice%"=="2" goto show_sizes
if "%choice%"=="3" goto init_volumes
if "%choice%"=="4" goto sync_to_volumes
if "%choice%"=="5" goto sync_from_volumes
if "%choice%"=="6" goto backup_volume
if "%choice%"=="7" goto restore_volume
if "%choice%"=="8" goto clean_volumes
if "%choice%"=="9" goto reset_volumes
if "%choice%"=="0" exit /b 0
goto menu

:list_volumes
echo.
echo === Netra Docker Volumes ===
docker volume ls | findstr netra
if %errorlevel% neq 0 (
    echo No Netra volumes found
)
pause
goto menu

:show_sizes
echo.
echo === Volume Sizes ===
for /f "tokens=*" %%v in ('docker volume ls -q ^| findstr netra') do (
    for /f "tokens=1" %%s in ('docker run --rm -v %%v:/data alpine du -sh /data 2^>nul') do (
        echo %%v: %%s
    )
)
pause
goto menu

:init_volumes
echo.
echo === Initializing Code Volumes ===
echo Copying code to named volumes...

REM Backend services
docker run --rm -v %cd%:/source -v netra-dev-backend-code:/target alpine sh -c "cp -r /source/netra_backend/* /target/ 2>/dev/null || true"
docker run --rm -v %cd%:/source -v netra-dev-auth-code:/target alpine sh -c "cp -r /source/auth_service/* /target/ 2>/dev/null || true"
docker run --rm -v %cd%:/source -v netra-dev-analytics-code:/target alpine sh -c "cp -r /source/analytics_service/* /target/ 2>/dev/null || true"
docker run --rm -v %cd%:/source -v netra-dev-shared-code:/target alpine sh -c "cp -r /source/shared/* /target/ 2>/dev/null || true"
docker run --rm -v %cd%:/source -v netra-dev-spec-data:/target alpine sh -c "cp -r /source/SPEC/* /target/ 2>/dev/null || true"
docker run --rm -v %cd%:/source -v netra-dev-scripts:/target alpine sh -c "cp -r /source/scripts/* /target/ 2>/dev/null || true"

REM Frontend
docker run --rm -v %cd%/frontend:/source -v netra-dev-frontend-code:/target alpine sh -c "cp -r /source/* /target/ 2>/dev/null || true"

echo Code volumes initialized
pause
goto menu

:sync_to_volumes
echo.
echo Syncing code from host to volumes...
call :init_volumes
echo Sync completed
pause
goto menu

:sync_from_volumes
echo.
echo Syncing code from volumes to host...

REM Create backup first
set backup_dir=volume_sync_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set backup_dir=%backup_dir: =0%
mkdir "%backup_dir%" 2>nul
xcopy /E /I /Q netra_backend "%backup_dir%\netra_backend" >nul 2>&1
xcopy /E /I /Q auth_service "%backup_dir%\auth_service" >nul 2>&1
xcopy /E /I /Q analytics_service "%backup_dir%\analytics_service" >nul 2>&1
xcopy /E /I /Q shared "%backup_dir%\shared" >nul 2>&1

REM Sync from volumes
docker run --rm -v netra-dev-backend-code:/source -v %cd%:/target alpine sh -c "cp -r /source/* /target/netra_backend/ 2>/dev/null || true"
docker run --rm -v netra-dev-auth-code:/source -v %cd%:/target alpine sh -c "cp -r /source/* /target/auth_service/ 2>/dev/null || true"
docker run --rm -v netra-dev-analytics-code:/source -v %cd%:/target alpine sh -c "cp -r /source/* /target/analytics_service/ 2>/dev/null || true"
docker run --rm -v netra-dev-shared-code:/source -v %cd%:/target alpine sh -c "cp -r /source/* /target/shared/ 2>/dev/null || true"

echo Sync completed. Backup saved to: %backup_dir%
pause
goto menu

:backup_volume
echo.
set /p volume="Enter volume name: "
set timestamp=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set timestamp=%timestamp: =0%
set backup_file=backups\%volume%_%timestamp%.tar.gz

if not exist backups mkdir backups

echo Backing up %volume% to %backup_file%...
docker run --rm -v %volume%:/source -v %cd%\backups:/backup alpine tar -czf /backup/%volume%_%timestamp%.tar.gz -C /source .
echo Backup completed: %backup_file%
pause
goto menu

:restore_volume
echo.
set /p volume="Enter volume name: "
set /p backup_file="Enter backup file path: "

if not exist "%backup_file%" (
    echo Error: Backup file not found: %backup_file%
    pause
    goto menu
)

echo Restoring %volume% from %backup_file%...
for %%F in ("%backup_file%") do set filename=%%~nxF
for %%F in ("%backup_file%") do set dirname=%%~dpF
docker run --rm -v %volume%:/target -v %dirname%:/backup alpine tar -xzf /backup/%filename% -C /target
echo Restore completed
pause
goto menu

:clean_volumes
echo.
echo Cleaning unused volumes...
docker volume prune -f
echo Cleanup completed
pause
goto menu

:reset_volumes
echo.
echo WARNING: This will delete all Netra Docker volumes and their data!
set /p confirm="Are you sure? (yes/no): "

if /i not "%confirm%"=="yes" (
    echo Operation cancelled
    pause
    goto menu
)

echo Stopping all Netra containers...
docker-compose down

echo Removing all Netra volumes...
for /f "tokens=*" %%v in ('docker volume ls -q ^| findstr netra') do (
    docker volume rm %%v >nul 2>&1
)

echo All Netra volumes have been reset
pause
goto menu