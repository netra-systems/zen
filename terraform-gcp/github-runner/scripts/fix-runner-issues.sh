#!/bin/bash
# Quick Fix Script for GitHub Runner Issues
# This script attempts to fix common problems with GitHub runners

set -euo pipefail

# Configuration
RUNNER_USER="${RUNNER_USER:-runner}"
RUNNER_HOME="/home/$RUNNER_USER"
RUNNER_DIR="$RUNNER_HOME/actions-runner"
FIX_LOG="/var/log/github-runner-fix-$(date +%Y%m%d-%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging
exec > >(tee -a "$FIX_LOG") 2>&1

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

success() {
    log "${GREEN}✓${NC} $1"
}

warning() {
    log "${YELLOW}⚠${NC} $1"
}

error() {
    log "${RED}✗${NC} $1"
}

# Check root
if [[ "$EUID" -ne 0 ]]; then
    error "This script must be run as root"
    echo "Please run: sudo $0"
    exit 1
fi

log "========================================="
log "GitHub Runner Issue Fixer"
log "========================================="

# Fix 1: Docker Permissions
fix_docker_permissions() {
    log "\n=== Fixing Docker Permissions ==="
    
    if ! command -v docker &>/dev/null; then
        warning "Docker not installed, skipping..."
        return
    fi
    
    # Ensure docker group exists
    if ! getent group docker >/dev/null; then
        log "Creating docker group..."
        groupadd docker
    fi
    
    # Add runner to docker group
    if id "$RUNNER_USER" &>/dev/null; then
        log "Adding $RUNNER_USER to docker group..."
        usermod -aG docker "$RUNNER_USER"
        success "User added to docker group"
    fi
    
    # Fix socket permissions
    if [[ -S /var/run/docker.sock ]]; then
        log "Setting Docker socket permissions..."
        chmod 666 /var/run/docker.sock
        chown root:docker /var/run/docker.sock 2>/dev/null || true
        success "Docker socket permissions fixed"
    fi
    
    # Restart Docker to apply changes
    log "Restarting Docker service..."
    systemctl daemon-reload
    
    # Stop Docker cleanly
    systemctl stop docker || true
    sleep 2
    
    # Clean stale files
    rm -f /var/run/docker.pid /var/run/docker.sock 2>/dev/null || true
    
    # Start Docker
    if systemctl start docker; then
        success "Docker service restarted"
        
        # Verify it works
        sleep 3
        if docker version &>/dev/null; then
            success "Docker is working"
            
            # Test runner access
            if su - "$RUNNER_USER" -c "docker version" &>/dev/null; then
                success "Runner can access Docker"
            else
                warning "Runner still cannot access Docker (may need logout/login)"
            fi
        else
            error "Docker still not working properly"
        fi
    else
        error "Failed to start Docker"
    fi
}

# Fix 2: Runner Service
fix_runner_service() {
    log "\n=== Fixing Runner Service ==="
    
    # Find the service
    local service_name=$(systemctl list-units --all | grep -o "actions\.runner\..*\.service" | head -1)
    
    if [[ -z "$service_name" ]]; then
        warning "No runner service found"
        
        # Try to reinstall service
        if [[ -f "$RUNNER_DIR/svc.sh" ]]; then
            log "Attempting to install runner service..."
            cd "$RUNNER_DIR"
            ./svc.sh stop 2>/dev/null || true
            ./svc.sh uninstall 2>/dev/null || true
            
            if ./svc.sh install "$RUNNER_USER"; then
                ./svc.sh start
                success "Runner service reinstalled"
            else
                error "Failed to install runner service"
            fi
        else
            error "Runner not properly installed at $RUNNER_DIR"
        fi
    else
        log "Found service: $service_name"
        
        # Stop the service
        log "Stopping runner service..."
        systemctl stop "$service_name" || true
        
        # Clear any failed state
        systemctl reset-failed "$service_name" 2>/dev/null || true
        
        # Start the service
        log "Starting runner service..."
        if systemctl start "$service_name"; then
            success "Runner service started"
            systemctl enable "$service_name"
        else
            error "Failed to start runner service"
            log "Service logs:"
            journalctl -u "$service_name" -n 20 --no-pager
        fi
    fi
}

# Fix 3: File Permissions
fix_file_permissions() {
    log "\n=== Fixing File Permissions ==="
    
    if [[ -d "$RUNNER_HOME" ]]; then
        log "Fixing ownership of runner home directory..."
        chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_HOME"
        success "Runner home directory ownership fixed"
    fi
    
    # Fix log permissions
    if [[ -d "$RUNNER_DIR/_diag" ]]; then
        chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR/_diag"
        success "Log directory permissions fixed"
    fi
    
    # Ensure runner can write to temp
    if [[ -d "$RUNNER_DIR/_work" ]]; then
        chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR/_work"
        chmod -R 755 "$RUNNER_DIR/_work"
        success "Work directory permissions fixed"
    fi
}

# Fix 4: Network Issues
fix_network_issues() {
    log "\n=== Checking Network Configuration ==="
    
    # Test GitHub connectivity
    if ! curl -sSf https://api.github.com >/dev/null 2>&1; then
        error "Cannot reach GitHub API"
        
        # Try to fix DNS
        log "Attempting to fix DNS..."
        echo "nameserver 8.8.8.8" >> /etc/resolv.conf
        echo "nameserver 8.8.4.4" >> /etc/resolv.conf
        
        if curl -sSf https://api.github.com >/dev/null 2>&1; then
            success "DNS fix applied"
        else
            error "Still cannot reach GitHub"
        fi
    else
        success "Network connectivity OK"
    fi
}

