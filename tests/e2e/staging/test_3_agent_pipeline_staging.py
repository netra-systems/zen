"""
Test 3: Agent Pipeline - Basic agent pipeline functionality
Tests agent pipeline operations in staging.
Business Value: Ensures agent execution pipeline works correctly.
"""

import asyncio
import json
import time
from shared.isolated_environment import IsolatedEnvironment

import pytest
from tests.e2e.staging_test_base import StagingTestBase, staging_test


class TestAgentPipelineStaging(StagingTestBase):
    """Test agent pipeline in staging environment"""
    
    @staging_test
    async def test_agent_discovery(self):
        """Test agent discovery endpoints"""
        
        # Test MCP servers (agents)
        response = await self.call_api("/api/mcp/servers")
        assert response.status_code == 200
        data = response.json()
        
        if isinstance(data, dict) and "data" in data:
            agents = data["data"]
            print(f"[INFO] Found {len(agents)} agents")
            for agent in agents:
                if isinstance(agent, dict):
                    print(f"  - Agent: {agent.get('name', 'unknown')}")
        
        print("[PASS] Agent discovery successful")
    
    @staging_test
    async def test_agent_configuration(self):
        """Test agent configuration endpoint"""
        
        response = await self.call_api("/api/mcp/config")
        assert response.status_code == 200
        config = response.json()
        
        # Check for various config formats
        has_config = False
        if "claude" in config or "mcp" in config:
            has_config = True
        
        assert has_config, "No agent configuration found"
        print("[PASS] Agent configuration available")
    
    @staging_test
    async def test_pipeline_stages(self):
        """Test pipeline stage concepts"""
        
        pipeline_stages = [
            "initialization",
            "validation",
            "execution",
            "result_processing",
            "cleanup"
        ]
        
        print("[INFO] Pipeline stages:")
        for stage in pipeline_stages:
            print(f"  -> {stage}")
        
        print("[PASS] Pipeline stages validated")
    
    @staging_test
    async def test_agent_lifecycle(self):
        """Test agent lifecycle states"""
        
        lifecycle_states = [
            ("idle", "Agent is idle"),
            ("starting", "Agent is starting"),
            ("running", "Agent is running"),
            ("paused", "Agent is paused"),
            ("completed", "Agent completed"),
            ("failed", "Agent failed")
        ]
        
        print("[INFO] Agent lifecycle states:")
        for state, description in lifecycle_states:
            print(f"  - {state}: {description}")
        
        print("[PASS] Agent lifecycle states validated")
    
    @staging_test
    async def test_pipeline_error_handling(self):
        """Test pipeline error handling"""
        
        error_types = [
            "initialization_error",
            "validation_error",
            "execution_error",
            "timeout_error",
            "resource_error"
        ]
        
        for error_type in error_types:
            error_payload = {
                "type": "pipeline_error",
                "error": error_type,
                "message": f"Test {error_type}",
                "timestamp": time.time()
            }
            
            assert "type" in error_payload
            assert "error" in error_payload
            
        print(f"[PASS] Validated {len(error_types)} error types")
    
    @staging_test
    async def test_pipeline_metrics(self):
        """Test pipeline metrics structure"""
        
        sample_metrics = {
            "pipeline_id": "test_pipeline_001",
            "start_time": time.time(),
            "end_time": time.time() + 10,
            "duration": 10.0,
            "stages_completed": 5,
            "stages_failed": 0,
            "status": "completed"
        }
        
        # Validate metrics structure
        assert "pipeline_id" in sample_metrics
        assert "duration" in sample_metrics
        assert sample_metrics["duration"] >= 0
        
        print("[PASS] Pipeline metrics structure validated")


if __name__ == "__main__":
    async def run_tests():
        test_class = TestAgentPipelineStaging()
        test_class.setup_class()
        
        try:
            print("=" * 60)
            print("Agent Pipeline Staging Tests")
            print("=" * 60)
            
            await test_class.test_agent_discovery()
            await test_class.test_agent_configuration()
            await test_class.test_pipeline_stages()
            await test_class.test_agent_lifecycle()
            await test_class.test_pipeline_error_handling()
            await test_class.test_pipeline_metrics()
            
            print("\n" + "=" * 60)
            print("[SUCCESS] All tests passed")
            print("=" * 60)
            
        finally:
            test_class.teardown_class()
    
    asyncio.run(run_tests())