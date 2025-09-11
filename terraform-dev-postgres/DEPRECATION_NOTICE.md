# 🚨 DEPRECATION WARNING - WEEK 1 SSOT REMEDIATION

**GitHub Issue #245: Deployment canonical source conflicts**

## This Terraform Configuration is Deprecated

This `terraform-dev-postgres/` directory is deprecated in favor of the canonical Terraform infrastructure.

### CANONICAL SOURCE

**terraform-gcp-staging/** - The official Terraform configuration for all GCP infrastructure

### Migration Path

```bash
# OLD: Development Postgres setup
cd terraform-dev-postgres/
terraform init && terraform apply

# NEW: Use canonical GCP staging infrastructure
cd terraform-gcp-staging/
terraform init && terraform apply
```

### Why This Directory is Deprecated

1. **Multiple Infrastructure Sources**: Having separate dev and staging Terraform configs creates deployment confusion
2. **Environment Drift**: Different configurations lead to inconsistent environments
3. **Maintenance Overhead**: Multiple Terraform states to manage and maintain
4. **SSOT Violation**: Violates Single Source of Truth principle for infrastructure

### Recommended Actions

#### For Local Development:
```bash
# Use Docker Compose for local development databases
docker-compose --profile dev up postgres redis clickhouse
```

#### For Staging Environment:
```bash
# Use canonical GCP Terraform configuration
cd terraform-gcp-staging/
terraform init
terraform plan
terraform apply
```

#### For Production Environment:
```bash
# Use canonical GCP Terraform configuration with production variables
cd terraform-gcp-staging/
cp terraform.tfvars.example terraform.tfvars.prod
# Edit terraform.tfvars.prod with production settings
terraform workspace new production
terraform init
terraform plan -var-file="terraform.tfvars.prod"
terraform apply -var-file="terraform.tfvars.prod"
```

### Current Infrastructure Status

This directory contains:
- PostgreSQL database configuration
- ClickHouse analytics database setup
- Redis caching layer configuration
- Network and security configurations

**All of this functionality is available in `terraform-gcp-staging/` with better:**
- Resource management
- Security configurations
- Scalability options
- Cost optimization
- Monitoring integration

### Timeline

- **Week 1 (Current)**: Deprecation warnings and migration guidance
- **Week 2**: Active migration support and validation
- **Week 3**: Directory removal after confirming all teams have migrated

### Support

If you have questions about migrating from this deprecated infrastructure:

1. Review `terraform-gcp-staging/README.md` for setup instructions
2. Check `terraform-gcp-staging/terraform.tfvars.example` for configuration options
3. Use `docker-compose --profile dev up` for local development databases
4. For staging/production, use `scripts/deploy_to_gcp_actual.py --project netra-staging`

### DO NOT USE THIS DIRECTORY FOR NEW DEPLOYMENTS

**⚠️ WARNING**: This directory will be removed in Week 3 of the SSOT remediation process.

Please migrate to the canonical sources immediately to avoid deployment issues.