#!/bin/bash
# Start Real Services Testing Infrastructure
# This script sets up and starts all required services for real service testing

set -e

echo "🚀 Starting Real Services Testing Infrastructure"
echo "================================================"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Compose first."
    exit 1
fi

# Set environment variables for real services
export USE_REAL_SERVICES=true
export TESTING=1
export SKIP_MOCKS=true

# Test service configuration
export TEST_POSTGRES_HOST=localhost
export TEST_POSTGRES_PORT=5434
export TEST_POSTGRES_USER=test_user
export TEST_POSTGRES_PASSWORD=test_pass
export TEST_POSTGRES_DB=netra_test

export TEST_REDIS_HOST=localhost
export TEST_REDIS_PORT=6381
export TEST_REDIS_DB=0

export TEST_CLICKHOUSE_HOST=localhost
export TEST_CLICKHOUSE_HTTP_PORT=8125
export TEST_CLICKHOUSE_USER=test_user
export TEST_CLICKHOUSE_PASSWORD=test_pass
export TEST_CLICKHOUSE_DB=netra_test_analytics

# Service startup timeout
export TEST_SERVICE_STARTUP_TIMEOUT=60

echo "🔧 Configuration:"
echo "  - PostgreSQL: ${TEST_POSTGRES_HOST}:${TEST_POSTGRES_PORT}"
echo "  - Redis: ${TEST_REDIS_HOST}:${TEST_REDIS_PORT}"
echo "  - ClickHouse: ${TEST_CLICKHOUSE_HOST}:${TEST_CLICKHOUSE_HTTP_PORT}"
echo ""

# Stop any existing test services
echo "🧹 Cleaning up any existing test services..."
docker-compose -f docker-compose.test.yml down --remove-orphans --volumes 2>/dev/null || true

# Start test services
echo "🏗️  Starting test services..."
docker-compose -f docker-compose.test.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
max_attempts=30
attempt=0

check_service() {
    local service_name=$1
    local check_command=$2
    
    while [ $attempt -lt $max_attempts ]; do
        if eval "$check_command" &> /dev/null; then
            echo "✅ $service_name is ready"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo "   Waiting for $service_name... (attempt $attempt/$max_attempts)"
        sleep 2
    done
    
    echo "❌ $service_name failed to start after $max_attempts attempts"
    return 1
}

# Check PostgreSQL
check_service "PostgreSQL" "docker exec netra-test-postgres pg_isready -U test_user -d netra_test"

# Check Redis  
check_service "Redis" "docker exec netra-test-redis redis-cli ping"

# Check ClickHouse
check_service "ClickHouse" "curl -s http://localhost:8125/ping"

# Wait for seeder to complete (if running)
echo "⏳ Waiting for test data seeding to complete..."
if docker ps --format "table {{.Names}}" | grep -q netra-test-seeder; then
    docker wait netra-test-seeder 2>/dev/null || true
    echo "✅ Test data seeding completed"
fi

# Verify service monitor is running
echo "📊 Starting service monitor..."
if ! curl -s http://localhost:9090/health-status &> /dev/null; then
    echo "⚠️  Service monitor not available (this is optional)"
else
    echo "✅ Service monitor is running at http://localhost:9090"
fi

echo ""
echo "🎉 Real Services Testing Infrastructure is ready!"
echo ""
echo "📋 Available Services:"
echo "  - PostgreSQL: localhost:5434 (user: test_user, db: netra_test)"
echo "  - Redis: localhost:6381 (db: 0)"
echo "  - ClickHouse: localhost:8125 (user: test_user, db: netra_test_analytics)"
echo "  - Service Monitor: http://localhost:9090 (optional)"
echo ""
echo "🔧 Usage:"
echo "  # Run tests with real services"
echo "  export USE_REAL_SERVICES=true"
echo "  pytest tests/ -v"
echo ""
echo "  # Run validation tests"
echo "  pytest tests/test_real_services_validation.py -v"
echo ""
echo "  # Check service health"
echo "  curl http://localhost:9090/health-status | jq"
echo ""
echo "  # Stop services when done"
echo "  docker-compose -f docker-compose.test.yml down"
echo ""

# Show service status
echo "📊 Current Service Status:"
docker-compose -f docker-compose.test.yml ps

# Show logs if any service is not healthy
unhealthy_services=$(docker-compose -f docker-compose.test.yml ps --services --filter "health=unhealthy" 2>/dev/null || true)
if [ -n "$unhealthy_services" ]; then
    echo ""
    echo "⚠️  Some services are unhealthy. Showing logs:"
    for service in $unhealthy_services; do
        echo ""
        echo "📋 Logs for $service:"
        docker-compose -f docker-compose.test.yml logs --tail=20 "$service"
    done
fi

echo ""
echo "🎯 Ready to eliminate 5766+ mock violations with real services!"