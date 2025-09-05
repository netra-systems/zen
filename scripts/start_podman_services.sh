#!/bin/bash
# Podman Services Startup Script for Netra E2E Testing
# Usage: wsl -d podman-machine-default -- bash scripts/start_podman_services.sh [command]

set -e

# Configuration
PROJECT_ROOT="/mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1"
COMPOSE_FILE="docker-compose.podman.yml"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

show_help() {
    echo -e "${GREEN}Netra Podman Services Management Script${NC}"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start all services (default)"
    echo "  stop      Stop all services"
    echo "  restart   Restart all services"
    echo "  status    Show service status"
    echo "  clean     Stop and clean up containers"
    echo "  logs      Show service logs"
    echo "  help      Show this help message"
    echo ""
    echo "Services managed:"
    echo "  - PostgreSQL (port 5433)"
    echo "  - Redis (port 6380)"
    echo "  - ClickHouse (port 8124)"
    echo "  - Auth Service (port 8081)"
    echo "  - Backend Service (port 8000)"
}

test_service_health() {
    local service_name="$1"
    local url="$2"
    
    if curl -f -s --max-time 5 "$url" > /dev/null 2>&1; then
        echo -e "✅ ${GREEN}$service_name is healthy${NC}"
        return 0
    else
        echo -e "❌ ${RED}$service_name is not responding at $url${NC}"
        return 1
    fi
}

wait_for_services() {
    echo -e "${YELLOW}Waiting for services to become healthy...${NC}"
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        echo -e "${CYAN}Health check attempt $attempt of $max_attempts${NC}"
        
        local all_healthy=true
        
        # Test backend health
        if ! test_service_health "Backend" "http://localhost:8000/health"; then
            all_healthy=false
        fi
        
        # Test auth service health
        if ! test_service_health "Auth Service" "http://localhost:8081/health"; then
            all_healthy=false
        fi
        
        if $all_healthy; then
            echo -e "🎉 ${GREEN}All services are healthy!${NC}"
            return 0
        fi
        
        if [ $attempt -lt $max_attempts ]; then
            echo -e "${YELLOW}Waiting 10 seconds before next health check...${NC}"
            sleep 10
        fi
    done
    
    echo -e "⚠️ ${YELLOW}Not all services became healthy within the timeout period${NC}"
    return 1
}

show_status() {
    echo -e "${GREEN}=== Podman Container Status ===${NC}"
    podman ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo -e "\n${GREEN}=== Compose Service Status ===${NC}"
    podman-compose -f "$COMPOSE_FILE" ps
    
    echo -e "\n${GREEN}=== Service Health Checks ===${NC}"
    test_service_health "Backend" "http://localhost:8000/health"
    test_service_health "Auth Service" "http://localhost:8081/health"
    
    echo -e "\n${GREEN}=== Database Connectivity ===${NC}"
    if podman exec netra-postgres pg_isready -U netra -d netra_dev > /dev/null 2>&1; then
        echo -e "✅ ${GREEN}PostgreSQL: Ready${NC}"
    else
        echo -e "❌ ${RED}PostgreSQL: Not accessible${NC}"
    fi
    
    if podman exec netra-redis redis-cli ping > /dev/null 2>&1; then
        echo -e "✅ ${GREEN}Redis: Ready${NC}"
    else
        echo -e "❌ ${RED}Redis: Not accessible${NC}"
    fi
    
    if podman exec netra-clickhouse clickhouse-client --query "SELECT 1" > /dev/null 2>&1; then
        echo -e "✅ ${GREEN}ClickHouse: Ready${NC}"
    else
        echo -e "❌ ${RED}ClickHouse: Not accessible${NC}"
    fi
}

start_services() {
    echo -e "🚀 ${GREEN}Starting Netra Podman Services...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Start services
    if podman-compose -f "$COMPOSE_FILE" up -d; then
        echo -e "${GREEN}Services started successfully!${NC}"
        
        # Wait for services to become healthy
        if wait_for_services; then
            echo -e "\n✅ ${GREEN}All services are ready for E2E testing!${NC}"
            show_status
        else
            echo -e "\n⚠️ ${YELLOW}Services started but some may not be fully healthy yet${NC}"
            echo -e "${CYAN}Run '$0 status' to check current state${NC}"
        fi
    else
        echo -e "❌ ${RED}Failed to start services${NC}"
        return 1
    fi
}

stop_services() {
    echo -e "🛑 ${YELLOW}Stopping Netra Podman Services...${NC}"
    
    cd "$PROJECT_ROOT"
    
    if podman-compose -f "$COMPOSE_FILE" down; then
        echo -e "${GREEN}Services stopped successfully!${NC}"
    else
        echo -e "❌ ${RED}Failed to stop services${NC}"
        return 1
    fi
}

clean_services() {
    echo -e "🧹 ${YELLOW}Cleaning up Podman containers and volumes...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Stop and remove containers with volumes
    podman-compose -f "$COMPOSE_FILE" down -v
    
    # Remove any dangling images
    podman image prune -f
    
    echo -e "${GREEN}Cleanup completed!${NC}"
}

restart_services() {
    echo -e "🔄 ${YELLOW}Restarting Netra Podman Services...${NC}"
    stop_services
    sleep 5
    start_services
}

show_logs() {
    echo -e "${GREEN}=== Service Logs ===${NC}"
    cd "$PROJECT_ROOT"
    podman-compose -f "$COMPOSE_FILE" logs --tail=50
}

# Main script logic
case "${1:-start}" in
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        restart_services
        ;;
    "status")
        show_status
        ;;
    "clean")
        clean_services
        ;;
    "logs")
        show_logs
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac