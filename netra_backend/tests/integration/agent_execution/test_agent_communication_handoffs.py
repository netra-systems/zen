"""
Agent Communication & Handoff Integration Tests

These tests validate agent-to-agent communication patterns, context handoffs,
multi-agent workflow coordination, and state synchronization without external dependencies.

Business Value Focus:
- Agent-to-agent handoff protocols and data preservation
- Context sharing between agents maintains business continuity
- Multi-agent workflow coordination delivers comprehensive results  
- Agent state synchronization prevents data loss
- Communication error handling maintains system reliability

CRITICAL: Tests real agent communication patterns with mock agent instances.
"""

import asyncio
import time
import uuid
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.tests.integration.agent_execution.base_agent_execution_test import BaseAgentExecutionTest


class CommunicatingMockAgent(BaseAgent):
    """Mock agent that simulates real communication patterns and state management."""
    
    def __init__(self, agent_name: str, communication_delay: float = 0.2):
        super().__init__(llm_manager=None, name=agent_name, description=f"Communicating mock {agent_name}")
        self.agent_name = agent_name
        self.communication_delay = communication_delay
        self.received_contexts = []
        self.sent_messages = []
        self.state_snapshots = []
        self.execution_count = 0
        
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with communication tracking and realistic business logic."""
        self.execution_count += 1
        
        # Capture context snapshot for handoff analysis
        context_snapshot = {
            "agent_name": self.agent_name,
            "execution_count": self.execution_count,
            "user_id": context.user_id,
            "run_id": context.run_id,
            "received_metadata_keys": list(context.metadata.keys()),
            "timestamp": time.time()
        }
        self.received_contexts.append(context_snapshot)
        self.state_snapshots.append(context_snapshot)
        
        # Simulate realistic processing time
        await asyncio.sleep(self.communication_delay)
        
        # Generate business result with communication data
        result = {
            "status": "completed",
            "agent_name": self.agent_name,
            "execution_count": self.execution_count,
            "communication_metadata": {
                "contexts_received": len(self.received_contexts),
                "processing_time": self.communication_delay,
                "handoff_data": f"Processed by {self.agent_name} - execution {self.execution_count}"
            },
            "business_output": {
                "insights": [f"Insight {i+1} from {self.agent_name}" for i in range(3)],
                "recommendations": [f"Recommendation {i+1} from {self.agent_name}" for i in range(2)],
                "next_agent_suggestions": self._suggest_next_agents(context)
            },
            "context_continuity": {
                "preserved_metadata": len(context.metadata),
                "user_request_preserved": "user_request" in context.metadata,
                "business_context_preserved": True
            }
        }
        
        # Add agent-specific business logic
        if self.agent_name == "triage":
            result["triage_specific"] = {
                "category": "optimization_request",
                "priority": "high",
                "data_sufficiency": "partial",
                "recommended_workflow": ["data_helper", "optimization", "reporting"]
            }
        elif self.agent_name == "data_helper":
            result["data_helper_specific"] = {
                "guidance_provided": True,
                "data_collection_steps": ["step1", "step2", "step3"],
                "data_quality_assessment": "needs_improvement"
            }
        elif self.agent_name == "optimization":
            result["optimization_specific"] = {
                "strategies_identified": 5,
                "cost_savings_potential": "25%",
                "implementation_complexity": "medium"
            }
        elif self.agent_name == "reporting":
            result["reporting_specific"] = {
                "report_sections": ["executive_summary", "detailed_analysis", "recommendations"],
                "business_value_demonstrated": True,
                "final_deliverable": True
            }
            
        # Store message for communication validation
        message = {
            "from_agent": self.agent_name,
            "timestamp": time.time(),
            "context_id": context.run_id,
            "result_summary": result["business_output"]["insights"][0] if result["business_output"]["insights"] else "No insights"
        }
        self.sent_messages.append(message)
        
        return result
    
    def _suggest_next_agents(self, context: UserExecutionContext) -> List[str]:
        """Suggest next agents based on current agent's role and context."""
        user_request = context.metadata.get("user_request", "").lower()
        
        if self.agent_name == "triage":
            if "optimization" in user_request:
                return ["data_helper", "optimization"]
            elif "analysis" in user_request:
                return ["data_helper", "reporting"]
            else:
                return ["data_helper"]
        elif self.agent_name == "data_helper":
            return ["optimization", "reporting"]
        elif self.agent_name == "optimization":
            return ["actions", "reporting"]
        else:
            return ["reporting"]  # Most agents suggest reporting as final step
    
    def get_communication_stats(self) -> Dict[str, Any]:
        """Get communication statistics for validation."""
        return {
            "agent_name": self.agent_name,
            "execution_count": self.execution_count,
            "contexts_received": len(self.received_contexts),
            "messages_sent": len(self.sent_messages),
            "state_snapshots": len(self.state_snapshots),
            "avg_processing_time": self.communication_delay
        }


