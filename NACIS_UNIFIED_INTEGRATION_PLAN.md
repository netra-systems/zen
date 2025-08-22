# NACIS Unified Integration Implementation Plan

## Executive Summary

This plan outlines the complete integration of NACIS (Netra's Agentic Customer Interaction System) with the unified Netra platform. NACIS currently exists as isolated code that must be fully integrated with modern patterns, unified configuration, and existing infrastructure.

**Objective**: Transform NACIS from isolated component to fully integrated production system.

**Timeline**: 2 weeks for full integration

**Business Impact**: Enable $500K+ ARR premium consultation tier

## Phase 0: Critical System Integration (Days 1-3)

### 0.1 Agent Registration Integration

**File**: `netra_backend/app/agents/supervisor/agent_registry.py`

```python
# Add to _register_auxiliary_agents() method
def _register_nacis_agent(self) -> None:
    """Register NACIS agent if enabled in unified config."""
    from netra_backend.app.config import get_config
    
    if get_config().nacis.enabled:
        from netra_backend.app.agents.chat_orchestrator_main import ChatOrchestrator
        
        # Pass db_session from supervisor context
        orchestrator = ChatOrchestrator(
            db_session=self.db_session,  # Need to pass from supervisor
            llm_manager=self.llm_manager,
            websocket_manager=self.websocket_manager,
            tool_dispatcher=self.tool_dispatcher,
            cache_manager=self.cache_manager  # Unified Redis cache
        )
        
        self.register("nacis", orchestrator)
        logger.info("NACIS ChatOrchestrator registered successfully")
```

### 0.2 Unified Configuration Integration

**File**: `netra_backend/app/schemas/Config.py`

```python
class NACISConfig(BaseSettings):
    """NACIS configuration aligned with unified system."""
    enabled: bool = Field(default=False, env="NACIS_ENABLED")
    
    # Model cascade configuration
    tier1_model: str = Field(default="gpt-3.5-turbo", env="NACIS_TIER1_MODEL")
    tier2_model: str = Field(default="gpt-4", env="NACIS_TIER2_MODEL")
    tier3_model: str = Field(default="gpt-4-turbo", env="NACIS_TIER3_MODEL")
    
    # Cache configuration
    semantic_cache_enabled: bool = Field(default=True, env="NACIS_CACHE_ENABLED")
    cache_ttl: int = Field(default=3600, env="NACIS_CACHE_TTL")
    
    # Guardrails configuration
    guardrails_enabled: bool = Field(default=True, env="NACIS_GUARDRAILS_ENABLED")
    pii_redaction: bool = Field(default=True, env="NACIS_PII_REDACTION")
    
    # Research configuration
    deep_research_api_key: Optional[str] = Field(default=None, env="DEEP_RESEARCH_API_KEY")
    research_timeout: int = Field(default=30, env="NACIS_RESEARCH_TIMEOUT")
    
    # Sandbox configuration
    sandbox_enabled: bool = Field(default=True, env="NACIS_SANDBOX_ENABLED")
    sandbox_docker_image: str = Field(default="python:3.11-slim", env="NACIS_SANDBOX_IMAGE")

class AppConfig(BaseSettings):
    # ... existing config ...
    nacis: NACISConfig = Field(default_factory=NACISConfig)
```

### 0.3 Update ChatOrchestrator for Unified Patterns

**File**: `netra_backend/app/agents/chat_orchestrator_main.py`

```python
from netra_backend.app.config import get_config
from netra_backend.app.agents.base.interface import (
    BaseExecutionInterface, 
    ExecutionContext,
    WebSocketManagerProtocol
)
from netra_backend.app.core.cache.redis_cache_manager import RedisCacheManager

class ChatOrchestrator(ModernSupervisorAgent):
    """NACIS Chat Orchestrator with full unified integration."""
    
    def __init__(self,
                 db_session: AsyncSession,
                 llm_manager: LLMManager,
                 websocket_manager: WebSocketManagerProtocol,
                 tool_dispatcher: ToolDispatcher,
                 cache_manager: Optional[RedisCacheManager] = None):
        super().__init__(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        # Use unified configuration
        self.config = get_config().nacis
        self.nacis_enabled = self.config.enabled
        
        # Use injected unified cache manager
        self.cache_manager = cache_manager or RedisCacheManager.get_instance()
        
        # Initialize with unified patterns
        self._init_unified_components()
    
    def _init_unified_components(self) -> None:
        """Initialize components using unified patterns."""
        # Use unified WebSocket patterns
        self.trace_logger = TraceLogger(self.websocket_manager)
        
        # Use unified config for model cascade
        self.model_cascade = ModelCascade(
            tier1_model=self.config.tier1_model,
            tier2_model=self.config.tier2_model,
            tier3_model=self.config.tier3_model
        )
        
        # Initialize other components with config
        self.semantic_cache_enabled = self.config.semantic_cache_enabled
        self.guardrails_enabled = self.config.guardrails_enabled
```

### 0.4 Triage Routing Integration

**File**: `netra_backend/app/agents/triage_sub_agent/agent.py`

```python
class TriageSubAgent(BaseExecutionInterface, BaseSubAgent):
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute triage with NACIS routing support."""
        # Existing triage logic...
        
        # Check if should route to NACIS
        if await self._should_route_to_nacis(context):
            return {
                "next_agent": "nacis",
                "intent": "research_consultation",
                "confidence": context.metadata.get("confidence", 0.9),
                "reason": "Query requires research and verification capabilities"
            }
        
        # Continue with existing routing...
        return await self._execute_standard_triage(context)
    
    async def _should_route_to_nacis(self, context: ExecutionContext) -> bool:
        """Determine if query should route to NACIS."""
        from netra_backend.app.config import get_config
        
        if not get_config().nacis.enabled:
            return False
        
        # Check for NACIS-appropriate intents
        nacis_keywords = [
            "research", "verify", "fact-check", "analyze market",
            "compare solutions", "best practices", "industry standards",
            "ROI calculation", "TCO analysis", "benchmark"
        ]
        
        query = context.state.current_request.lower()
        
        # Check for keywords
        for keyword in nacis_keywords:
            if keyword in query:
                return True
        
        # Use LLM for intent classification if uncertain
        if context.metadata.get("intent_type") in ["research", "consultation", "analysis"]:
            return context.metadata.get("confidence", 0) >= 0.8
        
        return False
```

## Phase 1: Infrastructure Alignment (Days 4-6)

### 1.1 WebSocket Manager Alignment

**Update all NACIS components to use UnifiedWebSocketManager patterns:**

```python
# netra_backend/app/agents/chat_orchestrator/trace_logger.py
class TraceLogger:
    def __init__(self, websocket_manager: WebSocketManagerProtocol):
        self.websocket_manager = websocket_manager
    
    async def log(self, message: str, metadata: Dict = None) -> None:
        """Send trace log using unified WebSocket patterns."""
        if not self.websocket_manager:
            return
        
        # Use unified message format
        await self.websocket_manager.send_agent_update(
            run_id=self.current_run_id,
            agent_name="NACIS",
            update={
                "type": "trace",
                "message": message,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        )
```

### 1.2 Redis Cache Integration

**Implement semantic cache using unified Redis infrastructure:**

```python
# netra_backend/app/agents/chat_orchestrator/semantic_cache.py
from netra_backend.app.core.cache.redis_cache_manager import RedisCacheManager
from netra_backend.app.core.cache.cache_strategies import SemanticCacheStrategy

class NACISSemanticCache:
    def __init__(self, cache_manager: RedisCacheManager):
        self.cache_manager = cache_manager
        self.strategy = SemanticCacheStrategy()
    
    async def get_semantic_match(self, query: str, threshold: float = 0.85) -> Optional[Dict]:
        """Get semantically similar cached result."""
        # Use vector similarity search in Redis
        key_pattern = f"nacis:semantic:*"
        
        # Implement using Redis Vector Similarity Search (VSS)
        cached_items = await self.cache_manager.search_vectors(
            query_embedding=await self._get_embedding(query),
            namespace="nacis_semantic",
            threshold=threshold
        )
        
        if cached_items:
            return cached_items[0]  # Return best match
        return None
    
    async def cache_result(self, query: str, result: Dict, ttl: int = 3600) -> None:
        """Cache result with semantic embedding."""
        embedding = await self._get_embedding(query)
        
        await self.cache_manager.set_with_vector(
            key=f"nacis:semantic:{hash(query)}",
            value=result,
            vector=embedding,
            ttl=ttl
        )
```

### 1.3 Base Pattern Adoption

**Refactor NACIS components to use base patterns:**

```python
# netra_backend/app/agents/enhanced_researcher.py
from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.agents.base.interface import (
    BaseExecutionInterface,
    ExecutionContext,
    ExecutionResult
)

class EnhancedResearcherAgent(BaseExecutionInterface, BaseSubAgent):
    """Enhanced researcher using unified base patterns."""
    
    def __init__(self, llm_manager: LLMManager, config: NACISConfig):
        BaseSubAgent.__init__(
            self, 
            llm_manager,
            name="EnhancedResearcher",
            description="Research agent with verification capabilities"
        )
        BaseExecutionInterface.__init__(self, "EnhancedResearcher")
        self.config = config
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate research preconditions."""
        return bool(context.state.research_query)
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute research with verification."""
        # Use Deep Research API if available
        if self.config.deep_research_api_key:
            results = await self._deep_research(context)
        else:
            results = await self._fallback_research(context)
        
        # Apply Georgetown criteria
        verified_results = await self._verify_sources(results)
        
        return {
            "research_results": verified_results,
            "confidence_score": self._calculate_confidence(verified_results),
            "citations": self._format_citations(verified_results)
        }
```

## Phase 2: Component Modernization (Days 7-9)

### 2.1 Guardrails System Modernization

```python
# netra_backend/app/agents/chat_orchestrator/guardrails.py
from netra_backend.app.core.security.input_validator import InputValidator
from netra_backend.app.core.security.output_sanitizer import OutputSanitizer

class UnifiedGuardrails:
    """Guardrails system using unified security patterns."""
    
    def __init__(self, config: NACISConfig):
        self.config = config
        self.input_validator = InputValidator()
        self.output_sanitizer = OutputSanitizer()
    
    async def validate_input(self, text: str) -> Tuple[bool, str]:
        """Validate input using unified patterns."""
        # Use unified PII detection
        if self.config.pii_redaction:
            text = await self.input_validator.redact_pii(text)
        
        # Use unified jailbreak detection
        if await self.input_validator.is_jailbreak_attempt(text):
            return False, "Query rejected: Security policy violation"
        
        return True, text
    
    async def sanitize_output(self, response: str) -> str:
        """Sanitize output using unified patterns."""
        # Apply unified output sanitization
        response = await self.output_sanitizer.sanitize(response)
        
        # Add required disclaimers
        if self.config.guardrails_enabled:
            response = self._add_disclaimers(response)
        
        return response
```

### 2.2 Model Cascade with Unified Metrics

```python
# netra_backend/app/agents/chat_orchestrator/model_cascade.py
from netra_backend.app.core.monitoring.metrics import MetricsCollector

class UnifiedModelCascade:
    """Model cascade with unified monitoring."""
    
    def __init__(self, config: NACISConfig, metrics: MetricsCollector):
        self.config = config
        self.metrics = metrics
        self.tiers = {
            "fast": config.tier1_model,
            "balanced": config.tier2_model,
            "powerful": config.tier3_model
        }
    
    async def select_model(self, task: str, complexity: float) -> str:
        """Select model with metrics tracking."""
        selected_tier = self._determine_tier(complexity)
        
        # Track selection metrics
        self.metrics.increment(
            "nacis.model_selection",
            tags={"tier": selected_tier, "task": task}
        )
        
        return self.tiers[selected_tier]
```

### 2.3 Docker Sandbox Integration

```python
# netra_backend/app/tools/unified_sandbox.py
from netra_backend.app.core.docker.container_manager import ContainerManager

class UnifiedSandboxExecutor:
    """Sandboxed executor using unified Docker patterns."""
    
    def __init__(self, config: NACISConfig):
        self.config = config
        self.container_manager = ContainerManager()
        self.container_prefix = "netra_sandbox_"  # Unified prefix
    
    async def execute_code(self, code: str, timeout: int = 30) -> Dict:
        """Execute code in unified sandbox."""
        if not self.config.sandbox_enabled:
            return {"error": "Sandbox disabled"}
        
        container_config = {
            "image": self.config.sandbox_docker_image,
            "name": f"{self.container_prefix}{uuid.uuid4().hex[:8]}",
            "memory_limit": "512m",
            "cpu_quota": 50000,
            "network_mode": "none",
            "timeout": timeout
        }
        
        return await self.container_manager.run_isolated(
            code=code,
            config=container_config
        )
```

## Phase 3: Testing & Validation (Days 10-12)

### 3.1 Integration Tests

```python
# tests/integration/test_nacis_integration.py
import pytest
from netra_backend.app.config import get_config

@pytest.mark.asyncio
async def test_nacis_registration():
    """Test NACIS is properly registered in AgentRegistry."""
    config = get_config()
    config.nacis.enabled = True
    
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    
    registry = AgentRegistry(mock_llm, mock_dispatcher)
    registry.register_default_agents()
    
    assert "nacis" in registry.list_agents()
    assert registry.get("nacis") is not None

@pytest.mark.asyncio
async def test_triage_routes_to_nacis():
    """Test triage correctly routes to NACIS."""
    context = ExecutionContext(
        run_id="test",
        agent_name="triage",
        state=DeepAgentState(current_request="Research the best AI models for optimization")
    )
    
    triage = TriageSubAgent(mock_llm, mock_dispatcher)
    result = await triage.execute_core_logic(context)
    
    assert result["next_agent"] == "nacis"
    assert result["intent"] == "research_consultation"

@pytest.mark.asyncio
async def test_nacis_uses_unified_websocket():
    """Test NACIS uses UnifiedWebSocketManager."""
    orchestrator = ChatOrchestrator(
        mock_db, mock_llm, mock_websocket, mock_dispatcher
    )
    
    # Verify uses unified WebSocket patterns
    assert isinstance(orchestrator.websocket_manager, WebSocketManagerProtocol)
    
    # Test trace logging
    await orchestrator.trace_logger.log("Test message")
    assert mock_websocket.send_agent_update.called
```

### 3.2 End-to-End Validation

```python
# tests/e2e/test_nacis_e2e.py
@pytest.mark.e2e
async def test_nacis_full_flow():
    """Test complete NACIS flow from request to response."""
    # Start with supervisor
    supervisor = ModernSupervisorAgent(db, llm, websocket, dispatcher)
    
    state = DeepAgentState(
        current_request="What's the ROI of implementing Claude vs GPT-4?"
    )
    
    # Execute through supervisor
    await supervisor.execute(state, "test_run", stream_updates=True)
    
    # Verify flow
    assert state.triage_result["next_agent"] == "nacis"
    assert state.nacis_result is not None
    assert "roi_analysis" in state.nacis_result
    assert "citations" in state.nacis_result
```

## Phase 4: Production Deployment (Days 13-14)

### 4.1 Configuration Setup

```yaml
# .env.production
NACIS_ENABLED=true
NACIS_TIER1_MODEL=gpt-3.5-turbo
NACIS_TIER2_MODEL=gpt-4
NACIS_TIER3_MODEL=gpt-4-turbo
NACIS_CACHE_ENABLED=true
NACIS_GUARDRAILS_ENABLED=true
DEEP_RESEARCH_API_KEY=${DEEP_RESEARCH_KEY}
NACIS_SANDBOX_ENABLED=true
```

### 4.2 Monitoring Setup

```python
# netra_backend/app/monitoring/nacis_metrics.py
class NACISMonitoring:
    """Production monitoring for NACIS."""
    
    def setup_metrics(self):
        # Prometheus metrics
        self.request_counter = Counter(
            'nacis_requests_total',
            'Total NACIS requests',
            ['intent_type', 'status']
        )
        
        self.latency_histogram = Histogram(
            'nacis_latency_seconds',
            'NACIS request latency',
            ['operation']
        )
        
        self.cache_hit_rate = Gauge(
            'nacis_cache_hit_rate',
            'NACIS semantic cache hit rate'
        )
```

### 4.3 Gradual Rollout

```python
# netra_backend/app/core/feature_flags.py
class NACISFeatureFlag:
    """Gradual rollout control for NACIS."""
    
    def is_enabled_for_user(self, user_id: str) -> bool:
        """Check if NACIS enabled for specific user."""
        config = get_config()
        
        if not config.nacis.enabled:
            return False
        
        # Percentage rollout
        rollout_percentage = config.nacis.rollout_percentage
        
        # Use consistent hashing for user assignment
        user_hash = hash(user_id) % 100
        return user_hash < rollout_percentage
```

## Success Criteria

### Integration Milestones
- [ ] NACIS registered in AgentRegistry
- [ ] Triage routing to NACIS functional
- [ ] Unified configuration integrated
- [ ] WebSocket patterns aligned
- [ ] Redis cache operational
- [ ] Base patterns adopted

### Performance Targets
- Response time: <2s for 60% of queries
- Cache hit rate: >40%
- Model cascade optimization: 40% cost reduction
- Accuracy: 95%+ on benchmark queries

### Production Readiness
- [ ] All integration tests passing
- [ ] E2E tests validated
- [ ] Monitoring configured
- [ ] Feature flags operational
- [ ] Rollback plan documented

## Risk Mitigation

### Technical Risks
1. **WebSocket compatibility**: Test thoroughly with existing clients
2. **Cache poisoning**: Implement TTL and validation
3. **Sandbox escape**: Use hardened Docker containers
4. **Model drift**: A/B testing framework

### Operational Risks
1. **Rollout issues**: Use feature flags for gradual deployment
2. **Performance degradation**: Monitor latency metrics closely
3. **Cost overruns**: Implement usage limits and alerts

## Timeline Summary

**Week 1 (Days 1-7)**:
- Days 1-3: Critical system integration
- Days 4-6: Infrastructure alignment
- Day 7: Component modernization begins

**Week 2 (Days 8-14)**:
- Days 8-9: Complete modernization
- Days 10-12: Testing and validation
- Days 13-14: Production deployment

## Conclusion

This plan transforms NACIS from an isolated component into a fully integrated part of the Netra platform. By following unified patterns, leveraging existing infrastructure, and maintaining backward compatibility, we can deploy NACIS as a premium feature that drives significant revenue growth while maintaining system stability.

---

*Document Version: 1.0*
*Created: 2025-08-22*
*Author: Principal Engineer*
*Status: READY FOR IMPLEMENTATION*