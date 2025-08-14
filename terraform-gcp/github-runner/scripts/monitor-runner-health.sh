#!/bin/bash
# GitHub Runner Health Monitor with Auto-Recovery
# Continuously monitors runner health and triggers recovery when needed

set -euo pipefail

# Configuration
CHECK_INTERVAL=60  # Check every 60 seconds
FAILURE_THRESHOLD=3  # Trigger recovery after 3 consecutive failures
SCRIPTS_DIR="/opt/github-runner/scripts"
LOG_FILE="/var/log/github-runner-monitor.log"
RUNNER_DIR="/home/runner/actions-runner"

# Redirect output to log
exec > >(tee -a "$LOG_FILE") 2>&1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Health check function
check_runner_health() {
    local healthy=true
    local issues=""
    
    # Check 1: Runner user exists
    if ! id runner &>/dev/null; then
        healthy=false
        issues="$issues\n  - Runner user missing"
    fi
    
    # Check 2: Runner service is active
    local service_name=$(systemctl list-units --all 2>/dev/null | grep -o "actions\.runner\..*\.service" | head -1 || true)
    if [[ -n "$service_name" ]]; then
        if ! systemctl is-active --quiet "$service_name"; then
            healthy=false
            issues="$issues\n  - Runner service not active: $service_name"
        fi
    else
        # Check if runner is configured but service not installed
        if [[ -f "$RUNNER_DIR/.runner" ]]; then
            healthy=false
            issues="$issues\n  - Runner configured but service not installed"
        fi
    fi
    
    # Check 3: Can access GitHub API
    if ! curl -sSf --max-time 10 https://api.github.com >/dev/null 2>&1; then
        healthy=false
        issues="$issues\n  - Cannot reach GitHub API"
    fi
    
    # Check 4: Secret Manager access (if gcloud available)
    if command -v gcloud &>/dev/null; then
        local project_id=$(curl -s -H "Metadata-Flavor: Google" \
            "http://metadata.google.internal/computeMetadata/v1/project/project-id" 2>/dev/null || echo "")
        
        if [[ -n "$project_id" ]]; then
            if ! gcloud secrets describe "github-runner-token" --project="$project_id" &>/dev/null 2>&1; then
                healthy=false
                issues="$issues\n  - Cannot access Secret Manager"
            fi
        fi
    fi
    
    # Check 5: Docker (if installed)
    if command -v docker &>/dev/null; then
        if ! docker version &>/dev/null 2>&1; then
            # Try to fix Docker automatically
            log "Docker not responding, attempting quick fix..."
            chmod 666 /var/run/docker.sock 2>/dev/null || true
            systemctl restart docker 2>/dev/null || true
            sleep 5
            
            # Re-check
            if ! docker version &>/dev/null 2>&1; then
                healthy=false
                issues="$issues\n  - Docker daemon not responding"
            fi
        fi
    fi
    
    if [[ "$healthy" == "false" ]]; then
        echo "$issues"
        return 1
    fi
    
    return 0
}

# Recovery trigger function
trigger_recovery() {
    local reason="$1"
    
    log "ALERT: Triggering auto-recovery due to health check failures:"
    log "$reason"
    
    # Run auto-recovery script
    if [[ -x "$SCRIPTS_DIR/auto-recovery.sh" ]]; then
        log "Executing auto-recovery script..."
        "$SCRIPTS_DIR/auto-recovery.sh" || {
            log "ERROR: Auto-recovery failed"
            
            # Send alert if possible
            if command -v gcloud &>/dev/null; then
                local project_id=$(curl -s -H "Metadata-Flavor: Google" \
                    "http://metadata.google.internal/computeMetadata/v1/project/project-id" 2>/dev/null || echo "")
                
                if [[ -n "$project_id" ]]; then
                    gcloud logging write github-runner-alert \
                        "GitHub runner auto-recovery failed on $(hostname): $reason" \
                        --severity=CRITICAL \
                        --project="$project_id" 2>/dev/null || true
                fi
            fi
        }
    else
        log "ERROR: Auto-recovery script not found at $SCRIPTS_DIR/auto-recovery.sh"
    fi
}

# Quick fix function for minor issues
quick_fix() {
    local issue="$1"
    
    case "$issue" in
        *"Docker daemon"*)
            log "Attempting Docker quick fix..."
            systemctl stop docker 2>/dev/null || true
            rm -f /var/run/docker.sock /var/run/docker.pid 2>/dev/null || true
            systemctl start docker 2>/dev/null || true
            chmod 666 /var/run/docker.sock 2>/dev/null || true
            ;;
            
        *"service not active"*)
            log "Attempting service restart..."
            local service_name=$(systemctl list-units --all 2>/dev/null | grep -o "actions\.runner\..*\.service" | head -1 || true)
            if [[ -n "$service_name" ]]; then
                systemctl restart "$service_name" 2>/dev/null || true
            fi
            ;;
    esac
}

# Main monitoring loop
main() {
    log "========================================="
    log "GitHub Runner Health Monitor Started"
    log "========================================="
    log "Check interval: ${CHECK_INTERVAL}s"
    log "Failure threshold: $FAILURE_THRESHOLD consecutive failures"
    
    local consecutive_failures=0
    local last_status="unknown"
    
    while true; do
        if issues=$(check_runner_health 2>&1); then
            if [[ "$last_status" != "healthy" ]]; then
                log "✓ Runner is healthy"
                last_status="healthy"
            fi
            consecutive_failures=0
        else
            consecutive_failures=$((consecutive_failures + 1))
            log "✗ Health check failed ($consecutive_failures/$FAILURE_THRESHOLD):"
            log "$issues"
            
            # Try quick fixes for minor issues
            if [[ $consecutive_failures -eq 1 ]]; then
                quick_fix "$issues"
            fi
            
            # Trigger recovery if threshold reached
            if [[ $consecutive_failures -ge $FAILURE_THRESHOLD ]]; then
                trigger_recovery "$issues"
                # Reset counter after recovery attempt
                consecutive_failures=0
                # Wait longer after recovery
                sleep 300
            fi
            
            last_status="unhealthy"
        fi
        
        sleep "$CHECK_INTERVAL"
    done
}

# Handle signals gracefully
trap 'log "Monitor shutting down..."; exit 0' SIGTERM SIGINT

# Run main monitoring loop
main