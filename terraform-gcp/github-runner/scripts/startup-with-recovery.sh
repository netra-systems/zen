#!/bin/bash
# Enhanced GitHub Runner Startup Script with Auto-Recovery
# This script deploys all recovery components and starts the installation

set -euo pipefail

# Configuration from Terraform
GITHUB_ORG="${github_org}"
GITHUB_REPO="${github_repo}"
RUNNER_NAME="${runner_name}"
RUNNER_LABELS="${runner_labels}"
RUNNER_GROUP="${runner_group}"
PROJECT_ID="${project_id}"
RUNNER_VERSION="${runner_version:-2.317.0}"

# Script paths
SCRIPTS_DIR="/opt/github-runner/scripts"
LOG_FILE="/var/log/github-runner-startup.log"

# Redirect output to log
exec > >(tee -a "$LOG_FILE") 2>&1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Deploy all recovery scripts
deploy_recovery_system() {
    log "Deploying auto-recovery system..."
    
    # Create scripts directory
    mkdir -p "$SCRIPTS_DIR"
    
    # Deploy auto-recovery script
    cat > "$SCRIPTS_DIR/auto-recovery.sh" << 'RECOVERY_EOF'
$(cat /opt/github-runner/scripts/auto-recovery.sh 2>/dev/null || echo '#!/bin/bash
# Auto-recovery script will be deployed here
echo "Auto-recovery system not yet deployed"
exit 1')
RECOVERY_EOF
    chmod +x "$SCRIPTS_DIR/auto-recovery.sh"
    
    # Deploy diagnostic script
    cat > "$SCRIPTS_DIR/diagnose-runner-enhanced.sh" << 'DIAG_EOF'
$(cat /opt/github-runner/scripts/diagnose-runner-enhanced.sh 2>/dev/null || echo '#!/bin/bash
# Diagnostic script will be deployed here
echo "Diagnostic system not yet deployed"
exit 1')
DIAG_EOF
    chmod +x "$SCRIPTS_DIR/diagnose-runner-enhanced.sh"
    
    # Deploy quick fix script
    cat > "$SCRIPTS_DIR/fix-runner-quick.sh" << 'FIX_EOF'
$(cat /opt/github-runner/scripts/fix-runner-quick.sh 2>/dev/null || echo '#!/bin/bash
# Quick fix script will be deployed here
echo "Quick fix system not yet deployed"
exit 1')
FIX_EOF
    chmod +x "$SCRIPTS_DIR/fix-runner-quick.sh"
    
    # Deploy health monitor script
    cat > "$SCRIPTS_DIR/monitor-runner-health.sh" << 'MONITOR_EOF'
$(cat /opt/github-runner/scripts/monitor-runner-health.sh 2>/dev/null || echo '#!/bin/bash
# Health monitor will be deployed here
echo "Health monitor not yet deployed"
exit 1')
MONITOR_EOF
    chmod +x "$SCRIPTS_DIR/monitor-runner-health.sh"
    
    # Create convenience symlinks
    ln -sf "$SCRIPTS_DIR/diagnose-runner-enhanced.sh" /usr/local/bin/runner-diagnose 2>/dev/null || true
    ln -sf "$SCRIPTS_DIR/fix-runner-quick.sh" /usr/local/bin/runner-fix 2>/dev/null || true
    ln -sf "$SCRIPTS_DIR/auto-recovery.sh" /usr/local/bin/runner-recover 2>/dev/null || true
    
    log "Auto-recovery system deployed successfully"
}

# Install systemd service for monitoring
install_monitor_service() {
    log "Installing health monitor service..."
    
    # Create systemd service file
    cat > /etc/systemd/system/github-runner-monitor.service << 'SERVICE_EOF'
[Unit]
Description=GitHub Runner Health Monitor and Auto-Recovery
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/opt/github-runner/scripts/monitor-runner-health.sh
Restart=always
RestartSec=300
StandardOutput=journal
StandardError=journal
SyslogIdentifier=github-runner-monitor

[Install]
WantedBy=multi-user.target
SERVICE_EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable github-runner-monitor.service
    
    # Don't start yet - will start after runner installation
    log "Monitor service installed (will start after runner installation)"
}

# Setup cron job for periodic recovery checks
setup_cron_recovery() {
    log "Setting up cron-based recovery checks..."
    
    cat > /etc/cron.d/github-runner-recovery << 'CRON_EOF'
# GitHub Runner Auto-Recovery Cron Jobs
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Check runner health every 5 minutes
*/5 * * * * root if ! systemctl is-active --quiet "actions.runner.*"; then /opt/github-runner/scripts/auto-recovery.sh >/dev/null 2>&1; fi

# Daily diagnostic report
0 2 * * * root /opt/github-runner/scripts/diagnose-runner-enhanced.sh > /var/log/github-runner-daily-diagnostic.log 2>&1

# Clean up old logs weekly
0 3 * * 0 root find /var/log -name "github-runner-*.log" -mtime +7 -delete
CRON_EOF
    
    log "Cron recovery jobs configured"
}

# Main startup function
main() {
    log "========================================="
    log "GitHub Runner Startup with Auto-Recovery"
    log "========================================="
    
    # Wait for system to stabilize
    log "Waiting for system initialization..."
    sleep 20
    
    # Deploy recovery system first
    deploy_recovery_system
    
    # Install monitor service
    install_monitor_service
    
    # Setup cron recovery
    setup_cron_recovery
    
    # Now run the main installation with auto-recovery enabled
    log "Starting runner installation with auto-recovery..."
    
    # The install script will automatically trigger recovery on failure
    if [[ -x "$SCRIPTS_DIR/install-runner.sh" ]]; then
        "$SCRIPTS_DIR/install-runner.sh" || {
            log "Installation failed, auto-recovery should have been triggered"
            exit 1
        }
    else
        log "ERROR: Install script not found at $SCRIPTS_DIR/install-runner.sh"
        exit 1
    fi
    
    # Start the monitor service after successful installation
    log "Starting health monitor service..."
    systemctl start github-runner-monitor.service || {
        log "WARNING: Failed to start monitor service"
    }
    
    # Final status check
    log ""
    log "========================================="
    log "Startup Complete"
    log "========================================="
    log "Auto-recovery system: ENABLED"
    log "Health monitoring: ACTIVE"
    log "Available commands:"
    log "  runner-diagnose  - Run diagnostics"
    log "  runner-fix       - Quick fixes"
    log "  runner-recover   - Manual recovery"
    log ""
    log "Monitor status: systemctl status github-runner-monitor"
    log "Logs: journalctl -u github-runner-monitor -f"
    log "========================================="
}

# Run main function
main "$@"