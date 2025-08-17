@echo off
REM Local staging deployment for Windows

echo Starting local staging deployment...

REM Set environment for local build
set LOCAL_BUILD=true
set DOCKER_BUILDKIT=1
set COMPOSE_DOCKER_CLI_BUILD=1

REM Build images with caching
echo Building images with Docker Compose...
docker-compose -f docker-compose.staging.yml build --build-arg BUILDKIT_INLINE_CACHE=1 --parallel

REM Start services
echo Starting services...
docker-compose -f docker-compose.staging.yml up -d

REM Wait for services
echo Waiting for services to be healthy...
timeout /t 10 /nobreak > nul

REM Check health status
docker-compose -f docker-compose.staging.yml ps

echo.
echo Local staging environment ready!
echo    Frontend: http://localhost:3000
echo    Backend: http://localhost:8080
echo.
echo Useful commands:
echo    View logs: docker-compose -f docker-compose.staging.yml logs -f
echo    Stop: docker-compose -f docker-compose.staging.yml down
echo    Restart: docker-compose -f docker-compose.staging.yml restart