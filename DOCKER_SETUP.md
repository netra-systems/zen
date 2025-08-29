# Docker Setup Guide for Netra Platform

## Overview
Complete Docker configuration for the Netra AI Optimization Platform with development, production, and monitoring setups.

## Quick Start

### Development Environment
```bash
# Copy environment file
cp .env.example .env
# Edit .env with your API keys and settings

# Start all services with hot reload
docker-compose -f docker-compose.dev.yml up

# Start specific profiles
docker-compose -f docker-compose.dev.yml --profile backend up  # Backend + DB + Redis
docker-compose -f docker-compose.dev.yml --profile frontend up # Frontend only
docker-compose -f docker-compose.dev.yml --profile full up    # Everything
```

### Production Environment
```bash
# Build and start production services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With monitoring
docker-compose -f docker-compose.yml -f docker-compose.prod.yml --profile monitoring up -d

# Scale services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale backend=3 --scale frontend=2
```

## File Structure
```
.
├── docker-compose.yml          # Base production configuration
├── docker-compose.dev.yml      # Development configuration with hot reload
├── docker-compose.override.yml # Auto-loaded dev overrides (Mac/Windows optimizations)
├── docker-compose.prod.yml     # Production overrides and scaling
├── docker-compose.test.yml     # Test environment configuration
├── docker/
│   ├── backend.Dockerfile      # Production backend image
│   ├── backend.development.Dockerfile
│   ├── backend.test.Dockerfile
│   ├── auth.Dockerfile         # Production auth service image
│   ├── auth.development.Dockerfile
│   ├── auth.test.Dockerfile
│   ├── frontend.Dockerfile     # Production frontend image
│   ├── frontend.development.Dockerfile
│   └── frontend.test.Dockerfile
└── .env.example                # Environment template
```

## Services

### Core Services
- **PostgreSQL**: Main database (port 5432)
- **Redis**: Caching and sessions (port 6379)
- **ClickHouse**: Analytics database (ports 8123/9000)
- **Backend**: Main API service (port 8000)
- **Auth**: Authentication service (port 8081)
- **Frontend**: Next.js application (port 3000)

### Optional Services
- **Nginx**: Reverse proxy (ports 80/443)
- **Prometheus**: Metrics collection (port 9090)
- **Grafana**: Metrics visualization (port 3001)

## Profiles
Docker Compose profiles allow selective service startup:

- `db`: Database services only
- `backend`: Backend + databases
- `auth`: Auth service + dependencies
- `frontend`: Frontend application
- `full`: All development services
- `analytics`: ClickHouse analytics
- `monitoring`: Prometheus + Grafana
- `proxy`: Nginx reverse proxy
- `backup`: Automated backup service

## Environment Variables
Key variables to configure in `.env`:

```bash
# Critical Security Keys (MUST CHANGE!)
SECRET_KEY=generate-with-openssl-rand-hex-32
JWT_SECRET_KEY=generate-with-openssl-rand-hex-32
POSTGRES_PASSWORD=strong-password-here
REDIS_PASSWORD=redis-password-here
CLICKHOUSE_PASSWORD=clickhouse-password-here

# API Keys
ANTHROPIC_API_KEY=your-key
OPENAI_API_KEY=your-key
GEMINI_API_KEY=your-key

# OAuth (for production)
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
```

## Commands

### Development
```bash
# Start with hot reload
docker-compose -f docker-compose.dev.yml up

# Rebuild after dependency changes
docker-compose -f docker-compose.dev.yml build --no-cache

# View logs
docker-compose -f docker-compose.dev.yml logs -f backend

# Execute commands in containers
docker-compose -f docker-compose.dev.yml exec backend python manage.py shell
docker-compose -f docker-compose.dev.yml exec postgres psql -U netra

# Clean up
docker-compose -f docker-compose.dev.yml down -v  # Remove volumes too
```

### Production
```bash
# Deploy
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Update specific service
docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull backend
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps backend

# Backup database
docker-compose -f docker-compose.yml --profile backup run --rm backup

# Monitor
docker-compose -f docker-compose.yml logs -f --tail=100

# Health check
docker-compose -f docker-compose.yml ps
docker-compose -f docker-compose.yml exec backend curl http://localhost:8000/health
```

## Networking
All services communicate via the `netra-network` bridge network:
- Services can reach each other by name (e.g., `http://backend:8000`)
- Development: 172.20.0.0/16 subnet
- Production: 10.0.0.0/24 subnet (overlay for Swarm)

## Volumes
Persistent data volumes:
- `postgres_data`: PostgreSQL database
- `redis_data`: Redis persistence
- `clickhouse_data`: ClickHouse database
- `clickhouse_logs`: ClickHouse logs
- `prometheus_data`: Metrics history
- `grafana_data`: Dashboard configurations

## Health Checks
All services include health checks for orchestration:
- Backend: `GET /health`
- Auth: `GET /health`
- Frontend: `GET /api/health`
- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`
- ClickHouse: `GET /ping`

## Performance Optimizations

### Mac/Windows Development
The `docker-compose.override.yml` includes:
- Volume mount optimizations (`:delegated`, `:cached`)
- Polling for file watchers
- Optimized reload settings

### Production
- Multi-stage builds for smaller images
- Resource limits and reservations
- Graceful shutdown handling
- Log rotation
- Horizontal scaling support

## Troubleshooting

### Common Issues

1. **Port conflicts**
   ```bash
   # Check what's using a port
   netstat -an | grep 8000
   # Change port in .env file
   BACKEND_PORT=8001
   ```

2. **Database connection issues**
   ```bash
   # Check database is ready
   docker-compose exec postgres pg_isready
   # Check logs
   docker-compose logs postgres
   ```

3. **Hot reload not working**
   - Ensure `WATCHDOG_USE_POLLING=true` in override file
   - Check volume mounts are correct
   - Restart the container

4. **Out of memory**
   - Adjust resource limits in docker-compose.prod.yml
   - Increase Docker Desktop memory allocation

## Security Notes
- Never commit `.env` file
- Rotate secrets regularly
- Use strong passwords (min 32 chars for keys)
- Enable rate limiting in production
- Configure SSL/TLS for production
- Restrict network access with firewall rules

## Monitoring Setup
Access monitoring dashboards:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/configured-password)

Import provided dashboards from `./grafana/dashboards/`

## Backup Strategy
Automated daily backups with the backup profile:
```bash
docker-compose -f docker-compose.yml --profile backup up -d
```

Backups stored in `./backups/` with 30-day retention.