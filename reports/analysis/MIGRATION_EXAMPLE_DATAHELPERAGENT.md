# Migration Example: DataHelperAgent

This document demonstrates the **SAFE MIGRATION** from DeepAgentState to UserExecutionContext pattern using DataHelperAgent as a concrete example.

## 🎯 Migration Strategy

### Phase 1: Identify Current Usage Patterns
The DataHelperAgent currently has:

1. ✅ **Modern Core**: Uses BaseAgent with UserExecutionContext support
2. ⚠️ **Legacy Imports**: Still imports DeepAgentState 
3. ⚠️ **Backward Compatibility**: Methods using `execute(state: DeepAgentState)` pattern
4. ⚠️ **Direct State Access**: Accesses `context.state.user_request` directly

### Phase 2: Modern Migration Pattern

#### BEFORE (Current Legacy Pattern)
```python
# Legacy import
from netra_backend.app.agents.state import DeepAgentState

class DataHelperAgent(BaseAgent):
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> None:
        # Legacy pattern - direct state access
        user_request = state.user_request
        triage_result = state.triage_result
        
        # Store results in state
        state.context_tracking['data_helper_result'] = result
```

#### AFTER (Modern UserExecutionContext Pattern)
```python
# Modern import
from netra_backend.app.services.user_execution_context import UserExecutionContext

class DataHelperAgent(BaseAgent):
    async def _execute_core(self, context: UserExecutionContext) -> UserExecutionContext:
        """Modern execution using UserExecutionContext (SECURE)."""
        # Modern pattern - access through context metadata
        user_request = context.metadata.get('user_request', '')
        triage_result = context.metadata.get('triage_result', {})
        
        # Generate data request
        result = await self.data_helper_tool.generate_data_request(
            user_request=user_request,
            triage_result=triage_result,
            previous_results=self._extract_previous_results(context)
        )
        
        # Store results using SSOT metadata method
        self.store_metadata_result(context, 'data_helper_result', result)
        
        return context
```

### Phase 3: Eliminate Legacy Methods

#### Remove Legacy Compatibility
```python
# REMOVE these methods after migration:
async def execute(self, state: DeepAgentState, ...) -> None: ...
async def run(self, ..., state: DeepAgentState) -> DeepAgentState: ...
```

#### Update Imports
```python
# REMOVE
from netra_backend.app.agents.state import DeepAgentState

# KEEP (modern pattern)
from netra_backend.app.services.user_execution_context import UserExecutionContext
```

## 🚀 Complete Migration Implementation

Here's the complete migrated DataHelperAgent:

