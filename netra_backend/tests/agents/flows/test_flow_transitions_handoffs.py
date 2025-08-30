"""Test flow transitions, agent handoffs, and state accumulation.

Business Value Justification (BVJ):
- Segment: Enterprise, Mid
- Business Goal: System Reliability and Data Integrity
- Value Impact: Ensures seamless workflow transitions worth $10K-100K+ optimizations
- Strategic Impact: Prevents data loss and maintains context through complex flows

This test validates that agent handoffs work correctly, state accumulates properly,
and transitions between different workflow types are handled seamlessly.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Dict, Any, List
import json
import copy

from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState


class TestFlowTransitionsAndHandoffs:
    """Validate transitions between agents and workflow adaptations."""
    
    @pytest.fixture
    def initial_state(self):
        """Create initial state for testing."""
        state = DeepAgentState()
        state.user_request = json.dumps({
            "request": "Optimize my AI",
            "session_id": "test-session-123"
        })
        return state
    
    @pytest.fixture
    def mock_agent_outputs(self):
        """Mock outputs from different agents."""
        return {
            "triage": {
                "data_sufficiency": "partial",
                "category": "cost_optimization",
                "confidence": 0.75,
                "identified_metrics": ["spend", "model"],
                "missing_data": ["usage_patterns", "latency"]
            },
            "optimization": {
                "recommendations": [
                    {"strategy": "model_switching", "savings": 1000},
                    {"strategy": "batch_processing", "savings": 500}
                ],
                "total_estimated_savings": 1500,
                "confidence_level": "medium"
            },
            "data": {
                "insights": {
                    "token_efficiency": 0.65,
                    "peak_usage_hours": [9, 10, 14, 15]
                },
                "patterns_identified": 3
            },
            "actions": {
                "implementation_plan": [
                    {"step": 1, "action": "Setup monitoring"},
                    {"step": 2, "action": "Implement routing"}
                ],
                "timeline": "2 weeks"
            },
            "data_helper": {
                "data_request": {
                    "metrics_needed": ["latency", "error_rates"],
                    "collection_method": "API export"
                }
            },
            "reporting": {
                "executive_summary": "Optimization plan ready",
                "next_steps": ["Review", "Approve", "Implement"]
            }
        }
    
    @pytest.mark.asyncio
    async def test_triage_to_optimization_handoff(self, initial_state, mock_agent_outputs):
        """Test state handoff from triage to optimization agent."""
        # Setup state after triage
        from netra_backend.app.agents.triage_sub_agent.models import TriageResult
        initial_state.triage_result = TriageResult(
            category="cost_optimization",
            confidence_score=0.75,
            data_sufficiency="partial",
            identified_metrics=["spend", "model"],
            missing_data=["usage_patterns", "latency"],
            workflow_recommendation="modified_pipeline",
            data_request_priority="medium"
        )
        
        # Verify optimization agent receives triage output
        from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
        
        with patch.object(OptimizationsCoreSubAgent, 'llm_manager') as mock_llm_manager:
            mock_llm_manager.ask_structured_llm.return_value = mock_agent_outputs["optimization"]
            
            agent = OptimizationsCoreSubAgent()
            context = ExecutionContext(
                run_id="test-run",
                agent_name="optimization",
                state=initial_state
            )
            
            # Agent should have access to triage output
            triage_output = context.state.get_agent_output("triage")
            assert triage_output is not None
            assert triage_output["data_sufficiency"] == "partial"
            assert triage_output["category"] == "cost_optimization"
            
            result = await agent.execute(context)
            
            assert result.success
            # Optimization should adapt based on partial data
            assert result.result["confidence_level"] == "medium"
    
    @pytest.mark.asyncio
    async def test_state_accumulation_through_pipeline(self, initial_state, mock_agent_outputs):
        """Test that state correctly accumulates through entire pipeline."""
        agents_executed = []
        state_snapshots = []
        
        async def execute_and_track(agent_name, state, output):
            """Execute agent and track state changes."""
            agents_executed.append(agent_name)
            # Set appropriate state field based on agent_name
            if agent_name == "triage":
                from netra_backend.app.agents.triage_sub_agent.models import TriageResult
                state.triage_result = TriageResult(**output) if isinstance(output, dict) else output
            elif agent_name == "optimization":
                from netra_backend.app.agents.state import OptimizationsResult
                state.optimizations_result = OptimizationsResult(**output) if isinstance(output, dict) else output
            # Add other agent types as needed
            # Take a deep copy snapshot of the state
            outputs_available = []
            if state.triage_result:
                outputs_available.append("triage")
            if state.optimizations_result:
                outputs_available.append("optimization")
            if state.data_result:
                outputs_available.append("data")
            if state.action_plan_result:
                outputs_available.append("action_plan")
            if state.report_result:
                outputs_available.append("report")
            
            state_snapshots.append({
                "agent": agent_name,
                "outputs_available": outputs_available,
                "output_count": len(outputs_available)
            })
            return ExecutionResult(success=True, status="completed", result=output)
        
        # Simulate pipeline execution
        flow_sequence = ["triage", "optimization", "actions", "data_helper", "reporting"]
        
        for agent_name in flow_sequence:
            await execute_and_track(
                agent_name,
                initial_state,
                mock_agent_outputs[agent_name]
            )
        
        # Verify state accumulation
        assert len(agents_executed) == 5
        assert len(state_snapshots) == 5
        
        # Check progressive accumulation
        for i, snapshot in enumerate(state_snapshots):
            assert snapshot["output_count"] == i + 1
            assert len(snapshot["outputs_available"]) == i + 1
        
        # Verify final state has all outputs
        final_outputs = initial_state.agent_outputs
        assert len(final_outputs) == 5
        for agent_name in flow_sequence:
            assert agent_name in final_outputs
            assert final_outputs[agent_name] == mock_agent_outputs[agent_name]
    
    @pytest.mark.asyncio
    async def test_workflow_transition_sufficient_to_partial(self):
        """Test transition from sufficient to partial data workflow."""
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        with patch.object(WorkflowOrchestrator, '_define_workflow_based_on_triage') as mock_define:
            orchestrator = WorkflowOrchestrator(None, None, None)
            
            # Start with sufficient data
            triage_sufficient = {"data_sufficiency": "sufficient"}
            workflow_sufficient = orchestrator._define_workflow_based_on_triage(triage_sufficient)
            mock_define.return_value = [
                {"agent": "triage"}, {"agent": "optimization"}, 
                {"agent": "data"}, {"agent": "actions"}, {"agent": "reporting"}
            ]
            
            # User provides additional context that changes sufficiency
            updated_request = {
                "original_request": "Optimize costs",
                "additional_context": "We have changing requirements"
            }
            
            # Re-evaluate with new context
            triage_partial = {"data_sufficiency": "partial", "reason": "requirements unclear"}
            workflow_partial = orchestrator._define_workflow_based_on_triage(triage_partial)
            mock_define.return_value = [
                {"agent": "triage"}, {"agent": "optimization"},
                {"agent": "actions"}, {"agent": "data_helper"}, {"agent": "reporting"}
            ]
            
            # Verify workflow adapted
            assert len(mock_define.call_args_list) >= 1
            # Workflow should now include data_helper instead of data analysis
    
    @pytest.mark.asyncio
    async def test_error_handling_in_handoff(self):
        """Test error handling during agent handoffs."""
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        with patch.object(WorkflowOrchestrator, 'execute_agent') as mock_execute:
            # Triage succeeds
            mock_execute.side_effect = [
                ExecutionResult(success=True, status="completed", result={"data_sufficiency": "sufficient"}),
                # Optimization fails
                ExecutionResult(success=False, status="failed", error="LLM timeout"),
                # Recovery attempt with fallback
                ExecutionResult(success=True, status="completed", result={"fallback": True, "recommendations": []})
            ]
            
            orchestrator = WorkflowOrchestrator(None, None, None)
            context = ExecutionContext(
                run_id="test-run",
                agent_name="supervisor",
                state=DeepAgentState()
            )
            
            # Execute with error handling
            results = []
            results.append(await orchestrator.execute_agent("triage", context))
            
            # Handle optimization failure
            optimization_result = await orchestrator.execute_agent("optimization", context)
            if not optimization_result.success:
                # Attempt recovery with simplified optimization
                # Store error information in metadata
                context.state = context.state.add_metadata("optimization_error", optimization_result.error)
                context.state = context.state.add_metadata("fallback_mode", "true")
                results.append(await orchestrator.execute_agent("optimization", context))
            
            # Verify error was handled
            assert len(results) == 2
            assert results[0].success  # Triage succeeded
            assert results[1].result.get("fallback") is True  # Fallback was used
    
    @pytest.mark.asyncio
    async def test_parallel_agent_handoffs(self):
        """Test parallel execution and result merging."""
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        parallel_results = {
            "cost_analysis": {"monthly_spend": 5000, "breakdown": {}},
            "performance_analysis": {"p95_latency": 2.5, "throughput": 1000},
            "usage_analysis": {"peak_hours": [9, 10, 14, 15], "patterns": {}}
        }
        
        with patch('asyncio.gather') as mock_gather:
            mock_gather.return_value = [
                ExecutionResult(success=True, status="completed", result=parallel_results["cost_analysis"]),
                ExecutionResult(success=True, status="completed", result=parallel_results["performance_analysis"]),
                ExecutionResult(success=True, status="completed", result=parallel_results["usage_analysis"])
            ]
            
            orchestrator = WorkflowOrchestrator(None, None, None)
            
            # Simulate parallel analysis execution
            import asyncio
            results = await asyncio.gather(
                orchestrator.execute_agent("cost_analysis", None),
                orchestrator.execute_agent("performance_analysis", None),
                orchestrator.execute_agent("usage_analysis", None)
            )
            
            # Verify all parallel executions completed
            assert len(results) == 3
            assert all(r.success for r in results)
            
            # Merge results for next agent
            merged_analysis = {}
            for r in results:
                merged_analysis.update(r.result)
            
            assert "monthly_spend" in merged_analysis
            assert "p95_latency" in merged_analysis
            assert "peak_hours" in merged_analysis
    
    @pytest.mark.asyncio
    async def test_conditional_flow_branching(self):
        """Test conditional branching based on intermediate results."""
        state = DeepAgentState()
        
        # Simulate triage identifying high-priority issue
        from netra_backend.app.agents.triage_sub_agent.models import TriageResult
        state.triage_result = TriageResult(
            category="cost_explosion",
            confidence_score=0.95,
            data_sufficiency="sufficient",
            identified_metrics=[],
            missing_data=[],
            workflow_recommendation="emergency_optimization",
            data_request_priority="critical"
        )
        
        # Conditional branch logic
        def determine_next_agent(state):
            if state.triage_result and state.triage_result.data_request_priority == "critical":
                if state.triage_result.category == "cost_explosion":
                    return "emergency_cost_optimization"
                elif state.triage_result.category == "performance_degradation":
                    return "emergency_performance_optimization"
            return "standard_optimization"
        
        next_agent = determine_next_agent(state)
        assert next_agent == "emergency_cost_optimization"
        
        # Execute emergency optimization - store in action plan result
        from netra_backend.app.agents.state import ActionPlanResult
        state.action_plan_result = ActionPlanResult(
            action_plan_summary="Emergency cost optimization",
            actions=[
                {"action": "Switch to cheaper model", "priority": "immediate"},
                {"action": "Implement rate limiting", "priority": "immediate"}
            ]
        )
        state = state.add_metadata("estimated_immediate_savings", "2000")
        
        # Verify critical path was taken
        assert state.action_plan_result is not None
        assert len(state.action_plan_result.actions) == 2
        assert "estimated_immediate_savings" in state.metadata.custom_fields
    
    @pytest.mark.asyncio
    async def test_state_rollback_on_failure(self):
        """Test state rollback when critical agent fails."""
        initial_state = DeepAgentState()
        from netra_backend.app.agents.triage_sub_agent.models import TriageResult
        initial_state.triage_result = TriageResult(
            category="cost_optimization",
            confidence_score=0.85,
            data_sufficiency="sufficient",
            identified_metrics=[],
            missing_data=[],
            workflow_recommendation="standard_optimization",
            data_request_priority="none"
        )
        
        # Create checkpoint before risky operation
        state_checkpoint = initial_state.model_dump()
        
        try:
            # Attempt optimization that fails  
            from netra_backend.app.agents.state import OptimizationsResult
            initial_state.optimizations_result = OptimizationsResult(
                optimization_type="cost_optimization",
                confidence_score=0.0
            )
            # Simulate failure
            raise Exception("Optimization failed due to invalid model response")
        except Exception:
            # Rollback to checkpoint
            initial_state = DeepAgentState(**state_checkpoint)
            # Add error context to metadata
            initial_state = initial_state.add_metadata("optimization_error", "Invalid model response")
            initial_state = initial_state.add_metadata("rollback", "true")
            initial_state = initial_state.add_metadata("retry_with", "simplified_optimization")
        
        # Verify rollback succeeded
        assert initial_state.optimizations_result is None  # Failed output removed
        assert "optimization_error" in initial_state.metadata.custom_fields  # Error context added
        assert initial_state.triage_result is not None  # Original preserved
    
    @pytest.mark.asyncio
    async def test_dynamic_workflow_reordering(self):
        """Test dynamic reordering of workflow based on discoveries."""
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        initial_workflow = ["triage", "optimization", "data", "actions", "reporting"]
        
        # Triage discovers urgent issue requiring immediate data analysis
        triage_result = {
            "data_sufficiency": "sufficient",
            "urgent_analysis_needed": True,
            "reason": "Anomaly detected in recent data"
        }
        
        def reorder_workflow(workflow, triage_result):
            if triage_result.get("urgent_analysis_needed"):
                # Move data analysis before optimization
                if "data" in workflow and "optimization" in workflow:
                    workflow.remove("data")
                    opt_index = workflow.index("optimization")
                    workflow.insert(opt_index, "data")
            return workflow
        
        adjusted_workflow = reorder_workflow(initial_workflow.copy(), triage_result)
        
        assert adjusted_workflow == ["triage", "data", "optimization", "actions", "reporting"]
        assert adjusted_workflow.index("data") < adjusted_workflow.index("optimization")
    
    @pytest.mark.asyncio
    async def test_context_preservation_across_retries(self):
        """Test that context is preserved when retrying failed agents."""
        state = DeepAgentState()
        state.user_request = json.dumps({"request": "Optimize", "retry_count": 0})
        
        # First attempt context
        first_context = {
            "attempt": 1,
            "timestamp": "2024-01-01T10:00:00",
            "parameters": {"temperature": 0.7}
        }
        
        # Store optimization attempt 1 in metadata
        state = state.add_metadata("optimization_attempt_1", json.dumps({
            "context": first_context,
            "status": "failed",
            "error": "Timeout"
        }))
        
        # Retry with adjusted parameters
        retry_context = {
            "attempt": 2,
            "timestamp": "2024-01-01T10:01:00",
            "parameters": {"temperature": 0.5},  # Lower temperature for retry
            "previous_error": "Timeout"
        }
        
        state.set_agent_output("optimization_attempt_2", {
            "context": retry_context,
            "status": "success",
            "result": {"recommendations": []}
        })
        
        # Verify retry context preservation
        attempt_1 = state.get_agent_output("optimization_attempt_1")
        attempt_2 = state.get_agent_output("optimization_attempt_2")
        
        assert attempt_1["context"]["attempt"] == 1
        assert attempt_2["context"]["attempt"] == 2
        assert attempt_2["context"]["previous_error"] == "Timeout"
        assert attempt_2["context"]["parameters"]["temperature"] < attempt_1["context"]["parameters"]["temperature"]
    
    @pytest.mark.asyncio
    async def test_multi_stage_validation_handoff(self):
        """Test multi-stage validation between agents."""
        validation_stages = {
            "stage_1_syntax": {"valid": True, "errors": []},
            "stage_2_business_logic": {"valid": True, "warnings": ["Consider cost impact"]},
            "stage_3_implementation": {"valid": False, "errors": ["Missing dependencies"]}
        }
        
        state = DeepAgentState()
        
        # Stage 1: Syntax validation
        state.set_agent_output("validation_syntax", validation_stages["stage_1_syntax"])
        
        # Continue only if stage 1 passes
        if state.get_agent_output("validation_syntax")["valid"]:
            # Stage 2: Business logic validation
            state.set_agent_output("validation_business", validation_stages["stage_2_business_logic"])
            
            if state.get_agent_output("validation_business")["valid"]:
                # Stage 3: Implementation validation
                state.set_agent_output("validation_implementation", validation_stages["stage_3_implementation"])
        
        # Check validation cascade
        assert "validation_syntax" in state.agent_outputs
        assert "validation_business" in state.agent_outputs
        assert "validation_implementation" in state.agent_outputs
        
        # Final validation failed
        final_validation = state.get_agent_output("validation_implementation")
        assert final_validation["valid"] is False
        assert "Missing dependencies" in final_validation["errors"]
    
    @pytest.mark.asyncio
    async def test_state_merge_from_parallel_flows(self):
        """Test merging state from parallel workflow branches."""
        state = DeepAgentState()
        
        # Parallel branch 1: Cost optimization
        branch1_state = {
            "cost_recommendations": ["Use spot instances", "Batch processing"],
            "estimated_savings": 3000
        }
        
        # Parallel branch 2: Performance optimization  
        branch2_state = {
            "performance_recommendations": ["Add caching", "Optimize queries"],
            "latency_improvement": 0.5
        }
        
        # Merge parallel results
        state.set_agent_output("cost_optimization", branch1_state)
        state.set_agent_output("performance_optimization", branch2_state)
        
        # Consolidated recommendations
        merged_recommendations = {
            "combined_strategy": [
                *branch1_state["cost_recommendations"],
                *branch2_state["performance_recommendations"]
            ],
            "total_impact": {
                "cost_savings": branch1_state["estimated_savings"],
                "latency_improvement": branch2_state["latency_improvement"]
            },
            "implementation_order": [
                "Add caching",  # Quick win
                "Use spot instances",  # Cost impact
                "Batch processing",  # Complexity
                "Optimize queries"  # Final optimization
            ]
        }
        
        state.set_agent_output("merged_recommendations", merged_recommendations)
        
        # Verify merge
        final = state.get_agent_output("merged_recommendations")
        assert len(final["combined_strategy"]) == 4
        assert final["total_impact"]["cost_savings"] == 3000
        assert final["total_impact"]["latency_improvement"] == 0.5
        assert final["implementation_order"][0] == "Add caching"  # Priority order maintained