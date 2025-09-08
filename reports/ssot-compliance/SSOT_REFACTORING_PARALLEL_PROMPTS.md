# 🚨 ULTRA CRITICAL: SSOT Refactoring Parallel Agent Prompts
**ULTRA THINK DEEPLY ALWAYS. Our lives DEPEND on you SUCCEEDING.**

## Executive Summary
These 5 prompts enable ATOMIC parallel refactoring of critical SSOT violations. Each agent works independently on their assigned scope, with completion resulting in 100% resolution of P0 violations, comprehensive testing, legacy deletion, and full compliance with CLAUDE.md principles.

**CRITICAL: All 5 agents MUST complete for the refactoring to be atomic and successful.**

---

## 🔴 PROMPT 1: Factory & WebSocket Emitter Consolidation Agent
**Priority:** P0 ULTRA CRITICAL  
**Time Estimate:** 8-10 hours  
**Dependencies:** None (can start immediately)

### LIFE OR DEATH MISSION:
You are the Factory Consolidation Specialist. Your mission is to eliminate the most critical SSOT violation: the duplicate agent instance factory and WebSocket emitter implementations. This duplication causes bugs to be fixed in one place but not another, breaking chat functionality - our PRIMARY business value.

### CRITICAL CONTEXT & REQUIREMENTS:
1. **READ FIRST (MANDATORY):**
   - [`CLAUDE.md`](CLAUDE.md) - Section 2.1 (SSOT principles), Section 6 (WebSocket requirements)
   - [`SPEC/type_safety.xml`](SPEC/type_safety.xml) - Principle TS-P1
   - [`SPEC/mega_class_exceptions.xml`](SPEC/mega_class_exceptions.xml) - Understand size limits
   - [`SPEC/learnings/websocket_agent_integration_critical.xml`](SPEC/learnings/websocket_agent_integration_critical.xml)
   - [`SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml`](SPEC/MISSION_CRITICAL_NAMED_VALUES_INDEX.xml)
   - [`USER_CONTEXT_ARCHITECTURE.md`](USER_CONTEXT_ARCHITECTURE.md) - Factory isolation patterns

2. **CURRENT VIOLATIONS TO FIX:**
   - `agent_instance_factory.py` (1073 lines) - Keep as base
   - `agent_instance_factory_optimized.py` (575 lines) - MUST DELETE after merging
   - 5+ duplicate `UserWebSocketEmitter` implementations across codebase

3. **DETAILED IMPLEMENTATION STEPS:**

   **Phase 1: MRO Analysis (MANDATORY per CLAUDE.md 3.6)**
   ```python
   # Generate comprehensive MRO report BEFORE touching any code
   # Document in reports/mro_analysis_factory_consolidation_[date].md
   - Map ALL classes in both factory files
   - Document inheritance hierarchies
   - Identify method overrides and resolution paths
   - Find all consumers and their usage patterns
   ```

   **Phase 2: Performance Configuration Architecture**
   ```python
   @dataclass
   class FactoryPerformanceConfig:
       """SSOT for all factory performance settings"""
       # Emitter pooling (from optimized version)
       enable_emitter_pooling: bool = True
       pool_initial_size: int = 20
       pool_max_size: int = 200
       pool_cleanup_interval: int = 300
       
       # Class caching (from optimized version)
       enable_class_caching: bool = True
       cache_size: int = 128
       cache_ttl: int = 3600
       
       # Metrics collection
       enable_metrics: bool = True
       metrics_sample_rate: float = 0.1
       
       # Object reuse
       enable_object_reuse: bool = True
       reuse_pool_size: int = 50
   ```

   **Phase 3: Merge Implementation**
   - Extract ALL optimizations from `agent_instance_factory_optimized.py`
   - Add as configurable features to base `agent_instance_factory.py`
   - Use strategy pattern for emitter selection:
     ```python
     def _create_emitter(self, config: FactoryPerformanceConfig):
         if config.enable_emitter_pooling:
             return self._get_pooled_emitter()
         return UserWebSocketEmitter(...)
     ```

   **Phase 4: WebSocket Emitter SSOT**
   - Create SINGLE `services/websocket_emitter.py`:
     ```python
     class UserWebSocketEmitter:
         """SSOT for all WebSocket agent event emissions"""
         # Merge ALL functionality from duplicates
         # Support pooling via configuration
         # Maintain backward compatibility
     ```
   - Delete ALL duplicate implementations
   - Update ALL imports (use grep to find every occurrence)

   **Phase 5: Comprehensive Testing**
   ```python
   # Create tests/unit/test_factory_consolidation.py
   - Test with pooling enabled/disabled
   - Test performance metrics collection
   - Test object reuse patterns
   - Test backward compatibility
   - Test with 100+ concurrent agent creations
   - Benchmark performance (must maintain <10ms creation time)
   ```

