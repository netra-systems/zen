# ClickHouse Connection Audit Report

## Executive Summary
The ClickHouse connection is failing in the Netra backend due to multiple configuration mismatches between the Docker container setup and the application configuration.

## Issues Identified

### 1. Port Configuration Mismatch
**Issue**: Application attempting to connect to wrong port
- **Development Docker Container**: Running on port `8124`  
- **Application Configuration**: Incorrectly using port `8125` (test environment port) for development
- **Location**: `netra_backend/app/db/clickhouse.py:171` - Hardcoded test port being used

### 2. Authentication Credentials Mismatch
**Issue**: Wrong credentials being used
- **Docker Container Credentials**: `netra` / `netra123`
- **Application Credentials**: Using environment variable defaults that don't match
- **Container Configuration**: Creates user 'netra' instead of 'default' user

### 3. Environment Variable Configuration
**Current Environment Variables**:
```
CLICKHOUSE_URL: clickhouse://netra:netra123@localhost:8123/netra_analytics
CLICKHOUSE_HOST: localhost
CLICKHOUSE_USER: netra
CLICKHOUSE_DB: netra_analytics
CLICKHOUSE_MODE: local
DEV_MODE_CLICKHOUSE_ENABLED: false
```

**Issues**:
- `CLICKHOUSE_URL` uses port 8123 (wrong for dev environment)
- `DEV_MODE_CLICKHOUSE_ENABLED` is set to false, potentially causing graceful degradation

### 4. Configuration Source Conflicts
The configuration is loaded from multiple sources with conflicting values:
1. Environment variables (via IsolatedEnvironment)
2. Hardcoded defaults in `database.py`
3. Docker-specific overrides in `clickhouse.py`
4. Development/test environment detection logic

## Root Cause Analysis

### Primary Root Cause
The main issue is a **configuration synchronization problem** between:
1. Docker Compose port mappings (dev: 8124, test: 8125)
2. Application configuration defaults
3. Environment variable settings

### Secondary Issues
1. **Testing vs Development Environment Detection**: The code path for determining which port to use is based on environment detection, but the logic is inconsistent
2. **Graceful Degradation Logic**: The code allows ClickHouse to fail silently in development mode, masking configuration issues

## Recommendations

### Immediate Fix
1. **Set correct environment variables**:
   ```bash
   CLICKHOUSE_HTTP_PORT=8124
   CLICKHOUSE_PASSWORD=netra123
   ```

2. **Update configuration loading logic** in `database.py`:
   - Line 391: Change default development port from 8125 to 8124
   - Ensure proper credential loading from environment

### Long-term Improvements
1. **Centralize ClickHouse configuration** in a single location
2. **Add validation** to ensure Docker container configuration matches application configuration
3. **Improve error messages** to clearly indicate configuration mismatches
4. **Document** the correct environment variables in `.env.example`

## Docker Container Status
```
Container: netra-dev-clickhouse
Status: Running (healthy)
Port Mapping: 0.0.0.0:8124->8123/tcp
User: netra
Password: netra123
Database: netra_analytics
```

## Test Connection Command
To verify ClickHouse connectivity:
```bash
docker exec netra-dev-clickhouse clickhouse-client --user netra --password netra123 -q "SELECT 1"
```

## Impact
- **Development Environment**: ClickHouse features unavailable
- **Startup Process**: ClickHouse initialization fails but is marked as optional (Phase 7)
- **Data Analytics**: Unable to store or retrieve analytics data
- **Performance Monitoring**: Metrics collection disabled

## Resolution Status
- [x] Identified port mismatch (8124 vs 8125)
- [x] Identified credential mismatch
- [x] Located configuration sources
- [x] Verified Docker container is healthy
- [ ] Applied configuration fixes
- [ ] Tested end-to-end connectivity

## Next Steps
1. Apply the immediate fixes to environment variables
2. Update the configuration loading logic
3. Test the connection with corrected configuration
4. Verify ClickHouse table initialization
5. Document the correct configuration in project documentation