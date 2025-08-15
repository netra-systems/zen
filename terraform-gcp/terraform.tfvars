# terraform.staging.tfvars - Staging environment configuration
# This file contains staging-specific values to ensure staging deployments
# do not use production resources

project_id = "netra-staging"  # Staging project ID
region     = "us-central1"
zone       = "us-central1-a"

# Redis URL for staging
redis_url = "redis://staging-redis:6379"

# IMPORTANT: Set environment to staging
environment = "staging"

# Resource sizing for staging (smaller than production)
# Optimized for testing and development

# Database settings - smaller for staging
db_tier      = "db-f1-micro"  # Smallest tier for cost savings
db_disk_size = 20              # Minimum 20GB

# Backend settings - reduced for staging
backend_cpu           = "0.5"   # 0.5 vCPU
backend_memory        = "1Gi"   # 1GB RAM
backend_min_instances = 0       # Scale to zero when not in use
backend_max_instances = 2       # Limited scaling for staging

# Frontend settings - minimal for staging
frontend_cpu           = "0.25"  # 0.25 vCPU
frontend_memory        = "512Mi" # 512MB RAM
frontend_min_instances = 0       # Scale to zero when not in use
frontend_max_instances = 2       # Limited scaling for staging

# Enable APIs for staging project
enable_apis = true

# Create backups bucket for staging
create_backups_bucket = true