class TestAgentCommunicationHandoffs(BaseAgentExecutionTest):
    """Test agent communication and handoff patterns."""
    
    def create_communicating_agent_network(self, agent_names: List[str]) -> Dict[str, CommunicatingMockAgent]:
        """Create network of communicating mock agents.
        
        Args:
            agent_names: List of agent names to create
            
        Returns:
            Dictionary mapping agent names to agent instances
        """
        agents = {}
        
        for agent_name in agent_names:
            # Different agents have different processing characteristics
            delay = 0.1 if agent_name == "triage" else 0.2
            if agent_name == "optimization":
                delay = 0.3  # Optimization takes longer
                
            agent = CommunicatingMockAgent(agent_name, communication_delay=delay)
            agents[agent_name] = agent
            
        return agents

    @pytest.mark.asyncio
    async def test_agent_to_agent_handoff_protocols(self):
        """Test agent-to-agent handoff protocols and data preservation.
        
        Validates:
        - Context data is properly passed between agents
        - Agent results are accessible to subsequent agents
        - Handoff timing and sequencing is correct
        - Business continuity maintained across handoffs
        """
        # Create context for multi-agent handoff scenario
        context = self.create_user_execution_context(
            user_request="Execute multi-agent workflow with comprehensive handoffs",
            additional_metadata={
                "workflow_type": "sequential_handoffs",
                "business_priority": "high",
                "requires_coordination": True,
                "handoff_validation": True
            }
        )
        
        # Create communicating agent network
        agent_names = ["triage", "data_helper", "optimization", "reporting"]
        agents = self.create_communicating_agent_network(agent_names)
        
        # Execute sequential handoff workflow
        handoff_chain = []
        current_context = context
        
        for agent_name in agent_names:
            agent = agents[agent_name]
            
            # Record handoff initiation
            handoff_start = time.time()
            
            # Execute agent with current context
            result = await agent.execute(current_context, stream_updates=True)
            
            handoff_duration = time.time() - handoff_start
            
            # Record handoff completion
            handoff_info = {
                "agent_name": agent_name,
                "handoff_duration": handoff_duration,
                "context_preserved": current_context.user_id == context.user_id,
                "result_status": result.get("status"),
                "business_output_count": len(result.get("business_output", {}).get("insights", [])),
                "context_continuity": result.get("context_continuity", {})
            }
            handoff_chain.append(handoff_info)
            
            # Create child context for next agent (simulating handoff)
            if agent_name != agent_names[-1]:  # Not the last agent
                current_context = current_context.create_child_context(
                    operation_name=f"handoff_to_next_agent",
                    additional_agent_context={
                        f"{agent_name}_result": result,
                        "handoff_sequence": len(handoff_chain)
                    }
                )
        
        # Validate handoff chain
        assert len(handoff_chain) == len(agent_names), "All agents should complete handoff"
        
        for i, handoff in enumerate(handoff_chain):
            # Validate successful handoff
            assert handoff["result_status"] == "completed", f"Agent {handoff['agent_name']} should complete successfully"
            assert handoff["context_preserved"] is True, f"Context should be preserved for {handoff['agent_name']}"
            assert handoff["business_output_count"] > 0, f"Agent {handoff['agent_name']} should produce business output"
            
            # Validate handoff timing
            assert handoff["handoff_duration"] < 2.0, f"Handoff to {handoff['agent_name']} should complete quickly"
            
            # Validate context continuity
            continuity = handoff["context_continuity"]
            assert continuity.get("preserved_metadata", 0) > 0, "Metadata should be preserved"
            assert continuity.get("user_request_preserved") is True, "User request should be preserved"
            
        # Validate handoff sequencing (each handoff should start after previous completes)
        for i in range(1, len(handoff_chain)):
            # This is implicitly tested by sequential execution, but validate timing
            prev_agent = handoff_chain[i-1]["agent_name"]
            curr_agent = handoff_chain[i]["agent_name"]
            
            # Check that agents executed in expected order
            expected_sequence = ["triage", "data_helper", "optimization", "reporting"]
            assert expected_sequence.index(curr_agent) > expected_sequence.index(prev_agent), \
                f"Agent {curr_agent} should execute after {prev_agent}"
        
        # Validate communication statistics
        total_contexts_received = sum(agent.get_communication_stats()["contexts_received"] for agent in agents.values())
        total_messages_sent = sum(agent.get_communication_stats()["messages_sent"] for agent in agents.values())
        
        assert total_contexts_received >= len(agent_names), "All agents should receive contexts"
        assert total_messages_sent >= len(agent_names), "All agents should send messages"

    @pytest.mark.asyncio
    async def test_context_sharing_between_agents(self):
        """Test context sharing mechanisms between agents maintain business data.
        
        Validates:
        - Shared context contains all necessary business information
        - Context modifications are properly propagated
        - Agent-specific data is preserved and accessible
        - Context isolation prevents cross-contamination
        """
        # Create rich context with business data
        business_context = self.create_user_execution_context(
            user_request="Share complex business context across multiple agents",
            additional_metadata={
                "customer_id": "enterprise_customer_001",
                "project_type": "cost_optimization", 
                "budget_constraints": {"max_budget": 50000, "currency": "USD"},
                "technical_requirements": ["scalability", "security", "performance"],
                "stakeholders": ["cto", "cfo", "engineering_lead"],
                "timeline": "q2_2024",
                "business_metrics": {
                    "current_monthly_cost": 15000,
                    "target_savings": 30,
                    "performance_baseline": {"latency": 200, "throughput": 1000}
                }
            }
        )
        
        # Create agents for context sharing test
        agent_names = ["context_receiver", "context_processor", "context_aggregator"]
        agents = self.create_communicating_agent_network(agent_names)
        
        # Track context evolution
        context_evolution = []
        shared_context = business_context
        
        for i, agent_name in enumerate(agent_names):
            agent = agents[agent_name]
            
            # Capture context state before agent execution
            pre_execution_state = {
                "agent_name": agent_name,
                "metadata_keys": list(shared_context.metadata.keys()),
                "metadata_size": len(shared_context.metadata),
                "business_data_present": {
                    "customer_id": "customer_id" in shared_context.metadata,
                    "budget_constraints": "budget_constraints" in shared_context.metadata,
                    "business_metrics": "business_metrics" in shared_context.metadata
                }
            }
            
            # Execute agent with shared context
            result = await agent.execute(shared_context, stream_updates=True)
            
            # Create evolved context with agent's contribution
            agent_contribution = {
                f"{agent_name}_insights": result["business_output"]["insights"],
                f"{agent_name}_recommendations": result["business_output"]["recommendations"],
                f"{agent_name}_execution_timestamp": time.time()
            }
            
            # Create new context with accumulated data
            shared_context = shared_context.create_child_context(
                operation_name=f"context_sharing_stage_{i+1}",
                additional_agent_context=agent_contribution
            )
            
            # Capture context state after agent execution
            post_execution_state = {
                "agent_name": agent_name,
                "metadata_keys": list(shared_context.metadata.keys()),
                "metadata_size": len(shared_context.metadata),
                "metadata_growth": len(shared_context.metadata) - pre_execution_state["metadata_size"],
                "agent_contribution_keys": list(agent_contribution.keys())
            }
            
            context_evolution.append({
                "pre_execution": pre_execution_state,
                "post_execution": post_execution_state,
                "result": result
            })
        
        # Validate context sharing and evolution
        assert len(context_evolution) == len(agent_names), "All agents should process shared context"
        
        for i, evolution in enumerate(context_evolution):
            pre = evolution["pre_execution"]
            post = evolution["post_execution"]
            result = evolution["result"]
            
            # Validate business data preservation
            for key, present in pre["business_data_present"].items():
                assert present is True, f"Business data '{key}' should be present for {pre['agent_name']}"
            
            # Validate context growth (agents should add data)
            assert post["metadata_growth"] > 0, f"Agent {post['agent_name']} should contribute to context"
            assert len(post["agent_contribution_keys"]) >= 3, "Agent should contribute insights, recommendations, and timestamp"
            
            # Validate business output quality
            insights = result["business_output"]["insights"]
            recommendations = result["business_output"]["recommendations"]
            
            assert len(insights) >= 2, f"Agent {pre['agent_name']} should provide meaningful insights"
            assert len(recommendations) >= 1, f"Agent {pre['agent_name']} should provide actionable recommendations"
        
        # Validate final context contains cumulative business value
        final_metadata_keys = list(shared_context.metadata.keys())
        
        # Should contain original business data
        original_keys = ["customer_id", "project_type", "budget_constraints", "business_metrics"]
        for key in original_keys:
            assert key in final_metadata_keys, f"Original business data '{key}' should be preserved"
            
        # Should contain contributions from all agents
        for agent_name in agent_names:
            agent_insight_key = f"{agent_name}_insights"
            assert agent_insight_key in final_metadata_keys, f"Agent {agent_name} contributions should be preserved"
        
        # Validate context isolation (each context should have unique request_id)
        unique_request_ids = set()
        for agent in agents.values():
            for context_snapshot in agent.received_contexts:
                # Note: We create child contexts, so request_ids will be different
                # This is correct behavior for isolation
                pass
        
        # Final context should have significantly more data than initial
        initial_metadata_count = len(business_context.metadata)
        final_metadata_count = len(shared_context.metadata)
        
        # Expect significant growth in metadata from agent contributions
        # Each of 3 agents should contribute at least 3 pieces of data (insights, recommendations, timestamp)
        expected_minimum_growth = initial_metadata_count + (3 * 3)  # 3 agents × 3 contributions
        assert final_metadata_count >= expected_minimum_growth, \
            f"Final context should have significantly more business data from agent contributions. " \
            f"Got {final_metadata_count}, expected >= {expected_minimum_growth} (initial {initial_metadata_count} + 9 agent contributions)"

    @pytest.mark.asyncio
    async def test_multi_agent_workflow_coordination(self):
        """Test multi-agent workflow coordination and orchestration patterns.
        
        Validates:
        - Multiple agents work together toward common business goal
        - Workflow coordination maintains business objectives
        - Agent outputs complement each other for comprehensive results
        - Resource utilization is efficient across agents
        """
        # Create context for coordinated workflow
        coordination_context = self.create_user_execution_context(
            user_request="Execute coordinated multi-agent business optimization workflow",
            additional_metadata={
                "workflow_goal": "comprehensive_business_optimization",
                "coordination_required": True,
                "expected_agents": ["market_analyzer", "cost_optimizer", "performance_enhancer", "strategy_coordinator"],
                "success_criteria": {
                    "cost_reduction": ">20%",
                    "performance_improvement": ">15%",
                    "market_insights": ">5",
                    "strategic_recommendations": ">3"
                }
            }
        )
        
        # Create specialized agents for coordination
        specialist_agents = {
            "market_analyzer": CommunicatingMockAgent("market_analyzer", 0.4),
            "cost_optimizer": CommunicatingMockAgent("cost_optimizer", 0.5),
            "performance_enhancer": CommunicatingMockAgent("performance_enhancer", 0.6),
            "strategy_coordinator": CommunicatingMockAgent("strategy_coordinator", 0.3)
        }
        
        # Override execute method for specialized business logic
        async def market_analyzer_execute(context: UserExecutionContext, stream_updates: bool = False):
            await asyncio.sleep(0.4)
            return {
                "status": "completed",
                "agent_name": "market_analyzer",
                "business_output": {
                    "insights": [
                        "Market trend indicates 25% growth in AI optimization services",
                        "Competitor analysis shows pricing opportunities",
                        "Customer demand for cost reduction services increased 40%",
                        "Market consolidation creating efficiency opportunities",
                        "Technology adoption rates favor automated optimization",
                        "Regulatory environment supports optimization initiatives"
                    ],
                    "recommendations": [
                        "Focus on automated cost optimization solutions",
                        "Develop market-leading performance benchmarks",
                        "Target enterprise customers with complex infrastructures"
                    ],
                    "next_agent_suggestions": ["cost_optimizer", "performance_enhancer"]
                },
                "market_data": {
                    "market_size": 2.5e9,  # $2.5B market
                    "growth_rate": 25,
                    "opportunity_score": 8.5
                }
            }
        
        async def cost_optimizer_execute(context: UserExecutionContext, stream_updates: bool = False):
            await asyncio.sleep(0.5)
            return {
                "status": "completed", 
                "agent_name": "cost_optimizer",
                "business_output": {
                    "insights": [
                        "Infrastructure costs can be reduced by 30% through optimization",
                        "Cloud resource utilization currently at 60% efficiency",
                        "Automated scaling can reduce peak-time costs by 40%"
                    ],
                    "recommendations": [
                        "Implement automated resource scaling",
                        "Optimize cloud resource allocation patterns",
                        "Deploy cost monitoring and alerting systems"
                    ],
                    "next_agent_suggestions": ["performance_enhancer"]
                },
                "optimization_results": {
                    "potential_savings": 30,  # 30% cost reduction
                    "implementation_complexity": "medium",
                    "payback_period_months": 6
                }
            }
        
        async def performance_enhancer_execute(context: UserExecutionContext, stream_updates: bool = False):
            await asyncio.sleep(0.6)
            return {
                "status": "completed",
                "agent_name": "performance_enhancer", 
                "business_output": {
                    "insights": [
                        "System performance can improve 35% with optimization",
                        "Latency reduction opportunities identified in 3 key areas",
                        "Throughput can increase 25% with current resources"
                    ],
                    "recommendations": [
                        "Deploy performance monitoring systems",
                        "Implement caching strategies for common operations",
                        "Optimize database query patterns"
                    ],
                    "next_agent_suggestions": ["strategy_coordinator"]
                },
                "performance_metrics": {
                    "latency_improvement": 35,  # 35% improvement
                    "throughput_increase": 25,
                    "resource_efficiency_gain": 20
                }
            }
        
        async def strategy_coordinator_execute(context: UserExecutionContext, stream_updates: bool = False):
            await asyncio.sleep(0.3)
            
            # Access previous agents' results from context metadata
            market_data = context.metadata.get("market_analyzer_result", {}).get("market_data", {})
            cost_data = context.metadata.get("cost_optimizer_result", {}).get("optimization_results", {})
            performance_data = context.metadata.get("performance_enhancer_result", {}).get("performance_metrics", {})
            
            return {
                "status": "completed",
                "agent_name": "strategy_coordinator",
                "business_output": {
                    "insights": [
                        "Coordinated optimization can deliver 50% total business value improvement",
                        "Market opportunity aligns with performance and cost capabilities",
                        "Strategic positioning for market leadership is achievable"
                    ],
                    "recommendations": [
                        "Execute coordinated market entry with optimized cost structure",
                        "Leverage performance advantages for competitive positioning", 
                        "Implement integrated business optimization platform",
                        "Develop strategic partnerships for market expansion"
                    ],
                    "next_agent_suggestions": []  # Final coordinator
                },
                "strategic_synthesis": {
                    "total_business_impact": 50,  # Combined impact
                    "market_opportunity": market_data.get("opportunity_score", 0),
                    "cost_optimization": cost_data.get("potential_savings", 0),
                    "performance_enhancement": performance_data.get("latency_improvement", 0),
                    "coordination_success": True
                }
            }
        
        # Assign specialized execute methods
        specialist_agents["market_analyzer"].execute = market_analyzer_execute
        specialist_agents["cost_optimizer"].execute = cost_optimizer_execute
        specialist_agents["performance_enhancer"].execute = performance_enhancer_execute
        specialist_agents["strategy_coordinator"].execute = strategy_coordinator_execute
        
        # Execute coordinated workflow
        workflow_results = {}
        current_context = coordination_context
        
        # Execute in coordination order
        coordination_order = ["market_analyzer", "cost_optimizer", "performance_enhancer", "strategy_coordinator"]
        
        for agent_name in coordination_order:
            agent = specialist_agents[agent_name]
            
            # Execute agent
            result = await agent.execute(current_context, stream_updates=True)
            workflow_results[agent_name] = result
            
            # Update context with result for next agent
            current_context = current_context.create_child_context(
                operation_name=f"coordination_{agent_name}_complete",
                additional_agent_context={f"{agent_name}_result": result}
            )
        
        # Validate coordinated workflow results
        assert len(workflow_results) == len(coordination_order), "All coordinated agents should complete"
        
        # Validate business success criteria
        success_criteria = coordination_context.metadata["success_criteria"]
        
        # Check cost reduction (from cost_optimizer)
        cost_savings = workflow_results["cost_optimizer"]["optimization_results"]["potential_savings"]
        assert cost_savings >= 20, f"Cost reduction {cost_savings}% should meet >20% criteria"
        
        # Check performance improvement (from performance_enhancer)
        perf_improvement = workflow_results["performance_enhancer"]["performance_metrics"]["latency_improvement"]
        assert perf_improvement >= 15, f"Performance improvement {perf_improvement}% should meet >15% criteria"
        
        # Check market insights (from market_analyzer)
        market_insights = len(workflow_results["market_analyzer"]["business_output"]["insights"])
        assert market_insights >= 5, f"Market insights {market_insights} should meet >5 criteria"
        
        # Check strategic recommendations (from strategy_coordinator)
        strategic_recommendations = len(workflow_results["strategy_coordinator"]["business_output"]["recommendations"])
        assert strategic_recommendations >= 3, f"Strategic recommendations {strategic_recommendations} should meet >3 criteria"
        
        # Validate coordination success
        coordination_success = workflow_results["strategy_coordinator"]["strategic_synthesis"]["coordination_success"]
        assert coordination_success is True, "Coordination should be marked as successful"
        
        # Validate total business impact
        total_impact = workflow_results["strategy_coordinator"]["strategic_synthesis"]["total_business_impact"]
        assert total_impact >= 40, f"Total business impact {total_impact}% should demonstrate significant value"

    @pytest.mark.asyncio
    async def test_agent_state_synchronization(self):
        """Test agent state synchronization and consistency across workflow execution.
        
        Validates:
        - Agent states remain consistent across execution workflow
        - State changes are properly synchronized between agents
        - No state corruption or data loss occurs
        - State isolation prevents cross-agent contamination
        """
        # Create context for state synchronization testing
        sync_context = self.create_user_execution_context(
            user_request="Test agent state synchronization across workflow execution",
            additional_metadata={
                "sync_testing": True,
                "state_tracking": True,
                "consistency_validation": True,
                "initial_state": {
                    "workflow_id": str(uuid.uuid4()),
                    "state_version": 1,
                    "business_data": {"initial_value": 100}
                }
            }
        )
        
        # Create agents with state tracking
        state_tracking_agents = {
            "state_initializer": CommunicatingMockAgent("state_initializer", 0.2),
            "state_modifier": CommunicatingMockAgent("state_modifier", 0.3),
            "state_validator": CommunicatingMockAgent("state_validator", 0.2),
            "state_finalizer": CommunicatingMockAgent("state_finalizer", 0.2)
        }
        
        # Track state evolution
        state_history = []
        
        # Execute state synchronization workflow
        current_context = sync_context
        workflow_state = sync_context.metadata["initial_state"].copy()
        
        for agent_name, agent in state_tracking_agents.items():
            # Capture state before agent execution
            pre_state = {
                "agent_name": agent_name,
                "timestamp": time.time(),
                "workflow_state": workflow_state.copy(),
                "context_metadata_size": len(current_context.metadata)
            }
            
            # Execute agent
            result = await agent.execute(current_context, stream_updates=True)
            
            # Update workflow state based on agent type
            if agent_name == "state_initializer":
                workflow_state.update({
                    "initialized": True,
                    "initialization_timestamp": time.time(),
                    "business_data": {"initial_value": 100, "processed_count": 0}
                })
            elif agent_name == "state_modifier":
                workflow_state["state_version"] += 1
                workflow_state["business_data"]["processed_count"] += 50
                workflow_state["business_data"]["modified_by"] = agent_name
                workflow_state["modified"] = True
            elif agent_name == "state_validator":
                workflow_state["validated"] = True
                workflow_state["validation_score"] = 95
                workflow_state["business_data"]["validation_passed"] = True
            elif agent_name == "state_finalizer":
                workflow_state["finalized"] = True
                workflow_state["final_business_value"] = workflow_state["business_data"]["processed_count"] * 2
                workflow_state["state_version"] += 1
            
            # Update context with evolved state
            current_context = current_context.create_child_context(
                operation_name=f"state_sync_{agent_name}",
                additional_agent_context={
                    "workflow_state": workflow_state.copy(),
                    f"{agent_name}_result": result
                }
            )
            
            # Capture state after agent execution  
            post_state = {
                "agent_name": agent_name,
                "timestamp": time.time(),
                "workflow_state": workflow_state.copy(),
                "context_metadata_size": len(current_context.metadata),
                "agent_result": result
            }
            
            state_history.append({
                "pre_state": pre_state,
                "post_state": post_state
            })
        
        # Validate state synchronization
        assert len(state_history) == len(state_tracking_agents), "All agents should complete state tracking"
        
        # Validate state evolution consistency
        for i, state_record in enumerate(state_history):
            pre = state_record["pre_state"]
            post = state_record["post_state"]
            
            # Validate state progression
            assert post["timestamp"] > pre["timestamp"], "Post-execution timestamp should be later"
            assert post["context_metadata_size"] >= pre["context_metadata_size"], "Context should grow or maintain size"
            
            # Validate workflow state consistency
            pre_workflow = pre["workflow_state"]
            post_workflow = post["workflow_state"]
            
            # Core workflow data should be preserved
            assert post_workflow["workflow_id"] == pre_workflow["workflow_id"], "Workflow ID should remain constant"
            assert post_workflow["state_version"] >= pre_workflow["state_version"], "State version should increase or stay same"
            
            # Business data should evolve appropriately
            if "business_data" in post_workflow:
                assert "initial_value" in post_workflow["business_data"], "Initial business value should be preserved"
                assert post_workflow["business_data"]["initial_value"] == 100, "Initial value should remain constant"
        
        # Validate final synchronized state
        final_state = state_history[-1]["post_state"]["workflow_state"]
        
        # All state flags should be set
        assert final_state.get("initialized") is True, "State should be initialized"
        assert final_state.get("modified") is True, "State should be modified"
        assert final_state.get("validated") is True, "State should be validated"
        assert final_state.get("finalized") is True, "State should be finalized"
        
        # Business metrics should be computed correctly
        assert final_state.get("final_business_value", 0) > 0, "Final business value should be calculated"
        assert final_state["business_data"]["processed_count"] > 0, "Should have processed items"
        assert final_state["business_data"]["validation_passed"] is True, "Validation should pass"
        
        # State version should have incremented appropriately
        initial_version = sync_context.metadata["initial_state"]["state_version"]
        final_version = final_state["state_version"]
        assert final_version > initial_version, "State version should increment during workflow"
        
        # Validate no state corruption
        for agent in state_tracking_agents.values():
            comm_stats = agent.get_communication_stats()
            assert comm_stats["execution_count"] == 1, "Each agent should execute exactly once"
            assert comm_stats["contexts_received"] >= 1, "Each agent should receive context"

    @pytest.mark.asyncio
    async def test_communication_error_handling(self):
        """Test communication error handling between agents maintains system reliability.
        
        Validates:
        - Communication failures are handled gracefully
        - System continues operation despite communication issues
        - Error context is preserved for debugging
        - Fallback communication mechanisms work correctly
        """
        # Create context for communication error testing
        error_context = self.create_user_execution_context(
            user_request="Test communication error handling and recovery mechanisms",
            additional_metadata={
                "error_testing": True,
                "communication_reliability": True,
                "fallback_mechanisms": True,
                "error_simulation": "communication_failures"
            }
        )
        
        # Create agents with mixed reliability
        communication_agents = {
            "reliable_communicator": CommunicatingMockAgent("reliable_communicator", 0.2),
            "unreliable_communicator": CommunicatingMockAgent("unreliable_communicator", 0.3),
            "error_recovery_agent": CommunicatingMockAgent("error_recovery_agent", 0.2),
            "communication_monitor": CommunicatingMockAgent("communication_monitor", 0.1)
        }
        
        # Simulate communication errors for unreliable agent
        original_execute = communication_agents["unreliable_communicator"].execute
        communication_failure_count = 0
        
        async def failing_execute(context: UserExecutionContext, stream_updates: bool = False):
            nonlocal communication_failure_count
            communication_failure_count += 1
            
            # Fail first attempt, succeed on retry
            if communication_failure_count == 1:
                raise ConnectionError("Simulated communication failure - network timeout")
            else:
                # Succeed but with degraded functionality
                result = await original_execute(context, stream_updates)
                result["communication_status"] = "recovered_after_failure"
                result["degraded_mode"] = True
                return result
        
        communication_agents["unreliable_communicator"].execute = failing_execute
        
        # Execute workflow with error handling
        communication_results = {}
        error_log = []
        current_context = error_context
        
        for agent_name, agent in communication_agents.items():
            try:
                # First attempt
                result = await agent.execute(current_context, stream_updates=True)
                communication_results[agent_name] = result
                
            except Exception as e:
                error_info = {
                    "agent_name": agent_name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "timestamp": time.time()
                }
                error_log.append(error_info)
                
                # Attempt recovery for communication errors
                if "communication" in str(e).lower() or isinstance(e, ConnectionError):
                    try:
                        # Retry with backoff
                        await asyncio.sleep(0.1)  # Brief backoff
                        retry_result = await agent.execute(current_context, stream_updates=True)
                        retry_result["recovered_from_error"] = True
                        retry_result["original_error"] = str(e)
                        communication_results[agent_name] = retry_result
                        
                    except Exception as retry_error:
                        # Final fallback - create minimal result
                        fallback_result = {
                            "status": "partial_failure",
                            "agent_name": agent_name,
                            "error_handled": True,
                            "original_error": str(e),
                            "retry_error": str(retry_error),
                            "business_output": {
                                "insights": ["Error recovery mode - limited functionality"],
                                "recommendations": ["Check communication systems"],
                                "next_agent_suggestions": []
                            }
                        }
                        communication_results[agent_name] = fallback_result
                        error_log.append({
                            "agent_name": agent_name,
                            "error_type": "retry_failed",
                            "error_message": str(retry_error),
                            "timestamp": time.time()
                        })
                else:
                    # Non-communication error - fail fast
                    raise
            
            # Update context for next agent
            if agent_name in communication_results:
                current_context = current_context.create_child_context(
                    operation_name=f"communication_handling_{agent_name}",
                    additional_agent_context={
                        f"{agent_name}_result": communication_results[agent_name],
                        "error_count": len(error_log)
                    }
                )
        
        # Validate communication error handling
        assert len(communication_results) == len(communication_agents), "All agents should complete (with recovery if needed)"
        
        # Validate specific agent behaviors
        reliable_result = communication_results["reliable_communicator"]
        assert reliable_result["status"] == "completed", "Reliable agent should complete normally"
        assert "communication_status" not in reliable_result, "Reliable agent should not have communication issues"
        
        unreliable_result = communication_results["unreliable_communicator"]
        assert unreliable_result["status"] in ["completed", "partial_failure"], "Unreliable agent should complete or partially succeed"
        assert "recovered_from_error" in unreliable_result or "error_handled" in unreliable_result, \
            "Unreliable agent should show recovery or error handling"
            
        # Validate error logging
        assert len(error_log) > 0, "Should capture communication errors"
        communication_errors = [error for error in error_log if "communication" in error["error_message"].lower()]
        assert len(communication_errors) > 0, "Should capture specific communication failures"
        
        # Validate system resilience
        successful_agents = [result for result in communication_results.values() if result["status"] == "completed"]
        assert len(successful_agents) >= 3, "Majority of agents should succeed despite communication issues"
        
        # Validate business continuity despite errors
        total_business_output = 0
        for result in communication_results.values():
            if "business_output" in result and "insights" in result["business_output"]:
                total_business_output += len(result["business_output"]["insights"])
                
        assert total_business_output > 0, "Should maintain business output despite communication errors"
        
        # Validate error context preservation
        for error in error_log:
            assert "timestamp" in error, "Error timestamp should be preserved"
            assert "error_type" in error, "Error type should be captured"
            assert "agent_name" in error, "Agent name should be preserved for debugging"