# Team F: Implementation Agent - Data Helper Fallback Integration

## COPY THIS ENTIRE PROMPT:

You are implementing automatic data_helper fallback when ReportingSubAgent encounters insufficient data, ensuring seamless recovery.

CRITICAL: This integration must work with the existing DataHelperAgent and recent SSOT consolidations.

## MANDATORY FIRST ACTIONS:

1. READ `netra_backend/app/agents/data_helper_agent.py` - Current DataHelperAgent
2. READ `netra_backend/app/agents/supervisor/workflow_orchestrator.py` - Workflow logic
3. READ `reporting_crash_audit_and_plan.md` - Fallback requirements
4. READ `AGENT_EXECUTION_ORDER_REASONING.md` - Correct execution order
5. VERIFY these unified agents exist and understand their interfaces:
   - `netra_backend/app/agents/triage/unified_triage_agent.py`
   - `netra_backend/app/agents/data/unified_data_agent.py`
6. READ `SPEC/learnings/agent_execution_order_fix_20250904.xml` - Execution order
7. CHECK `netra_backend/app/services/agent_websocket_bridge.py` - WebSocket integration

## CRITICAL CONTEXT:

**Correct Agent Execution Order:**
1. Triage → 2. Data → 3. Optimization → 4. Actions → 5. Reporting

**When Reporting fails due to missing data:**
- Must trigger DataHelperAgent
- Must NOT restart entire workflow
- Must provide partial results + data request

## YOUR FALLBACK IMPLEMENTATION TASK:

### 1. Fallback Coordinator Implementation

