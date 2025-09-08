# Auth Service Database Configuration

## Overview
The auth service uses DatabaseURLBuilder SSOT for database connections:
1. **Auth Database** - For auth-specific data (users, sessions, audit logs)
2. **Main Database Sync** - For syncing users to the main application database

## Environment Variables

### Database Configuration (DatabaseURLBuilder SSOT)
The auth service uses DatabaseURLBuilder to construct database URLs from component parts:

**Postgres Component Variables:**
- `POSTGRES_HOST` - Database host (required)
- `POSTGRES_PORT` - Database port (default: 5432)
- `POSTGRES_USER` - Database user (required)
- `POSTGRES_PASSWORD` - Database password (required)
- `POSTGRES_DB` - Database name (required)
- `ENVIRONMENT` - Environment (test/development/staging/production)

**Legacy Support:**
- `DATABASE_URL` - Direct URL override (takes precedence when set)

### Main Database (User Sync)
- `MAIN_DATABASE_URL` - Primary main app database URL (recommended for clarity)

## Deployment Configuration



### Google Cloud Run (Staging/Production)
Set these environment variables in your Cloud Run service:

```yaml
env:
  # DatabaseURLBuilder SSOT approach (recommended)
  - name: POSTGRES_HOST
    value: "/cloudsql/project:region:instance"
  - name: POSTGRES_USER
    value: "auth_user"
  - name: POSTGRES_PASSWORD
    value: "secure_password"
  - name: POSTGRES_DB
    value: "auth_db"
  - name: ENVIRONMENT
    value: "production"
  # Main database for user sync
  - name: MAIN_DATABASE_URL
    value: "postgresql://user:password@/apex_db?host=/cloudsql/project:region:instance"
```

### Terraform Configuration
Add to your Terraform variables:

```hcl
resource "google_cloud_run_service" "auth_service" {
  template {
    spec {
      containers {
        # DatabaseURLBuilder SSOT approach
        env {
          name  = "POSTGRES_HOST"
          value = var.postgres_host
        }
        env {
          name  = "POSTGRES_USER"
          value = var.postgres_user
        }
        env {
          name  = "POSTGRES_PASSWORD"
          value = var.postgres_password
        }
        env {
          name  = "POSTGRES_DB"
          value = var.postgres_db
        }
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        env {
          name  = "MAIN_DATABASE_URL"
          value = var.main_database_url
        }
      }
    }
  }
}
```

## Key Features

### Cloud Run Optimizations
- Uses `NullPool` for connection pooling (required for serverless)
- Lazy initialization to reduce cold start impact
- Proper connection cleanup on shutdown

### Connection Management
- Single shared engine instance per database
- Automatic retry and reconnection handling
- Session-level transaction management

### Security
- Supports Cloud SQL proxy connections
- SSL/TLS encryption when configured
- No hardcoded credentials

## Troubleshooting

### Connection Issues
1. Check environment variables are set correctly
2. Verify Cloud SQL proxy is running (for Cloud Run)
3. Check database user permissions
4. Review logs for connection errors

### Performance
- The `NullPool` is essential for Cloud Run to prevent connection exhaustion
- Each request creates a new connection (serverless pattern)
- Connection overhead is minimal with Cloud SQL proxy