4. **VALIDATION CHECKLIST (MANDATORY):**
   - [ ] MRO report generated and saved
   - [ ] ALL optimizations preserved as config
   - [ ] Performance benchmarks show no regression
   - [ ] Zero duplicate WebSocket emitters remain
   - [ ] ALL imports updated to SSOT
   - [ ] `agent_instance_factory_optimized.py` DELETED
   - [ ] 50+ tests passing with real services
   - [ ] Mission critical WebSocket tests passing
   - [ ] Memory profiling shows pool cleanup working
   - [ ] Update string literals index

5. **SPAWN THESE SUB-AGENTS:**
   - **MRO Analysis Agent**: Document all inheritance before changes
   - **Performance Testing Agent**: Benchmark before/after
   - **Import Migration Agent**: Update all references
   - **Memory Profiling Agent**: Verify no leaks from pooling
   - **Integration Testing Agent**: Test with real WebSocket flows

6. **CRITICAL SUCCESS METRICS:**
   - Agent creation time: <10ms maintained
   - Zero WebSocket event drops
   - Memory usage stable over 1 hour
   - All 5 required WebSocket events working
   - 75% code reduction in factory domain

7. **ROLLBACK PLAN:**
   - Keep backup of original files
   - Feature flag for gradual rollout:
     ```python
     USE_CONSOLIDATED_FACTORY = os.getenv('USE_CONSOLIDATED_FACTORY', 'true')
     ```

### DELIVERABLES:
1. Single consolidated `agent_instance_factory.py` with config
2. Single `services/websocket_emitter.py` as SSOT
3. Deleted `agent_instance_factory_optimized.py`
4. MRO analysis report
5. Performance benchmark report
6. 50+ passing tests
7. Updated SPEC/learnings/factory_consolidation_2025.xml

---

## 🟠 PROMPT 2: Data Sub-Agent & Agent Architecture Consolidation
**Priority:** P0 CRITICAL  
**Time Estimate:** 8-10 hours  
**Dependencies:** Can run parallel with Prompt 1

### LIFE OR DEATH MISSION:
You are the Agent Architecture Specialist. Your mission is to eliminate the triple DataSubAgent implementation and consolidate all agent-related registries and patterns. This chaos prevents reliable agent execution - the core of our AI value delivery.

### CRITICAL CONTEXT & REQUIREMENTS:
1. **READ FIRST (MANDATORY):**
   - [`docs/GOLDEN_AGENT_INDEX.md`](docs/GOLDEN_AGENT_INDEX.md) - Definitive agent patterns
   - [`docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md`](docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)
   - [`SPEC/learnings/agent_execution_order_fix_20250904.xml`](SPEC/learnings/agent_execution_order_fix_20250904.xml)
   - [`AGENT_EXECUTION_ORDER_REASONING.md`](AGENT_EXECUTION_ORDER_REASONING.md)
   - [`SPEC/learnings/unified_agent_testing_implementation.xml`](SPEC/learnings/unified_agent_testing_implementation.xml)

2. **CURRENT VIOLATIONS TO FIX:**
   - `data_sub_agent/agent_core_legacy.py` - DELETE
   - `data_sub_agent/agent_legacy_massive.py` - DELETE  
   - `data_sub_agent/data_sub_agent.py` - Keep as SSOT
   - `supervisor/agent_registry.py` + `supervisor/agent_class_registry.py` - Merge

