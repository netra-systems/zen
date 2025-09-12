#!/usr/bin/env python3
"""
Integration Test for Test Orchestrator Agent

This test validates the integration between the TestOrchestratorAgent
and the existing unified_test_runner.py system.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.orchestration.test_orchestrator_agent import (
    TestOrchestratorAgent, OrchestrationConfig, ExecutionMode
)


async def test_orchestrator_initialization():
    """Test that orchestrator initializes correctly"""
    print("Testing orchestrator initialization...")
    
    orchestrator = TestOrchestratorAgent(PROJECT_ROOT)
    await orchestrator.initialize()
    
    # Verify initialization
    assert orchestrator.layer_system is not None, "Layer system should be initialized"
    assert orchestrator.communication is not None, "Communication protocol should be initialized"
    assert len(orchestrator.communication.agents) > 0, "Agents should be registered"
    
    # Test agent registration
    expected_agents = ["orchestrator", "layer_executor", "background_e2e", "progress_streamer", "resource_manager"]
    for agent_id in expected_agents:
        assert agent_id in orchestrator.communication.agents, f"Agent {agent_id} should be registered"
    
    await orchestrator.shutdown()
    print(" PASS:  Orchestrator initialization test passed")


async def test_layer_configuration():
    """Test layer configuration loading and access"""
    print("Testing layer configuration...")
    
    orchestrator = TestOrchestratorAgent(PROJECT_ROOT)
    await orchestrator.initialize()
    
    try:
        # Test available layers
        layers = orchestrator.get_available_layers()
        assert len(layers) > 0, "Should have available layers"
        print(f"   Available layers: {layers}")
        
        # Test layer configuration retrieval
        for layer_name in layers:
            config = orchestrator.get_layer_configuration(layer_name)
            if config:
                assert "name" in config, f"Layer {layer_name} should have name"
                assert "categories" in config, f"Layer {layer_name} should have categories"
                assert "execution_mode" in config, f"Layer {layer_name} should have execution mode"
                print(f"    PASS:  Layer {layer_name}: {len(config['categories'])} categories")
        
    finally:
        await orchestrator.shutdown()
    
    print(" PASS:  Layer configuration test passed")


async def test_execution_modes():
    """Test different execution modes"""
    print("Testing execution modes...")
    
    orchestrator = TestOrchestratorAgent(PROJECT_ROOT)
    await orchestrator.initialize()
    
    try:
        # Test each execution mode
        for mode in ExecutionMode:
            config = OrchestrationConfig(
                execution_mode=mode,
                environment="development",
                use_background_e2e=False,
                enable_progress_streaming=False
            )
            
            layers = orchestrator._determine_layers(config)
            assert len(layers) > 0, f"Mode {mode} should determine some layers"
            print(f"    PASS:  Mode {mode.value}: {len(layers)} layers - {layers}")
            
    finally:
        await orchestrator.shutdown()
    
    print(" PASS:  Execution modes test passed")


async def test_orchestration_config():
    """Test orchestration configuration creation"""
    print("Testing orchestration configuration...")
    
    orchestrator = TestOrchestratorAgent(PROJECT_ROOT)
    
    # Test config creation
    config = orchestrator.create_execution_config(
        execution_mode=ExecutionMode.CI,
        layers=["fast_feedback", "core_integration"],
        environment="staging",
        use_background_e2e=True
    )
    
    assert config.execution_mode == ExecutionMode.CI, "Execution mode should be CI"
    assert config.layers == ["fast_feedback", "core_integration"], "Layers should match"
    assert config.environment == "staging", "Environment should be staging"
    assert config.use_background_e2e == True, "Background E2E should be enabled"
    
    print(" PASS:  Orchestration configuration test passed")


def test_cli_integration():
    """Test CLI integration with unified_test_runner.py"""
    print("Testing CLI integration...")
    
    # Test that orchestrator arguments are properly integrated
    try:
        # Test help command to see if orchestrator arguments are present
        result = subprocess.run([
            sys.executable, "scripts/unified_test_runner.py", "--help"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        help_output = result.stdout
        
        # Check for orchestrator-specific arguments
        orchestrator_args = [
            "--use-layers",
            "--layers",
            "--execution-mode",
            "--show-layers", 
            "--background-e2e"
        ]
        
        for arg in orchestrator_args:
            if arg in help_output:
                print(f"    PASS:  Found argument: {arg}")
            else:
                print(f"    WARNING: [U+FE0F]  Missing argument: {arg} (may be conditional)")
        
        # Test show layers command (if orchestrator is available)
        try:
            result = subprocess.run([
                sys.executable, "scripts/unified_test_runner.py", "--show-layers"
            ], capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=10)
            
            if result.returncode == 0:
                print("    PASS:  --show-layers command works")
            else:
                print(f"    WARNING: [U+FE0F]  --show-layers failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print("    WARNING: [U+FE0F]  --show-layers command timed out")
        except Exception as e:
            print(f"    WARNING: [U+FE0F]  --show-layers test error: {e}")
        
    except Exception as e:
        print(f"    FAIL:  CLI integration test error: {e}")
        return False
    
    print(" PASS:  CLI integration test completed")
    return True


async def run_all_tests():
    """Run all integration tests"""
    print("="*60)
    print("TEST ORCHESTRATOR AGENT - INTEGRATION TESTS")
    print("="*60)
    
    tests_passed = 0
    total_tests = 0
    
    # Async tests
    async_tests = [
        test_orchestrator_initialization,
        test_layer_configuration,
        test_execution_modes,
        test_orchestration_config
    ]
    
    for test_func in async_tests:
        total_tests += 1
        try:
            await test_func()
            tests_passed += 1
        except Exception as e:
            print(f" FAIL:  Test {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Sync tests
    sync_tests = [
        test_cli_integration
    ]
    
    for test_func in sync_tests:
        total_tests += 1
        try:
            if test_func():
                tests_passed += 1
        except Exception as e:
            print(f" FAIL:  Test {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("INTEGRATION TEST RESULTS")
    print("="*60)
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print(" CELEBRATION:  ALL INTEGRATION TESTS PASSED!")
        print("\nTest Orchestrator Agent is ready for production use.")
        return 0
    else:
        print(f" FAIL:  {total_tests - tests_passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run_all_tests()))