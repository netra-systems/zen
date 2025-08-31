#!/bin/bash

# Docker Volume Management Script
# This script helps manage Docker volumes for the Netra platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_color "$RED" "Error: Docker is not running. Please start Docker Desktop."
        exit 1
    fi
}

# Function to list all Netra volumes
list_volumes() {
    print_color "$GREEN" "=== Netra Docker Volumes ==="
    docker volume ls | grep netra || print_color "$YELLOW" "No Netra volumes found"
}

# Function to show volume sizes
show_volume_sizes() {
    print_color "$GREEN" "=== Volume Sizes ==="
    for volume in $(docker volume ls -q | grep netra); do
        size=$(docker run --rm -v ${volume}:/data alpine du -sh /data 2>/dev/null | cut -f1)
        echo "${volume}: ${size}"
    done
}

# Function to backup a volume
backup_volume() {
    local volume=$1
    local backup_dir=${2:-./backups}
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${backup_dir}/${volume}_${timestamp}.tar.gz"
    
    mkdir -p "$backup_dir"
    
    print_color "$YELLOW" "Backing up ${volume} to ${backup_file}..."
    docker run --rm -v ${volume}:/source -v $(pwd)/${backup_dir}:/backup alpine \
        tar -czf /backup/$(basename ${backup_file}) -C /source .
    
    print_color "$GREEN" "Backup completed: ${backup_file}"
}

# Function to restore a volume
restore_volume() {
    local volume=$1
    local backup_file=$2
    
    if [ ! -f "$backup_file" ]; then
        print_color "$RED" "Error: Backup file not found: ${backup_file}"
        exit 1
    fi
    
    print_color "$YELLOW" "Restoring ${volume} from ${backup_file}..."
    docker run --rm -v ${volume}:/target -v $(pwd)/$(dirname ${backup_file}):/backup alpine \
        tar -xzf /backup/$(basename ${backup_file}) -C /target
    
    print_color "$GREEN" "Restore completed"
}

# Function to clean unused volumes
clean_volumes() {
    print_color "$YELLOW" "Cleaning unused volumes..."
    docker volume prune -f
    print_color "$GREEN" "Cleanup completed"
}

# Function to reset all Netra volumes
reset_volumes() {
    print_color "$RED" "WARNING: This will delete all Netra Docker volumes and their data!"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        print_color "$YELLOW" "Operation cancelled"
        exit 0
    fi
    
    print_color "$YELLOW" "Stopping all Netra containers..."
    docker-compose down
    
    print_color "$YELLOW" "Removing all Netra volumes..."
    docker volume ls -q | grep netra | xargs -r docker volume rm || true
    
    print_color "$GREEN" "All Netra volumes have been reset"
}

# Function to initialize volumes with code
init_code_volumes() {
    print_color "$GREEN" "=== Initializing Code Volumes ==="
    
    # Create temporary container to copy files
    print_color "$YELLOW" "Copying code to named volumes..."
    
    # Backend services
    docker run --rm -v $(pwd):/source -v netra-dev-backend-code:/target alpine \
        sh -c "cp -r /source/netra_backend/* /target/ 2>/dev/null || true"
    
    docker run --rm -v $(pwd):/source -v netra-dev-auth-code:/target alpine \
        sh -c "cp -r /source/auth_service/* /target/ 2>/dev/null || true"
    
    docker run --rm -v $(pwd):/source -v netra-dev-analytics-code:/target alpine \
        sh -c "cp -r /source/analytics_service/* /target/ 2>/dev/null || true"
    
    docker run --rm -v $(pwd):/source -v netra-dev-shared-code:/target alpine \
        sh -c "cp -r /source/shared/* /target/ 2>/dev/null || true"
    
    docker run --rm -v $(pwd):/source -v netra-dev-spec-data:/target alpine \
        sh -c "cp -r /source/SPEC/* /target/ 2>/dev/null || true"
    
    docker run --rm -v $(pwd):/source -v netra-dev-scripts:/target alpine \
        sh -c "cp -r /source/scripts/* /target/ 2>/dev/null || true"
    
    # Frontend
    docker run --rm -v $(pwd)/frontend:/source -v netra-dev-frontend-code:/target alpine \
        sh -c "cp -r /source/* /target/ 2>/dev/null || true"
    
    print_color "$GREEN" "Code volumes initialized"
}