```python
# Location: netra_backend/app/agents/reporting_fallback_coordinator.py

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import asyncio

from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class FallbackContext:
    """Context for data helper fallback"""
    missing_fields: List[str]
    available_data: Dict[str, Any]
    original_request: str
    run_id: str
    user_id: str
    reason: str


class DataHelperFallbackCoordinator:
    """Coordinates automatic fallback to DataHelperAgent
    
    SSOT compliant coordinator that:
    - Detects missing data conditions
    - Triggers DataHelperAgent automatically
    - Integrates results back into reporting
    - Maintains workflow continuity
    """
    
    # Fields required for each report level
    LEVEL_REQUIREMENTS = {
        'FULL': ['action_plan_result', 'optimizations_result', 'data_result', 'triage_result'],
        'STANDARD': ['optimizations_result', 'data_result', 'triage_result'],
        'BASIC': ['data_result', 'triage_result'],
        'MINIMAL': ['triage_result']
    }
    
    def __init__(self, context: UserExecutionContext):
        """Initialize with user context
        
        Args:
            context: User execution context for isolation
        """
        self.context = context
        self.agent_registry = None  # Lazy init
        self.data_helper_agent = None  # Lazy init
        
    async def _get_data_helper_agent(self) -> DataHelperAgent:
        """Get or create DataHelperAgent instance"""
        if not self.data_helper_agent:
            # Try to get from registry first (SSOT)
            if not self.agent_registry:
                self.agent_registry = AgentRegistry()
            
            # Create with proper context
            from netra_backend.app.llm.llm_manager import get_llm_manager
            from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            
            llm_manager = await get_llm_manager()
            tool_dispatcher = ToolDispatcher(llm_manager, self.context)
            
            self.data_helper_agent = DataHelperAgent(
                llm_manager=llm_manager,
                tool_dispatcher=tool_dispatcher,
                context=self.context
            )
            
        return self.data_helper_agent
    
    def should_trigger_fallback(self, metadata: Dict[str, Any]) -> bool:
        """Determine if fallback to data_helper is needed
        
        Args:
            metadata: Current context metadata
            
        Returns:
            bool: True if fallback should be triggered
        """
        # Check if we have minimum data for any report level
        for level, required_fields in self.LEVEL_REQUIREMENTS.items():
            if all(metadata.get(field) for field in required_fields):
                # We have enough data for at least this level
                return False
        
        # We don't have enough data for even MINIMAL report
        logger.info(f"Insufficient data detected for run {self.context.run_id}, fallback needed")
        return True
    
    def identify_missing_data(self, metadata: Dict[str, Any]) -> List[str]:
        """Identify what data is missing for a full report
        
        Args:
            metadata: Current context metadata
            
        Returns:
            List of missing field names
        """
        missing = []
        for field in self.LEVEL_REQUIREMENTS['FULL']:
            if not metadata.get(field):
                missing.append(field)
        
        logger.info(f"Missing data fields: {missing}")
        return missing
    
    def determine_achievable_level(self, metadata: Dict[str, Any]) -> str:
        """Determine highest achievable report level with current data
        
        Args:
            metadata: Current context metadata
            
        Returns:
            Highest achievable level name
        """
        for level, required_fields in self.LEVEL_REQUIREMENTS.items():
            if all(metadata.get(field) for field in required_fields):
                return level
        
        return 'FALLBACK'
    
    async def prepare_fallback_context(self, metadata: Dict[str, Any]) -> FallbackContext:
        """Prepare context for data_helper invocation
        
        Args:
            metadata: Current context metadata
            
        Returns:
            FallbackContext ready for data_helper
        """
        missing_fields = self.identify_missing_data(metadata)
        available_data = {
            field: value 
            for field, value in metadata.items() 
            if field in self.LEVEL_REQUIREMENTS['FULL'] and value
        }
        
        return FallbackContext(
            missing_fields=missing_fields,
            available_data=available_data,
            original_request=metadata.get('user_request', ''),
            run_id=self.context.run_id,
            user_id=self.context.user_id,
            reason=f"Missing {len(missing_fields)} required fields for complete report"
        )
    
    async def trigger_data_helper(self, fallback_context: FallbackContext) -> Dict[str, Any]:
        """Execute DataHelperAgent for missing data collection
        
        Args:
            fallback_context: Prepared fallback context
            
        Returns:
            Data request result from DataHelperAgent
        """
        logger.info(f"Triggering DataHelperAgent for {len(fallback_context.missing_fields)} missing fields")
        
        try:
            # Get data helper agent
            data_helper = await self._get_data_helper_agent()
            
            # Prepare state for data helper
            from netra_backend.app.agents.state import DeepAgentState
            state = DeepAgentState()
            state.user_request = fallback_context.original_request
            state.context_tracking = {
                'missing_fields': fallback_context.missing_fields,
                'available_data': list(fallback_context.available_data.keys()),
                'report_fallback': True
            }
            
            # Add existing results to state
            if fallback_context.available_data:
                state.triage_result = fallback_context.available_data.get('triage_result', {})
                
            # Execute data helper
            await data_helper.execute(state, fallback_context.run_id, stream_updates=True)
            
            # Extract result
            data_request = state.context_tracking.get('data_helper_result', {})
            
            return {
                'success': True,
                'data_request': data_request.get('data_request', {}),
                'user_instructions': data_request.get('user_instructions', ''),
                'structured_items': data_request.get('structured_items', []),
                'missing_fields': fallback_context.missing_fields
            }
            
        except Exception as e:
            logger.error(f"Failed to trigger DataHelperAgent: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_message': self._create_fallback_message(fallback_context)
            }
    
    def _create_fallback_message(self, context: FallbackContext) -> str:
        """Create user-friendly message when data_helper also fails"""
        
        missing_str = ', '.join(context.missing_fields)
        return (
            f"To provide a comprehensive analysis, I need additional information:\n\n"
            f"Missing data categories: {missing_str}\n\n"
            f"Please provide:\n"
            f"1. Any relevant metrics or performance data\n"
            f"2. Current system configuration details\n"
            f"3. Historical trends or baselines\n"
            f"4. Specific goals or constraints\n\n"
            f"With this information, I can deliver actionable optimization recommendations."
        )
    
    async def create_data_collection_report(self, 
                                           data_request: Dict[str, Any],
                                           available_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a report that includes data collection request
        
        Args:
            data_request: Result from DataHelperAgent
            available_data: Currently available data
            
        Returns:
            Report combining partial results and data request
        """
        report = {
            'type': 'data_collection_needed',
            'status': 'partial_analysis',
            'sections': {}
        }
        
        # Add available data sections
        if 'triage_result' in available_data:
            report['sections']['current_classification'] = {
                'title': 'Request Classification',
                'content': available_data['triage_result']
            }
        
        if 'data_result' in available_data:
            report['sections']['available_data'] = {
                'title': 'Available Data Analysis',
                'content': available_data['data_result']
            }
        
        # Add data request section
        report['sections']['data_request'] = {
            'title': 'Additional Information Needed',
            'content': {
                'instructions': data_request.get('user_instructions', ''),
                'structured_items': data_request.get('structured_items', []),
                'reason': 'Complete data required for optimization recommendations'
            }
        }
        
        # Add next steps
        report['sections']['next_steps'] = {
            'title': 'Next Steps',
            'content': [
                'Provide the requested information',
                'System will generate comprehensive analysis',
                'Receive actionable optimization recommendations'
            ]
        }
        
        return report


class FallbackFactory:
    """Factory for creating fallback coordinators"""
    
    @staticmethod
    def create_for_context(context: UserExecutionContext) -> DataHelperFallbackCoordinator:
        """Create fallback coordinator for context
        
        Args:
            context: User execution context
            
        Returns:
            Configured fallback coordinator
        """
        return DataHelperFallbackCoordinator(context)
```

