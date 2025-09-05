#!/bin/bash

# Podman Services Manager for macOS
# Manages Netra services using Podman instead of Docker Desktop

set -e

COMPOSE_FILE="docker-compose.podman-mac.yml"
PROJECT_NAME="netra-apex"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_podman() {
    if ! command -v podman &> /dev/null; then
        log_error "Podman is not installed. Install with: brew install podman"
        exit 1
    fi
    
    if ! command -v podman-compose &> /dev/null; then
        log_error "podman-compose is not installed. Install with: pip3 install podman-compose"
        exit 1
    fi
}

check_machine() {
    if ! podman machine list | grep -q "Currently running"; then
        log_warning "Podman machine is not running. Starting..."
        podman machine start
        sleep 5
    fi
}

start_services() {
    log_info "Starting Netra services with Podman..."
    check_podman
    check_machine
    
    podman-compose -f "$COMPOSE_FILE" up -d
    
    log_success "Services started successfully!"
    show_status
}

stop_services() {
    log_info "Stopping Netra services..."
    podman-compose -f "$COMPOSE_FILE" down
    log_success "Services stopped successfully!"
}

restart_services() {
    log_info "Restarting Netra services..."
    stop_services
    sleep 2
    start_services
}

show_status() {
    log_info "Service Status:"
    podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo
    log_info "Health Check Results:"
    
    # Check Frontend (local)
    if curl -sf http://localhost:3001/api/health > /dev/null 2>&1; then
        log_success "Frontend (http://localhost:3001) - HEALTHY"
    else
        log_warning "Frontend (http://localhost:3001) - NOT RUNNING (start with: cd frontend && npm run dev)"
    fi
    
    # Check Auth Service
    if curl -sf http://localhost:8482/health > /dev/null 2>&1; then
        log_success "Auth Service (http://localhost:8482) - HEALTHY"
    else
        log_error "Auth Service (http://localhost:8482) - UNHEALTHY"
    fi
    
    # Check Backend Service
    if curl -sf http://localhost:8480/health > /dev/null 2>&1; then
        log_success "Backend Service (http://localhost:8480) - HEALTHY"
    else
        log_error "Backend Service (http://localhost:8480) - UNHEALTHY"
    fi
    
    # Check Redis
    if redis-cli -h localhost -p 8410 ping > /dev/null 2>&1; then
        log_success "Redis (localhost:8410) - HEALTHY"
    else
        log_error "Redis (localhost:8410) - UNHEALTHY"
    fi
    
    # Check PostgreSQL
    if PGPASSWORD=netra123 psql -h localhost -p 8090 -U netra -d netra_dev -c "SELECT 1;" > /dev/null 2>&1; then
        log_success "PostgreSQL (localhost:8090) - HEALTHY"
    else
        log_error "PostgreSQL (localhost:8090) - UNHEALTHY"
    fi
    
    # Check ClickHouse
    if curl -sf http://localhost:8492 > /dev/null 2>&1; then
        log_success "ClickHouse (localhost:8492) - HEALTHY"
    else
        log_error "ClickHouse (localhost:8492) - UNHEALTHY"
    fi
}

show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        log_info "Showing logs for all services..."
        podman-compose -f "$COMPOSE_FILE" logs -f
    else
        log_info "Showing logs for $service..."
        podman-compose -f "$COMPOSE_FILE" logs -f "$service"
    fi
}

clean_services() {
    log_warning "This will remove all containers and volumes. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        log_info "Cleaning up services..."
        podman-compose -f "$COMPOSE_FILE" down -v
        podman system prune -f
        log_success "Cleanup completed!"
    else
        log_info "Cleanup cancelled."
    fi
}

build_images() {
    log_info "Building Docker images..."
    check_podman
    check_machine
    
    podman-compose -f "$COMPOSE_FILE" build
    log_success "Images built successfully!"
}

show_help() {
    echo "Netra Podman Services Manager for macOS"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  start     Start all services"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  status    Show service status and health"
    echo "  logs      Show logs for all services"
    echo "  logs <service>  Show logs for specific service"
    echo "  build     Build Docker images"
    echo "  clean     Remove containers and volumes"
    echo "  help      Show this help message"
    echo
    echo "Services:"
    echo "  - Frontend: http://localhost:3001 (running locally)"
    echo "  - Auth Service: http://localhost:8482"
    echo "  - Backend Service: http://localhost:8480"
    echo "  - PostgreSQL: localhost:8090"
    echo "  - Redis: localhost:8410"
    echo "  - ClickHouse: localhost:8492"
}

# Main script logic
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    build)
        build_images
        ;;
    clean)
        clean_services
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac