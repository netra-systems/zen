# Docker Configuration Index

## Overview

This document provides a comprehensive index of all Docker configurations in the Netra platform, clearly distinguishing between development and production (GCP) configurations.

## Configuration Structure

The system maintains **two distinct Docker configuration sets**:

### 1. Development Configuration (Local Docker Development)
**Purpose:** Local development with hot-reload, debugging tools, and full stack services  
**Location:** `/docker/` directory  
**Compose File:** `docker-compose.dev.yml`

### 2. Production/GCP Configuration (Cloud Deployment)
**Purpose:** Optimized production builds for Google Cloud Platform deployment  
**Location:** `/deployment/docker/` directory  
**Used By:** GCP deployment scripts

## Docker Files Mapping

### Backend Service

| Environment | File Path | Purpose |
|------------|-----------|---------|
| Development | `/docker/backend.development.Dockerfile` | Multi-stage dev build with hot-reload, includes dev tools |
| Production/GCP | `/deployment/docker/backend.gcp.Dockerfile` | Slim production build for Cloud Run |

**Key Differences:**
- **Development:** Includes reload capabilities, development dependencies, mounts source code
- **Production:** Minimal image size, no dev tools, copies code into image

### Auth Service

| Environment | File Path | Purpose |
|------------|-----------|---------|
| Development | `/docker/auth.development.Dockerfile` | Auth service for local development |
| Production/GCP | `/deployment/docker/auth.gcp.Dockerfile` | Production auth service for Cloud Run |

**Key Differences:**
- **Development:** JWT with dev secret key, hot-reload enabled
- **Production:** Production JWT configuration, optimized for Cloud Run

### Frontend Service

| Environment | File Path | Purpose |
|------------|-----------|---------|
| Development | `/docker/frontend.development.Dockerfile` | Next.js dev server with hot-reload |
| Production/GCP | `/deployment/docker/frontend.gcp.Dockerfile` | Production Next.js build |

**Key Differences:**
- **Development:** Runs Next.js dev server, source code mounted as volumes
- **Production:** Pre-built static assets, optimized for serving

## Compose Files

### docker-compose.dev.yml
**Purpose:** Orchestrates complete development environment with **profile support for selective service management**

**Services & Profiles:**
| Profile | Services Included | Use Case |
|---------|------------------|----------|
| `netra` | PostgreSQL, Redis, Backend | Netra backend development only |
| `backend` | PostgreSQL, Redis, Backend, Auth | Full backend development |
| `frontend` | Frontend | Frontend development only |
| `full` | All services | Complete stack |
| `db` | PostgreSQL | Database only |
| `cache` | Redis | Cache only |
| `analytics` | ClickHouse | Analytics only |
| `auth` | PostgreSQL, Redis, Auth | Auth service development |

**Features:**
- **Profile-based selective service control** (NEW)
- Health checks for all services
- Volume mounts for hot-reload
- Database initialization scripts
- Shared network (netra-network)
- Named volumes for data persistence

## Usage Guide

### Development Environment

#### Quick Service Management (NEW)
```bash
# Refresh/Restart Netra backend only
python scripts/docker_services.py restart netra

# Start just Netra backend (with dependencies)
python scripts/docker_services.py start netra

# Start just frontend
python scripts/docker_services.py start frontend

# Start everything
python scripts/docker_services.py start full

# View logs for Netra
python scripts/docker_services.py logs netra

# Stop all services
python scripts/docker_services.py stop
```

#### Traditional Docker Commands
```bash
# Using Docker Dev Launcher (Full stack)
python scripts/docker_dev_launcher.py

# Direct Docker Compose with profiles
docker compose -f docker-compose.dev.yml --profile netra up
docker compose -f docker-compose.dev.yml --profile full up

# With specific profiles (e.g., analytics)
docker compose -f docker-compose.dev.yml --profile analytics up
```

### Production/GCP Deployment

```bash
# Deploy to GCP Staging
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Build staging images locally
python scripts/build_staging.py
```

## File References

### Scripts Using Docker Configurations

| Script | Docker Files Used | Purpose |
|--------|-------------------|---------|
| `scripts/docker_services.py` | docker-compose.dev.yml | **Selective service management (NEW)** |
| `scripts/docker_dev_launcher.py` | docker-compose.dev.yml | Local development launcher |
| `scripts/deploy_to_gcp.py` | deployment/docker/*.gcp.Dockerfile | GCP deployment |
| `scripts/build_staging.py` | deployment/docker/*.gcp.Dockerfile | Staging builds |
| `scripts/fix_deployment_logging.py` | deployment/docker/*.gcp.Dockerfile | Deployment fixes |
| `scripts/validate_staging_deployment.py` | deployment/docker/*.gcp.Dockerfile | Deployment validation |

## Environment Variables

### Development (.env or docker-compose.dev.yml defaults)
- `POSTGRES_USER`: netra
- `POSTGRES_PASSWORD`: netra123
- `POSTGRES_DB`: netra_db
- `REDIS_PORT`: 6379
- `ENVIRONMENT`: development
- `JWT_SECRET_KEY`: dev-secret-key-change-in-production

### Production (Set in GCP Secret Manager)
- `DATABASE_URL`: Cloud SQL connection
- `REDIS_URL`: Redis instance URL
- `JWT_SECRET_KEY`: Secure production key
- `ENVIRONMENT`: staging/production

## Port Mappings

### Development Ports
- **PostgreSQL:** 5432
- **Redis:** 6379
- **ClickHouse HTTP:** 8123
- **ClickHouse TCP:** 9000
- **Backend API:** 8000
- **Auth Service:** 8081
- **Frontend:** 3000

### Production Ports
- Managed by Cloud Run (PORT environment variable)
- Default: 8080 for all services

## Best Practices

### When to Use Each Configuration

**Use Development Configuration When:**
- Working locally
- Debugging with hot-reload
- Testing with local databases
- Developing new features

**Use Production/GCP Configuration When:**
- Deploying to staging/production
- Building optimized images
- Testing production-like scenarios
- Running performance benchmarks

### Important Notes

1. **Never mix configurations** - Development and production configs are intentionally separate
2. **Image size matters** - Production images are optimized for size and security
3. **Security** - Production images run as non-root users, development may require root for certain tools
4. **Secrets** - Never commit production secrets; use environment variables or secret managers
5. **Dependencies** - Development includes build tools; production only runtime dependencies

## Troubleshooting

### Common Issues

**Development Docker Issues:**
```bash
# Reset everything
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml build --no-cache
docker compose -f docker-compose.dev.yml up
```

**Production Build Issues:**
```bash
# Validate Dockerfiles exist
ls deployment/docker/*.gcp.Dockerfile

# Check build context
python scripts/validate_staging_deployment.py
```

## Related Documentation

- [Docker Services Guide](./docker-services-guide.md) - **Complete guide for selective service management**
- [Docker Service Management Spec](../SPEC/docker_service_management.xml) - **Service profiles and patterns**
- [Docker Development Guide](./DOCKER_DEV_GUIDE.md)
- [GCP Deployment Spec](../SPEC/gcp_deployment.xml)
- [Deployment Architecture](../SPEC/deployment_architecture.xml)
- [Environment Management](../SPEC/unified_environment_management.xml)