# Netra Services - Podman Direct Mode

This documentation covers running Netra services using direct podman commands with host networking to bypass DNS/networking issues in WSL environments.

## Overview

Due to DNS/networking issues with podman-compose in WSL, we've created scripts that start services using direct `podman run` commands with `--network=host` mode. This bypasses container networking issues and makes services directly accessible on localhost.

## Prerequisites

- Podman installed and accessible via WSL (`wsl -d podman-machine-default`)
- Pre-built images: `netra-backend-alpine:latest` and `netra-auth-alpine:latest`
- WSL 2 environment with Windows 10/11

## Quick Start

### Option 1: Windows Batch File (Recommended)
```cmd
# Start all services
start_netra_services.bat start

# Check status
start_netra_services.bat status

# Stop all services
start_netra_services.bat stop

# View logs for a specific service
start_netra_services.bat logs auth
```

### Option 2: Direct Bash Script
```bash
# In WSL podman environment
wsl -d podman-machine-default -- bash -c "cd /mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1 && bash start_netra_services.sh start"
```

## Service Configuration

### Default Ports
- **PostgreSQL**: `localhost:5433`
- **Redis**: `localhost:6380`
- **ClickHouse HTTP**: `localhost:8124`
- **ClickHouse TCP**: `localhost:9001`
- **Auth Service**: `localhost:8081`
- **Backend Service**: `localhost:8000`

### Environment Variables
You can customize ports and settings by setting environment variables before running:

```bash
# Custom ports example
export POSTGRES_PORT=5434
export REDIS_PORT=6381
export AUTH_PORT=8082
export BACKEND_PORT=8001

# Then start services
start_netra_services.bat start
```

### Key Environment Variables
- `POSTGRES_PORT` - PostgreSQL port (default: 5433)
- `REDIS_PORT` - Redis port (default: 6380)
- `CLICKHOUSE_HTTP_PORT` - ClickHouse HTTP port (default: 8124)
- `CLICKHOUSE_TCP_PORT` - ClickHouse TCP port (default: 9001)
- `AUTH_PORT` - Auth service port (default: 8081)
- `BACKEND_PORT` - Backend service port (default: 8000)
- `GEMINI_API_KEY` - Required for AI functionality

## Available Commands

### start_netra_services Script Commands

| Command | Description |
|---------|-------------|
| `start` | Start all Netra services (default) |
| `stop` | Stop all Netra services |
| `restart` | Restart all Netra services |
| `status` | Show status of all services |
| `logs [service]` | Show logs for a specific service |
| `cleanup` | Remove all containers and volumes |
| `help` | Show help message |

### Service Names for Logs
- `postgres` - PostgreSQL database
- `redis` - Redis cache
- `clickhouse` - ClickHouse analytics database
- `auth` - Authentication service
- `backend` - Main backend service

## Service Verification

Use the verification script to check service health:

```bash
# Run comprehensive health checks
wsl -d podman-machine-default -- bash -c "cd /mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1 && bash verify_services.sh"
```

This script checks:
- Container status
- Service connectivity
- Process health
- Resource usage
- Connection instructions

## Manual Service Testing

### Database Connections
```bash
# Connect to PostgreSQL
wsl -d podman-machine-default -- podman exec -it netra-postgres psql -U netra -d netra_dev

# Test Redis
wsl -d podman-machine-default -- podman exec -it netra-redis redis-cli -p 6380

# Query ClickHouse
wsl -d podman-machine-default -- podman exec -it netra-clickhouse clickhouse-client --port 9001
```

### Application Services
```bash
# Check Auth service logs
wsl -d podman-machine-default -- podman logs netra-auth

# Check Backend service logs
wsl -d podman-machine-default -- podman logs netra-backend
```

## Architecture Details

### Host Networking Mode
All containers run with `--network=host` which means:
- Services bind directly to localhost ports
- No container-to-container DNS resolution needed
- Direct access from host system
- Bypasses WSL networking complications

### Service Dependencies
Services start in dependency order:
1. PostgreSQL (database)
2. Redis (cache)
3. ClickHouse (analytics)
4. Auth Service (authentication)
5. Backend Service (main application)

### Data Persistence
Named volumes ensure data persists across container restarts:
- `netra_postgres_data` - PostgreSQL data
- `netra_redis_data` - Redis data
- `netra_clickhouse_data` - ClickHouse data
- `netra_auth_cache` - Auth service cache
- `netra_backend_cache` - Backend service cache

## Troubleshooting

### Common Issues

**1. Port Already in Use**
```bash
# Check what's using a port (from Windows)
netstat -ano | findstr :8000

# Kill process if needed
taskkill /PID <PID> /F
```

**2. Container Won't Start**
```bash
# Check container logs
wsl -d podman-machine-default -- podman logs netra-[service-name]

# Check container status
wsl -d podman-machine-default -- podman ps -a
```

**3. Service Health Check Warnings**
These are often due to WSL networking limitations. If containers are running and consuming CPU, they're likely working correctly despite health check warnings.

**4. Permission Issues**
```bash
# Fix script permissions
wsl -d podman-machine-default -- chmod +x start_netra_services.sh verify_services.sh
```

### WSL Networking Limitations

Due to WSL networking limitations:
- Port checks may fail even when services are working
- Health endpoints may not be accessible from outside containers
- Services still work correctly for inter-service communication

### Resource Usage

Monitor resource usage:
```bash
# Check container resource usage
wsl -d podman-machine-default -- podman stats --no-stream
```

## Advanced Configuration

### Custom Environment File
Create a `.env` file to set multiple environment variables:

```bash
# .env file
POSTGRES_PORT=5434
REDIS_PORT=6381
GEMINI_API_KEY=your-api-key-here
```

Then source it before starting:
```bash
# In WSL
source .env
bash start_netra_services.sh start
```

### Development Mode
For development, you might want to:
1. Mount additional volumes for live code updates
2. Enable debug logging
3. Use different database configurations

## Integration with Development Workflow

### With Tests
```bash
# Start services for testing
start_netra_services.bat start

# Run tests (from project root)
python tests/unified_test_runner.py --real-services

# Stop services when done
start_netra_services.bat stop
```

### With Frontend Development
The backend service running on `localhost:8000` can be accessed by frontend development servers running on Windows.

## Cleanup

### Full Cleanup
```bash
# Stop and remove everything
start_netra_services.bat cleanup
```

This removes all containers and volumes, giving you a fresh start.

### Selective Cleanup
```bash
# Just stop services (keeps data)
start_netra_services.bat stop

# Remove specific container
wsl -d podman-machine-default -- podman rm netra-backend
```

---

## Files Reference

- `start_netra_services.sh` - Main service management script (Bash)
- `start_netra_services.bat` - Windows wrapper for easy execution
- `verify_services.sh` - Comprehensive service verification script
- `PODMAN_SERVICES_README.md` - This documentation

## Support

If you encounter issues:
1. Check service logs: `start_netra_services.bat logs [service]`
2. Verify service status: `start_netra_services.bat status`
3. Run verification script: `bash verify_services.sh`
4. Check WSL and podman configuration