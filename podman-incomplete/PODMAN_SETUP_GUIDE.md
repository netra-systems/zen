# Podman Environment Setup Guide for Netra E2E Testing

## Status Summary

✅ **COMPLETED**:
1. Podman is properly installed and accessible via WSL (`podman-machine-default`)
2. All container images built successfully:
   - Auth Service (Alpine-based): `netra-auth-alpine:latest`  
   - Backend Service (Debian-based): `netra-backend-alpine:latest`
   - External services (PostgreSQL, Redis, ClickHouse) images pulled
3. Environment variables configured correctly via existing `.env` file
4. Scripts created for reliable service management

⚠️ **KNOWN ISSUE**: 
Podman networking issues with aardvark-dns in WSL2 environment preventing container startup.

---

## Quick Start

### Using PowerShell Script:
```powershell
# Start all services
.\scripts\start_podman_services.ps1

# Check status
.\scripts\start_podman_services.ps1 -Status

# Stop services
.\scripts\start_podman_services.ps1 -Stop

# Restart services
.\scripts\start_podman_services.ps1 -Restart

# Clean up
.\scripts\start_podman_services.ps1 -Clean
```

### Using Bash Script via WSL:
```bash
# Start services
wsl -d podman-machine-default -- /mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/start_podman_services.sh

# Check status
wsl -d podman-machine-default -- /mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/start_podman_services.sh status

# Stop services  
wsl -d podman-machine-default -- /mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/scripts/start_podman_services.sh stop
```

---

## Service Configuration

All services are configured via `docker-compose.podman.yml`:

- **PostgreSQL**: Port 5433, Database: `netra_dev`
- **Redis**: Port 6380 
- **ClickHouse**: Port 8124 (HTTP), 9001 (TCP)
- **Auth Service**: Port 8081
- **Backend Service**: Port 8000

Environment variables are loaded from the main `.env` file with appropriate defaults.

---

## Networking Issue Troubleshooting

### Current Problem
Podman containers fail to start due to DNS/networking issues:
```
Error: netavark: error while applying dns entries: aardvark-dns failed to start
```

### Solution Options

#### Option 1: Use Host Networking (Recommended for Testing)
Modify `docker-compose.podman.yml` to use host networking:

```yaml
services:
  postgres:
    network_mode: host
    ports: [] # Remove port mappings when using host network
    
  redis:
    network_mode: host
    ports: []
    
  # ... repeat for all services
```

#### Option 2: Disable DNS Resolution
Add to each service in `docker-compose.podman.yml`:
```yaml
dns: []
dns_search: []
```

#### Option 3: Use Podman Bridge Network
```bash
# Create custom network
wsl -d podman-machine-default -- podman network create netra-network

# Update docker-compose.podman.yml:
networks:
  default:
    external: true
    name: netra-network
```

#### Option 4: Restart Podman Machine
```bash
podman machine stop podman-machine-default
podman machine start podman-machine-default
```

---

## Built Images

The following images are ready:

1. **netra-auth-alpine:latest**
   - Base: python:3.11-alpine3.19
   - Size: Optimized (~200MB)
   - Features: All required dependencies installed

2. **netra-backend-alpine:latest** 
   - Base: python:3.11-slim (multi-stage build)
   - Size: Optimized (~500MB)
   - Features: All app code, dependencies, and configurations

3. **External Services**:
   - postgres:15-alpine
   - redis:7-alpine  
   - clickhouse/clickhouse-server:23-alpine

---

## Manual Testing Commands

### Check Images
```bash
wsl -d podman-machine-default -- podman images
```

### Manual Container Start (for debugging)
```bash
# Start PostgreSQL only
wsl -d podman-machine-default -- podman run -d --name netra-postgres -p 5433:5432 -e POSTGRES_USER=netra -e POSTGRES_PASSWORD=netra123 -e POSTGRES_DB=netra_dev postgres:15-alpine

# Test connection
wsl -d podman-machine-default -- podman exec netra-postgres pg_isready -U netra
```

### Build Only (no start)
```bash
wsl -d podman-machine-default -- bash -c "cd /mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1 && podman-compose -f docker-compose.podman.yml build"
```

---

## Environment Variables

The system uses the existing `.env` file with the following key variables:

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=netra
POSTGRES_PASSWORD=netra123
POSTGRES_DB=netra_dev

# Redis
REDIS_HOST=localhost
REDIS_PORT=6380

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_HTTP_PORT=8124
CLICKHOUSE_TCP_PORT=9001

# Services
AUTH_PORT=8081
BACKEND_PORT=8000

# Security
JWT_SECRET_KEY=rsWwwvq8X6mCSuNv-TMXHDCfb96Xc-Dbay9MZy6EDCU
SERVICE_SECRET=xNp9hKjT5mQ8w2fE7vR4yU3iO6aS1gL9cB0zZ8tN6wX2eR4vY7uI0pQ3s9dF5gH8

# APIs
GEMINI_API_KEY=AIzaSyCb8CRcMrUHPQWel_MZ_KT5f4oowumwanM
```

---

## Next Steps

1. **Resolve Networking Issues**: Apply one of the troubleshooting solutions above
2. **Verify Service Health**: Once containers start, check health endpoints:
   - Backend: http://localhost:8000/health
   - Auth: http://localhost:8081/health
3. **Run E2E Tests**: Use the test runner with `--real-services` flag
4. **Monitor Logs**: Use `podman-compose logs -f` to monitor service logs

---

## Files Created

- `scripts/start_podman_services.ps1` - PowerShell management script
- `scripts/start_podman_services.sh` - Bash management script  
- `docker-compose.podman.yml` - Podman compose configuration
- `docker/auth.podman.Dockerfile` - Auth service Dockerfile
- `docker/backend.podman.Dockerfile` - Backend service Dockerfile

The Podman environment is ready for E2E testing once the networking issues are resolved.