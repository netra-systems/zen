# Terraform Infrastructure Guide

## Directory Structure

This project has multiple Terraform configurations for different environments:

### 1. `terraform-dev-postgres/` - LOCAL Development (Docker)
**Purpose**: Local development environment on YOUR machine  
**Creates**: Docker containers for PostgreSQL, Redis, and ClickHouse  
**Use When**: Developing locally on your laptop/desktop  
**Requirements**: Docker Desktop  

```bash
cd terraform-dev-postgres
terraform init
terraform apply
```

### 2. `terraform/staging/` - CLOUD Staging (Google Cloud)
**Purpose**: Cloud staging environment on GCP  
**Creates**: Cloud Run services, Cloud SQL, etc.  
**Use When**: Testing in cloud staging environment  
**Requirements**: GCP account, gcloud CLI  

```bash
cd terraform/staging
# See deploy-instructions.md for detailed steps
```

### 3. `terraform-gcp/` - GCP Production Infrastructure
**Purpose**: Production infrastructure on Google Cloud  
**Creates**: Production services and resources  
**Use When**: Deploying to production  
**Requirements**: GCP production account  

## Quick Reference

| Environment | Directory | Infrastructure | Port/URL |
|------------|-----------|---------------|----------|
| **Local Dev** | `terraform-dev-postgres/` | Docker containers | localhost:5433 (PG), localhost:6379 (Redis), localhost:9000 (ClickHouse) |
| **Cloud Staging** | `terraform/staging/` | GCP Cloud Run | https://staging.netrasystems.ai |
| **Production** | `terraform-gcp/` | GCP Production | https://app.netrasystems.ai |

## Environment Variables

### Local Development (.env)
```bash
ENVIRONMENT=development
REDIS_MODE=local
CLICKHOUSE_MODE=local
REDIS_HOST=localhost
CLICKHOUSE_HOST=localhost
```

### Cloud Staging
```bash
ENVIRONMENT=staging
REDIS_MODE=shared
CLICKHOUSE_MODE=shared
# Uses GCP Secret Manager for credentials
```

## Common Commands

### Local Development
```bash
# Start local infrastructure
cd terraform-dev-postgres
terraform apply

# Start application
python scripts/dev_launcher.py

# Stop and destroy local infrastructure
terraform destroy
```

### Cloud Staging
```bash
# Deploy to staging
cd terraform/staging
terraform apply -var="pr_number=123"

# Destroy staging environment
terraform destroy -var="pr_number=123"
```

## Troubleshooting

### Local Dev Issues
- Ensure Docker Desktop is running
- Check ports aren't already in use
- Review `terraform-dev-postgres/connection_info.txt` for credentials

### Cloud Staging Issues
- Ensure GCP authentication: `gcloud auth login`
- Check project: `gcloud config get-value project`
- Review `terraform/staging/deploy-instructions.md`

## Important Notes

1. **Never mix environments** - Local dev configs should not point to cloud services
2. **Use correct .env file** - `.env` for local, staging configs for cloud
3. **Check terraform state** - Each environment has separate state management