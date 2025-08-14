#!/bin/bash
# Enhanced GitHub Runner Diagnostic Script
# This script provides comprehensive diagnostics for troubleshooting runner setup issues

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LOG_FILE="/var/log/github-runner-install.log"
ERROR_LOG="/var/log/github-runner-errors.log"
STARTUP_LOG="/var/log/github-runner-startup.log"
PROJECT_ID="${PROJECT_ID:-}"

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}GitHub Runner Enhanced Diagnostics${NC}"
echo -e "${BLUE}=========================================${NC}"
echo "Date: $(date)"
echo ""

# Function to check status
check_status() {
    local check_name="$1"
    local command="$2"
    
    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}✓${NC} $check_name"
        return 0
    else
        echo -e "${RED}✗${NC} $check_name"
        return 1
    fi
}

# Function to get metadata
get_metadata() {
    local path="$1"
    curl -s -H "Metadata-Flavor: Google" \
        "http://metadata.google.internal/computeMetadata/v1/$path" 2>/dev/null || echo "N/A"
}

echo -e "${BLUE}=== System Information ===${NC}"
echo "Hostname: $(hostname)"
echo "Instance: $(get_metadata "instance/name")"
echo "Zone: $(get_metadata "instance/zone" | awk -F/ '{print $NF}')"
echo "Machine Type: $(get_metadata "instance/machine-type" | awk -F/ '{print $NF}')"
echo ""

echo -e "${BLUE}=== User and Permissions ===${NC}"
check_status "Runner user exists" "id runner"
if id runner &>/dev/null; then
    echo "  Groups: $(id -nG runner | tr ' ' ', ')"
fi
echo ""

echo -e "${BLUE}=== Service Account ===${NC}"
SA_EMAIL=$(get_metadata "instance/service-accounts/default/email")
echo "Service Account: $SA_EMAIL"
echo "Scopes:"
get_metadata "instance/service-accounts/default/scopes" | sed 's/^/  - /'
echo ""

echo -e "${BLUE}=== Secret Manager Access ===${NC}"
if [[ -n "$PROJECT_ID" ]]; then
    echo "Project ID: $PROJECT_ID"
    
    # Check if gcloud is installed
    if command -v gcloud &>/dev/null; then
        echo -e "${GREEN}✓${NC} gcloud CLI installed"
        
        # Check authentication
        if gcloud auth application-default print-access-token &>/dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Authenticated with metadata service"
        else
            echo -e "${RED}✗${NC} Not authenticated properly"
        fi
        
        # Check secret existence
        echo ""
        echo "Checking secret 'github-runner-token'..."
        SECRET_CHECK=$(gcloud secrets describe "github-runner-token" \
            --project="$PROJECT_ID" 2>&1 || true)
        
        if [[ "$SECRET_CHECK" == *"PERMISSION_DENIED"* ]]; then
            echo -e "${RED}✗${NC} Permission denied accessing secret"
            echo "  Fix: Grant roles/secretmanager.secretAccessor to $SA_EMAIL"
            echo ""
            echo "  Run this command:"
            echo "  gcloud projects add-iam-policy-binding $PROJECT_ID \\"
            echo "    --member=\"serviceAccount:$SA_EMAIL\" \\"
            echo "    --role=\"roles/secretmanager.secretAccessor\""
        elif [[ "$SECRET_CHECK" == *"NOT_FOUND"* ]]; then
            echo -e "${RED}✗${NC} Secret 'github-runner-token' not found"
            echo "  Fix: Create the secret with your GitHub PAT"
            echo ""
            echo "  Run this command:"
            echo "  echo -n 'YOUR_GITHUB_PAT' | gcloud secrets create github-runner-token \\"
            echo "    --data-file=- --project=$PROJECT_ID"
        else
            echo -e "${GREEN}✓${NC} Secret exists"
            
            # Check if we can access it
            if gcloud secrets versions access latest \
                --secret="github-runner-token" \
                --project="$PROJECT_ID" &>/dev/null 2>&1; then
                echo -e "${GREEN}✓${NC} Can access secret"
            else
                echo -e "${RED}✗${NC} Cannot access secret (check IAM permissions)"
            fi
        fi
        
        # List IAM roles for service account
        echo ""
        echo "IAM Roles for service account:"
        gcloud projects get-iam-policy "$PROJECT_ID" \
            --flatten="bindings[].members" \
            --filter="bindings.members:serviceAccount:$SA_EMAIL" \
            --format="table(bindings.role)" 2>/dev/null | head -20 || echo "  Unable to retrieve IAM roles"
    else
        echo -e "${RED}✗${NC} gcloud CLI not installed"
        echo "  This is required to access Secret Manager"
    fi
else
    echo -e "${YELLOW}⚠${NC} PROJECT_ID not set"
    echo "  Cannot check Secret Manager access"
fi
echo ""

