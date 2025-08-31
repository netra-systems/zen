# Docker Development Environment Guide

## Overview

The Docker development environment provides a containerized, consistent development experience for the Netra platform. It ensures all developers work with the same environment configuration regardless of their host operating system.

## Prerequisites

- **Docker Desktop** (includes Docker Engine and Docker Compose)
  - [Windows/Mac](https://www.docker.com/products/docker-desktop)
  - [Linux](https://docs.docker.com/engine/install/)
- **8GB+ RAM** allocated to Docker
- **20GB+ free disk space**

## Quick Start

### 1. Basic Usage

```bash
# Start all services with defaults
python scripts/docker_dev_launcher.py

# Start with custom ports
python scripts/docker_dev_launcher.py --backend-port 8001 --frontend-port 3001

# Rebuild images and start
python scripts/docker_dev_launcher.py --build

# Start with verbose logging
python scripts/docker_dev_launcher.py --verbose
```

### 2. Alternative: Direct Docker Compose

```bash
# Start all services
docker compose -f docker-compose.dev.yml up

# Start in background
docker compose -f docker-compose.dev.yml up -d

# View logs
docker compose -f docker-compose.dev.yml logs -f

# Stop services
docker compose -f docker-compose.dev.yml down
```

## Architecture

### Services

1. **Backend** (port 8000)
   - Main Netra backend API
   - FastAPI application with hot reload
   - Connected to PostgreSQL, Redis, and ClickHouse

2. **Auth Service** (port 8081)
   - Authentication and authorization service
   - JWT token management
   - User session handling

3. **Frontend** (port 3000)
   - Next.js application with Turbopack
   - Hot module replacement enabled
   - Connected to backend and auth services

4. **PostgreSQL** (port 5432)
   - Primary database
   - Persistent volume for data
   - Auto-initialized with schema

5. **Redis** (port 6379)
   - Cache and session storage
   - Pub/sub for real-time features
   - Persistent volume for data

6. **ClickHouse** (port 8123, optional)
   - Analytics database
   - Time-series data storage
   - Enable with `--enable-clickhouse` flag

### Network

All services communicate through the `netra-network` Docker bridge network. Services can reference each other by name (e.g., `backend`, `postgres`, `redis`).

### Volumes

Persistent volumes ensure data survives container restarts:

- `netra-postgres-data` - PostgreSQL data
- `netra-redis-data` - Redis persistence
- `netra-clickhouse-data` - ClickHouse data

Source code is mounted as read-only volumes with hot reload support.

## Environment Configuration

### Default Environment Variables

The Docker environment uses sensible defaults suitable for development:

```env
# Database
POSTGRES_USER=netra
POSTGRES_PASSWORD=netra123
POSTGRES_DB=netra_db

# Services
BACKEND_PORT=8000
FRONTEND_PORT=3000
AUTH_PORT=8081

# Redis
REDIS_PORT=6379

# Environment
ENVIRONMENT=development
```

### Custom Configuration

Create a `.env` file in the project root to override defaults:

```env
# API Keys
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
NETRA_API_KEY=your-key-here

# Custom Ports
BACKEND_PORT=8001
FRONTEND_PORT=3001
```

## Development Workflow

### Hot Reload

All services support hot reload:

- **Backend**: Changes to Python files trigger automatic reload
- **Frontend**: Next.js fast refresh updates components instantly
- **Auth Service**: Python files trigger reload

### Database Migrations

Migrations run automatically on startup. To run manually:

```bash
# Run migrations
docker compose -f docker-compose.dev.yml exec backend \
  alembic -c netra_backend/alembic.ini upgrade head

# Create new migration
docker compose -f docker-compose.dev.yml exec backend \
  alembic -c netra_backend/alembic.ini revision --autogenerate -m "description"
```

### Debugging

#### View Logs

```bash
# All services
docker compose -f docker-compose.dev.yml logs -f

# Specific service
docker compose -f docker-compose.dev.yml logs -f backend

# Last 100 lines
docker compose -f docker-compose.dev.yml logs --tail 100 backend
```

#### Access Container Shell

```bash
# Backend shell
docker compose -f docker-compose.dev.yml exec backend sh

# Database shell
docker compose -f docker-compose.dev.yml exec postgres psql -U netra -d netra_db

# Redis CLI
docker compose -f docker-compose.dev.yml exec redis redis-cli
```

#### Port Debugging

```bash
# Check if ports are in use
netstat -an | grep -E ":(8000|3000|8081|5432|6379)"

# On Windows
netstat -an | findstr /R ":[8000|3000|8081|5432|6379]"
```

## Common Tasks

### Restart a Service

```bash
docker compose -f docker-compose.dev.yml restart backend
```

### Rebuild Images

```bash
# Rebuild all
docker compose -f docker-compose.dev.yml build

# Rebuild specific service
docker compose -f docker-compose.dev.yml build backend

# Rebuild without cache
docker compose -f docker-compose.dev.yml build --no-cache backend
```

### Clean Up

```bash
# Stop services (keep data)
docker compose -f docker-compose.dev.yml down

# Stop and remove volumes (DELETES DATA)
docker compose -f docker-compose.dev.yml down -v

# Remove all Netra containers and volumes
python scripts/docker_dev_launcher.py --cleanup --clean-volumes

# Prune unused Docker resources
docker system prune -f
```

### Database Operations

```bash
# Backup database
docker compose -f docker-compose.dev.yml exec postgres \
  pg_dump -U netra netra_db > backup.sql

# Restore database
docker compose -f docker-compose.dev.yml exec -T postgres \
  psql -U netra netra_db < backup.sql

# Reset database (DELETES DATA)
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up postgres -d
```

## Troubleshooting

### Services Won't Start

1. **Port conflicts**: Check if ports are already in use
   ```bash
   lsof -i :8000,:3000,:8081,:5432,:6379  # Unix/Mac
   netstat -an | findstr "8000 3000 8081"  # Windows
   ```

2. **Docker not running**: Ensure Docker Desktop is running
   ```bash
   docker version
   docker compose version
   ```

3. **Insufficient resources**: Increase Docker memory allocation in Docker Desktop settings

### Slow Performance

1. **Windows/Mac**: File sync can be slow. Minimize mounted volumes or use WSL2 (Windows)
2. **Memory**: Allocate at least 4GB RAM to Docker
3. **CPU**: Allocate at least 2 CPUs to Docker

### Database Connection Issues

1. **Wait for initialization**: Database takes 10-30 seconds to initialize on first run
2. **Check health**: `docker compose -f docker-compose.dev.yml ps` shows health status
3. **Reset if corrupted**: `docker compose -f docker-compose.dev.yml down -v` and restart

### Frontend Can't Connect to Backend

1. **Check CORS settings**: Backend should allow `http://localhost:3000`
2. **Verify network**: All services should be on `netra-network`
3. **Check environment variables**: Frontend needs correct `NEXT_PUBLIC_API_URL`

## Advanced Configuration

### Custom Dockerfile Modifications

To add system packages or modify the build:

1. Edit the appropriate Dockerfile in `docker/`
2. Rebuild: `docker compose -f docker-compose.dev.yml build --no-cache [service]`

### Production-like Environment

For testing closer to production:

1. Set `NODE_ENV=production` and `ENVIRONMENT=production`
2. Build frontend: `docker compose -f docker-compose.dev.yml exec frontend npm run build`
3. Use production commands instead of dev commands

### Multi-Environment Setup

**IMPORTANT: Docker Compose is for LOCAL development only. Staging refers to GCP Cloud Run deployment.**

Use with: `docker compose --profile dev up` or `docker compose --profile test up`

For actual staging environment testing, use:
```bash
# Test against deployed GCP staging services
ENVIRONMENT=staging python tests/run_staging_tests.py
```

## Comparison: Docker vs Native Dev Launcher

| Feature | Docker Dev | Native Dev |
|---------|------------|------------|
| Setup Complexity | Simple (Docker only) | Complex (multiple tools) |
| Consistency | High (identical environments) | Variable (OS differences) |
| Performance | Good (some overhead) | Best (native execution) |
| Resource Usage | Higher (containers) | Lower (native processes) |
| Isolation | Complete | Partial |
| Hot Reload | Supported | Supported |
| Database Setup | Automatic | Manual |
| Clean Up | Simple (remove containers) | Manual |

## Best Practices

1. **Don't commit .env files** - Use `.env.template` as reference
2. **Regular cleanup** - Run `docker system prune` weekly
3. **Monitor resources** - Check Docker Desktop dashboard
4. **Use volumes wisely** - Mount only necessary directories
5. **Keep images updated** - Rebuild periodically for security updates

## Support

For issues:
1. Check logs: `docker compose -f docker-compose.dev.yml logs`
2. Verify Docker status: `docker version`
3. Review this guide's troubleshooting section
4. Check project issues on GitHub