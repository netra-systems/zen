#!/bin/bash
# Unified Testing Environment Startup Script
# Purpose: One-command startup for complete testing environment
# Usage: ./start-unified-tests.sh [--build] [--logs] [--cleanup]

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.test.yml"
ENV_FILE=".env.test"
PROJECT_NAME="netra-unified-test"

# Function to print colored output
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

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop or Docker daemon."
        exit 1
    fi
    print_success "Docker is running"
}

# Function to check if docker-compose is available
check_compose() {
    if ! command -v docker-compose > /dev/null 2>&1; then
        if ! docker compose version > /dev/null 2>&1; then
            print_error "docker-compose or 'docker compose' not available"
            exit 1
        fi
        DOCKER_COMPOSE_CMD="docker compose"
    else
        DOCKER_COMPOSE_CMD="docker-compose"
    fi
    print_success "Docker Compose is available"
}

# Function to validate configuration files
check_config() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "Docker Compose file ($COMPOSE_FILE) not found"
        exit 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        print_error "Environment file ($ENV_FILE) not found"
        exit 1
    fi

    print_success "Configuration files found"
}

# Function to cleanup existing containers
cleanup() {
    print_status "Cleaning up existing containers..."
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file $ENV_FILE down --volumes --remove-orphans
    
    # Remove any dangling images
    docker image prune -f > /dev/null 2>&1 || true
    
    print_success "Cleanup completed"
}

# Function to build images
build_images() {
    print_status "Building Docker images..."
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file $ENV_FILE build --no-cache
    print_success "Images built successfully"
}

# Function to start services
start_services() {
    print_status "Starting unified test environment..."
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file $ENV_FILE up -d \
        test-postgres test-clickhouse test-redis
    
    # Wait for databases to be ready
    print_status "Waiting for databases to be ready..."
    sleep 30
    
    # Start application services
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file $ENV_FILE up -d \
        auth-service backend-service
    
    # Wait for backend services
    print_status "Waiting for backend services..."
    sleep 30
    
    # Start frontend
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file $ENV_FILE up -d \
        frontend-service
    
    # Wait for frontend
    print_status "Waiting for frontend service..."
    sleep 20
    
    print_success "All services started"
}

# Function to run migrations
run_migrations() {
    print_status "Running database migrations..."
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file $ENV_FILE run --rm migration-runner
    print_success "Migrations completed"
}

# Function to run tests
run_tests() {
    print_status "Running unified test suite..."
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file $ENV_FILE run --rm test-runner
    
    # Copy test results to host
    CONTAINER_ID=$($DOCKER_COMPOSE_CMD -f $COMPOSE_FILE ps -q test-runner)
    if [ -n "$CONTAINER_ID" ]; then
        docker cp $CONTAINER_ID:/app/test_results ./test_results_unified/ || true
        print_success "Test results copied to ./test_results_unified/"
    fi
}

# Function to show service status
show_status() {
    print_status "Service Status:"
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file $ENV_FILE ps
    
    echo ""
    print_status "Service Health Checks:"
    
    # Check PostgreSQL
    if $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file $ENV_FILE exec test-postgres pg_isready -U test_user > /dev/null 2>&1; then
        print_success "PostgreSQL: Healthy"
    else
        print_warning "PostgreSQL: Not Ready"
    fi
    
    # Check ClickHouse
    if curl -sf http://localhost:8124/ping > /dev/null 2>&1; then
        print_success "ClickHouse: Healthy"
    else
        print_warning "ClickHouse: Not Ready"
    fi
    
    # Check Redis
    if $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file $ENV_FILE exec test-redis redis-cli -a test_password ping > /dev/null 2>&1; then
        print_success "Redis: Healthy"
    else
        print_warning "Redis: Not Ready"
    fi
    
    # Check Auth Service
    if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
        print_success "Auth Service: Healthy"
    else
        print_warning "Auth Service: Not Ready"
    fi
    
    # Check Backend Service
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Backend Service: Healthy"
    else
        print_warning "Backend Service: Not Ready"
    fi
    
    # Check Frontend Service
    if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
        print_success "Frontend Service: Healthy"
    else
        print_warning "Frontend Service: Not Ready"
    fi
}

# Function to show logs
show_logs() {
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file $ENV_FILE logs -f
}

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --build         Force rebuild of Docker images"
    echo "  --cleanup       Clean up containers and volumes before starting"
    echo "  --logs          Show live logs after starting services"
    echo "  --status        Show service status and health checks"
    echo "  --test-only     Only run tests (assume services are already running)"
    echo "  --stop          Stop all services"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Start services and run tests"
    echo "  $0 --build --cleanup  # Clean rebuild and run tests"
    echo "  $0 --status           # Check service health"
    echo "  $0 --logs             # View live logs"
    echo "  $0 --stop             # Stop all services"
}

# Main execution
main() {
    local BUILD=false
    local CLEANUP=false
    local LOGS=false
    local STATUS=false
    local TEST_ONLY=false
    local STOP=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build)
                BUILD=true
                shift
                ;;
            --cleanup)
                CLEANUP=true
                shift
                ;;
            --logs)
                LOGS=true
                shift
                ;;
            --status)
                STATUS=true
                shift
                ;;
            --test-only)
                TEST_ONLY=true
                shift
                ;;
            --stop)
                STOP=true
                shift
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Perform pre-flight checks
    check_docker
    check_compose
    check_config
    
    if $STOP; then
        cleanup
        exit 0
    fi
    
    if $STATUS; then
        show_status
        exit 0
    fi
    
    if $LOGS; then
        show_logs
        exit 0
    fi
    
    # Main execution flow
    print_status "Starting Netra Unified Testing Environment"
    echo "========================================"
    
    if $CLEANUP; then
        cleanup
    fi
    
    if $BUILD; then
        build_images
    fi
    
    if ! $TEST_ONLY; then
        start_services
        run_migrations
    fi
    
    # Wait a bit more for services to fully stabilize
    print_status "Allowing services to stabilize..."
    sleep 10
    
    run_tests
    
    if $LOGS; then
        print_status "Showing live logs (Press Ctrl+C to exit)..."
        show_logs
    else
        print_success "Unified testing completed!"
        print_status "To view logs: docker-compose -f $COMPOSE_FILE logs"
        print_status "To stop services: docker-compose -f $COMPOSE_FILE down"
        show_status
    fi
}

# Execute main function with all arguments
main "$@"