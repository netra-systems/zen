#!/bin/bash

# Bash script for managing development database on Unix/Linux/Mac

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_color "$YELLOW" "Checking prerequisites..."
    
    # Check Docker
    if command -v docker &> /dev/null; then
        print_color "$GREEN" "✓ Docker is installed"
        if docker info &> /dev/null; then
            print_color "$GREEN" "✓ Docker daemon is running"
        else
            print_color "$RED" "✗ Docker daemon is not running. Please start Docker."
            exit 1
        fi
    else
        print_color "$RED" "✗ Docker is not installed. Please install Docker."
        exit 1
    fi
    
    # Check Terraform
    if command -v terraform &> /dev/null; then
        print_color "$GREEN" "✓ Terraform is installed"
    else
        print_color "$RED" "✗ Terraform is not installed. Please install Terraform."
        exit 1
    fi
}

# Start development database
start_dev_database() {
    print_color "$CYAN" "Starting development database infrastructure..."
    
    if [ ! -d ".terraform" ]; then
        print_color "$YELLOW" "Initializing Terraform..."
        terraform init
    fi
    
    print_color "$YELLOW" "Creating infrastructure..."
    if terraform apply -auto-approve; then
        print_color "$GREEN" "\n✓ Development database started successfully!"
        print_color "$CYAN" "Connection details saved in: connection_info.txt"
        print_color "$CYAN" "Environment file created: ../.env.development.local"
        
        echo -e "\n${YELLOW}Quick Connect:${NC}"
        echo "PostgreSQL: psql -h localhost -p 5432 -U postgres -d netra_dev"
        echo "Redis:      redis-cli -h localhost -p 6379"
        echo "ClickHouse: http://localhost:8123"
    else
        print_color "$RED" "Failed to start infrastructure"
        exit 1
    fi
}

# Stop development database
stop_dev_database() {
    print_color "$CYAN" "Stopping development database infrastructure..."
    if terraform destroy -auto-approve; then
        print_color "$GREEN" "✓ Infrastructure stopped successfully"
    else
        print_color "$RED" "Failed to stop infrastructure"
        exit 1
    fi
}

# Restart development database
restart_dev_database() {
    stop_dev_database
    sleep 2
    start_dev_database
}

# Get status
get_status() {
    print_color "$CYAN" "Development Database Status"
    echo "=================================================="
    
    # Check containers
    containers=("netra-postgres-dev" "netra-redis-dev" "netra-clickhouse-dev")
    for container in "${containers[@]}"; do
        if docker inspect "$container" --format='{{.State.Status}}' 2>/dev/null | grep -q "running"; then
            print_color "$GREEN" "✓ $container : running"
            # Show port mappings
            ports=$(docker port "$container" 2>/dev/null || echo "")
            if [ -n "$ports" ]; then
                echo "  Ports: $ports"
            fi
        else
            status=$(docker inspect "$container" --format='{{.State.Status}}' 2>/dev/null || echo "not found")
            if [ "$status" = "not found" ]; then
                print_color "$RED" "✗ $container : not found"
            else
                print_color "$YELLOW" "⚠ $container : $status"
            fi
        fi
    done
    
    # Check volumes
    echo -e "\n${CYAN}Volumes:${NC}"
    volumes=("netra-postgres-dev-data" "netra-redis-dev-data" "netra-clickhouse-dev-data")
    for volume in "${volumes[@]}"; do
        if docker volume inspect "$volume" &>/dev/null; then
            print_color "$GREEN" "✓ $volume"
        else
            print_color "$RED" "✗ $volume : not found"
        fi
    done
    
    # Check network
    echo -e "\n${CYAN}Network:${NC}"
    if docker network inspect netra-dev-network &>/dev/null; then
        print_color "$GREEN" "✓ netra-dev-network"
    else
        print_color "$RED" "✗ netra-dev-network : not found"
    fi
}

# Show logs
show_logs() {
    print_color "$CYAN" "Showing logs (Ctrl+C to exit)..."
    
    echo -n "Enter container name (postgres/redis/clickhouse) [postgres]: "
    read container
    container=${container:-postgres}
    
    full_name="netra-$container-dev"
    docker logs -f "$full_name"
}

