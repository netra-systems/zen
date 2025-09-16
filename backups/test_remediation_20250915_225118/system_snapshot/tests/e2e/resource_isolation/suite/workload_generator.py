"""
from shared.isolated_environment import get_env
Workload Generator for Resource Isolation Testing

Generates various workload patterns for testing tenant isolation.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict

import websockets

from tests.e2e.resource_isolation.test_infrastructure import TenantAgent

logger = logging.getLogger(__name__)

class WorkloadGenerator:
    """Generate various workload patterns for tenant agents."""
    
    async def generate_workload(self, agent: TenantAgent, workload_type: str, 
                              duration: float, intensity: str = "normal") -> Dict[str, Any]:
        """Generate workload for a tenant agent."""
        # Check if we're in offline mode
        import os
        offline_mode = get_env().get("CPU_ISOLATION_OFFLINE_MODE", "false").lower() == "true"
        
        if offline_mode:
            return await self._generate_offline_workload(agent, workload_type, duration, intensity)
        
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

    async def _generate_offline_workload(self, agent: TenantAgent, workload_type: str, 
                                       duration: float, intensity: str = "normal") -> Dict[str, Any]:
        """Generate CPU workload without WebSocket connections for offline testing."""
        import threading
        import math
        
        logger.info(f"Generating offline {workload_type} workload for {agent.tenant_id} (duration: {duration}s, intensity: {intensity})")
        
        # Configure CPU workload based on type and intensity
        workload_config = self._get_offline_workload_config(workload_type, intensity)
        
        start_time = time.time()
        operations_performed = 0
        
        # Create CPU-intensive work in separate thread to simulate agent processing
        def cpu_intensive_work():
            nonlocal operations_performed
            end_time = start_time + duration
            
            while time.time() < end_time:
                # Perform CPU-intensive operations based on configuration
                for _ in range(workload_config["operations_per_cycle"]):
                    # Simulate different types of CPU work
                    if workload_type == "heavy" or workload_type == "noisy":
                        # Heavy mathematical operations
                        result = sum(math.sqrt(i) for i in range(workload_config["compute_size"]))
                        operations_performed += workload_config["compute_size"]
                    else:
                        # Normal workload - lighter operations
                        result = sum(i * 2 for i in range(workload_config["compute_size"]))
                        operations_performed += workload_config["compute_size"]
                
                # Control CPU usage intensity
                time.sleep(workload_config["sleep_between_cycles"])
        
        # Run workload in thread to avoid blocking the event loop
        workload_thread = threading.Thread(target=cpu_intensive_work, daemon=True)
        workload_thread.start()
        
        # Monitor workload progress with timeout
        timeout_time = start_time + duration + 5  # 5 second grace period
        while workload_thread.is_alive() and time.time() < timeout_time:
            await asyncio.sleep(0.5)  # Less frequent checks to reduce CPU overhead
            
        # If thread is still running after timeout, continue anyway
        if workload_thread.is_alive():
            logger.warning(f"Workload thread for {agent.tenant_id} still running after timeout, continuing with test")
        
        actual_duration = time.time() - start_time
        
        return {
            "workload_type": f"{workload_type}_offline",
            "intensity": intensity,
            "duration": actual_duration,
            "operations_performed": operations_performed,
            "operations_per_second": operations_performed / actual_duration if actual_duration > 0 else 0,
            "mode": "offline_cpu_simulation",
            "tenant_id": agent.tenant_id
        }
    
    def _get_offline_workload_config(self, workload_type: str, intensity: str) -> Dict[str, Any]:
        """Get configuration for offline workload generation."""
        base_configs = {
            "normal": {
                "operations_per_cycle": 100,
                "compute_size": 1000,
                "sleep_between_cycles": 0.01
            },
            "heavy": {
                "operations_per_cycle": 1000,
                "compute_size": 5000,
                "sleep_between_cycles": 0.001
            },
            "noisy": {
                "operations_per_cycle": 2000,
                "compute_size": 10000,
                "sleep_between_cycles": 0.0001
            },
            "mixed": {
                "operations_per_cycle": 500,
                "compute_size": 2500,
                "sleep_between_cycles": 0.005
            }
        }
        
        # Intensity multipliers
        intensity_multipliers = {
            "low": 0.5,
            "normal": 1.0,
            "high": 2.0,
            "extreme": 4.0
        }
        
        config = base_configs.get(workload_type, base_configs["normal"]).copy()
        multiplier = intensity_multipliers.get(intensity, 1.0)
        
        # Apply intensity scaling
        config["operations_per_cycle"] = int(config["operations_per_cycle"] * multiplier)
        config["compute_size"] = int(config["compute_size"] * multiplier)
        config["sleep_between_cycles"] = max(0.0001, config["sleep_between_cycles"] / multiplier)
        
        return config

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
