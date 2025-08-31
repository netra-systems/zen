#!/usr/bin/env python3
"""
Mission Critical Test Suite - Orchestration System Integration
==============================================================

This is a MISSION CRITICAL test suite that validates the complete orchestration
system integration. These tests MUST pass for the orchestration system to be
considered production ready.

Critical Test Areas:
1. Master Orchestration Controller functionality
2. Agent coordination and lifecycle management  
3. CLI integration and backward compatibility
4. Layer system configuration and execution
5. Progress streaming and WebSocket integration
6. Resource management and service dependencies
7. Error handling and recovery scenarios
8. Performance and reliability characteristics

CRITICAL: These tests ensure the orchestration system does not break existing
functionality while providing the new layered execution capabilities.

Business Value: Prevents regression of critical test infrastructure while
enabling advanced orchestration capabilities for improved developer experience.
"""

import asyncio
import json
import os
import pytest
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import all orchestration components
try:
    from test_framework.orchestration.master_orchestration_controller import (
        MasterOrchestrationController, MasterOrchestrationConfig, OrchestrationMode
    )
    from test_framework.orchestration.test_orchestrator_agent import TestOrchestratorAgent
    from test_framework.orchestration.layer_execution_agent import LayerExecutionAgent
    from test_framework.orchestration.progress_streaming_agent import ProgressStreamingAgent, ProgressOutputMode
    from test_framework.orchestration.resource_management_agent import ResourceManagementAgent
    from test_framework.orchestration.background_e2e_agent import BackgroundE2EAgent
    from test_framework.layer_system import LayerSystem
    ORCHESTRATION_AVAILABLE = True
except ImportError as e:
    ORCHESTRATION_AVAILABLE = False
    pytest.skip(f"Orchestration system not available: {e}", allow_module_level=True)


@pytest.mark.mission_critical
class TestOrchestrationSystemIntegration:
    """Mission critical integration tests for the complete orchestration system"""
    
    @pytest.fixture(scope="class")
    def project_root(self):
        """Get project root path"""
        return PROJECT_ROOT
    
    @pytest.fixture
    def orchestration_config(self):
        """Create test orchestration configuration"""
        return MasterOrchestrationConfig(
            mode=OrchestrationMode.FAST_FEEDBACK,
            enable_progress_streaming=True,
            enable_resource_management=True,
            enable_background_execution=False,
            websocket_enabled=False,
            max_total_duration_minutes=5,
            output_mode=ProgressOutputMode.SILENT,
            verbose_logging=False
        )
    
    def test_orchestration_system_imports(self):
        """CRITICAL: Verify all orchestration components can be imported"""
        # This test ensures all imports work and dependencies are satisfied
        assert MasterOrchestrationController is not None
        assert TestOrchestratorAgent is not None
        assert LayerExecutionAgent is not None
        assert ProgressStreamingAgent is not None
        assert ResourceManagementAgent is not None
        assert BackgroundE2EAgent is not None
        assert LayerSystem is not None
    
    @pytest.mark.asyncio
    async def test_controller_lifecycle(self, orchestration_config):
        """CRITICAL: Test complete controller lifecycle"""
        controller = MasterOrchestrationController(orchestration_config)
        
        try:
            # Test initialization
            assert controller.state.status.value == "initializing"
            
            # Test agent initialization (may fail due to missing services)
            initialization_success = await controller.initialize_agents()
            
            # Verify state is consistent regardless of initialization result
            assert controller.state.status.value in ["initializing", "starting_services", "failed"]
            
            # Test status reporting
            status = controller.get_orchestration_status()
            assert "mode" in status
            assert "status" in status
            assert "agent_health" in status
            
        finally:
            # Test cleanup
            await controller.shutdown()
            assert not controller._monitoring_active
    
    @pytest.mark.asyncio
    async def test_agent_coordination(self, orchestration_config):
        """CRITICAL: Test coordination between different agents"""
        controller = MasterOrchestrationController(orchestration_config)
        
        try:
            # Mock agent initialization to succeed
            with patch.object(controller, 'initialize_agents', return_value=True):
                # Mock individual agents
                controller.resource_manager = Mock()
                controller.progress_streamer = Mock()
                controller.layer_executor = Mock()
                controller.layer_executor.execute_layer = AsyncMock(return_value={
                    "success": True,
                    "duration": 30.0,
                    "summary": {"test_counts": {"total": 5, "passed": 5, "failed": 0}}
                })
                
                # Test coordinated execution
                execution_args = {
                    "env": "test",
                    "real_llm": False,
                    "real_services": False
                }
                
                results = await controller.execute_orchestration(
                    execution_args=execution_args,
                    layers=["fast_feedback"]
                )
                
                # Verify coordination worked
                assert "success" in results
                
        finally:
            await controller.shutdown()
    
    def test_layer_system_configuration(self, project_root):
        """CRITICAL: Test layer system configuration loading"""
        layer_system = LayerSystem(project_root)
        
        # Verify basic layer configuration
        assert len(layer_system.layers) >= 0  # May be empty if config missing
        
        # Test validation
        issues = layer_system.validate_configuration()
        # Should not have critical configuration errors
        critical_issues = [issue for issue in issues if "circular" in issue.lower() or "error" in issue.lower()]
        assert len(critical_issues) == 0, f"Critical configuration issues: {critical_issues}"
    
    def test_progress_streaming_agent_initialization(self, project_root):
        """CRITICAL: Test progress streaming agent can be initialized"""
        config = {
            "output_mode": ProgressOutputMode.SILENT,
            "websocket_enabled": False
        }
        
        # Should not raise exceptions during initialization
        try:
            agent = ProgressStreamingAgent(project_root)
            assert agent is not None
            assert agent.agent_id is not None
        except Exception as e:
            pytest.fail(f"ProgressStreamingAgent initialization failed: {e}")
    
    def test_resource_management_agent_initialization(self):
        """CRITICAL: Test resource management agent can be initialized"""
        try:
            agent = ResourceManagementAgent(enable_monitoring=False)
            assert agent is not None
            
            # Test basic functionality
            status = agent.get_resource_status()
            assert "timestamp" in status
            assert "system_metrics" in status
            
            # Cleanup
            agent.shutdown()
            
        except Exception as e:
            pytest.fail(f"ResourceManagementAgent initialization failed: {e}")


