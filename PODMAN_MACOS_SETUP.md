# Podman Setup for macOS - Netra Apex

## ✅ Setup Complete

Podman has been successfully configured as a Docker Desktop replacement for the Netra Apex AI Optimization Platform on macOS.

## 🚀 Quick Start

### Start All Services
```bash
./scripts/podman_mac_services.sh start
```

### Check Service Status
```bash
./scripts/podman_mac_services.sh status
```

### Stop All Services
```bash
./scripts/podman_mac_services.sh stop
```

## 📋 Service Endpoints

| Service | Endpoint | Health Check |
|---------|----------|--------------|
| **Backend** | http://localhost:8480 | http://localhost:8480/health |
| **Auth Service** | http://localhost:8482 | http://localhost:8482/health |
| **PostgreSQL** | localhost:8090 | User: `netra`, Password: `netra123`, DB: `netra_dev` |
| **Redis** | localhost:8410 | `redis-cli -h localhost -p 8410 ping` |
| **ClickHouse** | localhost:8492 (HTTP), localhost:9492 (TCP) | http://localhost:8492 |

## 🛠️ Management Commands

The `./scripts/podman_mac_services.sh` script provides comprehensive service management:

```bash
# Service Management
./scripts/podman_mac_services.sh start      # Start all services
./scripts/podman_mac_services.sh stop       # Stop all services  
./scripts/podman_mac_services.sh restart    # Restart all services
./scripts/podman_mac_services.sh status     # Show status and health checks

# Maintenance
./scripts/podman_mac_services.sh build      # Build Docker images
./scripts/podman_mac_services.sh logs       # Show all service logs
./scripts/podman_mac_services.sh logs auth  # Show specific service logs
./scripts/podman_mac_services.sh clean      # Remove containers and volumes
./scripts/podman_mac_services.sh help       # Show help
```

## 🔧 Configuration Files

- **Main Compose File**: `docker-compose.podman-mac.yml` - macOS-optimized configuration with conflict-free ports
- **Original Compose File**: `docker-compose.podman.yml` - Original Windows/Linux configuration  
- **Docker Files**: 
  - `docker/auth.podman.Dockerfile` - Auth service image
  - `docker/backend.podman.Dockerfile` - Backend service image

## 📦 Built Images

The following images are ready and cached locally:

- **netra-auth-alpine:latest** - Auth service (471 MB)
- **netra-backend-alpine:latest** - Backend service (772 MB)

External images pulled:
- postgres:15-alpine
- redis:7-alpine  
- clickhouse/clickhouse-server:23-alpine

## 🏗️ Installation Details

### What Was Installed
1. **Podman 5.6.1** - Container runtime via Homebrew
2. **podman-compose 1.5.0** - Docker Compose compatibility via pip3
3. **Podman Machine** - Linux VM for container execution

### Port Mapping Changes
To avoid conflicts with Docker Desktop and other services:

| Service | Original Port | macOS Port | Reason |
|---------|---------------|------------|---------|
| PostgreSQL | 5433 | 8090 | Avoid conflicts |
| Redis | 6380 | 8410 | Avoid conflicts |
| ClickHouse HTTP | 8124 | 8492 | Avoid conflicts |
| ClickHouse TCP | 9001 | 9492 | Avoid conflicts |
| Auth Service | 8081 | 8482 | Docker Desktop conflict |
| Backend Service | 8000 | 8480 | Avoid conflicts |

## 🧪 Testing with Podman

To run tests with the Podman services:

```bash
# Update environment variables for new ports
export POSTGRES_PORT=8090
export REDIS_PORT=8410
export CLICKHOUSE_HTTP_PORT=8492
export AUTH_PORT=8482
export BACKEND_PORT=8480

# Run E2E tests
python tests/unified_test_runner.py --real-services --real-llm --category e2e
```

## 🔍 Troubleshooting

### Check Podman Machine Status
```bash
podman machine list
podman machine start  # If not running
```

### View Service Logs
```bash
podman logs netra-backend  # Individual container
podman-compose -f docker-compose.podman-mac.yml logs -f  # All services
```

### Restart Individual Services
```bash
podman restart netra-backend
podman restart netra-auth
```

### Port Conflicts
If you encounter port conflicts:
1. Check what's using the port: `lsof -i :8480`
2. Stop the conflicting service or change the port in `docker-compose.podman-mac.yml`

### Resource Issues
```bash
# Check resource usage
podman stats

# Clean up unused resources
podman system prune -f
```

## 📊 Performance Benefits

Compared to Docker Desktop:
- **Faster startup times** - No Docker Desktop overhead
- **Lower memory usage** - Podman is more lightweight
- **Better resource management** - Direct control over containers
- **No licensing restrictions** - Fully open source

## 🔄 Migration from Docker

If migrating from Docker Desktop:
1. Stop Docker Desktop
2. Use the Podman setup (already complete)
3. Update any scripts to use the new ports
4. All Docker Compose commands work with `podman-compose`

## ✅ Health Verification

All services are confirmed healthy and operational:

- ✅ Auth Service responding at http://localhost:8482/health
- ✅ Backend Service responding at http://localhost:8480/health  
- ✅ PostgreSQL accepting connections on port 8090
- ✅ Redis responding to PING on port 8410
- ✅ ClickHouse HTTP interface active on port 8492

## 🎯 Next Steps

The Podman setup is complete and ready for:
- Running E2E tests with `--real-services`
- Development and debugging
- Production-like testing environments
- CI/CD integration

Your Netra Apex development environment is now running efficiently on Podman! 🚀