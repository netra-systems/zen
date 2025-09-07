# ClickHouse Configuration Loading Flow Analysis

## THE PROBLEM: Staging Gets Wrong Configuration

The staging environment is getting `localhost:8124` instead of `xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443`

---

## CURRENT BROKEN FLOW

```mermaid
graph TD
    Start[Application Starts in Staging] --> GetConfig[get_clickhouse_config]
    GetConfig --> GetUnified[get_configuration]
    GetUnified --> LoadBase[Load StagingConfig class]
    
    LoadBase --> CheckMode{Check config.clickhouse_mode}
    
    CheckMode -->|"Default: 'shared'"| UseHTTPS[Use config.clickhouse_https]
    
    UseHTTPS --> Problem1[❌ PROBLEM: clickhouse_https is EMPTY]
    Problem1 --> Why1[WHY: populate_database_config not called yet]
    
    Why1 --> ExtractConfig[_extract_clickhouse_config]
    ExtractConfig --> CheckEnv{Check environment}
    
    CheckEnv -->|staging| CheckMode2{Check clickhouse_mode}
    CheckMode2 -->|"shared (not 'local')"| ReturnHTTPS[Return config.clickhouse_https]
    
    ReturnHTTPS --> Empty[❌ Returns EMPTY config object]
    Empty --> Default[Falls back to development defaults]
    Default --> Wrong[Uses localhost:8124]
    
    style Problem1 fill:#ff6666
    style Empty fill:#ff6666
    style Wrong fill:#ff6666
```

## WHY IT BREAKS - DETAILED

### Step 1: Configuration Class Initialization
- `StagingConfig` class is instantiated with DEFAULT values
- `clickhouse_mode = "shared"` (default)
- `clickhouse_https` = Empty ClickHouseHTTPSConfig object

### Step 2: ClickHouse Code Requests Config TOO EARLY
- `get_clickhouse_config()` is called BEFORE `populate_database_config()`
- The config object exists but has NO actual values

### Step 3: Wrong Branch Taken
- Since `clickhouse_mode = "shared"` (not "local"), it uses `clickhouse_https`
- But `clickhouse_https` is empty because population hasn't happened yet

### Step 4: No Staging-Specific Handling
- The `_extract_clickhouse_config()` function only handles:
  - `testing` → TestClickHouseConfig (hardcoded)
  - `development` → DevClickHouseConfig (hardcoded)
  - Everything else → Uses config.clickhouse_http or config.clickhouse_https
- **NO SPECIAL HANDLING FOR STAGING!**

---

## THE ROOT CAUSE

```mermaid
sequenceDiagram
    participant App
    participant ClickHouse as clickhouse.py
    participant ConfigMgr as UnifiedConfigManager
    participant DBMgr as DatabaseConfigManager
    participant Env as Environment/Secrets
    
    App->>ClickHouse: get_clickhouse_client()
    ClickHouse->>ClickHouse: get_clickhouse_config()
    ClickHouse->>ConfigMgr: get_configuration()
    
    Note over ConfigMgr: Creates StagingConfig with DEFAULTS
    ConfigMgr-->>ClickHouse: Returns config (UNPOPULATED)
    
    ClickHouse->>ClickHouse: _extract_clickhouse_config()
    Note over ClickHouse: Staging not handled!
    Note over ClickHouse: Falls through to clickhouse_https
    Note over ClickHouse: But it's EMPTY!
    
    ClickHouse-->>App: Returns empty/wrong config
    
    Note over DBMgr: populate_database_config() NEVER CALLED!
    Note over Env: CLICKHOUSE_URL never loaded!
```

---

## FIXED FLOW - SOLUTION

```mermaid
graph TD
    Start[Application Starts in Staging] --> GetConfig[get_clickhouse_config]
    GetConfig --> GetUnified[get_configuration]
    GetUnified --> LoadComplete[Load COMPLETE configuration]
    
    LoadComplete --> Pop1[1. Create StagingConfig base]
    Pop1 --> Pop2[2. populate_database_config]
    Pop2 --> Pop3[3. Load CLICKHOUSE_URL from env]
    Pop3 --> Pop4[4. Parse and set clickhouse_https values]
    
    Pop4 --> ExtractConfig[_extract_clickhouse_config]
    ExtractConfig --> CheckEnv{Check environment}
    
    CheckEnv -->|staging| NewHandler[✅ NEW: Staging Handler]
    
    NewHandler --> LoadFromEnv[Load from Environment]
    LoadFromEnv --> ParseURL[Parse CLICKHOUSE_URL]
    ParseURL --> CreateConfig[Create StagingClickHouseConfig]
    
    CreateConfig --> SetValues[Set Correct Values:<br/>host: xedvrr4c3r.us-central1.gcp.clickhouse.cloud<br/>port: 8443<br/>secure: true]
    
    SetValues --> Success[✅ Returns correct config]
    
    style NewHandler fill:#66ff66
    style Success fill:#66ff66
```

