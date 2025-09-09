"""
Test Agent Execution Order Validation Logic for Golden Path

CRITICAL UNIT TEST: This validates the Data → Optimization → Report agent execution 
order that is fundamental to delivering business value in the Golden Path.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure proper agent execution sequence for accurate insights  
- Value Impact: Wrong order = incorrect cost optimization recommendations
- Strategic Impact: Core business logic for $500K+ ARR delivery

GOLDEN PATH REQUIREMENT: Agent Execution Pipeline Order
Data Agent (collect metrics) → Optimization Agent (analyze) → Report Agent (deliver)
This test validates the ordering logic without actual agent execution.
"""

import pytest
import time
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from unittest.mock import Mock

# SSOT imports following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.types.core_types import UserID, ThreadID, RunID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class AgentType(Enum):
    """Agent types in the Golden Path execution pipeline."""
    DATA = "data_agent"
    OPTIMIZATION = "optimization_agent" 
    REPORT = "report_agent"
    TRIAGE = "triage_agent"  # Can run first for message classification


class AgentExecutionState(Enum):
    """Agent execution states for tracking."""
    PENDING = "pending"
    STARTED = "started"
    THINKING = "thinking"
    EXECUTING_TOOLS = "executing_tools"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentExecutionContext:
    """Context for agent execution tracking."""
    agent_type: AgentType
    user_id: UserID
    thread_id: ThreadID
    run_id: RunID
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    state: AgentExecutionState = AgentExecutionState.PENDING
    dependencies_met: bool = False
    execution_order_position: int = 0
    
    def mark_completed(self):
        """Mark agent execution as completed."""
        self.state = AgentExecutionState.COMPLETED
        self.end_time = time.time()
    
    def mark_failed(self, error_message: str = ""):
        """Mark agent execution as failed."""
        self.state = AgentExecutionState.FAILED
        self.end_time = time.time()
    
    def get_duration(self) -> float:
        """Get execution duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time


class AgentExecutionOrderValidator:
    """
    Core logic for validating and enforcing agent execution order.
    This is the system under test - extracted from production code for unit testing.
    """
    
    def __init__(self):
        self.required_order = self._get_required_execution_order()
        self.dependency_map = self._build_dependency_map()
        self.execution_contexts: List[AgentExecutionContext] = []
        
    def _get_required_execution_order(self) -> List[AgentType]:
        """Define the required agent execution order for Golden Path."""
        return [
            AgentType.DATA,         # Step 1: Collect and analyze data
            AgentType.OPTIMIZATION, # Step 2: Generate optimization recommendations  
            AgentType.REPORT        # Step 3: Format and deliver results
        ]
    
    def _build_dependency_map(self) -> Dict[AgentType, List[AgentType]]:
        """Build dependency map for agent execution order."""
        return {
            AgentType.DATA: [],  # No dependencies - can start immediately
            AgentType.OPTIMIZATION: [AgentType.DATA],  # Needs data first
            AgentType.REPORT: [AgentType.DATA, AgentType.OPTIMIZATION],  # Needs both
            AgentType.TRIAGE: []  # Can run independently for message classification
        }
    
    def validate_execution_order(self, proposed_order: List[AgentType]) -> Dict[str, Any]:
        """
        Validate a proposed agent execution order against requirements.
        
        Returns:
            Dict with validation results
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "corrected_order": None,
            "dependency_violations": [],
            "missing_agents": [],
            "extra_agents": []
        }
        
        # Check for missing required agents
        required_set = set(self.required_order)
        proposed_set = set(proposed_order)
        
        missing = required_set - proposed_set
        extra = proposed_set - required_set
        
        if missing:
            validation_result["missing_agents"] = list(missing)
            validation_result["errors"].append(f"Missing required agents: {missing}")
            validation_result["valid"] = False
        
        if extra:
            validation_result["extra_agents"] = list(extra)
            validation_result["warnings"].append(f"Extra agents not in standard flow: {extra}")
        
        # Check dependency violations
        for i, agent in enumerate(proposed_order):
            if agent in self.dependency_map:
                dependencies = self.dependency_map[agent]
                
                # Check if all dependencies appear before this agent
                for dep in dependencies:
                    if dep not in proposed_order[:i]:
                        violation = f"{agent.value} requires {dep.value} to execute first"
                        validation_result["dependency_violations"].append(violation)
                        validation_result["errors"].append(violation)
                        validation_result["valid"] = False
        
        # Generate corrected order if needed
        if not validation_result["valid"]:
            validation_result["corrected_order"] = self._generate_corrected_order(proposed_order)
        
        return validation_result
    
    def _generate_corrected_order(self, proposed_order: List[AgentType]) -> List[AgentType]:
        """Generate a corrected execution order that satisfies dependencies."""
        # Start with required agents in correct order
        corrected = self.required_order.copy()
        
        # Add any extra agents at appropriate positions
        for agent in proposed_order:
            if agent not in corrected and agent in self.dependency_map:
                # Find appropriate insertion point based on dependencies
                dependencies = self.dependency_map[agent]
                
                if not dependencies:
                    # No dependencies - can go first
                    corrected.insert(0, agent)
                else:
                    # Insert after all dependencies
                    max_dep_index = -1
                    for dep in dependencies:
                        if dep in corrected:
                            max_dep_index = max(max_dep_index, corrected.index(dep))
                    
                    insertion_point = max_dep_index + 1
                    corrected.insert(insertion_point, agent)
        
        return corrected
    
    def check_agent_dependencies_met(
        self, 
        agent_type: AgentType, 
        completed_agents: List[AgentType]
    ) -> Dict[str, Any]:
        """Check if an agent's dependencies are met."""
        dependencies = self.dependency_map.get(agent_type, [])
        
        missing_deps = [dep for dep in dependencies if dep not in completed_agents]
        
        return {
            "dependencies_met": len(missing_deps) == 0,
            "required_dependencies": dependencies,
            "missing_dependencies": missing_deps,
            "can_execute": len(missing_deps) == 0
        }
    
    def track_agent_execution(self, context: AgentExecutionContext):
        """Track agent execution for order validation."""
        self.execution_contexts.append(context)
    
    def validate_actual_execution_order(self) -> Dict[str, Any]:
        """Validate the actual execution order from tracked contexts."""
        if not self.execution_contexts:
            return {"valid": True, "message": "No executions to validate"}
        
        # Sort by start time to get actual execution order
        sorted_contexts = sorted(self.execution_contexts, key=lambda x: x.start_time)
        actual_order = [ctx.agent_type for ctx in sorted_contexts]
        
        # Validate against required order
        return self.validate_execution_order(actual_order)
    
    def get_next_executable_agents(
        self, 
        completed_agents: List[AgentType]
    ) -> List[AgentType]:
        """Get list of agents that can execute next based on completed agents."""
        executable = []
        
        for agent_type in AgentType:
            if agent_type not in completed_agents:
                deps_check = self.check_agent_dependencies_met(agent_type, completed_agents)
                if deps_check["can_execute"]:
                    executable.append(agent_type)
        
        return executable