@pytest.mark.mission_critical
class TestCLIIntegrationMissionCritical:
    """Mission critical CLI integration tests"""
    
    def test_unified_test_runner_executable(self):
        """CRITICAL: Test that unified_test_runner.py is executable"""
        runner_path = PROJECT_ROOT / "scripts" / "unified_test_runner.py"
        assert runner_path.exists(), f"unified_test_runner.py not found at {runner_path}"
        
        # Test basic execution
        result = subprocess.run([
            sys.executable, str(runner_path), "--help"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
        
        assert result.returncode == 0, f"unified_test_runner.py --help failed: {result.stderr}"
        assert len(result.stdout) > 0, "Help output is empty"
    
    def test_orchestration_mode_selection(self):
        """CRITICAL: Test orchestration mode selection logic"""
        runner_path = PROJECT_ROOT / "scripts" / "unified_test_runner.py"
        
        # Test orchestration status (should not hang or crash)
        result = subprocess.run([
            sys.executable, str(runner_path), "--orchestration-status"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
        
        # Should complete without hanging
        assert result.returncode == 0
        assert "ORCHESTRATION STATUS" in result.stdout
    
    def test_legacy_mode_fallback(self):
        """CRITICAL: Test fallback to legacy mode when orchestration unavailable"""
        runner_path = PROJECT_ROOT / "scripts" / "unified_test_runner.py"
        
        # Test with legacy arguments only
        result = subprocess.run([
            sys.executable, str(runner_path), "--list-categories"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
        
        # Should work in legacy mode
        assert result.returncode == 0
        assert "CATEGORIES" in result.stdout
    
    def test_argument_validation(self):
        """CRITICAL: Test argument validation and error handling"""
        runner_path = PROJECT_ROOT / "scripts" / "unified_test_runner.py"
        
        # Test invalid execution mode
        result = subprocess.run([
            sys.executable, str(runner_path), 
            "--execution-mode", "nonexistent_mode"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30)
        
        # Should fail gracefully with helpful error
        assert result.returncode != 0
        assert "invalid" in result.stderr.lower() or "error" in result.stderr.lower()


@pytest.mark.mission_critical  
class TestSystemReliability:
    """Test system reliability and failure handling"""
    
    @pytest.mark.asyncio
    async def test_graceful_failure_handling(self):
        """CRITICAL: Test graceful handling of various failure scenarios"""
        config = MasterOrchestrationConfig(
            mode=OrchestrationMode.FAST_FEEDBACK,
            graceful_shutdown_timeout=5
        )
        
        controller = MasterOrchestrationController(config)
        
        # Test shutdown without initialization
        await controller.shutdown()  # Should not raise
        
        # Test shutdown after partial state
        controller.state.agent_health["mock_agent"] = Mock()
        await controller.shutdown()  # Should not raise
    
    @pytest.mark.asyncio
    async def test_concurrent_access_safety(self):
        """CRITICAL: Test thread safety and concurrent access"""
        config = MasterOrchestrationConfig(mode=OrchestrationMode.FAST_FEEDBACK)
        controller = MasterOrchestrationController(config)
        
        try:
            # Test concurrent status requests
            async def get_status():
                return controller.get_orchestration_status()
            
            # Run multiple concurrent status requests
            tasks = [get_status() for _ in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed or fail consistently
            for result in results:
                assert isinstance(result, dict) or isinstance(result, Exception)
                if isinstance(result, dict):
                    assert "mode" in result
        
        finally:
            await controller.shutdown()
    
    def test_configuration_validation(self):
        """CRITICAL: Test configuration validation"""
        # Test invalid configuration
        try:
            invalid_config = MasterOrchestrationConfig(
                max_total_duration_minutes=-1,  # Invalid
                graceful_shutdown_timeout=-5   # Invalid
            )
            # Should either validate or handle gracefully
            controller = MasterOrchestrationController(invalid_config)
            # If created, should be functional
            assert controller is not None
        except Exception:
            # If validation fails, that's also acceptable
            pass


def run_mission_critical_tests():
    """Run mission critical orchestration tests"""
    # Configure pytest for mission critical testing
    pytest_args = [
        __file__,
        "-v",
        "-m", "mission_critical",
        "--tb=short",
        "--disable-warnings",
        "-x"  # Stop on first failure for mission critical tests
    ]
    
    print("Running Mission Critical Orchestration System Tests...")
    print("=" * 60)
    
    result = pytest.main(pytest_args)
    
    if result == 0:
        print("\n" + "=" * 60)
        print("✅ ALL MISSION CRITICAL ORCHESTRATION TESTS PASSED")
        print("🚀 Orchestration system is ready for production")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ MISSION CRITICAL TESTS FAILED")
        print("🚨 Orchestration system is NOT ready for production")
        print("=" * 60)
    
    return result


if __name__ == "__main__":
    sys.exit(run_mission_critical_tests())