"""
Test helpers for comprehensive agent system testing.

Provides mock implementations and helper methods for agent system tests.
These are simplified implementations focused on testing the core patterns.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.schemas.strict_types import TypedAgentResult

class MockSupervisorAgent:
    """Mock supervisor agent for testing routing and coordination"""
    
    def __init__(self, llm_manager, tool_dispatcher):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.agent_registry = MockAgentRegistry()
        self.max_concurrent_agents = 3
        self.min_quality_threshold = 0.7
        self.current_daily_spend = 0.0
        self.daily_budget = 1000.0
        self.active_executions = set()
        
    async def _determine_agent_routing(self, state: DeepAgentState) -> Dict[str, Any]:
        """Determine routing for agent requests"""
        routing = {
            "primary_agents": [],
            "routing_strategy": "balanced",
            "estimated_duration": 1.0,
            "priority": 1,
            "resource_allocation": 1.0
        }
        
        # Route based on request type
        if "data" in state.request_type.lower():
            routing["primary_agents"].append("data")
        if "optimization" in state.request_type.lower():
            routing["primary_agents"].append("optimization")
        if "critical" in str(state.context).lower():
            routing["priority"] = 3
            routing["resource_allocation"] = 2.0
            routing["routing_strategy"] = "specialized"
            
        if not routing["primary_agents"]:
            routing["primary_agents"] = ["triage"]
            
        return routing
        
    async def execute(self, state: DeepAgentState, run_id: str) -> TypedAgentResult:
        """Execute agent pipeline"""
        self.active_executions.add(run_id)
        try:
            await asyncio.sleep(0.1)  # Simulate processing
            return TypedAgentResult(
                success=True,
                result="Analysis completed successfully",
                metadata={"execution_time": 0.1}
            )
        finally:
            self.active_executions.discard(run_id)
            
    async def _aggregate_agent_responses(self, responses: Dict[str, TypedAgentResult]) -> TypedAgentResult:
        """Aggregate responses from multiple agents"""
        if not responses:
            return TypedAgentResult(
                success=False,
                result="No responses to aggregate",
                error="No responses to aggregate",
                metadata={"execution_time": 0.0}
            )
            
        successful_responses = {k: v for k, v in responses.items() if v.success}
        failed_responses = {k: v for k, v in responses.items() if not v.success}
        
        if not successful_responses:
            return TypedAgentResult(
                success=False,
                result="All agents failed",
                error="All agents failed",
                metadata={"execution_time": sum(r.metadata.get("execution_time", 0) for r in responses.values())}
            )
            
        # Determine overall status
        overall_success = not failed_responses
            
        # Combine results
        result_parts = []
        for agent, response in successful_responses.items():
            result_parts.append(f"{agent}: {response.result}")
            
        if failed_responses:
            for agent, response in failed_responses.items():
                result_parts.append(f"{agent}: {response.result}")
                
        return TypedAgentResult(
            success=overall_success,
            result="; ".join(result_parts),
            metadata={
                "execution_time": max(r.metadata.get("execution_time", 0) for r in responses.values()),
                "partial_success": bool(failed_responses)
            }
        )
        
    async def _generate_cost_optimization_recommendations(self, cost_data: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate cost optimization recommendations"""
        recommendations = []
        
        for agent_name, data in cost_data.items():
            if data["cost"] > 50.0:
                recommendations.append(f"Consider optimizing {agent_name} - high cost per operation")
            if data["avg_duration"] > 3.0:
                recommendations.append(f"Optimize {agent_name} performance - long execution times")
                
        return recommendations
        
    def set_daily_budget(self, budget: float):
        """Set daily cost budget"""
        self.daily_budget = budget
        
    async def execute_with_budget_check(self, state: DeepAgentState, run_id: str) -> TypedAgentResult:
        """Execute with budget checking"""
        estimated_cost = 10.0  # Simplified cost estimation
        
        if self.current_daily_spend + estimated_cost > self.daily_budget:
            return TypedAgentResult(
                success=False,
                result="Daily budget exceeded",
                error="Daily budget exceeded",
                metadata={"execution_time": 0.0}
            )
            
        result = await self.execute(state, run_id)
        if result.success:
            self.current_daily_spend += estimated_cost
            
        return result
        
    async def _calculate_quality_score(self, response: str) -> float:
        """Calculate quality score for response"""
        score = 0.5  # Base score
        
        # Length-based scoring
        if len(response) > 50:
            score += 0.2
        if len(response) > 100:
            score += 0.1
            
        # Content-based scoring
        if any(word in response.lower() for word in ["analysis", "insights", "recommendations"]):
            score += 0.2
        if any(char.isdigit() for char in response):  # Contains metrics
            score += 0.1
        if "error" in response.lower() or "failed" in response.lower():
            score -= 0.3
            
        return max(0.0, min(1.0, score))
        
    async def _process_with_quality_check(self, response: TypedAgentResult) -> TypedAgentResult:
        """Process response with quality checking"""
        quality_score = await self._calculate_quality_score(response.result)
        
        if quality_score < self.min_quality_threshold:
            # Enhance or flag low quality response
            if len(response.result) < 20:
                enhanced_result = f"Enhanced response: {response.result} - providing additional context and details"
                return TypedAgentResult(
                    success=response.success,
                    result=enhanced_result,
                    error=response.error,
                    metadata=response.metadata
                )
            else:
                return TypedAgentResult(
                    success=False,
                    result=response.result,
                    error="Quality score below threshold",
                    metadata=response.metadata
                )
                
        return response
        
    def _get_fallback_config(self) -> Dict[str, Any]:
        """Get fallback configuration"""
        return {
            "primary": "advanced_agent",
            "fallbacks": ["standard_agent", "basic_agent"],
            "timeout_per_fallback": 2.0
        }
        
    async def _execute_with_fallback(self, state: DeepAgentState, run_id: str) -> TypedAgentResult:
        """Execute with fallback logic"""
        fallback_config = self._get_fallback_config()
        agents_to_try = [fallback_config["primary"]] + fallback_config["fallbacks"]
        
        for agent_name in agents_to_try:
            try:
                agent = self.agent_registry.get_agent(agent_name)
                result = await agent.execute(state, run_id)
                if result.status == ExecutionStatus.SUCCESS:
                    return result
            except Exception as e:
                continue
                
        return TypedAgentResult(
            success=False,
            result="All fallback options exhausted",
            error="All fallback options exhausted",
            metadata={"execution_time": 0.0}
        )
        
    async def _execute_with_access_control(self, state: DeepAgentState, run_id: str) -> TypedAgentResult:
        """Execute with access control validation"""
        user_permissions = state.context.get("permissions", [])
        
        # Check if user has required permissions
        if not user_permissions:
            return TypedAgentResult(
                success=False,
                result="Access denied - no permissions",
                error="Access denied - no permissions",
                metadata={"execution_time": 0.0}
            )
            
        if "sensitive_operation" in state.request_type and "admin" not in user_permissions:
            return TypedAgentResult(
                success=False,
                result="Access denied - insufficient permissions",
                error="Access denied - insufficient permissions",
                metadata={"execution_time": 0.0}
            )
            
        return await self.execute(state, run_id)
        
    async def _audit_log(self, event_type: str, details: Dict[str, Any]):
        """Mock audit logging"""
        # In real implementation, this would write to audit log
        pass
        
    async def _send_coordination_message(self, from_agent: str, to_agent: str, message: Dict[str, Any]):
        """Mock inter-agent communication"""
        # In real implementation, this would send messages between agents
        pass