3. **DETAILED IMPLEMENTATION STEPS:**

   **Phase 1: DataSubAgent Audit & Consolidation**
   ```python
   # Analyze all three implementations
   - Document unique functionality in each
   - Identify which version has most complete features
   - Extract any unique optimizations from legacy versions
   - Verify data_sub_agent.py has ALL required functionality
   ```

   **Phase 2: Legacy Migration**
   ```python
   # Before deleting legacy files:
   - Search ENTIRE codebase for imports
   - Document all usage patterns
   - Create migration map:
     OLD: from data_sub_agent.agent_core_legacy import DataSubAgent
     NEW: from data_sub_agent.data_sub_agent import DataSubAgent
   ```

   **Phase 3: Registry Unification**
   ```python
   class UnifiedAgentRegistry:
       """SSOT for all agent registration and discovery"""
       
       # Merge functionality from both registries
       _agent_classes: Dict[str, Type[BaseAgent]] = {}
       _agent_instances: Dict[str, BaseAgent] = {}
       _agent_metadata: Dict[str, AgentMetadata] = {}
       
       def register_agent_class(self, agent_type: str, agent_class: Type[BaseAgent]):
           """Register an agent class for discovery"""
           
       def get_agent_instance(self, agent_type: str, config: AgentConfig):
           """Get or create agent instance with caching"""
           
       def discover_agents(self) -> List[str]:
           """Discover all available agent types"""
   ```

   **Phase 4: Supervisor Consolidation**
   ```python
   # Update supervisor_consolidated.py:
   - Use unified registry
   - Ensure execution order: Data BEFORE Optimization
   - Remove all legacy workflow patterns
   - Implement modern execution flow from GOLDEN_AGENT_INDEX
   ```

   **Phase 5: Comprehensive Agent Testing**
   ```python
   # Create tests/integration/test_agent_consolidation.py
   - Test all 37 agent types still work
   - Test agent discovery mechanism
   - Test registry caching behavior
   - Test supervisor execution order
   - Test with 50+ concurrent agent requests
   - Verify Data agent runs before Optimization
   ```

4. **VALIDATION CHECKLIST (MANDATORY):**
   - [ ] All unique functionality preserved
   - [ ] Legacy files DELETED completely
   - [ ] All imports updated to SSOT
   - [ ] Unified registry working
   - [ ] All 37 agents functioning
   - [ ] Execution order verified
   - [ ] 100+ agent tests passing
   - [ ] Performance benchmarks maintained
   - [ ] Git history searched for references
   - [ ] SPEC updated with patterns

5. **SPAWN THESE SUB-AGENTS:**
   - **Code Archaeology Agent**: Extract unique features from legacy
   - **Import Migration Agent**: Update all references
   - **Agent Testing Agent**: Verify all 37 types work
   - **Execution Order Agent**: Validate correct sequencing
   - **Performance Agent**: Benchmark consolidation impact

6. **CRITICAL SUCCESS METRICS:**
   - All 37 agent types operational
   - Agent discovery <100ms
   - Registry memory footprint <50MB
   - Correct execution order (Data→Optimization)
   - 40% reduction in agent codebase

### DELIVERABLES:
1. Single `data_sub_agent/data_sub_agent.py` implementation
2. Unified `supervisor/agent_registry.py`
3. Updated `supervisor_consolidated.py`
4. Deleted legacy files (2 data agents, 1 registry)
5. Migration documentation
6. 100+ passing agent tests
7. Updated SPEC/learnings/agent_consolidation_2025.xml

---

## 🟡 PROMPT 3: Tool Dispatcher & Execution Engine Unification
**Priority:** P1 HIGH  
**Time Estimate:** 10-12 hours  
**Dependencies:** Can run parallel, benefits from Prompt 1 completion

### LIFE OR DEATH MISSION:
You are the Execution Architecture Expert. Your mission is to unify the fragmented tool dispatchers (5+) and execution engines (6+) into coherent SSOT implementations. This fragmentation causes tool execution failures and inconsistent behavior - breaking agent functionality.

