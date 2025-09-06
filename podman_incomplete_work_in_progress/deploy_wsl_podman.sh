#!/bin/bash
# Deploy Netra services in WSL Podman
set -e

echo "Deploying Netra services with WSL Podman..."
cd /mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1

# Clean up any existing containers
echo "Cleaning up existing containers..."
podman stop -a 2>/dev/null || true
podman rm -a -f 2>/dev/null || true
podman network prune -f 2>/dev/null || true

# Create network
echo "Creating network..."
podman network create netra-network || true

# Pull base images
echo "Pulling base images..."
podman pull postgres:15-alpine
podman pull redis:7-alpine  
podman pull clickhouse/clickhouse-server:23.8

# Build custom images
echo "Building backend image..."
podman build -f docker/backend.podman.Dockerfile -t netra-backend:latest .

echo "Building auth image..."
podman build -f docker/auth.Dockerfile -t netra-auth:latest .

echo "Building frontend image..."
podman build -f docker/frontend.Dockerfile -t netra-frontend:latest \
    --build-arg BUILD_ENV=development \
    --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 \
    --build-arg NEXT_PUBLIC_AUTH_URL=http://localhost:8081 \
    --build-arg NEXT_PUBLIC_WS_URL=ws://localhost:8000 \
    --build-arg NEXT_PUBLIC_ENVIRONMENT=development

# Start infrastructure services with reduced memory
echo "Starting PostgreSQL..."
podman run -d --name netra-postgres \
    --network netra-network \
    --memory=512m \
    -e POSTGRES_USER=netra \
    -e POSTGRES_PASSWORD=netra123 \
    -e POSTGRES_DB=netra_dev \
    -p 5433:5432 \
    postgres:15-alpine

echo "Starting Redis..."
podman run -d --name netra-redis \
    --network netra-network \
    --memory=256m \
    -p 6380:6379 \
    redis:7-alpine \
    redis-server --maxmemory 100mb --maxmemory-policy allkeys-lru

echo "Starting ClickHouse..."
podman run -d --name netra-clickhouse \
    --network netra-network \
    --memory=1g \
    -e CLICKHOUSE_DB=netra_analytics \
    -e CLICKHOUSE_USER=netra \
    -e CLICKHOUSE_PASSWORD=netra123 \
    -e CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1 \
    -p 8124:8123 \
    -p 9001:9000 \
    clickhouse/clickhouse-server:23.8

# Wait for databases
echo "Waiting for databases to be ready..."
sleep 15

# Start application services with memory limits
echo "Starting Auth service..."
podman run -d --name netra-auth \
    --network netra-network \
    --memory=512m \
    -e ENVIRONMENT=development \
    -e LOG_LEVEL=info \
    -e POSTGRES_HOST=netra-postgres \
    -e POSTGRES_PORT=5432 \
    -e POSTGRES_USER=netra \
    -e POSTGRES_PASSWORD=netra123 \
    -e POSTGRES_DB=netra_dev \
    -e REDIS_HOST=netra-redis \
    -e REDIS_PORT=6379 \
    -e PORT=8081 \
    -e HOST=0.0.0.0 \
    -e SERVICE_ID=auth-service \
    -e SERVICE_SECRET=test-secret-for-local-development-only-32chars \
    -e JWT_SECRET_KEY=dev-jwt-secret-key-must-be-at-least-32-characters \
    -p 8081:8081 \
    netra-auth:latest

echo "Starting Backend service..."
podman run -d --name netra-backend \
    --network netra-network \
    --memory=1g \
    -e ENVIRONMENT=development \
    -e LOG_LEVEL=info \
    -e POSTGRES_HOST=netra-postgres \
    -e POSTGRES_PORT=5432 \
    -e POSTGRES_USER=netra \
    -e POSTGRES_PASSWORD=netra123 \
    -e POSTGRES_DB=netra_dev \
    -e REDIS_HOST=netra-redis \
    -e REDIS_PORT=6379 \
    -e CLICKHOUSE_HOST=netra-clickhouse \
    -e CLICKHOUSE_PORT=9000 \
    -e CLICKHOUSE_USER=netra \
    -e CLICKHOUSE_PASSWORD=netra123 \
    -e CLICKHOUSE_DB=netra_analytics \
    -e AUTH_SERVICE_URL=http://netra-auth:8081 \
    -e PORT=8000 \
    -e HOST=0.0.0.0 \
    -e JWT_SECRET_KEY=dev-jwt-secret-key-must-be-at-least-32-characters \
    -e SERVICE_SECRET=dev-service-secret-for-cross-service-auth \
    -e FERNET_KEY=iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw= \
    -e SECRET_KEY=dev-secret-key-for-development \
    -p 8000:8000 \
    netra-backend:latest

echo "Starting Frontend service..."
podman run -d --name netra-frontend \
    --network netra-network \
    --memory=512m \
    -e NODE_ENV=production \
    -e PORT=3000 \
    -p 3000:3000 \
    netra-frontend:latest

echo "Waiting for services to start..."
sleep 10

# Check status
echo "================================"
echo "Service Status:"
echo "================================"
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "================================"
echo "Deployment complete!"
echo "================================"
echo "Frontend:   http://localhost:3000"
echo "Backend:    http://localhost:8000"
echo "Auth:       http://localhost:8081"
echo "PostgreSQL: localhost:5433"
echo "Redis:      localhost:6380"
echo "ClickHouse: http://localhost:8124"