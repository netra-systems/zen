"""
CRITICAL INTEGRATION TEST #10: Multi-Agent Coordination Initialization

BVJ:
- Segment: Platform/Internal (foundation for ALL customer segments)
- Business Goal: Platform Stability - Prevent $35K MRR loss from coordination failures
- Value Impact: Ensures start multiple agents → establish communication → verify message passing
- Revenue Impact: Prevents customer requests from failing due to broken agent coordination

REQUIREMENTS:
- Start multiple agents simultaneously
- Establish inter-agent communication channels
- Verify message passing between agents
- Validate coordination protocols
- Coordination setup within 15 seconds
- 100% message delivery success rate
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Set testing environment
import os
os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.agents.base_agent import BaseSubAgent
from app.agents.supervisor.agent_registry import AgentRegistry
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher
from app.ws_manager import WebSocketManager
from app.logging_config import central_logger
from test_framework.mock_utils import mock_justified

logger = central_logger.get_logger(__name__)


class MockCoordinationAgent(BaseSubAgent):
    """Mock agent with coordination capabilities."""
    
    def __init__(self, name: str, llm_manager=None):
        super().__init__(llm_manager, name=name)
        self.peer_agents = {}
        self.message_inbox = []
        self.message_outbox = []
        self.coordination_status = "initializing"
        self.coordination_channels = {}
        self.heartbeat_interval = 1.0
        self.last_heartbeat = None
    
    async def execute(self, request: Dict[str, Any], state: DeepAgentState) -> Dict[str, Any]:
        """Execute with coordination tracking."""
        execution_id = str(uuid.uuid4())
        
        # Check for coordination requests
        if "coordination_action" in request:
            return await self._handle_coordination_action(request, execution_id)
        
        # Regular execution
        return {
            "status": "success",
            "execution_id": execution_id,
            "agent": self.name,
            "coordination_status": self.coordination_status,
            "peer_count": len(self.peer_agents)
        }
    
    async def _handle_coordination_action(self, request: Dict[str, Any], execution_id: str) -> Dict[str, Any]:
        """Handle coordination-specific actions."""
        action = request["coordination_action"]
        
        if action == "register_peer":
            peer_name = request["peer_name"]
            peer_agent = request["peer_agent"]
            await self.register_peer(peer_name, peer_agent)
            
        elif action == "send_message":
            target = request["target"]
            message = request["message"]
            await self.send_message(target, message)
            
        elif action == "broadcast":
            message = request["message"]
            await self.broadcast_message(message)
            
        elif action == "heartbeat":
            await self.send_heartbeat()
        
        return {
            "status": "success",
            "execution_id": execution_id,
            "action": action,
            "coordination_status": self.coordination_status
        }
    
    async def register_peer(self, peer_name: str, peer_agent: 'MockCoordinationAgent'):
        """Register a peer agent for coordination."""
        self.peer_agents[peer_name] = peer_agent
        
        # Establish bidirectional channel
        channel_id = f"{self.name}-{peer_name}"
        self.coordination_channels[peer_name] = {
            "channel_id": channel_id,
            "established": datetime.now(timezone.utc),
            "message_count": 0,
            "last_activity": datetime.now(timezone.utc)
        }
        
        # Update coordination status
        if len(self.peer_agents) > 0:
            self.coordination_status = "coordinating"
    
    async def send_message(self, target: str, message: Dict[str, Any]) -> bool:
        """Send message to specific peer agent."""
        if target not in self.peer_agents:
            return False
        
        target_agent = self.peer_agents[target]
        
        # Create message envelope
        envelope = {
            "id": str(uuid.uuid4()),
            "from": self.name,
            "to": target,
            "message": message,
            "timestamp": datetime.now(timezone.utc),
            "type": "direct"
        }
        
        # Send to target agent's inbox
        target_agent.message_inbox.append(envelope)
        self.message_outbox.append(envelope)
        
        # Update channel statistics
        if target in self.coordination_channels:
            self.coordination_channels[target]["message_count"] += 1
            self.coordination_channels[target]["last_activity"] = datetime.now(timezone.utc)
        
        return True
    
    async def broadcast_message(self, message: Dict[str, Any]) -> int:
        """Broadcast message to all peer agents."""
        sent_count = 0
        
        for peer_name in self.peer_agents:
            success = await self.send_message(peer_name, message)
            if success:
                sent_count += 1
        
        return sent_count
    
    async def send_heartbeat(self):
        """Send heartbeat to all peer agents."""
        heartbeat_message = {
            "type": "heartbeat",
            "agent": self.name,
            "status": self.coordination_status,
            "timestamp": datetime.now(timezone.utc),
            "peer_count": len(self.peer_agents)
        }
        
        await self.broadcast_message(heartbeat_message)
        self.last_heartbeat = datetime.now(timezone.utc)
    
    def get_received_messages(self, message_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get received messages, optionally filtered by type."""
        if message_type:
            return [msg for msg in self.message_inbox 
                   if msg["message"].get("type") == message_type]
        return self.message_inbox
    
    def get_coordination_stats(self) -> Dict[str, Any]:
        """Get coordination statistics."""
        return {
            "agent_name": self.name,
            "coordination_status": self.coordination_status,
            "peer_count": len(self.peer_agents),
            "messages_sent": len(self.message_outbox),
            "messages_received": len(self.message_inbox),
            "channels_established": len(self.coordination_channels),
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None
        }


