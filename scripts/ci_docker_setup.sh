#!/bin/bash
# CI Docker Setup Script - Ensures services are properly started for E2E tests

set -e

echo "=== CI Docker Setup for E2E Tests ==="

# Function to wait for a service
wait_for_service() {
    local service_name=$1
    local check_command=$2
    local max_attempts=30
    local attempt=1
    
    echo "Waiting for $service_name..."
    while [ $attempt -le $max_attempts ]; do
        if eval "$check_command" 2>/dev/null; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service_name failed to start after $max_attempts attempts"
    return 1
}

# Function to check Docker Compose file exists
check_compose_file() {
    if [ ! -f "$1" ]; then
        echo "❌ Docker Compose file not found: $1"
        exit 1
    fi
    echo "✅ Found Docker Compose file: $1"
}

# Main setup
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.alpine-test.yml}"

echo "Using Docker Compose file: $COMPOSE_FILE"
check_compose_file "$COMPOSE_FILE"

# Stop any existing containers
echo "Cleaning up existing containers..."
docker compose -f "$COMPOSE_FILE" down -v || true

# Start services
echo "Starting services with Docker Compose..."
docker compose -f "$COMPOSE_FILE" up -d

# Wait for PostgreSQL
wait_for_service "PostgreSQL" "docker compose -f $COMPOSE_FILE exec -T postgres pg_isready -U test_user"

# Wait for Redis
wait_for_service "Redis" "docker compose -f $COMPOSE_FILE exec -T redis redis-cli ping"

# Wait for Backend
wait_for_service "Backend" "curl -f http://localhost:8000/health"

# Wait for Auth Service
wait_for_service "Auth Service" "curl -f http://localhost:8081/health"

# Show service status
echo ""
echo "=== Service Status ==="
docker compose -f "$COMPOSE_FILE" ps

# Export environment variables for tests
echo ""
echo "=== Setting Test Environment Variables ==="
export USE_REAL_SERVICES=true
export DATABASE_URL="postgresql://test_user:test_password@localhost:5434/netra_test"
export REDIS_URL="redis://:test_password@localhost:6381/0"
export BACKEND_URL="http://localhost:8000"
export AUTH_URL="http://localhost:8081"
export TEST_MODE=ci
export CI_MODE=true

echo "✅ Docker services are ready for E2E tests!"
echo ""
echo "Environment variables set:"
echo "  DATABASE_URL=$DATABASE_URL"
echo "  REDIS_URL=$REDIS_URL"
echo "  BACKEND_URL=$BACKEND_URL"
echo "  AUTH_URL=$AUTH_URL"