### CRITICAL CONTEXT & REQUIREMENTS:
1. **READ FIRST (MANDATORY):**
   - [`TOOL_DISPATCHER_MIGRATION_GUIDE.md`](TOOL_DISPATCHER_MIGRATION_GUIDE.md)
   - [`SPEC/learnings/websocket_agent_integration_critical.xml`](SPEC/learnings/websocket_agent_integration_critical.xml)
   - [`USER_CONTEXT_ARCHITECTURE.md`](USER_CONTEXT_ARCHITECTURE.md) - Request-scoped patterns

2. **CURRENT VIOLATIONS TO FIX:**
   **Tool Dispatchers (5+):**
   - `tool_dispatcher_unified.py` - Keep as base
   - `tool_dispatcher_core.py` - Merge and delete
   - `request_scoped_tool_dispatcher.py` - Extract pattern, delete
   - `admin_tool_dispatcher/dispatcher_core.py` - Merge admin features
   - `admin_tool_dispatcher/modernized_wrapper.py` - Delete

   **Execution Engines (6+):**
   - `supervisor/execution_engine.py` - Keep as base
   - `supervisor/user_execution_engine.py` - Merge user features
   - `supervisor/request_scoped_execution_engine.py` - Extract pattern
   - `data_sub_agent/execution_engine.py` - Merge data features
   - `supervisor/mcp_execution_engine.py` - Merge MCP features
   - `unified_tool_execution.py` - Delete after merging

3. **DETAILED IMPLEMENTATION STEPS:**

   **Phase 1: Tool Dispatcher Strategy Pattern**
   ```python
   class UnifiedToolDispatcher:
       """SSOT for all tool dispatching"""
       
       def __init__(self, strategy: DispatchStrategy = None):
           self.strategy = strategy or DefaultDispatchStrategy()
           self._request_scope = RequestScope()  # From request_scoped pattern
           
       async def dispatch(self, tool_name: str, params: Dict, context: ExecutionContext):
           # Unified dispatch with strategy pattern
           if self.strategy.requires_admin(tool_name):
               return await self._dispatch_admin(tool_name, params, context)
           return await self._dispatch_standard(tool_name, params, context)
           
       def with_request_scope(self, request_id: str):
           """Enable request-scoped isolation"""
           return RequestScopedDispatcher(self, request_id)
   ```

   **Phase 2: Execution Engine Composition**
   ```python
   class ExecutionEngine:
       """Base execution engine with composition"""
       
       def __init__(self, config: EngineConfig):
           self.config = config
           self._extensions = {}
           self._load_extensions()
           
       def _load_extensions(self):
           """Load engine extensions based on config"""
           if self.config.enable_user_features:
               self._extensions['user'] = UserExecutionExtension()
           if self.config.enable_mcp:
               self._extensions['mcp'] = MCPExecutionExtension()
           if self.config.enable_data_features:
               self._extensions['data'] = DataExecutionExtension()
               
       async def execute(self, task: Task, context: ExecutionContext):
           # Base execution with extension hooks
           for extension in self._extensions.values():
               await extension.pre_execute(task, context)
               
           result = await self._execute_core(task, context)
           
           for extension in self._extensions.values():
               result = await extension.post_execute(result, context)
               
           return result
   ```

   **Phase 3: Registry Consolidation**
   ```python
   class UnifiedToolRegistry:
       """SSOT for tool registration and discovery"""
       
       _tools: Dict[str, ToolDefinition] = {}
       _admin_tools: Set[str] = set()
       _tool_categories: Dict[str, List[str]] = {}
       
       def register_tool(self, name: str, definition: ToolDefinition, admin: bool = False):
           """Single registration point for all tools"""
           
       def discover_tools(self, context: Optional[ExecutionContext] = None):
           """Discover available tools with context filtering"""
   ```

   **Phase 4: Request-Scoped Isolation**
   ```python
   # Implement request-scoped pattern from USER_CONTEXT_ARCHITECTURE.md
   class RequestScopedDispatcher:
       """Request-scoped wrapper for isolation"""
       
       def __init__(self, dispatcher: UnifiedToolDispatcher, request_id: str):
           self.dispatcher = dispatcher
           self.request_id = request_id
           self.context = RequestContext(request_id)
           
       async def dispatch(self, tool_name: str, params: Dict):
           # Ensure complete isolation per request
           with self.context:
               return await self.dispatcher.dispatch(tool_name, params, self.context)
   ```

   **Phase 5: Migration & Testing**
   ```python
   # Create tests/integration/test_execution_consolidation.py
   - Test all dispatch strategies
   - Test request-scoped isolation
   - Test admin tool execution
   - Test MCP integration
   - Test 100+ concurrent executions
   - Test extension loading
   - Benchmark dispatch overhead (<5ms)
   ```

