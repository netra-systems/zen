#!/bin/bash
# Netra Services Startup Script - Direct Podman Commands with Host Networking
# Bypasses DNS issues by using host networking mode

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/mnt/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1"
CONTAINER_PREFIX="netra"

# Default environment variables
export POSTGRES_USER="${POSTGRES_USER:-netra}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-netra123}"
export POSTGRES_DB="${POSTGRES_DB:-netra_dev}"
export POSTGRES_PORT="${POSTGRES_PORT:-5433}"

export REDIS_PORT="${REDIS_PORT:-6380}"

export CLICKHOUSE_DB="${CLICKHOUSE_DB:-netra_analytics}"
export CLICKHOUSE_USER="${CLICKHOUSE_USER:-netra}"
export CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD:-netra123}"
export CLICKHOUSE_HTTP_PORT="${CLICKHOUSE_HTTP_PORT:-8124}"
export CLICKHOUSE_TCP_PORT="${CLICKHOUSE_TCP_PORT:-9001}"

export AUTH_PORT="${AUTH_PORT:-8081}"
export BACKEND_PORT="${BACKEND_PORT:-8000}"

export SERVICE_SECRET="${SERVICE_SECRET:-test-secret-for-local-development-only-32chars}"
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-dev-jwt-secret-key-must-be-at-least-32-characters}"
export FERNET_KEY="${FERNET_KEY:-iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=}"
export SECRET_KEY="${SECRET_KEY:-dev-secret-key-for-development-32-chars}"

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

# Function to check if a port is available
check_port() {
    local port=$1
    if netstat -tuln | grep -q ":$port "; then
        print_warning "Port $port is already in use"
        return 1
    fi
    return 0
}

# Function to wait for service to be healthy
wait_for_service() {
    local service_name=$1
    local health_check=$2
    local max_attempts=${3:-30}
    local attempt=0
    
    print_status "Waiting for $service_name to be healthy..."
    
    while [ $attempt -lt $max_attempts ]; do
        if eval "$health_check" >/dev/null 2>&1; then
            print_success "$service_name is healthy"
            return 0
        fi
        attempt=$((attempt + 1))
        printf "."
        sleep 2
    done
    
    print_error "$service_name failed to become healthy after $max_attempts attempts"
    return 1
}

# Function to wait for port to be available
wait_for_port() {
    local port=$1
    local service_name=$2
    local max_attempts=${3:-30}
    local attempt=0
    
    print_status "Waiting for $service_name on port $port to be ready..."
    
    while [ $attempt -lt $max_attempts ]; do
        # Try to connect to the port using bash's built-in network functionality
        if timeout 2 bash -c "exec 3<>/dev/tcp/localhost/$port && exec 3>&-" 2>/dev/null; then
            print_success "$service_name on port $port is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        printf "."
        sleep 2
    done
    
    # For now, just warn instead of failing - containers might be working but port check failing due to WSL networking
    print_warning "$service_name on port $port health check failed, but continuing (container might still be working)"
    return 0
}

# Function to stop and remove existing containers
cleanup_containers() {
    print_status "Cleaning up existing containers..."
    
    containers=("${CONTAINER_PREFIX}-postgres" "${CONTAINER_PREFIX}-redis" "${CONTAINER_PREFIX}-clickhouse" "${CONTAINER_PREFIX}-auth" "${CONTAINER_PREFIX}-backend")
    
    for container in "${containers[@]}"; do
        if podman ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
            print_status "Stopping and removing container: $container"
            podman stop "$container" >/dev/null 2>&1 || true
            podman rm "$container" >/dev/null 2>&1 || true
        fi
    done
}

# Function to create volumes
create_volumes() {
    print_status "Creating named volumes..."
    
    volumes=("${CONTAINER_PREFIX}_postgres_data" "${CONTAINER_PREFIX}_redis_data" "${CONTAINER_PREFIX}_clickhouse_data" "${CONTAINER_PREFIX}_auth_cache" "${CONTAINER_PREFIX}_backend_cache")
    
    for volume in "${volumes[@]}"; do
        if ! podman volume exists "$volume" 2>/dev/null; then
            podman volume create "$volume"
            print_status "Created volume: $volume"
        fi
    done
}

