# Multi-Agent Team: UVS Supervisor Orchestration v3

## 📚 CRITICAL: Required Reading Before Starting

### Primary Source of Truth
**MUST READ FIRST**: [`../../UVS_REQUIREMENTS.md`](../../UVS_REQUIREMENTS.md) - This is the authoritative specification for UVS implementation.

### Coordination with Other Teams
**If any confusion or conflicts arise**, read the other agent team prompts in this directory:
- `01_action_plan_enhancement_prompt.md` - ActionPlanBuilder enhancements
- `02_reporting_resilience_prompt.md` - ReportingSubAgent enhancements

These prompts work together - understanding all three ensures consistent implementation.

## Team Mission
Simplify the SupervisorAgent to implement the UVS principle that ONLY Triage and Reporting agents are required, with dynamic workflow orchestration based on data availability.

## Team Composition & Roles

### 1. Principal Engineer (Coordinator)
- **Role**: System architecture and orchestration design
- **Responsibilities**:
  - Redesign supervisor flow for 2-agent minimum
  - Implement dynamic workflow routing
  - Ensure backward compatibility
  - Maintain WebSocket event flow

### 2. Product Manager Agent  
- **Role**: Business flow optimization
- **Responsibilities**:
  - Map user journeys through simplified flow
  - Define success metrics for each path
  - Validate "Ship for Value" principle
  - Ensure minimal latency for users

### 3. Implementation Agent
- **Role**: Execute supervisor simplification
- **Responsibilities**:
  - Modify agent dependency graph
  - Implement dynamic execution order
  - Add data sufficiency detection
  - Preserve existing integrations

### 4. QA/Security Agent
- **Role**: Flow validation and testing
- **Responsibilities**:
  - Test all workflow permutations
  - Verify graceful degradation
  - Load test simplified flow
  - Ensure no feature regression

## Core UVS Architecture Change

### Before (Complex, Rigid)
```python
# OLD: All agents required, fixed order
REQUIRED_AGENTS = ["triage", "data", "optimization", "actions", "reporting"]
EXECUTION_ORDER = ["triage", "data", "optimization", "actions", "reporting"]
```

### After (Simple, Dynamic)
```python
# NEW: Only 2 required, dynamic order
REQUIRED_AGENTS = ["triage", "reporting"]  
OPTIONAL_AGENTS = ["data_helper", "data", "optimization", "actions"]

def get_execution_order(triage_result):
    if has_sufficient_data(triage_result):
        return ["data", "optimization", "actions", "reporting"]
    else:
        return ["data_helper", "reporting"]  # Default flow
```

## Implementation Requirements

### 1. Supervisor Agent Refactoring

```python
class SupervisorAgent:
    """Simplified orchestrator with UVS principles"""
    
    def __init__(self, context: UserExecutionContext):
        self.context = context
        self.registry = AgentRegistry()
        # Only 2 agents are truly required
        self.required_agents = ["triage", "reporting"]
        self.optional_agents = ["data_helper", "data", "optimization", "actions"]
    
    async def execute(self) -> Dict[str, Any]:
        """Execute with dynamic workflow based on data availability"""
        
        results = {}
        
        # Step 1: Always run triage (but can fail gracefully)
        try:
            triage_result = await self._execute_triage()
            results['triage'] = triage_result
            
            # Step 2: Determine workflow based on triage
            workflow = self._determine_workflow(triage_result)
            
        except Exception as e:
            logger.warning(f"Triage failed, using default flow: {e}")
            # Triage failed - use minimal flow
            workflow = ["data_helper", "reporting"]
            results['triage'] = {'status': 'failed', 'error': str(e)}
        
        # Step 3: Execute determined workflow
        for agent_name in workflow:
            try:
                if agent_name == "reporting":
                    # Reporting gets ALL previous results
                    results['reporting'] = await self._execute_reporting(results)
                else:
                    results[agent_name] = await self._execute_agent(agent_name, results)
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {e}")
                results[agent_name] = {'status': 'failed', 'error': str(e)}
                
                # Only reporting is critical - it must succeed
                if agent_name == "reporting":
                    results['reporting'] = await self._fallback_reporting(results)
        
        return results
    
    def _determine_workflow(self, triage_result: Dict) -> List[str]:
        """Dynamically determine workflow based on triage analysis"""
        
        if not triage_result or triage_result.get('status') == 'failed':
            # No triage or failed - minimal flow
            return ["data_helper", "reporting"]
        
        data_sufficiency = triage_result.get('data_sufficiency', 'none')
        user_intent = triage_result.get('user_intent', {})
        
        if data_sufficiency == 'sufficient':
            # Full flow - we have data to work with
            workflow = []
            
            if user_intent.get('needs_data_analysis', True):
                workflow.append("data")
            
            if user_intent.get('needs_optimization', True):
                workflow.append("optimization")
            
            if user_intent.get('needs_action_plan', True):
                workflow.append("actions")
            
            workflow.append("reporting")  # Always end with reporting
            return workflow
            
        elif data_sufficiency == 'partial':
            # Partial flow - work with what we have
            return ["data", "data_helper", "reporting"]
            
        else:
            # No data - guidance flow
            return ["data_helper", "reporting"]
```