---

## THE FIX IMPLEMENTATION

### Fix 1: Add Staging Handler in `_extract_clickhouse_config`

```python
def _extract_clickhouse_config(config):
    """Extract appropriate ClickHouse configuration from unified config based on mode."""
    
    # Handle testing environment
    if config.environment == "testing":
        # ... existing test config ...
        return TestClickHouseConfig()
    
    # Handle development environment    
    elif config.environment == "development":
        # ... existing dev config ...
        return DevClickHouseConfig()
    
    # ✅ NEW: Handle staging environment explicitly
    elif config.environment == "staging":
        class StagingClickHouseConfig:
            def __init__(self):
                from shared.isolated_environment import get_env
                env = get_env()
                
                # Load ClickHouse URL from environment
                clickhouse_url = env.get("CLICKHOUSE_URL", "")
                
                if not clickhouse_url:
                    # CRITICAL: Must have ClickHouse URL in staging
                    raise ConfigurationError(
                        "CLICKHOUSE_URL not set in staging environment. "
                        "Expected: clickhouse://user:pass@host:8443/db?secure=1"
                    )
                
                # Parse the URL
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(clickhouse_url)
                query_params = parse_qs(parsed.query)
                
                self.host = parsed.hostname or "xedvrr4c3r.us-central1.gcp.clickhouse.cloud"
                self.port = parsed.port or 8443
                self.user = parsed.username or "default"
                self.password = parsed.password or env.get("CLICKHOUSE_PASSWORD", "")
                self.database = parsed.path.lstrip('/') or "default"
                self.secure = query_params.get('secure', ['1'])[0] == '1'
                
                logger.info(f"[ClickHouse Staging Config] Using host={self.host}, port={self.port}, secure={self.secure}")
        
        return StagingClickHouseConfig()
    
    # Handle production (existing fallback logic)
    # ... rest of existing code ...
```

### Fix 2: Ensure Population Happens BEFORE Use

```python
# In UnifiedConfigManager._load_complete_configuration()
def _load_complete_configuration(self) -> AppConfig:
    """Load complete configuration from all sources."""
    config = self._create_base_config()
    
    # CRITICAL: Populate BEFORE anyone can use it
    self._populate_configuration_data(config)  # ← This MUST happen
    
    # Now config.clickhouse_https has actual values
    self._validate_final_config(config)
    
    return config
```

### Fix 3: Add Staging URL Loading in DatabaseConfigManager

```python
def _set_clickhouse_url(self, config: AppConfig) -> None:
    """Set unified ClickHouse URL for external integrations."""
    
    clickhouse_url = self._env.get("CLICKHOUSE_URL")
    
    if self._environment == "staging":
        if not clickhouse_url:
            # In staging, we MUST have ClickHouse Cloud URL
            raise ConfigurationError(
                "CLICKHOUSE_URL required in staging. "
                "Set to: clickhouse://default:PASSWORD@xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/default?secure=1"
            )
        
        # Parse and populate clickhouse_https from URL
        from urllib.parse import urlparse
        parsed = urlparse(clickhouse_url)
        
        config.clickhouse_https.host = parsed.hostname
        config.clickhouse_https.port = parsed.port or 8443
        config.clickhouse_https.user = parsed.username or "default"
        config.clickhouse_https.password = parsed.password or ""
        config.clickhouse_https.database = parsed.path.lstrip('/') or "default"
        
    config.clickhouse_url = clickhouse_url
```

---

## VERIFICATION CHECKLIST

- [ ] `_extract_clickhouse_config` has explicit staging handler
- [ ] Staging handler loads from CLICKHOUSE_URL environment variable
- [ ] Staging handler parses URL correctly
- [ ] Password is loaded from GCP Secret Manager if not in URL
- [ ] Config returns ClickHouse Cloud host, not localhost
- [ ] Port is 8443, not 8124
- [ ] secure=True for HTTPS connection
- [ ] Connection test passes with real ClickHouse Cloud

---

## ENVIRONMENT VARIABLES REQUIRED

For staging deployment:
```bash
ENVIRONMENT=staging
CLICKHOUSE_URL=clickhouse://default:PASSWORD@xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/default?secure=1
# OR separate components:
CLICKHOUSE_HOST=xedvrr4c3r.us-central1.gcp.clickhouse.cloud
CLICKHOUSE_PORT=8443
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=<from-secret-manager>
CLICKHOUSE_DB=default
CLICKHOUSE_SECURE=true
```

---

## CONCLUSION

The issue is **NOT** SSOT violations or recursion. The issue is:

1. **Missing staging-specific handler** in `_extract_clickhouse_config`
2. **Config requested before population** - timing issue
3. **No URL parsing for staging** - just returns empty config

The fix is straightforward: Add explicit staging handling that loads and parses CLICKHOUSE_URL.