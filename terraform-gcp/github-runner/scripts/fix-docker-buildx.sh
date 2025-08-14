#!/bin/bash
# Fix Docker buildx issues on GitHub runner instances

set -e

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

fix_docker_buildx() {
    local instance_name=$1
    
    if [ -z "$instance_name" ]; then
        echo "Usage: $0 <instance-name>"
        echo "Example: $0 gcp-runner-fixed-20250814-052047"
        exit 1
    fi
    
    log "Fixing Docker buildx on instance: $instance_name"
    
    # SSH into the instance and fix Docker buildx
    gcloud compute ssh "$instance_name" --zone=us-central1-a --command="
        echo '=== Fixing Docker buildx issues ==='
        
        # Stop any existing buildx builders
        docker buildx rm runner-builder 2>/dev/null || true
        docker buildx rm mybuilder 2>/dev/null || true
        
        # Clean up Docker buildx state
        rm -rf ~/.docker/buildx/instances/* 2>/dev/null || true
        sudo rm -rf /root/.docker/buildx/instances/* 2>/dev/null || true
        
        # Restart Docker to ensure clean state
        sudo systemctl restart docker
        sleep 5
        
        # Verify Docker is working
        if docker run --rm hello-world; then
            echo 'Docker is working correctly'
        else
            echo 'ERROR: Docker is not working'
            exit 1
        fi
        
        # Create new buildx builder with explicit driver
        docker buildx create --name runner-builder --driver docker-container --driver-opt network=host --use
        
        # Bootstrap the builder
        docker buildx inspect --bootstrap
        
        # Verify buildx is working
        if docker buildx ls | grep -q runner-builder; then
            echo 'Docker buildx is now configured correctly'
            docker buildx ls
        else
            echo 'ERROR: Docker buildx configuration failed'
            exit 1
        fi
        
        # Fix permissions for runner user
        sudo usermod -aG docker runner 2>/dev/null || true
        sudo chmod 666 /var/run/docker.sock
        
        # Setup buildx for runner user
        sudo su - runner -c 'docker buildx use runner-builder' || true
        
        # Restart GitHub runner service
        sudo systemctl restart 'actions.runner.*'
        
        echo '=== Docker buildx fix completed ==='
    "
    
    log "Docker buildx fix completed for $instance_name"
}

# Main execution
main() {
    fix_docker_buildx "$1"
}

main "$@"