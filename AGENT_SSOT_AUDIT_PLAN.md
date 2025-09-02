# Agent SSOT Violation Audit Plan

## Executive Summary
This document outlines a comprehensive plan to audit the top 10 critical agents in the Netra platform for SSOT (Single Source of Truth) violations and alignment with the new UserExecutionContext pattern.

## Top 10 Critical Agents (Prioritized by Business Impact)

### Tier 1: Revenue-Critical (Direct User Impact)
1. **TriageSubAgent** - First contact for ALL users
2. **OptimizationsCoreSubAgent** - Core optimization engine (main value prop)
3. **ReportingSubAgent** - User insights and reporting
4. **DataSubAgent** - Data processing and analysis

### Tier 2: Infrastructure-Critical  
5. **SupervisorAgent** - Orchestrates all agent interactions
6. **GoalsTriageSubAgent** - Goal-based routing
7. **ActionsToMeetGoalsSubAgent** - Action planning and execution

### Tier 3: Supporting Services
8. **SyntheticDataSubAgent** - Test data generation
9. **CorpusAdminSubAgent** - Knowledge base management
10. **DataHelperAgent** - Data transformation utilities

## Common SSOT Violation Patterns to Audit

### 1. Duplicate JSON Handling
**Pattern**: Custom JSON extraction/parsing instead of using `unified_json_handler.py`
```python
# VIOLATION - Custom implementation
def extract_json(response):
    # Custom regex/parsing logic
    
# CORRECT - Use canonical
from netra_backend.app.core.serialization.unified_json_handler import LLMResponseParser
```

### 2. Duplicate Hash/Cache Key Generation
**Pattern**: Custom hash generation instead of using `CacheHelpers`
```python
# VIOLATION
import hashlib
def generate_hash(data):
    return hashlib.sha256(data.encode()).hexdigest()
    
# CORRECT
from netra_backend.app.services.cache.cache_helpers import CacheHelpers
```

### 3. Missing UserExecutionContext Integration
**Pattern**: Not accepting or passing UserExecutionContext for request isolation
```python
# VIOLATION
class Agent:
    def __init__(self):
        pass
        
# CORRECT
class Agent:
    def __init__(self, context: Optional[UserExecutionContext] = None):
        self.context = context
```

### 4. Direct Environment Access
**Pattern**: Using `os.environ` instead of `IsolatedEnvironment`
```python
# VIOLATION
import os
value = os.environ.get('KEY')

# CORRECT
from shared.isolated_environment import IsolatedEnvironment
env = IsolatedEnvironment()
value = env.get('KEY')
```

### 5. Custom Retry Logic
**Pattern**: Implementing retry logic instead of using `UnifiedRetryHandler`
```python
# VIOLATION
for attempt in range(3):
    try:
        # logic
    except:
        if attempt == 2:
            raise
            
# CORRECT
from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler
```

### 6. Direct Database Session Storage
**Pattern**: Storing database sessions in instance variables
```python
# VIOLATION
self.db_session = session

# CORRECT
# Pass through context or use DatabaseSessionManager
```

### 7. Global State Storage
**Pattern**: Storing user-specific data in class/instance variables
```python
# VIOLATION
self.user_id = user_id
self.thread_id = thread_id

# CORRECT
# Use UserExecutionContext to pass through
```

### 8. Custom Error Handling
**Pattern**: Custom error handling instead of unified patterns
```python
# VIOLATION
try:
    # logic
except Exception as e:
    logger.error(f"Error: {e}")
    
# CORRECT
from netra_backend.app.core.unified_error_handler import agent_error_handler
```

### 9. WebSocket Event Duplication
**Pattern**: Custom WebSocket event emission instead of using WebSocketBridgeAdapter
```python
# VIOLATION
await websocket.send_json({"event": "..."})

# CORRECT
self._websocket_adapter.emit_thinking(message)
```

### 10. Configuration Access Patterns
**Pattern**: Direct config file reading instead of using configuration architecture
```python
# VIOLATION
with open('config.json') as f:
    config = json.load(f)
    
# CORRECT
from netra_backend.app.core.config import get_config
config = get_config()
```

## Audit Checklist for Each Agent

### Pre-Audit Setup
- [ ] Read USER_CONTEXT_ARCHITECTURE.md
- [ ] Review CLAUDE.md compliance requirements
- [ ] Check recent commits for the agent
- [ ] Review test coverage

### Code Review Checklist
- [ ] **JSON Handling**
  - [ ] No custom JSON parsing implementations
  - [ ] Uses `unified_json_handler.py` functions
  - [ ] Proper error handling with JSONErrorFixer

- [ ] **Caching & Hashing**
  - [ ] Uses CacheHelpers for key generation
  - [ ] Includes user context in cache keys when available
  - [ ] No custom hash implementations

- [ ] **UserExecutionContext**
  - [ ] Accepts context parameter (optional for backward compat)
  - [ ] Passes context to sub-components
  - [ ] No user data stored in instance variables

