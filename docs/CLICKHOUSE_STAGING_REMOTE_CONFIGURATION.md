# ClickHouse Staging/Production Remote Configuration

## CRITICAL: ClickHouse is a REMOTE Service in Staging/Production

Unlike local development where ClickHouse runs in a Docker container, **staging and production environments use a REMOTE ClickHouse Cloud instance**.

## Key Configuration Details

### Remote ClickHouse Cloud Instance
- **Service Type:** ClickHouse Cloud (SaaS)
- **Location:** Remote cloud instance (NOT a local container)
- **Region:** us-central1 (GCP)
- **Protocol:** HTTPS (port 8443)

### Google Secret Manager Storage
The complete ClickHouse connection URL is stored as a single secret in Google Secret Manager:

**Secret Name:** `clickhouse-url-staging` (for staging)
**Secret Name:** `clickhouse-url-production` (for production)

**Format:**
```
https://[username]:[password]@[cluster-id].us-central1.gcp.clickhouse.cloud:8443/[database]
```

### Example URL Structure
```
https://default:6a_z1t0qQ1.ET@xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/default
```

## Configuration Flow

```mermaid
graph TD
    A[Google Secret Manager] -->|Fetch CLICKHOUSE_URL| B[Backend Service]
    B --> C[Parse URL for Connection]
    C --> D[Connect to Remote ClickHouse Cloud]
    
    E[Note: No local ClickHouse container]
    F[Note: Full URL with credentials in single secret]
```

## Key Files Updated

1. **`netra_backend/app/core/configuration/secrets.py`**
   - Added `CLICKHOUSE_URL` to secret mappings
   - Added `_get_clickhouse_url_mapping()` method
   - Updated environment variable mappings

2. **`shared/secret_mappings.py`**
   - Added `clickhouse-url-staging` mapping
   - Added `clickhouse-url-production` mapping
   - Marked individual ClickHouse components as legacy/backup

3. **`netra_backend/app/core/configuration/staging_validator.py`**
   - Added `CLICKHOUSE_URL` to CRITICAL_VARIABLES list

4. **`docs/configuration_architecture.md`**
   - Added section 3.1: ClickHouse Configuration in Staging/Production
   - Added mermaid diagram showing remote configuration flow

## Important Notes

### Why a Single URL Secret?
- **Simplicity:** One secret to manage instead of 5+ individual components
- **Security:** Complete connection string is atomic and can be rotated easily
- **Compatibility:** Works directly with ClickHouse client libraries
- **Cloud-Native:** Matches how ClickHouse Cloud provides connection strings

### Migration from Individual Secrets
The codebase still supports individual secrets (host, port, user, password, database) for backward compatibility, but the preferred method for staging/production is the single `CLICKHOUSE_URL` secret.

### Local Development
Local development continues to use Docker containers and can use either:
- Individual environment variables (CLICKHOUSE_HOST, CLICKHOUSE_PORT, etc.)
- A local CLICKHOUSE_URL pointing to `localhost`

## Troubleshooting

### Error Code 60 (UNKNOWN_TABLE)
This error indicates the remote ClickHouse Cloud instance is accessible but tables don't exist. Solutions:
1. Run table creation scripts against the remote instance
2. Use the ClickHouse Cloud console to create tables
3. Ensure initialization code runs on startup

### Connection Issues
1. Verify the CLICKHOUSE_URL secret exists in Google Secret Manager
2. Check Cloud Run service account has Secret Manager access
3. Confirm the URL format is correct (https, port 8443)
4. Test connection using ClickHouse Cloud console

## Security Considerations

- **Never log the full CLICKHOUSE_URL** as it contains credentials
- Rotate the URL secret periodically through Google Secret Manager
- Use separate secrets for staging and production
- Ensure Cloud Run service account has minimal required permissions