# 🚨 ULTRA CRITICAL: Parallel SSOT Refactoring Agent Prompts V2
**Date:** 2025-09-04  
**Status:** READY FOR EXECUTION  
**Scope:** Complete remaining SSOT violations  

## Executive Summary
These 5 prompts enable ATOMIC parallel refactoring of remaining SSOT violations. Each agent works independently with zero dependencies initially, converging only for integration testing.

---

## 🔴 AGENT 1: Data SubAgent Consolidation Specialist

### YOUR MISSION (LIFE OR DEATH CRITICAL)
You are the Data Architecture Specialist. The `data_sub_agent/` folder contains 30+ files with massive duplication - the LARGEST remaining SSOT violation. Your mission: Create ONE unified data agent that preserves ALL functionality while eliminating ALL duplication.

### MANDATORY READING BEFORE STARTING
```bash
# Read these files IN THIS ORDER:
1. CLAUDE.md - Sections 2.1 (SSOT), 3.6 (Refactoring Process), 6 (WebSocket)
2. USER_CONTEXT_ARCHITECTURE.md - Factory isolation patterns
3. SPEC/type_safety.xml - SSOT principles
4. SPEC/learnings/execution_consolidation_2025.xml - Extension patterns
5. AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md - Agent relationships
```

### YOUR SPECIFIC TASKS

#### Phase 1: MRO Analysis (MANDATORY - 2 hours)
```python
# Generate MRO report for ALL classes in data_sub_agent/
import inspect
import os

def analyze_data_agent_mro():
    report = []
    for file in os.listdir('netra_backend/app/agents/data_sub_agent/'):
        if file.endswith('.py'):
            # Import and analyze each class
            # Document inheritance, methods, consumers
    
    # Save to: reports/mro_analysis_data_agent_20250904.md
    # Include:
    # - All 30+ classes and their relationships
    # - Method override patterns
    # - Consumer analysis (who calls what)
    # - Duplication patterns identified
```

#### Phase 2: Design Unified Architecture (3 hours)
```python
# netra_backend/app/agents/data_sub_agent/unified_data_agent.py

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

class DataOperationType(Enum):
    CORPUS = "corpus"
    ANALYSIS = "analysis"
    ANOMALY = "anomaly"
    CACHE = "cache"
    EXECUTION = "execution"

@dataclass
class DataAgentConfig:
    """Configuration for unified data agent"""
    enable_caching: bool = True
    cache_ttl: int = 3600
    enable_anomaly_detection: bool = True
    anomaly_threshold: float = 0.8
    corpus_batch_size: int = 100
    analysis_timeout: int = 30
    max_concurrent_operations: int = 10

class UnifiedDataAgent:
    """
    SSOT for ALL data agent operations.
    Consolidates 30+ files into single, strategy-based implementation.
    """
    
    def __init__(self, config: DataAgentConfig):
        self.config = config
        self._strategies = self._init_strategies()
        self._cache = self._init_cache() if config.enable_caching else None
        
    def _init_strategies(self) -> Dict[DataOperationType, 'BaseStrategy']:
        """Initialize all operation strategies"""
        return {
            DataOperationType.CORPUS: CorpusOperationStrategy(),
            DataOperationType.ANALYSIS: AnalysisEngineStrategy(),
            DataOperationType.ANOMALY: AnomalyDetectionStrategy(),
            DataOperationType.CACHE: CacheManagementStrategy(),
            DataOperationType.EXECUTION: ExecutionStrategy()
        }
    
    async def execute(self, operation: DataOperationType, **kwargs):
        """Unified execution entry point"""
        strategy = self._strategies[operation]
        
        # Check cache first
        if self._cache and operation.cacheable:
            cached = await self._cache.get(operation, kwargs)
            if cached:
                return cached
        
        # Execute operation
        result = await strategy.execute(**kwargs)
        
        # Cache result
        if self._cache and operation.cacheable:
            await self._cache.set(operation, kwargs, result)
        
        return result
```

