#!/bin/bash
# Deploy a new GitHub runner instance with Docker fixes

set -e

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

main() {
    log "Starting deployment of fixed GitHub runner..."
    
    # Check if we're in the right directory
    if [ ! -f "single-runner.tf" ]; then
        echo -e "${RED}Error: single-runner.tf not found. Please run from terraform-gcp/github-runner directory${NC}"
        exit 1
    fi
    
    # Initialize Terraform if needed
    if [ ! -d ".terraform" ]; then
        log "Initializing Terraform..."
        terraform init
    fi
    
    # Plan the deployment
    log "Planning Terraform deployment..."
    terraform plan -target=google_compute_instance.github_runner_fixed -out=tfplan
    
    # Ask for confirmation
    echo -e "${YELLOW}Ready to deploy the fixed GitHub runner instance.${NC}"
    read -p "Do you want to proceed? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        log "Deployment cancelled"
        exit 0
    fi
    
    # Apply the configuration
    log "Applying Terraform configuration..."
    terraform apply tfplan
    
    # Get the instance details
    INSTANCE_NAME=$(terraform output -json fixed_runner_instance 2>/dev/null | jq -r '.name' || echo "")
    INSTANCE_IP=$(terraform output -json fixed_runner_instance 2>/dev/null | jq -r '.ip' || echo "")
    
    if [ -z "$INSTANCE_NAME" ]; then
        echo -e "${RED}Warning: Could not get instance name from Terraform output${NC}"
        INSTANCE_NAME=$(gcloud compute instances list --filter="name:gcp-runner-fixed-*" --format="value(name)" | head -1)
    fi
    
    if [ -n "$INSTANCE_NAME" ]; then
        echo -e "${GREEN}✓ Instance deployed: $INSTANCE_NAME${NC}"
        [ -n "$INSTANCE_IP" ] && echo -e "${GREEN}✓ External IP: $INSTANCE_IP${NC}"
        
        # Wait for startup script to complete
        log "Waiting for startup script to complete (this may take 5-10 minutes)..."
        
        sleep 30  # Initial wait for instance to boot
        
        # Monitor the startup script progress
        MAX_WAIT=600  # 10 minutes
        ELAPSED=0
        
        while [ $ELAPSED -lt $MAX_WAIT ]; do
            # Try to get the startup script status
            STATUS=$(gcloud compute instances get-serial-port-output "$INSTANCE_NAME" \
                --zone=us-central1-a 2>/dev/null | tail -20 | grep -E "(GitHub runner installation completed|ERROR:|Installation Complete)" || true)
            
            if echo "$STATUS" | grep -q "GitHub runner installation completed"; then
                echo -e "${GREEN}✓ GitHub runner installation completed successfully!${NC}"
                break
            elif echo "$STATUS" | grep -q "Installation Complete"; then
                echo -e "${GREEN}✓ Installation completed!${NC}"
                break
            elif echo "$STATUS" | grep -q "ERROR:"; then
                echo -e "${RED}✗ Error detected in startup script${NC}"
                echo "$STATUS"
                break
            fi
            
            echo -n "."
            sleep 10
            ELAPSED=$((ELAPSED + 10))
        done
        
        echo ""
        
        # Check runner status
        log "Checking runner status..."
        gcloud compute ssh "$INSTANCE_NAME" --zone=us-central1-a --command="
            echo '=== Docker Status ==='
            sudo docker version 2>/dev/null || echo 'Docker not ready'
            echo ''
            echo '=== Docker Buildx Status ==='
            sudo docker buildx ls 2>/dev/null || echo 'Buildx not configured'
            echo ''
            echo '=== GitHub Runner Status ==='
            sudo systemctl status 'actions.runner.*' --no-pager 2>/dev/null || echo 'Runner service not found'
        " 2>/dev/null || {
            echo -e "${YELLOW}Note: SSH connection not ready yet. Please wait a few minutes and check manually.${NC}"
        }
        
        echo ""
        echo -e "${GREEN}Deployment complete!${NC}"
        echo ""
        echo "To check the logs:"
        echo "  gcloud compute ssh $INSTANCE_NAME --zone=us-central1-a --command='sudo tail -f /var/log/github-runner-install.log'"
        echo ""
        echo "To check runner status:"
        echo "  gcloud compute ssh $INSTANCE_NAME --zone=us-central1-a --command='sudo systemctl status actions.runner.*'"
        echo ""
        echo "If Docker buildx has issues, run:"
        echo "  ./scripts/fix-docker-buildx.sh $INSTANCE_NAME"
        
    else
        echo -e "${RED}Error: Could not determine instance name${NC}"
        exit 1
    fi
}

main "$@"