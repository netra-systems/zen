# Docker Services Selective Management Guide

## Overview

The Docker Compose configuration now supports **profiles** for selective service management. This allows you to start, stop, and manage specific services or groups of services independently.

## Quick Start

### Using the Helper Script

The easiest way to manage services is using the `docker_services.py` script:

```bash
# Start just the Netra backend (with its required dependencies)
python scripts/docker_services.py start netra

# Start just the frontend
python scripts/docker_services.py start frontend

# Start everything
python scripts/docker_services.py start full

# View logs for specific services
python scripts/docker_services.py logs netra

# Stop all services
python scripts/docker_services.py stop
```

## Available Profiles

| Profile | Services Included | Use Case |
|---------|------------------|----------|
| `netra` | PostgreSQL, Redis, Netra Backend | Development on Netra backend only |
| `backend` | PostgreSQL, Redis, Netra Backend, Auth Service | All backend development |
| `frontend` | Frontend only | Frontend development (requires backend running separately) |
| `full` | All services | Complete development environment |
| `db` | PostgreSQL only | Database management |
| `cache` | Redis only | Cache management |
| `analytics` | ClickHouse only | Analytics service |
| `auth` | PostgreSQL, Redis, Auth Service | Auth service development |

## Direct Docker Compose Commands

You can also use Docker Compose directly with profiles:

```bash
# Start just Netra backend services
docker compose -f docker-compose.dev.yml --profile netra up -d

# Start multiple profiles
docker compose -f docker-compose.dev.yml --profile netra --profile frontend up -d

# Stop specific services
docker compose -f docker-compose.dev.yml stop backend

# View logs for specific services
docker compose -f docker-compose.dev.yml logs -f backend redis
```

## Common Use Cases

### 1. Backend Development Only
When working on the Netra backend without needing the frontend:

```bash
python scripts/docker_services.py start netra
```

This starts:
- PostgreSQL database
- Redis cache
- Netra backend service

### 2. Frontend Development
When working on the frontend with an existing backend:

```bash
# First, ensure backend is running
python scripts/docker_services.py start backend

# Then start frontend
python scripts/docker_services.py start frontend
```

### 3. Database Management
To work with just the database:

```bash
python scripts/docker_services.py start db

# Access PostgreSQL
docker compose -f docker-compose.dev.yml exec postgres psql -U netra -d netra_db
```

### 4. Debugging Specific Services
To restart a specific service:

```bash
python scripts/docker_services.py restart netra
```

To view logs for debugging:

```bash
python scripts/docker_services.py logs netra --tail 100
```

### 5. Clean Shutdown
To stop all services and optionally remove volumes:

```bash
# Stop all services
python scripts/docker_services.py stop

# Stop and remove volumes (clean slate)
python scripts/docker_services.py stop --volumes
```

## Service Dependencies

The profiles automatically handle dependencies:

- `netra` profile includes PostgreSQL and Redis (required dependencies)
- `auth` profile includes PostgreSQL and Redis 
- `frontend` profile runs standalone but requires backend services to be functional

## Port Mappings

| Service | Port | URL |
|---------|------|-----|
| Netra Backend | 8000 | http://localhost:8000 |
| Auth Service | 8081 | http://localhost:8081 |
| Frontend | 3000 | http://localhost:3000 |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |
| ClickHouse | 8123 | http://localhost:8123 |

## Troubleshooting

### Check Service Status
```bash
python scripts/docker_services.py status
```

### View Container Logs
```bash
# All logs for a profile
python scripts/docker_services.py logs netra

# Specific service logs
docker compose -f docker-compose.dev.yml logs backend
```

### Access Container Shell
```bash
python scripts/docker_services.py exec backend bash
```

### Reset Everything
```bash
# Stop all services and remove volumes
docker compose -f docker-compose.dev.yml down -v

# Start fresh
python scripts/docker_services.py start full --build
```

## Environment Variables

The services respect environment variables from your `.env` file. Key variables:

- `BACKEND_PORT` - Netra backend port (default: 8000)
- `FRONTEND_PORT` - Frontend port (default: 3000)
- `AUTH_PORT` - Auth service port (default: 8081)
- `POSTGRES_PORT` - PostgreSQL port (default: 5432)
- `REDIS_PORT` - Redis port (default: 6379)

## Benefits of Selective Service Management

1. **Faster Startup**: Start only what you need
2. **Resource Efficiency**: Run fewer containers, use less memory
3. **Isolation**: Test services independently
4. **Flexibility**: Mix and match services as needed
5. **Development Speed**: Restart individual services without affecting others