### 2. Integration with ReportingSubAgent

```python
# MODIFY ReportingSubAgent to include fallback:

from netra_backend.app.agents.reporting_fallback_coordinator import FallbackFactory

class ReportingSubAgent(BaseAgent):
    
    def __init__(self, context: Optional[UserExecutionContext] = None):
        # Existing init...
        
        # ADD: Fallback coordinator
        self._fallback_coordinator = None
        
    def _get_fallback_coordinator(self) -> DataHelperFallbackCoordinator:
        """Get or create fallback coordinator"""
        if not self._fallback_coordinator and self._user_context:
            self._fallback_coordinator = FallbackFactory.create_for_context(
                self._user_context
            )
        return self._fallback_coordinator
    
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with automatic data_helper fallback"""
        
        # Check if fallback is needed upfront
        fallback_coord = self._get_fallback_coordinator()
        if fallback_coord and fallback_coord.should_trigger_fallback(context.metadata):
            return await self._execute_with_data_helper_fallback(context, stream_updates)
        
        # Normal execution
        return await self._execute_normal(context, stream_updates)
    
    async def _execute_with_data_helper_fallback(self, context: UserExecutionContext,
                                                stream_updates: bool) -> Dict[str, Any]:
        """Execute with data_helper fallback for missing data"""
        
        fallback_coord = self._get_fallback_coordinator()
        
        if stream_updates:
            await self.emit_agent_started("Analyzing available data...")
            await self.emit_thinking("Insufficient data detected, preparing data collection request...")
        
        # Prepare fallback context
        fallback_context = await fallback_coord.prepare_fallback_context(context.metadata)
        
        # Trigger data helper
        if stream_updates:
            await self.emit_tool_executing("data_helper", {
                "missing_fields": fallback_context.missing_fields
            })
        
        data_request_result = await fallback_coord.trigger_data_helper(fallback_context)
        
        if stream_updates:
            await self.emit_tool_completed("data_helper", {
                "success": data_request_result['success']
            })
        
        # Create combined report
        report = await fallback_coord.create_data_collection_report(
            data_request_result,
            fallback_context.available_data
        )
        
        result = {
            'success': True,
            'level': 'DATA_COLLECTION',
            'report': report,
            'data_helper_triggered': True,
            'missing_data': fallback_context.missing_fields,
            'data_request': data_request_result.get('data_request', {}),
            'next_action': 'provide_requested_data'
        }
        
        if stream_updates:
            await self.emit_agent_completed(result)
        
        return result
```