#### Phase 3: Implement Strategies (8 hours)
```python
# Consolidate each group of files into a strategy:

class CorpusOperationStrategy:
    """Consolidates: agent_corpus_operations.py, corpus_helpers.py, etc."""
    async def execute(self, **kwargs):
        # Merge all corpus logic here
        pass

class AnalysisEngineStrategy:
    """Consolidates: analysis_engine.py, analysis_operations.py, helpers, etc."""
    async def execute(self, **kwargs):
        # Merge all analysis logic here
        pass

class AnomalyDetectionStrategy:
    """Consolidates: anomaly_detection.py, agent_anomaly_processing.py, etc."""
    async def execute(self, **kwargs):
        # Merge all anomaly logic here
        pass

# Continue for all operation types...
```

#### Phase 4: Migration & Testing (5 hours)
```python
# tests/unit/test_unified_data_agent.py

class TestUnifiedDataAgent:
    """Comprehensive tests for consolidated data agent"""
    
    async def test_corpus_operations_preserved(self):
        """Verify all corpus functionality works"""
        pass
    
    async def test_analysis_engine_compatibility(self):
        """Ensure analysis operations unchanged"""
        pass
    
    async def test_anomaly_detection_accuracy(self):
        """Validate anomaly detection still works"""
        pass
    
    async def test_cache_performance(self):
        """Benchmark cache operations"""
        pass
    
    async def test_concurrent_operations(self):
        """Test 10+ concurrent data operations"""
        pass
    
    async def test_websocket_events_delivered(self):
        """Ensure all events still fire"""
        pass
```

#### Phase 5: Delete Legacy Code (2 hours)
```bash
# After ALL tests pass, delete these files:
rm netra_backend/app/agents/data_sub_agent/agent_anomaly_processing.py
rm netra_backend/app/agents/data_sub_agent/agent_cache.py
rm netra_backend/app/agents/data_sub_agent/agent_corpus_operations.py
rm netra_backend/app/agents/data_sub_agent/agent_data_processing.py
rm netra_backend/app/agents/data_sub_agent/agent_execution.py
rm netra_backend/app/agents/data_sub_agent/analysis_operations.py
# ... delete all 30+ legacy files

# Update all imports
grep -r "from.*data_sub_agent" --include="*.py" | while read line; do
    # Update to use unified_data_agent
done
```

### SUCCESS CRITERIA
- [ ] Single UnifiedDataAgent class < 1500 lines
- [ ] All 30+ files consolidated to < 5 files
- [ ] Zero functionality regression
- [ ] All tests passing
- [ ] < 100ms operation latency
- [ ] Memory usage reduced by 50%

---

## 🟠 AGENT 2: Registry Pattern Unification Architect

### YOUR MISSION
You are the Registry Architect. Multiple registry implementations exist throughout the codebase. Create ONE universal registry pattern that handles agents, tools, services, and any future registry needs.

### MANDATORY READING
```bash
1. CLAUDE.md - Section 2.1 (SSOT principles)
2. SPEC/type_safety.xml - Registry patterns
3. SPEC/learnings/execution_consolidation_2025.xml - Registry consolidation examples
```

### YOUR SPECIFIC TASKS

#### Phase 1: Audit Existing Registries (2 hours)
```python
# Find ALL registry patterns:
"""
Current violations:
- netra_backend/app/agents/supervisor/agent_registry.py
- netra_backend/app/agents/supervisor/agent_class_registry.py  
- netra_backend/app/agents/tool_registry_unified.py
- netra_backend/app/agents/tool_dispatcher_registry.py
- netra_backend/app/services/unified_tool_registry/registry.py
- Plus 10+ ad-hoc registries
"""

# Document in: reports/registry_audit_20250904.md
```

