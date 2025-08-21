"""
Agent Communication Integration Tests

BVJ:
- Segment: Platform/Internal (foundation for ALL customer segments)
- Business Goal: Platform Stability - Prevent $35K MRR loss from coordination failures
- Value Impact: Validates inter-agent communication channels and message passing
- Revenue Impact: Ensures reliable agent communication for coordinated workflows

REQUIREMENTS:
- Establish inter-agent communication channels
- Verify message passing between agents
- 100% message delivery success rate
- Communication channel reliability
"""

import pytest
import asyncio
from datetime import datetime, timezone

from .shared_fixtures import coordination_infrastructure, coordination_agents


class TestAgentCommunication:
    """BVJ: Validates inter-agent communication channels and message passing."""

    @pytest.mark.asyncio
    async def test_inter_agent_message_passing(self, coordination_agents):
        """BVJ: Validates message passing between agents works correctly."""
        agents = list(coordination_agents.values())
        sender = agents[0]
        receiver = agents[1]
        
        message = {"type": "test", "content": "Hello from agent coordination test"}
        
        await sender.send_message(receiver.name, message)
        
        assert len(sender.message_outbox) == 1
        assert len(receiver.message_inbox) == 1
        
        received_message = receiver.message_inbox[0]
        assert received_message["message"]["content"] == message["content"]

    @pytest.mark.asyncio
    async def test_broadcast_message_delivery(self, coordination_agents):
        """BVJ: Validates broadcast messages are delivered to all agents."""
        agents = list(coordination_agents.values())
        broadcaster = agents[0]
        
        broadcast_message = {"type": "broadcast", "content": "Broadcast test message"}
        
        await broadcaster.broadcast_message(broadcast_message)
        
        # Check all other agents received the message
        for i in range(1, len(agents)):
            receiver = agents[i]
            assert len(receiver.message_inbox) == 1
            received = receiver.message_inbox[0]
            assert received["message"]["content"] == broadcast_message["content"]

    @pytest.mark.asyncio
    async def test_message_delivery_success_rate(self, coordination_agents):
        """BVJ: Validates 100% message delivery success rate."""
        agents = list(coordination_agents.values())
        sender = agents[0]
        receivers = agents[1:]
        
        total_messages = 10
        for i in range(total_messages):
            for receiver in receivers:
                message = {"id": i, "content": f"Message {i}"}
                await sender.send_message(receiver.name, message)
        
        # Verify all messages delivered
        expected_messages_per_receiver = total_messages
        for receiver in receivers:
            assert len(receiver.message_inbox) == expected_messages_per_receiver

    @pytest.mark.asyncio
    async def test_communication_channel_establishment(self, coordination_agents):
        """BVJ: Validates communication channels are properly established."""
        agents = list(coordination_agents.values())
        
        for agent in agents:
            # Each agent should have channels to all other agents
            expected_channels = len(agents) - 1
            assert len(agent.coordination_channels) == expected_channels
            
            # All channels should be active
            for channel_status in agent.coordination_channels.values():
                assert channel_status["status"] == "active"

    @pytest.mark.asyncio
    async def test_message_envelope_structure(self, coordination_agents):
        """BVJ: Validates message envelope contains required metadata."""
        agents = list(coordination_agents.values())
        sender = agents[0]
        receiver = agents[1]
        
        message = {"content": "Envelope structure test"}
        await sender.send_message(receiver.name, message)
        
        envelope = receiver.message_inbox[0]
        assert "from" in envelope
        assert "to" in envelope
        assert "message" in envelope
        assert "timestamp" in envelope
        assert "message_id" in envelope
        
        assert envelope["from"] == sender.name
        assert envelope["to"] == receiver.name

    @pytest.mark.asyncio
    async def test_heartbeat_communication(self, coordination_agents):
        """BVJ: Validates heartbeat communication between agents."""
        agents = list(coordination_agents.values())
        heartbeat_sender = agents[0]
        
        await heartbeat_sender.send_heartbeat()
        
        assert heartbeat_sender.last_heartbeat is not None
        
        # All other agents should receive heartbeat
        for i in range(1, len(agents)):
            receiver = agents[i]
            assert len(receiver.message_inbox) == 1
            heartbeat_msg = receiver.message_inbox[0]["message"]
            assert heartbeat_msg["type"] == "heartbeat"
            assert heartbeat_msg["agent"] == heartbeat_sender.name

    @pytest.mark.asyncio
    async def test_concurrent_message_handling(self, coordination_agents):
        """BVJ: Validates concurrent message handling works correctly."""
        agents = list(coordination_agents.values())
        sender = agents[0]
        receivers = agents[1:]
        
        # Send messages concurrently
        tasks = []
        for i, receiver in enumerate(receivers):
            message = {"id": i, "content": f"Concurrent message {i}"}
            task = sender.send_message(receiver.name, message)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify all messages delivered
        for receiver in receivers:
            assert len(receiver.message_inbox) == 1

    @pytest.mark.asyncio
    async def test_bidirectional_communication(self, coordination_agents):
        """BVJ: Validates bidirectional communication between agents."""
        agents = list(coordination_agents.values())
        agent_a = agents[0]
        agent_b = agents[1]
        
        # A sends to B
        message_a_to_b = {"content": "Message from A to B"}
        await agent_a.send_message(agent_b.name, message_a_to_b)
        
        # B sends to A
        message_b_to_a = {"content": "Message from B to A"}
        await agent_b.send_message(agent_a.name, message_b_to_a)
        
        # Both should have sent and received
        assert len(agent_a.message_outbox) == 1
        assert len(agent_a.message_inbox) == 1
        assert len(agent_b.message_outbox) == 1
        assert len(agent_b.message_inbox) == 1

    @pytest.mark.asyncio
    async def test_message_ordering_preservation(self, coordination_agents):
        """BVJ: Validates message ordering is preserved in delivery."""
        agents = list(coordination_agents.values())
        sender = agents[0]
        receiver = agents[1]
        
        # Send multiple messages in sequence
        messages = [{"id": i, "content": f"Ordered message {i}"} for i in range(5)]
        
        for message in messages:
            await sender.send_message(receiver.name, message)
        
        # Verify messages received in order
        assert len(receiver.message_inbox) == 5
        for i, received_envelope in enumerate(receiver.message_inbox):
            assert received_envelope["message"]["id"] == i

    @pytest.mark.asyncio
    async def test_communication_reliability_under_load(self, coordination_infrastructure):
        """BVJ: Validates communication reliability under high message load."""
        agents = await coordination_infrastructure.create_agent_coordination_scenario(5)
        
        message_count = 50
        agents_list = list(agents.values())
        
        # Generate high message volume
        tasks = []
        for i in range(message_count):
            sender = agents_list[i % len(agents_list)]
            receiver = agents_list[(i + 1) % len(agents_list)]
            message = {"load_test": True, "message_id": i}
            
            task = sender.send_message(receiver.name, message)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Verify all messages delivered
        total_received = sum(len(agent.message_inbox) for agent in agents_list)
        assert total_received == message_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])