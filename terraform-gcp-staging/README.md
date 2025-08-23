# GCP Staging Infrastructure with Terraform

This directory contains Terraform configuration for managing GCP staging infrastructure, specifically Cloud SQL PostgreSQL 17 and Redis instances.

## Overview

This Terraform configuration creates and manages:
- **Cloud SQL PostgreSQL 17** instance (upgraded from PostgreSQL 14)
- **Google Cloud Memorystore Redis** instance
- **VPC networking** for private connectivity
- **Secret Manager** entries for connection strings
- **Automated backups** and maintenance windows

## Prerequisites

1. **GCloud CLI** installed and authenticated:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project netra-staging
   ```

2. **Terraform** installed (version 1.5.0 or higher)

3. **Required GCP APIs** enabled (Terraform will enable these automatically):
   - Cloud SQL Admin API
   - Compute Engine API
   - Service Networking API
   - Secret Manager API
   - Redis API

## Quick Start - Complete Migration Process

### Step 1: Initialize Terraform

```bash
cd terraform-gcp-staging

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Initialize Terraform
terraform init
```

### Step 2: Review and Apply Infrastructure

```bash
# Review the planned changes
terraform plan

# Apply the infrastructure (creates new PostgreSQL 17 instance)
terraform apply
```

This will create:
- New Cloud SQL instance with PostgreSQL 17
- Redis instance
- VPC networking
- Secret Manager entries

### Step 3: Migrate Data from Old Instance

```bash
# Run the migration script
python migrate.py --project netra-staging

# Or with specific options:
python migrate.py \
  --project netra-staging \
  --old-instance staging-shared-postgres \
  --database netra \
  --bucket netra-staging-migrations
```

The migration script will:
1. Create a backup of the old PostgreSQL 14 instance
2. Export the database to Google Cloud Storage
3. Import the data into the new PostgreSQL 17 instance
4. Update the deployment script to use the new instance
5. Verify the migration

### Step 4: Update Application Configuration

The migration script automatically updates `scripts/deploy_to_gcp.py` to use the new instance. Verify the changes:

```bash
# Check the updated deployment script
git diff scripts/deploy_to_gcp.py

# Deploy applications with new database
python scripts/deploy_to_gcp.py --project netra-staging --build-local --run-checks
```

### Step 5: Verify and Test

```bash
# Check new instance status
gcloud sql instances describe $(terraform output -raw database_instance_name) \
  --project netra-staging

# Get connection details
terraform output database_public_ip
terraform output database_connection_name

# Run integration tests
python unified_test_runner.py --level integration --env staging
```

### Step 6: Cleanup Old Instance (After Verification)

Once everything is verified and working:

```bash
# List all instances to confirm
gcloud sql instances list --project netra-staging

# Delete the old PostgreSQL 14 instance
gcloud sql instances delete staging-shared-postgres --project netra-staging
```

## Infrastructure Details

### PostgreSQL Configuration

- **Version**: PostgreSQL 17 (latest)
- **Tier**: `db-g1-small` (matching current staging)
- **Storage**: 10GB SSD with autoresize up to 100GB
- **Backups**: Daily at 2 AM with 7-day retention
- **Maintenance**: Sunday at 3 AM

### Redis Configuration

- **Version**: Redis 7.2
- **Tier**: BASIC
- **Memory**: 1GB

### Network Configuration

- **VPC**: Custom VPC with private IP ranges
- **Access**: Both public and private IPs enabled
- **Security**: Authorized networks configured (allow-all for staging)

### Secret Manager

Connection strings are automatically stored in Secret Manager:
- `staging-database-url`: For Cloud Run services (uses Cloud SQL proxy)
- `staging-database-url-direct`: For direct connections
- `staging-redis-url`: Redis connection string
- `staging-jwt-secret`: JWT signing secret

## Terraform Commands

### Basic Operations

```bash
# Initialize Terraform
terraform init

# Format configuration files
terraform fmt