class MockCoordinationRegistry(AgentRegistry):
    """Extended registry with coordination capabilities."""
    
    def __init__(self, llm_manager, tool_dispatcher):
        super().__init__(llm_manager, tool_dispatcher)
        self.coordination_network = {}
        self.coordination_metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "coordination_latency": [],
            "network_topology": {}
        }
    
    def register_coordination_agent(self, name: str, agent: MockCoordinationAgent):
        """Register agent with coordination capabilities."""
        self.register(name, agent)
        self.coordination_network[name] = agent
    
    async def establish_coordination_network(self) -> Dict[str, Any]:
        """Establish coordination network between all agents."""
        start_time = time.time()
        
        agent_names = list(self.coordination_network.keys())
        
        # Create all-to-all coordination network
        for i, agent_name in enumerate(agent_names):
            agent = self.coordination_network[agent_name]
            
            # Register all other agents as peers
            for j, peer_name in enumerate(agent_names):
                if i != j:
                    peer_agent = self.coordination_network[peer_name]
                    await agent.register_peer(peer_name, peer_agent)
        
        # Update network topology
        self.coordination_metrics["network_topology"] = {
            "nodes": len(agent_names),
            "edges": len(agent_names) * (len(agent_names) - 1),
            "topology": "full_mesh",
            "establishment_time": time.time() - start_time
        }
        
        return self.coordination_metrics["network_topology"]
    
    async def validate_network_connectivity(self) -> Dict[str, Any]:
        """Validate connectivity across the coordination network."""
        connectivity_results = {}
        
        for agent_name, agent in self.coordination_network.items():
            # Test message sending to all peers
            peer_connectivity = {}
            
            for peer_name in agent.peer_agents:
                test_message = {
                    "type": "connectivity_test",
                    "test_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc)
                }
                
                start_time = time.time()
                success = await agent.send_message(peer_name, test_message)
                latency = time.time() - start_time
                
                peer_connectivity[peer_name] = {
                    "success": success,
                    "latency": latency
                }
                
                if success:
                    self.coordination_metrics["messages_sent"] += 1
                    self.coordination_metrics["coordination_latency"].append(latency)
            
            connectivity_results[agent_name] = peer_connectivity
        
        # Count received messages
        for agent in self.coordination_network.values():
            connectivity_messages = agent.get_received_messages("connectivity_test")
            self.coordination_metrics["messages_received"] += len(connectivity_messages)
        
        return connectivity_results
    
    def get_network_metrics(self) -> Dict[str, Any]:
        """Get comprehensive network coordination metrics."""
        if self.coordination_metrics["coordination_latency"]:
            avg_latency = sum(self.coordination_metrics["coordination_latency"]) / len(self.coordination_metrics["coordination_latency"])
            max_latency = max(self.coordination_metrics["coordination_latency"])
        else:
            avg_latency = 0
            max_latency = 0
        
        return {
            "network_topology": self.coordination_metrics["network_topology"],
            "messages_sent": self.coordination_metrics["messages_sent"],
            "messages_received": self.coordination_metrics["messages_received"],
            "avg_coordination_latency": avg_latency,
            "max_coordination_latency": max_latency,
            "message_delivery_rate": (self.coordination_metrics["messages_received"] / max(1, self.coordination_metrics["messages_sent"])) * 100
        }


