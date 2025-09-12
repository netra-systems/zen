#!/usr/bin/env python3
"""
Demo script for LayerExecutionAgent

This script demonstrates the LayerExecutionAgent functionality with the existing
test framework, showing how layers are executed, category coordination, and
progress reporting.
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.orchestration.layer_execution_agent import (
    LayerExecutionAgent, LayerExecutionConfig, ExecutionStrategy,
    create_layer_execution_config
)

def print_banner(title: str):
    """Print a banner for demo sections"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_section(title: str):
    """Print a section header"""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")

async def demo_basic_functionality():
    """Demonstrate basic LayerExecutionAgent functionality"""
    print_banner("LayerExecutionAgent Basic Functionality Demo")
    
    # Initialize agent
    print_section("Initializing LayerExecutionAgent")
    agent = LayerExecutionAgent(project_root)
    print(f"Agent ID: {agent.agent_id}")
    print(f"Project Root: {agent.project_root}")
    
    # Show available layers
    print_section("Available Test Layers")
    layers = agent.get_available_layers()
    for i, layer in enumerate(layers, 1):
        categories = agent.get_layer_categories(layer)
        print(f"{i}. {layer}")
        print(f"   Categories: {', '.join(categories)}")
    
    # Show layer validation
    print_section("Layer Configuration Validation")
    for layer in layers[:3]:  # Check first 3 layers
        issues = agent.validate_layer_configuration(layer)
        if issues:
            print(f"Layer '{layer}': {len(issues)} issues found")
            for issue in issues[:2]:  # Show first 2 issues
                print(f"  - {issue}")
        else:
            print(f"Layer '{layer}': [U+2713] Configuration valid")
    
    # Show execution status
    print_section("Current Execution Status")
    status = agent.get_execution_status()
    print(f"Active: {status['active']}")
    print(f"Execution Stats: {status['execution_stats']}")
    
    return agent

async def demo_health_check(agent: LayerExecutionAgent):
    """Demonstrate health check functionality"""
    print_section("Agent Health Check")
    
    health = await agent.health_check()
    print(f"Health Status: {health['status']}")
    
    print("Component Health:")
    for component, status in health['checks'].items():
        status_icon = "[U+2713]" if status else "[U+2717]"
        print(f"  {status_icon} {component}")
    
    if health['issues']:
        print("Issues Found:")
        for issue in health['issues']:
            print(f"  - {issue}")

def demo_execution_configuration():
    """Demonstrate different execution configurations"""
    print_section("Execution Configuration Examples")
    
    # Sequential configuration
    sequential_config = create_layer_execution_config(
        "fast_feedback",
        execution_mode="sequential",
        environment="test",
        fail_fast_enabled=True,
        timeout_multiplier=0.5
    )
    print(f"Sequential Config: {sequential_config.layer_name}")
    print(f"  Strategy: {sequential_config.execution_strategy}")
    print(f"  Fail Fast: {sequential_config.fail_fast_enabled}")
    
    # Parallel configuration
    parallel_config = create_layer_execution_config(
        "core_integration",
        execution_mode="parallel_limited",
        environment="development",
        max_parallel_categories=4,
        use_real_services=True
    )
    print(f"\nParallel Config: {parallel_config.layer_name}")
    print(f"  Strategy: {parallel_config.execution_strategy}")
    print(f"  Max Parallel: {parallel_config.max_parallel_categories}")
    print(f"  Real Services: {parallel_config.use_real_services}")
    
    # Hybrid configuration
    hybrid_config = create_layer_execution_config(
        "service_integration",
        execution_mode="hybrid_smart",
        environment="staging",
        use_real_services=True,
        use_real_llm=True
    )
    print(f"\nHybrid Config: {hybrid_config.layer_name}")
    print(f"  Strategy: {hybrid_config.execution_strategy}")
    print(f"  Real LLM: {hybrid_config.use_real_llm}")
    
    return [sequential_config, parallel_config, hybrid_config]

async def demo_mock_layer_execution(agent: LayerExecutionAgent):
    """Demonstrate layer execution with mocked test runner"""
    print_section("Mock Layer Execution")
    
    # Create a configuration for fast execution
    config = LayerExecutionConfig(
        layer_name="fast_feedback",
        execution_strategy=ExecutionStrategy.SEQUENTIAL,
        environment="test",
        timeout_multiplier=0.01,  # Very fast for demo
        fail_fast_enabled=False
    )
    
    print(f"Executing layer: {config.layer_name}")
    print(f"Strategy: {config.execution_strategy.value}")
    
    # Mock the command execution for demo
    call_count = 0
    async def demo_mock_command(cmd, config):
        nonlocal call_count
        call_count += 1
        
        # Extract category from command
        category = "unknown"
        try:
            cat_idx = cmd.index("--category")
            if cat_idx + 1 < len(cmd):
                category = cmd[cat_idx + 1]
        except ValueError:
            pass
        
        print(f"  Executing category: {category}")
        
        # Simulate execution time
        await asyncio.sleep(0.05)
        
        # Return mock results
        if category == "smoke":
            return {
                "success": True,
                "output": "5 passed in 0.5s",
                "errors": "",
                "return_code": 0
            }
        elif category == "unit":
            return {
                "success": True,
                "output": "25 passed in 2.1s",
                "errors": "",
                "return_code": 0
            }
        else:
            return {
                "success": True,
                "output": f"10 passed in 1.0s",
                "errors": "",
                "return_code": 0
            }
    
    # Patch the command execution method
    original_execute = agent._execute_command
    agent._execute_command = demo_mock_command
    
    try:
        # Execute the layer
        start_time = time.time()
        result = await agent.execute_layer("fast_feedback", config)
        execution_time = time.time() - start_time
        
        # Show results
        print(f"\nExecution completed in {execution_time:.2f} seconds")
        print(f"Success: {result.success}")
        print(f"Categories executed: {len(result.categories_executed)}")
        print(f"Total tests: {result.total_tests}")
        print(f"Passed: {result.passed_tests}")
        print(f"Failed: {result.failed_tests}")
        
        print("\nCategory Details:")
        for category, details in result.category_results.items():
            print(f"  {category}: {details.get('test_counts', {}).get('total', 0)} tests")
            
    finally:
        # Restore original method
        agent._execute_command = original_execute