echo -e "${BLUE}=== Docker Status ===${NC}"
if command -v docker &>/dev/null; then
    echo -e "${GREEN}✓${NC} Docker installed"
    
    if systemctl is-active --quiet docker; then
        echo -e "${GREEN}✓${NC} Docker service running"
    else
        echo -e "${RED}✗${NC} Docker service not running"
        echo "  Fix: sudo systemctl start docker"
    fi
    
    if docker version &>/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Docker daemon responding"
    else
        echo -e "${RED}✗${NC} Docker daemon not responding"
    fi
    
    if [[ -S /var/run/docker.sock ]]; then
        echo -e "${GREEN}✓${NC} Docker socket exists"
        SOCKET_PERMS=$(stat -c %a /var/run/docker.sock)
        if [[ "$SOCKET_PERMS" == "666" ]] || [[ "$SOCKET_PERMS" == "660" ]]; then
            echo -e "${GREEN}✓${NC} Docker socket permissions OK ($SOCKET_PERMS)"
        else
            echo -e "${YELLOW}⚠${NC} Docker socket permissions: $SOCKET_PERMS (should be 666 or 660)"
        fi
    else
        echo -e "${RED}✗${NC} Docker socket missing"
    fi
    
    if id runner &>/dev/null && su - runner -c "docker version" &>/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Runner user can access Docker"
    else
        echo -e "${RED}✗${NC} Runner user cannot access Docker"
        echo "  Fix: sudo usermod -aG docker runner && sudo chmod 666 /var/run/docker.sock"
    fi
else
    echo -e "${YELLOW}⚠${NC} Docker not installed"
fi
echo ""

echo -e "${BLUE}=== GitHub Runner Status ===${NC}"
if [[ -d "/home/runner/actions-runner" ]]; then
    echo -e "${GREEN}✓${NC} Runner directory exists"
    
    if [[ -f "/home/runner/actions-runner/.runner" ]]; then
        echo -e "${GREEN}✓${NC} Runner is configured"
        RUNNER_NAME=$(jq -r .agentName /home/runner/actions-runner/.runner 2>/dev/null || echo "Unknown")
        echo "  Name: $RUNNER_NAME"
    else
        echo -e "${RED}✗${NC} Runner not configured"
    fi
    
    # Check for runner service
    SERVICE_NAME=$(systemctl list-units --all 2>/dev/null | grep -o "actions\.runner\..*\.service" | head -1 || true)
    if [[ -n "$SERVICE_NAME" ]]; then
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            echo -e "${GREEN}✓${NC} Runner service active: $SERVICE_NAME"
        else
            echo -e "${RED}✗${NC} Runner service not active: $SERVICE_NAME"
            echo "  Fix: sudo systemctl start $SERVICE_NAME"
        fi
    else
        echo -e "${RED}✗${NC} No runner service found"
    fi
else
    echo -e "${RED}✗${NC} Runner not installed"
fi
echo ""

echo -e "${BLUE}=== Recent Logs ===${NC}"
echo "Checking installation logs..."

# Function to show recent log entries
show_recent_logs() {
    local log_file="$1"
    local log_name="$2"
    
    if [[ -f "$log_file" ]]; then
        echo ""
        echo "$log_name (last 10 lines):"
        tail -10 "$log_file" | sed 's/^/  /'
    else
        echo "$log_name: Not found"
    fi
}

# Show error logs first
if [[ -f "$ERROR_LOG" ]] && [[ -s "$ERROR_LOG" ]]; then
    echo -e "${RED}Errors found in $ERROR_LOG:${NC}"
    tail -20 "$ERROR_LOG" | sed 's/^/  /'
fi

# Show recent installation logs
show_recent_logs "$LOG_FILE" "Installation log"

# Look for specific error patterns
echo ""
echo -e "${BLUE}=== Error Analysis ===${NC}"
if [[ -f "$LOG_FILE" ]]; then
    if grep -q "Permission denied" "$LOG_FILE" 2>/dev/null; then
        echo -e "${RED}✗${NC} Permission errors found in logs"
    fi
    
    if grep -q "Failed to retrieve GitHub PAT" "$LOG_FILE" 2>/dev/null; then
        echo -e "${RED}✗${NC} Failed to retrieve GitHub token from Secret Manager"
        echo "  This is likely the root cause of the failure"
    fi
    
    if grep -q "User runner created successfully" "$LOG_FILE" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Runner user was created successfully"
        
        # Check what happened after user creation
        echo ""
        echo "Events after user creation:"
        grep -A 5 "User runner created successfully" "$LOG_FILE" 2>/dev/null | tail -6 | sed 's/^/  /'
    fi
else
    echo "No log file found at $LOG_FILE"
fi

echo ""
echo -e "${BLUE}=== Recommendations ===${NC}"

# Provide specific recommendations based on findings
ISSUES_FOUND=false

if ! id runner &>/dev/null; then
    echo "1. Runner user doesn't exist. The installation may not have started."
    ISSUES_FOUND=true
fi

if [[ -n "$PROJECT_ID" ]] && command -v gcloud &>/dev/null; then
    if ! gcloud secrets describe "github-runner-token" --project="$PROJECT_ID" &>/dev/null 2>&1; then
        echo "2. Secret 'github-runner-token' is missing or inaccessible."
        echo "   Create it with: echo -n 'YOUR_PAT' | gcloud secrets create github-runner-token --data-file=- --project=$PROJECT_ID"
        ISSUES_FOUND=true
    fi
fi

if [[ "$ISSUES_FOUND" == "false" ]]; then
    echo -e "${GREEN}No critical issues detected.${NC}"
    echo "If the runner still isn't working, check the full logs at:"
    echo "  - $LOG_FILE"
    echo "  - $ERROR_LOG"
fi

echo ""
echo -e "${BLUE}=========================================${NC}"
echo "Diagnostic complete."
echo "For manual fixes, SSH into the instance and run:"
echo "  sudo /opt/github-runner/scripts/fix-runner.sh"
echo -e "${BLUE}=========================================${NC}"