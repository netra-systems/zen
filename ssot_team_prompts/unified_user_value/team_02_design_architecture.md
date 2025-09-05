# Team B: Design Agent - ReportingSubAgent Resilience Architecture

## COPY THIS ENTIRE PROMPT:

You are a System Design Expert architecting resilience enhancements for the EXISTING ReportingSubAgent class.

CRITICAL: We are NOT designing a new system. We are adding resilience features to the EXISTING `ReportingSubAgent` class while maintaining it as the SINGLE SOURCE OF TRUTH for all reporting.

## MANDATORY FIRST ACTIONS:

1. READ `netra_backend/app/agents/reporting_sub_agent.py` - Current implementation
2. READ `reporting_crash_audit_and_plan.md` - Failure analysis
3. READ `USER_CONTEXT_ARCHITECTURE.md` - Factory patterns
4. READ `netra_backend/app/agents/base_agent.py` - Base class capabilities
5. ANALYZE integration points with workflow orchestrator

## YOUR DESIGN TASK:

### 1. Architecture Enhancements for ReportingSubAgent

```python
# Location: netra_backend/app/agents/reporting_sub_agent.py
class ReportingSubAgent(BaseAgent):
    """SSOT for ALL reporting - enhanced with resilience
    
    New Capabilities:
    - Progressive report generation
    - Checkpoint-based recovery
    - Automatic data_helper fallback
    - Graceful degradation
    """
    
    # NEW: Report generation strategies
    REPORT_STRATEGIES = {
        'FULL': FullReportStrategy,
        'STANDARD': StandardReportStrategy,
        'BASIC': BasicReportStrategy,
        'MINIMAL': MinimalReportStrategy,
        'FALLBACK': FallbackReportStrategy
    }
    
    # NEW: Checkpoint manager
    checkpoint_manager: CheckpointManager
    
    # NEW: Fallback coordinator
    fallback_coordinator: FallbackCoordinator
    
    # NEW: Retry policy
    retry_policy: ExponentialBackoffPolicy
```

### 2. Component Design

**A. Checkpoint System**
```python
class ReportCheckpointManager:
    """Manages report generation checkpoints"""
    
    async def save_section(self, run_id: str, section: str, content: Dict):
        """Save completed report section atomically"""
        
    async def load_progress(self, run_id: str) -> ReportProgress:
        """Load all saved sections for a run"""
        
    async def cleanup(self, run_id: str):
        """Remove checkpoints after successful completion"""
```

**B. Progressive Generation Strategy**
```python
class ProgressiveReportGenerator:
    """Generates best possible report with available data"""
    
    def determine_strategy(self, available_data: Dict) -> ReportStrategy:
        """Select appropriate generation strategy"""
        
    async def generate_sections(self, strategy: ReportStrategy) -> List[Section]:
        """Generate report sections based on strategy"""
```

**C. Fallback Coordinator**
```python  
class DataHelperFallbackCoordinator:
    """Coordinates fallback to data_helper on failure"""
    
    async def should_fallback(self, context: ExecutionContext) -> bool:
        """Determine if fallback is needed"""
        
    async def prepare_fallback_context(self, missing_data: List) -> FallbackContext:
        """Prepare context for data_helper invocation"""
        
    async def trigger_data_helper(self, context: FallbackContext) -> DataRequest:
        """Execute data_helper agent for missing data"""
```

### 3. Integration Points

**Workflow Orchestrator Integration:**
```python
# Location: workflow_orchestrator.py modifications
class WorkflowOrchestrator:
    async def handle_reporting_failure(self, error: Exception, context: ExecutionContext):
        """New: Handle reporting failures adaptively"""
        if isinstance(error, MissingDataError):
            # Route to data_helper
            return await self.execute_data_helper_fallback(context)
        elif isinstance(error, TransientError):
            # Retry with backoff
            return await self.retry_with_backoff(context)
```

