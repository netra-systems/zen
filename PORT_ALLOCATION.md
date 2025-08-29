# Docker Compose Port Allocation Guide

## Current Port Allocation

### Test Environment (docker-compose.test.yml)
- **PostgreSQL**: 5432
- **Redis**: 6379  
- **ClickHouse HTTP**: 8123
- **ClickHouse TCP**: 9000

### Development Environment (docker-compose.dev.yml)
- **PostgreSQL**: 5433
- **Redis**: 6380
- **ClickHouse HTTP**: 8124
- **ClickHouse TCP**: 9001

### Production/Main Environment (docker-compose.yml)
- **PostgreSQL**: 5435
- **Redis**: 6382
- **ClickHouse HTTP**: 8125
- **ClickHouse TCP**: 9002
- **Backend**: 8000
- **Auth Service**: 8081
- **Frontend**: 3000
- **Prometheus**: 9090
- **Grafana**: 3001

## Usage

### To use specific environments:

```bash
# Test environment
docker-compose -f docker-compose.test.yml up -d

# Development environment  
docker-compose -f docker-compose.dev.yml up -d

# Production/Main environment
docker-compose up -d
```

### To check for port conflicts:
```bash
# List all containers and their ports
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Check specific port usage
netstat -an | grep :8123
lsof -i :8123  # on macOS/Linux
```

## Environment Variables

Set these in your `.env` file to override default ports:

```bash
# Main environment
POSTGRES_PORT=5435
REDIS_PORT=6382
CLICKHOUSE_HTTP_PORT=8125
CLICKHOUSE_TCP_PORT=9002

# Dev environment
DEV_POSTGRES_PORT=5433
DEV_REDIS_PORT=6380
DEV_CLICKHOUSE_HTTP_PORT=8124
DEV_CLICKHOUSE_TCP_PORT=9001

# Test environment
TEST_POSTGRES_PORT=5432
TEST_REDIS_PORT=6379
TEST_CLICKHOUSE_HTTP_PORT=8123
TEST_CLICKHOUSE_TCP_PORT=9000
```

## Troubleshooting

If you encounter port allocation errors:

1. Check which containers are running: `docker ps`
2. Stop conflicting containers: `docker stop <container-name>`
3. Or use different ports by updating the `.env` file
4. Restart with: `docker-compose down && docker-compose up -d`

## Notes

- The `.env.docker` file contains a comprehensive port mapping reference
- Always check for running containers before starting a new environment
- Use `docker-compose down` to cleanly stop all services in an environment