#### Phase 2: Create Universal Registry (4 hours)
```python
# netra_backend/app/core/universal_registry.py

from typing import Generic, TypeVar, Dict, List, Optional, Callable, Any
from datetime import datetime
import asyncio
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class RegistryMetadata:
    """Metadata for registered items"""
    registered_at: datetime
    category: str
    tags: List[str] = None
    permissions: List[str] = None
    custom: Dict[str, Any] = None

class UniversalRegistry(Generic[T]):
    """
    SSOT for ALL registry needs.
    Thread-safe, async-compatible, with metadata support.
    """
    
    def __init__(self, category: str, validator: Optional[Callable] = None):
        self.category = category
        self.validator = validator
        self._items: Dict[str, T] = {}
        self._metadata: Dict[str, RegistryMetadata] = {}
        self._aliases: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        
    async def register(
        self, 
        name: str, 
        item: T, 
        aliases: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Register item with optional aliases and metadata"""
        # Validate if validator provided
        if self.validator and not self.validator(item):
            raise ValueError(f"Item {name} failed validation")
        
        async with self._lock:
            self._items[name] = item
            self._metadata[name] = RegistryMetadata(
                registered_at=datetime.now(),
                category=self.category,
                custom=metadata or {}
            )
            
            # Register aliases
            if aliases:
                for alias in aliases:
                    self._aliases[alias] = name
    
    def get(self, name: str) -> Optional[T]:
        """Get item by name or alias"""
        # Check aliases first
        if name in self._aliases:
            name = self._aliases[name]
        return self._items.get(name)
    
    def discover(
        self, 
        filter_fn: Optional[Callable[[str, T], bool]] = None,
        tags: Optional[List[str]] = None
    ) -> List[T]:
        """Discover items with optional filtering"""
        items = list(self._items.items())
        
        # Filter by tags if provided
        if tags:
            items = [
                (k, v) for k, v in items 
                if self._metadata[k].tags and 
                any(tag in self._metadata[k].tags for tag in tags)
            ]
        
        # Apply custom filter
        if filter_fn:
            items = [(k, v) for k, v in items if filter_fn(k, v)]
        
        return [v for k, v in items]
    
    async def unregister(self, name: str) -> bool:
        """Remove item from registry"""
        async with self._lock:
            if name in self._items:
                del self._items[name]
                del self._metadata[name]
                # Remove aliases
                self._aliases = {
                    k: v for k, v in self._aliases.items() 
                    if v != name
                }
                return True
        return False
```

#### Phase 3: Create Specialized Facades (4 hours)
```python
# netra_backend/app/agents/supervisor/unified_agent_registry.py

from typing import Type
from netra_backend.app.core.universal_registry import UniversalRegistry

class UnifiedAgentRegistry:
    """Facade for agent registration using UniversalRegistry"""
    
    def __init__(self):
        self._registry = UniversalRegistry[Type['BaseAgent']](
            category="agents",
            validator=self._validate_agent_class
        )
        self._init_builtin_agents()
    
    def _validate_agent_class(self, agent_class: Type) -> bool:
        """Validate agent class has required methods"""
        return all(hasattr(agent_class, m) for m in ['execute', 'get_capabilities'])
    
    async def register_agent(
        self,
        agent_class: Type['BaseAgent'],
        aliases: Optional[List[str]] = None
    ):
        """Register agent with capabilities metadata"""
        await self._registry.register(
            name=agent_class.__name__,
            item=agent_class,
            aliases=aliases,
            metadata={
                "capabilities": agent_class.get_capabilities(),
                "requires_auth": getattr(agent_class, 'requires_auth', False),
                "max_concurrent": getattr(agent_class, 'max_concurrent', 1)
            }
        )
    
    def get_agent(self, name: str) -> Optional[Type['BaseAgent']]:
        """Get agent class by name"""
        return self._registry.get(name)
    
    def discover_agents(self, capability: Optional[str] = None) -> List[Type['BaseAgent']]:
        """Discover agents with optional capability filter"""
        if capability:
            return self._registry.discover(
                filter_fn=lambda k, v: capability in v.get_capabilities()
            )
        return self._registry.discover()

# Similarly create UnifiedToolRegistry facade
```