4. **VALIDATION CHECKLIST (MANDATORY):**
   - [ ] Single UnifiedToolDispatcher implementation
   - [ ] Single ExecutionEngine with extensions
   - [ ] Request-scoped isolation working
   - [ ] All tool types supported
   - [ ] All legacy files deleted
   - [ ] Performance maintained
   - [ ] 150+ tests passing
   - [ ] WebSocket notifications preserved
   - [ ] Admin tools functioning
   - [ ] MCP integration working

5. **SPAWN THESE SUB-AGENTS:**
   - **Pattern Extraction Agent**: Extract unique patterns from each implementation
   - **Performance Profiling Agent**: Ensure <5ms dispatch overhead
   - **Isolation Testing Agent**: Verify request-scoped isolation
   - **Admin Security Agent**: Validate admin tool security
   - **Integration Agent**: Test with real agent workflows

6. **CRITICAL SUCCESS METRICS:**
   - Single dispatch path for all tools
   - <5ms dispatch overhead maintained
   - 100% tool compatibility
   - Request isolation verified
   - 60% code reduction

### DELIVERABLES:
1. Single `UnifiedToolDispatcher` implementation
2. Single `ExecutionEngine` with extensions
3. Consolidated `UnifiedToolRegistry`
4. Deleted duplicate implementations (9+ files)
5. Migration guide for consumers
6. 150+ passing tests
7. Updated SPEC/learnings/execution_consolidation_2025.xml

---

## 🟢 PROMPT 4: WebSocket Manager & Infrastructure Consolidation
**Priority:** P1 HIGH  
**Time Estimate:** 8-10 hours  
**Dependencies:** Benefits from Prompt 1 WebSocket emitter work

### LIFE OR DEATH MISSION:
You are the Infrastructure Consolidation Expert. Your mission is to unify WebSocket managers, centralize ID generation (30+ scattered functions), and audit 197 manager classes. This infrastructure chaos causes session leaks and connection failures - breaking real-time chat.

### CRITICAL CONTEXT & REQUIREMENTS:
1. **READ FIRST (MANDATORY):**
   - [`WEBSOCKET_MODERNIZATION_REPORT.md`](WEBSOCKET_MODERNIZATION_REPORT.md)
   - [`SPEC/learnings/websocket_bridge_ssot_critical_fix.xml`](SPEC/learnings/websocket_bridge_ssot_critical_fix.xml)
   - [`docs/shared_library_pattern.md`](docs/shared_library_pattern.md)
   - [`SPEC/mega_class_exceptions.xml`](SPEC/mega_class_exceptions.xml) - WebSocket manager exception

2. **CURRENT VIOLATIONS TO FIX:**
   **WebSocket Managers:**
   - `websocket_core/manager.py` (1718 lines) - Keep as SSOT
   - `websocket/manager.py` - ConnectionScopedWebSocketManager - Merge features

   **ID Generation (30+ functions):**
   - Scattered across files
   - Must centralize in `core/unified_id_manager.py`

   **Manager Classes (197 total):**
   - Audit and reduce to <50 essential managers