- [ ] **Environment & Config**
  - [ ] Uses IsolatedEnvironment for env vars
  - [ ] Uses configuration architecture for settings
  - [ ] No direct os.environ access

- [ ] **Database Operations**
  - [ ] Uses DatabaseSessionManager
  - [ ] No sessions stored in instance variables
  - [ ] Proper session cleanup in finally blocks

- [ ] **Error Handling & Resilience**
  - [ ] Uses UnifiedRetryHandler for retries
  - [ ] Uses agent_error_handler for errors
  - [ ] Proper circuit breaker integration

- [ ] **WebSocket Integration**
  - [ ] Uses WebSocketBridgeAdapter
  - [ ] No direct WebSocket manipulation
  - [ ] Proper event types and structure

- [ ] **Base Class Alignment**
  - [ ] Extends BaseAgent where appropriate
  - [ ] Doesn't duplicate BaseAgent functionality
  - [ ] Uses inherited methods properly

### Testing Checklist
- [ ] Backward compatibility maintained
- [ ] Works with and without UserExecutionContext
- [ ] No global state leakage between requests
- [ ] Proper isolation in concurrent scenarios

## Execution Plan

### Phase 1: Critical Path (Week 1)
**Goal**: Fix revenue-critical agents
1. **Day 1-2**: OptimizationsCoreSubAgent
   - High business impact
   - Core value proposition
   
2. **Day 3-4**: ReportingSubAgent
   - User-facing insights
   - Data presentation layer
   
3. **Day 5**: DataSubAgent
   - Data processing pipeline
   - Foundation for other agents

### Phase 2: Infrastructure (Week 2)
**Goal**: Fix orchestration layer
1. **Day 1-2**: SupervisorAgent
   - Central orchestration
   - Affects all agent interactions
   
2. **Day 3**: GoalsTriageSubAgent
   - Routing logic
   - Goal management
   
3. **Day 4-5**: ActionsToMeetGoalsSubAgent
   - Action planning
   - Execution coordination

### Phase 3: Supporting Services (Week 3)
**Goal**: Complete remaining agents
1. **Day 1-2**: SyntheticDataSubAgent
2. **Day 3**: CorpusAdminSubAgent  
3. **Day 4**: DataHelperAgent
4. **Day 5**: Testing and validation

## Automation Tools

### 1. SSOT Violation Scanner
```bash
# Script to find common violations
python scripts/find_ssot_violations.py --agent <agent_name>
```

### 2. Migration Helper
```bash
# Automated refactoring suggestions
python scripts/migrate_to_user_context.py --agent <agent_name>
```

### 3. Test Generator
```bash
# Generate tests for refactored agents
python scripts/generate_agent_tests.py --agent <agent_name>
```

## Success Metrics

### Technical Metrics
- Zero duplicate implementations across agents
- 100% UserExecutionContext adoption
- No global state storage
- All agents pass isolation tests

### Business Metrics
- No increase in agent response times
- No new bugs introduced
- Improved concurrent user handling
- Reduced memory usage per request

## Risk Mitigation

### Backward Compatibility
- Make UserExecutionContext optional initially
- Maintain existing interfaces
- Gradual migration approach

### Testing Strategy
- Create comprehensive test suite before changes
- Test with and without context
- Load testing for concurrent users
- Integration testing with WebSocket events

### Rollback Plan
- Git branch for each agent refactoring
- Feature flags for new implementations
- Monitoring for performance degradation
- Quick revert capability

## Documentation Requirements

### Per Agent
- Update docstrings with context usage
- Document migration changes
- Update integration examples
- Add to DEFINITION_OF_DONE_CHECKLIST.md

### System-Wide
- Update LLM_MASTER_INDEX.md
- Add learnings to SPEC/learnings/
- Update architectural diagrams
- Create migration guide for future agents

## Timeline Summary

- **Week 1**: Revenue-critical agents (Tier 1)
- **Week 2**: Infrastructure agents (Tier 2)
- **Week 3**: Supporting services (Tier 3)
- **Week 4**: Testing, documentation, and deployment

## Next Steps

1. Create tracking issue in GitHub
2. Set up monitoring dashboards
3. Schedule daily standup for progress
4. Create agent-specific subtasks
5. Begin with OptimizationsCoreSubAgent audit

---

## Appendix: Quick Reference

### Key Files
- `netra_backend/app/core/serialization/unified_json_handler.py` - JSON SSOT
- `netra_backend/app/services/cache/cache_helpers.py` - Cache key generation
- `netra_backend/app/agents/supervisor/user_execution_context.py` - Context pattern
- `shared/isolated_environment.py` - Environment access
- `netra_backend/app/core/resilience/unified_retry_handler.py` - Retry logic

### Key Patterns
- Always make context optional for backward compatibility
- Use factory methods when available
- Prefer composition over inheritance
- Test isolation between concurrent requests

### Contact Points
- Architecture: Review with team lead
- Testing: Coordinate with QA
- Deployment: Work with DevOps
- Monitoring: Set up with observability team