class TestAgentExecutionOrderValidator(SSotAsyncTestCase):
    """Test agent execution order validation logic."""
    
    def setup_method(self, method=None):
        """Setup test with order validator."""
        super().setup_method(method)
        self.order_validator = AgentExecutionOrderValidator()
        self.id_generator = UnifiedIdGenerator()
        
        # Test metrics
        self.record_metric("test_category", "unit")
        self.record_metric("golden_path_component", "agent_execution_order")
        
    @pytest.mark.unit
    def test_correct_agent_execution_order_validation(self):
        """Test validation of correct agent execution order."""
        # Test the required golden path order
        correct_order = [AgentType.DATA, AgentType.OPTIMIZATION, AgentType.REPORT]
        
        result = self.order_validator.validate_execution_order(correct_order)
        
        # Assertions
        assert result["valid"] is True, f"Correct order should be valid: {result}"
        assert len(result["errors"]) == 0, f"Should have no errors: {result['errors']}"
        assert len(result["dependency_violations"]) == 0, \
            f"Should have no dependency violations: {result['dependency_violations']}"
        assert result["corrected_order"] is None, "Should not need correction"
        
        self.record_metric("correct_order_validation_passed", True)
        
    @pytest.mark.unit
    def test_incorrect_agent_execution_order_detection(self):
        """Test detection of incorrect agent execution order."""
        # Test wrong order - optimization before data
        wrong_order = [AgentType.OPTIMIZATION, AgentType.DATA, AgentType.REPORT]
        
        result = self.order_validator.validate_execution_order(wrong_order)
        
        # Assertions
        assert result["valid"] is False, "Wrong order should be invalid"
        assert len(result["errors"]) > 0, "Should have errors for wrong order"
        assert len(result["dependency_violations"]) > 0, "Should detect dependency violations"
        assert result["corrected_order"] is not None, "Should provide corrected order"
        
        # Check specific violation
        violations = result["dependency_violations"]
        optimization_violation = any("optimization_agent requires data_agent" in v for v in violations)
        assert optimization_violation, f"Should detect optimization before data violation: {violations}"
        
        self.record_metric("incorrect_order_detection_passed", True)
        
    @pytest.mark.unit
    def test_missing_required_agents_detection(self):
        """Test detection of missing required agents."""
        # Test with missing optimization agent
        incomplete_order = [AgentType.DATA, AgentType.REPORT]
        
        result = self.order_validator.validate_execution_order(incomplete_order)
        
        # Assertions
        assert result["valid"] is False, "Incomplete order should be invalid"
        assert AgentType.OPTIMIZATION in result["missing_agents"], \
            f"Should detect missing optimization agent: {result['missing_agents']}"
        assert len(result["errors"]) > 0, "Should have errors for missing agents"
        
        self.record_metric("missing_agents_detection_passed", True)
        
    @pytest.mark.unit
    def test_extra_agents_handling(self):
        """Test handling of extra agents not in standard flow."""
        # Test with triage agent (allowed but extra)
        order_with_extra = [AgentType.TRIAGE, AgentType.DATA, AgentType.OPTIMIZATION, AgentType.REPORT]
        
        result = self.order_validator.validate_execution_order(order_with_extra)
        
        # Assertions
        assert result["valid"] is True, "Extra agents should not invalidate if dependencies met"
        assert AgentType.TRIAGE in result["extra_agents"], \
            f"Should identify triage as extra: {result['extra_agents']}"
        assert len(result["warnings"]) > 0, "Should warn about extra agents"
        
        self.record_metric("extra_agents_handling_passed", True)
        
    @pytest.mark.unit
    def test_agent_dependency_checking(self):
        """Test individual agent dependency checking."""
        # Test data agent (no dependencies)
        data_deps = self.order_validator.check_agent_dependencies_met(
            AgentType.DATA, []
        )
        assert data_deps["dependencies_met"] is True, "Data agent should have no dependencies"
        assert data_deps["can_execute"] is True, "Data agent should be executable"
        
        # Test optimization agent without data
        opt_deps_without_data = self.order_validator.check_agent_dependencies_met(
            AgentType.OPTIMIZATION, []
        )
        assert opt_deps_without_data["dependencies_met"] is False, \
            "Optimization agent should need data dependency"
        assert AgentType.DATA in opt_deps_without_data["missing_dependencies"], \
            "Should identify data as missing dependency"
        
        # Test optimization agent with data
        opt_deps_with_data = self.order_validator.check_agent_dependencies_met(
            AgentType.OPTIMIZATION, [AgentType.DATA]
        )
        assert opt_deps_with_data["dependencies_met"] is True, \
            "Optimization agent should be satisfied with data"
        assert opt_deps_with_data["can_execute"] is True, \
            "Optimization agent should be executable with data"
        
        # Test report agent (needs both data and optimization)
        report_deps_partial = self.order_validator.check_agent_dependencies_met(
            AgentType.REPORT, [AgentType.DATA]
        )
        assert report_deps_partial["dependencies_met"] is False, \
            "Report agent needs both data and optimization"
        assert AgentType.OPTIMIZATION in report_deps_partial["missing_dependencies"], \
            "Should identify optimization as missing"
        
        report_deps_complete = self.order_validator.check_agent_dependencies_met(
            AgentType.REPORT, [AgentType.DATA, AgentType.OPTIMIZATION]
        )
        assert report_deps_complete["dependencies_met"] is True, \
            "Report agent should be satisfied with both dependencies"
        
        self.record_metric("dependency_checking_passed", True)
        
    @pytest.mark.unit
    def test_corrected_order_generation(self):
        """Test automatic generation of corrected execution order."""
        test_cases = [
            {
                "wrong_order": [AgentType.REPORT, AgentType.DATA, AgentType.OPTIMIZATION],
                "description": "Completely reversed order"
            },
            {
                "wrong_order": [AgentType.OPTIMIZATION, AgentType.REPORT, AgentType.DATA],
                "description": "Random wrong order"
            },
            {
                "wrong_order": [AgentType.DATA, AgentType.REPORT],
                "description": "Missing middle agent"
            }
        ]
        
        for case in test_cases:
            result = self.order_validator.validate_execution_order(case["wrong_order"])
            corrected = result["corrected_order"]
            
            assert corrected is not None, f"Should provide correction for: {case['description']}"
            
            # Validate the corrected order is actually valid
            corrected_result = self.order_validator.validate_execution_order(corrected)
            assert corrected_result["valid"] is True, \
                f"Corrected order should be valid for: {case['description']}"
            
            # Verify correct sequence
            data_pos = corrected.index(AgentType.DATA)
            opt_pos = corrected.index(AgentType.OPTIMIZATION) 
            report_pos = corrected.index(AgentType.REPORT)
            
            assert data_pos < opt_pos, f"Data should come before optimization: {corrected}"
            assert opt_pos < report_pos, f"Optimization should come before report: {corrected}"
        
        self.record_metric("corrected_order_generation_passed", True)
        
    @pytest.mark.unit
    def test_next_executable_agents_calculation(self):
        """Test calculation of which agents can execute next."""
        # Start with no completed agents
        next_agents = self.order_validator.get_next_executable_agents([])
        assert AgentType.DATA in next_agents, "Data agent should be executable first"
        assert AgentType.TRIAGE in next_agents, "Triage agent should also be executable first"
        assert AgentType.OPTIMIZATION not in next_agents, "Optimization should not be executable yet"
        assert AgentType.REPORT not in next_agents, "Report should not be executable yet"
        
        # After data completes
        next_after_data = self.order_validator.get_next_executable_agents([AgentType.DATA])
        assert AgentType.OPTIMIZATION in next_after_data, \
            "Optimization should be executable after data"
        assert AgentType.REPORT not in next_after_data, \
            "Report should still not be executable"
        
        # After data and optimization complete
        next_after_opt = self.order_validator.get_next_executable_agents([
            AgentType.DATA, AgentType.OPTIMIZATION
        ])
        assert AgentType.REPORT in next_after_opt, \
            "Report should be executable after data and optimization"
        
        # After all complete
        next_after_all = self.order_validator.get_next_executable_agents([
            AgentType.DATA, AgentType.OPTIMIZATION, AgentType.REPORT
        ])
        assert len(next_after_all) == 0, "No agents should be executable after all complete"
        
        self.record_metric("next_executable_calculation_passed", True)
        
    @pytest.mark.unit
    def test_execution_context_tracking(self):
        """Test tracking of agent execution contexts."""
        user_id = UserID(self.id_generator.generate_user_id())
        thread_id = ThreadID(self.id_generator.generate_thread_id())
        run_id = RunID(self.id_generator.generate_run_id())
        
        # Create execution contexts
        data_context = AgentExecutionContext(
            agent_type=AgentType.DATA,
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        
        # Test context state transitions
        assert data_context.state == AgentExecutionState.PENDING, "Should start pending"
        
        data_context.state = AgentExecutionState.STARTED
        data_context.state = AgentExecutionState.THINKING
        data_context.state = AgentExecutionState.EXECUTING_TOOLS
        data_context.mark_completed()
        
        assert data_context.state == AgentExecutionState.COMPLETED, "Should be completed"
        assert data_context.end_time is not None, "Should have end time"
        assert data_context.get_duration() > 0, "Should have positive duration"
        
        # Track in validator
        self.order_validator.track_agent_execution(data_context)
        assert len(self.order_validator.execution_contexts) == 1, \
            "Should track execution context"
        
        self.record_metric("execution_tracking_passed", True)
        
    @pytest.mark.unit  
    def test_actual_execution_order_validation(self):
        """Test validation of actual execution order from tracked contexts."""
        user_id = UserID(self.id_generator.generate_user_id())
        thread_id = ThreadID(self.id_generator.generate_thread_id())
        run_id = RunID(self.id_generator.generate_run_id())
        
        # Create contexts with different start times to simulate execution order
        base_time = time.time()
        
        contexts = [
            AgentExecutionContext(
                agent_type=AgentType.DATA,
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                start_time=base_time
            ),
            AgentExecutionContext(
                agent_type=AgentType.OPTIMIZATION,
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                start_time=base_time + 1.0
            ),
            AgentExecutionContext(
                agent_type=AgentType.REPORT,
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                start_time=base_time + 2.0
            )
        ]
        
        # Track contexts in correct order
        for context in contexts:
            self.order_validator.track_agent_execution(context)
        
        # Validate actual execution order
        result = self.order_validator.validate_actual_execution_order()
        
        assert result["valid"] is True, f"Correct actual order should be valid: {result}"
        assert len(result["errors"]) == 0, f"Should have no errors: {result['errors']}"
        
        self.record_metric("actual_execution_validation_passed", True)
        
    @pytest.mark.unit
    def test_concurrent_agent_dependency_resolution(self):
        """Test dependency resolution for concurrent agent scenarios."""
        # Test scenario where multiple agents could theoretically run in parallel
        # but must respect dependencies
        
        # Triage and Data can run concurrently (no dependencies)
        concurrent_executable = self.order_validator.get_next_executable_agents([])
        assert AgentType.DATA in concurrent_executable, "Data should be executable"
        assert AgentType.TRIAGE in concurrent_executable, "Triage should be executable"
        
        # But optimization must wait for data
        assert AgentType.OPTIMIZATION not in concurrent_executable, \
            "Optimization cannot run concurrently with data"
        
        # After data completes, optimization can start while triage might still be running
        after_data = self.order_validator.get_next_executable_agents([AgentType.DATA])
        assert AgentType.OPTIMIZATION in after_data, \
            "Optimization should be executable after data"
        
        # Verify that even if triage completes, optimization still needs data
        triage_only = self.order_validator.get_next_executable_agents([AgentType.TRIAGE])
        assert AgentType.OPTIMIZATION not in triage_only, \
            "Optimization should not be executable with only triage complete"
        
        self.record_metric("concurrent_dependency_resolution_passed", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])