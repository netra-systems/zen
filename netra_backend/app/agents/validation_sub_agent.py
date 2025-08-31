"""ValidationSubAgent - Example Sub-Agent with WebSocket Events

Demonstrates the proper pattern for sub-agents to emit WebSocket events
during their execution lifecycle for real-time user interface updates.

Business Value: Quality assurance and validation for AI operations
BVJ: Growth & Enterprise | Quality Assurance | Risk reduction & compliance
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.base.interface import (
    BaseExecutionInterface,
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
    WebSocketManagerProtocol,
)
from netra_backend.app.agents.base.websocket_context import WebSocketContextMixin
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.core.type_validators import agent_type_safe
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.registry import DeepAgentState
from netra_backend.app.schemas.strict_types import TypedAgentResult

logger = central_logger.get_logger(__name__)


class ValidationSubAgent(BaseSubAgent, BaseExecutionInterface, WebSocketContextMixin):
    """Example validation sub-agent with comprehensive WebSocket event emissions.
    
    Demonstrates the complete pattern for sub-agents to provide real-time feedback
    during validation operations including:
    - Agent startup notifications
    - Real-time thinking/reasoning updates
    - Progress updates during validation steps
    - Tool execution notifications
    - Completion status with results
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher,
                 websocket_manager: Optional[WebSocketManagerProtocol] = None):
        """Initialize ValidationSubAgent with WebSocket capabilities."""
        # Initialize base classes
        BaseSubAgent.__init__(self, llm_manager, name="ValidationSubAgent", 
                            description="Comprehensive validation with real-time feedback")
        BaseExecutionInterface.__init__(self, "ValidationSubAgent", websocket_manager)
        WebSocketContextMixin.__init__(self)
        
        # Initialize core components
        self.tool_dispatcher = tool_dispatcher
        self.logger = central_logger.get_logger("ValidationSubAgent")
        
        # Validation configuration
        self.validation_rules = [
            "input_format_check",
            "business_logic_validation", 
            "security_compliance_check",
            "performance_requirements_check",
            "integration_compatibility_check"
        ]
        
        self.logger.info("ValidationSubAgent initialized successfully")
    
    @agent_type_safe
    async def execute(self, state: Optional[DeepAgentState], run_id: str = "", 
                     stream_updates: bool = False) -> TypedAgentResult:
        """Execute validation workflow with comprehensive WebSocket events."""
        start_time = time.time()
        
        try:
            # Set up WebSocket context for legacy execution
            await self._setup_websocket_context_for_legacy(run_id)
            
            # Emit agent started event
            await self.emit_agent_started("Starting comprehensive validation process")
            
            # Validate input state
            if not self._validate_execution_state(state):
                await self.emit_error("Invalid execution state for validation")
                return self._create_error_result("Invalid execution state", start_time)
            
            # Emit initial thinking
            await self.emit_thinking("Analyzing validation requirements and preparing validation suite...")
            
            # Extract validation request
            validation_request = self._extract_validation_request(state)
            
            # Execute validation steps with progress updates
            validation_results = await self._execute_validation_steps(validation_request, run_id)
            
            # Generate validation summary
            await self.emit_progress("Generating validation summary and recommendations...")
            validation_summary = await self._generate_validation_summary(validation_results)
            
            # Prepare final result
            execution_time = (time.time() - start_time) * 1000
            
            result_data = {
                "validation_type": validation_request.get("type", "comprehensive"),
                "execution_time_ms": execution_time,
                "rules_checked": len(self.validation_rules),
                "validation_passed": validation_summary.get("overall_passed", False),
                "issues_found": validation_summary.get("issues_count", 0),
                "recommendations": ", ".join(validation_summary.get("recommendations", []))
            }
            
            # Emit completion event
            await self.emit_agent_completed(result_data, execution_time)
            
            return TypedAgentResult(
                success=True,
                result=result_data,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            await self.emit_error(f"ValidationSubAgent execution failed: {str(e)}")
            self.logger.error(f"ValidationSubAgent execution failed: {str(e)}")
            return self._create_error_result(str(e), start_time)
    
    async def execute_core_logic(self, context: ExecutionContext) -> ExecutionResult:
        """Core execution logic for BaseExecutionInterface with WebSocket events."""
        start_time = time.time()
        
        try:
            # Set up WebSocket context if available
            await self._setup_websocket_context_if_available(context)
            
            # Emit agent started event
            await self.emit_agent_started("Starting validation via BaseExecutionInterface")
            
            # Convert context to state for backward compatibility
            state = self._context_to_state(context)
            
            # Execute main logic
            result = await self.execute(state, context.run_id, context.stream_updates)
            
            # Emit completion
            duration_ms = (time.time() - start_time) * 1000
            await self.emit_agent_completed(result.result if result.success else {}, duration_ms)
            
            return ExecutionResult(
                success=result.success,
                status=ExecutionStatus.COMPLETED if result.success else ExecutionStatus.FAILED,
                result=result.result,
                execution_time_ms=result.execution_time_ms
            )
            
        except Exception as e:
            await self.emit_error(f"Core logic execution failed: {str(e)}")
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.FAILED,
                error=str(e)
            )
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate preconditions for execution."""
        return (
            context.state is not None and
            hasattr(context.state, 'agent_input') and
            context.state.agent_input is not None
        )
    
    def _validate_execution_state(self, state: DeepAgentState) -> bool:
        """Validate execution state has required validation parameters."""
        return (
            state and 
            hasattr(state, 'agent_input') and 
            state.agent_input is not None
        )
    
    def _extract_validation_request(self, state: DeepAgentState) -> Dict[str, Any]:
        """Extract validation request parameters from state."""
        agent_input = state.agent_input
        
        return {
            "type": agent_input.get("validation_type", "comprehensive"),
            "target": agent_input.get("validation_target", "general"),
            "rules": agent_input.get("custom_rules", self.validation_rules),
            "strictness": agent_input.get("strictness_level", "standard"),
            "user_id": getattr(state, 'user_id', None)
        }
    
    async def _execute_validation_steps(self, request: Dict[str, Any], run_id: str) -> List[Dict[str, Any]]:
        """Execute validation steps with progress updates and tool notifications."""
        validation_results = []
        rules = request.get("rules", self.validation_rules)
        
        for i, rule in enumerate(rules):
            # Emit thinking about current validation step
            await self.emit_thinking(f"Executing validation rule: {rule} ({i+1}/{len(rules)})")
            
            # Emit tool execution (simulate validation tool usage)
            await self.emit_tool_executing(f"validation_tool_{rule}")
            
            # Execute validation rule
            rule_result = await self._execute_validation_rule(rule, request)
            validation_results.append(rule_result)
            
            # Emit tool completion
            await self.emit_tool_completed(f"validation_tool_{rule}", rule_result)
            
            # Emit progress update
            await self.emit_progress(f"Completed {rule} validation - {rule_result.get('status', 'unknown')}")
        
        return validation_results
    
    async def _execute_validation_rule(self, rule: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific validation rule."""
        # Simulate validation logic
        start_time = time.time()
        
        # Mock validation results based on rule
        validation_data = {
            "rule": rule,
            "status": "passed" if rule != "security_compliance_check" else "warning",
            "execution_time_ms": (time.time() - start_time) * 1000,
            "details": f"Validation for {rule} completed",
            "issues": [] if rule != "security_compliance_check" else ["Minor security recommendation available"]
        }
        
        # Add some realistic validation delay
        await asyncio.sleep(0.1)
        
        return validation_data
    
    async def _generate_validation_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive validation summary."""
        total_rules = len(results)
        passed_rules = len([r for r in results if r.get("status") == "passed"])
        warning_rules = len([r for r in results if r.get("status") == "warning"])
        failed_rules = len([r for r in results if r.get("status") == "failed"])
        
        all_issues = []
        for result in results:
            all_issues.extend(result.get("issues", []))
        
        recommendations = []
        if warning_rules > 0:
            recommendations.append("Review warning items for optimization opportunities")
        if failed_rules > 0:
            recommendations.append("Address failed validation rules before proceeding")
        if len(all_issues) == 0:
            recommendations.append("All validation checks passed successfully")
        
        return {
            "overall_passed": failed_rules == 0,
            "total_rules": total_rules,
            "passed_rules": passed_rules,
            "warning_rules": warning_rules,
            "failed_rules": failed_rules,
            "issues_count": len(all_issues),
            "issues": all_issues,
            "recommendations": recommendations,
            "validation_score": (passed_rules + warning_rules * 0.5) / total_rules if total_rules > 0 else 0.0
        }
    
    def _create_error_result(self, error_message: str, start_time: float) -> TypedAgentResult:
        """Create standardized error result."""
        execution_time = (time.time() - start_time) * 1000
        
        return TypedAgentResult(
            success=False,
            result={
                "error": error_message,
                "execution_time_ms": execution_time,
                "validation_status": "failed"
            },
            execution_time_ms=execution_time
        )
    
    def _context_to_state(self, context: ExecutionContext) -> DeepAgentState:
        """Convert ExecutionContext to DeepAgentState for backward compatibility."""
        return context.state
    
    # WebSocket context setup methods
    async def _setup_websocket_context_if_available(self, context: ExecutionContext) -> None:
        """Set up WebSocket context if websocket manager is available."""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            # Import here to avoid circular imports
            from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
            from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
            
            try:
                # Create WebSocket notifier and execution context
                notifier = WebSocketNotifier(self.websocket_manager)
                ws_context = AgentExecutionContext(
                    run_id=context.run_id,
                    agent_name="ValidationSubAgent",
                    thread_id=getattr(context.state, 'chat_thread_id', context.run_id),
                    user_id=getattr(context.state, 'user_id', None),
                    start_time=time.time()
                )
                
                # Set WebSocket context in mixin
                self.set_websocket_context(notifier, ws_context)
                
            except Exception as e:
                self.logger.debug(f"Failed to setup WebSocket context: {e}")
    
    async def _setup_websocket_context_for_legacy(self, run_id: str) -> None:
        """Set up WebSocket context for legacy execution paths."""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            # Import here to avoid circular imports
            from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
            from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
            
            try:
                # Create WebSocket notifier and execution context
                notifier = WebSocketNotifier(self.websocket_manager)
                ws_context = AgentExecutionContext(
                    run_id=run_id,
                    agent_name="ValidationSubAgent",
                    thread_id=run_id,  # Use run_id as thread_id for legacy
                    user_id=None,
                    start_time=time.time()
                )
                
                # Set WebSocket context in mixin
                self.set_websocket_context(notifier, ws_context)
                
            except Exception as e:
                self.logger.debug(f"Failed to setup WebSocket context for legacy: {e}")
    
    # Health and status methods
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        return {
            "agent_name": "ValidationSubAgent",
            "status": "healthy",
            "validation_rules_loaded": len(self.validation_rules),
            "websocket_enabled": self.websocket_enabled,
            "components": {
                "validation_engine": "active",
                "websocket_context": "active" if self.websocket_enabled else "inactive"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Import asyncio for sleep function
import asyncio