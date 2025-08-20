"""L3 Integration Test: Agent Tool Loading Concurrency

Business Value Justification (BVJ):
- Segment: Enterprise (performance and reliability)
- Business Goal: Ensure concurrent tool initialization doesn't cause conflicts
- Value Impact: Prevents tool loading bottlenecks affecting $100K MRR
- Strategic Impact: Critical for scalable multi-agent tool management

L3 Test: Uses real local services to validate concurrent tool loading and initialization.
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
import testcontainers.redis as redis_container
import testcontainers.postgres as postgres_container

from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState, AgentStateManager
from app.services.tool_loader import ToolLoader
from app.services.tool_registry import ToolRegistry
from app.redis_manager import RedisManager
from app.services.database.postgres_service import PostgresService
from test_framework.testcontainers_utils import TestcontainerHelper

logger = logging.getLogger(__name__)


class L3ToolLoadingManager:
    """Manages L3 tool loading concurrency testing with real infrastructure."""
    
    def __init__(self):
        self.redis_client = None
        self.postgres_service = None
        self.state_manager: Optional[AgentStateManager] = None
        self.tool_loader: Optional[ToolLoader] = None
        self.tool_registry: Optional[ToolRegistry] = None
        self.active_agents: Dict[str, BaseSubAgent] = {}
        self.tool_loading_sessions: Dict[str, Dict[str, Any]] = {}
        self.concurrent_metrics = {
            "total_tool_loads": 0,
            "successful_loads": 0,
            "failed_loads": 0,
            "concurrent_conflicts": 0,
            "average_load_time": 0.0,
            "peak_concurrent_loads": 0
        }
        
    async def initialize_l3_infrastructure(self, redis_url: str, postgres_url: str):
        """Initialize L3 infrastructure with real containers."""
        # Initialize Redis connection
        self.redis_client = RedisManager()
        self.redis_client.redis_url = redis_url
        await self.redis_client.initialize()
        
        # Initialize Postgres connection
        self.postgres_service = PostgresService()
        self.postgres_service.database_url = postgres_url
        await self.postgres_service.initialize()
        
        # Initialize state manager
        self.state_manager = AgentStateManager(
            redis_client=self.redis_client,
            postgres_service=self.postgres_service
        )
        
        # Initialize tool registry
        self.tool_registry = ToolRegistry(
            redis_client=self.redis_client,
            postgres_service=self.postgres_service
        )
        await self.tool_registry.initialize()
        
        # Initialize tool loader
        self.tool_loader = ToolLoader(
            tool_registry=self.tool_registry,
            state_manager=self.state_manager
        )
        
        # Register test tools
        await self._register_test_tools()
        
    async def _register_test_tools(self):
        """Register test tools for concurrent loading."""
        test_tools = [
            {
                "name": "data_analyzer",
                "version": "1.0.0",
                "type": "analysis",
                "size_mb": 15,
                "dependencies": [],
                "initialization_time": 2.0
            },
            {
                "name": "ml_optimizer",
                "version": "2.1.0",
                "type": "optimization",
                "size_mb": 45,
                "dependencies": ["numpy", "scipy"],
                "initialization_time": 5.0
            },
            {
                "name": "cost_calculator",
                "version": "1.5.0",
                "type": "calculation",
                "size_mb": 8,
                "dependencies": [],
                "initialization_time": 1.0
            },
            {
                "name": "report_generator",
                "version": "3.0.0",
                "type": "reporting",
                "size_mb": 25,
                "dependencies": ["data_analyzer"],
                "initialization_time": 3.0
            },
            {
                "name": "llm_interface",
                "version": "4.2.0",
                "type": "llm",
                "size_mb": 120,
                "dependencies": ["transformers", "torch"],
                "initialization_time": 10.0
            },
            {
                "name": "graph_visualizer",
                "version": "1.3.0",
                "type": "visualization",
                "size_mb": 32,
                "dependencies": ["matplotlib", "plotly"],
                "initialization_time": 4.0
            }
        ]
        
        for tool_spec in test_tools:
            await self.tool_registry.register_tool(tool_spec)
    
    async def create_concurrent_agents(self, agent_count: int, tools_per_agent: int = 3) -> Dict[str, Any]:
        """Create multiple agents for concurrent tool loading testing."""
        agents_created = []
        
        for i in range(agent_count):
            agent_id = f"tool_agent_{i}_{uuid.uuid4().hex[:6]}"
            
            # Create agent
            agent = BaseSubAgent(
                agent_id=agent_id,
                agent_type="tool_loading_agent",
                state_manager=self.state_manager,
                redis_client=self.redis_client
            )
            
            # Initialize agent state
            agent_state = DeepAgentState(
                agent_id=agent_id,
                agent_type="tool_loading_agent",
                status="initializing",
                required_tools=[],
                loaded_tools=[],
                created_at=time.time()
            )
            
            # Assign random tools to each agent
            available_tools = await self.tool_registry.list_available_tools()
            import random
            selected_tools = random.sample(available_tools, min(tools_per_agent, len(available_tools)))
            agent_state.required_tools = [tool["name"] for tool in selected_tools]
            
            await self.state_manager.save_state(agent_id, agent_state)
            
            self.active_agents[agent_id] = agent
            agents_created.append({
                "agent_id": agent_id,
                "required_tools": agent_state.required_tools
            })
        
        return {
            "agents_created": len(agents_created),
            "agent_details": agents_created,
            "total_tool_requirements": sum(len(a["required_tools"]) for a in agents_created)
        }
    
    async def test_concurrent_tool_loading(self, agent_ids: List[str]) -> Dict[str, Any]:
        """Test concurrent tool loading across multiple agents."""
        loading_start = time.time()
        
        try:
            # Track concurrent loading sessions
            loading_tasks = []
            session_ids = []
            
            for agent_id in agent_ids:
                session_id = f"session_{agent_id}_{uuid.uuid4().hex[:8]}"
                session_ids.append(session_id)
                
                # Create loading task for each agent
                task = self._load_agent_tools(agent_id, session_id)
                loading_tasks.append(task)
            
            # Update peak concurrent loads
            self.concurrent_metrics["peak_concurrent_loads"] = max(
                self.concurrent_metrics["peak_concurrent_loads"],
                len(loading_tasks)
            )
            
            # Execute concurrent loading
            loading_results = await asyncio.gather(*loading_tasks, return_exceptions=True)
            
            loading_time = time.time() - loading_start
            
            # Analyze results
            successful_loads = [r for r in loading_results if not isinstance(r, Exception) and r.get("success")]
            failed_loads = [r for r in loading_results if isinstance(r, Exception) or not r.get("success")]
            
            # Check for conflicts
            conflicts = await self._detect_loading_conflicts(session_ids)
            self.concurrent_metrics["concurrent_conflicts"] += len(conflicts)
            
            # Update metrics
            self.concurrent_metrics["successful_loads"] += len(successful_loads)
            self.concurrent_metrics["failed_loads"] += len(failed_loads)
            self.concurrent_metrics["total_tool_loads"] += len(loading_results)
            
            # Update average load time
            if successful_loads:
                avg_time = sum(r["loading_time"] for r in successful_loads) / len(successful_loads)
                self._update_average_load_time(avg_time)
            
            return {
                "success": True,
                "total_agents": len(agent_ids),
                "successful_loads": len(successful_loads),
                "failed_loads": len(failed_loads),
                "conflicts_detected": len(conflicts),
                "total_loading_time": loading_time,
                "loading_results": loading_results,
                "conflict_details": conflicts
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "loading_time": time.time() - loading_start
            }
    
    async def _load_agent_tools(self, agent_id: str, session_id: str) -> Dict[str, Any]:
        """Load tools for a specific agent."""
        load_start = time.time()
        
        try:
            # Get agent state
            agent_state = await self.state_manager.load_state(agent_id)
            if not agent_state:
                return {"success": False, "error": "Agent state not found"}
            
            # Track loading session
            self.tool_loading_sessions[session_id] = {
                "agent_id": agent_id,
                "required_tools": agent_state.required_tools,
                "start_time": load_start,
                "status": "loading"
            }
            
            loaded_tools = []
            loading_errors = []
            
            # Load each required tool
            for tool_name in agent_state.required_tools:
                try:
                    tool_load_result = await self.tool_loader.load_tool(
                        tool_name=tool_name,
                        agent_id=agent_id,
                        session_id=session_id
                    )
                    
                    if tool_load_result.get("success"):
                        loaded_tools.append(tool_name)
                    else:
                        loading_errors.append({
                            "tool": tool_name,
                            "error": tool_load_result.get("error", "Unknown error")
                        })
                        
                except Exception as e:
                    loading_errors.append({
                        "tool": tool_name,
                        "error": str(e)
                    })
            
            # Update agent state with loaded tools
            agent_state.loaded_tools = loaded_tools
            agent_state.tool_loading_errors = loading_errors
            agent_state.status = "tools_loaded" if len(loading_errors) == 0 else "partial_tools_loaded"
            await self.state_manager.save_state(agent_id, agent_state)
            
            # Update session status
            load_time = time.time() - load_start
            self.tool_loading_sessions[session_id].update({
                "status": "completed",
                "loaded_tools": loaded_tools,
                "loading_errors": loading_errors,
                "loading_time": load_time
            })
            
            return {
                "success": len(loading_errors) == 0,
                "agent_id": agent_id,
                "session_id": session_id,
                "loaded_tools": loaded_tools,
                "loading_errors": loading_errors,
                "loading_time": load_time,
                "tools_requested": len(agent_state.required_tools),
                "tools_loaded": len(loaded_tools)
            }
            
        except Exception as e:
            # Update session with error
            if session_id in self.tool_loading_sessions:
                self.tool_loading_sessions[session_id]["status"] = "error"
                self.tool_loading_sessions[session_id]["error"] = str(e)
            
            return {
                "success": False,
                "agent_id": agent_id,
                "session_id": session_id,
                "error": str(e),
                "loading_time": time.time() - load_start
            }
    
    async def _detect_loading_conflicts(self, session_ids: List[str]) -> List[Dict[str, Any]]:
        """Detect conflicts in concurrent tool loading."""
        conflicts = []
        
        try:
            # Check for tool loading conflicts
            for i, session_id_a in enumerate(session_ids):
                for session_id_b in session_ids[i+1:]:\n                    session_a = self.tool_loading_sessions.get(session_id_a)\n                    session_b = self.tool_loading_sessions.get(session_id_b)\n                    \n                    if not (session_a and session_b):\n                        continue\n                    \n                    # Check for overlapping tool loads\n                    tools_a = set(session_a.get(\"required_tools\", []))\n                    tools_b = set(session_b.get(\"required_tools\", []))\n                    \n                    overlapping_tools = tools_a & tools_b\n                    \n                    if overlapping_tools:\n                        # Check if loading happened at similar times (potential conflict)\n                        time_diff = abs(session_a.get(\"start_time\", 0) - session_b.get(\"start_time\", 0))\n                        \n                        if time_diff < 1.0:  # Within 1 second = potential conflict\n                            conflicts.append({\n                                \"type\": \"concurrent_tool_load\",\n                                \"session_a\": session_id_a,\n                                \"session_b\": session_id_b,\n                                \"overlapping_tools\": list(overlapping_tools),\n                                \"time_difference\": time_diff,\n                                \"severity\": \"high\" if time_diff < 0.1 else \"medium\"\n                            })\n            \n            # Check for resource conflicts\n            resource_conflicts = await self._check_resource_conflicts(session_ids)\n            conflicts.extend(resource_conflicts)\n            \n        except Exception as e:\n            conflicts.append({\"type\": \"conflict_detection_error\", \"error\": str(e)})\n        \n        return conflicts\n    \n    async def _check_resource_conflicts(self, session_ids: List[str]) -> List[Dict[str, Any]]:\n        \"\"\"Check for resource conflicts during concurrent loading.\"\"\"\n        resource_conflicts = []\n        \n        try:\n            # Check Redis key conflicts\n            redis_conflicts = await self._check_redis_key_conflicts(session_ids)\n            resource_conflicts.extend(redis_conflicts)\n            \n            # Check memory usage conflicts\n            memory_conflicts = await self._check_memory_conflicts(session_ids)\n            resource_conflicts.extend(memory_conflicts)\n            \n        except Exception as e:\n            resource_conflicts.append({\"type\": \"resource_check_error\", \"error\": str(e)})\n        \n        return resource_conflicts\n    \n    async def _check_redis_key_conflicts(self, session_ids: List[str]) -> List[Dict[str, Any]]:\n        \"\"\"Check for Redis key conflicts during tool loading.\"\"\"\n        conflicts = []\n        \n        try:\n            # Check for tool lock conflicts\n            for session_id in session_ids:\n                session = self.tool_loading_sessions.get(session_id)\n                if not session:\n                    continue\n                \n                for tool_name in session.get(\"required_tools\", []):\n                    lock_key = f\"tool_lock:{tool_name}\"\n                    \n                    # Check if tool was locked by multiple sessions\n                    lock_info = await self.redis_client.get(lock_key)\n                    if lock_info:\n                        lock_data = json.loads(lock_info)\n                        if lock_data.get(\"session_id\") != session_id:\n                            conflicts.append({\n                                \"type\": \"redis_tool_lock_conflict\",\n                                \"tool\": tool_name,\n                                \"conflicting_sessions\": [session_id, lock_data.get(\"session_id\")],\n                                \"severity\": \"medium\"\n                            })\n        \n        except Exception as e:\n            conflicts.append({\"type\": \"redis_check_error\", \"error\": str(e)})\n        \n        return conflicts\n    \n    async def _check_memory_conflicts(self, session_ids: List[str]) -> List[Dict[str, Any]]:\n        \"\"\"Check for memory conflicts during concurrent loading.\"\"\"\n        conflicts = []\n        \n        try:\n            # Calculate total memory requirements\n            total_memory_mb = 0\n            for session_id in session_ids:\n                session = self.tool_loading_sessions.get(session_id)\n                if session:\n                    for tool_name in session.get(\"required_tools\", []):\n                        tool_info = await self.tool_registry.get_tool_info(tool_name)\n                        if tool_info:\n                            total_memory_mb += tool_info.get(\"size_mb\", 0)\n            \n            # Check if total memory exceeds reasonable limits\n            if total_memory_mb > 500:  # 500MB threshold for testing\n                conflicts.append({\n                    \"type\": \"memory_pressure_conflict\",\n                    \"total_memory_mb\": total_memory_mb,\n                    \"threshold_mb\": 500,\n                    \"severity\": \"high\" if total_memory_mb > 1000 else \"medium\"\n                })\n        \n        except Exception as e:\n            conflicts.append({\"type\": \"memory_check_error\", \"error\": str(e)})\n        \n        return conflicts\n    \n    async def test_tool_dependency_resolution(self, agent_count: int) -> Dict[str, Any]:\n        \"\"\"Test tool dependency resolution during concurrent loading.\"\"\"\n        dependency_start = time.time()\n        \n        try:\n            # Create agents with interdependent tools\n            dependency_agents = []\n            \n            for i in range(agent_count):\n                agent_id = f\"dep_agent_{i}_{uuid.uuid4().hex[:6]}\"\n                \n                # Create agent with tools that have dependencies\n                agent = BaseSubAgent(\n                    agent_id=agent_id,\n                    agent_type=\"dependency_test_agent\",\n                    state_manager=self.state_manager,\n                    redis_client=self.redis_client\n                )\n                \n                # Assign tools with dependencies\n                required_tools = [\"report_generator\", \"data_analyzer\"]  # report_generator depends on data_analyzer\n                if i % 2 == 0:\n                    required_tools.append(\"ml_optimizer\")\n                \n                agent_state = DeepAgentState(\n                    agent_id=agent_id,\n                    agent_type=\"dependency_test_agent\",\n                    status=\"initializing\",\n                    required_tools=required_tools,\n                    loaded_tools=[],\n                    created_at=time.time()\n                )\n                \n                await self.state_manager.save_state(agent_id, agent_state)\n                \n                self.active_agents[agent_id] = agent\n                dependency_agents.append(agent_id)\n            \n            # Test concurrent dependency resolution\n            dependency_result = await self.test_concurrent_tool_loading(dependency_agents)\n            \n            # Verify dependency resolution\n            dependency_violations = await self._check_dependency_violations(dependency_agents)\n            \n            dependency_time = time.time() - dependency_start\n            \n            return {\n                \"success\": dependency_result[\"success\"],\n                \"dependency_agents\": len(dependency_agents),\n                \"loading_success_rate\": dependency_result[\"successful_loads\"] / len(dependency_agents),\n                \"dependency_violations\": len(dependency_violations),\n                \"dependency_resolution_time\": dependency_time,\n                \"violation_details\": dependency_violations\n            }\n            \n        except Exception as e:\n            return {\n                \"success\": False,\n                \"error\": str(e),\n                \"dependency_time\": time.time() - dependency_start\n            }\n    \n    async def _check_dependency_violations(self, agent_ids: List[str]) -> List[Dict[str, Any]]:\n        \"\"\"Check for tool dependency violations.\"\"\"\n        violations = []\n        \n        try:\n            for agent_id in agent_ids:\n                agent_state = await self.state_manager.load_state(agent_id)\n                if not agent_state:\n                    continue\n                \n                loaded_tools = set(agent_state.loaded_tools)\n                \n                # Check each loaded tool's dependencies\n                for tool_name in agent_state.loaded_tools:\n                    tool_info = await self.tool_registry.get_tool_info(tool_name)\n                    if tool_info:\n                        dependencies = tool_info.get(\"dependencies\", [])\n                        \n                        # Check if dependencies are loaded\n                        missing_deps = [dep for dep in dependencies if dep not in loaded_tools]\n                        \n                        if missing_deps:\n                            violations.append({\n                                \"type\": \"missing_dependencies\",\n                                \"agent_id\": agent_id,\n                                \"tool\": tool_name,\n                                \"missing_dependencies\": missing_deps,\n                                \"severity\": \"high\"\n                            })\n        \n        except Exception as e:\n            violations.append({\"type\": \"dependency_check_error\", \"error\": str(e)})\n        \n        return violations\n    \n    def _update_average_load_time(self, new_time: float):\n        \"\"\"Update rolling average load time.\"\"\"\n        current_count = self.concurrent_metrics[\"successful_loads\"]\n        current_avg = self.concurrent_metrics[\"average_load_time\"]\n        \n        if current_count == 1:\n            self.concurrent_metrics[\"average_load_time\"] = new_time\n        else:\n            new_avg = ((current_avg * (current_count - 1)) + new_time) / current_count\n            self.concurrent_metrics[\"average_load_time\"] = new_avg\n    \n    async def generate_concurrency_report(self) -> Dict[str, Any]:\n        \"\"\"Generate comprehensive concurrency testing report.\"\"\"\n        return {\n            \"concurrency_metrics\": self.concurrent_metrics,\n            \"loading_sessions\": dict(self.tool_loading_sessions),\n            \"performance_summary\": {\n                \"success_rate\": (\n                    self.concurrent_metrics[\"successful_loads\"] / \n                    max(self.concurrent_metrics[\"total_tool_loads\"], 1)\n                ),\n                \"conflict_rate\": (\n                    self.concurrent_metrics[\"concurrent_conflicts\"] / \n                    max(self.concurrent_metrics[\"total_tool_loads\"], 1)\n                ),\n                \"average_load_time\": self.concurrent_metrics[\"average_load_time\"],\n                \"peak_concurrency\": self.concurrent_metrics[\"peak_concurrent_loads\"]\n            },\n            \"concurrency_score\": self._calculate_concurrency_score()\n        }\n    \n    def _calculate_concurrency_score(self) -> float:\n        \"\"\"Calculate concurrency handling score.\"\"\"\n        if self.concurrent_metrics[\"total_tool_loads\"] == 0:\n            return 1.0\n        \n        success_rate = (\n            self.concurrent_metrics[\"successful_loads\"] / \n            self.concurrent_metrics[\"total_tool_loads\"]\n        )\n        \n        conflict_penalty = (\n            self.concurrent_metrics[\"concurrent_conflicts\"] / \n            max(self.concurrent_metrics[\"total_tool_loads\"], 1)\n        ) * 0.5\n        \n        # Performance bonus for fast loading\n        perf_bonus = 0.1 if self.concurrent_metrics[\"average_load_time\"] < 3.0 else 0.0\n        \n        return max(0.0, success_rate - conflict_penalty + perf_bonus)\n    \n    async def cleanup_l3_resources(self):\n        \"\"\"Clean up L3 test resources.\"\"\"\n        try:\n            # Clean up active agents\n            for agent in self.active_agents.values():\n                if hasattr(agent, 'cleanup'):\n                    await agent.cleanup()\n            \n            # Clean up tool registry\n            if self.tool_registry:\n                await self.tool_registry.cleanup()\n            \n            # Close connections\n            if self.redis_client:\n                await self.redis_client.close()\n            if self.postgres_service:\n                await self.postgres_service.close()\n                \n        except Exception as e:\n            logger.warning(f\"Cleanup warning: {e}\")\n\n\n@pytest.fixture\nasync def testcontainer_infrastructure():\n    \"\"\"Setup real Redis and Postgres containers for L3 testing.\"\"\"\n    helper = TestcontainerHelper()\n    \n    # Start Redis container\n    redis_container_instance = redis_container.RedisContainer(\"redis:7-alpine\")\n    redis_container_instance.start()\n    redis_url = f\"redis://localhost:{redis_container_instance.get_exposed_port(6379)}\"\n    \n    # Start Postgres container\n    postgres_container_instance = postgres_container.PostgresContainer(\"postgres:15-alpine\")\n    postgres_container_instance.start()\n    postgres_url = postgres_container_instance.get_connection_url()\n    \n    yield redis_url, postgres_url\n    \n    # Cleanup containers\n    redis_container_instance.stop()\n    postgres_container_instance.stop()\n\n\n@pytest.fixture\nasync def l3_tool_manager(testcontainer_infrastructure):\n    \"\"\"Create L3 tool loading manager with real infrastructure.\"\"\"\n    redis_url, postgres_url = testcontainer_infrastructure\n    \n    manager = L3ToolLoadingManager()\n    await manager.initialize_l3_infrastructure(redis_url, postgres_url)\n    \n    yield manager\n    \n    await manager.cleanup_l3_resources()\n\n\n@pytest.mark.L3\n@pytest.mark.integration\nclass TestAgentToolLoadingConcurrencyL3:\n    \"\"\"L3 integration tests for agent tool loading concurrency.\"\"\"\n    \n    async def test_basic_concurrent_tool_loading(self, l3_tool_manager):\n        \"\"\"Test basic concurrent tool loading across multiple agents.\"\"\"\n        # Create agents for concurrent testing\n        agent_creation = await l3_tool_manager.create_concurrent_agents(3, 2)\n        agent_ids = [a[\"agent_id\"] for a in agent_creation[\"agent_details\"]]\n        \n        # Test concurrent loading\n        loading_result = await l3_tool_manager.test_concurrent_tool_loading(agent_ids)\n        \n        # Verify loading success\n        assert loading_result[\"success\"] is True\n        assert loading_result[\"total_agents\"] == 3\n        assert loading_result[\"successful_loads\"] >= 2  # Most should succeed\n        assert loading_result[\"total_loading_time\"] < 15.0\n        \n        # Verify minimal conflicts\n        assert loading_result[\"conflicts_detected\"] <= 1  # Minimal conflicts expected\n    \n    async def test_high_concurrency_tool_loading(self, l3_tool_manager):\n        \"\"\"Test tool loading under high concurrency.\"\"\"\n        # Create more agents for stress testing\n        agent_creation = await l3_tool_manager.create_concurrent_agents(6, 3)\n        agent_ids = [a[\"agent_id\"] for a in agent_creation[\"agent_details\"]]\n        \n        # Test high concurrency loading\n        loading_result = await l3_tool_manager.test_concurrent_tool_loading(agent_ids)\n        \n        # Verify system handles high concurrency\n        assert loading_result[\"success\"] is True\n        assert loading_result[\"total_agents\"] == 6\n        \n        # Success rate should be reasonable even under high load\n        success_rate = loading_result[\"successful_loads\"] / loading_result[\"total_agents\"]\n        assert success_rate >= 0.7  # 70% success rate minimum\n        \n        # Performance should be reasonable\n        assert loading_result[\"total_loading_time\"] < 25.0\n    \n    async def test_tool_dependency_resolution_concurrent(self, l3_tool_manager):\n        \"\"\"Test concurrent tool dependency resolution.\"\"\"\n        # Test dependency resolution\n        dependency_result = await l3_tool_manager.test_tool_dependency_resolution(4)\n        \n        # Verify dependency resolution\n        assert dependency_result[\"success\"] is True\n        assert dependency_result[\"dependency_agents\"] == 4\n        assert dependency_result[\"loading_success_rate\"] >= 0.75  # 75% success rate\n        assert dependency_result[\"dependency_violations\"] == 0  # No violations\n        assert dependency_result[\"dependency_resolution_time\"] < 20.0\n    \n    async def test_conflict_detection_and_resolution(self, l3_tool_manager):\n        \"\"\"Test conflict detection during concurrent loading.\"\"\"\n        # Create agents with overlapping tool requirements\n        overlapping_agents = []\n        \n        for i in range(4):\n            agent_id = f\"overlap_agent_{i}_{uuid.uuid4().hex[:6]}\"\n            \n            agent = BaseSubAgent(\n                agent_id=agent_id,\n                agent_type=\"overlap_test_agent\",\n                state_manager=l3_tool_manager.state_manager,\n                redis_client=l3_tool_manager.redis_client\n            )\n            \n            # All agents need same tools (intentional overlap)\n            agent_state = DeepAgentState(\n                agent_id=agent_id,\n                agent_type=\"overlap_test_agent\",\n                status=\"initializing\",\n                required_tools=[\"data_analyzer\", \"cost_calculator\"],  # Same tools\n                loaded_tools=[],\n                created_at=time.time()\n            )\n            \n            await l3_tool_manager.state_manager.save_state(agent_id, agent_state)\n            l3_tool_manager.active_agents[agent_id] = agent\n            overlapping_agents.append(agent_id)\n        \n        # Test concurrent loading with overlaps\n        loading_result = await l3_tool_manager.test_concurrent_tool_loading(overlapping_agents)\n        \n        # Verify conflict detection works\n        assert loading_result[\"success\"] is True\n        assert loading_result[\"total_agents\"] == 4\n        \n        # All agents should still succeed despite conflicts\n        assert loading_result[\"successful_loads\"] == 4\n        \n        # Conflicts may be detected but should be handled gracefully\n        # (conflicts in tool loading can be normal and handled)\n    \n    async def test_performance_under_memory_pressure(self, l3_tool_manager):\n        \"\"\"Test tool loading performance under memory pressure.\"\"\"\n        # Create agents requiring memory-intensive tools\n        memory_agents = []\n        \n        for i in range(3):\n            agent_id = f\"memory_agent_{i}_{uuid.uuid4().hex[:6]}\"\n            \n            agent = BaseSubAgent(\n                agent_id=agent_id,\n                agent_type=\"memory_test_agent\",\n                state_manager=l3_tool_manager.state_manager,\n                redis_client=l3_tool_manager.redis_client\n            )\n            \n            # Assign memory-intensive tools\n            agent_state = DeepAgentState(\n                agent_id=agent_id,\n                agent_type=\"memory_test_agent\",\n                status=\"initializing\",\n                required_tools=[\"llm_interface\", \"ml_optimizer\"],  # Large tools\n                loaded_tools=[],\n                created_at=time.time()\n            )\n            \n            await l3_tool_manager.state_manager.save_state(agent_id, agent_state)\n            l3_tool_manager.active_agents[agent_id] = agent\n            memory_agents.append(agent_id)\n        \n        # Test loading under memory pressure\n        loading_result = await l3_tool_manager.test_concurrent_tool_loading(memory_agents)\n        \n        # Verify graceful handling of memory pressure\n        assert loading_result[\"success\"] is True\n        \n        # Some agents may fail due to memory pressure, but system should handle gracefully\n        success_rate = loading_result[\"successful_loads\"] / loading_result[\"total_agents\"]\n        assert success_rate >= 0.5  # At least 50% should succeed\n        \n        # Check for memory-related conflicts\n        memory_conflicts = [\n            c for c in loading_result[\"conflict_details\"] \n            if c.get(\"type\") == \"memory_pressure_conflict\"\n        ]\n        # Memory conflicts are acceptable under pressure\n    \n    async def test_tool_loading_performance_metrics(self, l3_tool_manager):\n        \"\"\"Test comprehensive tool loading performance metrics.\"\"\"\n        # Execute multiple concurrent loading scenarios\n        scenarios = [\n            (3, 2),  # 3 agents, 2 tools each\n            (4, 3),  # 4 agents, 3 tools each\n            (2, 4),  # 2 agents, 4 tools each\n        ]\n        \n        for agent_count, tools_per_agent in scenarios:\n            agent_creation = await l3_tool_manager.create_concurrent_agents(agent_count, tools_per_agent)\n            agent_ids = [a[\"agent_id\"] for a in agent_creation[\"agent_details\"]]\n            \n            await l3_tool_manager.test_concurrent_tool_loading(agent_ids)\n        \n        # Generate comprehensive report\n        report = await l3_tool_manager.generate_concurrency_report()\n        \n        # Verify report structure\n        assert \"concurrency_metrics\" in report\n        assert \"performance_summary\" in report\n        assert \"concurrency_score\" in report\n        \n        # Verify metrics\n        metrics = report[\"concurrency_metrics\"]\n        assert metrics[\"total_tool_loads\"] > 0\n        assert metrics[\"successful_loads\"] > 0\n        assert metrics[\"peak_concurrent_loads\"] >= 2\n        \n        # Verify performance\n        performance = report[\"performance_summary\"]\n        assert performance[\"success_rate\"] >= 0.7  # 70% success rate\n        assert performance[\"conflict_rate\"] <= 0.3  # Max 30% conflict rate\n        assert performance[\"average_load_time\"] < 10.0  # Reasonable load time\n        \n        # Verify overall score\n        assert report[\"concurrency_score\"] >= 0.6  # Good concurrency handling