#### Phase 4: Migration Script (6 hours)
```python
# scripts/migrate_to_universal_registry.py

async def migrate_registries():
    """Migrate all existing registries to universal pattern"""
    
    # 1. Load existing registry data
    old_agent_registry = load_old_agent_registry()
    old_tool_registry = load_old_tool_registry()
    
    # 2. Create new registries
    agent_registry = UnifiedAgentRegistry()
    tool_registry = UnifiedToolRegistry()
    
    # 3. Migrate data
    for agent in old_agent_registry.get_all():
        await agent_registry.register_agent(agent)
    
    for tool in old_tool_registry.get_all():
        await tool_registry.register_tool(tool)
    
    # 4. Update all imports
    update_imports()
    
    # 5. Delete old registry files
    delete_legacy_registries()
```

### SUCCESS CRITERIA
- [ ] Single UniversalRegistry base class
- [ ] 3-4 specialized facades only
- [ ] All registries migrated
- [ ] 80% code reduction
- [ ] Zero lookup regression
- [ ] Thread-safe operations

---

## 🟡 AGENT 3: Supervisor Pattern Completion Expert

### YOUR MISSION
Complete the `supervisor_consolidated.py` implementation with proper workflow orchestration, agent coordination, and WebSocket event integration.

### MANDATORY READING
```bash
1. CLAUDE.md - Section 6 (WebSocket requirements)
2. AGENT_EXECUTION_ORDER_REASONING.md - Critical execution order
3. docs/GOLDEN_AGENT_INDEX.md - Agent patterns
4. SPEC/learnings/websocket_agent_integration_critical.xml
```

### YOUR SPECIFIC TASKS

#### Phase 1: Analyze Current State (2 hours)
```python
# Review supervisor_consolidated.py
# Document what's missing:
"""
Missing components:
1. Workflow orchestration logic
2. Agent coordination strategies  
3. Execution order enforcement
4. WebSocket event integration
5. Error recovery patterns
6. Result aggregation
"""
```