# Clean everything
clean_all() {
    print_color "$YELLOW" "WARNING: This will delete all data!"
    echo -n "Are you sure? (yes/no): "
    read confirm
    
    if [ "$confirm" = "yes" ]; then
        print_color "$RED" "Cleaning up everything..."
        
        # Destroy infrastructure
        terraform destroy -auto-approve 2>/dev/null || true
        
        # Remove volumes
        docker volume rm netra-postgres-dev-data 2>/dev/null || true
        docker volume rm netra-redis-dev-data 2>/dev/null || true
        docker volume rm netra-clickhouse-dev-data 2>/dev/null || true
        
        # Remove network
        docker network rm netra-dev-network 2>/dev/null || true
        
        # Remove terraform state
        rm -rf .terraform* terraform.tfstate* connection_info.txt
        rm -f ../.env.development.local
        
        print_color "$GREEN" "✓ Cleanup complete"
    else
        print_color "$YELLOW" "Cleanup cancelled"
    fi
}

# Connect to database
connect_database() {
    print_color "$CYAN" "Connect to database"
    echo "1. PostgreSQL"
    echo "2. Redis"
    echo "3. ClickHouse"
    
    echo -n "Select database (1-3): "
    read choice
    
    case $choice in
        1)
            print_color "$YELLOW" "Connecting to PostgreSQL..."
            docker exec -it netra-postgres-dev psql -U postgres -d netra_dev
            ;;
        2)
            print_color "$YELLOW" "Connecting to Redis..."
            docker exec -it netra-redis-dev redis-cli
            ;;
        3)
            print_color "$YELLOW" "Opening ClickHouse in browser..."
            if command -v xdg-open &> /dev/null; then
                xdg-open "http://localhost:8123"
            elif command -v open &> /dev/null; then
                open "http://localhost:8123"
            else
                echo "Please open http://localhost:8123 in your browser"
            fi
            ;;
        *)
            print_color "$RED" "Invalid choice"
            ;;
    esac
}

# Backup databases
backup_databases() {
    print_color "$CYAN" "Creating backups..."
    
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_dir="backups/$timestamp"
    mkdir -p "$backup_dir"
    
    # Backup PostgreSQL
    print_color "$YELLOW" "Backing up PostgreSQL..."
    docker exec netra-postgres-dev pg_dumpall -U postgres > "$backup_dir/postgres_backup.sql"
    
    # Backup Redis
    print_color "$YELLOW" "Backing up Redis..."
    docker exec netra-redis-dev redis-cli SAVE
    docker cp netra-redis-dev:/data/dump.rdb "$backup_dir/redis_backup.rdb"
    
    print_color "$GREEN" "✓ Backups saved to $backup_dir"
}

# Show usage
show_usage() {
    echo "Usage: $0 {start|stop|restart|status|logs|clean|connect|backup}"
    echo ""
    echo "Commands:"
    echo "  start    - Start development database infrastructure"
    echo "  stop     - Stop development database infrastructure"
    echo "  restart  - Restart development database infrastructure"
    echo "  status   - Show status of all containers and resources"
    echo "  logs     - Show logs for a specific container"
    echo "  clean    - Remove all containers, volumes, and data (WARNING: destructive)"
    echo "  connect  - Connect to a database interactively"
    echo "  backup   - Create backups of all databases"
    echo ""
}

# Main execution
echo -e "\n${CYAN}Netra Development Database Manager${NC}"
echo "=================================================="

check_prerequisites

# Parse command
case "${1:-status}" in
    start)
        start_dev_database
        ;;
    stop)
        stop_dev_database
        ;;
    restart)
        restart_dev_database
        ;;
    status)
        get_status
        ;;
    logs)
        show_logs
        ;;
    clean)
        clean_all
        ;;
    connect)
        connect_database
        ;;
    backup)
        backup_databases
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_color "$RED" "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac

echo "" # Add newline at end