#!/usr/bin/env python3
"""
Comprehensive test for agent failover and recovery:
1. Agent health monitoring and detection
2. Automatic failover to backup agents
3. State persistence and recovery
4. Task redistribution during failures
5. Circuit breaker activation
6. Graceful degradation strategies
7. Recovery time objectives (RTO)
8. Data consistency after recovery

This test validates the complete agent failover and recovery system.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import asyncio
import json
import time
import random
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import aiohttp
import websockets
import pytest
from datetime import datetime, timedelta
import uuid

# Add project root to path
import sys
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configuration
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/websocket"
AGENT_MANAGER_URL = "http://localhost:8002"
SUPERVISOR_URL = "http://localhost:8003"

# Test configuration
NUM_AGENTS = 5
NUM_TASKS = 20
FAILURE_SCENARIOS = [
    "agent_crash",
    "network_partition",
    "resource_exhaustion",
    "deadlock",
    "timeout"
]

# Recovery targets
RTO_TARGETS = {
    "detection_time": 5,      # 5 seconds to detect failure
    "failover_time": 10,      # 10 seconds to complete failover
    "recovery_time": 30,      # 30 seconds to full recovery
    "data_sync_time": 15      # 15 seconds to sync state
}


class AgentInstance:
    """Represents an agent instance for testing."""
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.status = "healthy"
        self.tasks: List[str] = []
        self.state: Dict[str, Any] = {}
        self.websocket = None
        self.last_heartbeat = time.time()
        self.failure_count = 0
        self.circuit_breaker_open = False
        

class AgentFailoverTester:
    """Test agent failover and recovery mechanisms."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.agents: Dict[str, AgentInstance] = {}
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.admin_token: Optional[str] = None
        self.failure_events: List[Dict[str, Any]] = []
        self.recovery_metrics: Dict[str, float] = {}
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        # Close all agent WebSockets
        for agent in self.agents.values():
            if agent.websocket:
                try:
                    await agent.websocket.close()
                except:
                    pass
                    
        if self.session:
            await self.session.close()
            
    async def setup_agents(self) -> bool:
        """Setup test agents."""
        print(f"\n[SETUP] Creating {NUM_AGENTS} test agents...")
        
        agent_types = ["supervisor", "worker", "analyzer", "validator", "coordinator"]
        
        for i in range(NUM_AGENTS):
            agent_id = f"agent_{uuid.uuid4().hex[:8]}"
            agent_type = agent_types[i % len(agent_types)]
            agent = AgentInstance(agent_id, agent_type)
            
            try:
                # Register agent
                agent_data = {
                    "agent_id": agent_id,
                    "agent_type": agent_type,
                    "capabilities": ["process", "analyze", "validate"],
                    "max_tasks": 10,
                    "priority": i + 1
                }
                
                async with self.session.post(
                    f"{AGENT_MANAGER_URL}/agents/register",
                    json=agent_data
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        agent.state = data.get("initial_state", {})
                        self.agents[agent_id] = agent
                        print(f"[OK] Registered {agent_type} agent: {agent_id}")
                    else:
                        print(f"[ERROR] Failed to register agent: {response.status}")
                        
                # Connect WebSocket for agent
                agent.websocket = await websockets.connect(
                    f"{WS_URL}/agent/{agent_id}"
                )
                
                # Start heartbeat
                asyncio.create_task(self._agent_heartbeat(agent))
                
            except Exception as e:
                print(f"[ERROR] Agent setup failed: {e}")
                
        return len(self.agents) == NUM_AGENTS
        
    async def _agent_heartbeat(self, agent: AgentInstance):
        """Send periodic heartbeats for agent."""
        while agent.status == "healthy":
            try:
                if agent.websocket and not agent.websocket.closed:
                    await agent.websocket.send(json.dumps({
                        "type": "heartbeat",
                        "agent_id": agent.agent_id,
                        "timestamp": time.time(),
                        "status": agent.status,
                        "task_count": len(agent.tasks)
                    }))
                    agent.last_heartbeat = time.time()
                    
                await asyncio.sleep(2)  # Heartbeat every 2 seconds
                
            except Exception:
                break
                
    async def create_tasks(self) -> bool:
        """Create tasks for agents to process."""
        print(f"\n[TASKS] Creating {NUM_TASKS} test tasks...")
        
        for i in range(NUM_TASKS):
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            task = {
                "task_id": task_id,
                "type": random.choice(["analyze", "process", "validate", "transform"]),
                "priority": random.randint(1, 10),
                "data": {
                    "input": f"test_data_{i}",
                    "complexity": random.choice(["low", "medium", "high"]),
                    "timeout": random.randint(10, 60)
                },
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending"
            }
            
            try:
                # Submit task
                async with self.session.post(
                    f"{SUPERVISOR_URL}/tasks/submit",
                    json=task
                ) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        task["assigned_agent"] = data.get("assigned_agent")
                        self.tasks[task_id] = task
                        
                        # Update agent's task list
                        if task["assigned_agent"] in self.agents:
                            self.agents[task["assigned_agent"]].tasks.append(task_id)
                            
                        print(f"[OK] Created task {task_id} -> {task['assigned_agent']}")
                        
            except Exception as e:
                print(f"[ERROR] Task creation failed: {e}")
                
        return len(self.tasks) == NUM_TASKS
        
    async def simulate_agent_failure(self, agent_id: str, failure_type: str) -> bool:
        """Simulate an agent failure."""
        print(f"\n[FAILURE] Simulating {failure_type} for {agent_id}...")
        
        if agent_id not in self.agents:
            return False
            
        agent = self.agents[agent_id]
        failure_start = time.time()
        
        try:
            if failure_type == "agent_crash":
                # Simulate sudden crash
                agent.status = "crashed"
                if agent.websocket:
                    await agent.websocket.close()
                    agent.websocket = None
                print(f"[OK] Agent {agent_id} crashed")
                
            elif failure_type == "network_partition":
                # Simulate network issue
                agent.status = "unreachable"
                # Don't close WebSocket but stop heartbeats
                print(f"[OK] Agent {agent_id} network partitioned")
                
            elif failure_type == "resource_exhaustion":
                # Simulate resource exhaustion
                agent.status = "overloaded"
                await self._send_agent_status(agent_id, {
                    "status": "overloaded",
                    "cpu_usage": 95,
                    "memory_usage": 98,
                    "error": "Resource exhaustion"
                })
                print(f"[OK] Agent {agent_id} resource exhausted")
                
            elif failure_type == "deadlock":
                # Simulate deadlock
                agent.status = "deadlocked"
                agent.last_heartbeat = 0  # Stop heartbeat updates
                print(f"[OK] Agent {agent_id} deadlocked")
                
            elif failure_type == "timeout":
                # Simulate processing timeout
                agent.status = "timeout"
                for task_id in agent.tasks[:]:
                    self.tasks[task_id]["status"] = "timeout"
                print(f"[OK] Agent {agent_id} timed out")
                
            # Record failure event
            self.failure_events.append({
                "agent_id": agent_id,
                "failure_type": failure_type,
                "timestamp": failure_start,
                "tasks_affected": len(agent.tasks)
            })
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failure simulation failed: {e}")
            return False
            
    async def _send_agent_status(self, agent_id: str, status: Dict[str, Any]):
        """Send agent status update."""
        try:
            async with self.session.post(
                f"{AGENT_MANAGER_URL}/agents/{agent_id}/status",
                json=status
            ) as response:
                return response.status == 200
        except:
            return False
            
    async def test_failure_detection(self) -> Tuple[bool, float]:
        """Test failure detection mechanisms."""
        print("\n[DETECTION] Testing failure detection...")
        
        # Pick a healthy agent to fail
        healthy_agents = [a for a in self.agents.values() if a.status == "healthy"]
        if not healthy_agents:
            return False, 0
            
        target_agent = random.choice(healthy_agents)
        detection_start = time.time()
        
        # Simulate failure
        await self.simulate_agent_failure(target_agent.agent_id, "agent_crash")
        
        # Wait for detection
        detected = False
        while time.time() - detection_start < RTO_TARGETS["detection_time"]:
            try:
                async with self.session.get(
                    f"{AGENT_MANAGER_URL}/agents/{target_agent.agent_id}/health"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") in ["failed", "unhealthy", "crashed"]:
                            detected = True
                            break
                            
            except:
                pass
                
            await asyncio.sleep(0.5)
            
        detection_time = time.time() - detection_start
        
        if detected:
            print(f"[OK] Failure detected in {detection_time:.2f}s")
        else:
            print(f"[ERROR] Failure not detected within {RTO_TARGETS['detection_time']}s")
            
        return detected, detection_time
        
    async def test_automatic_failover(self) -> Tuple[bool, float]:
        """Test automatic failover to backup agents."""
        print("\n[FAILOVER] Testing automatic failover...")
        
        failover_start = time.time()
        
        # Get failed agents
        failed_agents = [a for a in self.agents.values() if a.status != "healthy"]
        if not failed_agents:
            # Create a failure if none exist
            healthy = [a for a in self.agents.values() if a.status == "healthy"]
            if healthy:
                await self.simulate_agent_failure(healthy[0].agent_id, "agent_crash")
                failed_agents = [healthy[0]]
                
        if not failed_agents:
            return False, 0
            
        failed_agent = failed_agents[0]
        affected_tasks = failed_agent.tasks.copy()
        
        # Wait for task redistribution
        redistributed = 0
        while time.time() - failover_start < RTO_TARGETS["failover_time"]:
            for task_id in affected_tasks:
                try:
                    async with self.session.get(
                        f"{SUPERVISOR_URL}/tasks/{task_id}/status"
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            new_agent = data.get("assigned_agent")
                            
                            if new_agent and new_agent != failed_agent.agent_id:
                                if self.agents.get(new_agent, {}).get("status") == "healthy":
                                    redistributed += 1
                                    self.tasks[task_id]["assigned_agent"] = new_agent
                                    
                except:
                    pass
                    
            if redistributed >= len(affected_tasks) * 0.8:  # 80% redistribution success
                break
                
            await asyncio.sleep(1)
            
        failover_time = time.time() - failover_start
        success = redistributed >= len(affected_tasks) * 0.8
        
        print(f"[{'OK' if success else 'ERROR'}] Redistributed {redistributed}/{len(affected_tasks)} tasks in {failover_time:.2f}s")
        
        return success, failover_time
        
    async def test_state_recovery(self) -> Tuple[bool, float]:
        """Test state persistence and recovery."""
        print("\n[STATE] Testing state recovery...")
        
        recovery_start = time.time()
        
        # Pick an agent to recover
        failed_agents = [a for a in self.agents.values() if a.status != "healthy"]
        if not failed_agents:
            return False, 0
            
        recovering_agent = failed_agents[0]
        original_state = recovering_agent.state.copy()
        
        # Attempt recovery
        try:
            # Restart agent
            recovery_data = {
                "agent_id": recovering_agent.agent_id,
                "action": "restart",
                "restore_state": True
            }
            
            async with self.session.post(
                f"{AGENT_MANAGER_URL}/agents/recover",
                json=recovery_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    recovered_state = data.get("state", {})
                    
                    # Reconnect WebSocket
                    recovering_agent.websocket = await websockets.connect(
                        f"{WS_URL}/agent/{recovering_agent.agent_id}"
                    )
                    
                    # Verify state consistency
                    state_consistent = True
                    for key, value in original_state.items():
                        if recovered_state.get(key) != value:
                            state_consistent = False
                            print(f"[WARN] State mismatch for key {key}")
                            
                    if state_consistent:
                        recovering_agent.status = "healthy"
                        recovering_agent.state = recovered_state
                        asyncio.create_task(self._agent_heartbeat(recovering_agent))
                        
                    recovery_time = time.time() - recovery_start
                    print(f"[OK] Agent recovered in {recovery_time:.2f}s")
                    
                    return state_consistent, recovery_time
                    
        except Exception as e:
            print(f"[ERROR] State recovery failed: {e}")
            
        return False, time.time() - recovery_start
        
    async def test_circuit_breaker(self) -> bool:
        """Test circuit breaker activation."""
        print("\n[CIRCUIT] Testing circuit breaker...")
        
        # Pick an agent to test circuit breaker
        test_agent = list(self.agents.values())[0]
        
        # Simulate multiple failures
        for i in range(5):
            test_agent.failure_count += 1
            
            try:
                async with self.session.post(
                    f"{AGENT_MANAGER_URL}/agents/{test_agent.agent_id}/failure",
                    json={"failure_count": test_agent.failure_count}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("circuit_breaker_open"):
                            test_agent.circuit_breaker_open = True
                            print(f"[OK] Circuit breaker opened after {i+1} failures")
                            
                            # Verify no new tasks assigned
                            test_task = {
                                "type": "test",
                                "require_agent": test_agent.agent_id
                            }
                            
                            async with self.session.post(
                                f"{SUPERVISOR_URL}/tasks/submit",
                                json=test_task
                            ) as task_response:
                                if task_response.status == 503:
                                    print("[OK] Circuit breaker preventing new tasks")
                                    return True
                                    
            except Exception as e:
                print(f"[ERROR] Circuit breaker test failed: {e}")
                
        return test_agent.circuit_breaker_open
        
    async def test_graceful_degradation(self) -> bool:
        """Test graceful degradation strategies."""
        print("\n[DEGRADATION] Testing graceful degradation...")
        
        # Simulate progressive failures
        healthy_count = len([a for a in self.agents.values() if a.status == "healthy"])
        
        degradation_levels = []
        
        while healthy_count > 1:
            # Fail one more agent
            healthy = [a for a in self.agents.values() if a.status == "healthy"]
            if healthy:
                await self.simulate_agent_failure(
                    healthy[0].agent_id,
                    random.choice(FAILURE_SCENARIOS)
                )
                healthy_count -= 1
                
            # Check system response
            try:
                async with self.session.get(
                    f"{SUPERVISOR_URL}/system/status"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        degradation_level = data.get("degradation_level", "normal")
                        degradation_levels.append(degradation_level)
                        
                        print(f"[INFO] System degradation level: {degradation_level} ({healthy_count} agents healthy)")
                        
                        # Verify appropriate degradation
                        if healthy_count <= 2 and degradation_level not in ["degraded", "critical"]:
                            print("[WARN] System not detecting degradation properly")
                            
            except:
                pass
                
        # Verify progressive degradation
        expected_progression = ["normal", "degraded", "critical"]
        progression_correct = any(
            level in degradation_levels for level in ["degraded", "critical"]
        )
        
        return progression_correct
        
    async def test_data_consistency(self) -> bool:
        """Test data consistency after recovery."""
        print("\n[CONSISTENCY] Testing data consistency...")
        
        # Check task consistency
        inconsistencies = []
        
        for task_id, task in self.tasks.items():
            try:
                # Get task status from supervisor
                async with self.session.get(
                    f"{SUPERVISOR_URL}/tasks/{task_id}/status"
                ) as response:
                    if response.status == 200:
                        supervisor_data = await response.json()
                        
                        # Check consistency
                        if task["assigned_agent"] != supervisor_data.get("assigned_agent"):
                            if task["status"] not in ["failed", "timeout"]:
                                inconsistencies.append(f"Task {task_id} agent mismatch")
                                
                        if task["status"] != supervisor_data.get("status"):
                            # Status changes are expected during recovery
                            if supervisor_data.get("status") not in ["reassigned", "recovered"]:
                                inconsistencies.append(f"Task {task_id} status mismatch")
                                
            except:
                pass
                
        if inconsistencies:
            print(f"[WARN] Found {len(inconsistencies)} inconsistencies:")
            for issue in inconsistencies[:5]:  # Show first 5
                print(f"  - {issue}")
        else:
            print("[OK] Data consistency maintained")
            
        return len(inconsistencies) == 0
        
    async def test_recovery_metrics(self) -> bool:
        """Verify recovery time objectives."""
        print("\n[METRICS] Verifying recovery metrics...")
        
        metrics_met = True
        
        for metric, target in RTO_TARGETS.items():
            actual = self.recovery_metrics.get(metric, float('inf'))
            
            if actual <= target:
                print(f"[OK] {metric}: {actual:.2f}s <= {target}s target")
            else:
                print(f"[FAIL] {metric}: {actual:.2f}s > {target}s target")
                metrics_met = False
                
        return metrics_met
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all agent failover and recovery tests."""
        results = {}
        
        # Setup
        results["agent_setup"] = await self.setup_agents()
        results["task_creation"] = await self.create_tasks()
        
        # Test failure scenarios
        detection_passed, detection_time = await self.test_failure_detection()
        results["failure_detection"] = detection_passed
        self.recovery_metrics["detection_time"] = detection_time
        
        failover_passed, failover_time = await self.test_automatic_failover()
        results["automatic_failover"] = failover_passed
        self.recovery_metrics["failover_time"] = failover_time
        
        recovery_passed, recovery_time = await self.test_state_recovery()
        results["state_recovery"] = recovery_passed
        self.recovery_metrics["recovery_time"] = recovery_time
        
        # Test recovery mechanisms
        results["circuit_breaker"] = await self.test_circuit_breaker()
        results["graceful_degradation"] = await self.test_graceful_degradation()
        results["data_consistency"] = await self.test_data_consistency()
        results["recovery_metrics"] = await self.test_recovery_metrics()
        
        return results


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l4
async def test_agent_failover_recovery():
    """Test complete agent failover and recovery system."""
    async with AgentFailoverTester() as tester:
        results = await tester.run_all_tests()
        
        # Print comprehensive report
        print("\n" + "="*80)
        print("AGENT FAILOVER & RECOVERY TEST REPORT")
        print("="*80)
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print(f"Agents Tested: {len(tester.agents)}")
        print(f"Tasks Created: {len(tester.tasks)}")
        print("="*80)
        
        # Test results
        print("\nTEST RESULTS:")
        print("-"*40)
        for test_name, passed in results.items():
            if isinstance(passed, bool):
                status = "✓ PASS" if passed else "✗ FAIL"
                print(f"  {test_name:30} : {status}")
                
        # Agent status
        print("\nAGENT STATUS:")
        print("-"*40)
        status_counts = {}
        for agent in tester.agents.values():
            status_counts[agent.status] = status_counts.get(agent.status, 0) + 1
            
        for status, count in status_counts.items():
            print(f"  {status:15} : {count} agents")
            
        # Failure events
        if tester.failure_events:
            print("\nFAILURE EVENTS:")
            print("-"*40)
            for event in tester.failure_events:
                print(f"  {event['agent_id']}: {event['failure_type']} ({event['tasks_affected']} tasks)")
                
        # Recovery metrics
        print("\nRECOVERY METRICS:")
        print("-"*40)
        for metric, value in tester.recovery_metrics.items():
            target = RTO_TARGETS.get(metric, "N/A")
            status = "✓" if value <= target else "✗"
            print(f"  {metric:20} : {value:.2f}s (Target: {target}s) {status}")
            
        print("="*80)
        
        # Calculate overall result
        total_tests = sum(1 for v in results.values() if isinstance(v, bool))
        passed_tests = sum(1 for v in results.values() if v is True)
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        # Critical checks
        critical_tests = ["failure_detection", "automatic_failover", "data_consistency"]
        critical_passed = all(results.get(test, False) for test in critical_tests)
        
        if critical_passed:
            print("\n[SUCCESS] Agent failover and recovery system operational!")
        else:
            print("\n[CRITICAL] Core failover mechanisms not functioning properly!")
            
        assert critical_passed, f"Critical failover tests failed: {results}"


async def main():
    """Run the test standalone."""
    print("="*80)
    print("AGENT FAILOVER & RECOVERY TEST")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*80)
    
    async with AgentFailoverTester() as tester:
        results = await tester.run_all_tests()
        
        # Return exit code based on critical tests
        critical_tests = ["failure_detection", "automatic_failover", "data_consistency"]
        if all(results.get(test, False) for test in critical_tests):
            return 0
        else:
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)