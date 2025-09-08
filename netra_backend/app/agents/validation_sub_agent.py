"""ValidationSubAgent - Example Sub-Agent with WebSocket Events

Demonstrates the proper pattern for sub-agents to emit WebSocket events
during their execution lifecycle for real-time user interface updates.

Business Value: Quality assurance and validation for AI operations
BVJ: Growth & Enterprise | Quality Assurance | Risk reduction & compliance
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

from netra_backend.app.agents.base_agent import BaseAgent
# WebSocketContextMixin removed - BaseAgent now handles WebSocket via bridge
# Using single inheritance with standardized execution patterns
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.core.type_validators import agent_type_safe
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext, validate_user_context
from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.schemas.shared_types import ValidationResult, NestedJsonDict
from netra_backend.app.schemas.strict_types import TypedAgentResult

logger = central_logger.get_logger(__name__)


class ValidationRequest(TypedDict):
    """Type definition for validation request parameters."""
    type: str
    target: str
    rules: List[str]
    strictness: str
    user_id: Optional[str]


class ValidationRuleResult(TypedDict):
    """Type definition for individual validation rule results."""
    rule: str
    status: str
    execution_time_ms: float
    details: str
    issues: List[str]


class ValidationSummary(TypedDict):
    """Type definition for validation summary."""
    overall_passed: bool
    total_rules: int
    passed_rules: int
    warning_rules: int
    failed_rules: int
    issues_count: int
    issues: List[str]
    recommendations: List[str]
    validation_score: float


class AgentHealthStatus(TypedDict):
    """Type definition for agent health status."""
    agent_name: str
    status: str
    validation_rules_loaded: int
    websocket_enabled: bool
    components: Dict[str, str]
    timestamp: str



class ValidationSubAgent(BaseAgent):
    """Example validation sub-agent with comprehensive WebSocket event emissions.
    
    WebSocket events are handled through BaseAgent's bridge adapter.
    Demonstrates the complete pattern for sub-agents to provide real-time feedback
    during validation operations including:
    - Agent startup notifications
    - Real-time thinking/reasoning updates
    - Progress updates during validation steps
    - Tool execution notifications
    - Completion status with results
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: UnifiedToolDispatcher,
                 websocket_manager: Optional[Any] = None):
        """Initialize ValidationSubAgent with WebSocket capabilities."""
        # Initialize base class only - single inheritance pattern
        super().__init__(llm_manager, name="ValidationSubAgent", 
                        description="Comprehensive validation with real-time feedback")
        # WebSocketContextMixin removed - using BaseAgent's bridge
        # Using single inheritance with standardized execution patterns
        
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
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> TypedAgentResult:
        """Execute validation workflow with comprehensive WebSocket events."""
        start_time = time.time()
        
        # Validate context
        context = validate_user_context(context)
        
        try:
            # Create database session manager
            session_mgr = DatabaseSessionManager(context)
            
            # Emit thinking event (agent_started is handled by orchestrator)
            await self.emit_thinking("Starting comprehensive validation process")
            
            # Validate input context
            if not self._validate_execution_context(context):
                await self.emit_error("Invalid execution context for validation")
                return self._create_error_result("Invalid execution context", start_time)
            
            # Emit initial thinking
            await self.emit_thinking("Analyzing validation requirements and preparing validation suite...")
            
            # Extract validation request
            validation_request = self._extract_validation_request(context)
            
            # Execute validation steps with progress updates
            validation_results = await self._execute_validation_steps(validation_request, context.run_id)
            
            # Generate validation summary
            await self.emit_progress("Generating validation summary and recommendations...")
            validation_summary = await self._generate_validation_summary(validation_results)
            
            # Prepare final result
            execution_time = (time.time() - start_time) * 1000
            
            result_data = {
                "validation_type": validation_request["type"],
                "execution_time_ms": execution_time,
                "rules_checked": len(self.validation_rules),
                "validation_passed": validation_summary["overall_passed"],
                "issues_found": validation_summary["issues_count"],
                "recommendations": ", ".join(validation_summary["recommendations"])
            }
            
            # Emit completion event using mixin methods
            await self.emit_progress("Validation process completed successfully", is_complete=True)
            
            return TypedAgentResult(
                success=True,
                result=result_data,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            await self.emit_error(f"ValidationSubAgent execution failed: {str(e)}")
            self.logger.error(f"ValidationSubAgent execution failed: {str(e)}")
            return self._create_error_result(str(e), start_time)
        finally:
            # Ensure proper cleanup
            try:
                if 'session_mgr' in locals():
                    await session_mgr.cleanup()
            except Exception as cleanup_e:
                self.logger.error(f"Session cleanup error: {cleanup_e}")
    
    # execute_core_logic and validate_preconditions removed - single inheritance pattern
    # All execution logic is now in execute() method only
    
    def _validate_execution_context(self, context: UserExecutionContext) -> bool:
        """Validate execution context has required validation parameters."""
        return (
            context and 
            context.metadata and 
            ('agent_input' in context.metadata or 'validation_data' in context.metadata)
        )
    
    def _extract_validation_request(self, context: UserExecutionContext) -> ValidationRequest:
        """Extract validation request parameters from context."""
        agent_input = context.metadata.get('agent_input', {})
        validation_data = context.metadata.get('validation_data', {})
        
        # Merge both sources, with agent_input taking precedence
        combined_data = {**validation_data, **agent_input}
        
        return ValidationRequest(
            type=combined_data.get("validation_type", "comprehensive"),
            target=combined_data.get("validation_target", "general"),
            rules=combined_data.get("custom_rules", self.validation_rules),
            strictness=combined_data.get("strictness_level", "standard"),
            user_id=context.user_id
        )
    
    async def _execute_validation_steps(self, request: ValidationRequest, run_id: str) -> List[ValidationRuleResult]:
        """Execute validation steps with progress updates and tool notifications."""
        validation_results = []
        rules = request["rules"]
        
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
            await self.emit_progress(f"Completed {rule} validation - {rule_result['status']}")
        
        return validation_results
    
    async def _execute_validation_rule(self, rule: str, request: ValidationRequest) -> ValidationRuleResult:
        """Execute a specific validation rule."""
        # Simulate validation logic
        start_time = time.time()
        
        # Mock validation results based on rule
        validation_data = ValidationRuleResult(
            rule=rule,
            status="passed" if rule != "security_compliance_check" else "warning",
            execution_time_ms=(time.time() - start_time) * 1000,
            details=f"Validation for {rule} completed",
            issues=[] if rule != "security_compliance_check" else ["Minor security recommendation available"]
        )
        
        # Add some realistic validation delay
        await asyncio.sleep(0.1)
        
        return validation_data
    
    async def _generate_validation_summary(self, results: List[ValidationRuleResult]) -> ValidationSummary:
        """Generate comprehensive validation summary."""
        total_rules = len(results)
        passed_rules = len([r for r in results if r["status"] == "passed"])
        warning_rules = len([r for r in results if r["status"] == "warning"])
        failed_rules = len([r for r in results if r["status"] == "failed"])
        
        all_issues = []
        for result in results:
            all_issues.extend(result["issues"])
        
        recommendations = []
        if warning_rules > 0:
            recommendations.append("Review warning items for optimization opportunities")
        if failed_rules > 0:
            recommendations.append("Address failed validation rules before proceeding")
        if len(all_issues) == 0:
            recommendations.append("All validation checks passed successfully")
        
        return ValidationSummary(
            overall_passed=failed_rules == 0,
            total_rules=total_rules,
            passed_rules=passed_rules,
            warning_rules=warning_rules,
            failed_rules=failed_rules,
            issues_count=len(all_issues),
            issues=all_issues,
            recommendations=recommendations,
            validation_score=(passed_rules + warning_rules * 0.5) / total_rules if total_rules > 0 else 0.0
        )
    
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
    
    # _context_to_state removed - no longer needed with single inheritance pattern
    
    # Health and status methods
    def get_health_status(self) -> AgentHealthStatus:
        """Get comprehensive health status."""
        return AgentHealthStatus(
            agent_name="ValidationSubAgent",
            status="healthy",
            validation_rules_loaded=len(self.validation_rules),
            websocket_enabled=self.has_websocket_context(),
            components={
                "validation_engine": "active",
                "websocket_context": "active" if self.has_websocket_context() else "inactive"
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )
