# String Literals Index

**The SSOT for all string literals in the Netra platform codebase - preventing LLM hallucination and config cascade failures.**

> 🚨 **CRITICAL**: This index is your first line of defense against config regressions and cascade failures. ALWAYS validate literals before use!

*Generated on 2025-01-09*

## 🎯 Quick Start Guide

### ✅ How to Check if a String Literal Exists

**Before using ANY string literal in your code, validate it exists:**

```bash
# Validate a specific literal
python scripts/query_string_literals.py validate "SOMETHING"

# Search for similar literals
python scripts/query_string_literals.py search "database" --category critical_config

# Check environment-specific configs
python scripts/query_string_literals.py check-env staging
```

### 🔍 Common Use Cases

| **Task** | **Command** | **Example** |
|----------|-------------|-------------|
| **Validate before use** | `validate "literal"` | `python scripts/query_string_literals.py validate "NEXT_PUBLIC_API_URL"` |
| **Find similar configs** | `search "keyword"` | `python scripts/query_string_literals.py search "jwt" --category critical_config` |
| **List all in category** | `list --category name` | `python scripts/query_string_literals.py list --category critical_config` |
| **Check env health** | `check-env environment` | `python scripts/query_string_literals.py check-env staging` |
| **Show all critical** | `show-critical` | `python scripts/query_string_literals.py show-critical` |

## 📊 Current Statistics

| Metric | Value |
|--------|-------|
| **Files Scanned** | 2,872 |
| **Total Literals Found** | 205,821 |
| **Unique Literals** | 85,493 |
| **Critical Configs** | 11 |
| **Critical Domains** | 12 (4 per env) |
| **Categories** | 14 |

### 🚨 Critical Protection Status

- **Environment Variables**: 11 mission-critical configs protected
- **Domain Configurations**: 4 environments × 4 domains each = 12 critical domains
- **Cascade Failure Prevention**: ✅ Active
- **Cross-References**: Linked to MISSION_CRITICAL_NAMED_VALUES_INDEX.xml

## 📋 Navigation

