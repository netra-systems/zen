# String Literals Index - Navigation Hub

**Complete cross-referenced navigation for the String Literals Index system**

## 🚀 Quick Start

**New to string literals validation? Start here:**

1. **[Usage Guide](./STRING_LITERALS_USAGE_GUIDE.md)** - Step-by-step how-to guide
2. **[Complete Index](./string_literals_index.md)** - Full documentation with statistics
3. **[CLAUDE.md Integration](#claude-md-integration)** - How this fits into the execution checklist

## 📁 File Structure

```
docs/
├── string_literals_index.md              # Main documentation with statistics
├── STRING_LITERALS_USAGE_GUIDE.md        # How-to guide for daily usage
└── STRING_LITERALS_INDEX_NAVIGATION.md   # This navigation file

scripts/
├── scan_string_literals.py              # Generate/refresh indexes
└── query_string_literals.py             # Query and validate literals

SPEC/
└── generated/
    ├── string_literals.json             # Main index file
    ├── sub_indexes/                      # Category-specific indexes
    │   ├── critical_config.json
    │   ├── critical_domain_staging.json
    │   ├── paths.json
    │   └── ... (14 total categories)
    └── compact/                          # Compact lookup files
        ├── critical_config.json
        ├── paths.json
        └── ... (14 total categories)
```

## 🔧 Core Tools

### Primary Commands

| Command | Purpose | Example |
|---------|---------|---------|
| **validate** | Check if literal exists | `python scripts/query_string_literals.py validate "DATABASE_URL"` |
| **search** | Find similar literals | `python scripts/query_string_literals.py search "jwt" --category critical_config` |
| **show-critical** | Show all critical configs | `python scripts/query_string_literals.py show-critical` |
| **check-env** | Environment health check | `python scripts/query_string_literals.py check-env staging` |
| **stats** | Index statistics | `python scripts/query_string_literals.py stats` |
| **refresh** | Update index | `python scripts/scan_string_literals.py --verbose` |

### Advanced Usage

```bash
# List all literals in a category
python scripts/query_string_literals.py list --category critical_config

# Search with category filter
python scripts/query_string_literals.py search "websocket" --category events

# Include test files when scanning
python scripts/scan_string_literals.py --include-tests

# Search specific directories only
python scripts/scan_string_literals.py --dirs netra_backend/app auth_service
```

## 🚨 Critical Configurations

### Environment Variables (11 Critical)

**Database & Infrastructure:**
- `DATABASE_URL` - Database connections
- `REDIS_URL` - Redis connections

**Authentication:**
- `JWT_SECRET_KEY` - JWT secrets
- `GOOGLE_CLIENT_ID` - OAuth client ID
- `GOOGLE_CLIENT_SECRET` - OAuth client secret

**Frontend API Endpoints:**
- `NEXT_PUBLIC_API_URL` - Main API endpoint
- `NEXT_PUBLIC_WS_URL` - WebSocket endpoint
- `NEXT_PUBLIC_AUTH_URL` - Auth service endpoint
- `NEXT_PUBLIC_WEBSOCKET_URL` - WebSocket URL (alternative)

**Environment Control:**
- `NEXT_PUBLIC_ENVIRONMENT` - Frontend environment
- `ENVIRONMENT` - Backend environment

### Domain Configurations (12 Critical)

**Staging (4 domains):**
- `app.staging.netrasystems.ai`
- `api.staging.netrasystems.ai`
- `auth.staging.netrasystems.ai`
- `wss://api.staging.netrasystems.ai`

**Production (4 domains):**
- `app.netrasystems.ai`
- `api.netrasystems.ai`
- `auth.netrasystems.ai`
- `wss://api.netrasystems.ai`

**Development/Local (4 domains):**
- `localhost:3000`
- `localhost:8000`
- `localhost:8081`
- `ws://localhost:8000`

## 📋 Category Breakdown

| Category | Count | Risk | Description |
|----------|-------|------|-------------|
| **critical_config** | 11 | 🚨 CRITICAL | Mission-critical environment variables |
| **critical_domain_***| 12 | 🚨 CRITICAL | Environment-specific domains |
| **configuration** | 968 | HIGH | System configuration keys |
| **paths** | 1,375 | HIGH | API endpoints, file paths |
| **environment** | 178 | HIGH | Environment-specific configs |
| **identifiers** | 37,662 | MEDIUM | Component names, classes |
| **messages** | 23,353 | MEDIUM | Log messages, user text |
| **database** | 322 | MEDIUM | SQL keywords, table names |
| **events** | 36 | HIGH | WebSocket events |
| **states** | 30 | MEDIUM | Status values, booleans |
| **metrics** | 262 | LOW | Performance monitoring |
| **test_literals** | 21,284 | LOW | Test-specific strings |

## 🔗 CLAUDE.md Integration

### Section 4.1: String Literals Index
- **Purpose**: Prevent LLM hallucination with SSOT literals
- **Key files**: Index, query tool, documentation
- **Critical protection**: 11 env vars + 12 domains

### Section 9 Step 6: Verify Strings (Execution Checklist)
**MANDATORY validation process:**

1. **NEVER guess string literals**
2. **Always validate**: `python scripts/query_string_literals.py validate "literal"`
3. **Search for existing**: `python scripts/query_string_literals.py search "keyword"`
4. **Check environment health**: `python scripts/query_string_literals.py check-env staging`
5. **Review critical configs**: `python scripts/query_string_literals.py show-critical`

## 🔄 Cross-References

### Related CLAUDE.md Sections
- **Section 2**: Config SSOT warnings and regression prevention
- **Section 4**: Knowledge management and SSOT principles
- **Section 8**: Detailed specifications reference table
- **Section 9**: Complete execution checklist

### Related Documentation
- **[MISSION_CRITICAL_NAMED_VALUES_INDEX.xml](../SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml)** - Master cascade failure index
- **[CONFIG_REGRESSION_PREVENTION_PLAN.md](../reports/config/CONFIG_REGRESSION_PREVENTION_PLAN.md)** - Config safety strategies
- **[Configuration Architecture](./configuration_architecture.md)** - System config management

### Related System Components
- **Type Safety Validation** - Cross-reference with type drift audits
- **Environment Management** - Links to isolated environment patterns
- **Definition of Done Checklist** - String validation requirements
- **Test Framework** - E2E auth helper and real service patterns

## 📈 Usage Statistics

**Current Index (Generated 2025-01-09):**
- **Files Scanned**: 2,872
- **Total Literals**: 205,821
- **Unique Literals**: 85,493
- **Categories**: 14
- **Critical Protections**: 23 (11 env vars + 12 domains)

## 🚨 Warning Patterns

### ❌ NEVER DO:
```python
# Don't guess or hardcode without validation
DATABASE_URL = "postgresql://..."  # ❌
API_ENDPOINT = "/api/users"        # ❌
```

### ✅ ALWAYS DO:
```bash
# First validate
python scripts/query_string_literals.py validate "DATABASE_URL"
python scripts/query_string_literals.py validate "/api/users"
```

## 🛠️ Maintenance

### Daily Usage
- Validate all string literals before use
- Check environment health when deploying
- Search for existing patterns before creating new ones

### Weekly Maintenance
```bash
# Refresh index with latest changes
python scripts/scan_string_literals.py --include-tests --verbose

# Check critical configs
python scripts/query_string_literals.py show-critical

# Environment health checks
python scripts/query_string_literals.py check-env staging
python scripts/query_string_literals.py check-env production
```

### After Code Changes
```bash
# Refresh index if new literals were added
python scripts/scan_string_literals.py

# Verify new literals exist
python scripts/query_string_literals.py validate "NEW_LITERAL"

# Check statistics
python scripts/query_string_literals.py stats
```

---

**🔍 Quick Navigation**:
[Usage Guide](./STRING_LITERALS_USAGE_GUIDE.md) | [Full Index](./string_literals_index.md) | [CLAUDE.md](../CLAUDE.md#string-literals-index-preventing-hallucination) | [Tools](../scripts/)

*This navigation hub provides complete cross-referencing for the String Literals Index system as mandated by CLAUDE.md Section 4.1 and Execution Checklist Step 6.*