#### Phase 2: Complete Supervisor Implementation (8 hours)
```python
# netra_backend/app/agents/supervisor_consolidated.py

from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
from dataclasses import dataclass

class AgentPriority(Enum):
    """Execution priority based on business logic"""
    DATA_COLLECTION = 1
    DATA_ANALYSIS = 2
    OPTIMIZATION = 3
    VALIDATION = 4
    REPORTING = 5

@dataclass
class WorkflowDefinition:
    """Defines multi-agent workflow"""
    name: str
    agents: List['AgentConfig']
    coordination: str = "sequential"  # sequential, parallel, dag
    timeout: int = 300
    retry_policy: Optional['RetryPolicy'] = None

class UnifiedSupervisor:
    """
    SSOT for all agent orchestration and coordination.
    Ensures correct execution order and WebSocket notifications.
    """
    
    def __init__(
        self,
        factory: 'AgentInstanceFactory',
        websocket_manager: 'WebSocketManager',
        registry: 'UnifiedAgentRegistry'
    ):
        self.factory = factory
        self.websocket = websocket_manager
        self.registry = registry
        self.running_workflows: Dict[str, WorkflowExecution] = {}
        
    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        context: 'RequestContext'
    ) -> WorkflowResult:
        """
        Execute multi-agent workflow with proper ordering and notifications.
        CRITICAL: Must respect execution order from AGENT_EXECUTION_ORDER_REASONING.md
        """
        workflow_id = self._generate_workflow_id()
        
        try:
            # Notify workflow start
            await self.websocket.send_event(
                context.user_id,
                "workflow_started",
                {"workflow_id": workflow_id, "name": workflow.name}
            )
            
            # Order agents by priority
            ordered_agents = self._order_agents_by_priority(workflow.agents)
            
            # Create execution tracker
            execution = WorkflowExecution(
                workflow_id=workflow_id,
                workflow=workflow,
                context=context,
                started_at=datetime.now()
            )
            self.running_workflows[workflow_id] = execution
            
            # Execute based on coordination strategy
            if workflow.coordination == "sequential":
                result = await self._execute_sequential(ordered_agents, execution)
            elif workflow.coordination == "parallel":
                result = await self._execute_parallel(ordered_agents, execution)
            elif workflow.coordination == "dag":
                result = await self._execute_dag(ordered_agents, execution)
            else:
                raise ValueError(f"Unknown coordination: {workflow.coordination}")
            
            # Notify completion
            await self.websocket.send_event(
                context.user_id,
                "workflow_completed",
                {"workflow_id": workflow_id, "result": result.summary}
            )
            
            return result
            
        except Exception as e:
            # Notify failure
            await self.websocket.send_event(
                context.user_id,
                "workflow_failed",
                {"workflow_id": workflow_id, "error": str(e)}
            )
            raise
        finally:
            # Cleanup
            if workflow_id in self.running_workflows:
                del self.running_workflows[workflow_id]
    
    def _order_agents_by_priority(self, agents: List['AgentConfig']) -> List['AgentConfig']:
        """
        CRITICAL: Enforce execution order.
        Data agents MUST run before optimization agents.
        """
        priority_map = {
            'DataSubAgent': AgentPriority.DATA_COLLECTION,
            'AnalysisAgent': AgentPriority.DATA_ANALYSIS, 
            'OptimizationAgent': AgentPriority.OPTIMIZATION,
            'ValidationAgent': AgentPriority.VALIDATION,
            'ReportingAgent': AgentPriority.REPORTING
        }
        
        def get_priority(agent: 'AgentConfig') -> int:
            return priority_map.get(agent.type, AgentPriority.REPORTING).value
        
        return sorted(agents, key=get_priority)
    
    async def _execute_sequential(
        self,
        agents: List['AgentConfig'],
        execution: WorkflowExecution
    ) -> WorkflowResult:
        """Execute agents one after another"""
        results = []
        
        for agent_config in agents:
            # Create agent instance
            agent = await self._create_agent(agent_config, execution.context)
            
            # Notify agent start
            await self.websocket.send_event(
                execution.context.user_id,
                "agent_started",
                {"agent": agent_config.type, "workflow_id": execution.workflow_id}
            )
            
            # Execute agent
            try:
                result = await agent.execute(execution.context)
                results.append(result)
                
                # Update context with result for next agent
                execution.context.previous_results.append(result)
                
                # Notify completion
                await self.websocket.send_event(
                    execution.context.user_id,
                    "agent_completed",
                    {"agent": agent_config.type, "result": result.summary}
                )
                
            except Exception as e:
                # Handle failure based on policy
                if execution.workflow.retry_policy:
                    result = await self._retry_agent(agent, execution)
                    if result:
                        results.append(result)
                        continue
                
                # Notify failure and potentially continue
                await self.websocket.send_event(
                    execution.context.user_id,
                    "agent_failed",
                    {"agent": agent_config.type, "error": str(e)}
                )
                
                if agent_config.required:
                    raise  # Fail workflow if required agent fails
        
        return WorkflowResult(results=results, status="completed")
    
    async def _execute_parallel(
        self,
        agents: List['AgentConfig'],
        execution: WorkflowExecution
    ) -> WorkflowResult:
        """Execute independent agents in parallel"""
        # Group by priority for staged parallel execution
        priority_groups = {}
        for agent in agents:
            priority = self._get_priority(agent)
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(agent)
        
        all_results = []
        
        # Execute each priority group in parallel
        for priority in sorted(priority_groups.keys()):
            group = priority_groups[priority]
            tasks = [
                self._execute_single_agent(agent, execution)
                for agent in group
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results and exceptions
            for agent, result in zip(group, results):
                if isinstance(result, Exception):
                    if agent.required:
                        raise result
                    # Log and continue for optional agents
                else:
                    all_results.append(result)
                    execution.context.previous_results.append(result)
        
        return WorkflowResult(results=all_results, status="completed")
```

#### Phase 3: Integration Testing (6 hours)
```python
# tests/integration/test_supervisor_completion.py

class TestSupervisorCompletion:
    async def test_execution_order_enforced(self):
        """Verify data agents run before optimization"""
        pass
    
    async def test_websocket_events_complete(self):
        """All required events are sent"""
        pass
    
    async def test_parallel_execution(self):
        """Parallel groups execute correctly"""
        pass
    
    async def test_failure_recovery(self):
        """Retry policies work"""
        pass
```

