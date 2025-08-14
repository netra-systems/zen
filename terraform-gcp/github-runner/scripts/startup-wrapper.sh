#!/bin/bash
set -e

# Wrapper script for GitHub runner startup
# This ensures Docker is properly initialized before starting the runner

LOG_FILE="/var/log/github-runner-startup.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting GitHub runner initialization..."

# First, run the main installation script
log "Running main installation script..."
bash /tmp/install-runner.sh

# Then, ensure Docker is properly configured
log "Ensuring Docker daemon is properly configured..."
bash /tmp/fix-docker-daemon.sh

# Additional verification
log "Final verification of Docker setup..."
if docker version &>/dev/null && docker buildx version &>/dev/null; then
    log "✓ Docker and buildx are fully functional"
    
    # Test as runner user
    if su - runner -c "docker version" &>/dev/null; then
        log "✓ Runner user can access Docker"
    else
        log "⚠ Warning: Runner user cannot access Docker, attempting final fix..."
        usermod -aG docker runner
        systemctl restart docker
        sleep 5
        systemctl restart actions.runner.* || true
    fi
else
    log "✗ Docker setup verification failed"
    exit 1
fi

log "GitHub runner startup completed successfully!"