**Factory Pattern Compliance:**
```python
class ReportingSubAgentFactory:
    """Factory maintaining single instance per request"""
    
    @staticmethod
    def create_for_context(context: UserExecutionContext) -> ReportingSubAgent:
        """Create properly configured instance"""
        agent = ReportingSubAgent(context)
        agent.checkpoint_manager = CheckpointManager(context)
        agent.fallback_coordinator = FallbackCoordinator(context)
        return agent
```

### 4. API Contracts

**Enhanced Execute Method:**
```python
async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
    """Execute with progressive generation and recovery
    
    Returns:
        Dict with guaranteed keys:
        - success: bool (always present)
        - report: str | Dict (always present, may be partial)
        - level: str (FULL|STANDARD|BASIC|MINIMAL|FALLBACK)
        - missing_data: List[str] (if applicable)
        - recovery_performed: bool
    """
```

**New Internal Methods:**
```python
async def _execute_with_recovery(self, context: UserExecutionContext) -> ReportResult:
    """Main execution with all recovery mechanisms"""
    
async def _generate_progressive_report(self, available_data: Dict) -> ReportResult:
    """Generate best possible report with available data"""
    
async def _trigger_data_collection(self, missing: List[str]) -> DataRequest:
    """Trigger data_helper for missing information"""
    
async def _save_checkpoint(self, section: str, content: Dict) -> None:
    """Save progress checkpoint"""
    
async def _load_checkpoints(self) -> Dict[str, Any]:
    """Load previous progress if exists"""
```

### 5. Error Handling Architecture

```python
class ReportingErrorHandler:
    """Centralized error handling with recovery strategies"""
    
    ERROR_STRATEGIES = {
        ValidationError: 'degrade_gracefully',
        TimeoutError: 'retry_with_backoff',
        SerializationError: 'use_fallback_format',
        LLMError: 'use_cached_or_template',
        RedisError: 'continue_without_cache'
    }
    
    async def handle(self, error: Exception, context: ExecutionContext) -> RecoveryAction:
        """Determine and execute recovery action"""
```

### 6. State Management

**Report Generation State:**
```python
@dataclass
class ReportGenerationState:
    """Tracks report generation progress"""
    run_id: str
    started_at: datetime
    completed_sections: List[str]
    pending_sections: List[str]
    strategy_level: str
    checkpoints_saved: List[str]
    recovery_attempts: int
    fallback_triggered: bool
```

### 7. Migration Architecture

**Phase 1: Add New Capabilities (Non-breaking)**
- Add checkpoint system
- Add progressive generation
- Add retry logic
- Keep existing behavior as default

**Phase 2: Update Consumers**
- Update workflow_orchestrator
- Update supervisor agent
- Update WebSocket handlers
- Update tests

**Phase 3: Remove Legacy Code**
- Remove old error handlers
- Remove duplicate reporting logic
- Clean up unused utilities

### 8. Performance Optimizations

```python
class ReportingPerformanceOptimizer:
    """Ensures resilience doesn't impact performance"""
    
    # Async checkpoint saves (non-blocking)
    checkpoint_executor = ThreadPoolExecutor(max_workers=2)
    
    # Connection pooling for Redis
    redis_pool = ConnectionPool(max_connections=10)
    
    # LRU cache for report templates
    template_cache = LRUCache(maxsize=100)
    
    # Circuit breaker for external services
    circuit_breaker = CircuitBreaker(failure_threshold=3)
```

## DELIVERABLES:

1. **architecture.md** - Complete technical design
2. **api_contracts.yaml** - OpenAPI specification
3. **sequence_diagrams.md** - Failure/recovery flows
4. **integration_guide.md** - How components integrate

## VALIDATION CHECKLIST:

- [ ] Maintains single ReportingSubAgent class
- [ ] All failure modes addressed
- [ ] Zero breaking changes in Phase 1
- [ ] Factory pattern preserved
- [ ] WebSocket events maintained
- [ ] Performance targets achievable
- [ ] Clean migration path defined
- [ ] All legacy code removal planned

Remember: This is an ENHANCEMENT to the existing ReportingSubAgent, maintaining it as the SINGLE SOURCE OF TRUTH for all reporting operations.