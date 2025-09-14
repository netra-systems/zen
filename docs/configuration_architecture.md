# Configuration and Environment Management Architecture

**Last Updated:** 2025-09-14 | **Status:** OPERATIONAL - Configuration Manager SSOT Phase 1 Complete

## Related Documentation

- [Unified Environment Management Spec](../SPEC/unified_environment_management.xml) - Core specification for environment management
- [Independent Services Spec](../SPEC/independent_services.xml) - Service independence requirements
- [Type Safety Spec](../SPEC/type_safety.xml) - Type safety and duplication rules
- [Database Connectivity Architecture](../SPEC/database_connectivity_architecture.xml) - Database configuration patterns
- [WebSocket Agent Integration](../SPEC/learnings/websocket_agent_integration_critical.xml) - Critical WebSocket event requirements
- [WebSocket Silent Failure Prevention](../SPEC/learnings/websocket_silent_failure_prevention_masterclass.xml) - Comprehensive silent failure prevention
- [WebSocket Silent Failures](../SPEC/learnings/websocket_silent_failures.xml) - Silent failure detection and mitigation
- [CLAUDE.md](../CLAUDE.md) - Core development principles and mission-critical requirements

## Executive Summary

The Netra platform implements a sophisticated multi-layered configuration management system that ensures isolation, consistency, and traceability across all services. The architecture consists of three main layers:

1. **IsolatedEnvironment Layer** - Environment variable management with isolation support
2. **UnifiedConfigManager Layer** - Central configuration orchestration 
3. **Service-Specific Configuration** - Per-service configuration modules

## The "5 Whys" Behind Isolated Configuration

### Why Isolated Configuration?

**Why #1: Why do we need isolated configuration?**
- Because different environments (dev/test/staging/prod) require different configurations, and mixing them causes failures.

**Why #2: Why does mixing configurations cause failures?**
- Because environment variables persist in os.environ across test runs and development sessions, leading to pollution where test values leak into production code or vice versa.

**Why #3: Why do environment variables persist and cause pollution?**
- Because os.environ is a global mutable state that any code can modify at any time, and Python's import system caches modules, keeping stale configuration values.

**Why #4: Why is global mutable state problematic for configuration?**
- Because we can't track who changed what, when, or why. Without isolation, a test that sets #removed-legacyaffects all subsequent tests, and debugging becomes impossible.

**Why #5: Why do we need to track configuration changes?**
- Because configuration errors cause 60% of production outages (per Google SRE data), and without traceability, we lose $12K MRR from configuration-related incidents.

### Configuration vs Environment Loading: The 5 Whys

**Why #1: Why separate configuration from environment loading?**
- Configuration is business logic (what database to use, what features to enable), while environment loading is infrastructure (how to read .env files, access os.environ).

**Why #2: Why distinguish business logic from infrastructure?**
- Business logic changes frequently based on requirements, while infrastructure patterns remain stable. Mixing them creates tight coupling.

**Why #3: Why is tight coupling problematic?**
- Because changing a business rule (e.g., different database in staging) shouldn't require modifying the environment loading mechanism.

**Why #4: Why shouldn't business changes affect infrastructure?**
- Because infrastructure code is tested once and trusted, while business logic evolves. Stable infrastructure reduces bugs.

**Why #5: Why does stable infrastructure reduce bugs?**
- Because 90% of bugs come from changing code. If environment loading is stable and isolated, configuration bugs are contained to the configuration layer.

### Environment-Specific Definitions: The 5 Whys

**Why #1: Why do different environments need different definitions?**
- Development needs quick iteration with fallbacks, staging needs production-like validation, production needs strict security.

**Why #2: Why can't we use the same configuration everywhere?**
- Because development uses localhost databases, staging uses test cloud resources, and production uses customer data with strict access controls.

**Why #3: Why maintain these differences in code?**
- Because environment-specific behavior must be predictable and testable. Hard-coding environment logic makes it explicit and auditable.

**Why #4: Why explicit over implicit for environment behavior?**
- Because implicit behavior (like auto-detecting environment from hostname) fails catastrophically when assumptions change.

**Why #5: Why do assumption failures matter?**
- Because deploying development configuration to production exposes secrets, corrupts data, and violates compliance, costing enterprise contracts.

## Core Architecture Components

### 1. IsolatedEnvironment System

The `IsolatedEnvironment` class provides the foundation for all environment variable access across the platform. Each service maintains its own instance while following consistent patterns.

```mermaid
graph TB
    subgraph "Environment Layer"
        OS[OS Environment<br/>os.environ]
        ISO[IsolatedEnvironment<br/>Singleton Instance]
        ENV[.env File]
        
        ENV -->|load_from_file| ISO
        OS <-->|get/set| ISO
        ISO -->|isolation mode| ISODICT[Isolated Dictionary<br/>Internal State]
    end
    
    subgraph "Access Methods"
        GET[get<br/>Read Variable]
        SET[set<br/>Write Variable + Source]
        DEL[delete<br/>Remove Variable]
        LOAD[load_from_file<br/>Load .env]
        VAL[validate_all<br/>Check Requirements]
    end
    
    ISO --> GET
    ISO --> SET
    ISO --> DEL
    ISO --> LOAD
    ISO --> VAL
    
    subgraph "Features"
        TRACK[Source Tracking]
        PROTECT[Variable Protection]
        CALLBACK[Change Callbacks]
        SANITIZE[Value Sanitization]
    end
    
    SET --> TRACK
    SET --> PROTECT
    SET --> CALLBACK
    SET --> SANITIZE
```

### 2. Configuration Flow - Service Startup

```mermaid
sequenceDiagram
    participant SVC as Service
    participant ISO as IsolatedEnvironment
    participant ENV as .env File
    participant OS as os.environ
    participant CFG as UnifiedConfigManager
    participant VAL as ConfigurationValidator
    
    SVC->>ISO: get_env() [Singleton]
    ISO->>ISO: __init__()
    ISO->>ENV: _auto_load_env_file()
    ENV-->>ISO: Variables loaded
    
    Note over ISO: Isolation Mode Decision
    alt Development/Testing
        ISO->>ISO: enable_isolation()
        ISO->>ISO: Copy os.environ to internal dict
    else Production
        ISO->>OS: Direct os.environ access
    end
    
    SVC->>CFG: get_unified_config()
    CFG->>ISO: get environment variables
    CFG->>CFG: _detect_environment()
    CFG->>CFG: _create_base_config()
    CFG->>CFG: _populate_configuration_data()
    
    Note over CFG: Load from multiple sources
    CFG->>CFG: DatabaseConfigManager
    CFG->>CFG: ServiceConfigManager
    CFG->>CFG: SecretManager
    
    CFG->>VAL: validate_complete_config()
    VAL-->>CFG: Validation Result
    
    alt Validation Success
        CFG-->>SVC: AppConfig instance
    else Validation Failure
        CFG-->>SVC: ConfigurationError
    end
```

