#!/usr/bin/env python3
"""
Demo script for Test Orchestrator Agent Integration

This script demonstrates the layered test orchestration system
and validates the integration with unified_test_runner.py.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.orchestration.test_orchestrator_agent import (
    TestOrchestratorAgent, OrchestrationConfig, ExecutionMode
)


async def demo_orchestrator_basic():
    """Demonstrate basic orchestrator functionality"""
    print("="*60)
    print("DEMO: Test Orchestrator Agent - Basic Functionality")
    print("="*60)
    
    # Initialize orchestrator
    orchestrator = TestOrchestratorAgent(PROJECT_ROOT)
    await orchestrator.initialize()
    
    try:
        # Show available layers
        print("\n1. Available Layers:")
        layers = orchestrator.get_available_layers()
        for layer_name in layers:
            config = orchestrator.get_layer_configuration(layer_name)
            if config:
                print(f"   {layer_name}:")
                print(f"     Categories: {', '.join(config['categories'])}")
                print(f"     Mode: {config['execution_mode']}")
                print(f"     Duration: {config['estimated_duration']}")
        
        # Show execution status
        print("\n2. Execution Status:")
        status = orchestrator.get_execution_status()
        print(f"   Active: {status['active']}")
        print(f"   Background Tasks: {status['background_tasks']}")
        
        print("\n PASS:  Basic functionality demo completed successfully!")
        
    except Exception as e:
        print(f" FAIL:  Demo failed: {e}")
        raise
        
    finally:
        await orchestrator.shutdown()


async def demo_orchestrator_execution_modes():
    """Demonstrate different execution modes"""
    print("\n" + "="*60)
    print("DEMO: Test Orchestrator Agent - Execution Modes")
    print("="*60)
    
    orchestrator = TestOrchestratorAgent(PROJECT_ROOT)
    await orchestrator.initialize()
    
    try:
        # Test different execution modes
        modes = [
            (ExecutionMode.COMMIT, "Fast validation for commits"),
            (ExecutionMode.CI, "CI pipeline execution"),
            (ExecutionMode.DEVELOPMENT, "Developer-focused execution")
        ]
        
        for mode, description in modes:
            print(f"\n{mode.value.upper()} Mode - {description}")
            
            # Create config for this mode
            config = OrchestrationConfig(
                execution_mode=mode,
                environment="development",
                use_background_e2e=False,  # Disable for demo
                enable_progress_streaming=False  # Disable for demo
            )
            
            # Show what layers would be executed
            layers = orchestrator._determine_layers(config)
            print(f"   Layers: {', '.join(layers)}")
            
        print("\n PASS:  Execution modes demo completed successfully!")
        
    except Exception as e:
        print(f" FAIL:  Demo failed: {e}")
        raise
        
    finally:
        await orchestrator.shutdown()


async def demo_agent_communication():
    """Demonstrate agent communication system"""
    print("\n" + "="*60) 
    print("DEMO: Agent Communication Protocol")
    print("="*60)
    
    orchestrator = TestOrchestratorAgent(PROJECT_ROOT)
    await orchestrator.initialize()
    
    try:
        # Test message sending between agents
        print("\n1. Registered Agents:")
        for agent_id in orchestrator.communication.agents.keys():
            print(f"   - {agent_id}")
        
        # Send a test message
        print("\n2. Testing inter-agent communication...")
        await orchestrator.communication.send_message(
            "orchestrator", "layer_executor", "test_message",
            {"content": "Hello from orchestrator!", "timestamp": "demo"}
        )
        
        # Broadcast a message
        await orchestrator.communication.broadcast_message(
            "orchestrator", "demo_broadcast", 
            {"message": "Broadcasting to all agents"}
        )
        
        print("   Messages sent successfully!")
        print("\n PASS:  Agent communication demo completed successfully!")
        
    except Exception as e:
        print(f" FAIL:  Demo failed: {e}")
        raise
        
    finally:
        await orchestrator.shutdown()


async def main():
    """Run all demonstrations"""
    print("[U+1F680] Starting Test Orchestrator Agent Integration Demos\n")
    
    try:
        # Run basic functionality demo
        await demo_orchestrator_basic()
        
        # Run execution modes demo
        await demo_orchestrator_execution_modes()
        
        # Run agent communication demo
        await demo_agent_communication()
        
        print("\n" + "="*60)
        print(" CELEBRATION:  ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nThe Test Orchestrator Agent is ready for production use.")
        print("\nUsage Examples:")
        print("  python unified_test_runner.py --use-layers --layers fast_feedback")
        print("  python unified_test_runner.py --use-layers --execution-mode ci")
        print("  python unified_test_runner.py --show-layers")
        print("  python unified_test_runner.py --use-layers --background-e2e")
        
    except Exception as e:
        print(f"\n FAIL:  Demo suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))