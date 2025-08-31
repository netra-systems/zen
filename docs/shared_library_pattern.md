# Shared Library Pattern: When Shared Code is GOOD

## Quick Reference: The "Pip Package" Test

**Simple Rule:** If the code could be published as a pip package, it can go in `/shared`.

## ✅ GOOD Shared Code (Infrastructure Libraries)

These are like internal versions of external libraries:

### Examples of GOOD Shared Code

1. **`shared.isolated_environment`** - Environment variable management
   - Like: `python-dotenv`, `environs`
   - Why Good: Pure utility, no business logic, enables testing isolation

2. **Database URL builders** - String manipulation utilities
   - Like: Database connection string libraries
   - Why Good: Pure transformation, no state, prevents bugs

3. **JSON Schemas** - Data contracts
   - Like: OpenAPI specifications
   - Why Good: Defines interfaces, no behavior

4. **String utilities** - Generic helpers
   - Like: Standard library extensions
   - Why Good: Pure functions, no business logic

## ❌ BAD Shared Code (Business Logic & State)

These violate service independence:

### Examples of BAD Shared Code

1. **User authentication logic**
   - Why Bad: Core business logic
   - Solution: Use auth service API

2. **Redis connection managers**
   - Why Bad: Stateful, service-specific config
   - Solution: Each service has its own

3. **Agent orchestration logic**
   - Why Bad: Business behavior
   - Solution: Keep in main backend

4. **Service configurations**
   - Why Bad: Service-specific, couples deployments
   - Solution: Each service owns its config

## The Key Distinction

### Infrastructure Libraries (GOOD for /shared)
- **No business logic** - Pure utilities
- **Stateless** - Or per-process singleton like IsolatedEnvironment
- **Stable interfaces** - Rarely change
- **Universal** - Used identically across services
- **Like external libraries** - Could be pip packages

### Service Logic (BAD for /shared)
- **Business rules** - How the business works
- **Stateful components** - Connections, caches
- **Service-specific** - Unique to one service
- **Frequently changing** - Evolving with features
- **Coupling risk** - Forces coordinated deployments

## Real Example: IsolatedEnvironment

```python
# ✅ GOOD - Infrastructure library pattern
from shared.isolated_environment import get_env

class AuthServiceConfig:
    def __init__(self):
        # Using shared library for infrastructure
        self.env = get_env()
        
        # Service owns its configuration values
        self.jwt_secret = self.env.get("JWT_SECRET")
        self.database_url = self.env.get("AUTH_DATABASE_URL")
```

This is GOOD because:
- `isolated_environment` is a pure utility (like python-dotenv)
- Auth service still owns its configuration
- No business logic is shared
- Services remain independently deployable

## Mental Model

Think of `/shared` as your organization's unpublished pip packages:

```
/shared/
├── isolated_environment.py    # Could be: pip install netra-env
├── database_url_builder.py    # Could be: pip install netra-db-utils
├── schemas/                   # Could be: pip install netra-schemas
└── utils/string_utils.py      # Could be: pip install netra-utils
```

## Quick Decision Tree

1. **Could this be a pip package?** → If no, don't share
2. **Does it contain business logic?** → If yes, don't share
3. **Is it stateful?** → If yes, don't share
4. **Will it change frequently?** → If yes, don't share
5. **Is it truly universal?** → If no, don't share

If you passed all checks → Can go in /shared

## Remember

- **Service independence is paramount** - When in doubt, don't share
- **Duplication is OK** - Better than hidden coupling
- **Infrastructure ≠ Business** - Share utilities, not logic
- **Think "library"** - If it's not library-like, it doesn't belong in /shared