- [🚨 Critical Configuration](#critical-configuration) - **MISSION CRITICAL**
- [📊 Quick Reference](#quick-reference)
- [🏗️ Categories Overview](#categories-overview)
- [🛠️ Usage Examples](#usage-examples)
- [🔗 Cross-References](#cross-references)

### 🚨 Critical Configuration {#critical-configuration}

**⚠️ WARNING**: These configurations can cause CASCADE FAILURES if modified incorrectly!

#### Critical Environment Variables
- `REDIS_URL` - Redis connection strings for ALL environments  
- `JWT_SECRET_KEY` - Authentication secrets for ALL environments
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - OAuth credentials
- `NEXT_PUBLIC_API_URL` - Frontend API endpoints
- `NEXT_PUBLIC_WS_URL` - WebSocket endpoints
- `NEXT_PUBLIC_AUTH_URL` - Authentication service endpoints
- `ENVIRONMENT` - Environment identification

#### Critical Domains by Environment

**Staging**:
- Frontend: `app.staging.netrasystems.ai`
- API: `api.staging.netrasystems.ai` 
- Auth: `auth.staging.netrasystems.ai`
- WebSocket: `wss://api.staging.netrasystems.ai`

**Production**:
- Frontend: `app.netrasystems.ai`
- API: `api.netrasystems.ai`
- Auth: `auth.netrasystems.ai`
- WebSocket: `wss://api.netrasystems.ai`

**Development/Local**:
- Frontend: `localhost:3000`
- API: `localhost:8000`
- Auth: `localhost:8081` 
- WebSocket: `ws://localhost:8000`

> **🔍 Validate Critical Configs**: `python scripts/query_string_literals.py show-critical`

## 📊 Quick Reference {#quick-reference}

### Most Important Categories

| Category | Count | Description | Risk Level |
|----------|-------|-------------|------------|
| **critical_config** | 11 | 🚨 Mission-critical environment variables | **CRITICAL** |
| **critical_domain_***| 12 | 🚨 Environment-specific domains | **CRITICAL** |
| **configuration** | 968 | System configuration keys | High |
| **paths** | 1,375 | API endpoints, file paths | High |
| **identifiers** | 37,662 | Component names, class names | Medium |
| **messages** | 23,353 | Log messages, user text | Medium |
| **database** | 322 | Table names, SQL keywords | Medium |
| **environment** | 178 | Environment-specific configs | High |
| **events** | 36 | WebSocket events, handlers | High |
| **states** | 30 | Status values, boolean states | Medium |
| **metrics** | 262 | Performance monitoring | Low |
| **test_literals** | 21,284 | Test-specific strings | Low |

### 🔍 Search Patterns

**Use these search patterns to find what you need:**

```bash
# Find environment variables
python scripts/query_string_literals.py search "_URL" --category environment

# Find API endpoints 
python scripts/query_string_literals.py search "/api/" --category paths

# Find database elements
python scripts/query_string_literals.py search "SELECT" --category database

# Find WebSocket events
python scripts/query_string_literals.py search "websocket" --category events

# Find configuration keys
python scripts/query_string_literals.py search "config" --category configuration
```

## 🏗️ Categories Overview {#categories-overview}

**The string literals are organized into the following categories:**

### 🚨 Critical Categories (Mission Critical)

| Category | Count | Description |
|----------|-------|-------------|
| **critical_config** | 11 | Environment variables that cause cascade failures |
| **critical_domain_staging** | 4 | Staging environment domains |
| **critical_domain_production** | 4 | Production environment domains |
| **critical_domain_development** | 4 | Development environment domains |

### 🔧 System Categories (High Importance)

| Category | Count | Description |
|----------|-------|-------------|
| **configuration** | 968 | System configuration keys and settings |
| **paths** | 1,375 | API endpoints, file paths, directories |
| **environment** | 178 | Environment-specific configuration |
| **database** | 322 | Table names, SQL keywords, queries |
| **events** | 36 | WebSocket events and handlers |
| **states** | 30 | Status values and boolean states |
| **metrics** | 262 | Performance monitoring data |

### 📝 Content Categories (Medium Importance)

| Category | Count | Description |
|----------|-------|-------------|
| **identifiers** | 37,662 | Component names, class names, functions |
| **messages** | 23,353 | Log messages, user text, notifications |
| **test_literals** | 21,284 | Test-specific strings and data |

### 📋 Sub-Index Access

**Each category has detailed sub-indexes for efficient querying:**

```bash
# Access specific category data
cat SPEC/generated/sub_indexes/critical_config.json
cat SPEC/generated/sub_indexes/paths.json

# Or use compact versions for quick lookup
cat SPEC/generated/compact/critical_config.json
```

## 🛠️ Usage Examples {#usage-examples}

### Example 1: Validating Critical Environment Variables

# Check if all staging configs are present
python scripts/query_string_literals.py check-env staging
# Shows missing/found variables and domains
```

### Example 2: Finding API Endpoints

```bash
# Find all WebSocket endpoints
python scripts/query_string_literals.py search "websocket" --category paths

# Find specific API paths
python scripts/query_string_literals.py search "/api/v" --category paths
```

### Example 3: Discovering Similar Configs

```bash
# Find JWT-related configs
python scripts/query_string_literals.py search "jwt" 



### Example 4: Environment Health Checks

```bash
# Check all critical configs at once
python scripts/query_string_literals.py show-critical

# Validate specific environment
python scripts/query_string_literals.py check-env production
# Shows: Status: HEALTHY/CRITICAL with missing items
```

## 🔗 Cross-References {#cross-references}

### 📚 Related Documentation

- **[MISSION_CRITICAL_NAMED_VALUES_INDEX.xml](../SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml)** - Master index of cascade failure values
- **[CONFIG_REGRESSION_PREVENTION_PLAN.md](../reports/config/CONFIG_REGRESSION_PREVENTION_PLAN.md)** - Config regression prevention strategies  
- **[OAUTH_REGRESSION_ANALYSIS_20250905.md](../reports/auth/OAUTH_REGRESSION_ANALYSIS_20250905.md)** - OAuth configuration issues analysis
- **[Configuration Architecture](../docs/configuration_architecture.md)** - Complete system configuration architecture

### 🛠️ Tools and Scripts

- **[Query Tool](../scripts/query_string_literals.py)** - Search and validate literals
- **[Scanner Tool](../scripts/scan_string_literals.py)** - Generate fresh indexes
- **[Sub-Indexes](../SPEC/generated/sub_indexes/)** - Category-specific data files
- **[Compact Indexes](../SPEC/generated/compact/)** - Quick lookup files

### 🔄 Integration Points

- **CLAUDE.md Execution Checklist** - Step 6: "Verify Strings"
- **Definition of Done Checklist** - String literal validation requirements
- **Type Safety Validation** - Cross-reference with type drift audits
- **Environment Configuration** - Links to isolated environment management

## 📋 Maintenance

### 🔄 Refreshing the Index

```bash
# Full refresh (recommended weekly)
python scripts/scan_string_literals.py --verbose

# Include test files if needed
python scripts/scan_string_literals.py --include-tests

# Check statistics after refresh
python scripts/query_string_literals.py stats
```

### ⚠️ Critical Warnings

1. **NEVER delete critical configs** without checking `MISSION_CRITICAL_NAMED_VALUES_INDEX.xml`
2. **Environment configs are NOT duplicates** - each environment needs independent configs
3. **Hex strings are valid secrets** (from `openssl rand -hex 32`) - don't invalidate them
4. **Domain mismatches should warn in non-prod**, not fail entirely

---

*This index is automatically generated and cross-referenced with mission-critical documentation.*  
*Last updated: 2025-01-09 | Index Version: 3.1.0 | Files: 2,872 | Literals: 85,493*

**🔍 Quick Tools**: [Query](../scripts/query_string_literals.py) | [Scan](../scripts/scan_string_literals.py) | [Validate](../scripts/query_string_literals.py validate) | [Stats](../scripts/query_string_literals.py stats)