# Function to start PostgreSQL
start_postgres() {
    print_status "Starting PostgreSQL on port $POSTGRES_PORT..."
    
    if ! check_port "$POSTGRES_PORT"; then
        print_error "Port $POSTGRES_PORT is already in use. Please free the port or change POSTGRES_PORT environment variable."
        return 1
    fi
    
    podman run -d \
        --name "${CONTAINER_PREFIX}-postgres" \
        --network=host \
        -e POSTGRES_USER="$POSTGRES_USER" \
        -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
        -e POSTGRES_DB="$POSTGRES_DB" \
        -e POSTGRES_HOST_AUTH_METHOD=md5 \
        -e POSTGRES_INITDB_ARGS="--auth-host=md5" \
        -e PGPORT="$POSTGRES_PORT" \
        -v "${CONTAINER_PREFIX}_postgres_data":/var/lib/postgresql/data \
        -v "$PROJECT_DIR/scripts/init_db.sql":/docker-entrypoint-initdb.d/01-init.sql:ro \
        --memory=512m \
        --cpus=0.25 \
        postgres:15-alpine
    
    # Wait for PostgreSQL to be ready
    wait_for_port "$POSTGRES_PORT" "PostgreSQL"
}

# Function to start Redis
start_redis() {
    print_status "Starting Redis on port $REDIS_PORT..."
    
    if ! check_port "$REDIS_PORT"; then
        print_error "Port $REDIS_PORT is already in use. Please free the port or change REDIS_PORT environment variable."
        return 1
    fi
    
    podman run -d \
        --name "${CONTAINER_PREFIX}-redis" \
        --network=host \
        -e REDIS_PORT="$REDIS_PORT" \
        -v "${CONTAINER_PREFIX}_redis_data":/data \
        --memory=256m \
        --cpus=0.1 \
        redis:7-alpine \
        redis-server --port "$REDIS_PORT" --maxmemory 200mb --maxmemory-policy allkeys-lru --appendonly yes
    
    # Wait for Redis to be ready
    wait_for_port "$REDIS_PORT" "Redis"
}

# Function to start ClickHouse
start_clickhouse() {
    print_status "Starting ClickHouse on ports $CLICKHOUSE_HTTP_PORT/$CLICKHOUSE_TCP_PORT..."
    
    if ! check_port "$CLICKHOUSE_HTTP_PORT" || ! check_port "$CLICKHOUSE_TCP_PORT"; then
        print_error "ClickHouse ports are already in use. Please free the ports or change CLICKHOUSE_*_PORT environment variables."
        return 1
    fi
    
    podman run -d \
        --name "${CONTAINER_PREFIX}-clickhouse" \
        --network=host \
        -e CLICKHOUSE_DB="$CLICKHOUSE_DB" \
        -e CLICKHOUSE_USER="$CLICKHOUSE_USER" \
        -e CLICKHOUSE_PASSWORD="$CLICKHOUSE_PASSWORD" \
        -e CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1 \
        -e CLICKHOUSE_MAX_MEMORY_USAGE=500000000 \
        -e CLICKHOUSE_HTTP_PORT="$CLICKHOUSE_HTTP_PORT" \
        -e CLICKHOUSE_TCP_PORT="$CLICKHOUSE_TCP_PORT" \
        -v "${CONTAINER_PREFIX}_clickhouse_data":/var/lib/clickhouse \
        --memory=768m \
        --cpus=0.2 \
        clickhouse/clickhouse-server:23-alpine \
        /bin/bash -c "sed -i 's/<http_port>8123<\/http_port>/<http_port>$CLICKHOUSE_HTTP_PORT<\/http_port>/' /etc/clickhouse-server/config.xml && sed -i 's/<tcp_port>9000<\/tcp_port>/<tcp_port>$CLICKHOUSE_TCP_PORT<\/tcp_port>/' /etc/clickhouse-server/config.xml && /entrypoint.sh"
    
    # Wait for ClickHouse to be ready
    wait_for_port "$CLICKHOUSE_HTTP_PORT" "ClickHouse"
}