### 2. Triage Result Enhancement

```python
class UnifiedTriageAgent:
    """Enhanced to provide workflow hints"""
    
    async def execute(self, context: UserExecutionContext) -> Dict:
        """Analyze request and determine optimal workflow"""
        
        try:
            # Analyze user request
            analysis = await self._analyze_request(context)
            
            return {
                'status': 'success',
                'data_sufficiency': self._assess_data_sufficiency(context),
                'user_intent': {
                    'needs_data_analysis': self._needs_data_analysis(analysis),
                    'needs_optimization': self._needs_optimization(analysis),
                    'needs_action_plan': self._needs_action_plan(analysis)
                },
                'recommended_workflow': self._recommend_workflow(analysis),
                'data_sources_identified': self._identify_data_sources(context),
                'complexity_level': self._assess_complexity(analysis)
            }
            
        except Exception as e:
            # Triage can fail gracefully
            return {
                'status': 'failed',
                'error': str(e),
                'data_sufficiency': 'unknown',
                'recommended_workflow': ['data_helper', 'reporting']
            }
    
    def _assess_data_sufficiency(self, context: UserExecutionContext) -> str:
        """Determine how much data we have to work with"""
        
        has_usage_data = bool(context.metadata.get('usage_data'))
        has_cost_data = bool(context.metadata.get('cost_data'))
        has_performance_data = bool(context.metadata.get('performance_data'))
        
        if has_usage_data and has_cost_data:
            return 'sufficient'
        elif has_usage_data or has_cost_data or has_performance_data:
            return 'partial'
        else:
            return 'none'
```

### 3. Agent Registry Updates

```python
class AgentRegistry:
    """Updated for dynamic agent management"""
    
    def get_agent_dependencies(self) -> Dict[str, Dict]:
        """Define which agents depend on others"""
        return {
            "triage": {
                "depends_on": [],  # Independent
                "required": False,  # Can fail gracefully
                "provides": ["workflow_recommendation", "data_assessment"]
            },
            "reporting": {
                "depends_on": [],  # Can work with nothing (UVS)
                "required": True,  # MUST succeed
                "provides": ["final_report"],
                "consumes_optional": ["triage", "data", "optimization", "actions"]
            },
            "data_helper": {
                "depends_on": [],  # Independent
                "required": False,
                "provides": ["data_collection_guide"]
            },
            "data": {
                "depends_on": ["triage"],  # Needs triage to know what to analyze
                "required": False,
                "provides": ["data_analysis"]
            },
            "optimization": {
                "depends_on": ["data"],  # Needs data to optimize
                "required": False,
                "provides": ["optimization_recommendations"]
            },
            "actions": {
                "depends_on": ["optimization"],  # Needs optimizations for plan
                "required": False,
                "provides": ["action_plan"]
            }
        }
    
    def validate_workflow(self, workflow: List[str]) -> bool:
        """Ensure workflow respects dependencies"""
        
        dependencies = self.get_agent_dependencies()
        executed = set()
        
        for agent in workflow:
            deps = dependencies[agent]["depends_on"]
            for dep in deps:
                if dep not in executed and dep != agent:
                    logger.warning(f"{agent} depends on {dep} which hasn't executed")
                    return False
            executed.add(agent)
        
        # Must end with reporting
        return workflow[-1] == "reporting"
```

