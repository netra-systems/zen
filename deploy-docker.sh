#!/bin/bash

# Netra Docker Deployment Script
# Manages Docker deployment for development and test environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROFILE="dev"
ACTION="up"
BUILD=false
CLEAN=false
LOGS=false

# Function to print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -p, --profile PROFILE    Profile to use (dev|test) [default: dev]"
    echo "  -a, --action ACTION      Action to perform (up|down|restart|status|logs) [default: up]"
    echo "  -b, --build             Force rebuild of images"
    echo "  -c, --clean             Clean volumes and rebuild"
    echo "  -l, --logs              Follow logs after starting"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Start dev environment"
    echo "  $0 -p test              # Start test environment"
    echo "  $0 -a down              # Stop all services"
    echo "  $0 -b -c                # Clean rebuild dev environment"
    echo "  $0 -p dev -l            # Start dev and follow logs"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        -a|--action)
            ACTION="$2"
            shift 2
            ;;
        -b|--build)
            BUILD=true
            shift
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -l|--logs)
            LOGS=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate profile
if [[ "$PROFILE" != "dev" && "$PROFILE" != "test" ]]; then
    print_color "$RED" "Error: Invalid profile '$PROFILE'. Must be 'dev' or 'test'"
    exit 1
fi

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_color "$RED" "Error: Docker is not running. Please start Docker Desktop."
        exit 1
    fi
}

# Function to check environment files
check_env_files() {
    if [[ "$PROFILE" == "dev" ]]; then
        if [[ ! -f ".env.development" ]]; then
            print_color "$YELLOW" "Warning: .env.development not found. Creating from .env..."
            cp .env .env.development 2>/dev/null || touch .env.development
        fi
    fi
}

# Function to clean volumes
clean_volumes() {
    print_color "$YELLOW" "Cleaning Docker volumes for $PROFILE environment..."
    docker-compose --profile "$PROFILE" down -v
    print_color "$GREEN" "Volumes cleaned successfully"
}

# Function to build images
build_images() {
    print_color "$BLUE" "Building Docker images for $PROFILE environment..."
    docker-compose --profile "$PROFILE" build --no-cache
    print_color "$GREEN" "Images built successfully"
}

# Function to start services
start_services() {
    local build_flag=""
    if [[ "$BUILD" == true ]]; then
        build_flag="--build"
    fi
    
    print_color "$BLUE" "Starting $PROFILE environment..."
    docker-compose --profile "$PROFILE" up -d $build_flag
    
    # Wait for services to be healthy
    print_color "$YELLOW" "Waiting for services to become healthy..."
    sleep 5
    
    # Check service health
    check_service_health
}

# Function to stop services
stop_services() {
    print_color "$YELLOW" "Stopping $PROFILE environment..."
    docker-compose --profile "$PROFILE" down
    print_color "$GREEN" "Services stopped"
}

# Function to restart services
restart_services() {
    stop_services
    start_services
}

# Function to check service health
check_service_health() {
    print_color "$BLUE" "Checking service health..."
    
    # Get list of running containers for the profile
    services=$(docker-compose --profile "$PROFILE" ps --services)
    
    all_healthy=true
    for service in $services; do
        container_name="netra-${PROFILE}-${service#${PROFILE}-}"
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container_name"; then
            status=$(docker ps --format "{{.Status}}" -f "name=$container_name" | head -n1)
            if echo "$status" | grep -q "healthy"; then
                print_color "$GREEN" "✓ $service is healthy"
            elif echo "$status" | grep -q "starting"; then
                print_color "$YELLOW" "⏳ $service is starting..."
                all_healthy=false
            else
                print_color "$RED" "✗ $service is unhealthy or not running"
                all_healthy=false
            fi
        fi
    done
    
    if [[ "$all_healthy" == true ]]; then
        print_color "$GREEN" "\n✅ All services are healthy!"
        print_service_urls
    else
        print_color "$YELLOW" "\n⚠️ Some services are still starting or unhealthy"
        print_color "$YELLOW" "Run '$0 -a status' to check again"
    fi
}

# Function to print service URLs
print_service_urls() {
    print_color "$BLUE" "\n📌 Service URLs:"
    
    if [[ "$PROFILE" == "dev" ]]; then
        echo "  Frontend:    http://localhost:3000"
        echo "  Backend API: http://localhost:8000"
        echo "  Auth API:    http://localhost:8081"
        echo "  Analytics:   http://localhost:8090"
        echo "  WebSocket:   ws://localhost:8000/ws"
        echo ""
        echo "  PostgreSQL:  localhost:5433"
        echo "  Redis:       localhost:6380"
        echo "  ClickHouse:  http://localhost:8124"
    else
        echo "  Frontend:    http://localhost:3001"
        echo "  Backend API: http://localhost:8001"
        echo "  Auth API:    http://localhost:8082"
        echo "  Analytics:   http://localhost:8091"
        echo "  WebSocket:   ws://localhost:8001/ws"
        echo ""
        echo "  PostgreSQL:  localhost:5434"
        echo "  Redis:       localhost:6381"
        echo "  ClickHouse:  http://localhost:8123"
    fi
}

# Function to show logs
show_logs() {
    print_color "$BLUE" "Showing logs for $PROFILE environment..."
    docker-compose --profile "$PROFILE" logs -f
}

# Function to show service status
show_status() {
    print_color "$BLUE" "Service status for $PROFILE environment:\n"
    docker-compose --profile "$PROFILE" ps
    echo ""
    check_service_health
}

# Main execution
print_color "$BLUE" "🚀 Netra Docker Deployment Manager"
print_color "$BLUE" "==================================\n"

# Check Docker is running
check_docker

# Check environment files
check_env_files

# Execute action
case $ACTION in
    up)
        if [[ "$CLEAN" == true ]]; then
            clean_volumes
        fi
        start_services
        if [[ "$LOGS" == true ]]; then
            show_logs
        fi
        ;;
    down)
        stop_services
        ;;
    restart)
        restart_services
        if [[ "$LOGS" == true ]]; then
            show_logs
        fi
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    *)
        print_color "$RED" "Error: Invalid action '$ACTION'"
        show_usage
        exit 1
        ;;
esac