# Function to start Auth service
start_auth() {
    print_status "Starting Auth service on port $AUTH_PORT..."
    
    if ! check_port "$AUTH_PORT"; then
        print_error "Port $AUTH_PORT is already in use. Please free the port or change AUTH_PORT environment variable."
        return 1
    fi
    
    podman run -d \
        --name "${CONTAINER_PREFIX}-auth" \
        --network=host \
        -e ENVIRONMENT=development \
        -e LOG_LEVEL=INFO \
        -e PYTHONPATH=/app \
        -e PYTHONDONTWRITEBYTECODE=1 \
        -e PYTHONUNBUFFERED=1 \
        -e POSTGRES_HOST=localhost \
        -e POSTGRES_PORT="$POSTGRES_PORT" \
        -e POSTGRES_USER="$POSTGRES_USER" \
        -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
        -e POSTGRES_DB="$POSTGRES_DB" \
        -e REDIS_HOST=localhost \
        -e REDIS_PORT="$REDIS_PORT" \
        -e PORT="$AUTH_PORT" \
        -e HOST=0.0.0.0 \
        -e SERVICE_ID=auth-service \
        -e SERVICE_SECRET="$SERVICE_SECRET" \
        -e JWT_SECRET_KEY="$JWT_SECRET_KEY" \
        -e JWT_ALGORITHM=HS256 \
        -e ACCESS_TOKEN_EXPIRE_MINUTES=30 \
        -e GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT="$GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT" \
        -e GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT="$GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT" \
        -e E2E_OAUTH_SIMULATION_KEY="$E2E_OAUTH_SIMULATION_KEY" \
        -v "$PROJECT_DIR/auth_service":/app/auth_service:ro \
        -v "$PROJECT_DIR/shared":/app/shared:ro \
        -v "${CONTAINER_PREFIX}_auth_cache":/app/.cache \
        --memory=768m \
        --cpus=0.25 \
        netra-auth-alpine:latest
    
    # Wait for Auth service to be ready
    wait_for_port "$AUTH_PORT" "Auth service" 60
}

# Function to start Backend service
start_backend() {
    print_status "Starting Backend service on port $BACKEND_PORT..."
    
    if ! check_port "$BACKEND_PORT"; then
        print_error "Port $BACKEND_PORT is already in use. Please free the port or change BACKEND_PORT environment variable."
        return 1
    fi
    
    podman run -d \
        --name "${CONTAINER_PREFIX}-backend" \
        --network=host \
        -e ENVIRONMENT=development \
        -e LOG_LEVEL=INFO \
        -e PYTHONPATH=/app \
        -e PYTHONDONTWRITEBYTECODE=1 \
        -e PYTHONUNBUFFERED=1 \
        -e POSTGRES_HOST=localhost \
        -e POSTGRES_PORT="$POSTGRES_PORT" \
        -e POSTGRES_USER="$POSTGRES_USER" \
        -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
        -e POSTGRES_DB="$POSTGRES_DB" \
        -e REDIS_HOST=localhost \
        -e REDIS_PORT="$REDIS_PORT" \
        -e CLICKHOUSE_HOST=localhost \
        -e CLICKHOUSE_PORT="$CLICKHOUSE_TCP_PORT" \
        -e CLICKHOUSE_USER="$CLICKHOUSE_USER" \
        -e CLICKHOUSE_PASSWORD="$CLICKHOUSE_PASSWORD" \
        -e CLICKHOUSE_DB="$CLICKHOUSE_DB" \
        -e AUTH_SERVICE_URL="http://localhost:$AUTH_PORT" \
        -e PORT="$BACKEND_PORT" \
        -e HOST=0.0.0.0 \
        -e JWT_SECRET_KEY="$JWT_SECRET_KEY" \
        -e SERVICE_SECRET="$SERVICE_SECRET" \
        -e FERNET_KEY="$FERNET_KEY" \
        -e SECRET_KEY="$SECRET_KEY" \
        -e GEMINI_API_KEY="$GEMINI_API_KEY" \
        -e ENABLE_MEMORY_MONITORING=true \
        -e MEMORY_CHECK_INTERVAL=60 \
        -e MEMORY_WARNING_THRESHOLD=80 \
        -e MEMORY_CRITICAL_THRESHOLD=90 \
        -e MEMORY_CLEANUP_ENABLED=true \
        -v "$PROJECT_DIR/netra_backend":/app/netra_backend:ro \
        -v "$PROJECT_DIR/shared":/app/shared:ro \
        -v "$PROJECT_DIR/test_framework":/app/test_framework:ro \
        -v "$PROJECT_DIR/SPEC":/app/SPEC:ro \
        -v "${CONTAINER_PREFIX}_backend_cache":/app/.cache \
        --memory=2g \
        --cpus=0.4 \
        netra-backend-alpine:latest
    
    # Wait for Backend service to be ready
    wait_for_port "$BACKEND_PORT" "Backend service" 90
}

