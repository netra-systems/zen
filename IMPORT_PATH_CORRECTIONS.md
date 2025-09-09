# IMPORT PATH CORRECTIONS
**ULTRA CRITICAL REMEDIATION MAP - EXPECTED vs ACTUAL**

Generated: 2025-09-09  
Mission: Provide exact corrections for all broken import paths

## CRITICAL CORRECTIONS REQUIRED

### 1. OPTIMIZATION AGENT IMPORTS

#### ❌ BROKEN IMPORT:
```python
from netra_backend.app.agents.optimization_agents.optimization_helper_agent import OptimizationHelperAgent
```

#### ✅ CORRECTION NEEDED:
**Status**: FILE MISSING - OptimizationHelperAgent class not found

**Investigation Results**:
- ❌ No `optimization_agents/` directory exists
- ❌ No `optimization_helper_agent.py` file exists  
- ✅ Found: `optimizations_core_sub_agent.py` (different class)
- ⚠️ **REQUIRES MANUAL INVESTIGATION**: Need to identify actual optimization agent class

**Potential Correct Import** (requires verification):
```python
# Option 1: Use existing optimization agent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent

# Option 2: Class may be in different file - NEEDS INVESTIGATION
# from netra_backend.app.agents.[UNKNOWN_FILE] import OptimizationHelperAgent
```

---

### 2. REPORTING AGENT IMPORTS

#### ❌ BROKEN IMPORT:
```python
from netra_backend.app.agents.reporting_agents.uvs_reporting_agent import UVSReportingAgent  
```

#### ✅ CORRECTION NEEDED:
**Status**: FILE MISSING - UVSReportingAgent class not found

**Investigation Results**:
- ❌ No `reporting_agents/` directory exists
- ❌ No `uvs_reporting_agent.py` file exists
- ✅ Found: `reporting_sub_agent.py` (different class)
- ⚠️ **REQUIRES MANUAL INVESTIGATION**: Need to identify actual UVS reporting class

**Potential Correct Import** (requires verification):
```python
# Option 1: Use existing reporting agent  
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent

# Option 2: Class may be in different file - NEEDS INVESTIGATION
# from netra_backend.app.agents.[UNKNOWN_FILE] import UVSReportingAgent
```

---

### 3. AUTH SERVICE IMPORTS

#### ❌ BROKEN IMPORT:
```python
from auth_service.app.services.auth_service import AuthService
```

#### ✅ CORRECT IMPORT:
```python
from auth_service.auth_core.services.auth_service import AuthService
```

**Change**: `app` → `auth_core`

---

#### ❌ BROKEN IMPORT:  
```python
from auth_service.app.models.user import User
```

#### ✅ CORRECTION NEEDED:
**Status**: FILE MISSING - No `user.py` file exists

**Investigation Results**:
- ❌ No `app/models/` directory exists
- ❌ No `user.py` file exists
- ✅ Found: `auth_core/models/oauth_user.py` 
- ✅ Found: `auth_core/models/auth_models.py`

**Potential Correct Import** (requires verification):
```python
# Option 1: Use OAuth user model
from auth_service.auth_core.models.oauth_user import OAuthUser

# Option 2: Use auth models  
from auth_service.auth_core.models.auth_models import [USER_CLASS_NAME]

# Option 3: Class may be in different file - NEEDS INVESTIGATION
```

---

#### ❌ BROKEN IMPORT:
```python
from auth_service.app.schemas.auth import UserCreate, UserLogin, TokenResponse
```

#### ✅ CORRECTION NEEDED:  
**Status**: DIRECTORY MISSING - No schemas directory exists

**Investigation Results**:
- ❌ No `app/schemas/` directory exists
- ❌ No `auth.py` schema file exists
- ⚠️ **REQUIRES MANUAL INVESTIGATION**: Need to find where auth schemas are defined

**Potential Locations to Search**:
```python
# Check these locations for schema definitions:
# - auth_service/auth_core/models/
# - auth_service/auth_core/business_logic/  
# - auth_service/auth_core/validation/
# - auth_service/services/
```

---

## MOCK PATH CORRECTIONS

### 1. OPTIMIZATION MOCK PATHS

#### ❌ BROKEN MOCK:
```python
@patch('netra_backend.app.agents.optimization_agents.optimization_helper_agent.OptimizationHelperAgent.run')
```

#### ✅ CORRECTION NEEDED:
**Status**: Path does not exist - requires class location first

---

### 2. REPORTING MOCK PATHS  

#### ❌ BROKEN MOCK:
```python
@patch('netra_backend.app.agents.reporting_agents.uvs_reporting_agent.UVSReportingAgent.run')
```

#### ✅ CORRECTION NEEDED:
**Status**: Path does not exist - requires class location first

---

### 3. AUTH SERVICE MOCK PATHS

#### ❌ BROKEN MOCK:
```python
@patch('auth_service.app.services.auth_service.UserRepository')
```

#### ✅ CORRECT MOCK:
```python
@patch('auth_service.auth_core.services.auth_service.UserRepository')
```

#### ❌ BROKEN MOCK:
```python
@patch('auth_service.app.services.auth_service.verify_password')  
```

#### ✅ CORRECT MOCK:
```python
@patch('auth_service.auth_core.services.auth_service.verify_password')
```

---

## CORRECTION CONFIDENCE LEVELS

### 🟢 HIGH CONFIDENCE (Verified Paths):
1. **auth_service.auth_core.services.auth_service** - ✅ File exists
2. **Mock paths for auth_service** - ✅ Structure corrected

### 🟡 MEDIUM CONFIDENCE (Likely Correct):
1. **auth_service.auth_core.models.oauth_user** - ✅ File exists, class needs verification

### 🔴 LOW CONFIDENCE (Requires Investigation):
1. **OptimizationHelperAgent class location** - ⚠️ Class not found
2. **UVSReportingAgent class location** - ⚠️ Class not found  
3. **User class definition** - ⚠️ Multiple potential locations
4. **Auth schema definitions** - ⚠️ Directory structure unclear

## IMMEDIATE ACTIONS REQUIRED

### Phase 2 - CLASS LOCATION DISCOVERY:
1. **URGENT**: Search entire codebase for `OptimizationHelperAgent` class definition
2. **URGENT**: Search entire codebase for `UVSReportingAgent` class definition  
3. **HIGH**: Search entire codebase for `User` class in auth_service
4. **HIGH**: Search entire codebase for `UserCreate`, `UserLogin`, `TokenResponse` schemas

### Phase 3 - VERIFICATION:  
1. Verify corrected import paths actually work
2. Verify class interfaces match test expectations
3. Update all mock paths accordingly

**NEXT STEP**: Deploy specialized search agents to locate missing classes across entire codebase.