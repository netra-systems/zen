# String Literals Usage Guide

**CRITICAL: Follow this guide exactly as specified in CLAUDE.md Step 6: "Verify Strings"**

## 🚨 MANDATORY: Before Using ANY String Literal

**NEVER guess or assume string literals exist. ALWAYS validate first!**

### Step 1: Quick Validation

```bash
# Before using any config value in code
python scripts/query_string_literals.py validate "YOUR_STRING_HERE"
```

**Example - Validating DATABASE_URL before use:**
```bash
python scripts/query_string_literals.py validate "DATABASE_URL"
# ✅ [VALID] 'DATABASE_URL' - Category: critical_config
# ⚠️  CRITICAL CONFIG! See MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
```

**Example - Invalid string:**
```bash
python scripts/query_string_literals.py validate "NONEXISTENT_CONFIG"
# ❌ [INVALID] 'NONEXISTENT_CONFIG'
# 💡 Did you mean: DATABASE_URL, REDIS_URL?
```

## 🔍 Common Usage Patterns

### Pattern 1: Finding Environment Variables

```bash
# Find all URL-related configs
python scripts/query_string_literals.py search "_URL" --category environment

# Find all API endpoints
python scripts/query_string_literals.py search "/api/" --category paths

# Find all JWT-related configs
python scripts/query_string_literals.py search "JWT" --category critical_config
```

### Pattern 2: Validating Environment Health

```bash
# Check if all required configs exist for staging
python scripts/query_string_literals.py check-env staging

# Check production environment
python scripts/query_string_literals.py check-env production
```

### Pattern 3: Discovering Available Options

```bash
# Show all critical configurations
python scripts/query_string_literals.py show-critical

# List all literals in a specific category
python scripts/query_string_literals.py list --category critical_config

# Get overall statistics
python scripts/query_string_literals.py stats
```

## 🚨 CRITICAL CONFIG PROTECTION

**These configs cause CASCADE FAILURES if modified incorrectly:**

### Environment Variables (11 Critical)
- `DATABASE_URL` - Database connections for ALL environments
- `REDIS_URL` - Redis connections for ALL environments
- `JWT_SECRET_KEY` - Authentication secrets
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - OAuth credentials
- `NEXT_PUBLIC_API_URL` - Frontend API endpoints
- `NEXT_PUBLIC_WS_URL` - WebSocket endpoints
- `NEXT_PUBLIC_AUTH_URL` - Auth service endpoints
- `NEXT_PUBLIC_ENVIRONMENT` - Environment identification
- `NEXT_PUBLIC_WEBSOCKET_URL` - WebSocket URL
- `ENVIRONMENT` - Server environment identification

### Domain Protection by Environment

**Staging Domains (4):**
- `app.staging.netrasystems.ai` - Frontend
- `api.staging.netrasystems.ai` - API
- `auth.staging.netrasystems.ai` - Auth
- `wss://api.staging.netrasystems.ai` - WebSocket

**Production Domains (4):**
- `app.netrasystems.ai` - Frontend
- `api.netrasystems.ai` - API
- `auth.netrasystems.ai` - Auth
- `wss://api.netrasystems.ai` - WebSocket

**Development/Local Domains (4):**
- `localhost:3000` - Frontend
- `localhost:8000` - API
- `localhost:8081` - Auth
- `ws://localhost:8000` - WebSocket

## 📋 Integration with CLAUDE.md Workflow

### Execution Checklist Step 6: "Verify Strings"

**BEFORE making any code changes involving string literals:**

1. **Validate each literal**: `python scripts/query_string_literals.py validate "literal"`
2. **Check for suggestions if invalid**: Tool provides "Did you mean" suggestions
3. **Verify environment health**: `python scripts/query_string_literals.py check-env <environment>`
4. **Cross-reference critical configs**: See `MISSION_CRITICAL_NAMED_VALUES_INDEX.xml`

### Common Integration Scenarios

