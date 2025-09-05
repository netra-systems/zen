# Team 5: Registry Pattern Consolidation Prompt

## COPY THIS ENTIRE PROMPT:

You are a Registry Architecture Expert implementing SSOT consolidation for all Registry patterns across the codebase.

🚨 ULTRA CRITICAL FIRST ACTION - READ RECENT ISSUES:
Before ANY work, you MUST read and internalize the "Recent issues to be extra aware of" section from CLAUDE.md:
1. Race conditions in async/websockets - Plan ahead for concurrency
2. Solve 95% of cases first - Make breadth ironclad before edge cases  
3. Limit volume of code - Delete ugly tests rather than add complex code
4. This is a multi-user system - Always consider concurrent users

MANDATORY READING BEFORE STARTING:
1. CLAUDE.md (entire document, especially sections 2.1, 3.6, 6 AND the recent issues section)
2. USER_CONTEXT_ARCHITECTURE.md (factory patterns)
3. MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
4. docs/GOLDEN_AGENT_INDEX.md (agent registry patterns)
5. Registry section in DEFINITION_OF_DONE_CHECKLIST.md
6. METADATA_STORAGE_MIGRATION_AUDIT.md (metadata patterns)

YOUR SPECIFIC CONSOLIDATION TASKS:
1. Create ONE UniversalRegistry[T] generic class for ALL registries
2. Consolidate AgentRegistry, ToolRegistry, StrategyRegistry, etc.
3. Support factory registration for creating isolated instances
4. Implement thread-safe registration and lookup
5. Enable configuration-based registry population

TARGET IMPLEMENTATION:
```python
# Location: netra_backend/app/core/registry/universal_registry.py
from typing import TypeVar, Generic, Callable, Dict, Optional
import threading

T = TypeVar('T')

class UniversalRegistry(Generic[T]):
    """Generic SSOT registry supporting factory patterns"""
    
    def __init__(self, registry_name: str):
        self.name = registry_name
        self._items: Dict[str, T] = {}
        self._factories: Dict[str, Callable] = {}
        self._lock = threading.RLock()  # Thread-safe
        
    def register(self, key: str, item: T) -> None:
        """Register a singleton item"""
        with self._lock:
            if key in self._items:
                raise ValueError(f"{key} already registered in {self.name}")
            self._items[key] = item
            
    def register_factory(self, key: str, factory: Callable[[UserExecutionContext], T]) -> None:
        """Register factory for creating isolated instances"""
        with self._lock:
            if key in self._factories:
                raise ValueError(f"Factory {key} already registered in {self.name}")
            self._factories[key] = factory
    
    def get(self, key: str, context: Optional[UserExecutionContext] = None) -> T:
        """Get singleton or create instance via factory"""
        with self._lock:
            # Try singleton first
            if key in self._items:
                return self._items[key]
            
            # Try factory if context provided
            if key in self._factories and context:
                return self._factories[key](context)
                
            raise KeyError(f"{key} not found in {self.name}")
    
    def create_instance(self, key: str, context: UserExecutionContext) -> T:
        """Create isolated instance using registered factory"""
        with self._lock:
            if key not in self._factories:
                raise KeyError(f"No factory for {key} in {self.name}")
            return self._factories[key](context)

# Specialized registries using the universal pattern
class AgentRegistry(UniversalRegistry[BaseAgent]):
    """Agent-specific registry with WebSocket integration"""
    def __init__(self):
        super().__init__("AgentRegistry")
        self.websocket_manager = None
    
    def set_websocket_manager(self, manager: WebSocketManager):
        """Critical for WebSocket event emission"""
        self.websocket_manager = manager
        # Enhance all registered items with WebSocket
        for key in self._factories:
            # Factory will inject WebSocket on creation

class ToolRegistry(UniversalRegistry[Tool]):
    """Tool-specific registry"""
    pass

class StrategyRegistry(UniversalRegistry[Strategy]):
    """Strategy-specific registry"""
    pass
```

FILES TO CONSOLIDATE:
- AgentRegistry implementations (multiple found)
- ToolRegistry implementations
- StrategyRegistry implementations  
- ServiceRegistry implementations
- Any other registry patterns
- Registry initialization code

