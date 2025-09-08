# Test Fixes - Parallel Agent Execution Prompts
## 5 Specialized Agents for Comprehensive Test Suite Repair
## Generated: 2025-09-03

---

# 🚀 AGENT 1: Import Error and Collection Failure Specialist

## Mission
Fix all 44+ import errors and collection failures preventing test execution. Your primary goal is to unblock test discovery and execution across the entire test suite.

## Context
- **Working Directory**: `C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1`
- **Python Version**: 3.12.4
- **Test Framework**: pytest 8.4.1
- **Critical Files**: 44+ test files with import/collection errors

## Specific Tasks

### Task 1: Fix Missing 'env' Variable (32+ files)
```python
# Add this import to all affected files:
from os import environ as env

# Affected file pattern:
tests/critical/test_*.py
tests/e2e/test_*.py
tests/integration/**/*.py
```

### Task 2: Fix Missing Module Imports
| File | Current Import | Fix Required |
|------|---------------|--------------|
| `test_mcp_integration.py` | `from netra_backend.app.agents.base.interface import AgentExecutionMixin` | Check if module exists, update path or create stub |
| `test_supervisor_bulletproof.py` | `from netra_backend.app.websocket_core import UnifiedWebSocketManager` | Find correct import path or use WebSocketManager |
| `test_auth_security_comprehensive.py` | `from netra_backend.app.auth_integration.auth import create_access_token` | Check auth module exports |

### Task 3: Validate All Imports
```bash
# Run this to verify fixes:
cd netra_backend
python -m pytest --collect-only tests/ 2>&1 | grep -E "ERROR collecting"
```

## Expected Deliverables
1. **Fixed Files List**: Document all files modified
2. **Import Map**: Create mapping of old imports → new imports
3. **Verification Script**: Script to validate all imports work
4. **Zero Collection Errors**: All tests should be discoverable

## Success Criteria
- [ ] No "ERROR collecting" messages in pytest output
- [ ] All 44 import errors resolved
- [ ] Test discovery completes without errors
- [ ] Document all changes in `IMPORT_FIXES_CHANGELOG.md`

---

# 🛡️ AGENT 2: BaseAgent Reliability Infrastructure Engineer

## Mission
Implement the missing reliability infrastructure in BaseAgent class including circuit breaker, reliability manager, and execution monitor to fix 18 agent infrastructure test failures.

## Context
- **Primary File**: `netra_backend/app/agents/base_agent.py`
- **Test File**: `tests/agents/test_base_agent_reliability_ssot.py`
- **Architecture**: Must follow USER_CONTEXT_ARCHITECTURE.md patterns
- **Inheritance**: Changes must propagate to all child agents

## Specific Tasks

### Task 1: Add Circuit Breaker
```python
# In BaseAgent.__init__():
from netra_backend.app.core.resilience.circuit_breaker import CircuitBreaker

self.circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception
)
```

### Task 2: Add Reliability Manager
```python
# Create and integrate reliability manager
from netra_backend.app.core.resilience.reliability_manager import ReliabilityManager

self.reliability_manager = ReliabilityManager(
    circuit_breaker=self.circuit_breaker,
    retry_policy={"max_attempts": 3, "backoff": "exponential"}
)
```

### Task 3: Add Execution Monitor
```python
# Implement execution monitoring
from netra_backend.app.agents.execution_tracking.monitor import ExecutionMonitor

self.execution_monitor = ExecutionMonitor(
    agent_name=self.__class__.__name__,
    metrics_enabled=True
)
```

### Task 4: Implement Health Status
```python
def get_health_status(self) -> Dict[str, Any]:
    """Aggregate health status from all components."""
    return {
        "circuit_breaker": self.circuit_breaker.state,
        "reliability": self.reliability_manager.get_status(),
        "execution_metrics": self.execution_monitor.get_metrics(),
        "status": "healthy" if self.circuit_breaker.state != "open" else "degraded"
    }
```

## Expected Deliverables
1. **Updated BaseAgent**: With all reliability infrastructure
2. **Child Agent Verification**: Ensure inheritance works
3. **Test Results**: All 18 reliability tests passing
4. **Documentation**: Update docstrings and type hints

## Success Criteria
- [ ] All test_base_agent_reliability_ssot.py tests pass
- [ ] Circuit breaker properly protects execution
- [ ] Health status aggregation works
- [ ] Child agents inherit all reliability features

---

# 📏 AGENT 3: Context Length Validation Specialist

## Mission
Implement comprehensive context length validation and truncation across all agent types to fix 9 critical context validation failures that risk token overflow and system crashes.

