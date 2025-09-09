# SSOT IMPORT REGISTRY  
**SINGLE SOURCE OF TRUTH - MASTER IMPORT REFERENCE**

Generated: 2025-09-09
Mission: Provide authoritative import mappings for all Netra services

## SERVICE IMPORT PATTERNS

### netra_backend Service

#### ✅ VERIFIED IMPORTS (Working):
```python
# Agent Framework
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent  
from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.schemas.agent_schemas import AgentExecutionResult

# Shared Types (Cross-Service)
from shared.types.core_types import UserID, ThreadID, RunID
```

#### ✅ AVAILABLE AGENTS (Confirmed):
```python
# Core Agents (Verified Files)
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher

# State Management
from netra_backend.app.agents.state import DeepAgentState

# Specialized Agents (Requires Verification)
from netra_backend.app.agents.corpus_admin_sub_agent import CorpusAdminSubAgent  # ❓
from netra_backend.app.agents.supply_researcher_sub_agent import SupplyResearcherAgent  # ❓
```

#### ❌ BROKEN IMPORTS (Do Not Use):
```python
# THESE PATHS DO NOT EXIST:
from netra_backend.app.agents.optimization_agents.optimization_helper_agent import OptimizationHelperAgent  # ❌
from netra_backend.app.agents.reporting_agents.uvs_reporting_agent import UVSReportingAgent  # ❌
```

---

### auth_service Service

#### ✅ VERIFIED IMPORTS (Working):
```python
# Core Service (Verified Path)
from auth_service.auth_core.services.auth_service import AuthService

# Models (Verified Files)  
from auth_service.auth_core.models.oauth_user import OAuthUser
from auth_service.auth_core.models.oauth_token import OAuthToken
from auth_service.auth_core.models.auth_models import [AUTH_MODEL_CLASSES]  # ❓ Classes need verification

# Business Logic
from auth_service.auth_core.business_logic.user_business_logic import [USER_LOGIC_CLASSES]  # ❓

# OAuth Management
from auth_service.auth_core.oauth.oauth_business_logic import [OAUTH_CLASSES]  # ❓
```

#### ❌ BROKEN IMPORTS (Do Not Use):
```python  
# THESE PATHS DO NOT EXIST:
from auth_service.app.services.auth_service import AuthService  # ❌
from auth_service.app.models.user import User  # ❌
from auth_service.app.schemas.auth import UserCreate, UserLogin, TokenResponse  # ❌
```

---

## MOCK PATH REGISTRY

### netra_backend Mocks

#### ✅ CORRECT MOCK PATHS:
```python
# Core Agents
@patch('netra_backend.app.agents.optimizations_core_sub_agent.OptimizationsCoreSubAgent.run')
@patch('netra_backend.app.agents.reporting_sub_agent.ReportingSubAgent.run')
@patch('netra_backend.app.agents.data_helper_agent.DataHelperAgent.run')
```

#### ❌ BROKEN MOCK PATHS:
```python
# DO NOT USE THESE:
@patch('netra_backend.app.agents.optimization_agents.optimization_helper_agent.OptimizationHelperAgent.run')  # ❌
@patch('netra_backend.app.agents.reporting_agents.uvs_reporting_agent.UVSReportingAgent.run')  # ❌
```

---

### auth_service Mocks

#### ✅ CORRECT MOCK PATHS:
```python
# Service Mocking
@patch('auth_service.auth_core.services.auth_service.UserRepository')
@patch('auth_service.auth_core.services.auth_service.verify_password')
@patch('auth_service.auth_core.services.auth_service.AuthService.authenticate_user')
```

#### ❌ BROKEN MOCK PATHS:
```python
# DO NOT USE THESE:
@patch('auth_service.app.services.auth_service.UserRepository')  # ❌
@patch('auth_service.app.services.auth_service.verify_password')  # ❌
```

---

## IMPORT STANDARDS BY SERVICE

### Service Isolation Rules:
1. **NEVER import between services** (except shared utilities)
2. **Each service has independent structure**
3. **Use absolute imports only**
4. **Verify file exists before importing**

### Path Patterns:

#### netra_backend:
```
netra_backend.app.{component}.{specific_module} 
```

#### auth_service:  
```
auth_service.auth_core.{component}.{specific_module}
```

#### shared:
```  
shared.{utility_type}.{specific_module}
```

---

## MISSING CLASS INVESTIGATION REQUIRED

### 🔍 HIGH PRIORITY SEARCHES NEEDED:

1. **OptimizationHelperAgent**:
   - Search: `grep -r "class OptimizationHelperAgent" netra_backend/`
   - Alternative names: `OptimizationAgent`, `OptimHelper`, `OptiAgent`

2. **UVSReportingAgent**:  
   - Search: `grep -r "class UVSReportingAgent" netra_backend/`
   - Alternative names: `UVSReporting`, `ReportingAgent`, `UVSAgent`

3. **User Class (auth_service)**:
   - Search: `grep -r "class User" auth_service/`
   - Alternative names: `AuthUser`, `SystemUser`, `UserModel`

4. **Auth Schemas**:
   - Search: `grep -r "UserCreate\|UserLogin\|TokenResponse" auth_service/`
   - Alternative locations: Pydantic models, dataclasses

---

## USAGE GUIDELINES

### For Developers:
1. **ALWAYS use this registry before importing**
2. **Verify file exists before adding imports**  
3. **Update registry when adding new modules**
4. **Use correct mock paths for testing**

### For Testing:
1. **Import from VERIFIED section only**
2. **Use CORRECT MOCK PATHS section for patches**
3. **Never use BROKEN IMPORTS section**

### For CI/CD:
1. **Validate all imports against this registry**
2. **Fail builds on broken import patterns**  
3. **Auto-update registry on structural changes**

---

## UPDATE PROTOCOL

### When to Update Registry:
1. **New service modules added**
2. **Directory structure changes**  
3. **Service refactoring completed**
4. **Missing classes located**

### Update Process:
1. Verify new paths with filesystem scan
2. Test imports in isolation
3. Update VERIFIED section
4. Move corrected items from BROKEN section  
5. Regenerate documentation

**CRITICAL**: Keep this registry updated as THE authoritative source for all import decisions.