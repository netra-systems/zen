# Netra Docker Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Netra Apex platform using Docker. The deployment includes all core services required for the minimal viable product.

## Architecture

The Netra platform consists of the following services:

- **PostgreSQL**: Primary database for user data and application state
- **Redis**: Cache and session management
- **ClickHouse**: Analytics and event tracking database
- **Auth Service**: Authentication and authorization microservice
- **Analytics Service**: Event tracking and analytics microservice
- **Backend Service**: Core API and business logic
- **Frontend Service**: Next.js web application

## Prerequisites

- Docker Desktop 4.0+ installed and running
- At least 8GB RAM allocated to Docker
- 20GB free disk space
- Windows 10/11, macOS 10.15+, or Linux

## Quick Start

### Windows

```bash
# Start development environment
deploy-docker.bat

# Start with clean rebuild
deploy-docker.bat -c -b

# View logs
deploy-docker.bat -a logs
```

### macOS/Linux

```bash
# Make script executable
chmod +x deploy-docker.sh

# Start development environment
./deploy-docker.sh

# Start with clean rebuild
./deploy-docker.sh -c -b

# View logs
./deploy-docker.sh -a logs
```

## Docker Compose Files

### Main Configuration Files

1. **docker-compose.yml**: Base configuration with dev/test profiles
2. **docker-compose.dev.yml**: Simplified development configuration
3. **docker-compose.override.yml**: Local development overrides with bind mounts

### Usage Examples

```bash
# Using profiles (recommended)
docker-compose --profile dev up -d     # Start development
docker-compose --profile test up -d    # Start test environment

# Using dev-specific compose file
docker-compose -f docker-compose.dev.yml up -d

# Stop all services
docker-compose down

# Clean everything including volumes
docker-compose down -v
```

## Service Configuration

### Environment Variables

Create `.env.development` file with the following key variables:

```env
ENVIRONMENT=development

# Database
POSTGRES_USER=netra
POSTGRES_PASSWORD=netra123
POSTGRES_DB=netra_dev

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Security Keys
JWT_SECRET_KEY=<your-32-char-secret>
SERVICE_SECRET=<your-service-secret>
FERNET_KEY=<your-fernet-key>

# LLM Configuration
ANTHROPIC_API_KEY=<your-api-key>
OPENAI_API_KEY=<your-api-key>
```

### Service URLs

Once deployed, services are accessible at:

**Development Environment:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Auth API: http://localhost:8081
- Analytics API: http://localhost:8090
- PostgreSQL: localhost:5433
- Redis: localhost:6380
- ClickHouse: http://localhost:8124

**Test Environment:**
- Frontend: http://localhost:3001
- Backend API: http://localhost:8001
- Auth API: http://localhost:8082
- Analytics API: http://localhost:8091
- PostgreSQL: localhost:5434
- Redis: localhost:6381
- ClickHouse: http://localhost:8125

## Deployment Workflows

### Initial Setup

1. Clone the repository
2. Copy `.env` to `.env.development`
3. Update environment variables as needed
4. Run deployment script

### Development Workflow

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Watch logs
docker-compose -f docker-compose.dev.yml logs -f backend

# Restart a specific service
docker-compose -f docker-compose.dev.yml restart backend

# Execute commands in container
docker-compose -f docker-compose.dev.yml exec backend bash
```

### Testing Workflow

```bash
# Start test environment
docker-compose --profile test up -d

# Run tests
docker-compose --profile test exec test-backend pytest

# View test logs
docker-compose --profile test logs test-backend
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check for conflicting processes
   netstat -an | grep -E "3000|8000|8081|8090|5433|6380"
   
   # Kill conflicting process (Windows)
   taskkill /F /PID <process_id>
   
   # Kill conflicting process (Mac/Linux)
   kill -9 <process_id>
   ```

2. **Docker Desktop Crashes**
   - Reduce memory allocation in Docker Desktop settings
   - Use named volumes instead of bind mounts
   - Clean unused volumes: `docker volume prune`

3. **Service Health Check Failures**
   ```bash
   # Check service status
   docker-compose ps
   
   # View detailed logs
   docker-compose logs <service-name>
   
   # Restart unhealthy service
   docker-compose restart <service-name>
   ```

4. **Database Connection Issues**
   ```bash
   # Check if database is ready
   docker-compose exec postgres pg_isready
   
   # Run migrations manually
   docker-compose exec backend alembic upgrade head
   ```

### Debugging Commands

```bash
# View all containers
docker ps -a

# Inspect container
docker inspect <container-name>

# View container logs
docker logs <container-name> --tail 100 -f

# Execute shell in container
docker exec -it <container-name> /bin/sh

# Check network connectivity
docker network inspect netra-network

# Monitor resource usage
docker stats
```

## Maintenance

### Backup and Restore

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U netra netra_dev > backup.sql

# Restore PostgreSQL
docker-compose exec -T postgres psql -U netra netra_dev < backup.sql

# Backup volumes
docker run --rm -v netra-postgres-data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data
```

### Updates and Migrations

```bash
# Pull latest changes
git pull origin main

# Rebuild images
docker-compose build --no-cache

# Run database migrations
docker-compose exec backend alembic upgrade head

# Restart services
docker-compose restart
```

### Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Clean unused Docker resources
docker system prune -a --volumes

# Remove specific volume
docker volume rm netra-postgres-data
```

## Performance Optimization

### Resource Limits

Services are configured with resource limits to prevent system overload:

- PostgreSQL: 256MB RAM, 0.25 CPU
- Redis: 128MB RAM, 0.125 CPU
- ClickHouse: 512MB RAM, 0.25 CPU
- Auth Service: 256MB RAM, 0.25 CPU
- Analytics Service: 512MB RAM, 0.5 CPU
- Backend Service: 512MB RAM, 0.5 CPU
- Frontend Service: 512MB RAM, 0.5 CPU

Total: ~2.5GB RAM, ~2.375 CPUs

### Volume Optimization

The configuration uses named volumes to avoid Docker Desktop sync issues:
- Code is baked into images during build
- Only data and logs use volumes
- Maximum 10 volumes to prevent crashes

## Security Considerations

1. **Never commit secrets** to version control
2. **Use strong passwords** for all services
3. **Rotate JWT secrets** regularly
4. **Enable HTTPS** in production
5. **Use Docker secrets** for sensitive data in production
6. **Restrict network access** using Docker networks

## Production Deployment

For production deployment:

1. Use production Dockerfiles without development dependencies
2. Enable SSL/TLS termination
3. Configure proper logging and monitoring
4. Use Docker Swarm or Kubernetes for orchestration
5. Implement proper backup strategies
6. Use external managed databases when possible

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review service logs
3. Consult the SPEC documentation
4. Create an issue in the project repository

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Netra Architecture Documentation](./docs/configuration_architecture.md)
- [API Documentation](./docs/api_documentation.md)