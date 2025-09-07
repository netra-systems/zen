# ClickHouse Error Code 60 Remediation Plan

## Executive Summary
ClickHouse is failing with error code 60 (UNKNOWN_TABLE) in staging, but the error handling and logging make it appear as an authentication/connection issue, leading to incorrect debugging paths.

## Why Error Appears as Authentication

### Root Cause of Confusion
1. **Error Occurs During Connection Phase**
   - Tables are queried immediately after connection
   - When table queries fail, it appears as "connection failed"
   - Developers assume connection failures = authentication issues

2. **Generic Error Handling**
   ```python
   # Current code in clickhouse.py line 541
   logger.error(f"[ClickHouse] REAL connection failed in {environment}: {str(e)}")
   ```
   - Logs all errors as "connection failed"
   - Doesn't distinguish between auth errors (516) and table errors (60)

3. **Circuit Breaker Obscures Real Error**
   - Circuit breaker opens after initial failures
   - Subsequent requests show "circuit open" instead of real error
   - Original error code 60 gets buried

4. **Silent Failure in Staging**
   ```python
   # Line 544-546
   if environment == "staging":
       logger.warning("[ClickHouse] Connection failed in staging (optional service)")
       return  # Never raise in staging
   ```
   - Staging swallows errors for "graceful degradation"
   - Real error never propagates up

## Immediate Remediation (Phase 1)

### Step 1: Add Loud Error Differentiation
```python
def _handle_connection_error(e: Exception):
    """Handle ClickHouse connection error with LOUD, CLEAR error messages."""
    from shared.isolated_environment import get_env
    import clickhouse_connect.driver.exceptions as ch_exc
    
    environment = get_env().get("ENVIRONMENT", "development").lower()
    
    # LOUD ERROR DIFFERENTIATION
    if "error code 60" in str(e).lower() or "unknown_table" in str(e).lower():
        logger.error("🔴🔴🔴 CLICKHOUSE TABLE MISSING ERROR 🔴🔴🔴")
        logger.error(f"ERROR CODE 60: Tables do not exist in database!")
        logger.error(f"This is NOT an authentication issue!")
        logger.error(f"Required tables are missing. Run table initialization.")
        logger.error(f"Full error: {str(e)}")
    elif "error code 516" in str(e).lower() or "authentication failed" in str(e).lower():
        logger.error("🔴🔴🔴 CLICKHOUSE AUTHENTICATION ERROR 🔴🔴🔴")
        logger.error(f"ERROR CODE 516: Authentication failed!")
        logger.error(f"Check credentials in Secret Manager")
        logger.error(f"Full error: {str(e)}")
    else:
        logger.error("🔴🔴🔴 CLICKHOUSE CONNECTION ERROR 🔴🔴🔴")
        logger.error(f"Environment: {environment}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Full error: {str(e)}")
```

### Step 2: Force Table Creation on Startup
```python
# In main.py startup
async def ensure_clickhouse_tables():
    """Ensure all required ClickHouse tables exist - LOUD FAILURES."""
    try:
        async with get_clickhouse_client() as client:
            tables_to_create = [
                ("agent_state_history", AGENT_STATE_HISTORY_SCHEMA),
                ("events", EVENTS_TABLE_SCHEMA),
                ("metrics", METRICS_TABLE_SCHEMA),
                ("netra_logs", LOGS_TABLE_SCHEMA),
                ("netra_global_supply_catalog", SUPPLY_TABLE_SCHEMA),
                ("workload_events", WORKLOAD_EVENTS_TABLE_SCHEMA),
            ]
            
            for table_name, schema in tables_to_create:
                try:
                    await client.execute(schema)
                    logger.info(f"✅ ClickHouse table ensured: {table_name}")
                except Exception as e:
                    logger.error(f"🔴 FAILED TO CREATE TABLE {table_name}: {e}")
                    # Continue trying other tables
                    
    except Exception as e:
        logger.error("🔴🔴🔴 CLICKHOUSE TABLE INITIALIZATION FAILED 🔴🔴🔴")
        logger.error(f"Error: {e}")
        # Don't crash in staging, but make it VERY obvious
        if environment == "staging":
            logger.error("⚠️ CONTINUING WITHOUT CLICKHOUSE - ANALYTICS DISABLED")
        else:
            raise
```