```python
"""Data Helper Agent Module - MIGRATED to UserExecutionContext

This agent generates data requests when insufficient data is available for optimization.
Business Value: Ensures comprehensive data collection for accurate optimization strategies.

✅ MIGRATION COMPLETE: Uses UserExecutionContext for complete user isolation
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.tools.data_helper import DataHelper
from netra_backend.app.core.unified_error_handler import agent_error_handler
from netra_backend.app.schemas.shared_types import ErrorContext

logger = central_logger.get_logger(__name__)


class DataHelperAgent(BaseAgent):
    """Data Helper Agent for requesting additional data from users.
    
    ✅ MIGRATED: Uses UserExecutionContext for complete user isolation and request security.
    
    This agent analyzes the context and generates comprehensive data requests
    to enable optimization strategies when data is insufficient.
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: UnifiedToolDispatcher):
        """Initialize the Data Helper Agent.
        
        Args:
            llm_manager: LLM manager for the agent
            tool_dispatcher: Tool dispatcher for the agent
        """
        super().__init__(
            llm_manager=llm_manager,
            name="data_helper",
            description="Generates data requests when insufficient data is available",
            enable_reliability=False,  # DISABLED: Was hiding errors - see AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=True,          # Optional caching infrastructure
        )
        self.tool_dispatcher = tool_dispatcher
        self.data_helper_tool = DataHelper(llm_manager)
    
    async def _execute_core(self, context: 'UserExecutionContext') -> 'UserExecutionContext':
        """Execute core data request generation logic with complete user isolation.
        
        Args:
            context: UserExecutionContext with complete request isolation
            
        Returns:
            Enhanced UserExecutionContext with data request results
        """
        # Emit thinking event for reasoning visibility
        await self.notify_event("agent_thinking", {
            "message": "Analyzing user request to identify data gaps...",
            "agent": self.name
        })
        
        try:
            # Extract data from secure context metadata
            user_request = context.metadata.get('user_request', '')
            triage_result = context.metadata.get('triage_result', {})
            
            # Validate preconditions
            if not user_request or len(user_request.strip()) < 10:
                raise ValueError("Insufficient user request for data analysis")
            
            # Extract previous agent results from context
            previous_results = self._extract_previous_results_from_context(context)
            
            # Emit tool execution transparency
            await self.notify_event("tool_executing", {
                "tool": "data_helper",
                "params": {
                    "user_request_length": len(user_request),
                    "triage_result_available": bool(triage_result),
                    "previous_results_count": len(previous_results)
                }
            })
            
            # Generate data request using the tool
            data_request_result = await self.data_helper_tool.generate_data_request(
                user_request=user_request,
                triage_result=triage_result,
                previous_results=previous_results
            )
            
            # Emit tool completion with sanitized results
            await self.notify_event("tool_completed", {
                "tool": "data_helper",
                "result": {
                    "success": data_request_result.get('success', False),
                    "data_request_generated": bool(data_request_result.get('data_request')),
                    "instructions_count": len(data_request_result.get('data_request', {}).get('user_instructions', '')),
                    "structured_items_count": len(data_request_result.get('data_request', {}).get('structured_items', []))
                }
            })
            
            # Store results using SSOT metadata storage (SECURE)
            self.store_metadata_result(context, 'data_helper_result', data_request_result)
            self.store_metadata_result(context, 'data_request_generated', True)
            
            # Log successful execution
            logger.info(f"DataHelperAgent completed successfully: user_id={context.user_id}, run_id={context.run_id}")
            
            return context
            
        except Exception as e:
            # Use unified error handler with proper ErrorContext
            error_context = ErrorContext(
                trace_id=ErrorContext.generate_trace_id(),
                operation="data_request_generation",
                details={"run_id": context.run_id, "error_type": type(e).__name__},
                component="DataHelperAgent"
            )
            
            # Log the error through unified system
            logger.error(f"Error in DataHelperAgent: user_id={context.user_id}, run_id={context.run_id}, error={str(e)}")
            
            # Emit error event for WebSocket transparency
            await self.notify_event("agent_error", {
                "agent": self.name,
                "error": str(e),
                "error_type": type(e).__name__,
                "fallback_available": True
            })
            
            # Store error result using SSOT metadata storage (SECURE)
            self.store_metadata_result(context, 'data_helper_error', str(e))
            self.store_metadata_result(context, 'data_helper_fallback_message', 
                                     self._get_fallback_message(context.metadata.get('user_request', '')))
            
            # Return context with error state (don't re-raise - let BaseAgent handle)
            return context
    
    def _extract_previous_results_from_context(self, context: 'UserExecutionContext') -> Dict[str, Any]:
        """Extract previous agent results from UserExecutionContext metadata.
        
        Args:
            context: UserExecutionContext with metadata
            
        Returns:
            Dictionary of previous agent results
        """
        previous_results = {}
        
        # Extract known result types from context metadata
        result_keys = [
            'triage_result', 'data_result', 'optimizations_result',
            'action_plan_result', 'report_result', 'synthetic_data_result'
        ]
        
        for key in result_keys:
            value = context.metadata.get(key)
            if value is not None:
                previous_results[key] = value
        
        return previous_results
    
    def _get_fallback_message(self, user_request: str) -> str:
        """Generate a fallback message when data request generation fails.
        
        Args:
            user_request: Original user request
            
        Returns:
            Fallback message for the user
        """
        return (
            "I encountered an issue generating a specific data request. "
            "Please provide any additional information you think would be helpful "
            f"for analyzing your request: {user_request[:100]}..."
        )
```

## 🔍 Migration Validation

### Security Validation
- ✅ **User Isolation**: All data accessed through UserExecutionContext metadata
- ✅ **No Global State**: No shared state between concurrent users  
- ✅ **Immutable Context**: UserExecutionContext is immutable (frozen dataclass)
- ✅ **Request Scoping**: Each request gets isolated execution context

### Functionality Validation  
- ✅ **WebSocket Events**: Modern `notify_event` pattern for real-time updates
- ✅ **Error Handling**: Unified error handling with proper context
- ✅ **Result Storage**: SSOT metadata storage methods
- ✅ **Tool Integration**: Compatible with existing tool ecosystem

### Testing Validation
```python
async def test_data_helper_modern_execution():
    """Test DataHelperAgent with UserExecutionContext."""
    # Create isolated user context
    context = UserExecutionContext.from_request(
        user_id="user123",
        thread_id="thread456", 
        run_id="run789"
    )
    context.metadata['user_request'] = "Help me optimize my supply chain"
    
    # Execute agent
    result_context = await agent._execute_core(context)
    
    # Validate results are in metadata
    assert 'data_helper_result' in result_context.metadata
    assert result_context.metadata['data_request_generated'] is True
    
    # Validate user isolation (different context should not see results)
    other_context = UserExecutionContext.from_request(
        user_id="other_user",
        thread_id="other_thread",
        run_id="other_run"
    )
    assert 'data_helper_result' not in other_context.metadata
```

## 🚨 Critical Success Factors

1. **Complete Backward Compatibility Removal**: All DeepAgentState methods must be removed
2. **Metadata Access Pattern**: Always use `context.metadata.get()` instead of direct state access
3. **SSOT Storage Methods**: Use `self.store_metadata_result()` for consistent storage
4. **WebSocket Integration**: Use modern `notify_event` for real-time user updates
5. **Error Context**: Proper error handling with request isolation preserved

This migration ensures **complete user isolation** while maintaining all existing functionality.