### 4. WebSocket Event Management

```python
class WorkflowOrchestrator:
    """Manages WebSocket events for dynamic workflows"""
    
    async def execute_workflow(self, workflow: List[str], context: UserExecutionContext):
        """Execute workflow with proper WebSocket notifications"""
        
        # Notify workflow started
        await self.websocket.send_event('workflow_started', {
            'workflow_type': self._classify_workflow(workflow),
            'agents': workflow,
            'estimated_time': self._estimate_duration(workflow)
        })
        
        for agent_name in workflow:
            # Notify agent starting
            await self.websocket.send_event('agent_started', {
                'agent': agent_name,
                'position': workflow.index(agent_name) + 1,
                'total': len(workflow)
            })
            
            try:
                # Execute agent
                result = await self._execute_agent(agent_name, context)
                
                # Notify completion
                await self.websocket.send_event('agent_completed', {
                    'agent': agent_name,
                    'status': 'success',
                    'has_results': bool(result)
                })
                
            except Exception as e:
                # Notify failure (but continue workflow)
                await self.websocket.send_event('agent_completed', {
                    'agent': agent_name,
                    'status': 'failed',
                    'recoverable': agent_name != 'reporting'
                })
        
        # Workflow complete
        await self.websocket.send_event('workflow_completed', {
            'status': 'success',
            'workflow_type': self._classify_workflow(workflow)
        })
    
    def _classify_workflow(self, workflow: List[str]) -> str:
        """Classify workflow type for user communication"""
        
        if set(workflow) >= {'data', 'optimization', 'actions', 'reporting'}:
            return 'full_analysis'
        elif 'data_helper' in workflow:
            return 'guidance'
        else:
            return 'partial_analysis'
```

## Testing Scenarios

### Scenario 1: Minimal System (Only 2 Agents)
```python
async def test_minimal_system_works():
    """System works with just triage and reporting"""
    
    supervisor = SupervisorAgent(UserExecutionContext())
    
    # Verify only 2 required
    assert len(supervisor.required_agents) == 2
    assert "triage" in supervisor.required_agents
    assert "reporting" in supervisor.required_agents
    
    # Execute with no data
    results = await supervisor.execute()
    
    # Should still get a report
    assert 'reporting' in results
    assert results['reporting']['status'] == 'success'
```

### Scenario 2: Dynamic Workflow Selection
```python
async def test_dynamic_workflow_based_on_data():
    """Workflow adapts to available data"""
    
    # Test with no data
    context_no_data = UserExecutionContext()
    supervisor = SupervisorAgent(context_no_data)
    workflow = supervisor._determine_workflow({'data_sufficiency': 'none'})
    assert workflow == ["data_helper", "reporting"]
    
    # Test with full data
    context_with_data = UserExecutionContext()
    context_with_data.metadata['usage_data'] = [...]
    supervisor = SupervisorAgent(context_with_data)
    workflow = supervisor._determine_workflow({'data_sufficiency': 'sufficient'})
    assert "data" in workflow
    assert "optimization" in workflow
    assert workflow[-1] == "reporting"
```

### Scenario 3: Triage Failure Handling
```python
async def test_triage_failure_still_works():
    """System continues even if triage fails"""
    
    supervisor = SupervisorAgent(UserExecutionContext())
    
    # Mock triage to fail
    with patch.object(supervisor, '_execute_triage', side_effect=Exception("Triage failed")):
        results = await supervisor.execute()
    
    # Should use default flow
    assert 'reporting' in results
    assert results['reporting']['status'] == 'success'
    assert results['triage']['status'] == 'failed'
```

