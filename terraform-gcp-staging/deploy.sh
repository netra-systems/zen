#!/bin/bash
# Deployment script for GCP Staging Infrastructure
# This script orchestrates the complete PostgreSQL 17 migration

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${PROJECT_ID:-"netra-staging"}
OLD_INSTANCE=${OLD_INSTANCE:-"staging-shared-postgres"}
TERRAFORM_DIR="."

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}GCP Staging Infrastructure Deployment${NC}"
echo -e "${GREEN}PostgreSQL 14 → 17 Migration${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to check command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}Error: $1 is not installed${NC}"
        exit 1
    fi
}

# Function to confirm action
confirm() {
    read -p "$1 (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Aborted${NC}"
        exit 0
    fi
}

# Step 1: Check prerequisites
echo -e "\n${YELLOW}Step 1: Checking prerequisites...${NC}"
check_command gcloud
check_command terraform
check_command python3

# Check GCloud authentication
echo "Checking GCloud authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}Not authenticated with GCloud${NC}"
    echo "Please run: gcloud auth login"
    exit 1
fi

# Set project
echo "Setting GCP project to ${PROJECT_ID}..."
gcloud config set project ${PROJECT_ID}

# Step 2: Initialize Terraform
echo -e "\n${YELLOW}Step 2: Initializing Terraform...${NC}"
cd ${TERRAFORM_DIR}

if [ ! -f terraform.tfvars ]; then
    echo "Creating terraform.tfvars from example..."
    cp terraform.tfvars.example terraform.tfvars
    echo -e "${YELLOW}Please review terraform.tfvars and adjust if needed${NC}"
    read -p "Press enter to continue..."
fi

terraform init

# Step 3: Plan Terraform changes
echo -e "\n${YELLOW}Step 3: Planning infrastructure changes...${NC}"
terraform plan -out=tfplan

echo -e "\n${YELLOW}Review the plan above carefully!${NC}"
confirm "Do you want to apply these changes?"

# Step 4: Apply Terraform changes
echo -e "\n${YELLOW}Step 4: Creating new PostgreSQL 17 infrastructure...${NC}"
terraform apply tfplan

# Get new instance name
NEW_INSTANCE=$(terraform output -raw database_instance_name)
echo -e "${GREEN}✓ New instance created: ${NEW_INSTANCE}${NC}"

# Step 5: Backup old database
echo -e "\n${YELLOW}Step 5: Backing up old database...${NC}"
confirm "Do you want to create a backup of ${OLD_INSTANCE}?"

BACKUP_NAME="pre-migration-$(date +%Y%m%d-%H%M%S)"
gcloud sql backups create \
    --instance=${OLD_INSTANCE} \
    --project=${PROJECT_ID} \
    --description="Backup before PostgreSQL 17 migration"

echo -e "${GREEN}✓ Backup created${NC}"

# Step 6: Migrate data
echo -e "\n${YELLOW}Step 6: Migrating data...${NC}"
confirm "Do you want to migrate data from ${OLD_INSTANCE} to ${NEW_INSTANCE}?"

python3 migrate.py \
    --project ${PROJECT_ID} \
    --old-instance ${OLD_INSTANCE} \
    --skip-backup  # Already backed up

# Step 7: Update application deployment
echo -e "\n${YELLOW}Step 7: Updating application deployment...${NC}"
cd ..
python3 scripts/deploy_to_gcp_actual.py --project ${PROJECT_ID} --build-local --run-checks

# Step 8: Run tests
echo -e "\n${YELLOW}Step 8: Running integration tests...${NC}"
python3 unified_test_runner.py --level integration --env staging --fast-fail

# Step 9: Show summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Migration completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\nNew Infrastructure:"
echo -e "  PostgreSQL Instance: ${NEW_INSTANCE}"
echo -e "  PostgreSQL Version: 17"
echo -e "  Public IP: $(terraform output -raw database_public_ip)"
echo -e "  Connection: $(terraform output -raw database_connection_name)"
echo -e "\n${YELLOW}Next Steps:${NC}"
echo -e "1. Monitor application logs for any issues"
echo -e "2. Verify all services are functioning correctly"
echo -e "3. Once confirmed, delete old instance:"
echo -e "   ${YELLOW}gcloud sql instances delete ${OLD_INSTANCE} --project ${PROJECT_ID}${NC}"
echo -e "\n${GREEN}Documentation: terraform-gcp-staging/README.md${NC}"