### SUCCESS CRITERIA
- [ ] Complete supervisor implementation
- [ ] Correct execution order enforced
- [ ] All WebSocket events sent
- [ ] Support for 3 coordination strategies
- [ ] < 2s workflow initialization
- [ ] Comprehensive error handling

---

## 🔵 AGENT 4: Legacy Code Elimination Specialist

### YOUR MISSION
Safely identify and delete ALL legacy code, backup files, and duplicates. This is a surgical operation requiring precision.

### YOUR SPECIFIC TASKS

#### Phase 1: Comprehensive Legacy Scan (3 hours)
```bash
# scripts/comprehensive_legacy_scan.py

import os
import re
from pathlib import Path

def scan_for_legacy():
    legacy_patterns = [
        r'.*_legacy\.py$',
        r'.*_old\.py$',
        r'.*_backup\.py$',
        r'.*_deprecated\.py$',
        r'.*\.bak$',
        r'__consolidation_backup__\.py',
        r'.*_temp\.py$',
        r'.*_test\.py$',  # Loose test files outside test dirs
    ]
    
    comment_patterns = [
        r'#\s*TODO:?\s*delete',
        r'#\s*DEPRECATED',
        r'#\s*LEGACY',
        r'#\s*OLD CODE',
    ]
    
    results = {
        'files_to_delete': [],
        'files_with_legacy_comments': [],
        'duplicate_implementations': [],
        'unused_imports': []
    }
    
    # Scan all Python files
    for py_file in Path('netra_backend').rglob('*.py'):
        # Check filename patterns
        for pattern in legacy_patterns:
            if re.match(pattern, py_file.name):
                results['files_to_delete'].append(str(py_file))
                
        # Check file contents
        content = py_file.read_text()
        for pattern in comment_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                results['files_with_legacy_comments'].append(str(py_file))
    
    # Save comprehensive report
    save_report('reports/legacy_scan_20250904.md', results)
    return results
```

#### Phase 2: Dependency Verification (4 hours)
```python
# scripts/verify_safe_deletion.py

def verify_safe_to_delete(file_list):
    """Verify files are safe to delete"""
    
    for file in file_list:
        module_name = Path(file).stem
        
        # Search for imports
        import_patterns = [
            f'from .* import.*{module_name}',
            f'import.*{module_name}',
            f'from.*{module_name} import'
        ]
        
        found_imports = []
        for pattern in import_patterns:
            cmd = f'grep -r "{pattern}" --include="*.py" netra_backend'
            result = subprocess.run(cmd, shell=True, capture_output=True)
            if result.stdout:
                found_imports.append(result.stdout.decode())
        
        if found_imports:
            print(f"WARNING: {file} still has imports:")
            for imp in found_imports:
                print(f"  {imp}")
            
            # Ask for confirmation or skip
            if not confirm_deletion(file, found_imports):
                skip_files.append(file)
    
    return [f for f in file_list if f not in skip_files]
```

#### Phase 3: Staged Deletion (8 hours)
```bash
# Stage 1: Delete obvious legacy files
rm -f netra_backend/**/*_backup.py
rm -f netra_backend/**/*_old.py
rm -f netra_backend/**/*_deprecated.py
rm -f netra_backend/**/*.bak

# Stage 2: Delete test legacy
rm -rf tests/legacy/
rm -rf tests/old/
rm -rf tests/temp/

# Stage 3: Delete identified duplicates
python scripts/delete_duplicates.py --verify --confirm

# Stage 4: Clean up imports
python scripts/cleanup_imports.py --fix --verify

# Stage 5: Remove commented code
python scripts/remove_commented_code.py --aggressive --verify
```

#### Phase 4: Final Validation (3 hours)
```bash
# Run all tests to ensure nothing broke
python tests/unified_test_runner.py --real-services --all

# Check for broken imports
python scripts/check_imports.py --strict

# Verify no orphaned files
python scripts/find_orphaned_files.py

# Generate final report
python scripts/generate_cleanup_report.py
```