# Fix 5: Clean and Reinstall (last resort)
clean_reinstall() {
    log "\n=== Clean Reinstall Option ==="
    warning "This will remove and reinstall the runner configuration"
    
    read -p "Do you want to proceed with clean reinstall? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Clean reinstall skipped"
        return
    fi
    
    # Stop service
    local service_name=$(systemctl list-units --all | grep -o "actions\.runner\..*\.service" | head -1)
    if [[ -n "$service_name" ]]; then
        systemctl stop "$service_name"
        cd "$RUNNER_DIR" && ./svc.sh uninstall 2>/dev/null || true
    fi
    
    # Remove runner
    if [[ -f "$RUNNER_DIR/config.sh" ]]; then
        log "Removing runner configuration..."
        cd "$RUNNER_DIR"
        
        # Get token from environment or prompt
        if [[ -z "${GITHUB_TOKEN:-}" ]]; then
            read -p "Enter GitHub PAT token: " -s GITHUB_TOKEN
            echo
        fi
        
        # Try to remove runner registration
        ./config.sh remove --token "$GITHUB_TOKEN" 2>/dev/null || true
    fi
    
    log "Please re-run the installation script to complete setup"
}

# Fix 6: Install Missing Dependencies
fix_dependencies() {
    log "\n=== Checking Dependencies ==="
    
    local missing_deps=""
    
    # Check essential commands
    for cmd in curl jq git; do
        if ! command -v $cmd &>/dev/null; then
            missing_deps="$missing_deps $cmd"
        fi
    done
    
    if [[ -n "$missing_deps" ]]; then
        log "Installing missing dependencies:$missing_deps"
        apt-get update
        apt-get install -y $missing_deps
        success "Dependencies installed"
    else
        success "All essential dependencies present"
    fi
}

# Fix 7: Docker Buildx Setup
fix_docker_buildx() {
    log "\n=== Setting up Docker Buildx ==="
    
    if ! command -v docker &>/dev/null; then
        warning "Docker not installed, skipping buildx setup"
        return
    fi
    
    # Install buildx plugin
    local buildx_dir="/usr/local/lib/docker/cli-plugins"
    
    if [[ ! -f "$buildx_dir/docker-buildx" ]]; then
        log "Installing Docker buildx plugin..."
        mkdir -p "$buildx_dir"
        
        local buildx_version="0.11.2"
        if curl -fsSL "https://github.com/docker/buildx/releases/download/v${buildx_version}/buildx-v${buildx_version}.linux-amd64" \
            -o "$buildx_dir/docker-buildx"; then
            chmod +x "$buildx_dir/docker-buildx"
            success "Buildx plugin installed"
        else
            error "Failed to download buildx"
            return
        fi
    fi
    
    # Setup for runner user
    if id "$RUNNER_USER" &>/dev/null && [[ -d "$RUNNER_HOME" ]]; then
        local runner_docker_dir="$RUNNER_HOME/.docker/cli-plugins"
        su - "$RUNNER_USER" -c "mkdir -p '$runner_docker_dir'"
        cp "$buildx_dir/docker-buildx" "$runner_docker_dir/" 2>/dev/null || true
        chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_HOME/.docker" 2>/dev/null || true
        
        # Create buildx builder
        if su - "$RUNNER_USER" -c "docker buildx create --name runner-builder --driver docker-container --use" 2>/dev/null; then
            success "Buildx builder created for runner"
        else
            warning "Could not create buildx builder (may already exist)"
        fi
    fi
}

# Main execution
main() {
    # Run all fixes
    fix_dependencies
    fix_docker_permissions
    fix_file_permissions
    fix_docker_buildx
    fix_network_issues
    fix_runner_service
    
    log "\n========================================="
    log "Fix Script Complete"
    log "========================================="
    
    # Final status check
    log "\nFinal Status Check:"
    
    # Check Docker
    if command -v docker &>/dev/null && docker version &>/dev/null; then
        success "Docker: Working"
        
        if su - "$RUNNER_USER" -c "docker version" &>/dev/null 2>&1; then
            success "Docker (runner): Accessible"
        else
            warning "Docker (runner): Not accessible (may need re-login)"
        fi
    else
        warning "Docker: Not working or not installed"
    fi
    
    # Check runner service
    local service_name=$(systemctl list-units --all | grep -o "actions\.runner\..*\.service" | head -1)
    if [[ -n "$service_name" ]] && systemctl is-active --quiet "$service_name"; then
        success "Runner Service: Active"
    else
        warning "Runner Service: Not active"
    fi
    
    log "\n========================================="
    log "Fixes applied. Log saved to: $FIX_LOG"
    log ""
    log "If issues persist:"
    log "1. Check the diagnostic script: ./diagnose-runner.sh"
    log "2. Review logs in: $RUNNER_DIR/_diag/"
    log "3. Consider clean reinstall (run this script again and choose option)"
    log "========================================="
}

# Handle Ctrl+C
trap 'echo -e "\n${YELLOW}Script interrupted${NC}"; exit 130' INT

# Run main
main "$@"