class TestMultiAgentCoordinationInit:
    """BVJ: Protects $35K MRR through reliable multi-agent coordination initialization."""

    @pytest.fixture
    @mock_justified("LLM service external dependency for coordination testing")
    def llm_manager_mock(self):
        """Mock LLM manager for coordination testing."""
        llm_mock = Mock(spec=LLMManager)
        llm_mock.generate_response = AsyncMock(return_value={
            "content": "Coordination response",
            "usage": {"prompt_tokens": 35, "completion_tokens": 12}
        })
        return llm_mock

    @pytest.fixture
    @mock_justified("Tool dispatcher external dependency for coordination")
    def tool_dispatcher_mock(self):
        """Mock tool dispatcher for coordination testing."""
        dispatcher_mock = Mock(spec=ToolDispatcher)
        dispatcher_mock.dispatch = AsyncMock(return_value={"status": "success"})
        return dispatcher_mock

    @pytest.fixture
    @mock_justified("WebSocket manager external dependency for agent communication")
    def websocket_manager_mock(self):
        """Mock WebSocket manager for coordination testing."""
        ws_mock = Mock(spec=WebSocketManager)
        ws_mock.send_to_user = AsyncMock(return_value=True)
        return ws_mock

    @pytest.fixture
    def coordination_registry(self, llm_manager_mock, tool_dispatcher_mock):
        """Create coordination registry with mock agents."""
        registry = MockCoordinationRegistry(llm_manager_mock, tool_dispatcher_mock)
        
        # Create coordination agents
        coordination_agents = [
            MockCoordinationAgent("coordinator_triage", llm_manager_mock),
            MockCoordinationAgent("coordinator_data", llm_manager_mock),
            MockCoordinationAgent("coordinator_optimization", llm_manager_mock),
            MockCoordinationAgent("coordinator_actions", llm_manager_mock),
            MockCoordinationAgent("coordinator_reporting", llm_manager_mock)
        ]
        
        # Register coordination agents
        for agent in coordination_agents:
            registry.register_coordination_agent(agent.name, agent)
        
        return registry

    @pytest.mark.asyncio
    async def test_01_multi_agent_simultaneous_startup(self, coordination_registry):
        """BVJ: Validates multiple agents can start simultaneously without conflicts."""
        start_time = time.time()
        
        # Step 1: Validate all coordination agents are registered
        coordination_agents = list(coordination_registry.coordination_network.keys())
        expected_agents = ["coordinator_triage", "coordinator_data", "coordinator_optimization", 
                          "coordinator_actions", "coordinator_reporting"]
        
        assert len(coordination_agents) == 5, f"Expected 5 coordination agents, got {len(coordination_agents)}"
        
        for expected_agent in expected_agents:
            assert expected_agent in coordination_agents, f"Agent {expected_agent} not registered"
        
        # Step 2: Execute simultaneous startup operations
        startup_operations = []
        
        for agent_name in coordination_agents:
            agent = coordination_registry.coordination_network[agent_name]
            
            startup_operations.append(agent.execute({
                "operation": "startup",
                "agent_id": agent_name,
                "startup_mode": "coordination"
            }, DeepAgentState()))
        
        # Execute all startups concurrently
        startup_results = await asyncio.gather(*startup_operations)
        startup_time = time.time() - start_time
        
        # Step 3: Validate startup results
        assert len(startup_results) == 5, f"Expected 5 startup results, got {len(startup_results)}"
        
        for i, result in enumerate(startup_results):
            assert result["status"] == "success", f"Agent {i} startup failed"
            assert result["agent"] in expected_agents, f"Agent {i} identity mismatch"
        
        # Step 4: Validate startup timing
        assert startup_time < 5.0, f"Simultaneous startup took {startup_time:.2f}s, exceeds 5s limit"
        
        # Step 5: Verify agents are in correct initial state
        for agent_name in coordination_agents:
            agent = coordination_registry.coordination_network[agent_name]
            assert agent.coordination_status == "initializing", f"Agent {agent_name} wrong initial status"
            assert len(agent.peer_agents) == 0, f"Agent {agent_name} has unexpected peers"
        
        logger.info(f"Simultaneous startup validated: {len(coordination_agents)} agents in {startup_time:.2f}s")

    @pytest.mark.asyncio
    async def test_02_inter_agent_communication_channel_establishment(self, coordination_registry):
        """BVJ: Validates communication channels are established between all agents."""
        start_time = time.time()
        
        # Step 1: Establish coordination network
        network_topology = await coordination_registry.establish_coordination_network()
        
        # Step 2: Validate network topology
        assert network_topology["nodes"] == 5, f"Expected 5 nodes, got {network_topology['nodes']}"
        assert network_topology["edges"] == 20, f"Expected 20 edges (5*4), got {network_topology['edges']}"
        assert network_topology["topology"] == "full_mesh", f"Wrong topology: {network_topology['topology']}"
        
        establishment_time = network_topology["establishment_time"]
        assert establishment_time < 15.0, f"Network establishment took {establishment_time:.2f}s, exceeds 15s limit"
        
        # Step 3: Validate each agent has correct peer connections
        agent_names = list(coordination_registry.coordination_network.keys())
        
        for agent_name in agent_names:
            agent = coordination_registry.coordination_network[agent_name]
            
            # Verify peer count
            expected_peers = len(agent_names) - 1  # All agents except self
            assert len(agent.peer_agents) == expected_peers, \
                f"Agent {agent_name} has {len(agent.peer_agents)} peers, expected {expected_peers}"
            
            # Verify coordination status updated
            assert agent.coordination_status == "coordinating", \
                f"Agent {agent_name} status {agent.coordination_status}, expected 'coordinating'"
            
            # Verify coordination channels
            assert len(agent.coordination_channels) == expected_peers, \
                f"Agent {agent_name} has {len(agent.coordination_channels)} channels, expected {expected_peers}"
            
            # Verify all other agents are peers
            for other_agent_name in agent_names:
                if other_agent_name != agent_name:
                    assert other_agent_name in agent.peer_agents, \
                        f"Agent {agent_name} missing peer {other_agent_name}"
        
        logger.info(f"Communication channels established: {network_topology['nodes']} nodes, {network_topology['edges']} connections in {establishment_time:.2f}s")

    @pytest.mark.asyncio
    async def test_03_message_passing_validation(self, coordination_registry):
        """BVJ: Validates messages can be passed reliably between agents."""
        # Step 1: Establish coordination network
        await coordination_registry.establish_coordination_network()
        
        # Step 2: Execute comprehensive message passing tests
        connectivity_results = await coordination_registry.validate_network_connectivity()
        
        # Step 3: Validate connectivity results
        agent_names = list(coordination_registry.coordination_network.keys())
        
        for sender_name, peer_connectivity in connectivity_results.items():
            # Verify sender tested all peers
            expected_peer_count = len(agent_names) - 1
            assert len(peer_connectivity) == expected_peer_count, \
                f"Sender {sender_name} tested {len(peer_connectivity)} peers, expected {expected_peer_count}"
            
            # Verify all messages sent successfully
            for peer_name, connectivity_result in peer_connectivity.items():
                assert connectivity_result["success"], \
                    f"Message from {sender_name} to {peer_name} failed"
                assert connectivity_result["latency"] < 1.0, \
                    f"Message latency {connectivity_result['latency']:.3f}s too high"
        
        # Step 4: Validate message delivery metrics
        network_metrics = coordination_registry.get_network_metrics()
        
        assert network_metrics["message_delivery_rate"] == 100.0, \
            f"Message delivery rate {network_metrics['message_delivery_rate']}% below 100%"
        
        expected_total_messages = len(agent_names) * (len(agent_names) - 1)
        assert network_metrics["messages_sent"] == expected_total_messages, \
            f"Expected {expected_total_messages} messages sent, got {network_metrics['messages_sent']}"
        assert network_metrics["messages_received"] == expected_total_messages, \
            f"Expected {expected_total_messages} messages received, got {network_metrics['messages_received']}"
        
        # Step 5: Validate message latency performance
        assert network_metrics["avg_coordination_latency"] < 0.1, \
            f"Average coordination latency {network_metrics['avg_coordination_latency']:.3f}s too high"
        assert network_metrics["max_coordination_latency"] < 0.5, \
            f"Max coordination latency {network_metrics['max_coordination_latency']:.3f}s too high"
        
        logger.info(f"Message passing validated: {network_metrics['message_delivery_rate']}% delivery rate, {network_metrics['avg_coordination_latency']:.3f}s avg latency")

    @pytest.mark.asyncio
    async def test_04_coordination_protocol_validation(self, coordination_registry):
        """BVJ: Validates coordination protocols work correctly for complex scenarios."""
        # Step 1: Establish coordination network
        await coordination_registry.establish_coordination_network()
        
        # Step 2: Test heartbeat protocol
        agent_names = list(coordination_registry.coordination_network.keys())
        
        # Send heartbeats from all agents
        heartbeat_tasks = []
        for agent_name in agent_names:
            agent = coordination_registry.coordination_network[agent_name]
            heartbeat_tasks.append(agent.send_heartbeat())
        
        await asyncio.gather(*heartbeat_tasks)
        
        # Step 3: Validate heartbeat reception
        for agent_name in agent_names:
            agent = coordination_registry.coordination_network[agent_name]
            heartbeat_messages = agent.get_received_messages("heartbeat")
            
            # Should receive heartbeats from all other agents
            expected_heartbeats = len(agent_names) - 1
            assert len(heartbeat_messages) == expected_heartbeats, \
                f"Agent {agent_name} received {len(heartbeat_messages)} heartbeats, expected {expected_heartbeats}"
            
            # Verify heartbeat content
            for heartbeat in heartbeat_messages:
                assert "type" in heartbeat["message"], "Heartbeat missing type"
                assert heartbeat["message"]["type"] == "heartbeat", "Wrong message type"
                assert "agent" in heartbeat["message"], "Heartbeat missing agent"
                assert "status" in heartbeat["message"], "Heartbeat missing status"
        
        # Step 4: Test broadcast protocol
        broadcast_agent = coordination_registry.coordination_network[agent_names[0]]
        broadcast_message = {
            "type": "coordination_update",
            "update_id": str(uuid.uuid4()),
            "content": "System-wide coordination update",
            "priority": "high"
        }
        
        broadcast_count = await broadcast_agent.broadcast_message(broadcast_message)
        
        # Step 5: Validate broadcast reception
        expected_recipients = len(agent_names) - 1
        assert broadcast_count == expected_recipients, \
            f"Broadcast sent to {broadcast_count} agents, expected {expected_recipients}"
        
        # Verify all other agents received broadcast
        for i, agent_name in enumerate(agent_names[1:]):  # Skip broadcast sender
            agent = coordination_registry.coordination_network[agent_name]
            coordination_updates = agent.get_received_messages("coordination_update")
            
            assert len(coordination_updates) >= 1, f"Agent {agent_name} didn't receive broadcast"
            
            # Find the specific broadcast message
            received_broadcast = None
            for update in coordination_updates:
                if update["message"]["update_id"] == broadcast_message["update_id"]:
                    received_broadcast = update
                    break
            
            assert received_broadcast is not None, f"Agent {agent_name} didn't receive specific broadcast"
            assert received_broadcast["message"]["content"] == broadcast_message["content"], \
                "Broadcast content corrupted"
        
        logger.info(f"Coordination protocols validated: heartbeat and broadcast working across {len(agent_names)} agents")

    @pytest.mark.asyncio
    async def test_05_coordination_performance_under_load(self, coordination_registry):
        """BVJ: Validates coordination maintains performance under message load."""
        # Step 1: Establish coordination network
        await coordination_registry.establish_coordination_network()
        
        # Step 2: Generate high message load
        load_test_duration = 10.0  # seconds
        messages_per_second = 50
        total_messages = int(load_test_duration * messages_per_second)
        
        agent_names = list(coordination_registry.coordination_network.keys())
        
        async def generate_message_load(agent_name: str, message_count: int):
            """Generate sustained message load from specific agent."""
            agent = coordination_registry.coordination_network[agent_name]
            
            for i in range(message_count):
                # Select random target agent
                target_agents = [name for name in agent_names if name != agent_name]
                target = target_agents[i % len(target_agents)]
                
                # Send load test message
                load_message = {
                    "type": "load_test",
                    "message_id": f"{agent_name}_msg_{i}",
                    "sequence": i,
                    "timestamp": datetime.now(timezone.utc)
                }
                
                await agent.send_message(target, load_message)
                
                # Small delay to maintain consistent rate
                await asyncio.sleep(1.0 / messages_per_second)
        
        # Step 3: Execute load test
        start_time = time.time()
        
        load_tasks = []
        messages_per_agent = total_messages // len(agent_names)
        
        for agent_name in agent_names:
            load_tasks.append(generate_message_load(agent_name, messages_per_agent))
        
        await asyncio.gather(*load_tasks)
        
        actual_duration = time.time() - start_time
        
        # Step 4: Validate load test performance
        assert actual_duration <= load_test_duration * 1.2, \
            f"Load test took {actual_duration:.2f}s, expected ~{load_test_duration}s"
        
        # Step 5: Validate message delivery under load
        total_sent = 0
        total_received = 0
        
        for agent_name in agent_names:
            agent = coordination_registry.coordination_network[agent_name]
            
            # Count load test messages
            sent_messages = [msg for msg in agent.message_outbox 
                           if msg["message"].get("type") == "load_test"]
            received_messages = agent.get_received_messages("load_test")
            
            total_sent += len(sent_messages)
            total_received += len(received_messages)
        
        # Calculate delivery rate under load
        delivery_rate = (total_received / max(1, total_sent)) * 100
        throughput = total_received / actual_duration
        
        # Step 6: Validate performance metrics
        assert delivery_rate >= 95.0, f"Message delivery rate under load {delivery_rate:.1f}% below 95%"
        assert throughput >= messages_per_second * 0.8, \
            f"Message throughput {throughput:.1f} msg/sec below target {messages_per_second * 0.8}"
        
        # Step 7: Validate coordination stability under load
        for agent_name in agent_names:
            agent = coordination_registry.coordination_network[agent_name]
            assert agent.coordination_status == "coordinating", \
                f"Agent {agent_name} coordination status degraded under load"
            assert len(agent.peer_agents) == len(agent_names) - 1, \
                f"Agent {agent_name} lost peer connections under load"
        
        logger.info(f"Load test validated: {delivery_rate:.1f}% delivery rate, {throughput:.1f} msg/sec throughput")

    @pytest.mark.asyncio
    async def test_06_coordination_fault_tolerance(self, coordination_registry):
        """BVJ: Validates coordination system tolerates agent failures gracefully."""
        # Step 1: Establish coordination network
        await coordination_registry.establish_coordination_network()
        
        agent_names = list(coordination_registry.coordination_network.keys())
        
        # Step 2: Simulate agent failure by removing from network
        failed_agent_name = agent_names[0]
        failed_agent = coordination_registry.coordination_network[failed_agent_name]
        
        # Remove failed agent from all peer lists
        for agent_name in agent_names[1:]:
            agent = coordination_registry.coordination_network[agent_name]
            if failed_agent_name in agent.peer_agents:
                del agent.peer_agents[failed_agent_name]
            if failed_agent_name in agent.coordination_channels:
                del agent.coordination_channels[failed_agent_name]
        
        # Step 3: Test coordination continues among remaining agents
        remaining_agents = agent_names[1:]
        
        # Test message passing among remaining agents
        fault_tolerance_messages = []
        
        for sender_name in remaining_agents[:2]:  # Test with first 2 remaining agents
            sender = coordination_registry.coordination_network[sender_name]
            
            for target_name in remaining_agents:
                if target_name != sender_name:
                    fault_message = {
                        "type": "fault_tolerance_test",
                        "sender": sender_name,
                        "test_after_failure": True
                    }
                    
                    success = await sender.send_message(target_name, fault_message)
                    fault_tolerance_messages.append({
                        "sender": sender_name,
                        "target": target_name,
                        "success": success
                    })
        
        # Step 4: Validate fault tolerance
        successful_messages = sum(1 for msg in fault_tolerance_messages if msg["success"])
        total_messages = len(fault_tolerance_messages)
        
        fault_tolerance_rate = (successful_messages / max(1, total_messages)) * 100
        
        assert fault_tolerance_rate == 100.0, \
            f"Fault tolerance rate {fault_tolerance_rate}% below 100%"
        
        # Step 5: Validate remaining agents maintain coordination
        for agent_name in remaining_agents:
            agent = coordination_registry.coordination_network[agent_name]
            
            # Verify agent still operational
            assert agent.coordination_status == "coordinating", \
                f"Agent {agent_name} status degraded after failure"
            
            # Verify peer count adjusted correctly
            expected_peers = len(remaining_agents) - 1
            assert len(agent.peer_agents) == expected_peers, \
                f"Agent {agent_name} peer count incorrect after failure"
        
        # Step 6: Test network recovery (simulated agent restart)
        # Re-add failed agent to network
        coordination_registry.coordination_network[failed_agent_name] = failed_agent
        
        # Re-establish connections for recovered agent
        for peer_name in remaining_agents:
            peer_agent = coordination_registry.coordination_network[peer_name]
            await failed_agent.register_peer(peer_name, peer_agent)
            await peer_agent.register_peer(failed_agent_name, failed_agent)
        
        # Validate recovery
        assert len(failed_agent.peer_agents) == len(remaining_agents), \
            "Failed agent didn't recover peer connections"
        
        logger.info(f"Fault tolerance validated: {fault_tolerance_rate}% message success after agent failure")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])