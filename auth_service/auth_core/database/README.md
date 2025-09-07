# Auth Service Database Configuration

## Overview
The auth service uses two database connections:
1. **Auth Database** - For auth-specific data (users, sessions, audit logs)
2. **Main Database Sync** - For syncing users to the main application database

## Environment Variables


### Main Database (User Sync)
- `MAIN_DATABASE_URL` - Primary main app database URL (recommended for clarity)

## Deployment Configuration



### Google Cloud Run (Staging/Production)
Set these environment variables in your Cloud Run service:

```yaml
env:
  - name: DATABASE_URL
    value: "postgresql://user:password@/auth_db?host=/cloudsql/project:region:instance"
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
        env {
          name  = "DATABASE_URL"
          value = var.DATABASE_URL
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