3. **DETAILED IMPLEMENTATION STEPS:**

   **Phase 1: WebSocket Manager Consolidation**
   ```python
   # Analyze ConnectionScopedWebSocketManager features
   - Extract connection scoping logic
   - Identify unique functionality
   - Merge into base WebSocketManager as configurable feature:
   
   class WebSocketManager:
       """SSOT for all WebSocket management (mega class exception)"""
       
       def __init__(self, enable_connection_scoping: bool = True):
           self.enable_connection_scoping = enable_connection_scoping
           if enable_connection_scoping:
               self._connection_scopes = {}
               
       def get_connection_scope(self, connection_id: str):
           """Get or create connection-specific scope"""
           if not self.enable_connection_scoping:
               return self  # Use global scope
           return self._connection_scopes.setdefault(
               connection_id, 
               ConnectionScope(connection_id)
           )
   ```

   **Phase 2: ID Generation Centralization**
   ```python
   # Create core/unified_id_manager.py
   class UnifiedIDManager:
       """SSOT for all ID generation"""
       
       @staticmethod
       def generate_thread_id() -> str:
           """Generate thread ID: thr_[timestamp]_[random]"""
           
       @staticmethod
       def generate_connection_id() -> str:
           """Generate WebSocket connection ID: conn_[timestamp]_[random]"""
           
       @staticmethod
       def generate_message_id() -> str:
           """Generate message ID: msg_[timestamp]_[random]"""
           
       @staticmethod
       def generate_session_id() -> str:
           """Generate session ID: sess_[timestamp]_[random]"""
           
       @staticmethod
       def generate_request_id() -> str:
           """Generate request ID: req_[timestamp]_[random]"""
           
       # Add ALL other ID generation functions found
   ```

   **Phase 3: Manager Class Audit**
   ```python
   # Systematic manager audit:
   1. List all 197 manager classes
   2. Group by functionality domain
   3. Identify overlapping responsibilities
   4. Apply "Rule of Two" - merge if <2 unique use cases
   5. Create consolidation plan:
      - Keep: Core managers with clear single responsibility
      - Merge: Overlapping managers into domain managers
      - Delete: Unnecessary abstraction layers
   ```

   **Phase 4: Session Factory Cleanup**
   ```python
   class RequestScopedSessionFactory:
       """SSOT for database session management"""
       
       def __init__(self, config: SessionConfig):
           self.config = config
           self._sessions = {}
           
       def get_session(self, request_id: str):
           """Get request-scoped database session"""
           if request_id not in self._sessions:
               self._sessions[request_id] = self._create_session()
           return self._sessions[request_id]
           
       async def cleanup(self, request_id: str):
           """Clean up request session"""
           if request_id in self._sessions:
               await self._sessions[request_id].close()
               del self._sessions[request_id]
   ```

   **Phase 5: Comprehensive Testing**
   ```python
   # Create tests/integration/test_infrastructure_consolidation.py
   - Test WebSocket manager with/without scoping
   - Test all ID generation formats
   - Test ID uniqueness over 100k generations
   - Test session lifecycle management
   - Test manager consolidation didn't break features
   - Memory leak testing over 1 hour
   - Connection pool exhaustion tests
   ```

4. **VALIDATION CHECKLIST (MANDATORY):**
   - [ ] Single WebSocketManager with scoping
   - [ ] All ID generation centralized
   - [ ] Manager classes reduced to <50
   - [ ] No session leaks detected
   - [ ] All ID formats consistent
   - [ ] Zero duplicate managers
   - [ ] 200+ tests passing
   - [ ] Memory stable over 1 hour
   - [ ] Connection pools managed properly
   - [ ] Updated mega_class_exceptions.xml if needed

5. **SPAWN THESE SUB-AGENTS:**
   - **Manager Audit Agent**: Analyze all 197 managers systematically
   - **ID Pattern Agent**: Find and centralize all ID generation
   - **Memory Profiling Agent**: Detect session/connection leaks
   - **Consolidation Agent**: Merge overlapping managers
   - **Testing Agent**: Comprehensive infrastructure tests

6. **CRITICAL SUCCESS METRICS:**
   - 75% reduction in manager classes
   - Single ID generation source
   - Zero session leakage
   - <50 essential managers
   - Memory growth <100MB/hour

### DELIVERABLES:
1. Consolidated WebSocketManager with scoping
2. Complete `core/unified_id_manager.py`
3. Reduced manager classes (<50)
4. Session factory consolidation
5. Manager audit report
6. 200+ passing tests
7. Updated SPEC/learnings/infrastructure_consolidation_2025.xml

---

## ⚪ PROMPT 5: Testing, Validation & Legacy Cleanup Orchestrator
**Priority:** P0 CRITICAL  
**Time Estimate:** 6-8 hours  
**Dependencies:** Runs continuously, intensifies after other prompts complete