## Context
- **Test File**: `tests/agents/test_context_length_validation.py`
- **Affected Agents**: SupervisorAgent, DataSubAgent, TriageSubAgent, CorpusAdminSubAgent
- **Max Tokens**: Claude 3 = 200k, GPT-4 = 128k
- **Critical Risk**: Token overflow can crash the system

## Specific Tasks

### Task 1: Implement Token Counting
```python
# Add to BaseAgent
import tiktoken

def count_tokens(self, text: str, model: str = "gpt-4") -> int:
    """Count tokens for given text."""
    encoder = tiktoken.encoding_for_model(model)
    return len(encoder.encode(text))

def get_context_usage(self) -> Dict[str, int]:
    """Get current context token usage."""
    return {
        "prompt_tokens": self._prompt_tokens,
        "max_tokens": self.llm_manager.model_config.get("context_window", 128000),
        "usage_percent": (self._prompt_tokens / self.max_tokens) * 100
    }
```

### Task 2: Implement Context Truncation
```python
# Add intelligent truncation
def truncate_context(self, context: str, max_tokens: int) -> str:
    """Truncate context to fit within token limits."""
    current_tokens = self.count_tokens(context)
    
    if current_tokens <= max_tokens:
        return context
    
    # Implement sliding window truncation
    # Keep most recent context, summarize older
    return self._sliding_window_truncate(context, max_tokens)
```

### Task 3: Add Overflow Protection
```python
# Prevent context overflow
def validate_context_size(self, context: str) -> bool:
    """Validate context fits within limits."""
    tokens = self.count_tokens(context)
    max_allowed = self.llm_manager.model_config.get("context_window", 128000)
    
    if tokens > max_allowed * 0.9:  # 90% threshold warning
        logger.warning(f"Context near limit: {tokens}/{max_allowed}")
        
    if tokens > max_allowed:
        raise ContextOverflowError(f"Context exceeds limit: {tokens}/{max_allowed}")
    
    return True
```

### Task 4: Agent-Specific Implementations
```python
# SupervisorAgent
def _prepare_context(self, state: DeepAgentState) -> str:
    context = super()._prepare_context(state)
    return self.truncate_context(context, max_tokens=150000)

# DataSubAgent - handle large datasets
def _batch_data_processing(self, data: List) -> List:
    """Process data in batches to avoid context overflow."""
    batch_size = self._calculate_safe_batch_size(data)
    return [self._process_batch(batch) for batch in chunks(data, batch_size)]
```

## Expected Deliverables
1. **Token Counting System**: Accurate token measurement
2. **Truncation Strategy**: Intelligent context reduction
3. **Overflow Protection**: Prevent system crashes
4. **Metrics Tracking**: Context usage monitoring

## Success Criteria
- [ ] All 9 context validation tests pass
- [ ] No token overflow errors in any agent
- [ ] Context metrics properly tracked
- [ ] Document truncation strategies

---

# ⚙️ AGENT 4: Configuration System Repair Specialist

## Mission
Fix 10 configuration system failures related to environment detection, caching, and configuration loops that are breaking core system functionality.

## Context
- **Test Files**: `tests/core/test_configuration_*.py`
- **Core Module**: `netra_backend/app/core/configuration/`
- **Environments**: test, development, staging, production
- **Critical Issue**: Configuration loops and cache management

## Specific Tasks

### Task 1: Fix Environment Detection
```python
# In configuration manager
def detect_environment(self) -> str:
    """Reliably detect current environment."""
    # Priority order:
    # 1. Explicit ENVIRONMENT variable
    # 2. PYTEST_CURRENT_TEST (for tests)
    # 3. Development default
    
    if os.getenv("PYTEST_CURRENT_TEST"):
        return "test"
    
    env = os.getenv("ENVIRONMENT", "development").lower()
    valid_envs = ["test", "development", "staging", "production"]
    
    if env not in valid_envs:
        logger.warning(f"Invalid environment '{env}', defaulting to development")
        return "development"
    
    return env
```

### Task 2: Fix Cache Management
```python
# Implement proper cache lifecycle
class ConfigurationCache:
    def __init__(self):
        self._cache = {}
        self._environment = self.detect_environment()
        
    def should_clear_cache(self) -> bool:
        """Determine if cache should be cleared."""
        # Only clear in test environment
        return self._environment == "test" and os.getenv("PYTEST_CURRENT_TEST")
    
    def get_or_load(self, key: str, loader: Callable):
        """Get from cache or load."""
        if self.should_clear_cache():
            self._cache.clear()
        
        if key not in self._cache:
            self._cache[key] = loader()
        
        return self._cache[key]
```

