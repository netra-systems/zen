#!/bin/bash
# GitHub Runner Diagnostic Script
# This script helps diagnose common issues with GitHub runners

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
RUNNER_USER="${RUNNER_USER:-runner}"
RUNNER_HOME="/home/$RUNNER_USER"
RUNNER_DIR="$RUNNER_HOME/actions-runner"
DIAG_LOG="/tmp/runner-diagnosis-$(date +%Y%m%d-%H%M%S).log"

# Logging
log() {
    echo -e "$1" | tee -a "$DIAG_LOG"
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

header() {
    log "\n${GREEN}═══ $1 ═══${NC}"
}

# Check if running as root
check_root() {
    if [[ "$EUID" -eq 0 ]]; then
        return 0
    else
        return 1
    fi
}

# System Information
diagnose_system() {
    header "System Information"
    
    log "Hostname: $(hostname)"
    log "OS: $(lsb_release -d 2>/dev/null | cut -f2 || cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
    log "Kernel: $(uname -r)"
    log "Architecture: $(uname -m)"
    log "CPUs: $(nproc)"
    log "Memory: $(free -h | grep Mem: | awk '{print $2}')"
    log "Disk Space:"
    df -h / | tail -1
}

# Resource Check
diagnose_resources() {
    header "Resource Status"
    
    # Memory check
    local mem_available=$(free -m | awk '/^Mem:/{print $7}')
    if [[ $mem_available -lt 1024 ]]; then
        warning "Low memory available: ${mem_available}MB (recommended: >1GB)"
    else
        success "Memory available: ${mem_available}MB"
    fi
    
    # Disk check
    local disk_available=$(df / | awk 'NR==2 {print int($4/1024/1024)}')
    if [[ $disk_available -lt 5 ]]; then
        warning "Low disk space: ${disk_available}GB (recommended: >5GB)"
    else
        success "Disk space available: ${disk_available}GB"
    fi
    
    # CPU load
    local load_avg=$(uptime | awk -F'load average:' '{print $2}')
    log "Load average:$load_avg"
}

# Network Connectivity
diagnose_network() {
    header "Network Connectivity"
    
    # Check DNS
    if nslookup github.com >/dev/null 2>&1; then
        success "DNS resolution working"
    else
        error "DNS resolution failed"
    fi
    
    # Check GitHub API
    if curl -sSf https://api.github.com >/dev/null 2>&1; then
        success "GitHub API accessible"
    else
        error "Cannot reach GitHub API"
    fi
    
    # Check Docker Hub (if Docker installed)
    if command -v docker &>/dev/null; then
        if curl -sSf https://hub.docker.com >/dev/null 2>&1; then
            success "Docker Hub accessible"
        else
            warning "Cannot reach Docker Hub"
        fi
    fi
}

# GitHub Runner User
diagnose_runner_user() {
    header "Runner User Configuration"
    
    if id "$RUNNER_USER" &>/dev/null; then
        success "Runner user '$RUNNER_USER' exists"
        log "User info: $(id $RUNNER_USER)"
        
        # Check home directory
        if [[ -d "$RUNNER_HOME" ]]; then
            success "Runner home directory exists: $RUNNER_HOME"
        else
            error "Runner home directory missing: $RUNNER_HOME"
        fi
        
        # Check runner directory
        if [[ -d "$RUNNER_DIR" ]]; then
            success "Runner directory exists: $RUNNER_DIR"
            
            # Check runner configuration
            if [[ -f "$RUNNER_DIR/.runner" ]]; then
                success "Runner is configured"
                log "Runner name: $(jq -r .agentName $RUNNER_DIR/.runner 2>/dev/null || echo 'Unknown')"
            else
                warning "Runner not configured (missing .runner file)"
            fi
        else
            error "Runner directory missing: $RUNNER_DIR"
        fi
    else
        error "Runner user '$RUNNER_USER' does not exist"
    fi
}

# Docker Diagnostics
diagnose_docker() {
    header "Docker Configuration"
    
    # Check if Docker is installed
    if ! command -v docker &>/dev/null; then
        warning "Docker is not installed"
        return
    fi
    
    success "Docker is installed"
    
    # Check Docker service
    if systemctl is-active --quiet docker; then
        success "Docker service is active"
    else
        error "Docker service is not running"
        log "Docker service status:"
        systemctl status docker --no-pager 2>&1 | head -10 || true
    fi
    
    # Check Docker socket
    if [[ -S /var/run/docker.sock ]]; then
        success "Docker socket exists"
        local socket_perms=$(stat -c %a /var/run/docker.sock)
        log "Socket permissions: $socket_perms"
        
        if [[ "$socket_perms" == "666" ]] || [[ "$socket_perms" == "660" ]]; then
            success "Docker socket permissions look correct"
        else
            warning "Docker socket permissions may be restrictive: $socket_perms"
        fi
    else
        error "Docker socket not found"
    fi
    
    # Check if runner user can access Docker
    if id "$RUNNER_USER" &>/dev/null; then
        if groups "$RUNNER_USER" | grep -q docker; then
            success "Runner user is in docker group"
        else
            warning "Runner user is not in docker group"
        fi
        
        # Test actual Docker access
        if su - "$RUNNER_USER" -c "docker version" &>/dev/null 2>&1; then
            success "Runner user can execute Docker commands"
            
            # Check buildx
            if su - "$RUNNER_USER" -c "docker buildx version" &>/dev/null 2>&1; then
                success "Docker buildx is available"
            else
                warning "Docker buildx not available"
            fi
        else
            error "Runner user cannot execute Docker commands"
            log "Attempting Docker command as runner user:"
            su - "$RUNNER_USER" -c "docker version" 2>&1 | head -10 || true
        fi
    fi
    
    # Docker daemon info
    if docker info &>/dev/null 2>&1; then
        log "Docker daemon info:"
        docker info 2>&1 | grep -E "Server Version|Storage Driver|Cgroup Driver" || true
    fi
}

# GitHub Runner Service
diagnose_runner_service() {
    header "Runner Service Status"
    
    # Find runner service
    local service_name=$(systemctl list-units --all | grep -o "actions\.runner\..*\.service" | head -1)
    
    if [[ -n "$service_name" ]]; then
        success "Runner service found: $service_name"
        
        if systemctl is-active --quiet "$service_name"; then
            success "Runner service is active"
        else
            error "Runner service is not active"
        fi
        
        log "Service status:"
        systemctl status "$service_name" --no-pager 2>&1 | head -15 || true
        
        # Check recent logs
        log "\nRecent service logs:"
        journalctl -u "$service_name" -n 20 --no-pager 2>&1 || true
    else
        error "No runner service found"
    fi
    
    # Check for runner processes
    if pgrep -f "Runner.Listener" >/dev/null; then
        success "Runner process is running"
        log "Runner process info:"
        ps aux | grep -E "Runner.Listener|Runner.Worker" | grep -v grep || true
    else
        warning "No runner process found"
    fi
}

# Secret Manager Access (for GCP)
diagnose_secret_manager() {
    header "Secret Manager Access (GCP)"
    
    if ! command -v gcloud &>/dev/null; then
        warning "gcloud CLI not installed"
        return
    fi
    
    # Get project ID
    local project_id=$(gcloud config get-value project 2>/dev/null)
    
    if [[ -z "$project_id" ]]; then
        warning "No GCP project configured"
        return
    fi
    
    log "Project ID: $project_id"
    
    # Check service account
    local service_account=$(gcloud config get-value account 2>/dev/null)
    if [[ -n "$service_account" ]]; then
        success "Service account: $service_account"
    else
        error "No service account configured"
    fi
    
    # Check secret access
    if gcloud secrets describe "github-runner-token" --project="$project_id" &>/dev/null; then
        success "GitHub runner token secret exists"
        
        # Try to access it
        if gcloud secrets versions access latest --secret="github-runner-token" --project="$project_id" &>/dev/null; then
            success "Can access GitHub runner token"
        else
            error "Cannot access GitHub runner token"
        fi
    else
        error "GitHub runner token secret not found"
    fi
}

# Check logs
diagnose_logs() {
    header "Log Files"
    
    # System logs
    log "Recent system logs related to runner:"
    journalctl -n 50 | grep -i runner | tail -10 2>/dev/null || true
    
    # Runner logs
    if [[ -d "$RUNNER_DIR/_diag" ]]; then
        log "\nRunner diagnostic logs available in: $RUNNER_DIR/_diag"
        log "Recent runner logs:"
        ls -lt "$RUNNER_DIR/_diag/" 2>/dev/null | head -5 || true
    else
        warning "No runner diagnostic directory found"
    fi
    
    # Installation logs
    if [[ -f "/var/log/github-runner-install.log" ]]; then
        log "\nLast 20 lines of installation log:"
        tail -20 /var/log/github-runner-install.log 2>/dev/null || true
    fi
    
    if [[ -f "/var/log/github-runner-errors.log" ]]; then
        log "\nRecent errors:"
        tail -10 /var/log/github-runner-errors.log 2>/dev/null || true
    fi
}

# Recommendations
provide_recommendations() {
    header "Recommendations"
    
    local has_issues=false
    
    # Check if Docker is accessible
    if command -v docker &>/dev/null; then
        if ! su - "$RUNNER_USER" -c "docker version" &>/dev/null 2>&1; then
            has_issues=true
            log "\nTo fix Docker access for runner:"
            log "  sudo usermod -aG docker $RUNNER_USER"
            log "  sudo chmod 666 /var/run/docker.sock"
            log "  sudo systemctl restart docker"
        fi
    fi
    
    # Check if runner service is running
    local service_name=$(systemctl list-units --all | grep -o "actions\.runner\..*\.service" | head -1)
    if [[ -n "$service_name" ]] && ! systemctl is-active --quiet "$service_name"; then
        has_issues=true
        log "\nTo start the runner service:"
        log "  sudo systemctl start $service_name"
        log "  sudo systemctl enable $service_name"
    fi
    
    # Check resources
    local mem_available=$(free -m | awk '/^Mem:/{print $7}')
    if [[ $mem_available -lt 1024 ]]; then
        has_issues=true
        log "\nLow memory detected. Consider:"
        log "  - Stopping unnecessary services"
        log "  - Increasing instance size"
    fi
    
    if [[ "$has_issues" == "false" ]]; then
        success "\nNo major issues detected!"
    fi
}

# Main execution
main() {
    log "GitHub Runner Diagnostics"
    log "========================="
    log "Timestamp: $(date)"
    log "Running as: $(whoami)"
    
    if ! check_root; then
        warning "Not running as root. Some checks may be limited."
        log "For full diagnostics, run: sudo $0"
    fi
    
    diagnose_system
    diagnose_resources
    diagnose_network
    diagnose_runner_user
    diagnose_docker
    diagnose_runner_service
    diagnose_secret_manager
    diagnose_logs
    provide_recommendations
    
    log "\n========================="
    log "Diagnostics complete!"
    log "Full report saved to: $DIAG_LOG"
    log "========================="
}

# Run diagnostics
main "$@"