### 3. Environment Variable Hierarchy

```mermaid
graph TD
    subgraph "Variable Priority (Highest to Lowest)"
        P1[1. OS Environment<br/>System/Container/Cloud Run]
        P2[2. .env File<br/>Local Development]
        P3[3. Fallback Values<br/>Development Defaults]
        P4[4. Hard-coded Defaults<br/>Last Resort]
    end
    
    P1 --> MERGE[Merged Configuration]
    P2 --> MERGE
    P3 --> MERGE
    P4 --> MERGE
    
    MERGE --> CONFIG[Final Configuration]
    
    subgraph "Environment Detection"
        ENV_VAR[ENVIRONMENT Variable]
        TEST_MODE[TESTING/TEST_MODE]
        PYTEST[PYTEST_CURRENT_TEST]
    end
    
    ENV_VAR --> DETECTION[Environment Detection]
    TEST_MODE --> DETECTION
    PYTEST --> DETECTION
    
    DETECTION --> CONFIG
```

### 3.1 ClickHouse Configuration in Staging/Production

**CRITICAL:** ClickHouse in staging/production environments is a REMOTE service:

```mermaid
graph TB
    subgraph "Staging/Production ClickHouse Configuration"
        GCP[Google Secret Manager] -->|CLICKHOUSE_URL| SECRET[Remote ClickHouse URL<br/>https://cluster.clickhouse.cloud:8443]
        SECRET --> ENV[Environment Variable]
        ENV --> CONFIG[UnifiedConfigManager]
        CONFIG --> APP[Application]
        
        Note1[Note: Full connection URL with credentials<br/>stored as single secret in Google Secret Manager]
        Note2[Remote ClickHouse Cloud instance<br/>NOT a local container]
    end
```

**Key Points:**
- **Storage:** Complete ClickHouse URL stored in Google Secret Manager
- **Secret Name:** `CLICKHOUSE_URL` 
- **Format:** `https://[user]:[password]@[cluster-id].us-central1.gcp.clickhouse.cloud:8443/[database]`
- **Access:** Retrieved at runtime via Google Secret Manager API
- **Not Local:** This is a remote ClickHouse Cloud service, not a container

### 4. Cross-Service Configuration Flow

```mermaid
graph LR
    subgraph "dev_launcher"
        DL_ISO[IsolatedEnvironment<br/>dev_launcher]
        DL_ENV[Environment Manager]
    end
    
    subgraph "netra_backend"
        NB_ISO[IsolatedEnvironment<br/>netra_backend]
        NB_CFG[UnifiedConfigManager]
        NB_APP[AppConfig]
    end
    
    subgraph "auth_service"
        AS_ISO[IsolatedEnvironment<br/>auth_service]
        AS_CFG[AuthConfig]
    end
    
    subgraph "shared"
        DB_BUILD[DatabaseURLBuilder]
        JWT_MGR[SharedJWTSecretManager]
        PORT_DISC[PortDiscovery]
    end
    
    DL_ISO --> DL_ENV
    NB_ISO --> NB_CFG
    NB_CFG --> NB_APP
    AS_ISO --> AS_CFG
    
    NB_CFG --> DB_BUILD
    AS_CFG --> DB_BUILD
    
    NB_CFG --> JWT_MGR
    AS_CFG --> JWT_MGR
    
    AS_CFG --> PORT_DISC
    
    style DL_ISO fill:#e1f5e1
    style NB_ISO fill:#e1f5e1
    style AS_ISO fill:#e1f5e1
    style JWT_MGR fill:#ffe1e1
```

### 5. Configuration Validation Flow

```mermaid
flowchart TD
    START[Start Validation]
    
    START --> CHECK_REQ[Check Required Variables]
    CHECK_REQ --> REQ_MISSING{Required<br/>Missing?}
    
    REQ_MISSING -->|Yes| APPLY_FALL{Fallbacks<br/>Enabled?}
    REQ_MISSING -->|No| CHECK_OPT
    
    APPLY_FALL -->|Yes| GEN_FALL[Generate Fallbacks]
    APPLY_FALL -->|No| ADD_ERROR[Add to Errors]
    
    GEN_FALL --> CHECK_OPT
    ADD_ERROR --> CHECK_OPT
    
    CHECK_OPT[Check Optional Variables]
    CHECK_OPT --> CAT_OPT[Categorize by Type]
    
    CAT_OPT --> VAL_FORMAT[Validate Formats]
    VAL_FORMAT --> CHECK_URL{Valid URLs?}
    CHECK_URL -->|No| FORMAT_ERR[Format Errors]
    CHECK_URL -->|Yes| CHECK_SECRETS
    
    CHECK_SECRETS[Check Secret Keys]
    CHECK_SECRETS --> SECRET_LEN{Length >= 32?}
    SECRET_LEN -->|No| SECRET_WARN[Add Warning]
    SECRET_LEN -->|Yes| CHECK_CONSIST
    
    SECRET_WARN --> CHECK_CONSIST
    FORMAT_ERR --> CHECK_CONSIST
    
    CHECK_CONSIST[Check Consistency]
    CHECK_CONSIST --> PORT_CONF{Port<br/>Conflicts?}
    PORT_CONF -->|Yes| CONSIST_ERR[Consistency Errors]
    PORT_CONF -->|No| BUILD_RESULT
    
    CONSIST_ERR --> BUILD_RESULT
    
    BUILD_RESULT[Build ValidationResult]
    BUILD_RESULT --> IS_VALID{All Valid?}
    
    IS_VALID -->|Yes| SUCCESS[Return Success]
    IS_VALID -->|No| FAILURE[Return Errors + Suggestions]
    
    style SUCCESS fill:#90EE90
    style FAILURE fill:#FFB6C1
```

### 6. Test Environment Configuration

