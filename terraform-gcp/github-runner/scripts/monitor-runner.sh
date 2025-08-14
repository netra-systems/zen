#!/bin/bash
# GitHub Runner Health Monitoring Script
# Continuously monitors runner health and automatically attempts fixes

set -euo pipefail

# Configuration
RUNNER_USER="${RUNNER_USER:-runner}"
RUNNER_HOME="/home/$RUNNER_USER"
RUNNER_DIR="$RUNNER_HOME/actions-runner"
MONITOR_LOG="/var/log/github-runner-monitor.log"
MONITOR_INTERVAL="${MONITOR_INTERVAL:-60}" # Check every 60 seconds
MAX_LOG_SIZE=$((10 * 1024 * 1024)) # 10MB max log size

# Metrics
FAILURES=0
CONSECUTIVE_FAILURES=0
MAX_CONSECUTIVE_FAILURES=5
LAST_DOCKER_FIX=0
DOCKER_FIX_COOLDOWN=300 # 5 minutes between Docker fix attempts

# Colors (for interactive mode)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# Logging
log() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo -e "$message" >> "$MONITOR_LOG"
    [[ "${VERBOSE:-false}" == "true" ]] && echo -e "$message"
}

success() {
    log "${GREEN}✓${NC} $1"
}

warning() {
    log "${YELLOW}⚠${NC} $1"
}

error() {
    log "${RED}✗${NC} $1"
    ((FAILURES++))
}

# Rotate log if too large
rotate_log() {
    if [[ -f "$MONITOR_LOG" ]] && [[ $(stat -c%s "$MONITOR_LOG") -gt $MAX_LOG_SIZE ]]; then
        mv "$MONITOR_LOG" "$MONITOR_LOG.old"
        log "Log rotated (exceeded ${MAX_LOG_SIZE} bytes)"
    fi
}

# Check system resources
check_resources() {
    local status="OK"
    
    # Memory check
    local mem_available=$(free -m | awk '/^Mem:/{print $7}')
    local mem_threshold=512 # MB
    
    if [[ $mem_available -lt $mem_threshold ]]; then
        warning "Low memory: ${mem_available}MB available (threshold: ${mem_threshold}MB)"
        status="WARNING"
        
        # Try to free memory
        sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
    fi
    
    # Disk space check
    local disk_usage=$(df / | awk 'NR==2 {print int($5)}')
    local disk_threshold=90 # percentage
    
    if [[ $disk_usage -gt $disk_threshold ]]; then
        warning "High disk usage: ${disk_usage}% (threshold: ${disk_threshold}%)"
        status="WARNING"
        
        # Clean Docker if installed
        if command -v docker &>/dev/null; then
            docker system prune -f 2>/dev/null || true
        fi
        
        # Clean apt cache
        apt-get clean 2>/dev/null || true
    fi
    
    # CPU load check
    local load_1min=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    local cpu_count=$(nproc)
    local load_threshold=$(echo "$cpu_count * 2" | bc)
    
    if (( $(echo "$load_1min > $load_threshold" | bc -l) )); then
        warning "High CPU load: ${load_1min} (threshold: ${load_threshold})"
        status="WARNING"
    fi
    
    echo "$status"
}

# Check Docker health
check_docker() {
    local status="OK"
    
    if ! command -v docker &>/dev/null; then
        # Docker not installed is not necessarily an error
        return 0
    fi
    
    # Check Docker service
    if ! systemctl is-active --quiet docker; then
        error "Docker service not running"
        status="FAILED"
        
        # Try to start Docker
        if systemctl start docker 2>/dev/null; then
            success "Docker service restarted"
            status="RECOVERED"
        fi
    fi
    
    # Check Docker daemon responsiveness
    if ! timeout 5 docker version &>/dev/null; then
        error "Docker daemon not responsive"
        status="FAILED"
    fi
    
    # Check runner Docker access
    if ! timeout 5 su - "$RUNNER_USER" -c "docker version" &>/dev/null 2>&1; then
        warning "Runner cannot access Docker"
        
        # Fix permissions if enough time has passed
        local current_time=$(date +%s)
        if [[ $((current_time - LAST_DOCKER_FIX)) -gt $DOCKER_FIX_COOLDOWN ]]; then
            log "Attempting to fix Docker permissions..."
            chmod 666 /var/run/docker.sock 2>/dev/null || true
            LAST_DOCKER_FIX=$current_time
            
            if su - "$RUNNER_USER" -c "docker version" &>/dev/null 2>&1; then
                success "Docker permissions fixed"
                status="RECOVERED"
            fi
        fi
    fi
    
    echo "$status"
}

# Check runner service
check_runner_service() {
    local status="OK"
    
    # Find runner service
    local service_name=$(systemctl list-units --all 2>/dev/null | grep -o "actions\.runner\..*\.service" | head -1)
    
    if [[ -z "$service_name" ]]; then
        error "No runner service found"
        return 1
    fi
    
    # Check if service is active
    if ! systemctl is-active --quiet "$service_name"; then
        error "Runner service not active: $service_name"
        status="FAILED"
        
        # Try to restart the service
        log "Attempting to restart runner service..."
        
        if systemctl restart "$service_name" 2>/dev/null; then
            sleep 5
            if systemctl is-active --quiet "$service_name"; then
                success "Runner service restarted successfully"
                status="RECOVERED"
            fi
        fi
    fi
    
    # Check for runner process
    if ! pgrep -f "Runner.Listener" >/dev/null; then
        error "Runner process not found"
        status="FAILED"
    fi
    
    echo "$status"
}

