#!/bin/bash
# Secure Terraform wrapper script that prevents secrets from appearing in logs

set -euo pipefail

# Function to create secure tfvars file
create_secure_tfvars() {
    local TFVARS_FILE="${1:-terraform.tfvars}"
    
    # Create secure temporary file with restricted permissions
    touch "${TFVARS_FILE}"
    chmod 600 "${TFVARS_FILE}"
    
    # Write variables to file instead of command line
    cat > "${TFVARS_FILE}" << EOF
project_id = "${TF_VAR_project_id}"
project_id_numerical = "${TF_VAR_project_id_numerical}"
region = "${TF_VAR_region}"
pr_number = "${TF_VAR_pr_number}"
backend_image = "${TF_VAR_backend_image}"
frontend_image = "${TF_VAR_frontend_image}"
max_instances = ${TF_VAR_max_instances}
domain = "${TF_VAR_domain}"
postgres_password = "${TF_VAR_postgres_password}"
clickhouse_password = "${TF_VAR_clickhouse_password}"
EOF
    
    echo "Created secure tfvars file: ${TFVARS_FILE}"
}

# Function to clean up sensitive files
cleanup_sensitive_files() {
    rm -f terraform.tfvars terraform.tfvars.json *.auto.tfvars 2>/dev/null || true
}

# Trap to ensure cleanup on exit
trap cleanup_sensitive_files EXIT

# Main execution
case "${1:-}" in
    plan)
        create_secure_tfvars
        echo "Running terraform plan with secure variables..."
        terraform plan -var-file=terraform.tfvars -lock-timeout=120s -out=tfplan
        ;;
    apply)
        echo "Running terraform apply..."
        terraform apply -auto-approve tfplan
        ;;
    destroy)
        create_secure_tfvars
        echo "Running terraform destroy with secure variables..."
        terraform destroy -auto-approve -var-file=terraform.tfvars
        ;;
    *)
        echo "Usage: $0 {plan|apply|destroy}"
        exit 1
        ;;
esac