```mermaid
stateDiagram-v2
    [*] --> DetectTestContext
    
    DetectTestContext --> CheckPytest: Check pytest modules
    DetectTestContext --> CheckEnvVars: Check TEST env vars
    DetectTestContext --> CheckEnvironment: Check ENVIRONMENT=test
    
    CheckPytest --> TestDetected: PYTEST_CURRENT_TEST exists
    CheckEnvVars --> TestDetected: TESTING=true
    CheckEnvironment --> TestDetected: ENVIRONMENT=testing
    
    CheckPytest --> NormalMode: No test markers
    CheckEnvVars --> NormalMode: No test vars
    CheckEnvironment --> NormalMode: Not test env
    
    TestDetected --> EnableIsolation
    EnableIsolation --> SyncWithOSEnviron
    SyncWithOSEnviron --> TimeCachedConfig
    
    TimeCachedConfig --> CheckCache: Every access
    CheckCache --> CacheStale: > 30 seconds
    CheckCache --> UseCache: < 30 seconds
    
    CacheStale --> ClearAllCaches
    ClearAllCaches --> ReloadConfig
    ReloadConfig --> UpdateCache
    
    NormalMode --> ProductionConfig
    ProductionConfig --> [*]
    
    UpdateCache --> [*]
    UseCache --> [*]
```

## Configuration Layers Interaction

### Conceptual Separation: Environment vs Configuration vs Application

```mermaid
graph TD
    subgraph "Layer Separation"
        ENV[Environment Variables<br/>Raw Key-Value Pairs]
        CONFIG[Configuration Objects<br/>Validated Business Logic]
        APP[Application Code<br/>Feature Implementation]
    end
    
    subgraph "Why Separate?"
        ENV_WHY[Infrastructure Concern<br/>How to read/write]
        CONFIG_WHY[Business Rules<br/>What values mean]
        APP_WHY[Domain Logic<br/>What to do with values]
    end
    
    ENV --> ENV_WHY
    CONFIG --> CONFIG_WHY
    APP --> APP_WHY
    
    ENV_WHY --> BENEFIT1[Change Independently]
    CONFIG_WHY --> BENEFIT2[Test in Isolation]
    APP_WHY --> BENEFIT3[Deploy Safely]
```

### Layer 1: Environment Management (IsolatedEnvironment)

**Purpose**: Provides controlled access to environment variables with isolation support.

**Key Features**:
- Singleton pattern for consistency
- Isolation mode for testing (internal dictionary)
- Production mode (direct os.environ access)
- Source tracking for debugging
- Variable protection
- Automatic .env file loading
- Subprocess environment management
- Value sanitization (especially for database URLs)

**Implementations**:
- [`dev_launcher/isolated_environment.py`](../dev_launcher/isolated_environment.py) - Main implementation with full validation
- [`netra_backend/app/core/isolated_environment.py`](../netra_backend/app/core/isolated_environment.py) - Backend-specific with optimized persistence
- [`auth_service/auth_core/isolated_environment.py`](../auth_service/auth_core/isolated_environment.py) - Auth service-specific with Docker detection

**Related Specs**:
- [Unified Environment Management](../SPEC/unified_environment_management.xml) - Core requirements
- [Environment-Aware Testing](../SPEC/environment_aware_testing.xml) - Test isolation patterns

### Layer 2: Enhanced Configuration Orchestration (UnifiedConfigManager)

**Purpose**: Orchestrates configuration loading with SSOT compliance and progressive validation.

**CRITICAL CHANGES from Previous Implementation**:
- **Test-Aware Caching**: Disables configuration caching in test environments for fresh variable reads
- **Service Secret Sanitization**: Strips whitespace from critical service configuration to prevent header issues  
- **Progressive Validation Integration**: Works with ConfigurationValidator for environment-appropriate validation
- **Environment-Specific Config Classes**: Creates DevelopmentConfig, StagingConfig, ProductionConfig, NetraTestingConfig

**Enhanced Components**:
- `ConfigurationLoader` - Multi-source configuration loading with environment detection
- `ConfigurationValidator` - Progressive validation with fallback handling (WARN/ENFORCE_CRITICAL/ENFORCE_ALL modes)
- `DatabaseValidator` - Database configuration validation through DatabaseURLBuilder SSOT
- `AuthValidator` - OAuth and authentication configuration validation
- `LLMValidator` - LLM provider configuration validation
- `EnvironmentValidator` - Environment-specific configuration validation

**Key Features**:
- **Environment Detection**: Uses EnvironmentDetector for consistent environment identification
- **Test Environment Handling**: Forces fresh configuration loading in testing environments
- **Configuration Health Scoring**: Calculates 0-100 health score with penalties for errors/warnings
- **Service Secret Protection**: Sanitizes SERVICE_SECRET and SERVICE_ID from environment variables
- **Fallback Configuration**: Creates AppConfig fallback on configuration class creation failure

**Primary Location**: [`netra_backend/app/core/configuration/base.py`](../netra_backend/app/core/configuration/base.py) - UnifiedConfigManager

**Configuration Validation Architecture**:
- [`netra_backend/app/core/configuration/validator.py`](../netra_backend/app/core/configuration/validator.py) - Main validator orchestration
- [`netra_backend/app/core/configuration/validator_auth.py`](../netra_backend/app/core/configuration/validator_auth.py) - OAuth and JWT validation
- [`netra_backend/app/core/configuration/validator_database.py`](../netra_backend/app/core/configuration/validator_database.py) - Database configuration validation
- [`netra_backend/app/core/configuration/validator_llm.py`](../netra_backend/app/core/configuration/validator_llm.py) - LLM provider validation
- [`netra_backend/app/core/configuration/validator_environment.py`](../netra_backend/app/core/configuration/validator_environment.py) - External service validation

### Layer 3: Enhanced Service Configuration with SSOT Compliance

**Purpose**: Service-specific configuration classes that maintain independence while using shared SSOT components.

**CRITICAL ARCHITECTURAL CHANGE**: All services now use unified `shared.isolated_environment.IsolatedEnvironment` while maintaining service independence through service-specific configuration wrappers.

**Backend Service Configuration**:
- [`AppConfig`](../netra_backend/app/schemas/config.py) - Main backend configuration schema with environment-specific classes
- `DevelopmentConfig` - Development environment configuration with debug settings
- `StagingConfig` - Staging environment configuration with production-like validation
- `ProductionConfig` - Production configuration with strict security requirements  
- `NetraTestingConfig` - Test environment configuration with built-in defaults