### Step 3: Manual Table Creation Script
Create `scripts/create_clickhouse_tables.py`:
```python
#!/usr/bin/env python
"""
Manual ClickHouse table creation for production/staging.
Run this directly against ClickHouse Cloud to create required tables.
"""

import clickhouse_connect
from netra_backend.app.db.models_clickhouse import (
    LOGS_TABLE_SCHEMA,
    SUPPLY_TABLE_SCHEMA,
    WORKLOAD_EVENTS_TABLE_SCHEMA,
    get_llm_events_table_schema,
    get_content_corpus_schema
)

def create_tables():
    # Get credentials from environment or command line
    client = clickhouse_connect.get_client(
        host='xedvrr4c3r.us-central1.gcp.clickhouse.cloud',
        port=8443,
        username='default',
        password='6a_z1t0qQ1.ET',  # From Secret Manager
        secure=True,
        database='default'
    )
    
    tables = [
        LOGS_TABLE_SCHEMA,
        SUPPLY_TABLE_SCHEMA,
        WORKLOAD_EVENTS_TABLE_SCHEMA,
        get_llm_events_table_schema("llm_events"),
        """CREATE TABLE IF NOT EXISTS agent_state_history (
            run_id String,
            thread_id String,
            user_id String,
            agent_type String,
            timestamp DateTime64(3),
            event_type String,
            state_data String,
            metadata String
        ) ENGINE = MergeTree()
        ORDER BY (timestamp, run_id)""",
        # Add other required tables
    ]
    
    for schema in tables:
        try:
            client.execute(schema)
            print(f"✅ Created table from schema")
        except Exception as e:
            print(f"❌ Failed: {e}")

if __name__ == "__main__":
    create_tables()
```

## Long-term Fix (Phase 2)

### 1. Error Code Mapping
```python
CLICKHOUSE_ERROR_CODES = {
    60: ("UNKNOWN_TABLE", "Table does not exist - run table initialization"),
    516: ("AUTHENTICATION_FAILED", "Invalid credentials - check Secret Manager"),
    210: ("TIMEOUT_EXCEEDED", "Query timeout - check performance"),
    # Add other codes
}

def interpret_clickhouse_error(e: Exception) -> tuple[int, str, str]:
    """Extract and interpret ClickHouse error codes."""
    error_str = str(e)
    for code, (name, message) in CLICKHOUSE_ERROR_CODES.items():
        if f"code {code}" in error_str.lower():
            return code, name, message
    return 0, "UNKNOWN", error_str
```

### 2. Startup Health Check
```python
class ClickHouseHealthCheck:
    """Comprehensive ClickHouse health check with detailed reporting."""
    
    async def check_connection(self) -> bool:
        """Test basic connectivity."""
        pass
    
    async def check_authentication(self) -> bool:
        """Verify credentials work."""
        pass
    
    async def check_tables_exist(self) -> dict[str, bool]:
        """Check each required table exists."""
        pass
    
    async def run_full_check(self) -> HealthCheckResult:
        """Run all checks and return detailed report."""
        return HealthCheckResult(
            connected=self.check_connection(),
            authenticated=self.check_authentication(),
            tables=self.check_tables_exist(),
            recommendation=self.get_recommendation()
        )
```

### 3. Conditional Table Creation
```python
# In configuration
CLICKHOUSE_AUTO_CREATE_TABLES = env.get("CLICKHOUSE_AUTO_CREATE_TABLES", "true")
CLICKHOUSE_FAIL_ON_MISSING_TABLES = env.get("CLICKHOUSE_FAIL_ON_MISSING_TABLES", "false")

# In startup
if CLICKHOUSE_AUTO_CREATE_TABLES:
    await ensure_clickhouse_tables()
elif CLICKHOUSE_FAIL_ON_MISSING_TABLES:
    if not await check_tables_exist():
        raise RuntimeError("Required ClickHouse tables missing")
```

## Testing Plan

### 1. Local Testing
```bash
# Test with missing tables
docker-compose exec clickhouse-server clickhouse-client -q "DROP TABLE IF EXISTS events"
python tests/test_clickhouse_error_handling.py

# Verify loud error appears
grep "ERROR CODE 60" logs/backend.log
```

### 2. Staging Validation
```bash
# Deploy with new error handling
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Check logs for clear errors
gcloud logging read "ERROR CODE 60" --project=netra-staging

# Manually create tables
python scripts/create_clickhouse_tables.py --env staging
```

## Success Criteria

1. **Clear Error Messages**
   - Error code 60 shows "TABLE MISSING" not "connection failed"
   - Developers immediately know to create tables

2. **Automatic Recovery**
   - Tables created automatically on startup (when enabled)
   - System continues without ClickHouse if optional

3. **Monitoring**
   - Health check endpoint reports table status
   - Alerts fire when tables are missing

## Rollback Plan

If remediation causes issues:
1. Set `CLICKHOUSE_AUTO_CREATE_TABLES=false`
2. Revert error handling changes
3. Document manual table creation requirement

## Timeline

- **Immediate (Today)**: 
  - Deploy loud error logging
  - Run manual table creation script
  
- **Week 1**:
  - Implement automatic table creation
  - Add health checks
  
- **Week 2**:
  - Monitor and refine
  - Document learnings

## Key Insight

The confusion stems from treating all ClickHouse errors as "connection failures" when they should be categorized:
- **Authentication errors** (code 516) → Check credentials
- **Table errors** (code 60) → Create tables  
- **Network errors** → Check connectivity
- **Permission errors** → Check user grants

Making these distinctions LOUD and CLEAR will prevent future debugging confusion.