CRITICAL REQUIREMENTS:
1. Generate MRO report for registry hierarchies
2. Single generic UniversalRegistry base
3. Thread-safe registration and lookup
4. Support both singletons and factories
5. Preserve WebSocket integration for agents
6. Validate against MISSION_CRITICAL index
7. Test with real services
8. Extract registry logic before deletion
9. Support configuration-based setup
10. Enable hot-reloading if exists

VALUE PRESERVATION PROCESS (Per Registry):
1. Run git log - identify registry fixes
2. Grep for registration patterns
3. Check initialization sequences
4. Extract registry-specific logic
5. Document in extraction_report_[registry].md
6. Migrate registry tests
7. ONLY delete after extraction

TESTING AT EVERY STAGE:

Stage 1 - Pre-consolidation:
- [ ] Document all existing registries
- [ ] Run python tests/unified_test_runner.py --real-services --category registry
- [ ] Identify registration patterns
- [ ] Test thread-safety of current registries
- [ ] Document initialization order

Stage 2 - During consolidation:
- [ ] Test each registry migration
- [ ] Verify factory registration
- [ ] Test concurrent registration
- [ ] Ensure thread-safe lookups
- [ ] Verify WebSocket integration

Stage 3 - Post-consolidation:
- [ ] Full regression testing
- [ ] Load test registry lookups
- [ ] Concurrent registration tests
- [ ] Factory creation tests
- [ ] Memory profiling

CONTINUOUS BREAKING-CHANGE AUDIT:
After EVERY consolidation step, audit and update:
- [ ] All registry imports across codebase
- [ ] Registry initialization in main.py
- [ ] Factory registration calls
- [ ] Registry lookup patterns
- [ ] WebSocket manager injection
- [ ] Configuration loading for registries
- [ ] Test fixtures using registries
- [ ] API endpoints accessing registries
- [ ] Dependency injection points
- [ ] Service discovery mechanisms

DETAILED REPORTING REQUIREMENTS:
Create reports/team_05_registry_pattern_[timestamp].md with:

## Consolidation Report - Team 5: Registry Pattern
### Phase 1: Analysis
- Registries found: [list all registry types]
- Duplication patterns: [common code identified]
- Thread-safety issues: [current problems]
- Factory patterns: [existing implementations]
- WebSocket integration: [current approach]

### Phase 2: Implementation  
- SSOT location: netra_backend/app/core/registry/universal_registry.py
- Generic pattern: UniversalRegistry[T]
- Thread-safety: threading.RLock used
- Factory support: register_factory method
- Specializations: Agent, Tool, Strategy registries

### Phase 3: Validation
- Tests created: [registry operation tests]
- Tests passing: [percentage]
- Thread-safety verified: [concurrent test results]
- Factory patterns working: [test results]
- WebSocket integration: [verified for agents]

### Phase 4: Cleanup
- Registries consolidated: [count]
- Files deleted: [list]
- Imports updated: [count]
- Documentation: Registry patterns documented
- Learnings: Generic pattern benefits

### Evidence of Correctness:
- Test results for all registries
- Thread-safety verification
- Factory creation logs
- WebSocket event flow for agents
- Performance benchmarks
- Memory usage comparison

VALIDATION CHECKLIST:
- [ ] MRO report for registry hierarchy
- [ ] Generic UniversalRegistry created
- [ ] Thread-safe operations verified
- [ ] Factory pattern supported
- [ ] WebSocket integration preserved
- [ ] Absolute imports used
- [ ] Named values validated
- [ ] Tests with --real-services
- [ ] Value extracted from registries
- [ ] Extraction reports complete
- [ ] Configuration-based setup
- [ ] Zero direct registry access
- [ ] Legacy registries deleted
- [ ] CLAUDE.md compliance
- [ ] Breaking changes fixed
- [ ] No performance regression
- [ ] Multi-user safety verified
- [ ] Documentation complete

SUCCESS CRITERIA:
- Single UniversalRegistry[T] base class
- All registries using generic pattern
- Thread-safe registration/lookup
- Factory support for isolation
- WebSocket integration maintained
- Zero registry functionality loss
- Performance maintained/improved
- Configuration-based initialization
- Hot-reload support if applicable
- Complete consolidation

PRIORITY: P0 CRITICAL (Core infrastructure)
TIME ALLOCATION: 22 hours
EXPECTED REDUCTION: Multiple registries → 1 generic + specializations