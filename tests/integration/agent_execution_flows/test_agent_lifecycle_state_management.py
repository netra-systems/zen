"""
Test Agent Lifecycle State Management Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure proper agent lifecycle management from creation to cleanup
- Value Impact: Prevents resource leaks and ensures clean agent termination
- Strategic Impact: Enables reliable long-running platform operations with proper resource management

Tests the complete agent lifecycle state management including creation, initialization,
execution phases, termination, cleanup, and resource management.
"""

import asyncio
import pytest
from typing import Dict, Any, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import time
from enum import Enum

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentLifecycleManager
from netra_backend.app.agents.agent_state_tracker import AgentStateTracker


class AgentLifecyclePhase(Enum):
    """Agent lifecycle phases for testing."""
    CREATED = "created"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PROCESSING = "processing"
    COMPLETING = "completing"
    TERMINATED = "terminated"
    CLEANUP = "cleanup"
    DESTROYED = "destroyed"


class TestAgentLifecycleStateManagement(BaseIntegrationTest):
    """Integration tests for agent lifecycle state management."""

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_complete_agent_lifecycle_management(self, real_services_fixture):
        """Test complete agent lifecycle from creation to destruction."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="lifecycle_user_1300",
            thread_id="thread_1600",
            session_id="session_1900",
            workspace_id="lifecycle_workspace_1200"
        )
        
        lifecycle_manager = AgentLifecycleManager(
            user_context=user_context,
            resource_tracking=True,
            cleanup_automation=True,
            lifecycle_monitoring=True
        )
        
        state_tracker = AgentStateTracker(
            user_context=user_context,
            lifecycle_integration=True
        )
        
        # Track lifecycle events
        lifecycle_events = []
        resource_allocations = {}
        
        def lifecycle_event_handler(event_type: str, agent_id: str, details: Dict[str, Any]):
            lifecycle_events.append({
                "timestamp": time.time(),
                "event_type": event_type,
                "agent_id": agent_id,
                "details": details
            })
        
        lifecycle_manager.add_event_handler(lifecycle_event_handler)
        
        # Act - Execute complete lifecycle
        # Phase 1: Creation and Initialization
        agent_creation_request = {
            "agent_type": "lifecycle_test_agent",
            "initial_configuration": {
                "analysis_type": "cost_optimization",
                "data_sources": ["aws", "azure"],
                "optimization_goals": ["reduce_cost", "maintain_performance"]
            },
            "resource_requirements": {
                "memory_mb": 256,
                "cpu_cores": 1,
                "storage_mb": 100
            }
        }
        
        created_agent = await lifecycle_manager.create_agent(
            agent_creation_request=agent_creation_request,
            user_context=user_context
        )
        
        assert created_agent is not None
        assert created_agent.lifecycle_phase == AgentLifecyclePhase.CREATED.value
        
        # Phase 2: Initialization
        initialization_data = {
            "configuration_validated": True,
            "resources_allocated": True,
            "dependencies_resolved": True,
            "initialization_timestamp": time.time()
        }
        
        initialized_agent = await lifecycle_manager.initialize_agent(
            agent=created_agent,
            initialization_data=initialization_data
        )
        
        assert initialized_agent.lifecycle_phase == AgentLifecyclePhase.INITIALIZING.value
        
        # Phase 3: Activation
        activated_agent = await lifecycle_manager.activate_agent(
            agent=initialized_agent,
            activation_context={"ready_for_processing": True}
        )
        
        assert activated_agent.lifecycle_phase == AgentLifecyclePhase.ACTIVE.value
        
        # Phase 4: Processing (simulate work phases)
        work_phases = [
            {"phase": "data_collection", "duration": 0.1, "progress": 0.3},
            {"phase": "data_analysis", "duration": 0.15, "progress": 0.6},
            {"phase": "optimization_planning", "duration": 0.1, "progress": 0.9}
        ]
        
        for phase in work_phases:
            await lifecycle_manager.transition_agent_phase(
                agent=activated_agent,
                from_phase=activated_agent.lifecycle_phase,
                to_phase=AgentLifecyclePhase.PROCESSING.value,
                phase_data=phase
            )
            
            # Simulate work
            await asyncio.sleep(phase["duration"])
            
            # Update progress
            await lifecycle_manager.update_agent_progress(
                agent=activated_agent,
                progress_data={
                    "current_phase": phase["phase"],
                    "progress_percentage": phase["progress"],
                    "phase_complete": True
                }
            )
        
        # Phase 5: Completion
        completion_result = {
            "optimization_recommendations": [
                {"type": "rightsizing", "savings": 8000},
                {"type": "reserved_instances", "savings": 5000}
            ],
            "total_savings": 13000,
            "completion_timestamp": time.time(),
            "success": True
        }
        
        completed_agent = await lifecycle_manager.complete_agent_execution(
            agent=activated_agent,
            completion_result=completion_result
        )
        
        assert completed_agent.lifecycle_phase == AgentLifecyclePhase.COMPLETING.value
        
        # Phase 6: Termination
        termination_result = await lifecycle_manager.terminate_agent(
            agent=completed_agent,
            termination_reason="normal_completion",
            final_state_snapshot=True
        )
        
        assert termination_result["termination_successful"] is True
        assert completed_agent.lifecycle_phase == AgentLifecyclePhase.TERMINATED.value
        
        # Phase 7: Cleanup and Destruction
        cleanup_result = await lifecycle_manager.cleanup_and_destroy_agent(
            agent=completed_agent,
            cleanup_resources=True,
            cleanup_state=True,
            cleanup_persistence=True
        )
        
        assert cleanup_result["cleanup_successful"] is True
        assert cleanup_result["resources_released"] is True
        assert cleanup_result["state_cleaned"] is True
        
        # Assert - Verify complete lifecycle management
        # Verify all lifecycle phases were recorded
        phase_events = [event for event in lifecycle_events if event["event_type"] == "phase_transition"]
        assert len(phase_events) >= 6  # Should have multiple phase transitions
        
        # Verify resource management
        resource_events = [event for event in lifecycle_events if event["event_type"] == "resource_allocation"]
        cleanup_events = [event for event in lifecycle_events if event["event_type"] == "resource_cleanup"]
        
        # Should have allocated and cleaned up resources
        assert len(resource_events) > 0
        assert len(cleanup_events) > 0
        
        # Verify agent no longer exists in active state
        active_agents = await lifecycle_manager.get_active_agents(user_context)
        agent_ids = [agent.agent_id for agent in active_agents]
        assert created_agent.agent_id not in agent_ids

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_agent_lifecycle_error_handling_and_recovery(self, real_services_fixture):
        """Test agent lifecycle error handling and recovery scenarios."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="error_lifecycle_user_1301",
            thread_id="thread_1601",
            session_id="session_1901",
            workspace_id="error_lifecycle_workspace_1201"
        )
        
        lifecycle_manager = AgentLifecycleManager(
            user_context=user_context,
            error_recovery_enabled=True,
            automatic_retry=True,
            max_retry_attempts=3
        )
        
        # Create agent that will encounter errors
        error_prone_agent = await lifecycle_manager.create_agent(
            agent_creation_request={
                "agent_type": "error_prone_agent",
                "initial_configuration": {"simulate_errors": True}
            },
            user_context=user_context
        )
        
        error_scenarios = []
        recovery_results = []
        
        # Scenario 1: Initialization failure and recovery
        try:
            # Simulate initialization failure
            await lifecycle_manager.initialize_agent(
                agent=error_prone_agent,
                initialization_data={"force_initialization_failure": True}
            )
        except Exception as e:
            error_scenarios.append({
                "phase": "initialization",
                "error_type": str(type(e).__name__),
                "error_message": str(e)
            })
            
            # Attempt recovery
            recovery_result = await lifecycle_manager.recover_agent_from_error(
                agent=error_prone_agent,
                error_phase="initialization",
                recovery_strategy="retry_with_fallback_config"
            )
            
            recovery_results.append({
                "phase": "initialization",
                "recovery_successful": recovery_result.get("recovery_successful", False),
                "fallback_applied": recovery_result.get("fallback_applied", False)
            })
        
        # Scenario 2: Execution phase failure
        if error_prone_agent.lifecycle_phase in ["active", "processing"]:
            try:
                await lifecycle_manager.transition_agent_phase(
                    agent=error_prone_agent,
                    from_phase=error_prone_agent.lifecycle_phase,
                    to_phase=AgentLifecyclePhase.PROCESSING.value,
                    phase_data={"simulate_processing_failure": True}
                )
            except Exception as e:
                error_scenarios.append({
                    "phase": "processing",
                    "error_type": str(type(e).__name__),
                    "error_message": str(e)
                })
                
                # Attempt recovery
                recovery_result = await lifecycle_manager.recover_agent_from_error(
                    agent=error_prone_agent,
                    error_phase="processing",
                    recovery_strategy="rollback_to_stable_state"
                )
                
                recovery_results.append({
                    "phase": "processing",
                    "recovery_successful": recovery_result.get("recovery_successful", False),
                    "rollback_applied": recovery_result.get("rollback_applied", False)
                })
        
        # Scenario 3: Termination failure (zombie agent prevention)
        try:
            await lifecycle_manager.terminate_agent(
                agent=error_prone_agent,
                termination_reason="force_termination_failure",
                force_termination_failure=True
            )
        except Exception as e:
            error_scenarios.append({
                "phase": "termination",
                "error_type": str(type(e).__name__),
                "error_message": str(e)
            })
            
            # Force termination recovery (prevent zombie agents)
            recovery_result = await lifecycle_manager.force_terminate_agent(
                agent=error_prone_agent,
                recovery_strategy="force_kill_with_cleanup"
            )
            
            recovery_results.append({
                "phase": "termination",
                "recovery_successful": recovery_result.get("termination_forced", False),
                "cleanup_completed": recovery_result.get("cleanup_completed", False)
            })
        
        # Assert - Verify error handling and recovery
        assert len(error_scenarios) > 0  # Should have encountered errors
        assert len(recovery_results) > 0  # Should have attempted recovery
        
        # Verify recovery attempts were made
        for recovery in recovery_results:
            if recovery["phase"] == "initialization":
                assert recovery["recovery_successful"] is True or recovery["fallback_applied"] is True
            elif recovery["phase"] == "processing":
                assert recovery["recovery_successful"] is True or recovery["rollback_applied"] is True
            elif recovery["phase"] == "termination":
                assert recovery["recovery_successful"] is True and recovery["cleanup_completed"] is True
        
        # Verify no zombie agents remain
        active_agents = await lifecycle_manager.get_active_agents(user_context)
        zombie_agents = [agent for agent in active_agents if agent.lifecycle_phase == "error" and agent.agent_id == error_prone_agent.agent_id]
        assert len(zombie_agents) == 0

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_multi_agent_lifecycle_coordination(self, real_services_fixture):
        """Test lifecycle management coordination across multiple agents."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="multi_agent_user_1302",
            thread_id="thread_1602",
            session_id="session_1902",
            workspace_id="multi_agent_workspace_1202"
        )
        
        lifecycle_manager = AgentLifecycleManager(
            user_context=user_context,
            multi_agent_coordination=True,
            resource_pooling=True,
            dependency_management=True
        )
        
        # Create multiple interdependent agents
        agent_specs = [
            {
                "agent_type": "data_collector",
                "dependencies": [],
                "provides": ["collected_data"],
                "resource_requirements": {"memory_mb": 128, "priority": "high"}
            },
            {
                "agent_type": "data_analyzer",
                "dependencies": ["collected_data"],
                "provides": ["analysis_results"],
                "resource_requirements": {"memory_mb": 256, "priority": "medium"}
            },
            {
                "agent_type": "optimizer",
                "dependencies": ["analysis_results"],
                "provides": ["optimization_recommendations"],
                "resource_requirements": {"memory_mb": 512, "priority": "medium"}
            },
            {
                "agent_type": "reporter",
                "dependencies": ["optimization_recommendations"],
                "provides": ["final_report"],
                "resource_requirements": {"memory_mb": 128, "priority": "low"}
            }
        ]
        
        # Create all agents
        created_agents = []
        for spec in agent_specs:
            agent = await lifecycle_manager.create_agent(
                agent_creation_request=spec,
                user_context=user_context
            )
            created_agents.append(agent)
        
        # Coordinate lifecycle transitions based on dependencies
        lifecycle_coordination_results = []
        
        # Phase 1: Initialize agents in dependency order
        initialization_order = await lifecycle_manager.calculate_initialization_order(created_agents)
        
        for agent in initialization_order:
            init_result = await lifecycle_manager.initialize_agent(
                agent=agent,
                initialization_data={"dependency_order_respected": True}
            )
            
            lifecycle_coordination_results.append({
                "agent_type": agent.agent_type,
                "phase": "initialization",
                "order": len(lifecycle_coordination_results),
                "success": init_result.lifecycle_phase == AgentLifecyclePhase.INITIALIZING.value
            })
        
        # Phase 2: Coordinate activation with dependency checking
        for agent in initialization_order:
            # Check if dependencies are ready
            dependencies_ready = await lifecycle_manager.check_agent_dependencies(agent, created_agents)
            
            if dependencies_ready:
                activation_result = await lifecycle_manager.activate_agent(
                    agent=agent,
                    activation_context={"dependencies_verified": True}
                )
                
                lifecycle_coordination_results.append({
                    "agent_type": agent.agent_type,
                    "phase": "activation",
                    "dependencies_ready": dependencies_ready,
                    "success": activation_result.lifecycle_phase == AgentLifecyclePhase.ACTIVE.value
                })
        
        # Phase 3: Execute agents in pipeline with handoffs
        execution_pipeline = []
        
        for agent in initialization_order:
            if agent.lifecycle_phase == AgentLifecyclePhase.ACTIVE.value:
                # Execute agent
                execution_start = time.time()
                
                await lifecycle_manager.transition_agent_phase(
                    agent=agent,
                    from_phase=AgentLifecyclePhase.ACTIVE.value,
                    to_phase=AgentLifecyclePhase.PROCESSING.value,
                    phase_data={"pipeline_position": len(execution_pipeline)}
                )
                
                # Simulate work
                await asyncio.sleep(0.1)
                
                # Complete execution and prepare handoff
                execution_result = {
                    "agent_type": agent.agent_type,
                    "provides": agent_specs[created_agents.index(agent)]["provides"],
                    "execution_time": time.time() - execution_start,
                    "output_data": f"{agent.agent_type}_output_data"
                }
                
                # Notify dependent agents
                await lifecycle_manager.notify_dependent_agents(
                    completed_agent=agent,
                    execution_result=execution_result,
                    all_agents=created_agents
                )
                
                execution_pipeline.append(execution_result)
        
        # Phase 4: Coordinate shutdown in reverse dependency order
        shutdown_order = list(reversed(initialization_order))
        shutdown_results = []
        
        for agent in shutdown_order:
            # Complete agent
            completion_result = await lifecycle_manager.complete_agent_execution(
                agent=agent,
                completion_result={"pipeline_execution_complete": True}
            )
            
            # Terminate agent
            termination_result = await lifecycle_manager.terminate_agent(
                agent=agent,
                termination_reason="pipeline_complete"
            )
            
            shutdown_results.append({
                "agent_type": agent.agent_type,
                "completion_success": completion_result.lifecycle_phase == AgentLifecyclePhase.COMPLETING.value,
                "termination_success": termination_result["termination_successful"]
            })
        
        # Assert - Verify multi-agent lifecycle coordination
        # Verify initialization order respected dependencies
        data_collector_init = next(r for r in lifecycle_coordination_results if r["agent_type"] == "data_collector" and r["phase"] == "initialization")
        reporter_init = next(r for r in lifecycle_coordination_results if r["agent_type"] == "reporter" and r["phase"] == "initialization")
        
        assert data_collector_init["order"] < reporter_init["order"]  # Data collector should initialize before reporter
        
        # Verify all agents were successfully coordinated
        activation_results = [r for r in lifecycle_coordination_results if r["phase"] == "activation"]
        successful_activations = [r for r in activation_results if r["success"] and r["dependencies_ready"]]
        
        assert len(successful_activations) == len(created_agents)  # All agents should activate successfully
        
        # Verify execution pipeline completed
        assert len(execution_pipeline) == len(created_agents)
        
        # Verify data flow through pipeline
        provided_outputs = [result["provides"][0] for result in execution_pipeline if result["provides"]]
        expected_outputs = ["collected_data", "analysis_results", "optimization_recommendations", "final_report"]
        
        for expected_output in expected_outputs:
            assert expected_output in provided_outputs
        
        # Verify clean shutdown
        assert all(result["completion_success"] and result["termination_success"] for result in shutdown_results)
        
        # Verify no agents remain active
        remaining_active_agents = await lifecycle_manager.get_active_agents(user_context)
        remaining_agent_ids = [agent.agent_id for agent in remaining_active_agents]
        created_agent_ids = [agent.agent_id for agent in created_agents]
        
        for agent_id in created_agent_ids:
            assert agent_id not in remaining_agent_ids

    @pytest.mark.integration
    @pytest.mark.agent_state_management
    async def test_agent_lifecycle_resource_management(self, real_services_fixture):
        """Test resource management throughout agent lifecycle."""
        # Arrange
        user_context = UserExecutionContext(
            user_id="resource_mgmt_user_1303",
            thread_id="thread_1603",
            session_id="session_1903",
            workspace_id="resource_mgmt_workspace_1203"
        )
        
        lifecycle_manager = AgentLifecycleManager(
            user_context=user_context,
            resource_management=True,
            resource_limits={
                "total_memory_mb": 1024,
                "total_cpu_cores": 4,
                "max_concurrent_agents": 5
            },
            resource_monitoring=True
        )
        
        # Track resource usage throughout lifecycle
        resource_tracking = {
            "allocations": [],
            "deallocations": [],
            "peak_usage": {"memory_mb": 0, "cpu_cores": 0},
            "resource_violations": []
        }
        
        def resource_monitor_callback(event_type: str, resource_data: Dict[str, Any]):
            if event_type == "resource_allocated":
                resource_tracking["allocations"].append(resource_data)
            elif event_type == "resource_deallocated":
                resource_tracking["deallocations"].append(resource_data)
            elif event_type == "resource_usage_update":
                current_memory = resource_data.get("memory_mb", 0)
                current_cpu = resource_data.get("cpu_cores", 0)
                
                if current_memory > resource_tracking["peak_usage"]["memory_mb"]:
                    resource_tracking["peak_usage"]["memory_mb"] = current_memory
                    
                if current_cpu > resource_tracking["peak_usage"]["cpu_cores"]:
                    resource_tracking["peak_usage"]["cpu_cores"] = current_cpu
            
            elif event_type == "resource_limit_violation":
                resource_tracking["resource_violations"].append(resource_data)
        
        lifecycle_manager.add_resource_monitor(resource_monitor_callback)
        
        # Create agents with varying resource requirements
        agent_configs = [
            {"agent_type": "light_agent", "memory_mb": 64, "cpu_cores": 0.5},
            {"agent_type": "medium_agent", "memory_mb": 256, "cpu_cores": 1.0},
            {"agent_type": "heavy_agent", "memory_mb": 512, "cpu_cores": 2.0},
            {"agent_type": "resource_intensive_agent", "memory_mb": 400, "cpu_cores": 1.5}
        ]
        
        created_agents = []
        
        # Act - Create and manage agents with resource tracking
        for config in agent_configs:
            try:
                agent = await lifecycle_manager.create_agent_with_resources(
                    agent_creation_request={
                        "agent_type": config["agent_type"],
                        "resource_requirements": {
                            "memory_mb": config["memory_mb"],
                            "cpu_cores": config["cpu_cores"]
                        }
                    },
                    user_context=user_context,
                    resource_verification=True
                )
                
                if agent:
                    created_agents.append(agent)
                    
                    # Initialize with resource allocation
                    await lifecycle_manager.initialize_agent_with_resources(
                        agent=agent,
                        resource_allocation_verified=True
                    )
                    
                    # Activate and monitor resource usage
                    await lifecycle_manager.activate_agent(agent)
                    
                    # Simulate some processing load
                    await asyncio.sleep(0.1)
                    
                    # Monitor resource usage during processing
                    usage = await lifecycle_manager.get_agent_resource_usage(agent)
                    
                    if usage:
                        resource_monitor_callback("resource_usage_update", usage)
                    
            except Exception as e:
                # Expected if resource limits are exceeded
                if "resource" in str(e).lower():
                    resource_tracking["resource_violations"].append({
                        "agent_type": config["agent_type"],
                        "error": str(e),
                        "requested_memory": config["memory_mb"],
                        "requested_cpu": config["cpu_cores"]
                    })
        
        # Clean up agents and verify resource deallocation
        for agent in created_agents:
            await lifecycle_manager.terminate_agent(
                agent=agent,
                termination_reason="test_complete"
            )
            
            cleanup_result = await lifecycle_manager.cleanup_and_destroy_agent(
                agent=agent,
                cleanup_resources=True
            )
            
            if cleanup_result.get("resources_released"):
                resource_monitor_callback("resource_deallocated", {
                    "agent_id": agent.agent_id,
                    "memory_freed": agent.resource_requirements.get("memory_mb", 0),
                    "cpu_freed": agent.resource_requirements.get("cpu_cores", 0)
                })
        
        # Assert - Verify resource management
        # Verify resource allocations were tracked
        assert len(resource_tracking["allocations"]) > 0
        
        # Verify peak usage stayed within limits
        assert resource_tracking["peak_usage"]["memory_mb"] <= 1024  # Within total limit
        assert resource_tracking["peak_usage"]["cpu_cores"] <= 4    # Within total limit
        
        # Verify resource cleanup
        total_allocated_memory = sum(alloc.get("memory_mb", 0) for alloc in resource_tracking["allocations"])
        total_deallocated_memory = sum(dealloc.get("memory_freed", 0) for dealloc in resource_tracking["deallocations"])
        
        # Should deallocate approximately what was allocated (within small margin for tracking overhead)
        memory_balance_ratio = total_deallocated_memory / max(total_allocated_memory, 1)
        assert 0.9 <= memory_balance_ratio <= 1.1  # Within 10% (accounting for tracking differences)
        
        # Verify resource limit enforcement
        # Should either create agents within limits or properly reject with resource violations
        total_created_agents = len(created_agents)
        total_violations = len(resource_tracking["resource_violations"])
        
        # Should have enforced limits (either by creating within limits or rejecting excess)
        assert (total_created_agents > 0) or (total_violations > 0)  # Should have some result
        
        # If violations occurred, they should be properly documented
        if total_violations > 0:
            for violation in resource_tracking["resource_violations"]:
                assert "agent_type" in violation
                assert "error" in violation
                assert "resource" in violation["error"].lower()
        
        # Verify no agents remain with allocated resources
        final_active_agents = await lifecycle_manager.get_active_agents(user_context)
        assert len(final_active_agents) == 0  # All should be cleaned up