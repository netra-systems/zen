#!/bin/bash

# Docker Stability Test Script
# Tests Docker daemon stability before running full development stack

set -e

echo "🔍 Testing Docker daemon stability..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Test 1: Basic Docker connectivity
echo "1. Testing Docker daemon connectivity..."
if docker version >/dev/null 2>&1; then
    print_status "Docker daemon is responding"
else
    print_error "Docker daemon is not responding"
    exit 1
fi

# Test 2: Hello World container
echo "2. Testing basic container functionality..."
if docker run --rm hello-world >/dev/null 2>&1; then
    print_status "Basic container execution works"
else
    print_error "Basic container execution failed"
    exit 1
fi

# Test 3: Resource monitoring
echo "3. Checking Docker resource allocation..."
docker system df
echo ""

# Test 4: Simple service test (PostgreSQL)
echo "4. Testing database service startup..."
echo "Starting PostgreSQL container..."
if docker run -d --name test-postgres -e POSTGRES_PASSWORD=test postgres:15-alpine >/dev/null 2>&1; then
    print_status "PostgreSQL container started"
    
    # Wait a moment for startup
    sleep 5
    
    # Check if container is still running
    if docker ps | grep test-postgres >/dev/null; then
        print_status "PostgreSQL container is stable"
    else
        print_warning "PostgreSQL container may have issues"
    fi
    
    # Cleanup
    docker stop test-postgres >/dev/null 2>&1
    docker rm test-postgres >/dev/null 2>&1
    print_status "Test container cleaned up"
else
    print_error "PostgreSQL container failed to start"
    exit 1
fi

# Test 5: Multiple containers simultaneously
echo "5. Testing multiple container stability..."
echo "Starting Redis and PostgreSQL together..."

if docker run -d --name test-redis redis:7-alpine >/dev/null 2>&1 && \
   docker run -d --name test-postgres2 -e POSTGRES_PASSWORD=test postgres:15-alpine >/dev/null 2>&1; then
    
    print_status "Multiple containers started successfully"
    
    # Wait and check stability
    sleep 10
    
    if docker ps | grep -E "(test-redis|test-postgres2)" | wc -l | grep -q "2"; then
        print_status "Multiple containers are stable"
    else
        print_warning "Some containers may be unstable"
    fi
    
    # Cleanup
    docker stop test-redis test-postgres2 >/dev/null 2>&1
    docker rm test-redis test-postgres2 >/dev/null 2>&1
    print_status "Test containers cleaned up"
else
    print_error "Multiple container test failed"
    exit 1
fi

echo ""
print_status "🎉 Docker daemon stability test PASSED!"
print_status "Docker is ready for development stack deployment"
echo ""

# Show current Docker info
echo "📊 Current Docker System Info:"
docker system info | grep -E "(Server Version|Total Memory|CPUs|Kernel Version)"