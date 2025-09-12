#!/usr/bin/env python3
"""
Background E2E Agent Demo

This script demonstrates the key features of the BackgroundE2EAgent:
- Queuing E2E tests for background execution
- Monitoring queue status and task progress
- Retrieving background test results
- Managing background task lifecycle

Usage:
    python examples/background_e2e_demo.py
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_framework.orchestration.background_e2e_agent import (
    BackgroundE2EAgent,
    E2ETestCategory,
    BackgroundTaskConfig,
    BackgroundTaskStatus
)


def print_banner(title: str):
    """Print a formatted banner"""
    print(f"\n{'='*60}")
    print(f"{title:^60}")
    print(f"{'='*60}")


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'-'*40}")
    print(f"{title}")
    print(f"{'-'*40}")


def demo_basic_functionality():
    """Demonstrate basic BackgroundE2EAgent functionality"""
    print_banner("BACKGROUND E2E AGENT DEMO")
    
    # Initialize the agent
    project_root = Path(__file__).parent.parent
    agent = BackgroundE2EAgent(project_root=project_root, agent_id="demo_agent")
    
    try:
        print_section("1. Starting Background E2E Agent")
        agent.start()
        print(f"[U+2713] Agent started with ID: {agent.agent_id}")
        
        # Initial queue status
        print_section("2. Initial Queue Status")
        status = agent.get_queue_status()
        print(f"Agent Running: {status['agent_running']}")
        print(f"Queued Tasks: {status['queued_tasks']}")
        print(f"Active Tasks: {status['active_tasks']}")
        
        # Queue some E2E tests
        print_section("3. Queuing E2E Tests")
        
        # Queue a critical E2E test (fast)
        critical_config = BackgroundTaskConfig(
            category=E2ETestCategory.E2E_CRITICAL,
            environment="development",
            timeout_minutes=5,
            priority=1  # High priority
        )
        task_id1 = agent.queue_e2e_test(E2ETestCategory.E2E_CRITICAL, critical_config)
        print(f"[U+2713] Queued E2E Critical test: {task_id1}")
        
        # Queue a Cypress test (medium duration)
        cypress_config = BackgroundTaskConfig(
            category=E2ETestCategory.CYPRESS,
            environment="development", 
            timeout_minutes=20,
            priority=2,
            additional_args=["--no-coverage", "--fast-fail"],
            env_vars={"CYPRESS_ENV": "demo"}
        )
        task_id2 = agent.queue_e2e_test(E2ETestCategory.CYPRESS, cypress_config)
        print(f"[U+2713] Queued Cypress test: {task_id2}")
        
        # Queue a full E2E test (long duration)
        e2e_config = BackgroundTaskConfig(
            category=E2ETestCategory.E2E,
            environment="development",
            timeout_minutes=30,
            priority=3  # Lower priority
        )
        task_id3 = agent.queue_e2e_test(E2ETestCategory.E2E, e2e_config)
        print(f"[U+2713] Queued full E2E test: {task_id3}")
        
        # Check updated queue status
        print_section("4. Updated Queue Status")
        status = agent.get_queue_status()
        print(f"Queued Tasks: {status['queued_tasks']}")
        print(f"Active Tasks: {status['active_tasks']}")
        print(f"Queued by Category:")
        for category, count in status['queued_by_category'].items():
            print(f"  {category}: {count}")
        
        # Monitor task status
        print_section("5. Task Status Monitoring")
        tasks = [task_id1, task_id2, task_id3]
        
        for i, task_id in enumerate(tasks, 1):
            status = agent.get_task_status(task_id)
            if status:
                print(f"Task {i} ({task_id[:8]}...):")
                print(f"  Category: {status['category']}")
                print(f"  Status: {status['status']}")
                print(f"  Created: {status['created_at']}")
            else:
                print(f"Task {i}: Status not found")
        
        # Simulate waiting for some processing
        print_section("6. Simulating Background Execution")
        print("[U+23F3] In a real scenario, tests would run in the background...")
        print("[U+23F3] You could continue development while E2E tests execute...")
        
        # Show how to check recent results
        print_section("7. Recent Results (Demo)")
        recent_results = agent.get_recent_results(limit=5)
        if recent_results:
            print(f"Found {len(recent_results)} recent results:")
            for result in recent_results:
                print(f"  {result['task_id'][:8]}... | {result['category']} | {result['status']}")
        else:
            print("No recent results found (expected for demo)")
        
        # Demonstrate cancellation
        print_section("8. Task Cancellation Demo")
        # In a real scenario, you might cancel long-running tasks
        print("[U+2713] To cancel a task: agent.cancel_task(task_id)")
        print("[U+2713] To kill all background tasks: agent.stop()")
        
        print_section("9. CLI Integration Examples")
        print("The BackgroundE2EAgent integrates with unified_test_runner.py:")
        print()
        print("# Queue E2E tests in background")
        print("python unified_test_runner.py --background-e2e --background-category cypress")
        print()
        print("# Check queue status")
        print("python unified_test_runner.py --background-status")
        print()
        print("# View recent results")
        print("python unified_test_runner.py --background-results 10")
        print()
        print("# Cancel specific task")
        print("python unified_test_runner.py --kill-background TASK_ID")
        
    finally:
        # Clean shutdown
        print_section("10. Shutdown")
        agent.stop()
        print("[U+2713] Background E2E Agent stopped cleanly")
        
        print_banner("DEMO COMPLETE")
        print("Key Benefits:")
        print("[U+2022] Non-blocking E2E test execution")
        print("[U+2022] Queue management with prioritization")  
        print("[U+2022] Persistent result storage")
        print("[U+2022] Real-time status monitoring")
        print("[U+2022] Graceful failure recovery")
        print("[U+2022] Resource management and limits")
        print("[U+2022] Service dependency coordination")
        print("[U+2022] CLI integration for easy usage")


def demo_advanced_features():
    """Demonstrate advanced BackgroundE2EAgent features"""
    print_banner("ADVANCED FEATURES DEMO")
    
    project_root = Path(__file__).parent.parent
    agent = BackgroundE2EAgent(project_root=project_root, agent_id="advanced_demo")
    
    try:
        agent.start()
        
        print_section("Advanced Configuration Examples")
        
        # Performance test with resource limits
        perf_config = BackgroundTaskConfig(
            category=E2ETestCategory.PERFORMANCE,
            environment="staging",
            timeout_minutes=45,
            max_retries=1,
            cpu_limit_percent=50,  # Limit CPU usage
            memory_limit_gb=4,     # Limit memory usage
            priority=1,
            services_required={"postgres", "redis", "clickhouse", "backend"},
            additional_args=["--stress-test", "--load-factor=2"],
            env_vars={
                "PERF_MODE": "staging",
                "MAX_CONNECTIONS": "100",
                "TIMEOUT_MS": "30000"
            }
        )
        
        print("Performance Test Configuration:")
        print(f"  Category: {perf_config.category.value}")
        print(f"  Environment: {perf_config.environment}")
        print(f"  Timeout: {perf_config.timeout_minutes} minutes")
        print(f"  CPU Limit: {perf_config.cpu_limit_percent}%")
        print(f"  Memory Limit: {perf_config.memory_limit_gb}GB")
        print(f"  Services Required: {', '.join(perf_config.services_required)}")
        
        # Queue the performance test
        perf_task_id = agent.queue_e2e_test(E2ETestCategory.PERFORMANCE, perf_config)
        print(f"[U+2713] Queued performance test: {perf_task_id}")
        
        print_section("Context Manager Usage")
        print("The agent also supports context manager usage:")
        print()
        print("with BackgroundE2EAgent(project_root) as agent:")
        print("    task_id = agent.queue_e2e_test(E2ETestCategory.CYPRESS)")
        print("    # Agent automatically starts and stops")
        
    finally:
        agent.stop()


async def demo_async_integration():
    """Demonstrate async integration capabilities"""
    print_banner("ASYNC INTEGRATION DEMO")
    
    project_root = Path(__file__).parent.parent
    agent = BackgroundE2EAgent(project_root=project_root, agent_id="async_demo")
    
    try:
        agent.start()
        
        # Simulate orchestrator communication
        if hasattr(agent, 'handle_message'):
            print_section("Message Handling Simulation")
            print("[U+2713] Agent supports orchestrator message handling")
            print("[U+2713] Can receive queue requests from other agents")
            print("[U+2713] Can report status updates to orchestrator")
        
        print_section("Async Benefits")
        print("[U+2022] Non-blocking test execution")
        print("[U+2022] Concurrent task processing")
        print("[U+2022] Real-time progress updates")
        print("[U+2022] Efficient resource utilization")
        
    finally:
        agent.stop()


def main():
    """Main demo function"""
    try:
        # Run basic functionality demo
        demo_basic_functionality()
        
        # Run advanced features demo
        demo_advanced_features()
        
        # Run async integration demo (using asyncio.run for Python 3.7+)
        asyncio.run(demo_async_integration())
        
        print_banner("ALL DEMOS COMPLETED SUCCESSFULLY")
        
    except KeyboardInterrupt:
        print("\n\n WARNING: [U+FE0F]  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n FAIL:  Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())