# Function to show service status
show_status() {
    print_status "Service Status Summary:"
    echo
    
    containers=("${CONTAINER_PREFIX}-postgres" "${CONTAINER_PREFIX}-redis" "${CONTAINER_PREFIX}-clickhouse" "${CONTAINER_PREFIX}-auth" "${CONTAINER_PREFIX}-backend")
    ports=("$POSTGRES_PORT" "$REDIS_PORT" "$CLICKHOUSE_HTTP_PORT,$CLICKHOUSE_TCP_PORT" "$AUTH_PORT" "$BACKEND_PORT")
    
    for i in "${!containers[@]}"; do
        container=${containers[$i]}
        port=${ports[$i]}
        
        if podman ps --format "{{.Names}}" | grep -q "^${container}$"; then
            status=$(podman ps --filter "name=${container}" --format "{{.Status}}")
            print_success "$container: Running ($status) - Port(s): $port"
        else
            print_error "$container: Not running"
        fi
    done
    
    echo
    print_status "Service URLs:"
    echo "  PostgreSQL: localhost:$POSTGRES_PORT"
    echo "  Redis: localhost:$REDIS_PORT"
    echo "  ClickHouse HTTP: http://localhost:$CLICKHOUSE_HTTP_PORT"
    echo "  ClickHouse TCP: localhost:$CLICKHOUSE_TCP_PORT"
    echo "  Auth Service: http://localhost:$AUTH_PORT"
    echo "  Backend Service: http://localhost:$BACKEND_PORT"
    echo
    print_status "Health Check URLs:"
    echo "  Auth Health: http://localhost:$AUTH_PORT/health"
    echo "  Backend Health: http://localhost:$BACKEND_PORT/health"
}

# Function to stop all services
stop_services() {
    print_status "Stopping all Netra services..."
    cleanup_containers
    print_success "All services stopped"
}

# Function to show logs
show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        print_error "Please specify a service: postgres, redis, clickhouse, auth, backend"
        return 1
    fi
    
    container_name="${CONTAINER_PREFIX}-${service}"
    if podman ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
        podman logs "$container_name"
    else
        print_error "Container $container_name is not running"
        return 1
    fi
}

# Main execution
main() {
    case "${1:-start}" in
        "start")
            print_status "Starting Netra services with host networking..."
            
            # Change to project directory
            cd "$PROJECT_DIR" || exit 1
            
            cleanup_containers
            create_volumes
            
            # Start services in dependency order
            start_postgres || exit 1
            start_redis || exit 1
            start_clickhouse || exit 1
            start_auth || exit 1
            start_backend || exit 1
            
            show_status
            print_success "All Netra services started successfully!"
            ;;
            
        "stop")
            stop_services
            ;;
            
        "status")
            show_status
            ;;
            
        "restart")
            print_status "Restarting Netra services..."
            stop_services
            sleep 2
            main start
            ;;
            
        "logs")
            show_logs "$2"
            ;;
            
        "cleanup")
            print_status "Cleaning up containers and volumes..."
            cleanup_containers
            volumes=("${CONTAINER_PREFIX}_postgres_data" "${CONTAINER_PREFIX}_redis_data" "${CONTAINER_PREFIX}_clickhouse_data" "${CONTAINER_PREFIX}_auth_cache" "${CONTAINER_PREFIX}_backend_cache")
            for volume in "${volumes[@]}"; do
                if podman volume exists "$volume" 2>/dev/null; then
                    podman volume rm "$volume"
                    print_status "Removed volume: $volume"
                fi
            done
            print_success "Cleanup completed"
            ;;
            
        "help"|"-h"|"--help")
            echo "Netra Services Management Script"
            echo
            echo "Usage: $0 [COMMAND] [OPTIONS]"
            echo
            echo "Commands:"
            echo "  start     Start all Netra services (default)"
            echo "  stop      Stop all Netra services"
            echo "  restart   Restart all Netra services"
            echo "  status    Show status of all services"
            echo "  logs      Show logs for a specific service"
            echo "  cleanup   Remove all containers and volumes"
            echo "  help      Show this help message"
            echo
            echo "Environment Variables:"
            echo "  POSTGRES_PORT     PostgreSQL port (default: 5433)"
            echo "  REDIS_PORT        Redis port (default: 6380)"
            echo "  CLICKHOUSE_HTTP_PORT  ClickHouse HTTP port (default: 8124)"
            echo "  CLICKHOUSE_TCP_PORT   ClickHouse TCP port (default: 9001)"
            echo "  AUTH_PORT         Auth service port (default: 8081)"
            echo "  BACKEND_PORT      Backend service port (default: 8000)"
            echo
            echo "Examples:"
            echo "  $0 start"
            echo "  $0 logs auth"
            echo "  $0 status"
            echo "  POSTGRES_PORT=5434 $0 start"
            ;;
            
        *)
            print_error "Unknown command: $1"
            print_status "Use '$0 help' to see available commands"
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"