### LIFE OR DEATH MISSION:
You are the Quality Assurance & Cleanup Orchestrator. Your mission is to ensure ALL refactoring is atomic, complete, and tested. You validate other agents' work, remove ALL legacy code, and ensure zero regressions. Without you, the refactoring fails.

### CRITICAL CONTEXT & REQUIREMENTS:
1. **READ FIRST (MANDATORY):**
   - [`tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md`](tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md)
   - [`tests/mission_critical/test_websocket_agent_events_suite.py`](tests/mission_critical/test_websocket_agent_events_suite.py)
   - [`SPEC/git_commit_atomic_units.xml`](SPEC/git_commit_atomic_units.xml)
   - [`SPEC/learnings/index.xml`](SPEC/learnings/index.xml)
   - ALL reports from other agents

2. **CONTINUOUS VALIDATION TASKS:**
   - Monitor other agents' progress every 30 minutes
   - Run test suites after each major change
   - Track legacy code deletion
   - Ensure atomic commits
   - Update documentation

3. **DETAILED IMPLEMENTATION STEPS:**

   **Phase 1: Test Harness Setup (Hour 0-1)**
   ```python
   # Create tests/refactoring/continuous_validation.py
   class RefactoringValidator:
       """Continuous validation during SSOT refactoring"""
       
       def __init__(self):
           self.baseline_metrics = self._capture_baseline()
           self.test_suites = [
               'tests/mission_critical/test_websocket_agent_events_suite.py',
               'tests/integration/test_factory_consolidation.py',
               'tests/integration/test_agent_consolidation.py',
               'tests/integration/test_execution_consolidation.py',
               'tests/integration/test_infrastructure_consolidation.py'
           ]
           
       async def validate_continuously(self):
           """Run every 30 minutes during refactoring"""
           while True:
               results = await self._run_all_tests()
               self._compare_with_baseline(results)
               self._check_for_regressions()
               self._verify_legacy_removal()
               await asyncio.sleep(1800)  # 30 minutes
   ```

   **Phase 2: Legacy Code Tracking & Removal**
   ```python
   # Track ALL files marked for deletion
   LEGACY_FILES_TO_DELETE = [
       'agent_instance_factory_optimized.py',
       'data_sub_agent/agent_core_legacy.py',
       'data_sub_agent/agent_legacy_massive.py',
       'tool_dispatcher_core.py',
       'request_scoped_tool_dispatcher.py',
       'admin_tool_dispatcher/modernized_wrapper.py',
       # ... all other duplicate files
   ]
   
   def verify_legacy_removal():
       """Ensure ALL legacy files are deleted"""
       remaining = []
       for file in LEGACY_FILES_TO_DELETE:
           if os.path.exists(file):
               remaining.append(file)
       
       if remaining:
           raise Exception(f"Legacy files not deleted: {remaining}")
   ```

   **Phase 3: Import Verification**
   ```python
   def verify_no_legacy_imports():
       """Scan entire codebase for legacy imports"""
       legacy_patterns = [
           'from.*agent_instance_factory_optimized',
           'from.*agent_core_legacy',
           'from.*agent_legacy_massive',
           'from.*tool_dispatcher_core',
           # ... all legacy import patterns
       ]
       
       violations = []
       for pattern in legacy_patterns:
           # Use grep to find any remaining imports
           result = grep(pattern, recursive=True)
           if result:
               violations.append(result)
       
       if violations:
           raise Exception(f"Legacy imports still exist: {violations}")
   ```

   **Phase 4: Mission Critical Test Suite**
   ```python
   # Create tests/refactoring/test_ssot_complete.py
   class TestSSOTRefactoringComplete:
       """Comprehensive validation of SSOT refactoring"""
       
       def test_factory_consolidation_complete(self):
           # Verify single factory implementation
           # Verify performance maintained
           # Verify WebSocket events working
           
       def test_agent_consolidation_complete(self):
           # Verify all 37 agents working
           # Verify execution order correct
           # Verify no duplicate agents
           
       def test_tool_execution_consolidation_complete(self):
           # Verify single dispatch path
           # Verify all tools working
           # Verify request isolation
           
       def test_infrastructure_consolidation_complete(self):
           # Verify manager reduction
           # Verify ID centralization
           # Verify no session leaks
           
       def test_no_regressions(self):
           # Run ALL existing tests
           # Compare with baseline metrics
           # Verify no performance degradation
   ```

   **Phase 5: Documentation & Learnings**
   ```python
   # Update all documentation
   - Create SPEC/learnings/ssot_consolidation_2025.xml
   - Update CLAUDE.md with new patterns
   - Update README with architecture changes
   - Create migration guide for external consumers
   - Document all breaking changes
   ```

