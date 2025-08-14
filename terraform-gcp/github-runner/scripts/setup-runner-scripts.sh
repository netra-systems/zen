#!/bin/bash
# Setup script to deploy and configure all GitHub runner scripts with proper permissions

set -euo pipefail

# Configuration
SCRIPTS_DIR="/opt/github-runner/scripts"
SYSTEMD_DIR="/etc/systemd/system"
LOG_FILE="/var/log/github-runner-setup.log"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging
exec > >(tee -a "$LOG_FILE") 2>&1

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

success() {
    log "${GREEN}✓${NC} $1"
}

warning() {
    log "${YELLOW}⚠${NC} $1"
}

# Check root
if [[ "$EUID" -ne 0 ]]; then
    echo "This script must be run as root"
    exit 1
fi

log "========================================="
log "GitHub Runner Scripts Setup"
log "========================================="

# Create scripts directory
log "Creating scripts directory..."
mkdir -p "$SCRIPTS_DIR"

# Copy all scripts to the scripts directory
log "Deploying runner scripts..."

# Note: These scripts should be deployed via terraform or copied from the repository
# For now, we'll check if they exist in the current directory and copy them

SCRIPT_SOURCE_DIR="${SCRIPT_SOURCE_DIR:-/tmp/runner-scripts}"

if [[ -d "$SCRIPT_SOURCE_DIR" ]]; then
    log "Copying scripts from $SCRIPT_SOURCE_DIR..."
    
    for script in install-runner.sh diagnose-runner.sh fix-runner-issues.sh monitor-runner.sh; do
        if [[ -f "$SCRIPT_SOURCE_DIR/$script" ]]; then
            cp "$SCRIPT_SOURCE_DIR/$script" "$SCRIPTS_DIR/"
            success "Copied $script"
        else
            warning "Script $script not found in $SCRIPT_SOURCE_DIR"
        fi
    done
else
    log "Creating placeholder for manual script deployment..."
    
    # Create a README for manual installation
    cat > "$SCRIPTS_DIR/README.md" << 'EOF'
# GitHub Runner Scripts

The following scripts should be deployed here:
- install-runner.sh : Main installation script
- diagnose-runner.sh : Diagnostic tool
- fix-runner-issues.sh : Automatic fix tool
- monitor-runner.sh : Health monitoring

Deploy them from the terraform-gcp/github-runner/scripts/ directory.
EOF
    
    warning "Scripts not found. Please deploy manually to $SCRIPTS_DIR"
fi

# Set proper permissions
log "Setting script permissions..."
chmod 755 "$SCRIPTS_DIR"/*.sh
chown root:root "$SCRIPTS_DIR"/*.sh

success "Scripts deployed to $SCRIPTS_DIR"

# Create systemd service for monitoring
log "Creating monitoring service..."

cat > "$SYSTEMD_DIR/github-runner-monitor.service" << 'EOF'
[Unit]
Description=GitHub Runner Health Monitor
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
ExecStart=/opt/github-runner/scripts/monitor-runner.sh --verbose --interval 60
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=github-runner-monitor
User=root

[Install]
WantedBy=multi-user.target
EOF

# Create timer for periodic diagnostics
cat > "$SYSTEMD_DIR/github-runner-diagnostics.timer" << 'EOF'
[Unit]
Description=Run GitHub Runner Diagnostics every 6 hours
Requires=github-runner-diagnostics.service

[Timer]
OnBootSec=10min
OnUnitActiveSec=6h
Persistent=true

[Install]
WantedBy=timers.target
EOF

cat > "$SYSTEMD_DIR/github-runner-diagnostics.service" << 'EOF'
[Unit]
Description=GitHub Runner Diagnostics
After=network.target

[Service]
Type=oneshot
ExecStart=/opt/github-runner/scripts/diagnose-runner.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=github-runner-diagnostics
User=root
EOF

# Reload systemd
systemctl daemon-reload

# Enable services (but don't start yet)
systemctl enable github-runner-monitor.service || true
systemctl enable github-runner-diagnostics.timer || true

success "Systemd services configured"

# Create convenience aliases
log "Creating convenience commands..."

cat > /usr/local/bin/runner-status << 'EOF'
#!/bin/bash
echo "=== GitHub Runner Status ==="
/opt/github-runner/scripts/diagnose-runner.sh | grep -E "✓|✗|⚠" | tail -20
EOF

cat > /usr/local/bin/runner-fix << 'EOF'
#!/bin/bash
echo "=== Running GitHub Runner Fixes ==="
/opt/github-runner/scripts/fix-runner-issues.sh
EOF

cat > /usr/local/bin/runner-logs << 'EOF'
#!/bin/bash
echo "=== Recent Runner Logs ==="
journalctl -u "actions.runner.*" -n 50 --no-pager
echo ""
echo "=== Monitor Logs ==="
journalctl -u github-runner-monitor -n 20 --no-pager
EOF

chmod +x /usr/local/bin/runner-*

success "Convenience commands created:"
log "  - runner-status : Quick health check"
log "  - runner-fix    : Run automatic fixes"
log "  - runner-logs   : View recent logs"

# Create cron job for automatic fixes
log "Setting up automatic recovery..."

cat > /etc/cron.d/github-runner-autofix << 'EOF'
# Automatic GitHub Runner recovery
# Run fix script if runner is down for more than 5 minutes
*/5 * * * * root if ! systemctl is-active --quiet "actions.runner.*"; then /opt/github-runner/scripts/fix-runner-issues.sh > /dev/null 2>&1; fi
EOF

success "Automatic recovery configured"

log "========================================="
log "Setup Complete!"
log "========================================="
log ""
log "Scripts installed to: $SCRIPTS_DIR"
log "Available commands:"
log "  - runner-status : Check runner health"
log "  - runner-fix    : Fix common issues"
log "  - runner-logs   : View logs"
log ""
log "Services:"
log "  - github-runner-monitor.service : Continuous monitoring"
log "  - github-runner-diagnostics.timer : Periodic health checks"
log ""
log "To start monitoring:"
log "  systemctl start github-runner-monitor"
log "  systemctl start github-runner-diagnostics.timer"
log "========================================="