### 3. Workflow Orchestrator Integration

```python
# MODIFY workflow_orchestrator.py:

class WorkflowOrchestrator:
    
    async def handle_reporting_failure(self, error: Exception, 
                                      context: ExecutionContext) -> ExecutionResult:
        """Handle reporting failures with adaptive response"""
        
        # Check if it's a missing data error
        if 'missing' in str(error).lower() or 'insufficient' in str(error).lower():
            logger.info("Reporting failed due to missing data, triggering data_helper")
            
            # Create data_helper step
            data_helper_step = self._create_pipeline_step(
                'data_helper',
                'fallback_data_request',
                99,  # High priority
                dependencies=[]
            )
            
            # Execute data_helper
            result = await self._execute_workflow_step(context, data_helper_step)
            
            # Create partial report with data request
            reporting_result = ExecutionResult(
                success=True,
                agent_name='reporting',
                result={
                    'report_type': 'data_collection_needed',
                    'data_request': result.result,
                    'partial_results': self._extract_available_results(context.state)
                },
                execution_time_ms=100,
                status=ExecutionStatus.PARTIAL
            )
            
            return reporting_result
        
        # Other error types
        return await self._handle_generic_error(error, context)
    
    def _extract_available_results(self, state: DeepAgentState) -> Dict[str, Any]:
        """Extract any available results from state"""
        available = {}
        
        for field in ['triage_result', 'data_result', 'optimizations_result', 'action_plan_result']:
            value = getattr(state, field, None)
            if value:
                available[field] = value
        
        return available
```

### 4. End-to-End Flow Test

```python
# Location: tests/mission_critical/test_data_helper_fallback.py

@pytest.mark.critical
async def test_automatic_fallback_flow():
    """Test complete flow from reporting failure to data_helper"""
    
    # Create context with insufficient data
    context = create_test_context(
        metadata={'triage_result': {'category': 'optimization'}}
        # Missing: data_result, optimizations_result, action_plan_result
    )
    
    # Execute reporting
    agent = ReportingSubAgent(context)
    result = await agent.execute(context, stream_updates=True)
    
    # Verify fallback triggered
    assert result['success'] == True
    assert result['data_helper_triggered'] == True
    assert result['level'] == 'DATA_COLLECTION'
    
    # Verify data request generated
    assert 'data_request' in result
    assert 'missing_data' in result
    assert len(result['missing_data']) == 3  # Missing 3 fields
    
    # Verify report contains request
    report = result['report']
    assert report['type'] == 'data_collection_needed'
    assert 'data_request' in report['sections']
    assert 'next_steps' in report['sections']
```

## DELIVERABLES:

1. **reporting_fallback_coordinator.py** - Complete fallback implementation
2. **fallback_integration_updates.py** - ReportingSubAgent modifications
3. **workflow_fallback_handler.py** - Workflow orchestrator updates  
4. **test_fallback_flow.py** - End-to-end tests

## VALIDATION CHECKLIST:

- [ ] Detects missing data conditions
- [ ] Triggers DataHelperAgent automatically
- [ ] No workflow restart (continues from reporting)
- [ ] Generates partial report with data request
- [ ] Maintains user context isolation
- [ ] Uses factory pattern
- [ ] Integrates with unified systems
- [ ] WebSocket events maintained
- [ ] Performance < 500ms to trigger
- [ ] Graceful handling if data_helper also fails
- [ ] Test with real services

Remember: The fallback must be AUTOMATIC and SEAMLESS, providing users with actionable output even when data is insufficient.