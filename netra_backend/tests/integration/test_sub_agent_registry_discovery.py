"""
CRITICAL INTEGRATION TEST #7: Sub-Agent Registry and Discovery

BVJ:
- Segment: Platform/Internal (foundation for ALL customer segments)
- Business Goal: Platform Stability - Prevent $35K MRR loss from agent routing failures
- Value Impact: Ensures register → capability mapping → dynamic discovery → routing validation
- Revenue Impact: Prevents customer requests from failing due to agent discovery issues

REQUIREMENTS:
- Register agents with unique capabilities
- Map agent capabilities to request types
- Enable dynamic agent discovery by capabilities
- Validate routing decisions based on discovery
- Discovery resolution within 2 seconds
- 99% routing accuracy to correct agents
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio

# Set testing environment
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from netra_backend.app.logging_config import central_logger

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from test_framework.mock_utils import mock_justified

logger = central_logger.get_logger(__name__)

class MockCapabilityAgent(BaseSubAgent):
    """Mock agent with defined capabilities for testing."""
    
    def __init__(self, name: str, capabilities: List[str], llm_manager=None):
        super().__init__(llm_manager, name=name)
        self.capabilities = capabilities
        self.request_count = 0
    
    async def execute(self, request: Dict[str, Any], state: DeepAgentState) -> Dict[str, Any]:
        """Execute agent with capability validation."""
        self.request_count += 1
        return {
            "status": "success",
            "agent": self.name,
            "capabilities_used": self.capabilities,
            "request_count": self.request_count
        }
    
    def can_handle(self, request_type: str) -> bool:
        """Check if agent can handle specific request type."""
        return request_type.lower() in [cap.lower() for cap in self.capabilities]

class TestSubAgentRegistryDiscovery:
    """BVJ: Protects $35K MRR through reliable agent discovery and capability routing."""

    @pytest.fixture
    @mock_justified("LLM service external dependency for agent testing")
    def llm_manager_mock(self):
        """Mock LLM manager for registry testing."""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_mock = Mock(spec=LLMManager)
        # Mock: Async component isolation for testing without real async operations
        llm_mock.generate_response = AsyncMock(return_value={
            "content": "Agent discovery response",
            "usage": {"prompt_tokens": 40, "completion_tokens": 15}
        })
        return llm_mock

    @pytest.fixture
    @mock_justified("Tool dispatcher external dependency for capability mapping")
    def tool_dispatcher_mock(self):
        """Mock tool dispatcher for capability testing."""
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        dispatcher_mock = Mock(spec=ToolDispatcher)
        # Mock: Async component isolation for testing without real async operations
        dispatcher_mock.dispatch = AsyncMock(return_value={"status": "success"})
        return dispatcher_mock

    @pytest.fixture
    def capability_registry(self, llm_manager_mock, tool_dispatcher_mock):
        """Create registry with capability-specific agents."""
        registry = AgentRegistry(llm_manager_mock, tool_dispatcher_mock)
        
        # Create agents with specific capabilities
        capability_agents = {
            "data_analyst": MockCapabilityAgent("data_analyst", 
                ["data_analysis", "query_execution", "metrics_calculation"], llm_manager_mock),
            "performance_optimizer": MockCapabilityAgent("performance_optimizer", 
                ["gpu_optimization", "memory_optimization", "cost_optimization"], llm_manager_mock),
            "infrastructure_specialist": MockCapabilityAgent("infrastructure_specialist", 
                ["deployment", "scaling", "load_balancing", "monitoring"], llm_manager_mock),
            "security_auditor": MockCapabilityAgent("security_auditor", 
                ["vulnerability_scanning", "compliance_checking", "access_control"], llm_manager_mock),
            "report_generator": MockCapabilityAgent("report_generator", 
                ["report_creation", "data_visualization", "summary_generation"], llm_manager_mock)
        }
        
        # Register capability agents
        for name, agent in capability_agents.items():
            registry.register(name, agent)
        
        return registry

    @pytest.mark.asyncio
    async def test_01_agent_capability_registration_mapping(self, capability_registry):
        """BVJ: Validates agents are registered with correct capability mappings."""
        # Step 1: Verify all capability agents are registered
        registered_agents = capability_registry.list_agents()
        expected_agents = ["data_analyst", "performance_optimizer", "infrastructure_specialist", 
                          "security_auditor", "report_generator"]
        
        for expected_agent in expected_agents:
            assert expected_agent in registered_agents, f"Agent {expected_agent} not registered"
        
        # Step 2: Validate agent capability mappings
        capability_mapping_tests = [
            ("data_analyst", "data_analysis", True),
            ("data_analyst", "gpu_optimization", False),
            ("performance_optimizer", "memory_optimization", True),
            ("performance_optimizer", "report_creation", False),
            ("infrastructure_specialist", "scaling", True),
            ("security_auditor", "vulnerability_scanning", True),
            ("report_generator", "data_visualization", True)
        ]
        
        for agent_name, capability, should_handle in capability_mapping_tests:
            agent = capability_registry.get(agent_name)
            assert agent is not None, f"Agent {agent_name} not found"
            
            can_handle = agent.can_handle(capability)
            assert can_handle == should_handle, \
                f"Agent {agent_name} capability {capability} mapping incorrect: expected {should_handle}, got {can_handle}"
        
        # Step 3: Validate capability uniqueness and coverage
        all_capabilities = set()
        agent_capability_map = {}
        
        for agent_name in expected_agents:
            agent = capability_registry.get(agent_name)
            agent_capability_map[agent_name] = agent.capabilities
            all_capabilities.update(agent.capabilities)
        
        # Verify comprehensive capability coverage
        assert len(all_capabilities) >= 15, f"Only {len(all_capabilities)} unique capabilities, need at least 15"
        
        logger.info(f"Capability mapping validated: {len(expected_agents)} agents with {len(all_capabilities)} capabilities")

    @pytest.mark.asyncio
    async def test_02_dynamic_agent_discovery_by_capability(self, capability_registry):
        """BVJ: Validates dynamic discovery of agents based on request capabilities."""
        # Discovery test scenarios
        discovery_scenarios = [
            {
                "request_type": "data_analysis",
                "expected_agents": ["data_analyst"],
                "description": "Data analysis request routing"
            },
            {
                "request_type": "gpu_optimization", 
                "expected_agents": ["performance_optimizer"],
                "description": "GPU optimization request routing"
            },
            {
                "request_type": "deployment",
                "expected_agents": ["infrastructure_specialist"],
                "description": "Infrastructure deployment routing"
            },
            {
                "request_type": "vulnerability_scanning",
                "expected_agents": ["security_auditor"],
                "description": "Security audit routing"
            },
            {
                "request_type": "report_creation",
                "expected_agents": ["report_generator"],
                "description": "Report generation routing"
            }
        ]
        
        # Execute discovery tests
        discovery_results = []
        
        for scenario in discovery_scenarios:
            start_time = time.time()
            
            # Step 1: Discover agents capable of handling request
            capable_agents = []
            for agent_name in capability_registry.list_agents():
                agent = capability_registry.get(agent_name)
                if agent.can_handle(scenario["request_type"]):
                    capable_agents.append(agent_name)
            
            discovery_time = time.time() - start_time
            
            # Step 2: Validate discovery results
            assert len(capable_agents) > 0, f"No agents discovered for {scenario['request_type']}"
            
            for expected_agent in scenario["expected_agents"]:
                assert expected_agent in capable_agents, \
                    f"Expected agent {expected_agent} not discovered for {scenario['request_type']}"
            
            # Step 3: Validate discovery timing
            assert discovery_time < 2.0, \
                f"Discovery for {scenario['request_type']} took {discovery_time:.2f}s, exceeds 2s limit"
            
            discovery_results.append({
                "request_type": scenario["request_type"],
                "discovered_agents": capable_agents,
                "expected_agents": scenario["expected_agents"],
                "discovery_time": discovery_time,
                "success": set(capable_agents) >= set(scenario["expected_agents"])
            })
        
        # Step 4: Analyze overall discovery performance
        successful_discoveries = sum(1 for r in discovery_results if r["success"])
        discovery_success_rate = (successful_discoveries / len(discovery_results)) * 100
        avg_discovery_time = sum(r["discovery_time"] for r in discovery_results) / len(discovery_results)
        
        assert discovery_success_rate == 100.0, f"Discovery success rate {discovery_success_rate}% below 100%"
        assert avg_discovery_time < 1.0, f"Average discovery time {avg_discovery_time:.2f}s too slow"
        
        logger.info(f"Dynamic discovery validated: {discovery_success_rate}% success, {avg_discovery_time:.2f}s avg time")

    @pytest.mark.asyncio
    async def test_03_agent_routing_validation_pipeline(self, capability_registry):
        """BVJ: Validates routing decisions based on agent discovery results."""
        # Complex routing scenarios
        routing_scenarios = [
            {
                "user_request": "Analyze database performance metrics and optimize query execution",
                "primary_capability": "data_analysis",
                "secondary_capability": "performance_optimization",
                "expected_primary": "data_analyst",
                "expected_workflow": "data_analyst → performance_optimizer"
            },
            {
                "user_request": "Deploy scalable infrastructure with security compliance",
                "primary_capability": "deployment",
                "secondary_capability": "compliance_checking",
                "expected_primary": "infrastructure_specialist",
                "expected_workflow": "infrastructure_specialist → security_auditor"
            },
            {
                "user_request": "Generate performance optimization report with cost analysis",
                "primary_capability": "report_creation",
                "secondary_capability": "cost_optimization",
                "expected_primary": "report_generator",
                "expected_workflow": "report_generator → performance_optimizer"
            }
        ]
        
        # Mock intelligent routing function
        async def route_request(request: str, registry: AgentRegistry) -> Dict[str, Any]:
            """Simulate intelligent request routing based on content analysis."""
            request_lower = request.lower()
            
            # Primary agent selection
            if any(keyword in request_lower for keyword in ["analyze", "metrics", "data"]):
                primary_agent = "data_analyst"
            elif any(keyword in request_lower for keyword in ["deploy", "infrastructure", "scale"]):
                primary_agent = "infrastructure_specialist"
            elif any(keyword in request_lower for keyword in ["report", "generate", "summary"]):
                primary_agent = "report_generator"
            elif any(keyword in request_lower for keyword in ["optimize", "performance", "memory"]):
                primary_agent = "performance_optimizer"
            elif any(keyword in request_lower for keyword in ["security", "compliance", "vulnerability"]):
                primary_agent = "security_auditor"
            else:
                primary_agent = "data_analyst"  # Default
            
            # Secondary agent selection
            secondary_agents = []
            if "optimize" in request_lower and primary_agent != "performance_optimizer":
                secondary_agents.append("performance_optimizer")
            if any(keyword in request_lower for keyword in ["security", "compliance"]) and primary_agent != "security_auditor":
                secondary_agents.append("security_auditor")
            if "report" in request_lower and primary_agent != "report_generator":
                secondary_agents.append("report_generator")
            
            return {
                "primary_agent": primary_agent,
                "secondary_agents": secondary_agents,
                "confidence": 0.85,
                "routing_strategy": "capability_based"
            }
        
        # Execute routing validation tests
        routing_results = []
        
        for scenario in routing_scenarios:
            start_time = time.time()
            
            # Step 1: Execute routing decision
            routing_decision = route_request(scenario["user_request"], capability_registry)
            
            # Step 2: Validate primary agent selection
            assert routing_decision["primary_agent"] == scenario["expected_primary"], \
                f"Primary routing failed: expected {scenario['expected_primary']}, got {routing_decision['primary_agent']}"
            
            # Step 3: Verify agent exists and can handle request
            primary_agent = capability_registry.get(routing_decision["primary_agent"])
            assert primary_agent is not None, f"Primary agent {routing_decision['primary_agent']} not found"
            
            # Step 4: Test agent execution
            test_state = DeepAgentState()
            execution_result = await primary_agent.execute(
                {"request": scenario["user_request"]}, test_state
            )
            
            assert execution_result["status"] == "success", f"Primary agent execution failed"
            
            routing_time = time.time() - start_time
            
            # Step 5: Validate routing timing
            assert routing_time < 1.0, f"Routing took {routing_time:.2f}s, exceeds 1s limit"
            
            routing_results.append({
                "scenario": scenario["user_request"][:50] + "...",
                "primary_agent": routing_decision["primary_agent"],
                "expected_primary": scenario["expected_primary"],
                "routing_correct": routing_decision["primary_agent"] == scenario["expected_primary"],
                "execution_successful": execution_result["status"] == "success",
                "routing_time": routing_time,
                "confidence": routing_decision["confidence"]
            })
        
        # Step 6: Analyze routing accuracy
        correct_routings = sum(1 for r in routing_results if r["routing_correct"])
        successful_executions = sum(1 for r in routing_results if r["execution_successful"])
        
        routing_accuracy = (correct_routings / len(routing_results)) * 100
        execution_success_rate = (successful_executions / len(routing_results)) * 100
        avg_routing_time = sum(r["routing_time"] for r in routing_results) / len(routing_results)
        
        assert routing_accuracy >= 99.0, f"Routing accuracy {routing_accuracy}% below 99%"
        assert execution_success_rate == 100.0, f"Execution success rate {execution_success_rate}% below 100%"
        assert avg_routing_time < 0.5, f"Average routing time {avg_routing_time:.2f}s too slow"
        
        logger.info(f"Routing validation: {routing_accuracy}% accuracy, {execution_success_rate}% execution success")

    @pytest.mark.asyncio
    async def test_04_capability_conflict_resolution(self, capability_registry):
        """BVJ: Validates resolution when multiple agents can handle the same request."""
        # Add overlapping capability agents
        overlapping_agents = {
            "data_specialist": MockCapabilityAgent("data_specialist", 
                ["data_analysis", "metrics_calculation", "performance_analysis"], capability_registry.llm_manager),
            "optimization_expert": MockCapabilityAgent("optimization_expert", 
                ["performance_optimization", "cost_optimization", "gpu_optimization"], capability_registry.llm_manager)
        }
        
        for name, agent in overlapping_agents.items():
            capability_registry.register(name, agent)
        
        # Test conflict resolution scenarios
        conflict_scenarios = [
            {
                "capability": "data_analysis",
                "potential_agents": ["data_analyst", "data_specialist"],
                "resolution_strategy": "priority_based"
            },
            {
                "capability": "cost_optimization", 
                "potential_agents": ["performance_optimizer", "optimization_expert"],
                "resolution_strategy": "load_balancing"
            }
        ]
        
        for scenario in conflict_scenarios:
            # Step 1: Identify all capable agents
            capable_agents = []
            for agent_name in capability_registry.list_agents():
                agent = capability_registry.get(agent_name)
                if hasattr(agent, 'can_handle') and agent.can_handle(scenario["capability"]):
                    capable_agents.append(agent_name)
            
            # Step 2: Validate multiple agents found
            assert len(capable_agents) >= 2, f"Not enough agents for conflict testing: {len(capable_agents)}"
            
            # Step 3: Verify expected agents are in capable list
            for expected_agent in scenario["potential_agents"]:
                assert expected_agent in capable_agents, f"Expected agent {expected_agent} not found in capable agents"
            
            # Step 4: Test resolution strategy (select first available)
            selected_agent_name = capable_agents[0]
            selected_agent = capability_registry.get(selected_agent_name)
            
            # Step 5: Execute with selected agent
            test_state = DeepAgentState()
            execution_result = await selected_agent.execute(
                {"capability": scenario["capability"]}, test_state
            )
            
            assert execution_result["status"] == "success", f"Conflict resolution execution failed"
            assert execution_result["agent"] == selected_agent_name, f"Wrong agent executed"
        
        logger.info(f"Capability conflict resolution validated for {len(conflict_scenarios)} scenarios")

    @pytest.mark.asyncio
    async def test_05_agent_discovery_performance_load(self, capability_registry):
        """BVJ: Validates agent discovery maintains performance under load."""
        # Performance load test parameters
        concurrent_discoveries = 100
        max_discovery_time = 2.0
        
        # Create diverse discovery requests
        discovery_requests = []
        capability_types = ["data_analysis", "gpu_optimization", "deployment", "vulnerability_scanning", "report_creation"]
        
        for i in range(concurrent_discoveries):
            discovery_requests.append({
                "request_id": f"discovery_{i}",
                "capability": capability_types[i % len(capability_types)],
                "timestamp": datetime.now(timezone.utc)
            })
        
        # Execute concurrent discovery operations
        async def perform_discovery(request):
            """Perform single agent discovery operation."""
            start_time = time.time()
            
            try:
                # Find agents capable of handling request
                capable_agents = []
                for agent_name in capability_registry.list_agents():
                    agent = capability_registry.get(agent_name)
                    if hasattr(agent, 'can_handle') and agent.can_handle(request["capability"]):
                        capable_agents.append(agent_name)
                
                discovery_time = time.time() - start_time
                
                return {
                    "request_id": request["request_id"],
                    "capability": request["capability"],
                    "discovered_agents": capable_agents,
                    "discovery_time": discovery_time,
                    "success": len(capable_agents) > 0
                }
                
            except Exception as e:
                discovery_time = time.time() - start_time
                return {
                    "request_id": request["request_id"],
                    "capability": request["capability"],
                    "error": str(e),
                    "discovery_time": discovery_time,
                    "success": False
                }
        
        # Execute load test
        start_time = time.time()
        
        discovery_results = await asyncio.gather(*[
            perform_discovery(request) for request in discovery_requests
        ], return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze performance results
        successful_discoveries = [r for r in discovery_results if not isinstance(r, Exception) and r["success"]]
        failed_discoveries = [r for r in discovery_results if isinstance(r, Exception) or not r.get("success")]
        
        success_rate = (len(successful_discoveries) / len(discovery_results)) * 100
        
        if successful_discoveries:
            avg_discovery_time = sum(r["discovery_time"] for r in successful_discoveries) / len(successful_discoveries)
            max_discovery_time_actual = max(r["discovery_time"] for r in successful_discoveries)
            p95_discovery_time = sorted([r["discovery_time"] for r in successful_discoveries])[int(len(successful_discoveries) * 0.95)]
        else:
            avg_discovery_time = float('inf')
            max_discovery_time_actual = float('inf')
            p95_discovery_time = float('inf')
        
        # Validate performance requirements
        assert success_rate >= 98.0, f"Discovery success rate {success_rate}% below 98%"
        assert avg_discovery_time < 0.1, f"Average discovery time {avg_discovery_time:.3f}s too slow"
        assert p95_discovery_time < max_discovery_time, f"P95 discovery time {p95_discovery_time:.2f}s exceeds {max_discovery_time}s"
        
        # Validate throughput
        throughput = len(successful_discoveries) / total_time
        assert throughput >= 50.0, f"Discovery throughput {throughput:.1f} ops/sec too low"
        
        logger.info(f"Discovery load test: {success_rate}% success, {avg_discovery_time:.3f}s avg, {throughput:.1f} ops/sec")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])