### Task 3: Prevent Configuration Loops
```python
# Add loop detection
class ConfigurationLoader:
    def __init__(self):
        self._loading_stack = []
        
    def load_config(self, config_name: str):
        """Load configuration with loop prevention."""
        if config_name in self._loading_stack:
            raise ConfigurationLoopError(
                f"Configuration loop detected: {' -> '.join(self._loading_stack)} -> {config_name}"
            )
        
        self._loading_stack.append(config_name)
        try:
            config = self._do_load(config_name)
        finally:
            self._loading_stack.pop()
        
        return config
```

### Task 4: Performance Optimization
```python
# Optimize configuration loading
@lru_cache(maxsize=128)
def load_configuration(env: str) -> Dict:
    """Cache configuration per environment."""
    start = time.time()
    config = _load_from_source(env)
    
    duration = time.time() - start
    if duration > 1.0:
        logger.warning(f"Slow config load: {duration:.2f}s for {env}")
    
    return config
```

## Expected Deliverables
1. **Fixed Environment Detection**: Reliable env detection
2. **Cache Management**: Proper cache lifecycle
3. **Loop Prevention**: No configuration loops
4. **Performance**: Fast config loading (<1s)

## Success Criteria
- [ ] All 10 configuration tests pass
- [ ] No configuration loops in any environment
- [ ] Cache properly cleared in tests only
- [ ] Configuration loads in <1 second

---

# 📡 AGENT 5: WebSocket and Health Monitoring Specialist

## Mission
Restore WebSocket notification functionality and implement comprehensive health monitoring to fix critical user-facing features and system observability.

## Context
- **WebSocket Issues**: Error notifications not sent to users
- **Health Monitoring**: No system health visibility
- **Architecture**: Must follow WebSocketBridgeFactory patterns
- **User Impact**: Critical for chat functionality

## Specific Tasks

### Task 1: Fix WebSocket Error Notifications
```python
# In WebSocketManager or WebSocketBridge
async def send_error_notification(
    self,
    user_id: str,
    thread_id: str,
    error: Exception,
    context: Dict[str, Any]
):
    """Send error notification to user."""
    notification = {
        "type": "error",
        "timestamp": datetime.utcnow().isoformat(),
        "error": {
            "message": str(error),
            "type": error.__class__.__name__,
            "recoverable": isinstance(error, RecoverableError)
        },
        "context": context
    }
    
    await self.send_to_user(user_id, thread_id, notification)
```

### Task 2: Implement Circuit Breaker Notifications
```python
# Notify on circuit breaker state changes
async def notify_circuit_breaker_change(
    self,
    agent_name: str,
    old_state: str,
    new_state: str
):
    """Notify when circuit breaker state changes."""
    if new_state == "open":
        level = "error"
        message = f"{agent_name} circuit breaker opened - service degraded"
    elif new_state == "half_open":
        level = "warning"
        message = f"{agent_name} circuit breaker testing - recovery in progress"
    else:  # closed
        level = "info"
        message = f"{agent_name} circuit breaker closed - service restored"
    
    await self.broadcast_system_notification({
        "type": "circuit_breaker",
        "level": level,
        "message": message,
        "agent": agent_name,
        "state": new_state
    })
```

### Task 3: Implement Retry Notifications
```python
# Notify on retry attempts
async def notify_retry_attempt(
    self,
    operation: str,
    attempt: int,
    max_attempts: int,
    error: Exception
):
    """Notify user of retry attempts."""
    await self.send_notification({
        "type": "retry",
        "operation": operation,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "error": str(error),
        "message": f"Retrying {operation} (attempt {attempt}/{max_attempts})"
    })
```

### Task 4: Implement Health Status Aggregation
```python
# System-wide health monitoring
class HealthMonitor:
    def __init__(self):
        self.components = {}
        
    def register_component(self, name: str, component: Any):
        """Register component for health monitoring."""
        self.components[name] = component
        
    async def get_system_health(self) -> Dict[str, Any]:
        """Aggregate health from all components."""
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "components": {}
        }
        
        for name, component in self.components.items():
            try:
                if hasattr(component, 'get_health_status'):
                    component_health = await component.get_health_status()
                else:
                    component_health = {"status": "unknown"}
                    
                health["components"][name] = component_health
                
                # Update overall status
                if component_health.get("status") == "unhealthy":
                    health["overall_status"] = "unhealthy"
                elif component_health.get("status") == "degraded" and health["overall_status"] != "unhealthy":
                    health["overall_status"] = "degraded"
                    
            except Exception as e:
                health["components"][name] = {
                    "status": "error",
                    "error": str(e)
                }
                health["overall_status"] = "unhealthy"
        
        return health
    
    async def start_health_check_loop(self, interval: int = 60):
        """Periodically check and report health."""
        while True:
            health = await self.get_system_health()
            
            # Send health update via WebSocket
            await self.websocket_manager.broadcast_health_update(health)
            
            # Log critical issues
            if health["overall_status"] == "unhealthy":
                logger.error(f"System unhealthy: {health}")
            elif health["overall_status"] == "degraded":
                logger.warning(f"System degraded: {health}")
                
            await asyncio.sleep(interval)
```

