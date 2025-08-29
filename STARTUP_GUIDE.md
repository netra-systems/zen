# Netra Platform - Quick Startup Guide

## Quick Links
- 🚀 **[README.md](README.md#-quick-start)** - Quick start section in main README
- 🐳 **[docker-compose.all.yml](docker-compose.all.yml)** - Unified Docker configuration
- 📝 **[Docker Learnings](SPEC/learnings/docker_12_services_setup.xml)** - Technical details and learnings
- 🔧 **[Windows Script](scripts/start_all_services.bat)** | **[Linux/Mac Script](scripts/start_all_services.sh)** - Startup scripts

## Overview
The Netra platform infrastructure includes:
- **6 Infrastructure Services** (3 for Test: PostgreSQL, Redis, ClickHouse | 3 for Dev: PostgreSQL, Redis, ClickHouse)
- **Application Services** run locally during development (Backend, Auth, Frontend)

## Quick Start (All 12 Services)

### Windows
```bash
scripts\start_all_services.bat
```

### Linux/Mac
```bash
./scripts/start_all_services.sh
```

### Manual Docker Compose
```bash
docker-compose -f docker-compose.all.yml up -d
```

## Service Ports

### Test Environment (Primary)
| Service | Port | Container Name |
|---------|------|----------------|
| PostgreSQL | 5432 | netra-test-postgres |
| Redis | 6379 | netra-test-redis |
| ClickHouse | 8123 | netra-test-clickhouse |
| Backend | 8000 | netra-test-backend |
| Auth | 8081 | netra-test-auth |
| Frontend | 3000 | netra-test-frontend |

### Dev Environment (Secondary)
| Service | Port | Container Name |
|---------|------|----------------|
| PostgreSQL | 5433 | netra-dev-postgres |
| Redis | 6380 | netra-dev-redis |
| ClickHouse | 8124 | netra-dev-clickhouse |
| Backend | 8001 | netra-dev-backend |
| Auth | 8082 | netra-dev-auth |
| Frontend | 3001 | netra-dev-frontend |

## Environment Variables

### Default Credentials
```
# Test Environment
POSTGRES_USER=netra_test
POSTGRES_PASSWORD=netra_test
POSTGRES_DB=netra_test

# Dev Environment  
POSTGRES_USER=netra_dev
POSTGRES_PASSWORD=netra_dev
POSTGRES_DB=netra_dev

# ClickHouse (Both)
CLICKHOUSE_USER=netra
CLICKHOUSE_PASSWORD=netra123
CLICKHOUSE_DB=netra_analytics
```

## Verify Services

### Check All Services
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Check Service Health
```bash
# Test environment
docker inspect netra-test-postgres --format='{{.State.Health.Status}}'
docker inspect netra-test-redis --format='{{.State.Health.Status}}'
docker inspect netra-test-clickhouse --format='{{.State.Health.Status}}'

# Dev environment
docker inspect netra-dev-postgres --format='{{.State.Health.Status}}'
docker inspect netra-dev-redis --format='{{.State.Health.Status}}'
docker inspect netra-dev-clickhouse --format='{{.State.Health.Status}}'
```

## Access Points

### Test Environment
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Auth API: http://localhost:8081
- PostgreSQL: `postgresql://netra_test:netra_test@localhost:5432/netra_test`
- Redis: `redis://localhost:6379`
- ClickHouse: http://localhost:8123

### Dev Environment  
- Frontend: http://localhost:3001
- Backend API: http://localhost:8001
- Auth API: http://localhost:8082
- PostgreSQL: `postgresql://netra_dev:netra_dev@localhost:5433/netra_dev`
- Redis: `redis://localhost:6380`
- ClickHouse: http://localhost:8124

## Troubleshooting

### Services Not Starting
1. Ensure Docker Desktop is running
2. Check port conflicts: `netstat -an | findstr "5432 6379 8123"`
3. Clean up old containers: `docker-compose -f docker-compose.all.yml down`

### Database Connection Issues
1. Wait for health checks: Services need ~30 seconds to be fully ready
2. Check logs: `docker logs netra-test-postgres`
3. Verify credentials in environment files

### Port Conflicts
If ports are already in use, stop conflicting services or modify ports in `docker-compose.all.yml`

## Stop All Services
```bash
docker-compose -f docker-compose.all.yml down
```

## Clean Everything (Including Volumes)
```bash
docker-compose -f docker-compose.all.yml down -v
```

## Development Workflow

### Using Dev Launcher (Alternative)
```bash
python dev_launcher.py
```
Note: This uses the dev environment containers.

### Direct Service Access
All services can be accessed directly via their exposed ports without going through the application layer.

## Important Notes

1. **Container Names**: Always use the standard naming convention:
   - Test: `netra-test-[service]`
   - Dev: `netra-dev-[service]`
   - Never use `-2` suffix

2. **Health Checks**: All services include health checks. Wait for "healthy" status before accessing.

3. **Volumes**: Data persists in Docker volumes. Use `-v` flag with down command to clean data.

4. **Network**: All services share `netra-network` for inter-service communication.

## Quick Commands

```bash
# Start everything
docker-compose -f docker-compose.all.yml up -d

# Stop everything
docker-compose -f docker-compose.all.yml down

# View logs
docker-compose -f docker-compose.all.yml logs -f [service-name]

# Restart a service
docker-compose -f docker-compose.all.yml restart [service-name]

# Clean everything
docker-compose -f docker-compose.all.yml down -v
```