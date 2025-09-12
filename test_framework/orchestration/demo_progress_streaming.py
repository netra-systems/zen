#!/usr/bin/env python3
"""
Quick Demo of ProgressStreamingAgent
====================================

This is a simplified demonstration of the ProgressStreamingAgent functionality
showing real-time progress updates during simulated test execution.
"""

import asyncio
import sys
from pathlib import Path

# Add project root for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.orchestration.progress_streaming_agent import (
    create_console_streaming_agent, ProgressStatus
)


async def demo_progress_streaming():
    """Quick demo showing progress streaming in action"""
    print("[U+1F680] ProgressStreamingAgent Demo")
    print("=" * 50)
    
    # Create console streaming agent
    agent = create_console_streaming_agent()
    print(f" PASS:  Agent initialized: {agent.agent_id}")
    
    # Start streaming for test layers
    layers = ["fast_feedback", "integration"]
    await agent.start_streaming(layers, "demo_run")
    print(" PASS:  Progress streaming started\n")
    
    try:
        # Simulate test execution progress
        
        # Layer 1: Fast Feedback
        print(" CHART:  Executing Layer 1: Fast Feedback")
        await agent.update_layer_progress("fast_feedback", status=ProgressStatus.RUNNING)
        
        # Category: smoke tests
        await agent.update_layer_progress("fast_feedback", "smoke", status=ProgressStatus.RUNNING)
        for i in range(1, 11):
            await asyncio.sleep(0.1)
            progress = (i / 10) * 100
            await agent.update_layer_progress("fast_feedback", "smoke", progress=progress,
                                            test_counts={"total": 10, "passed": i, "failed": 0})
        await agent.update_layer_progress("fast_feedback", "smoke", status=ProgressStatus.COMPLETED)
        
        # Category: unit tests  
        await agent.update_layer_progress("fast_feedback", "unit", status=ProgressStatus.RUNNING)
        for i in range(1, 21):
            await asyncio.sleep(0.05)
            progress = (i / 20) * 100
            failed = 1 if i > 15 else 0  # One test fails
            await agent.update_layer_progress("fast_feedback", "unit", progress=progress,
                                            test_counts={"total": 20, "passed": i - failed, "failed": failed})
        await agent.update_layer_progress("fast_feedback", "unit", status=ProgressStatus.COMPLETED)
        
        await agent.update_layer_progress("fast_feedback", status=ProgressStatus.COMPLETED)
        print(" PASS:  Layer 1 completed\n")
        
        # Layer 2: Integration
        print(" CHART:  Executing Layer 2: Integration")
        await agent.update_layer_progress("integration", status=ProgressStatus.RUNNING)
        
        await agent.update_layer_progress("integration", "api", status=ProgressStatus.RUNNING)
        for i in range(1, 16):
            await asyncio.sleep(0.1)
            progress = (i / 15) * 100
            await agent.update_layer_progress("integration", "api", progress=progress,
                                            test_counts={"total": 15, "passed": i, "failed": 0})
        await agent.update_layer_progress("integration", "api", status=ProgressStatus.COMPLETED)
        
        await agent.update_layer_progress("integration", status=ProgressStatus.COMPLETED)
        print(" PASS:  Layer 2 completed\n")
        
        # Background task simulation
        print(" CYCLE:  Background tasks started")
        await agent.update_background_task("e2e_test", "started", progress=0)
        for i in range(0, 101, 20):
            await asyncio.sleep(0.2)
            await agent.update_background_task("e2e_test", "running", progress=i)
        await agent.update_background_task("e2e_test", "completed", progress=100)
        print(" PASS:  Background tasks completed\n")
        
        # Wait a moment to see final status
        await asyncio.sleep(0.5)
        
        # Get final statistics
        stats = agent.get_statistics()
        print("[U+1F4C8] Final Statistics:")
        print(f"   Total Updates: {stats['update_count']}")
        print(f"   Execution Duration: {stats['duration']:.2f}s")
        print(f"   Layers Processed: {stats['layers_count']}")
        print(f"   Background Tasks: {stats['background_tasks_count']}")
        
        success = True
        
    except Exception as e:
        print(f" FAIL:  Demo failed: {e}")
        success = False
    
    finally:
        # Stop streaming
        await agent.stop_streaming(success=success)
        print(f"\n TARGET:  Demo completed {'successfully' if success else 'with errors'}")


async def demo_json_output():
    """Demo JSON output mode"""
    print("\n" + "=" * 50)
    print("[U+1F527] JSON Output Mode Demo")
    print("=" * 50)
    
    from test_framework.orchestration.progress_streaming_agent import (
        ProgressStreamingAgent, StreamingConfig, ProgressOutputMode
    )
    
    config = StreamingConfig(output_mode=ProgressOutputMode.JSON)
    agent = ProgressStreamingAgent(config=config)
    
    await agent.start_streaming(["test_layer"], "json_demo")
    
    # Quick progress simulation
    await agent.update_layer_progress("test_layer", status=ProgressStatus.RUNNING)
    await agent.update_layer_progress("test_layer", "test_cat", status=ProgressStatus.RUNNING)
    await agent.update_layer_progress("test_layer", "test_cat", progress=100.0,
                                    test_counts={"total": 5, "passed": 5, "failed": 0})
    await agent.update_layer_progress("test_layer", "test_cat", status=ProgressStatus.COMPLETED)
    await agent.update_layer_progress("test_layer", status=ProgressStatus.COMPLETED)
    
    await asyncio.sleep(0.2)  # Allow processing
    await agent.stop_streaming(success=True)
    
    print(" PASS:  JSON output demo completed")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ProgressStreamingAgent Demo")
    parser.add_argument("--mode", choices=["console", "json", "both"], default="console")
    args = parser.parse_args()
    
    async def run_demos():
        if args.mode in ["console", "both"]:
            await demo_progress_streaming()
        
        if args.mode in ["json", "both"]:
            await demo_json_output()
    
    # Run the demo
    try:
        asyncio.run(run_demos())
    except KeyboardInterrupt:
        print("\n[U+1F44B] Demo interrupted by user")
    except Exception as e:
        print(f"\n[U+1F4A5] Demo failed: {e}")
        sys.exit(1)