#!/bin/bash

# Diagnostic script for GitHub runner issues
# Run this on an existing runner to diagnose and fix Docker issues

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root"
    exit 1
fi

log "GitHub Runner Diagnostic Tool"
log "=============================="

# 1. Check Docker installation
log "Checking Docker installation..."
if command -v docker &>/dev/null; then
    success "Docker is installed"
    docker --version
else
    error "Docker is not installed"
    echo "  Fix: apt-get update && apt-get install -y docker.io"
fi

# 2. Check Docker service
log "Checking Docker service..."
if systemctl is-active --quiet docker; then
    success "Docker service is running"
else
    error "Docker service is not running"
    echo "  Attempting to start Docker..."
    systemctl start docker
    if systemctl is-active --quiet docker; then
        success "Docker service started successfully"
    else
        error "Failed to start Docker service"
        systemctl status docker --no-pager
    fi
fi

# 3. Check Docker socket
log "Checking Docker socket..."
if [ -S /var/run/docker.sock ]; then
    success "Docker socket exists"
    ls -la /var/run/docker.sock
else
    error "Docker socket not found"
    echo "  This indicates Docker daemon is not running properly"
fi

# 4. Check Docker functionality
log "Checking Docker functionality..."
if docker version &>/dev/null; then
    success "Docker daemon is responsive"
else
    error "Docker daemon not responding"
    echo "  Checking Docker logs..."
    journalctl -xe -u docker --no-pager | tail -20
fi

# 5. Check buildx
log "Checking Docker buildx..."
if docker buildx version &>/dev/null; then
    success "Docker buildx is available"
    docker buildx ls
else
    warning "Docker buildx not available"
    echo "  Installing buildx..."
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -L "https://github.com/docker/buildx/releases/download/v0.11.2/buildx-v0.11.2.linux-amd64" \
        -o /usr/local/lib/docker/cli-plugins/docker-buildx
    chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
    if docker buildx version &>/dev/null; then
        success "Docker buildx installed successfully"
    fi
fi

# 6. Check runner user
log "Checking runner user..."
if id runner &>/dev/null; then
    success "Runner user exists"
    groups runner
else
    error "Runner user does not exist"
fi

# 7. Check runner Docker access
log "Checking runner's Docker access..."
if su - runner -c "docker version" &>/dev/null; then
    success "Runner user can access Docker"
else
    error "Runner user cannot access Docker"
    echo "  Fixing permissions..."
    usermod -aG docker runner
    systemctl restart docker
    sleep 3
    if su - runner -c "docker version" &>/dev/null; then
        success "Fixed Docker access for runner user"
    else
        error "Still cannot fix Docker access"
        echo "  This may require a system reboot"
    fi
fi

# 8. Check GitHub runner service
log "Checking GitHub runner service..."
runner_services=$(systemctl list-units --all --type=service | grep actions.runner | awk '{print $1}')
if [ -z "$runner_services" ]; then
    error "No GitHub runner services found"
else
    for service in $runner_services; do
        if systemctl is-active --quiet "$service"; then
            success "$service is running"
        else
            error "$service is not running"
            echo "  Attempting to restart..."
            systemctl restart "$service"
            if systemctl is-active --quiet "$service"; then
                success "$service restarted successfully"
            else
                error "Failed to restart $service"
            fi
        fi
    done
fi

# 9. Check runner configuration
log "Checking runner configuration..."
if [ -d /home/runner/actions-runner ]; then
    success "Runner directory exists"
    if [ -f /home/runner/actions-runner/.runner ]; then
        success "Runner is configured"
        echo "  Runner name: $(jq -r .agentName /home/runner/actions-runner/.runner)"
    else
        error "Runner is not configured"
    fi
else
    error "Runner directory not found"
fi

# 10. Network connectivity
log "Checking network connectivity..."
if curl -s https://api.github.com > /dev/null; then
    success "Can reach GitHub API"
else
    error "Cannot reach GitHub API"
fi

# Summary
log ""
log "=============================="
log "Diagnostic Summary:"

# Count successes and failures
total_checks=0
failed_checks=0

# Recheck all critical components
critical_checks=(
    "docker version"
    "docker buildx version"
    "su - runner -c 'docker version'"
    "systemctl is-active actions.runner.*"
)

for check in "${critical_checks[@]}"; do
    total_checks=$((total_checks + 1))
    if eval $check &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $check"
    else
        echo -e "  ${RED}✗${NC} $check"
        failed_checks=$((failed_checks + 1))
    fi
done

if [ $failed_checks -eq 0 ]; then
    success "All critical checks passed!"
else
    error "$failed_checks out of $total_checks critical checks failed"
    echo ""
    echo "To fix remaining issues, you can:"
    echo "  1. Run: bash /tmp/fix-docker-daemon.sh"
    echo "  2. Reboot the instance"
    echo "  3. Re-run the installation script"
fi