# Validate configuration
terraform validate

# Plan changes
terraform plan

# Apply changes
terraform apply

# Apply without confirmation
terraform apply -auto-approve

# Destroy infrastructure (CAUTION!)
terraform destroy
```

### Viewing Outputs

```bash
# Show all outputs
terraform output

# Get specific output
terraform output database_public_ip
terraform output database_connection_name

# Get sensitive outputs (connection strings)
terraform output -json app_connection_string
```

### State Management

```bash
# List resources in state
terraform state list

# Show specific resource
terraform state show google_sql_database_instance.postgres

# Pull remote state
terraform state pull

# Import existing resources
terraform import google_sql_database_instance.postgres projects/netra-staging/instances/existing-instance
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   gcloud auth application-default login
   gcloud config set project netra-staging
   ```

2. **API Not Enabled**
   ```bash
   gcloud services enable sqladmin.googleapis.com
   gcloud services enable servicenetworking.googleapis.com
   ```

3. **State Lock Issues**
   ```bash
   terraform force-unlock <lock_id>
   ```

4. **Migration Failures**
   - Check export file in GCS bucket
   - Verify database compatibility
   - Review instance logs in Cloud Console

### Monitoring and Logs

```bash
# View instance logs
gcloud sql operations list --instance=$(terraform output -raw database_instance_name) --project netra-staging

# Check instance metrics
gcloud monitoring metrics-descriptors list --filter="resource.type=cloudsql_database"

# Access Secret Manager
gcloud secrets versions access latest --secret=staging-database-url --project netra-staging
```

## Security Considerations

### For Production

1. **Network Security**:
   - Remove `0.0.0.0/0` from authorized networks
   - Use specific IP ranges or Cloud NAT
   - Enable `require_ssl = true`

2. **High Availability**:
   - Change `availability_type` to `REGIONAL`
   - Enable automated failover

3. **Backup Strategy**:
   - Increase retention period
   - Enable cross-region backups
   - Test restore procedures

4. **Access Control**:
   - Use service accounts with minimal permissions
   - Rotate passwords regularly
   - Enable audit logging

## CI/CD Integration

### GitHub Actions

```yaml
- name: Terraform Apply
  run: |
    cd terraform-gcp-staging
    terraform init
    terraform apply -auto-approve
  env:
    GOOGLE_CREDENTIALS: ${{ secrets.GCP_SA_KEY }}
```

### Pre-commit Hooks

```bash
# Add to .pre-commit-config.yaml
- repo: https://github.com/antonbabenko/pre-commit-terraform
  hooks:
    - id: terraform_fmt
    - id: terraform_validate
```

## Rollback Procedure

If issues occur after migration:

1. **Immediate Rollback**:
   ```bash
   # Update deployment script to use old instance
   # Edit scripts/deploy_to_gcp.py and change instance name back
   
   # Redeploy applications
   python scripts/deploy_to_gcp.py --project netra-staging --build-local
   ```

2. **Data Recovery**:
   ```bash
   # List available backups
   gcloud sql backups list --instance=staging-shared-postgres --project netra-staging
   
   # Restore from backup
   gcloud sql backups restore <backup_id> --restore-instance=staging-shared-postgres --project netra-staging
   ```

## Maintenance

### Regular Tasks

1. **Weekly**: Review backup success, check disk usage
2. **Monthly**: Review and optimize database flags, analyze slow queries
3. **Quarterly**: Update PostgreSQL minor versions, review security settings

### Performance Tuning

Adjust database flags in `terraform.tfvars`:
```hcl
database_flags = [
  { name = "max_connections", value = "200" },
  { name = "shared_buffers", value = "256000" },
  { name = "work_mem", value = "4096" }
]
```

## Support

For issues or questions:
1. Check [GCP Cloud SQL documentation](https://cloud.google.com/sql/docs)
2. Review Terraform state: `terraform state pull`
3. Check instance logs in GCP Console
4. File issues in the project repository