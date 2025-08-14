#!/bin/bash
set -euo pipefail

# Fix Docker daemon configuration
# This script ensures Docker is properly configured for GitHub Actions runners

LOG_FILE="/var/log/docker-fix.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

fix_docker_daemon() {
    log "Checking Docker daemon configuration..."
    
    # Ensure Docker daemon config directory exists
    mkdir -p /etc/docker
    
    # Create Docker daemon configuration if it doesn't exist
    if [[ ! -f /etc/docker/daemon.json ]]; then
        log "Creating Docker daemon configuration..."
        cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "userland-proxy": false
}
EOF
    else
        log "Docker daemon configuration already exists"
    fi
    
    # Restart Docker service
    if systemctl is-active --quiet docker; then
        log "Restarting Docker service..."
        systemctl restart docker
        sleep 5
    else
        log "Starting Docker service..."
        systemctl start docker
        systemctl enable docker
    fi
    
    # Verify Docker is running
    if docker info >/dev/null 2>&1; then
        log "Docker daemon is running successfully"
        return 0
    else
        log "ERROR: Docker daemon is not running properly"
        return 1
    fi
}

# Main execution
main() {
    log "Starting Docker daemon fix..."
    
    if fix_docker_daemon; then
        log "Docker daemon fix completed successfully"
        exit 0
    else
        log "Docker daemon fix failed"
        exit 1
    fi
}

main "$@"