def demo_layer_characteristics(agent: LayerExecutionAgent):
    """Show characteristics of different layer types"""
    print_section("Layer Characteristics Analysis")
    
    layers = agent.layer_system.layers
    
    for layer_name, layer in list(layers.items())[:4]:  # Show first 4 layers
        print(f"\nLayer: {layer.name}")
        print(f"  Description: {layer.description}")
        print(f"  Execution Mode: {layer.execution_mode.value}")
        print(f"  Max Duration: {layer.max_duration_minutes} minutes")
        print(f"  Background Execution: {layer.background_execution}")
        print(f"  Categories: {len(layer.categories)}")
        print(f"  Required Services: {list(layer.required_services) if layer.required_services else 'None'}")
        print(f"  LLM Mode: {layer.llm_requirements.mode}")
        
        if layer.dependencies:
            print(f"  Dependencies: {list(layer.dependencies)}")
        
        if layer.conflicts:
            print(f"  Conflicts: {list(layer.conflicts)}")

def demo_execution_summary(agent: LayerExecutionAgent):
    """Show comprehensive execution summary"""
    print_section("Execution Summary")
    
    summary = agent.get_execution_summary()
    
    print(f"Agent ID: {summary['agent_id']}")
    print(f"Available Layers: {len(summary['available_layers'])}")
    print(f"Communication Enabled: {summary['communication_enabled']}")
    
    print("\nExecution Statistics:")
    stats = summary['execution_stats']
    print(f"  Layers Executed: {stats['layers_executed']}")
    print(f"  Categories Executed: {stats['categories_executed']}")
    print(f"  Total Duration: {stats['total_duration']}")
    print(f"  Success Rate: {stats['success_rate']:.1%}")
    
    print("\nLayer System Summary:")
    layer_summary = summary['layer_system_summary']
    print(f"  Total Layers: {layer_summary['total_layers']}")
    print(f"  Total Categories: {layer_summary['total_categories']}")
    print(f"  Background Layers: {layer_summary['background_layers']}")
    print(f"  Configuration Valid: {layer_summary['configuration_valid']}")

async def demo_resource_management(agent: LayerExecutionAgent):
    """Demonstrate resource allocation and management"""
    print_section("Resource Management Demo")
    
    # Get a layer for testing
    layer = agent.layer_system.layers.get("fast_feedback")
    config = LayerExecutionConfig(layer_name="fast_feedback", environment="test")
    
    print("Testing resource allocation...")
    
    # Test allocation
    allocated = await agent._allocate_resources(layer, config)
    print(f"Resource allocation successful: {allocated}")
    
    if allocated:
        print(f"Resources allocated: {len(agent.allocated_resources)}")
        
        # Show allocated resources
        for resource_key, resources in agent.allocated_resources.items():
            print(f"  {resource_key}: {resources}")
    
    # Test release
    await agent._release_resources(layer)
    print(f"Resources after release: {len(agent.allocated_resources)}")

async def main():
    """Main demo function"""
    print_banner("LayerExecutionAgent Comprehensive Demo")
    print("This demo showcases the LayerExecutionAgent capabilities")
    print("for managing individual test layer execution within the orchestration system.")
    
    try:
        # Basic functionality
        agent = await demo_basic_functionality()
        
        # Health check
        await demo_health_check(agent)
        
        # Execution configurations
        configs = demo_execution_configuration()
        
        # Layer characteristics
        demo_layer_characteristics(agent)
        
        # Resource management
        await demo_resource_management(agent)
        
        # Mock execution
        await demo_mock_layer_execution(agent)
        
        # Execution summary
        demo_execution_summary(agent)
        
        print_banner("Demo Complete")
        print("LayerExecutionAgent is ready for integration with the orchestration system!")
        print("\nKey Features Demonstrated:")
        print("[U+2713] Layer discovery and validation")
        print("[U+2713] Multiple execution strategies (sequential, parallel, hybrid)")
        print("[U+2713] Resource allocation and management")
        print("[U+2713] Health monitoring and reporting")
        print("[U+2713] Integration with existing unified_test_runner")
        print("[U+2713] Category execution coordination")
        print("[U+2713] Progress tracking and error handling")
        
    except Exception as e:
        print(f"\n FAIL:  Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    # Run the demo
    sys.exit(asyncio.run(main()))