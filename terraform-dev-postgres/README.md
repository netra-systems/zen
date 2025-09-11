# 🚨 DEPRECATED - WEEK 1 SSOT REMEDIATION

**GitHub Issue #245: Deployment canonical source conflicts**

## ⚠️ DEPRECATION WARNING

**This terraform-dev-postgres/ directory is DEPRECATED.**

**CANONICAL SOURCES:**
- GCP Infrastructure: `terraform-gcp-staging/`
- Local Development: `docker-compose --profile dev up`

**Migration Path:**
```bash
# OLD: terraform-dev-postgres setup
cd terraform-dev-postgres/ && terraform apply

# NEW: Local development databases
docker-compose --profile dev up postgres redis clickhouse

# NEW: GCP staging infrastructure  
cd terraform-gcp-staging/ && terraform apply
```

**See [DEPRECATION_NOTICE.md](./DEPRECATION_NOTICE.md) for complete migration guide.**

**This directory will be removed in Week 3 of SSOT remediation.**

---

# LOCAL Development Database Infrastructure with Terraform

**⚠️ IMPORTANT: This is DEPRECATED - Use docker-compose for local development!**

This Terraform configuration sets up a complete LOCAL development database environment using Docker containers on your local machine for PostgreSQL, Redis, and ClickHouse.

## Prerequisites

- Docker Desktop installed and running
- Terraform >= 1.0 installed
- For Windows: Docker Desktop with WSL2 backend (recommended)
- For Linux/Mac: Docker daemon running

## Quick Start

1. **Initialize Terraform:**
   ```bash
   cd terraform-dev-postgres
   terraform init
   ```

2. **Review the planned infrastructure:**
   ```bash
   terraform plan
   ```

3. **Create the development databases:**
   ```bash
   terraform apply -auto-approve
   ```

4. **Use the generated configuration:**
   - The `.env.development.local` file is automatically created in the project root
   - Connection details are saved in `connection_info.txt`

## What Gets Created

### Containers
- **PostgreSQL 14**: Main database on port 5432
- **Redis 7**: Cache and session storage on port 6379
- **ClickHouse**: Analytics database on ports 8123 (HTTP) and 9000 (native)

### Volumes
- Persistent data volumes for each database
- Data persists between container restarts

### Network
- `netra-dev-network`: Docker network for container communication

### Configuration Files
- `.env.development.local`: Auto-generated environment variables
- `connection_info.txt`: All connection details and passwords

## Default Ports

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Database connections |
| Redis | 6379 | Cache/sessions |
| ClickHouse HTTP | 8123 | HTTP interface |
| ClickHouse Native | 9000 | Native protocol |

## Managing the Infrastructure

### Start/Create
```bash
terraform apply
```

### Stop/Destroy
```bash
terraform destroy
```

### View Database Logs
```bash
docker logs netra-postgres-dev
docker logs netra-redis-dev
docker logs netra-clickhouse-dev
```

### Connect to PostgreSQL
```bash
# Using psql
psql -h localhost -p 5432 -U postgres -d netra_dev

# Connection string (check connection_info.txt for password)
postgresql://postgres:PASSWORD@localhost:5432/netra_dev
```

### Connect to Redis
```bash
# Using redis-cli
redis-cli -h localhost -p 6379

# Connection string
redis://localhost:6379/0
```

### Connect to ClickHouse
```bash
# Using clickhouse-client
clickhouse-client --host localhost --port 9000

# HTTP interface
curl http://localhost:8123/

# Connection string (check connection_info.txt for credentials)
clickhouse://default:PASSWORD@localhost:9000/netra_dev
```

## Customization

### Change Ports
Edit `terraform.tfvars`:
```hcl
postgres_port = 5433  # Different port
redis_port = 6380
```

### Change Database Names
```hcl
postgres_db = "my_custom_db"
clickhouse_db = "my_analytics"
```

### Platform-Specific Docker Host

#### Windows (default)
```hcl
docker_host = "npipe:////./pipe/docker_engine"
```

#### Linux/Mac
```hcl
docker_host = "unix:///var/run/docker.sock"
```

## Integration with Application

### Automatic Configuration
The Terraform setup automatically generates `.env.development.local` with all connection strings.

### Manual Configuration
Copy values from `connection_info.txt` to your `.env.development` file.

### Docker Compose Alternative
If you prefer docker-compose, the generated environment can be accessed using the container names:
- `netra-postgres-dev`
- `netra-redis-dev`
- `netra-clickhouse-dev`

## Troubleshooting

### Docker Not Running
```
Error: Cannot connect to Docker daemon
```
**Solution**: Start Docker Desktop

### Port Already in Use
```
Error: bind: address already in use
```
**Solution**: Change the port in `variables.tf` or stop the conflicting service

### Container Health Check Failing
Check logs:
```bash
docker logs netra-postgres-dev
```

### Reset Everything
```bash
# Destroy all resources
terraform destroy -auto-approve

# Remove volumes (WARNING: Deletes all data)
docker volume rm netra-postgres-dev-data
docker volume rm netra-redis-dev-data
docker volume rm netra-clickhouse-dev-data

# Recreate
terraform apply -auto-approve
```

## Security Notes

- Passwords are randomly generated and stored in `connection_info.txt`
- The `.env.development.local` file contains sensitive data - don't commit it
- Add `*.local` and `connection_info.txt` to `.gitignore`

## Database Initialization

PostgreSQL is initialized with:
- UTF-8 encoding
- Extensions: uuid-ossp, pgcrypto, pg_trgm
- Application user: `netra_app`
- Test database: `netra_test`
- Performance tuning for development

## Backup and Restore

### Backup PostgreSQL
```bash
docker exec netra-postgres-dev pg_dump -U postgres netra_dev > backup.sql
```

### Restore PostgreSQL
```bash
docker exec -i netra-postgres-dev psql -U postgres netra_dev < backup.sql
```

### Backup Redis
```bash
docker exec netra-redis-dev redis-cli SAVE
docker cp netra-redis-dev:/data/dump.rdb ./redis-backup.rdb
```

### Backup ClickHouse
```bash
docker exec netra-clickhouse-dev clickhouse-backup create
```

## Performance Monitoring

### PostgreSQL Statistics
```sql
-- Connect to PostgreSQL
SELECT * FROM pg_stat_activity;
SELECT * FROM pg_stat_database WHERE datname = 'netra_dev';
```

### Redis Info
```bash
redis-cli INFO
```

### ClickHouse System Tables
```sql
SELECT * FROM system.metrics;
SELECT * FROM system.query_log;
```

## Next Steps

1. Run `terraform apply` to create the infrastructure
2. Update your application to use `.env.development.local`
3. Run database migrations if needed
4. Start developing!

## Support

For issues or questions:
1. Check `docker logs [container-name]`
2. Review `connection_info.txt` for correct credentials
3. Ensure Docker Desktop is running
4. Check the main project documentation