class MockAgentRegistry:
    """Mock agent registry for testing"""
    
    def get_agent(self, name: str):
        """Get mock agent by name"""
        # Mock: Generic component isolation for controlled unit testing
        agent = Mock()
        # Mock: Agent service isolation for testing without LLM agent execution
        agent.execute = AsyncMock(return_value=TypedAgentResult(
            success=True,
            result=f"Mock result from {name}",
            metadata={"execution_time": 0.5}
        ))
        return agent

class MockDataSubAgentExtensions:
    """Extensions for DataSubAgent to support comprehensive testing"""
    
    @staticmethod
    def enhance_agent_for_testing(agent):
        """Add testing capabilities to DataSubAgent"""
        # Cost tracking
        agent.enable_cost_tracking = True
        agent.cost_per_operation = 0.01
        agent.total_cost = 0.0
        agent.cost_history = []
        
        # Performance tracking
        agent.enable_performance_tracking = True
        agent.performance_metrics = []
        
        # Circuit breaker
        agent.circuit_breaker_threshold = 3
        agent.circuit_breaker_timeout = 1.0
        agent._circuit_breaker_active = False
        agent._failure_count = 0
        
        # Operation counter
        agent.operation_counter = 0
        
        # Override process_data to include tracking
        original_process_data = agent.process_data
        
        async def tracked_process_data(data):
            start_time = time.time()
            
            try:
                result = await original_process_data(data)
                
                # Track successful operation
                execution_time = time.time() - start_time
                
                if agent.enable_cost_tracking:
                    cost = agent.cost_per_operation
                    agent.total_cost += cost
                    agent.cost_history.append({
                        "operation": data.get("operation", "unknown"),
                        "cost": cost,
                        "timestamp": datetime.now(timezone.utc)
                    })
                    
                if agent.enable_performance_tracking:
                    agent.performance_metrics.append({
                        "operation": data.get("operation", "unknown"),
                        "execution_time": execution_time,
                        "timestamp": datetime.now(timezone.utc)
                    })
                    
                agent.operation_counter += 1
                agent._failure_count = 0  # Reset on success
                
                # Sanitize result for security
                result = MockDataSubAgentExtensions._sanitize_result(result, data)
                
                return result
                
            except Exception as e:
                agent._failure_count += 1
                if agent._failure_count >= agent.circuit_breaker_threshold:
                    agent._circuit_breaker_active = True
                raise
                
        agent.process_data = tracked_process_data
        
        return agent
        
    @staticmethod
    def _sanitize_result(result: Dict[str, Any], original_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize result for security and privacy"""
        result_str = json.dumps(result)
        
        # Mask PII
        if "ssn" in original_data:
            result_str = result_str.replace(original_data["ssn"], "***-**-****")
        if "credit_card" in original_data:
            result_str = result_str.replace(original_data["credit_card"], "****-****-****-****")
        if "email" in original_data:
            email = original_data["email"]
            if "@" in email:
                user, domain = email.split("@", 1)
                masked_email = f"***@{domain}"
                result_str = result_str.replace(email, masked_email)
                
        # Remove dangerous patterns
        dangerous_patterns = ["DROP TABLE", "__import__", "<script>", "../"]
        for pattern in dangerous_patterns:
            result_str = result_str.replace(pattern, "[FILTERED]")
            
        return json.loads(result_str)

# Enum extension for additional statuses
class ExtendedExecutionStatus:
    """Extended execution status for testing"""
    PARTIAL_SUCCESS = "partial_success"
    NEEDS_IMPROVEMENT = "needs_improvement" 
    FORBIDDEN = "forbidden"

# Mock the extended status into the original enum
ExecutionStatus.PARTIAL_SUCCESS = ExtendedExecutionStatus.PARTIAL_SUCCESS
ExecutionStatus.NEEDS_IMPROVEMENT = ExtendedExecutionStatus.NEEDS_IMPROVEMENT
ExecutionStatus.FORBIDDEN = ExtendedExecutionStatus.FORBIDDEN