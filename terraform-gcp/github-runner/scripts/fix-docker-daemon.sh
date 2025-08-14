#!/bin/bash
set -e

# Fix Docker daemon initialization for GitHub runners
echo "Fixing Docker daemon for GitHub runner..."

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Ensure Docker daemon is properly initialized
fix_docker_daemon() {
    log "Checking Docker daemon status..."
    
    # Check if Docker socket exists
    if [ ! -S /var/run/docker.sock ]; then
        log "Docker socket not found. Creating and starting Docker daemon..."
        
        # Ensure Docker is installed
        if ! command -v docker &>/dev/null; then
            log "Docker not installed. Installing..."
            apt-get update
            apt-get install -y docker.io docker-compose
        fi
        
        # Clean up any stale Docker state
        rm -rf /var/run/docker.pid
        rm -rf /var/run/docker.sock
        
        # Start Docker daemon
        systemctl daemon-reload
        systemctl enable docker
        systemctl start docker
    fi
    
    # Wait for Docker daemon to be ready
    log "Waiting for Docker daemon to initialize..."
    local max_wait=60
    local count=0
    
    while [ $count -lt $max_wait ]; do
        if docker version &>/dev/null 2>&1; then
            log "Docker daemon is ready"
            break
        fi
        sleep 1
        count=$((count + 1))
        
        if [ $((count % 10)) -eq 0 ]; then
            log "Still waiting for Docker daemon... ($count seconds)"
        fi
    done
    
    if [ $count -eq $max_wait ]; then
        log "ERROR: Docker daemon failed to start after $max_wait seconds"
        log "Docker service status:"
        systemctl status docker --no-pager
        log "Docker logs:"
        journalctl -xe -u docker --no-pager | tail -100
        exit 1
    fi
}

# Fix Docker permissions for runner user
fix_docker_permissions() {
    log "Fixing Docker permissions..."
    
    # Ensure docker group exists
    if ! getent group docker &>/dev/null; then
        groupadd docker
    fi
    
    # Add runner user to docker group if exists
    if id runner &>/dev/null 2>&1; then
        usermod -aG docker runner
        log "Added runner user to docker group"
    fi
    
    # Fix socket permissions
    if [ -S /var/run/docker.sock ]; then
        chgrp docker /var/run/docker.sock
        chmod 660 /var/run/docker.sock
        log "Fixed Docker socket permissions"
    fi
}

# Setup Docker buildx
setup_docker_buildx() {
    log "Setting up Docker buildx..."
    
    # Check if buildx is available
    if ! docker buildx version &>/dev/null 2>&1; then
        log "Installing Docker buildx plugin..."
        
        # Download and install buildx
        BUILDX_VERSION="v0.11.2"
        mkdir -p /usr/local/lib/docker/cli-plugins
        curl -L "https://github.com/docker/buildx/releases/download/${BUILDX_VERSION}/buildx-${BUILDX_VERSION}.linux-amd64" \
            -o /usr/local/lib/docker/cli-plugins/docker-buildx
        chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
    fi
    
    # Create buildx builder
    if docker buildx ls | grep -q "runner-builder"; then
        log "Buildx builder 'runner-builder' already exists"
        docker buildx use runner-builder
    else
        log "Creating new buildx builder..."
        docker buildx create --name runner-builder --driver docker-container --use
    fi
    
    # Bootstrap the builder
    docker buildx inspect --bootstrap &>/dev/null || {
        log "Bootstrapping buildx builder..."
        docker buildx inspect --bootstrap
    }
    
    log "Docker buildx is ready"
}

# Verify Docker functionality
verify_docker() {
    log "Verifying Docker functionality..."
    
    # Test basic Docker command
    if docker version &>/dev/null 2>&1; then
        log "✓ Docker daemon is responsive"
    else
        log "✗ Docker daemon not responding"
        return 1
    fi
    
    # Test Docker run
    if docker run --rm hello-world &>/dev/null 2>&1; then
        log "✓ Docker can run containers"
    else
        log "✗ Docker cannot run containers"
        return 1
    fi
    
    # Test buildx
    if docker buildx version &>/dev/null 2>&1; then
        log "✓ Docker buildx is available"
    else
        log "✗ Docker buildx not available"
        return 1
    fi
    
    # Test as runner user if exists
    if id runner &>/dev/null 2>&1; then
        if su - runner -c "docker version" &>/dev/null 2>&1; then
            log "✓ Runner user can access Docker"
        else
            log "✗ Runner user cannot access Docker"
            return 1
        fi
    fi
    
    return 0
}

# Restart GitHub runner service
restart_runner_service() {
    log "Restarting GitHub runner services..."
    
    # Find all runner services
    local services=$(systemctl list-units --all --type=service | grep actions.runner | awk '{print $1}')
    
    if [ -z "$services" ]; then
        log "No GitHub runner services found"
        return
    fi
    
    for service in $services; do
        log "Restarting $service..."
        systemctl restart "$service"
    done
    
    # Wait a moment for services to stabilize
    sleep 5
    
    # Check service status
    for service in $services; do
        if systemctl is-active --quiet "$service"; then
            log "✓ $service is running"
        else
            log "✗ $service failed to start"
            systemctl status "$service" --no-pager
        fi
    done
}

# Main execution
main() {
    log "Starting Docker daemon fix for GitHub runner..."
    log "================================================"
    
    # Fix Docker daemon
    fix_docker_daemon
    
    # Fix permissions
    fix_docker_permissions
    
    # Setup buildx
    setup_docker_buildx
    
    # Verify everything works
    if verify_docker; then
        log "Docker is fully functional"
        
        # Restart runner services
        restart_runner_service
        
        log "================================================"
        log "Docker daemon fix completed successfully!"
    else
        log "================================================"
        log "Docker daemon fix completed with errors"
        log "Please check the logs above for details"
        exit 1
    fi
}

# Run with elevated privileges check
if [ "$EUID" -ne 0 ]; then
    log "ERROR: This script must be run as root"
    exit 1
fi

# Run main function
main