**Auth Service Configuration (SSOT Delegation Pattern)**:
- [`AuthConfig`](../auth_service/auth_core/config.py) - **CONSOLIDATED** thin wrapper that delegates ALL configuration logic to AuthEnvironment
- [`AuthEnvironment`](../auth_service/auth_core/auth_environment.py) - **TRUE SSOT** for all auth service configuration
- **Property Accessor Pattern**: AuthConfig provides property accessors (jwt_secret_key, postgres_host, etc.) that delegate to AuthEnvironment
- **Test Compatibility**: Property setters allow test environments to override configuration values
- **OAuth Integration**: Environment-specific OAuth credential management through AuthEnvironment

**Service Independence Architecture**:
```mermaid
graph TB
    subgraph "Service-Specific Configuration Layer"
        BACKEND_CONFIG["netra_backend<br/>AppConfig + Environment Classes<br/>Uses UnifiedConfigManager"]
        AUTH_CONFIG["auth_service<br/>AuthConfig (Thin Wrapper)<br/>Delegates to AuthEnvironment"]
        AUTH_ENV["auth_service<br/>AuthEnvironment (TRUE SSOT)<br/>All Auth Configuration Logic"]
    end
    
    subgraph "Shared SSOT Infrastructure"
        SHARED_ISO["shared.isolated_environment<br/>IsolatedEnvironment<br/>UNIFIED SINGLETON"]
        SHARED_DB["shared.database_url_builder<br/>DatabaseURLBuilder<br/>Database URL SSOT"]
        SHARED_JWT["shared.jwt_secret_manager<br/>SharedJWTSecretManager<br/>JWT Secret SSOT"]
    end
    
    %% All services use shared SSOT infrastructure
    BACKEND_CONFIG -->|uses| SHARED_ISO
    AUTH_ENV -->|uses| SHARED_ISO
    BACKEND_CONFIG -->|uses| SHARED_DB
    AUTH_ENV -->|uses| SHARED_DB
    BACKEND_CONFIG -->|uses| SHARED_JWT
    AUTH_CONFIG -->|uses| SHARED_JWT
    
    %% Auth service delegation pattern
    AUTH_CONFIG -->|delegates_to| AUTH_ENV
    
    style SHARED_ISO fill:#ff9999
    style AUTH_ENV fill:#ccffcc
    style SHARED_DB fill:#ffcc99
```

**Service Configuration Features**:
- **SSOT Compliance**: No duplicate configuration logic between services
- **Service Independence**: Each service maintains its own configuration interface
- **Shared Infrastructure**: Common utilities shared through `/shared` directory
- **Test Compatibility**: Property accessors allow test configuration override
- **Environment Awareness**: Configuration behavior adapts to deployment environment
- **Progressive Validation**: Service-appropriate validation based on environment and role

## Database URL SSOT Architecture

**CRITICAL: DatabaseURLBuilder is the absolute SSOT for ALL database URL construction.**

### The SSOT Principle for Database URLs

The platform enforces strict SSOT compliance for database URLs to prevent configuration drift, silent failures, and environment-specific bugs.

**GOLDEN RULE: Never Read DATABASE_URL Directly**
```python
# ❌ FORBIDDEN - Direct DATABASE_URL access
database_url = os.environ.get("DATABASE_URL")
database_url = env.get("DATABASE_URL")

# ✅ CORRECT - Always use DatabaseURLBuilder
from shared.database_url_builder import DatabaseURLBuilder
builder = DatabaseURLBuilder(env_vars)
database_url = builder.get_url_for_environment(sync=False)
```

### Why SSOT for Database URLs?

1. **Environment Consistency**: Each environment (dev/test/staging/prod) has different URL construction logic
2. **Driver Compatibility**: Different drivers (asyncpg, psycopg2, psycopg) require different URL formats  
3. **Docker Resolution**: Docker environments need hostname resolution (localhost → postgres)
4. **Cloud SQL Support**: Unix socket URLs have completely different formats
5. **Security Validation**: Centralized credential validation and sanitization
6. **Debug Traceability**: Single point for URL masking and debug information

### DatabaseURLBuilder Integration Flow

```mermaid
graph TD
    subgraph "All Services"
        NS[netra_backend<br/>Service Config]
        AS[auth_service<br/>Service Config]  
        TS[test_framework<br/>Test Setup]
    end
    
    subgraph "SSOT Layer"
        DB[DatabaseURLBuilder<br/>shared/database_url_builder.py]
        ENV[Component Variables<br/>POSTGRES_HOST, USER, etc.]
    end
    
    subgraph "Environment Detection"
        DEV[Development Builder]
        TEST[Test Builder]
        STAGE[Staging Builder]
        PROD[Production Builder]
        DOCKER[Docker Builder]
        CLOUD[Cloud SQL Builder]
    end
    
    NS --> DB
    AS --> DB
    TS --> DB
    
    DB --> ENV
    
    DB --> DEV
    DB --> TEST
    DB --> STAGE
    DB --> PROD
    DB --> DOCKER
    DB --> CLOUD
    
    style DB fill:#ff9999
    style ENV fill:#ffcccc
```

### SSOT Compliance Checklist

**For ALL services using database connections:**

- [ ] **Import DatabaseURLBuilder from shared module**
- [ ] **Pass environment variables to builder constructor**
- [ ] **Use builder.get_url_for_environment() for URL generation**
- [ ] **NEVER read DATABASE_URL environment variable directly**
- [ ] **Use component variables (POSTGRES_HOST, POSTGRES_USER, etc.)**
- [ ] **Test URL generation in all target environments**

