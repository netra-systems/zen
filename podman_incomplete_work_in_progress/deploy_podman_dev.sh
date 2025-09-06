#!/bin/bash
# Deploy Netra Development Environment with Podman
set -e

echo "================================"
echo "Deploying Netra Development Environment with Podman"
echo "================================"

# Check if .env file exists, if not create a basic one
if [ ! -f .env ]; then
    echo "Creating default .env file..."
    cat > .env << 'EOF'
# Database
POSTGRES_USER=netra
POSTGRES_PASSWORD=netra123
POSTGRES_DB=netra_dev

# Redis
REDIS_PASSWORD=redis123

# ClickHouse
CLICKHOUSE_USER=netra
CLICKHOUSE_PASSWORD=netra123
CLICKHOUSE_DB=netra_analytics

# Auth Service
JWT_SECRET_KEY=dev-jwt-secret-key-must-be-at-least-32-characters
SERVICE_SECRET=test-secret-for-local-development-only-32chars
FERNET_KEY=iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=
SECRET_KEY=dev-secret-key-for-development

# OAuth (Optional - will work without these)
GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT=
GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT=
E2E_OAUTH_SIMULATION_KEY=test-key

# API Keys (Optional)
GEMINI_API_KEY=
EOF
    echo ".env file created with defaults"
fi

# Clean up any existing containers
echo "Cleaning up existing containers..."
podman-compose down -v 2>/dev/null || true

# Build all images
echo "Building images..."
echo "1/6: Building PostgreSQL (using official image)..."
podman pull postgres:15-alpine

echo "2/6: Building Redis (using official image)..."
podman pull redis:7-alpine

echo "3/6: Building ClickHouse (using official image)..."
podman pull clickhouse/clickhouse-server:23.8

echo "4/6: Building Auth Service..."
podman build -f docker/auth.Dockerfile -t netra-dev-auth:latest .

echo "5/6: Building Backend Service..."
podman build -f docker/backend.Dockerfile -t netra-dev-backend:latest .

echo "6/6: Building Frontend Service..."
podman build -f docker/frontend.Dockerfile -t netra-dev-frontend:latest \
    --build-arg BUILD_ENV=development \
    --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 \
    --build-arg NEXT_PUBLIC_AUTH_URL=http://localhost:8081 \
    --build-arg NEXT_PUBLIC_WS_URL=ws://localhost:8000 \
    --build-arg NEXT_PUBLIC_ENVIRONMENT=development .

# Start all services
echo "Starting all services with podman-compose..."
podman-compose up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 10

# Check status
echo "================================"
echo "Checking service status..."
echo "================================"
podman-compose ps

echo "================================"
echo "Service URLs:"
echo "================================"
echo "Frontend:   http://localhost:3000"
echo "Backend:    http://localhost:8000"
echo "Auth:       http://localhost:8081"
echo "PostgreSQL: localhost:5433"
echo "Redis:      localhost:6380"
echo "ClickHouse: http://localhost:8124 (HTTP), localhost:9001 (TCP)"
echo "================================"

# Check health endpoints
echo "Checking health endpoints..."
echo -n "Auth Service: "
curl -f http://localhost:8081/health 2>/dev/null && echo " ✓" || echo " ✗"
echo -n "Backend Service: "
curl -f http://localhost:8000/health 2>/dev/null && echo " ✓" || echo " ✗"
echo -n "Frontend Service: "
curl -f http://localhost:3000/api/health 2>/dev/null && echo " ✓" || echo " ✗"

echo "================================"
echo "Deployment complete!"
echo "================================"