### Task 5: Create Health Endpoint
```python
# Add health check endpoint
@router.get("/health/detailed")
async def get_detailed_health(
    health_monitor: HealthMonitor = Depends(get_health_monitor)
):
    """Get detailed system health."""
    health = await health_monitor.get_system_health()
    
    # Determine HTTP status
    if health["overall_status"] == "healthy":
        status_code = 200
    elif health["overall_status"] == "degraded":
        status_code = 206  # Partial Content
    else:
        status_code = 503  # Service Unavailable
        
    return JSONResponse(
        status_code=status_code,
        content=health
    )
```

## Expected Deliverables
1. **WebSocket Notifications**: All error types notified
2. **Circuit Breaker Alerts**: State change notifications
3. **Retry Notifications**: User-friendly retry messages
4. **Health Monitoring**: Complete system health visibility
5. **Health Endpoint**: REST API for health checks

## Success Criteria
- [ ] WebSocket error notifications working
- [ ] Circuit breaker notifications sent
- [ ] Retry attempts communicated to users
- [ ] Health status aggregation functional
- [ ] Health endpoint returns accurate status
- [ ] All WebSocket tests pass

---

# 🎯 Execution Strategy

## Parallel Execution Plan
All 5 agents should work simultaneously on their assigned areas:

1. **Agent 1**: Start immediately - unblocks all other testing
2. **Agent 2**: Can start immediately - independent implementation
3. **Agent 3**: Can start immediately - independent implementation  
4. **Agent 4**: Can start immediately - critical for system stability
5. **Agent 5**: Can start immediately - user-facing features

## Communication Protocol
- Create shared document: `TEST_FIX_PROGRESS.md`
- Update every 2 hours with progress
- Flag any blockers immediately
- Coordinate on shared dependencies

## Testing Protocol
```bash
# After each agent completes their tasks
cd netra_backend

# Agent 1 validation
python -m pytest --collect-only tests/ 2>&1 | grep -c "ERROR"  # Should be 0

# Agent 2 validation
python -m pytest tests/agents/test_base_agent_reliability_ssot.py -v

# Agent 3 validation
python -m pytest tests/agents/test_context_length_validation.py -v

# Agent 4 validation
python -m pytest tests/core/test_configuration*.py -v

# Agent 5 validation
python -m pytest tests/agents/test_base_agent_reliability_ssot.py::TestBaseAgentWebSocketNotificationsDuringFailures -v
```

## Final Integration Test
```bash
# Run all non-Docker tests
python tests/unified_test_runner.py --category unit --no-coverage

# Generate coverage report
python -m pytest tests/ --cov=netra_backend --cov-report=html
```

---

# 📊 Success Metrics

## Immediate Success (4 hours)
- [ ] Agent 1: All import errors fixed
- [ ] Agent 2: BaseAgent has all reliability attributes
- [ ] Agent 3: Token counting implemented
- [ ] Agent 4: Environment detection fixed
- [ ] Agent 5: WebSocket manager restored

## Complete Success (8 hours)
- [ ] All 44 collection errors resolved
- [ ] All 45 test failures fixed
- [ ] 95%+ of unit tests passing
- [ ] Health monitoring operational
- [ ] No configuration loops

## Documentation Requirements
Each agent must create:
1. **Change Log**: List of all files modified
2. **Test Results**: Before/after test outcomes
3. **Implementation Notes**: Key decisions and trade-offs
4. **Future Recommendations**: Long-term improvements

---

# 📝 Final Notes

## Critical Dependencies
- All agents need access to the same codebase
- Coordinate on shared files (especially BaseAgent)
- Test changes in isolation before integration

## Risk Mitigation
- Create backups before major changes
- Test incrementally
- Use version control for all changes
- Document any breaking changes

## Support Resources
- CLAUDE.md for coding standards
- USER_CONTEXT_ARCHITECTURE.md for patterns
- TEST_ARCHITECTURE_VISUAL_OVERVIEW.md for test structure
- LLM_MASTER_INDEX.md for navigation

---

*Generated: 2025-09-03 | Version: 1.0.0*
*Total Estimated Time: 8 hours with 5 parallel agents*