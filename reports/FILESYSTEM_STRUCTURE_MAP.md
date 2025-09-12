# FILESYSTEM STRUCTURE MAP
**ULTRA CRITICAL IMPORT DISCOVERY - PHASE 1**

Generated: 2025-09-09
Mission: Map actual directory structures to resolve critical import failures

## SERVICE DIRECTORY STRUCTURES

### netra_backend Service
```
netra_backend/
├── app/
│   ├── agents/
│   │   ├── base/               # Base agent classes
│   │   ├── chat_orchestrator/  # Chat orchestration
│   │   ├── corpus_admin/       # Corpus management
│   │   ├── data/               # Data processing agents
│   │   ├── data_sub_agent/     # Data sub-agents
│   │   ├── domain_experts/     # Domain-specific agents
│   │   ├── execution_tracking/ # Execution monitoring
│   │   ├── github_analyzer/    # GitHub analysis
│   │   ├── mcp_integration/    # MCP integration
│   │   ├── migration/          # Migration agents
│   │   ├── mixins/             # Agent mixins
│   │   ├── prompts/            # Prompt templates
│   │   │   └── optimization_prompts.py  # FOUND: Optimization prompts
│   │   ├── reporting/          # Reporting agents
│   │   │   └── templates.py    # Report templates
│   │   ├── security/           # Security agents
│   │   ├── supply_researcher/  # Supply research
│   │   ├── supervisor/         # Agent supervision
│   │   ├── synthetic_data/     # Synthetic data generation
│   │   ├── tools/              # Tool management
│   │   ├── triage/             # Issue triage
│   │   ├── triage_sub_agent/   # Triage sub-agents
│   │   │
│   │   ├── optimizations_core_sub_agent.py  # FOUND: Core optimization agent
│   │   ├── reporting_sub_agent.py           # FOUND: Reporting functionality
│   │   └── [67 other agent files]
│   │
│   └── services/
│       └── token_optimization/ # Token optimization service
│
└── tests/
    ├── agents/                 # Agent tests
    ├── integration/            # Integration tests
    ├── services/               # Service tests
    └── unit/                   # Unit tests
        └── golden_path/        # Golden path tests
```

### auth_service Service  
```
auth_service/
├── auth_core/                  # ACTUAL AUTH STRUCTURE (NOT app/)
│   ├── audit/                  # Audit functionality
│   ├── business_logic/         # Business logic
│   ├── compliance/             # Compliance features
│   ├── core/                   # Core auth functions
│   ├── database/               # Database operations
│   ├── models/                 # Data models
│   │   ├── auth_models.py      # FOUND: Auth models
│   │   ├── oauth_token.py      # OAuth tokens
│   │   └── oauth_user.py       # OAuth users (NOT user.py)
│   ├── oauth/                  # OAuth handling
│   ├── performance/            # Performance optimization
│   ├── routes/                 # API routes
│   ├── security/               # Security features
│   ├── services/               # Service classes
│   │   └── auth_service.py     # FOUND: Main auth service
│   └── validation/             # Validation logic
│
├── core/                       # Additional core functionality
├── services/                   # Service utilities
│   ├── oauth_service.py        # OAuth service
│   └── user_service.py         # User service
│
└── tests/
    ├── e2e/                    # End-to-end tests
    ├── integration/            # Integration tests
    └── unit/                   # Unit tests
        └── golden_path/        # Golden path tests
```

## KEY FINDINGS

### ❌ MISSING DIRECTORIES
1. **netra_backend**: No `optimization_agents/` directory exists
2. **netra_backend**: No `reporting_agents/` directory exists  
3. **auth_service**: No `app/` directory exists (uses `auth_core/` instead)
4. **auth_service**: No `app/models/user.py` exists
5. **auth_service**: No `app/schemas/` directory exists

### ✅ ACTUAL LOCATIONS FOUND
1. **Optimization**: `netra_backend/app/agents/optimizations_core_sub_agent.py`
2. **Reporting**: `netra_backend/app/agents/reporting_sub_agent.py`
3. **Auth Service**: `auth_service/auth_core/services/auth_service.py`
4. **User Models**: `auth_service/auth_core/models/oauth_user.py`
5. **Auth Models**: `auth_service/auth_core/models/auth_models.py`

## CRITICAL IMPORT PATH MISMATCHES

### Pattern 1: Non-existent Directory Structure
```python
# BROKEN: Expected structure that doesn't exist
from netra_backend.app.agents.optimization_agents.optimization_helper_agent import OptimizationHelperAgent
from netra_backend.app.agents.reporting_agents.uvs_reporting_agent import UVSReportingAgent
from auth_service.app.services.auth_service import AuthService
from auth_service.app.models.user import User
from auth_service.app.schemas.auth import UserCreate
```

### Pattern 2: Legacy Structure References
The broken imports suggest an old directory structure that no longer matches the current filesystem organization.

## ARCHITECTURAL IMPLICATIONS

### Service Isolation Confirmed
- **netra_backend**: Standard app/ structure with agents/ subdirectory
- **auth_service**: Uses auth_core/ instead of app/ (architectural decision for isolation)
- Each service maintains completely independent structure

### Agent Organization Pattern
- Flat file structure in `/agents/` directory rather than subdirectories
- Specialized agents use descriptive filenames with suffixes
- No optimization_agents/ or reporting_agents/ subdirectories exist

This mapping provides the foundation for systematic import correction in Phase 2.