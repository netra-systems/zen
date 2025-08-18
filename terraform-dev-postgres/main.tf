# LOCAL DEVELOPMENT Infrastructure Orchestration
# This terraform configuration is ONLY for LOCAL DEVELOPMENT
# NOT for staging or production environments
# 
# Creates Docker containers on your LOCAL machine:
# - PostgreSQL (port 5433)
# - Redis (port 6379)
# - ClickHouse (ports 8123/9000)
#
# This file coordinates all infrastructure modules

# Module dependencies are handled via resource references
# Each module is self-contained and focused on a single responsibility

# The actual resources are defined in:
# - providers.tf: Terraform providers configuration
# - passwords.tf: Password generation (simplified alphanumeric)
# - network.tf: Docker network setup
# - postgres.tf: PostgreSQL container
# - redis.tf: Redis container
# - clickhouse.tf: ClickHouse container
# - outputs_files.tf: Output file generation

# To deploy:
# terraform init
# terraform apply

# To destroy:
# terraform destroy