### SUCCESS CRITERIA
- [ ] 100+ files deleted
- [ ] Zero broken imports
- [ ] All tests passing
- [ ] 50% codebase reduction
- [ ] No functional regression

---

## 🟢 AGENT 5: Test Infrastructure Modernizer

### YOUR MISSION
Create a unified test framework that replaces all duplicate test infrastructure, standardizes patterns, and enables fast, reliable testing.

### YOUR SPECIFIC TASKS

#### Phase 1: Test Infrastructure Audit (3 hours)
```python
# Document all test patterns found:
"""
Current test infrastructure:
- tests/unified_test_runner.py (keep as base)
- Multiple fixture factories
- Duplicate assertion helpers
- Various mock patterns (DELETE ALL)
- Different setup/teardown approaches
"""
```

#### Phase 2: Unified Test Framework (8 hours)
```python
# tests/framework/unified_test_framework.py

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import pytest
import asyncio

@dataclass
class TestConfig:
    """Unified test configuration"""
    use_real_services: bool = True
    services: List[str] = None
    fixtures: List[str] = None
    performance_tracking: bool = True
    parallel_execution: bool = False
    timeout: int = 30

class UnifiedTestFramework:
    """
    SSOT for ALL test infrastructure.
    NO MOCKS ALLOWED - only real services.
    """
    
    def __init__(self, config: TestConfig = None):
        self.config = config or TestConfig()
        self.docker_manager = UnifiedDockerManager()
        self.fixture_factory = UnifiedFixtureFactory()
        self.assertions = UnifiedAssertions()
        self.performance = PerformanceTracker()
        
    async def setup_environment(self) -> 'TestContext':
        """Setup complete test environment"""
        context = TestContext()
        
        # Start Docker services if needed
        if self.config.use_real_services:
            await self.docker_manager.start_services(
                services=self.config.services or ['all'],
                alpine=True  # Use Alpine for speed
            )
            await self.docker_manager.wait_healthy(timeout=30)
            context.services = self.docker_manager.get_service_urls()
        
        # Create fixtures
        if self.config.fixtures:
            context.fixtures = await self.fixture_factory.create_fixtures(
                self.config.fixtures
            )
        
        # Start performance tracking
        if self.config.performance_tracking:
            self.performance.start()
            context.performance = self.performance
        
        return context
    
    async def teardown_environment(self, context: 'TestContext'):
        """Clean up test environment"""
        # Stop performance tracking
        if context.performance:
            report = context.performance.stop()
            if report.has_regression:
                raise PerformanceRegression(report)
        
        # Cleanup fixtures
        if context.fixtures:
            await self.fixture_factory.cleanup_fixtures(context.fixtures)
        
        # Stop Docker if we started it
        if self.config.use_real_services:
            await self.docker_manager.stop_services()

class UnifiedFixtureFactory:
    """SSOT for all test fixtures"""
    
    async def create_fixtures(self, fixture_names: List[str]) -> Dict[str, Any]:
        """Create requested fixtures"""
        fixtures = {}
        
        for name in fixture_names:
            if name == "test_user":
                fixtures[name] = await self._create_test_user()
            elif name == "test_agent_context":
                fixtures[name] = await self._create_agent_context()
            elif name == "test_workflow":
                fixtures[name] = await self._create_workflow()
            # Add more fixtures as needed
            
        return fixtures
    
    async def _create_test_user(self):
        """Create test user with proper isolation"""
        return {
            "user_id": f"test_user_{uuid.uuid4()}",
            "email": f"test_{uuid.uuid4()}@example.com",
            "permissions": ["test"]
        }

class UnifiedAssertions:
    """SSOT for all custom assertions"""
    
    def assert_websocket_events(self, events: List[Dict], expected: List[str]):
        """Verify WebSocket events were sent"""
        event_types = [e.get('type') for e in events]
        assert all(exp in event_types for exp in expected), \
            f"Missing events: {set(expected) - set(event_types)}"
    
    def assert_performance(self, metrics: Dict, thresholds: Dict):
        """Verify performance metrics"""
        for metric, threshold in thresholds.items():
            assert metrics[metric] <= threshold, \
                f"{metric} exceeded threshold: {metrics[metric]} > {threshold}"
    
    def assert_no_memory_leak(self, before: int, after: int, tolerance: float = 0.1):
        """Verify no memory leak occurred"""
        increase = (after - before) / before
        assert increase <= tolerance, \
            f"Memory increased by {increase:.2%} (tolerance: {tolerance:.2%})"
```