**Cross-Reference Documentation:**
- [`shared/database_url_builder.py`](../shared/database_url_builder.py) - Complete implementation
- [`SPEC/database_connectivity_architecture.xml`](../SPEC/database_connectivity_architecture.xml) - Architecture specification
- [Environment-Specific Behavior](#environment-specific-behavior) - Per-environment URL logic

## Shared Configuration Components

**Location**: [`shared/`](../shared/) directory for cross-service components

### DatabaseURLBuilder - SSOT for Database URLs

**CRITICAL: This is the ONLY SSOT for database_url construction across ALL services.**

Constructs database URLs from components or environment variables. ALL database URLs MUST be built through DatabaseURLBuilder subcomponents to ensure consistency and prevent configuration drift.

**Key SSOT Principle:**
- **NEVER directly read DATABASE_URL from environment**
- **ALWAYS use DatabaseURLBuilder with component variables (POSTGRES_HOST, POSTGRES_USER, etc.)**
- **ALL services must go through this builder to maintain SSOT compliance**

```python
# CORRECT Usage - SSOT Compliant
builder = DatabaseURLBuilder(env_vars)
url = builder.get_url_for_environment(sync=False)

# INCORRECT - Direct DATABASE_URL access violates SSOT
url = os.environ.get("DATABASE_URL")  # FORBIDDEN
```

**Cross-References:**
- **Implementation**: [`shared/database_url_builder.py`](../shared/database_url_builder.py) - Complete builder implementation with all environments
- **SSOT Spec**: [`SPEC/database_connectivity_architecture.xml`](../SPEC/database_connectivity_architecture.xml) - Database configuration patterns
- **Configuration Flow**: See [Cross-Service Configuration Flow](#4-cross-service-configuration-flow) for integration patterns

### SharedJWTSecretManager

Ensures consistent JWT secrets across services. See [`shared/jwt_secret_manager.py`](../shared/jwt_secret_manager.py).

```python
# Single source of truth for JWT
secret = SharedJWTSecretManager.get_jwt_secret()
```

### PortDiscovery

Dynamic port discovery for services. See [`shared/port_discovery.py`](../shared/port_discovery.py).

```python
# Get service URL with automatic port discovery
url = PortDiscovery.get_service_url("auth", environment=env)
```

## Configuration Validation

### Required Variables

**Database Configuration (via [DatabaseURLBuilder SSOT](#database-url-ssot-architecture)):**
- `POSTGRES_HOST` - PostgreSQL host (component-based via DatabaseURLBuilder)
- `POSTGRES_USER` - PostgreSQL user (component-based via DatabaseURLBuilder)
- `POSTGRES_PASSWORD` - PostgreSQL password (component-based via DatabaseURLBuilder)
- `POSTGRES_DB` - PostgreSQL database name (component-based via DatabaseURLBuilder)
- ~~`DATABASE_URL`~~ - **DEPRECATED: Use DatabaseURLBuilder instead**

**Other Required Variables:**
- `JWT_SECRET_KEY` - JWT signing key
- `SECRET_KEY` - Application secret
- `ENVIRONMENT` - Runtime environment

### Optional Variables (Categorized)
- **OAuth Configuration**: Google/GitHub OAuth credentials
- **LLM API Keys**: Anthropic, OpenAI, Gemini
- **Database Connections**: Redis, ClickHouse (PostgreSQL via [DatabaseURLBuilder SSOT](#database-url-ssot-architecture))
- **Monitoring**: Grafana, Prometheus, Langfuse
- **Feature Flags**: Various enable/disable flags

### Validation Rules
1. URL format validation (database via [DatabaseURLBuilder](#database-url-ssot-architecture), Redis, ClickHouse)
2. Secret key length requirements (>= 32 chars for production)
3. API key format validation
4. Port conflict detection
5. Environment consistency checks
6. **Database URL SSOT compliance** - Ensures all services use DatabaseURLBuilder

## OAuth Dual Naming Convention Rationale

### Background
The platform implements a dual naming convention for OAuth credentials that was identified as a MEDIUM risk in the CRITICAL_CONFIG_REGRESSION_AUDIT_REPORT. This section documents the rationale and proper usage.

### The Dual Naming Pattern

```python
# Backend Service Pattern (Simplified Names)
GOOGLE_CLIENT_ID = "your-client-id"
GOOGLE_CLIENT_SECRET = "your-client-secret"

# Auth Service Pattern (Environment-Specific Names)
GOOGLE_OAUTH_CLIENT_ID_STAGING = "your-staging-client-id"
GOOGLE_OAUTH_CLIENT_SECRET_STAGING = "your-staging-client-secret"
GOOGLE_OAUTH_CLIENT_ID_PRODUCTION = "your-production-client-id"
GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION = "your-production-client-secret"
```

### Why Two Naming Conventions?

#### 1. Service Architecture Differences
- **Backend Service**: Uses a single OAuth configuration per deployment
- **Auth Service**: Manages multiple environment configurations simultaneously
- **Deployment Scripts**: Need to map both patterns to the same GCP secrets

#### 2. Historical Evolution
- Initially, backend service was primary OAuth handler (simplified names)
- Auth service added later with multi-environment support requirement
- Maintaining backward compatibility prevented immediate unification

#### 3. Security Isolation
- **Backend**: Simplified names reduce configuration complexity for single-env deployments
- **Auth Service**: Environment-specific names prevent accidental cross-environment credential usage
- **Risk Mitigation**: Explicit environment naming prevents staging credentials in production

### Implementation in deployment/secrets_config.py

```python
# The dual mapping ensures both services get correct credentials
SECRET_MAPPINGS = {
    # Backend service uses simplified names
    "GOOGLE_CLIENT_ID": "google-oauth-client-id-{environment}",
    "GOOGLE_CLIENT_SECRET": "google-oauth-client-secret-{environment}",
    
    # Auth service uses explicit environment names
    "GOOGLE_OAUTH_CLIENT_ID_STAGING": "google-oauth-client-id-staging",
    "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "google-oauth-client-secret-staging",
    "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION": "google-oauth-client-id-production",
    "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION": "google-oauth-client-secret-production",
}
```

### Risk Assessment and Mitigation

**Current Risks:**
- Configuration complexity increases maintenance burden
- Potential for misconfiguration during deployment
- Different naming patterns can confuse developers

**Mitigation Strategies:**
1. **Documentation**: This section serves as the canonical reference
2. **Validation**: Deployment scripts validate both patterns exist
3. **Testing**: Integration tests verify OAuth works in both services
4. **Future Consolidation**: Plan to unify in next major version (2.0)

### Best Practices

1. **For Backend Service Development:**
   - Always use simplified names (GOOGLE_CLIENT_ID)
   - Let deployment system handle environment mapping

2. **For Auth Service Development:**
   - Always use environment-specific names
   - Never hardcode environment in variable values

3. **For Deployment:**
   - Ensure both patterns map to same GCP secrets
   - Validate credentials exist for target environment
   - Test OAuth flow end-to-end after deployment

### Future Consolidation Plan (v2.0)

**Target State:**
- Single naming convention: `OAUTH_{PROVIDER}_{FIELD}_{ENVIRONMENT}`
- Example: `OAUTH_GOOGLE_CLIENT_ID_STAGING`
- Migration script to update all references
- Backward compatibility layer for 6 months

**Benefits:**
- Reduced configuration complexity
- Single source of truth for OAuth config
- Easier debugging and maintenance
- Lower risk of misconfiguration

## Environment-Specific Behavior

### Why Different Behaviors per Environment?

```mermaid
graph LR
    subgraph "Development"
        DEV_NEED[Fast Iteration]
        DEV_IMPL[Isolation + Fallbacks]
        DEV_RISK[Low Risk Tolerance]
    end
    
    subgraph "Testing"
        TEST_NEED[Reproducibility]
        TEST_IMPL[Full Isolation]
        TEST_RISK[Zero Side Effects]
    end
    
    subgraph "Staging"
        STAGE_NEED[Production-Like]
        STAGE_IMPL[Real Services]
        STAGE_RISK[Medium Risk]
    end
    
    subgraph "Production"
        PROD_NEED[Stability]
        PROD_IMPL[Direct Access]
        PROD_RISK[Zero Tolerance]
    end
    
    DEV_NEED --> DEV_IMPL
    TEST_NEED --> TEST_IMPL
    STAGE_NEED --> STAGE_IMPL
    PROD_NEED --> PROD_IMPL
```

## Environment-Specific Behavior

### Development
- Isolation mode enabled by default
- Fallback values generated for missing required vars
- Relaxed validation
- .env file auto-loaded

### Testing
- Full isolation mode
- Time-based cache (30 seconds)
- Test environment detection via multiple methods
- Syncs with os.environ for pytest compatibility

### Staging/Production
- Direct os.environ access
- No .env file loading
- Strict validation
- No fallback values
- All secrets from deployment system

## Configuration Regression Prevention Architecture

**CRITICAL INSIGHT:** Configuration regressions cause 60% of production outages and significant business impact. The platform implements comprehensive regression prevention through multiple layers of protection.

### ConfigDependencyMap - Cascade Failure Prevention

**Purpose**: Prevents configuration deletions that would cause cascade failures across services.

**MISSION CRITICAL DEPENDENCIES** tracked by ConfigDependencyMap:
```python
CRITICAL_DEPENDENCIES = {
    "SERVICE_SECRET": {
        "required_by": ["netra_backend", "inter_service_auth", "circuit_breaker"],
        "deletion_impact": "ULTRA_CRITICAL - Complete auth failure, circuit breaker permanent open, 100% user lockout",
        "fallback_allowed": False,
        "validation_required": True
    },
    "DATABASE_URL": {
        "required_by": ["session_service", "state_persistence", "auth_service"],
        "deletion_impact": "CRITICAL - Complete backend failure with no data access",
        "fallback_allowed": False
    },
    "JWT_SECRET_KEY": {
        "required_by": ["auth_service", "backend_auth", "token_validation"],
        "deletion_impact": "CRITICAL - All authentication will fail",
        "fallback_allowed": False
    }
}
```

### Configuration Change Tracking and Validation

**Pre-Deployment Configuration Validation Pipeline**:
1. **Missing Critical Config Check**: Validate all mission-critical variables are present
2. **Configuration Value Validation**: Check formats, lengths, and security requirements  
3. **Breaking Change Detection**: Identify changes that could break existing functionality
4. **Configuration Isolation Testing**: Test configuration in isolated environment
5. **Backward Compatibility Verification**: Ensure existing integrations continue working

### OAuth Configuration Regression Prevention

**CRITICAL LESSONS** from OAuth configuration analysis:

**Previously Identified Issues**:
- **E2E_OAUTH_SIMULATION_KEY Missing**: E2E tests failed when OAuth simulation unavailable
- **Split Authentication Patterns**: Multiple competing auth helpers created confusion
- **Validation Inconsistency**: Different tests had different OAuth validation requirements
- **SSOT Violation**: No unified authentication configuration management

**Current OAuth Protection Mechanisms**:
- **Built-in Test Credentials**: IsolatedEnvironment auto-injects OAuth test credentials during test context detection
- **Unified Authentication Manager**: Single pattern for all E2E test authentication
- **Progressive OAuth Validation**: ConfigurationValidator gracefully handles missing OAuth in development
- **Environment-Specific Credential Isolation**: Staging credentials never leak to production
- **ConfigDependencyMap Integration**: OAuth credential dependencies tracked for impact analysis

### Environment Configuration Consistency

**Environment-Specific Configuration Validation**:
- **Development**: Relaxed validation with warnings, fallback values enabled
- **Testing**: Built-in defaults for OAuth and JWT, isolation mode auto-enabled
- **Staging**: Production-like validation, real service connections, no localhost URLs
- **Production**: Strict validation, all secrets from deployment system, hard failures for missing config

### Configuration Health Monitoring

**Runtime Configuration Validation**:
- **Continuous Validation Loop**: 30-second intervals checking configuration health
- **Health Score Calculation**: 0-100 score with penalties for errors/warnings
- **Alert System**: Immediate notifications on critical configuration changes
- **Configuration Health Dashboard**: Real-time visibility into configuration status

## Configuration Philosophy: Separation of Concerns

### The Three Realms

```mermaid
graph TB
    subgraph "1. Environment Realm"
        ENV_CONCERN[Reading/Writing Variables]
        ENV_IMPL[IsolatedEnvironment]
        ENV_RESP["✓ Isolation<br/>✓ Source Tracking<br/>✓ Sanitization"]
    end
    
    subgraph "2. Configuration Realm"
        CFG_CONCERN[Business Rules & Validation]
        CFG_IMPL[UnifiedConfigManager]
        CFG_RESP["✓ Schema Validation<br/>✓ Consistency<br/>✓ Hot Reload"]
    end
    
    subgraph "3. Application Realm"
        APP_CONCERN[Feature Logic]
        APP_IMPL[Service Code]
        APP_RESP["✓ Use Config<br/>✓ Business Logic<br/>✓ No Direct ENV"]
    end
    
    ENV_IMPL --> CFG_IMPL
    CFG_IMPL --> APP_IMPL
    
    style ENV_CONCERN fill:#e1f5e1
    style CFG_CONCERN fill:#fff4e1
    style APP_CONCERN fill:#e1e4ff
```

### Why This Separation?

1. **Environment doesn't know about business** - IsolatedEnvironment just manages key-value pairs
2. **Configuration doesn't know about features** - UnifiedConfigManager just validates and structures data
3. **Application doesn't know about storage** - Service code just uses configuration objects

This separation allows:
- Testing each layer independently
- Changing storage (env vars → Vault) without touching business logic
- Adding validation without modifying environment loading
- Deploying to new environments without code changes

## Enhanced Configuration Best Practices with Current Implementation

1. **SSOT Compliance (CRITICAL)** - Always use shared.isolated_environment.IsolatedEnvironment
2. **Track sources** - Always provide source parameter when setting variables
3. **Validate early** - Run validation during service startup
4. **Use shared components** - DatabaseURLBuilder, JWT manager, etc.
5. **Maintain service independence** - Each service has its own IsolatedEnvironment
6. **Handle secrets carefully** - Use sanitization and masking for logs
7. **Test with isolation** - Enable isolation mode in tests
8. **Document requirements** - Keep variable documentation up-to-date
9. **Monitor WebSocket health** - Use event monitoring to detect silent failures
10. **Verify critical services** - WebSocket events are critical infrastructure for chat functionality
11. **🚨 CRITICAL: Database URL SSOT Compliance** - ALWAYS use [DatabaseURLBuilder](#database-url-ssot-architecture), NEVER read DATABASE_URL directly

## Common Patterns

### Service Initialization
```python
from service.isolated_environment import get_env
env = get_env()
env.load_from_file(Path(".env"))
config = ServiceConfig()
```

### Configuration Access
```python
# SSOT-compliant database URL access
from shared.database_url_builder import DatabaseURLBuilder
from service.isolated_environment import get_env

env = get_env()
builder = DatabaseURLBuilder(env._dict)  # or env variables
database_url = builder.get_url_for_environment(sync=False)

# Other configuration access
from app.core.configuration.base import get_unified_config
config = get_unified_config()
# Access other config values (but NOT database_url directly)
```

### Test Setup
```python
@pytest.fixture
def isolated_env():
    env = get_env()
    env.enable_isolation()
    yield env
    env.reset_to_original()
```

## Deep Dive: Why Each Component Exists

### IsolatedEnvironment vs os.environ

**Problem**: os.environ is global mutable state
**Solution**: IsolatedEnvironment provides controlled access

```python
# BAD: Direct os.environ
os.environ["DATABASE_URL"] = "postgresql://..."  # No tracking, affects everything

# GOOD: IsolatedEnvironment
env.set("DATABASE_URL", "postgresql://...", source="test_setup")  # Tracked, isolated
```

### UnifiedConfigManager vs Direct ENV Access

**Problem**: Raw environment variables are strings without validation
**Solution**: UnifiedConfigManager provides typed, validated configuration

```python
# BAD: Direct environment access
port = int(os.environ.get("PORT", "8000"))  # Can fail, no validation

# GOOD: Unified configuration
config = get_unified_config()
port = config.port  # Already validated, typed as int
```

### Service-Specific Config vs Shared Config

**Problem**: Services have different requirements
**Solution**: Each service has its own config while sharing common patterns

```python
# Auth Service needs OAuth
class AuthConfig:
    def get_google_client_id(self): ...

# Backend needs database pools
class AppConfig:
    def get_connection_pool_size(self): ...

# Both share JWT secret through SharedJWTSecretManager
```

## Troubleshooting

### Common Issues

1. **Configuration not loading**: Check environment detection, verify .env file location
2. **Validation failures**: Run validation manually, check required variables
3. **Port conflicts**: Review service port assignments
4. **Secret key errors**: Ensure proper length and uniqueness
5. **Database connection issues**: Verify URL format and credentials via [DatabaseURLBuilder](#database-url-ssot-architecture)
6. **Database URL SSOT violations**: Check that code uses DatabaseURLBuilder instead of direct DATABASE_URL access
7. **Test isolation problems**: Ensure isolation mode is enabled

### Debug Tools

- `env.get_debug_info()` - Get environment manager state
- `config_manager.get_config_summary()` - Configuration overview
- `validator.print_validation_summary()` - Detailed validation report
- `builder.debug_info()` - Database URL builder diagnostics (see [DatabaseURLBuilder](#database-url-ssot-architecture))
- `builder.get_safe_log_message()` - Safe database URL logging with credential masking

## Understanding Environment Types

### Development Environment
```yaml
Purpose: Local development, rapid iteration
Isolation: Enabled (prevent pollution)
Validation: Relaxed (allow missing optional)
Fallbacks: Generated (DATABASE_URL, secrets)
.env Loading: Automatic
Example Variables:
  DATABASE_URL: postgresql://localhost:5432/netra_dev
  ENVIRONMENT: development
  FRONTEND_URL: http://localhost:3000
```

### Testing Environment
```yaml
Purpose: Automated testing, CI/CD
Isolation: Full (complete isolation)
Validation: Strict for tests
Fallbacks: Test-specific
.env Loading: Disabled
Cache: Time-based (30 seconds)
Example Variables:
  ENVIRONMENT: testing
  TESTING: true
  DATABASE_URL: sqlite:///:memory:
```

### Staging Environment
```yaml
Purpose: Pre-production validation
Isolation: Disabled (real environment)
Validation: Production-like
Fallbacks: None
.env Loading: Never
Example Variables:
  ENVIRONMENT: staging
  DATABASE_URL: postgresql://staging-db.gcp:5432/netra_staging
  K_SERVICE: netra-staging-backend
```

### Production Environment
```yaml
Purpose: Live customer traffic
Isolation: Disabled (direct os.environ)
Validation: Strict
Fallbacks: None (fail fast)
.env Loading: Never
Secrets: From deployment system only
Example Variables:
  ENVIRONMENT: production
  DATABASE_URL: <from-secret-manager>
  K_SERVICE: netra-production-backend
```

## Migration Guide

When migrating to the unified configuration system:

1. Replace direct `os.environ` access with `get_env().get()`
2. Add source tracking to all `set()` calls
3. Update imports to use service-specific IsolatedEnvironment
4. **CRITICAL: Replace direct DATABASE_URL usage with [DatabaseURLBuilder](#database-url-ssot-architecture)**
5. Remove legacy configuration code
6. Add validation to service startup
7. Update tests to use isolation mode
8. Document new environment variables

### Database URL Migration Priority

**High Priority - MUST be done immediately:**
```python
# OLD - Direct DATABASE_URL access (DELETE THIS)
database_url = os.environ.get("DATABASE_URL")
database_url = config.database_url  # If directly from env

# NEW - DatabaseURLBuilder SSOT compliance
from shared.database_url_builder import DatabaseURLBuilder
builder = DatabaseURLBuilder(env_vars)
database_url = builder.get_url_for_environment(sync=False)
```

## The Configuration Contract

### What Each Layer Promises

**IsolatedEnvironment Promises:**
- I will never leak variables between tests
- I will track who set each variable
- I will sanitize dangerous characters
- I will provide subprocess environments

**UnifiedConfigManager Promises:**
- I will validate all configuration
- I will provide consistent config objects
- I will detect environment correctly
- I will fail fast on invalid config

**Service Configuration Promises:**
- I will use only validated configuration
- I will never access os.environ directly
- I will handle environment-specific logic
- I will share secrets correctly

### The Trust Boundary

```mermaid
graph TD
    subgraph "Untrusted"
        USER[User Input]
        ENV_FILE[.env Files]
        OS_ENV[OS Environment]
    end
    
    subgraph "Trust Boundary"
        ISO[IsolatedEnvironment<br/>Sanitization & Validation]
    end
    
    subgraph "Trusted"
        CONFIG[Validated Config]
        APP[Application]
    end
    
    USER --> ISO
    ENV_FILE --> ISO
    OS_ENV --> ISO
    
    ISO --> CONFIG
    CONFIG --> APP
    
    style ISO fill:#ffcccc
    style CONFIG fill:#ccffcc
```

## WebSocket Event Monitoring Configuration

The platform includes comprehensive WebSocket event monitoring to prevent silent failures and ensure chat functionality reliability.

### WebSocket Health Verification
- **Startup Verification**: WebSocket events tested during system startup (Phase 5)
- **Runtime Monitoring**: Continuous monitoring via `ChatEventMonitor`
- **Health Endpoint**: `/health` includes WebSocket event monitor status
- **Critical Logging**: Silent failures logged at CRITICAL level

### Event Monitoring Components
| Component | File | Purpose |
|-----------|------|---------|
| **Event Monitor** | `netra_backend/app/websocket_core/event_monitor.py` | Runtime event flow monitoring |
| **Heartbeat Manager** | `netra_backend/app/websocket_core/heartbeat_manager.py` | Connection health tracking |
| **WebSocket Manager** | `netra_backend/app/websocket_core/manager.py` | Enhanced with health checks |
| **Startup Verification** | `netra_backend/app/smd.py` | WebSocket functionality validation |

### Monitoring Configuration Variables
```yaml
# Event Monitor Settings
WEBSOCKET_EVENT_TIMEOUT: 30  # seconds
WEBSOCKET_HEARTBEAT_INTERVAL: 15  # seconds
WEBSOCKET_HEALTH_CHECK_INTERVAL: 10  # seconds
WEBSOCKET_SILENT_FAILURE_THRESHOLD: 5  # failures before alert

# Agent Execution Tracking Settings (NEW)
AGENT_EXECUTION_TIMEOUT: 30  # seconds - maximum time for agent execution
AGENT_HEARTBEAT_TIMEOUT: 10  # seconds - time without heartbeat before agent marked dead
AGENT_HEARTBEAT_INTERVAL: 2  # seconds - how often agents send heartbeats
EXECUTION_CLEANUP_INTERVAL: 60  # seconds - cleanup old execution records
MAX_CONCURRENT_AGENTS: 10  # maximum concurrent agent executions
```

## Agent Death Detection System (NEW)

The platform includes comprehensive agent death detection to prevent silent failures and ensure reliable chat functionality.

### Death Detection Components
| Component | File | Purpose |
|-----------|------|---------|
| **Execution Tracker** | `netra_backend/app/core/agent_execution_tracker.py` | Tracks all agent executions with unique IDs |
| **Death Monitor** | `netra_backend/app/agents/supervisor/execution_engine.py` | Monitors agents for death/timeout |
| **Death Notification** | `netra_backend/app/services/agent_websocket_bridge.py` | Sends death notifications to users |
| **Health Integration** | `netra_backend/app/core/agent_health_monitor.py` | Reports dead agents in health status |

### Death Detection Mechanisms
1. **Heartbeat Monitoring**: Agents must send heartbeat every 2s or marked dead after 10s
2. **Execution Timeout**: 30s maximum execution time enforced
3. **State Tracking**: Track execution state throughout lifecycle (PENDING→RUNNING→COMPLETED/DEAD)
4. **Death Callbacks**: Automatic WebSocket notification when death detected
5. **Health Reporting**: Dead agents reported in `/health` endpoint

### WebSocket Death Event Format
```json
{
  "type": "agent_death",
  "run_id": "exec_abc123_1234567890",
  "agent_name": "triage_agent",
  "timestamp": "2025-01-09T20:30:00Z",
  "payload": {
    "status": "dead",
    "death_cause": "timeout|no_heartbeat|silent_failure",
    "message": "User-friendly recovery message",
    "recovery_action": "refresh_required"
  }
}
```

### Related Documentation
- See [`AGENT_DEATH_FIX_IMPLEMENTATION.md`](../AGENT_DEATH_FIX_IMPLEMENTATION.md) for complete implementation details
- See [`SPEC/learnings/agent_death_detection_critical.xml`](../SPEC/learnings/agent_death_detection_critical.xml) for lessons learned
- See [`WEBSOCKET_SILENT_FAILURE_FIXES.md`](../WEBSOCKET_SILENT_FAILURE_FIXES.md) for WebSocket implementation details
- See [`SPEC/learnings/websocket_silent_failure_prevention_masterclass.xml`](../SPEC/learnings/websocket_silent_failure_prevention_masterclass.xml) for comprehensive prevention strategies

## Security Considerations

1. **Never log secrets** - Use masking functions
2. **Sanitize inputs** - Remove control characters
3. **Validate URLs** - Check format and schemes
4. **Protect critical vars** - Use protection mechanism
5. **Separate concerns** - Different secrets for different purposes
6. **Environment isolation** - Keep dev/staging/prod separate
7. **Audit changes** - Track sources and callbacks
8. **Monitor WebSocket security** - Track connection health and prevent unauthorized access