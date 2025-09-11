from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""Demonstration Script for Optimized State Persistence

This script demonstrates the performance benefits of the optimized state persistence system.
It shows the difference between standard and optimized persistence under various scenarios.
"""

import asyncio
import time
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.agent_state import StatePersistenceRequest, CheckpointType
from netra_backend.app.services.state_persistence import state_persistence_service
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession


class PersistenceDemo:
    """Demonstration of optimized vs standard persistence performance."""
    
    def __init__(self):
        self.mock_db_session = AsyncMock(spec=AsyncSession)
        
    async def simulate_standard_persistence(self, requests):
        """Simulate standard persistence behavior."""
        start_time = time.time()
        saved_count = 0
        
        for request in requests:
            # Standard persistence always saves (simulate by counting)
            saved_count += 1
            await asyncio.sleep(0.001)  # Simulate DB write latency
            
        duration = time.time() - start_time
        return saved_count, duration
    
    async def simulate_optimized_persistence(self, requests):
        """Simulate optimized persistence behavior with actual service."""
        # Enable optimized persistence for demo
        optimized_service = state_persistence_service
        optimized_service._optimization_enabled = True
        
        # Mock the internal save method to avoid actual DB operations
        original_save = optimized_service._execute_state_save_transaction
        
        async def mock_save(request, session):
            await asyncio.sleep(0.001)  # Simulate DB write latency
            return f"snapshot_{request.run_id}"
        
        optimized_service._execute_state_save_transaction = mock_save
        
        start_time = time.time()
        saved_count = 0
        skipped_count = 0
        
        try:
            for request in requests:
                success, snapshot_id = await optimized_service.save_agent_state(
                    request, self.mock_db_session
                )
                if snapshot_id == "skipped_no_changes":
                    skipped_count += 1
                else:
                    saved_count += 1
                    
        finally:
            # Restore original service method
            optimized_service._execute_state_save_transaction = original_save
            
        duration = time.time() - start_time
        return saved_count, skipped_count, duration
    
    def generate_test_requests(self, scenario="mixed"):
        """Generate test persistence requests for different scenarios."""
        requests = []
        
        if scenario == "identical":
            # Multiple identical states - should be skipped after first
            base_state = {"agent_type": "supervisor", "status": "active", "data": {"count": 1}}
            for i in range(10):
                requests.append(StatePersistenceRequest(
                    run_id=f"identical_run",
                    thread_id="thread_1",
                    user_id="user_1", 
                    state_data=base_state.copy(),
                    checkpoint_type=CheckpointType.AUTO,
                    is_recovery_point=False
                ))
                
        elif scenario == "changing":
            # States that change meaningfully - should all be saved
            for i in range(10):
                state_data = {
                    "agent_type": "supervisor", 
                    "status": "active", 
                    "data": {"count": i, "iteration": i}
                }
                requests.append(StatePersistenceRequest(
                    run_id=f"changing_run",
                    thread_id="thread_1",
                    user_id="user_1",
                    state_data=state_data,
                    checkpoint_type=CheckpointType.AUTO,
                    is_recovery_point=False
                ))
                
        elif scenario == "trivial":
            # States with only trivial changes - should be skipped
            for i in range(10):
                state_data = {
                    "agent_type": "supervisor",
                    "status": "active", 
                    "data": {"count": 1},
                    "timestamp": f"2023-01-01T{i:02d}:00:00Z"  # Only timestamp changes
                }
                requests.append(StatePersistenceRequest(
                    run_id=f"trivial_run",
                    thread_id="thread_1",
                    user_id="user_1",
                    state_data=state_data,
                    checkpoint_type=CheckpointType.AUTO,
                    is_recovery_point=False
                ))
                
        elif scenario == "mixed":
            # Mixed scenario - some identical, some changing
            base_state = {"agent_type": "supervisor", "status": "active"}
            for i in range(20):
                if i % 3 == 0:
                    # Meaningful change every 3rd request
                    state_data = base_state.copy()
                    state_data["data"] = {"count": i // 3}
                else:
                    # Identical or trivial changes
                    state_data = base_state.copy()
                    state_data["data"] = {"count": 0}
                    state_data["timestamp"] = f"2023-01-01T{i:02d}:00:00Z"
                    
                requests.append(StatePersistenceRequest(
                    run_id=f"mixed_run",
                    thread_id="thread_1", 
                    user_id="user_1",
                    state_data=state_data,
                    checkpoint_type=CheckpointType.AUTO,
                    is_recovery_point=False
                ))
                
        return requests
    
    async def run_demo(self):
        """Run the persistence performance demonstration."""
        print("Optimized State Persistence Demonstration")
        print("=" * 60)
        print()
        
        scenarios = ["identical", "changing", "trivial", "mixed"]
        
        for scenario in scenarios:
            print(f"Scenario: {scenario.upper()}")
            print("-" * 40)
            
            requests = self.generate_test_requests(scenario)
            print(f"Generated {len(requests)} persistence requests")
            
            # Test standard persistence
            std_saved, std_duration = await self.simulate_standard_persistence(requests)
            
            # Test optimized persistence  
            opt_saved, opt_skipped, opt_duration = await self.simulate_optimized_persistence(requests)
            
            # Calculate improvements
            time_improvement = ((std_duration - opt_duration) / std_duration) * 100
            write_reduction = ((std_saved - opt_saved) / std_saved) * 100
            
            print(f"Results:")
            print(f"  Standard Persistence:")
            print(f"    - Saved: {std_saved} states")
            print(f"    - Duration: {std_duration:.3f}s")
            print(f"  Optimized Persistence:")
            print(f"    - Saved: {opt_saved} states")
            print(f"    - Skipped: {opt_skipped} states")
            print(f"    - Duration: {opt_duration:.3f}s")
            print(f"  Improvements:")
            print(f"    - Time saved: {time_improvement:.1f}%")
            print(f"    - DB writes reduced: {write_reduction:.1f}%")
            print()
    
    async def demonstrate_feature_flags(self):
        """Demonstrate feature flag control."""
        print("Feature Flag Control Demonstration")
        print("=" * 60)
        print()
        
        # Test with feature disabled
        print("Testing with ENABLE_OPTIMIZED_PERSISTENCE=false")
        os.environ["ENABLE_OPTIMIZED_PERSISTENCE"] = "false"
        
        # Create new service instance to pick up environment change
        disabled_service = state_persistence_service.__class__()
        print(f"   Optimized persistence enabled: {disabled_service._optimization_enabled}")
        
        # Test with feature enabled
        print("Testing with ENABLE_OPTIMIZED_PERSISTENCE=true") 
        os.environ["ENABLE_OPTIMIZED_PERSISTENCE"] = "true"
        
        enabled_service = state_persistence_service.__class__()
        print(f"   Optimized persistence enabled: {enabled_service._optimization_enabled}")
        print()
    
    async def demonstrate_monitoring(self):
        """Demonstrate async monitoring capabilities."""
        print("Async Monitoring Demonstration")
        print("=" * 60)
        print()
        
        print("Performance monitor features:")
        print("  - Queue-based metrics collection")
        print("  - Non-blocking persistence operations")
        print("  - Structured logging output") 
        print("  - Graceful degradation on queue full")
        print()
        
        print("Metrics collected:")
        print("  - Persistence duration")
        print("  - Success/failure rates")
        print("  - Fields changed count")
        print("  - Operation types (save/skip)")
        print()


async def main():
    """Main demonstration function."""
    demo = PersistenceDemo()
    
    try:
        await demo.run_demo()
        await demo.demonstrate_feature_flags()
        await demo.demonstrate_monitoring()
        
        print("Demonstration completed successfully!")
        print()
        print("Key Takeaways:")
        print("  1. Smart state diffing reduces unnecessary DB writes")
        print("  2. Selective persistence maintains consistency while improving performance")
        print("  3. Feature flags enable safe rollout and rollback")
        print("  4. Async monitoring removes overhead from critical path")
        print("  5. Connection pool optimization handles high-frequency workloads")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