# Check GitHub connectivity
check_github_connectivity() {
    local status="OK"
    
    # Check GitHub API
    if ! curl -sSf --max-time 10 https://api.github.com >/dev/null 2>&1; then
        error "Cannot reach GitHub API"
        status="FAILED"
        
        # Check DNS
        if ! nslookup github.com >/dev/null 2>&1; then
            error "DNS resolution failure"
            
            # Try to fix DNS
            echo "nameserver 8.8.8.8" > /etc/resolv.conf.tmp
            echo "nameserver 8.8.4.4" >> /etc/resolv.conf.tmp
            cat /etc/resolv.conf >> /etc/resolv.conf.tmp
            mv /etc/resolv.conf.tmp /etc/resolv.conf
            
            if nslookup github.com >/dev/null 2>&1; then
                success "DNS fixed"
                status="RECOVERED"
            fi
        fi
    fi
    
    echo "$status"
}

# Send alert (can be customized)
send_alert() {
    local severity="$1"
    local message="$2"
    
    # Log the alert
    log "ALERT [$severity]: $message"
    
    # You can add additional alerting mechanisms here:
    # - Send email
    # - Post to Slack
    # - Write to monitoring system
    # - Trigger PagerDuty
    
    # Example: Write to a separate alert file
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$severity] $message" >> /var/log/github-runner-alerts.log
}

# Health check summary
perform_health_check() {
    local overall_status="HEALTHY"
    local issues=""
    
    # Check resources
    local resource_status=$(check_resources)
    [[ "$resource_status" != "OK" ]] && overall_status="DEGRADED"
    
    # Check Docker
    local docker_status=$(check_docker)
    if [[ "$docker_status" == "FAILED" ]]; then
        overall_status="DEGRADED"
        issues="$issues Docker"
    fi
    
    # Check runner service
    local runner_status=$(check_runner_service)
    if [[ "$runner_status" == "FAILED" ]]; then
        overall_status="UNHEALTHY"
        issues="$issues Runner"
        ((CONSECUTIVE_FAILURES++))
    else
        CONSECUTIVE_FAILURES=0
    fi
    
    # Check GitHub connectivity
    local github_status=$(check_github_connectivity)
    if [[ "$github_status" == "FAILED" ]]; then
        overall_status="DEGRADED"
        issues="$issues GitHub"
    fi
    
    # Handle consecutive failures
    if [[ $CONSECUTIVE_FAILURES -ge $MAX_CONSECUTIVE_FAILURES ]]; then
        send_alert "CRITICAL" "Runner has failed $CONSECUTIVE_FAILURES consecutive health checks"
        
        # Attempt recovery
        log "Attempting automatic recovery..."
        if [[ -f "/opt/github-runner/scripts/fix-runner-issues.sh" ]]; then
            /opt/github-runner/scripts/fix-runner-issues.sh 2>&1 | tail -20 >> "$MONITOR_LOG"
        fi
        
        CONSECUTIVE_FAILURES=0
    fi
    
    # Report status
    if [[ "$overall_status" == "HEALTHY" ]]; then
        [[ "${VERBOSE:-false}" == "true" ]] && success "Health check passed"
    elif [[ "$overall_status" == "DEGRADED" ]]; then
        warning "System degraded - Issues with:$issues"
    else
        error "System unhealthy - Critical issues with:$issues"
        send_alert "WARNING" "Runner health check failed - Issues:$issues"
    fi
    
    echo "$overall_status"
}

# Write metrics to file (for external monitoring)
write_metrics() {
    local status="$1"
    local metrics_file="/var/log/github-runner-metrics.json"
    
    cat > "$metrics_file" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "status": "$status",
  "failures": $FAILURES,
  "consecutive_failures": $CONSECUTIVE_FAILURES,
  "checks": {
    "resources": "$(check_resources)",
    "docker": "$(check_docker 2>/dev/null || echo 'N/A')",
    "runner": "$(check_runner_service 2>/dev/null || echo 'FAILED')",
    "github": "$(check_github_connectivity)"
  },
  "system": {
    "memory_available_mb": $(free -m | awk '/^Mem:/{print $7}'),
    "disk_usage_percent": $(df / | awk 'NR==2 {print int($5)}'),
    "load_average": "$(uptime | awk -F'load average:' '{print $2}' | xargs)",
    "uptime_seconds": $(awk '{print int($1)}' /proc/uptime)
  }
}
EOF
}

# Signal handlers
cleanup() {
    log "Monitor shutting down..."
    exit 0
}

trap cleanup SIGTERM SIGINT

# Main monitoring loop
main() {
    log "========================================="
    log "GitHub Runner Monitor Started"
    log "========================================="
    log "Monitor interval: ${MONITOR_INTERVAL}s"
    log "Verbose mode: ${VERBOSE:-false}"
    
    # Initial check
    perform_health_check
    
    while true; do
        sleep "$MONITOR_INTERVAL"
        
        # Rotate log if needed
        rotate_log
        
        # Perform health check
        status=$(perform_health_check)
        
        # Write metrics
        write_metrics "$status"
    done
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            export VERBOSE=true
            shift
            ;;
        -i|--interval)
            MONITOR_INTERVAL="$2"
            shift 2
            ;;
        -d|--daemon)
            # Run as daemon
            nohup "$0" ${VERBOSE:+-v} --interval "$MONITOR_INTERVAL" > /dev/null 2>&1 &
            echo "Monitor started as daemon (PID: $!)"
            exit 0
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -v, --verbose    Show verbose output"
            echo "  -i, --interval   Check interval in seconds (default: 60)"
            echo "  -d, --daemon     Run as background daemon"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if running as root
if [[ "$EUID" -ne 0 ]]; then
    error "This script must be run as root"
    exit 1
fi

# Run main loop
main