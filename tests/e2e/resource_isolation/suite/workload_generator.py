"""
Workload Generator for Resource Isolation Testing

Generates various workload patterns for testing tenant isolation.
"""

import asyncio
import time
import json
import logging
from typing import Dict, Any

import websockets

from ..test_infrastructure import TenantAgent

logger = logging.getLogger(__name__)

class WorkloadGenerator:
    """Generate various workload patterns for tenant agents."""
    
    async def generate_workload(self, agent: TenantAgent, workload_type: str, 
                              duration: float, intensity: str = "normal") -> Dict[str, Any]:
        """Generate workload for a tenant agent."""
        if not agent.connection:
            raise RuntimeError(f"No connection for agent {agent.tenant_id}")
        
        if workload_type == "normal":
            return await self._generate_normal_workload(agent, duration)
        elif workload_type == "heavy":
            return await self._generate_heavy_workload(agent, duration, intensity)
        elif workload_type == "noisy":
            return await self._generate_noisy_workload(agent, duration, intensity)
        elif workload_type == "mixed":
            return await self._generate_mixed_workload(agent, duration)
        else:
            raise ValueError(f"Unknown workload type: {workload_type}")

    async def _generate_normal_workload(self, agent: TenantAgent, duration: float) -> Dict[str, Any]:
        """Generate normal workload pattern."""
        start_time = time.time()
        messages_sent = 0
        responses_received = 0
        
        end_time = start_time + duration
        
        while time.time() < end_time:
            try:
                # Send a normal message
                message = {
                    "type": "user_message",
                    "content": f"Normal workload message {messages_sent + 1}",
                    "message_id": f"{agent.tenant_id}-normal-{messages_sent}",
                    "timestamp": time.time()
                }
                
                await agent.connection.send(json.dumps(message))
                messages_sent += 1
                
                # Try to receive response
                try:
                    response = await asyncio.wait_for(agent.connection.recv(), timeout=1.0)
                    responses_received += 1
                except asyncio.TimeoutError:
                    pass
                
                # Normal workload: 1 message per second
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in normal workload for {agent.tenant_id}: {e}")
                break
        
        return {
            "workload_type": "normal",
            "duration": time.time() - start_time,
            "messages_sent": messages_sent,
            "responses_received": responses_received,
            "message_rate": messages_sent / (time.time() - start_time)
        }

    async def _generate_heavy_workload(self, agent: TenantAgent, duration: float, intensity: str) -> Dict[str, Any]:
        """Generate heavy computational workload."""
        start_time = time.time()
        messages_sent = 0
        responses_received = 0
        
        # Adjust message rate based on intensity
        message_delay = {
            "low": 0.5,      # 2 msg/sec
            "normal": 0.1,   # 10 msg/sec
            "high": 0.05,    # 20 msg/sec
            "extreme": 0.01  # 100 msg/sec
        }.get(intensity, 0.1)
        
        end_time = start_time + duration
        
        while time.time() < end_time:
            try:
                # Send heavy computation request
                message = {
                    "type": "heavy_computation",
                    "content": f"Heavy workload message {messages_sent + 1}",
                    "message_id": f"{agent.tenant_id}-heavy-{messages_sent}",
                    "computation_type": "matrix_multiply",
                    "size": 1000,  # Large computation
                    "timestamp": time.time()
                }
                
                await agent.connection.send(json.dumps(message))
                messages_sent += 1
                
                # Try to receive response
                try:
                    response = await asyncio.wait_for(agent.connection.recv(), timeout=2.0)
                    responses_received += 1
                except asyncio.TimeoutError:
                    pass
                
                await asyncio.sleep(message_delay)
                
            except Exception as e:
                logger.error(f"Error in heavy workload for {agent.tenant_id}: {e}")
                break
        
        return {
            "workload_type": "heavy",
            "intensity": intensity,
            "duration": time.time() - start_time,
            "messages_sent": messages_sent,
            "responses_received": responses_received,
            "message_rate": messages_sent / (time.time() - start_time)
        }

    async def _generate_noisy_workload(self, agent: TenantAgent, duration: float, intensity: str) -> Dict[str, Any]:
        """Generate noisy neighbor workload (resource intensive)."""
        start_time = time.time()
        messages_sent = 0
        
        # Create resource-intensive pattern
        message_burst_size = {
            "low": 5,
            "normal": 20,
            "high": 50,
            "extreme": 100
        }.get(intensity, 20)
        
        end_time = start_time + duration
        
        while time.time() < end_time:
            try:
                # Send burst of messages
                for i in range(message_burst_size):
                    message = {
                        "type": "resource_intensive",
                        "content": f"Noisy workload burst {messages_sent + 1} - {'x' * 10000}",  # Large payload
                        "message_id": f"{agent.tenant_id}-noisy-{messages_sent}",
                        "memory_allocation": "large",
                        "cpu_intensive": True,
                        "timestamp": time.time()
                    }
                    
                    await agent.connection.send(json.dumps(message))
                    messages_sent += 1
                
                # Brief pause between bursts
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in noisy workload for {agent.tenant_id}: {e}")
                break
        
        return {
            "workload_type": "noisy",
            "intensity": intensity,
            "duration": time.time() - start_time,
            "messages_sent": messages_sent,
            "message_rate": messages_sent / (time.time() - start_time),
            "burst_size": message_burst_size
        }

    async def _generate_mixed_workload(self, agent: TenantAgent, duration: float) -> Dict[str, Any]:
        """Generate mixed workload pattern."""
        # Alternate between normal and heavy workloads
        phase_duration = duration / 4
        results = []
        
        # Normal phase
        result = await self._generate_normal_workload(agent, phase_duration)
        results.append(result)
        
        # Heavy phase
        result = await self._generate_heavy_workload(agent, phase_duration, "normal")
        results.append(result)
        
        # Normal phase
        result = await self._generate_normal_workload(agent, phase_duration)
        results.append(result)
        
        # Noisy phase
        result = await self._generate_noisy_workload(agent, phase_duration, "normal")
        results.append(result)
        
        total_messages = sum(r["messages_sent"] for r in results)
        total_responses = sum(r.get("responses_received", 0) for r in results)
        
        return {
            "workload_type": "mixed",
            "duration": duration,
            "phases": results,
            "total_messages_sent": total_messages,
            "total_responses_received": total_responses,
            "average_message_rate": total_messages / duration
        }