#### Phase 3: Test Migration (6 hours)
```python
# Migrate existing tests to use unified framework

# Example migration:
# BEFORE:
class TestOldPattern:
    def setup_method(self):
        self.db = setup_test_db()
        self.client = create_test_client()
    
    def test_something(self):
        # test code
        pass

# AFTER:
@pytest.mark.asyncio
class TestNewPattern:
    async def test_something(self, unified_test_framework):
        context = await unified_test_framework.setup_environment()
        
        # test code using context.services, context.fixtures
        
        await unified_test_framework.teardown_environment(context)
```

### SUCCESS CRITERIA
- [ ] Single unified test framework
- [ ] All tests migrated
- [ ] 30% faster test execution
- [ ] Zero flaky tests
- [ ] No mocks in codebase
- [ ] Performance regression detection

---

## 🚀 EXECUTION INSTRUCTIONS

### Launch All Agents Simultaneously
```bash
# Save each agent prompt to a separate file
echo "Agent 1 prompt..." > prompts/agent1_data_consolidation.md
echo "Agent 2 prompt..." > prompts/agent2_registry_unification.md
echo "Agent 3 prompt..." > prompts/agent3_supervisor_completion.md
echo "Agent 4 prompt..." > prompts/agent4_legacy_elimination.md
echo "Agent 5 prompt..." > prompts/agent5_test_modernization.md

# Launch all agents in parallel
python scripts/launch_parallel_agents.py \
  --prompts prompts/ \
  --timeout 24h \
  --monitoring enabled \
  --rollback-ready true
```

### Monitoring Dashboard
```python
# scripts/monitor_parallel_refactoring.py

class RefactoringDashboard:
    def display_status(self):
        print("="*50)
        print("PARALLEL SSOT REFACTORING STATUS")
        print("="*50)
        
        agents = [
            ("Data Consolidation", self.get_agent_progress(1)),
            ("Registry Unification", self.get_agent_progress(2)),
            ("Supervisor Completion", self.get_agent_progress(3)),
            ("Legacy Elimination", self.get_agent_progress(4)),
            ("Test Modernization", self.get_agent_progress(5))
        ]
        
        for name, progress in agents:
            bar = "█" * int(progress/5) + "░" * (20 - int(progress/5))
            print(f"{name:25} [{bar}] {progress}%")
        
        print("\nMetrics:")
        print(f"Files Deleted: {self.files_deleted}")
        print(f"Lines Removed: {self.lines_removed:,}")
        print(f"Tests Passing: {self.tests_passing}/{self.total_tests}")
        print(f"Memory Saved: {self.memory_saved_mb}MB")
```

---

## ✅ FINAL VALIDATION

After all agents complete:

```bash
# Run comprehensive validation
python scripts/validate_ssot_refactoring.py \
  --check duplicates \
  --check imports \
  --check tests \
  --check performance \
  --generate-report

# If all checks pass, create completion commit
git add -A
git commit -m "feat: Complete SSOT refactoring - 60% codebase reduction

- Consolidated 30+ data agent files to UnifiedDataAgent
- Unified all registries to UniversalRegistry pattern  
- Completed supervisor orchestration implementation
- Eliminated 100+ legacy files
- Modernized test infrastructure

BREAKING CHANGE: All imports updated to use new SSOT implementations"
```

---

**REMEMBER:** Each agent works independently. No blocking dependencies. Execute with precision. ULTRA THINK DEEPLY on every decision. Our platform's future depends on this refactoring succeeding.