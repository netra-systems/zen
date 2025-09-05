#!/bin/bash
# Netra Services Verification Script
# Comprehensive health checks for all services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

CONTAINER_PREFIX="netra"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if container is running
check_container() {
    local container_name=$1
    if podman ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
        print_success "Container $container_name is running"
        return 0
    else
        print_error "Container $container_name is not running"
        return 1
    fi
}

# Function to check PostgreSQL
check_postgres() {
    print_status "Checking PostgreSQL..."
    check_container "netra-postgres" || return 1
    
    # Try to connect to PostgreSQL
    if podman exec netra-postgres pg_isready -U netra -p 5433 >/dev/null 2>&1; then
        print_success "PostgreSQL is accepting connections"
    else
        print_warning "PostgreSQL health check failed, but container is running"
    fi
}

# Function to check Redis
check_redis() {
    print_status "Checking Redis..."
    check_container "netra-redis" || return 1
    
    # Try to ping Redis
    if podman exec netra-redis redis-cli -p 6380 ping | grep -q PONG; then
        print_success "Redis is responding to ping"
    else
        print_warning "Redis health check failed, but container is running"
    fi
}

# Function to check ClickHouse
check_clickhouse() {
    print_status "Checking ClickHouse..."
    check_container "netra-clickhouse" || return 1
    
    # Try to query ClickHouse
    if podman exec netra-clickhouse clickhouse-client --port 9001 --query "SELECT 1" >/dev/null 2>&1; then
        print_success "ClickHouse is accepting queries"
    else
        print_warning "ClickHouse health check failed, but container is running"
    fi
}

# Function to check Auth service
check_auth() {
    print_status "Checking Auth service..."
    check_container "netra-auth" || return 1
    
    # Check if the process is running
    if podman exec netra-auth ps aux | grep -q "[p]ython"; then
        print_success "Auth service Python process is running"
    else
        print_warning "Auth service Python process not found"
    fi
}

# Function to check Backend service  
check_backend() {
    print_status "Checking Backend service..."
    check_container "netra-backend" || return 1
    
    # Check if the process is running
    if podman exec netra-backend ps aux | grep -q "[p]ython"; then
        print_success "Backend service Python process is running"
    else
        print_warning "Backend service Python process not found"
    fi
}

# Function to show service URLs and info
show_service_info() {
    print_status "Service Information:"
    echo
    echo "Database Services:"
    echo "  PostgreSQL: localhost:5433 (user: netra, db: netra_dev)"
    echo "  Redis: localhost:6380"
    echo "  ClickHouse HTTP: http://localhost:8124"
    echo "  ClickHouse TCP: localhost:9001"
    echo
    echo "Application Services:"
    echo "  Auth Service: http://localhost:8081"
    echo "  Backend Service: http://localhost:8000"
    echo
    echo "Health Endpoints (may not be accessible due to WSL networking):"
    echo "  Auth Health: http://localhost:8081/health"
    echo "  Backend Health: http://localhost:8000/health"
    echo
}

# Function to show container resource usage
show_resource_usage() {
    print_status "Container Resource Usage:"
    echo
    podman stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
    echo
}

# Main verification
main() {
    echo "=========================================="
    echo "    Netra Services Verification"
    echo "=========================================="
    echo

    local all_good=true
    
    check_postgres || all_good=false
    echo
    check_redis || all_good=false
    echo
    check_clickhouse || all_good=false
    echo
    check_auth || all_good=false
    echo
    check_backend || all_good=false
    echo
    
    show_resource_usage
    show_service_info
    
    if [ "$all_good" = true ]; then
        print_success "All services are running successfully!"
        echo
        print_status "To test the services, you can:"
        echo "  1. Connect to PostgreSQL: podman exec -it netra-postgres psql -U netra -d netra_dev"
        echo "  2. Test Redis: podman exec -it netra-redis redis-cli -p 6380"
        echo "  3. Query ClickHouse: podman exec -it netra-clickhouse clickhouse-client --port 9001"
        echo "  4. View service logs: bash start_netra_services.sh logs [service_name]"
    else
        print_error "Some services may have issues. Check the output above."
    fi
}

main "$@"