#### Scenario 1: Adding New Environment Variable
```bash
# 1. Check if it already exists
python scripts/query_string_literals.py validate "NEW_CONFIG_VAR"

# 2. Search for similar existing configs
python scripts/query_string_literals.py search "CONFIG" --category environment

# 3. After adding, refresh the index
python scripts/scan_string_literals.py
```

#### Scenario 2: Modifying API Endpoints
```bash
# 1. Find existing API paths
python scripts/query_string_literals.py search "/api/" --category paths

# 2. Validate specific endpoint
python scripts/query_string_literals.py validate "/api/v2/agents"

# 3. Check for WebSocket paths too
python scripts/query_string_literals.py search "websocket" --category paths
```

#### Scenario 3: Environment-Specific Configurations
```bash
# 1. Check current environment health
python scripts/query_string_literals.py check-env staging

# 2. Show all critical configs for reference
python scripts/query_string_literals.py show-critical

# 3. Validate specific environment domains
python scripts/query_string_literals.py validate "api.staging.netrasystems.ai"
```

## ⚠️ WARNING PATTERNS TO AVOID

### ❌ NEVER DO THIS:
```python
# DON'T guess or hardcode without validation
DATABASE_URL = "postgresql://..."  # ❌ Not validated!
API_ENDPOINT = "/api/v1/users"     # ❌ Not validated!
```

### ✅ ALWAYS DO THIS:
```bash
# First validate
python scripts/query_string_literals.py validate "DATABASE_URL"
python scripts/query_string_literals.py validate "/api/v1/users"
```

Then use in code:
```python
# Only after validation confirms they exist
DATABASE_URL = env.get("DATABASE_URL")
API_ENDPOINT = "/api/v1/users"  # ✅ Validated first!
```

## 🔄 Maintenance and Updates

### After Making Changes to String Literals

```bash
# 1. Refresh the index to include new literals
python scripts/scan_string_literals.py --verbose

# 2. Verify the changes were captured
python scripts/query_string_literals.py stats

# 3. Validate your new literals exist
python scripts/query_string_literals.py validate "YOUR_NEW_LITERAL"
```

### Weekly Maintenance (Recommended)

```bash
# Full refresh including test files
python scripts/scan_string_literals.py --include-tests --verbose

# Check for any new critical configs
python scripts/query_string_literals.py show-critical

# Validate environment health across all environments
python scripts/query_string_literals.py check-env staging
python scripts/query_string_literals.py check-env production
```

## 🔗 Cross-References

### Related CLAUDE.md Sections:
- **Section 4.1**: String Literals Index: Preventing Hallucination
- **Section 9**: Execution Checklist - Step 6: "Verify Strings"
- **Critical Values Check**: Step 2: CHECK CRITICAL VALUES

### Related Documentation:
- **[MISSION_CRITICAL_NAMED_VALUES_INDEX.xml](../SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml)** - Master index of cascade failure values
- **[String Literals Index](./string_literals_index.md)** - Complete documentation and statistics
- **[Configuration Architecture](./configuration_architecture.md)** - System-wide config management

### Related Tools:
- **[Query Tool](../scripts/query_string_literals.py)** - Primary validation tool
- **[Scanner Tool](../scripts/scan_string_literals.py)** - Index generation tool
- **[Generated Index](../SPEC/generated/string_literals.json)** - Raw index data

## 📞 Quick Reference Commands

```bash
# Essential daily commands
python scripts/query_string_literals.py validate "STRING"           # Validate single literal
python scripts/query_string_literals.py search "KEYWORD"            # Search for similar
python scripts/query_string_literals.py show-critical               # Show all critical configs
python scripts/query_string_literals.py check-env staging           # Environment health check
python scripts/query_string_literals.py stats                       # Index statistics
python scripts/scan_string_literals.py                              # Refresh index
```

---

**🚨 REMEMBER**: This is STEP 6 in the CLAUDE.md execution checklist. **NEVER skip string literal validation!**

*This guide enforces the CLAUDE.md requirement: "ALWAYS Validate literals before use, using either grep or: `python scripts/query_string_literals.py validate "your_string"`"*