4. **VALIDATION CHECKLIST (MANDATORY):**
   - [ ] All 4 agent prompts completed
   - [ ] ALL legacy files deleted (verified)
   - [ ] Zero legacy imports remaining
   - [ ] 500+ tests passing
   - [ ] Mission critical tests passing
   - [ ] Performance benchmarks maintained
   - [ ] Memory leaks eliminated
   - [ ] Documentation updated
   - [ ] Learnings captured
   - [ ] Atomic commits created

5. **SPAWN THESE SUB-AGENTS:**
   - **Test Runner Agent**: Continuous test execution
   - **Import Scanner Agent**: Find legacy imports
   - **Performance Monitor Agent**: Track metrics
   - **Documentation Agent**: Update all docs
   - **Git Orchestrator Agent**: Ensure atomic commits

6. **CRITICAL SUCCESS METRICS:**
   - 100% legacy code removed
   - Zero import violations
   - All tests passing (500+)
   - No performance regression
   - Complete documentation

### DELIVERABLES:
1. Continuous validation reports
2. Legacy removal verification
3. Import scan results
4. 500+ passing tests
5. Performance comparison report
6. Updated documentation
7. SPEC/learnings/ssot_consolidation_2025.xml
8. Migration guide
9. Atomic git commits

---

## 🚨 EXECUTION COORDINATION & CRITICAL RULES

### PARALLEL EXECUTION TIMELINE:
```
Hour 0-2:  All 5 agents start simultaneously
Hour 2-4:  Agents 1-4 deep implementation, Agent 5 monitoring
Hour 4-6:  Mid-point synchronization, Agent 5 validates progress
Hour 6-8:  Agents 1-4 complete core work, Agent 5 intensifies
Hour 8-10: Final integration, cleanup, Agent 5 final validation
Hour 10:   ATOMIC COMPLETION - All done or rollback
```

### MANDATORY RULES FOR ALL AGENTS:

1. **ULTRA THINK DEEPLY** - Every decision impacts the entire system
2. **SSOT IS SACRED** - One implementation per concept, no exceptions
3. **SEARCH FIRST** - Always check for existing implementations
4. **MRO ANALYSIS** - Required for all refactoring (CLAUDE.md 3.6)
5. **TEST EVERYTHING** - Minimum 10 tests per feature
6. **DELETE LEGACY** - ALL old code must be removed
7. **ATOMIC COMMITS** - Follow SPEC/git_commit_atomic_units.xml
8. **REAL SERVICES** - NO MOCKS in testing
9. **DOCUMENT CHANGES** - Update SPEC/learnings
10. **COORDINATE** - Share discoveries via reports

### FAILURE CONTINGENCY:
If ANY agent fails:
1. Agent 5 triggers STOP for all agents
2. Capture failure state in report
3. Determine if partial rollback needed
4. Create recovery plan
5. Document in SPEC/learnings
6. Retry with adjusted approach

### SUCCESS CRITERIA:
✅ 15+ SSOT violations resolved  
✅ 75% code reduction achieved  
✅ 500+ tests passing  
✅ Zero performance regression  
✅ All legacy code deleted  
✅ Complete documentation  
✅ Atomic refactoring complete  

### BUSINESS VALUE DELIVERED:
- **50% reduction** in maintenance burden
- **75% faster** bug fixes
- **60% faster** developer onboarding
- **40% reduction** in test complexity
- **Consistent performance** across all paths
- **Chat system reliability** maintained

---

**REMEMBER: This refactoring determines the platform's future maintainability. Each agent's work is CRITICAL. Complete atomicity is required - all succeed or all fail. ULTRA THINK DEEPLY and execute with precision.**

**The system's SSOT compliance and our ability to deliver chat value depends on this refactoring succeeding completely.**