### Scenario 4: Partial Agent Failures
```python
async def test_partial_failures_handled():
    """Some agents fail but reporting still works"""
    
    supervisor = SupervisorAgent(UserExecutionContext())
    
    # Mock data agent to fail
    with patch.object(supervisor, '_execute_agent') as mock:
        def side_effect(agent_name, results):
            if agent_name == "data":
                raise Exception("Data agent failed")
            return {'status': 'success'}
        
        mock.side_effect = side_effect
        results = await supervisor.execute()
    
    assert results['data']['status'] == 'failed'
    assert results['reporting']['status'] == 'success'
```

## Performance Optimizations

```python
class SupervisorAgent:
    """Performance-optimized supervisor"""
    
    def __init__(self, context):
        super().__init__(context)
        # Pre-compile workflow templates
        self._workflow_cache = {
            'full': ["data", "optimization", "actions", "reporting"],
            'partial': ["data", "data_helper", "reporting"],
            'guidance': ["data_helper", "reporting"]
        }
    
    async def execute_parallel_where_possible(self, workflow: List[str]):
        """Execute independent agents in parallel"""
        
        # Identify parallel opportunities
        parallel_groups = self._identify_parallel_groups(workflow)
        
        for group in parallel_groups:
            if len(group) == 1:
                # Sequential execution
                await self._execute_agent(group[0])
            else:
                # Parallel execution
                await asyncio.gather(*[
                    self._execute_agent(agent) for agent in group
                ])
    
    def _identify_parallel_groups(self, workflow: List[str]) -> List[List[str]]:
        """Group agents that can run in parallel"""
        
        # For now, keep it simple - all sequential
        # Future: identify independent agents
        return [[agent] for agent in workflow]
```

## Migration Strategy

### Phase 1: Add Feature Flag (Day 1)
```python
if settings.UVS_SUPERVISOR_ENABLED:
    return SupervisorAgentV2()  # New simplified version
else:
    return SupervisorAgentV1()  # Current version
```

### Phase 2: Test in Staging (Day 2-3)
- Deploy with flag enabled for internal testing
- Monitor all metrics
- Validate all workflows

### Phase 3: Gradual Production Rollout (Day 4-7)
- 10% traffic → 25% → 50% → 100%
- Monitor error rates and latency
- Instant rollback capability

## Success Metrics

### Must Have (Week 1)
✅ System works with only 2 agents  
✅ Dynamic workflow selection works  
✅ Triage failures handled gracefully  
✅ All existing features preserved  
✅ WebSocket events unchanged  
✅ No performance degradation  

### Performance Targets
- Workflow decision: < 50ms
- Agent execution: No change from baseline
- Total request time: Reduced by 20% for no-data cases

## Key Files

### Primary Changes
- `netra_backend/app/agents/supervisor.py` - Main refactoring
- `netra_backend/app/agents/workflow_orchestrator.py` - Workflow logic

### Minor Updates
- `netra_backend/app/agents/registry.py` - Dependency updates
- `netra_backend/app/agents/triage/unified_triage_agent.py` - Workflow hints

### New Files
- `netra_backend/app/agents/workflow_strategies.py` - Workflow templates
- `netra_backend/tests/unit/test_dynamic_workflow.py` - New tests

## Critical Constraints

### MUST Preserve
- All existing API contracts
- WebSocket event structure
- Database schemas
- Authentication flows
- Tool execution patterns

### Can Modify
- Internal agent dependencies
- Execution order logic
- Workflow decision logic
- Error recovery patterns

## Team Coordination

1. **Principal** maps current supervisor implementation
2. **PM** defines optimal user flows
3. **Principal** designs simplified architecture
4. **Implementation** refactors supervisor
5. **QA** tests all workflow permutations
6. **Implementation** adds dynamic routing
7. **QA** validates graceful degradation
8. **Principal** ensures backward compatibility
9. **Full team** monitors staging deployment

## Remember the Goal

We're not rebuilding the system. We're simplifying it to:

1. **Reduce complexity** - Only 2 required agents
2. **Increase reliability** - Graceful degradation
3. **Improve speed** - Skip unnecessary agents
4. **Maintain value** - Always deliver reports

This is about making the supervisor smarter, not bigger. The best code is no code, and the best workflow is the shortest one that delivers value.