# Function to sync code from host to volumes
sync_to_volumes() {
    print_color "$YELLOW" "Syncing code from host to volumes..."
    init_code_volumes
    print_color "$GREEN" "Sync completed"
}

# Function to sync code from volumes to host
sync_from_volumes() {
    print_color "$YELLOW" "Syncing code from volumes to host..."
    
    # Create backup first
    backup_dir="./volume_sync_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    cp -r netra_backend "$backup_dir/" 2>/dev/null || true
    cp -r auth_service "$backup_dir/" 2>/dev/null || true
    cp -r analytics_service "$backup_dir/" 2>/dev/null || true
    cp -r shared "$backup_dir/" 2>/dev/null || true
    
    # Sync from volumes
    docker run --rm -v netra-dev-backend-code:/source -v $(pwd):/target alpine \
        sh -c "cp -r /source/* /target/netra_backend/ 2>/dev/null || true"
    
    docker run --rm -v netra-dev-auth-code:/source -v $(pwd):/target alpine \
        sh -c "cp -r /source/* /target/auth_service/ 2>/dev/null || true"
    
    docker run --rm -v netra-dev-analytics-code:/source -v $(pwd):/target alpine \
        sh -c "cp -r /source/* /target/analytics_service/ 2>/dev/null || true"
    
    docker run --rm -v netra-dev-shared-code:/source -v $(pwd):/target alpine \
        sh -c "cp -r /source/* /target/shared/ 2>/dev/null || true"
    
    print_color "$GREEN" "Sync completed. Backup saved to: ${backup_dir}"
}

# Main menu
show_menu() {
    echo ""
    print_color "$GREEN" "=== Docker Volume Management for Netra ==="
    echo "1. List all Netra volumes"
    echo "2. Show volume sizes"
    echo "3. Initialize code volumes (first time setup)"
    echo "4. Sync code TO volumes (host -> volume)"
    echo "5. Sync code FROM volumes (volume -> host)"
    echo "6. Backup a volume"
    echo "7. Restore a volume"
    echo "8. Clean unused volumes"
    echo "9. Reset all volumes (DANGEROUS)"
    echo "0. Exit"
    echo ""
    read -p "Select an option: " choice
}

# Main script
check_docker

if [ $# -eq 0 ]; then
    # Interactive mode
    while true; do
        show_menu
        case $choice in
            1) list_volumes ;;
            2) show_volume_sizes ;;
            3) init_code_volumes ;;
            4) sync_to_volumes ;;
            5) sync_from_volumes ;;
            6) 
                read -p "Enter volume name: " volume
                backup_volume "$volume"
                ;;
            7)
                read -p "Enter volume name: " volume
                read -p "Enter backup file path: " backup_file
                restore_volume "$volume" "$backup_file"
                ;;
            8) clean_volumes ;;
            9) reset_volumes ;;
            0) exit 0 ;;
            *) print_color "$RED" "Invalid option" ;;
        esac
        read -p "Press Enter to continue..."
    done
else
    # Command mode
    case $1 in
        list) list_volumes ;;
        sizes) show_volume_sizes ;;
        init) init_code_volumes ;;
        sync-to) sync_to_volumes ;;
        sync-from) sync_from_volumes ;;
        backup) backup_volume "$2" "$3" ;;
        restore) restore_volume "$2" "$3" ;;
        clean) clean_volumes ;;
        reset) reset_volumes ;;
        *) 
            print_color "$RED" "Unknown command: $1"
            echo "Usage: $0 [list|sizes|init|sync-to|sync-from|backup|restore|clean|reset]"
            exit 1
            ;;
    esac
fi