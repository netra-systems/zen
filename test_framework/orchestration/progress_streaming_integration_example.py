#!/usr/bin/env python3
"""
Progress Streaming Integration Example
======================================

This example demonstrates how to integrate the ProgressStreamingAgent with:
1. LayerExecutionAgent for real-time layer progress
2. BackgroundE2EAgent for background task monitoring  
3. TestOrchestratorAgent for overall orchestration
4. WebSocket system for live web interface updates
5. Existing progress tracking infrastructure

Business Value: Shows complete integration of progress streaming across
the entire test execution pipeline, providing users with comprehensive
real-time visibility into test progress.

Usage Examples:
- Console progress display during CLI test execution
- JSON streaming for CI/CD pipeline integration  
- WebSocket streaming for real-time web dashboards
- Background task monitoring for long-running E2E tests
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.orchestration.progress_streaming_agent import (
    ProgressStreamingAgent, ProgressOutputMode, ProgressEventType,
    StreamingConfig, create_console_streaming_agent, create_websocket_streaming_agent
)

# Import orchestration agents for integration
try:
    from test_framework.orchestration.layer_execution_agent import (
        LayerExecutionAgent, LayerExecutionConfig, ExecutionStrategy
    )
    from test_framework.orchestration.background_e2e_agent import BackgroundE2EAgent
    ORCHESTRATION_AVAILABLE = True
except ImportError:
    ORCHESTRATION_AVAILABLE = False
    print("Orchestration agents not available - running in demo mode")

# WebSocket integration imports
try:
    from netra_backend.app.websocket_core.manager import WebSocketManager  
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("WebSocket integration not available")

from test_framework.progress_tracker import ProgressStatus


class IntegratedProgressOrchestrator:
    """
    Orchestrator that demonstrates integration of ProgressStreamingAgent
    with all test execution components.
    """
    
    def __init__(self, project_root: Path = None, websocket_manager=None, thread_id: str = None):
        self.project_root = project_root or Path.cwd()
        self.websocket_manager = websocket_manager
        self.thread_id = thread_id
        
        # Initialize agents
        self.progress_agent = None
        self.layer_agent = None
        self.background_agent = None
        
        # Execution state
        self.active_layers: Dict[str, Any] = {}
        self.background_tasks: Dict[str, Any] = {}
        self.execution_start_time = None
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("IntegratedProgressOrchestrator")
    
    async def initialize_with_console_output(self):
        """Initialize with console progress output"""
        self.progress_agent = create_console_streaming_agent(self.project_root)
        await self._setup_integrations()
        self.logger.info("Initialized with console progress output")
    
    async def initialize_with_websocket_output(self, websocket_manager, thread_id: str):
        """Initialize with WebSocket progress output"""
        if not WEBSOCKET_AVAILABLE:
            raise RuntimeError("WebSocket integration not available")
        
        self.progress_agent = create_websocket_streaming_agent(
            websocket_manager, thread_id, self.project_root
        )
        await self._setup_integrations()
        self.logger.info(f"Initialized with WebSocket progress output for thread: {thread_id}")
    
    async def initialize_with_json_output(self):
        """Initialize with JSON progress output for CI/CD"""
        from test_framework.orchestration.progress_streaming_agent import create_json_streaming_agent
        self.progress_agent = create_json_streaming_agent(self.project_root)
        await self._setup_integrations()
        self.logger.info("Initialized with JSON progress output")
    
    async def _setup_integrations(self):
        """Setup integrations between components"""
        if not self.progress_agent:
            raise RuntimeError("Progress agent not initialized")
        
        # Setup layer execution agent if available
        if ORCHESTRATION_AVAILABLE:
            self.layer_agent = LayerExecutionAgent(self.project_root)
            # In real integration, you would connect layer agent events to progress agent
            
        # Add custom event handlers
        self.progress_agent.add_event_subscriber(self._handle_progress_event)
        
        self.logger.info("Component integrations setup complete")
    
    async def _handle_progress_event(self, event_type: ProgressEventType, data: Dict[str, Any]):
        """Handle progress events for custom processing"""
        # Custom event processing - log important events, trigger actions, etc.
        if event_type in [ProgressEventType.LAYER_FAILED, ProgressEventType.ORCHESTRATION_FAILED]:
            self.logger.error(f"Critical failure: {event_type.value} - {data}")
        elif event_type in [ProgressEventType.LAYER_COMPLETED, ProgressEventType.ORCHESTRATION_COMPLETED]:
            self.logger.info(f"Success: {event_type.value} - {data}")
    
    async def execute_comprehensive_test_suite(self, test_levels: List[str] = None, 
                                            categories: List[str] = None,
                                            use_real_services: bool = False,
                                            use_real_llm: bool = False) -> bool:
        """
        Execute comprehensive test suite with full progress streaming
        
        Args:
            test_levels: Test levels to execute (e.g., ['unit', 'integration', 'e2e'])
            categories: Specific categories to run
            use_real_services: Whether to use real services
            use_real_llm: Whether to use real LLM
            
        Returns:
            bool: Success status
        """
        if not self.progress_agent:
            raise RuntimeError("Progress agent not initialized - call initialize_* method first")
        
        # Default test configuration
        test_levels = test_levels or ['fast_feedback', 'core_integration', 'service_integration', 'e2e_performance']
        categories = categories or ['smoke', 'unit', 'integration', 'api', 'websocket', 'e2e']
        
        self.execution_start_time = datetime.now()
        overall_success = True
        
        try:
            # Start progress streaming
            run_id = f"comprehensive_run_{int(time.time())}"
            await self.progress_agent.start_streaming(test_levels, run_id)
            
            self.logger.info(f"Starting comprehensive test execution: {run_id}")
            self.logger.info(f"Test levels: {test_levels}")
            self.logger.info(f"Categories: {categories}")
            
            # Execute each test level
            for i, level_name in enumerate(test_levels):
                self.logger.info(f"Executing test level {i+1}/{len(test_levels)}: {level_name}")
                
                success = await self._execute_test_level(
                    level_name, categories, use_real_services, use_real_llm
                )
                
                if not success:
                    overall_success = False
                    self.logger.error(f"Test level failed: {level_name}")
                    # Continue with other levels unless it's a critical failure
            
            # Execute background tasks
            if test_levels[-1] == 'e2e_performance':
                await self._execute_background_tasks()
            
            # Final summary
            execution_time = (datetime.now() - self.execution_start_time).total_seconds()
            self.logger.info(f"Comprehensive test execution completed in {execution_time:.2f}s")
            
            return overall_success
            
        except Exception as e:
            self.logger.error(f"Comprehensive test execution failed: {e}")
            overall_success = False
            raise
            
        finally:
            # Stop progress streaming
            if self.progress_agent and self.progress_agent.active:
                await self.progress_agent.stop_streaming(success=overall_success)
    
    async def _execute_test_level(self, level_name: str, categories: List[str], 
                                use_real_services: bool, use_real_llm: bool) -> bool:
        """Execute a single test level with progress tracking"""
        
        # Start level execution
        await self.progress_agent.update_layer_progress(level_name, status=ProgressStatus.RUNNING)
        
        level_success = True
        level_categories = self._get_categories_for_level(level_name, categories)
        
        try:
            # Execute categories in this level
            for category_name in level_categories:
                success = await self._execute_category(level_name, category_name, use_real_services, use_real_llm)
                if not success:
                    level_success = False
            
            # Complete level
            final_status = ProgressStatus.COMPLETED if level_success else ProgressStatus.FAILED
            await self.progress_agent.update_layer_progress(level_name, status=final_status)
            
            return level_success
            
        except Exception as e:
            self.logger.error(f"Error in test level {level_name}: {e}")
            await self.progress_agent.update_layer_progress(level_name, status=ProgressStatus.FAILED)
            return False
    
    async def _execute_category(self, level_name: str, category_name: str, 
                              use_real_services: bool, use_real_llm: bool) -> bool:
        """Execute a single test category with detailed progress"""
        
        self.logger.info(f"Executing category: {category_name} in level: {level_name}")
        
        # Start category
        await self.progress_agent.update_layer_progress(
            level_name, category_name, status=ProgressStatus.RUNNING
        )
        
        try:
            # Simulate category execution with real progress updates
            if ORCHESTRATION_AVAILABLE and self.layer_agent:
                # Use real layer execution agent
                config = LayerExecutionConfig(
                    layer_name=level_name,
                    use_real_services=use_real_services,
                    use_real_llm=use_real_llm,
                    execution_strategy=ExecutionStrategy.HYBRID_SMART
                )
                
                # In real implementation, you would:
                # 1. Configure the layer agent with the specific category
                # 2. Execute the category
                # 3. Stream progress updates to the progress agent
                # For now, we simulate this
                
                success = await self._simulate_category_execution(level_name, category_name)
                
            else:
                # Fallback simulation
                success = await self._simulate_category_execution(level_name, category_name)
            
            # Complete category
            final_status = ProgressStatus.COMPLETED if success else ProgressStatus.FAILED
            await self.progress_agent.update_layer_progress(
                level_name, category_name, status=final_status
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Category execution failed: {category_name}: {e}")
            await self.progress_agent.update_layer_progress(
                level_name, category_name, status=ProgressStatus.FAILED
            )
            return False
    
    async def _simulate_category_execution(self, level_name: str, category_name: str) -> bool:
        """Simulate category execution with realistic progress updates"""
        
        # Determine test count based on category type
        test_counts = {
            'smoke': 15,
            'unit': 50,
            'integration': 25,
            'api': 20,
            'websocket': 10,
            'e2e': 8,
            'performance': 5
        }
        
        total_tests = test_counts.get(category_name, 20)
        passed_tests = 0
        failed_tests = 0
        
        # Simulate test execution with progress updates
        for test_num in range(total_tests):
            # Simulate test execution time
            test_duration = {
                'smoke': 0.1,
                'unit': 0.05,  
                'integration': 0.3,
                'api': 0.2,
                'websocket': 0.4,
                'e2e': 1.0,
                'performance': 2.0
            }.get(category_name, 0.2)
            
            await asyncio.sleep(test_duration)
            
            # Simulate test result (90% success rate)
            test_passed = (test_num < total_tests * 0.9)
            if test_passed:
                passed_tests += 1
            else:
                failed_tests += 1
            
            # Update progress
            progress = ((test_num + 1) / total_tests) * 100
            await self.progress_agent.update_layer_progress(
                level_name, category_name, 
                progress=progress,
                test_counts={
                    "total": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "skipped": 0
                }
            )
        
        # Category succeeds if less than 10% failures
        success = failed_tests <= (total_tests * 0.1)
        self.logger.info(f"Category {category_name} {'PASSED' if success else 'FAILED'}: "
                        f"{passed_tests}/{total_tests} tests passed")
        
        return success
    
    async def _execute_background_tasks(self):
        """Execute background tasks (like E2E performance tests)"""
        background_tasks = [
            {"id": "e2e_user_journey_1", "duration": 30, "name": "User Registration Journey"},
            {"id": "e2e_user_journey_2", "duration": 45, "name": "Data Analysis Workflow"}, 
            {"id": "performance_load_test", "duration": 60, "name": "Load Testing"}
        ]
        
        self.logger.info(f"Starting {len(background_tasks)} background tasks")
        
        # Start all background tasks
        task_futures = []
        for task_info in background_tasks:
            future = asyncio.create_task(self._execute_background_task(task_info))
            task_futures.append(future)
        
        # Wait for all to complete
        await asyncio.gather(*task_futures, return_exceptions=True)
        
        self.logger.info("All background tasks completed")
    
    async def _execute_background_task(self, task_info: Dict[str, Any]):
        """Execute a single background task"""
        task_id = task_info["id"]
        duration = task_info["duration"] 
        task_name = task_info["name"]
        
        self.logger.info(f"Starting background task: {task_name}")
        
        # Start task
        await self.progress_agent.update_background_task(
            task_id, "started", progress=0.0, name=task_name
        )
        
        try:
            # Simulate task execution with progress updates
            steps = 20
            for step in range(steps):
                await asyncio.sleep(duration / steps)
                
                progress = ((step + 1) / steps) * 100
                await self.progress_agent.update_background_task(
                    task_id, "running", progress=progress
                )
            
            # Complete task
            await self.progress_agent.update_background_task(
                task_id, "completed", progress=100.0
            )
            
            self.logger.info(f"Background task completed: {task_name}")
            
        except Exception as e:
            self.logger.error(f"Background task failed: {task_name}: {e}")
            await self.progress_agent.update_background_task(
                task_id, "failed", progress=0.0, error=str(e)
            )
    
    def _get_categories_for_level(self, level_name: str, all_categories: List[str]) -> List[str]:
        """Get categories appropriate for a test level"""
        level_categories = {
            'fast_feedback': ['smoke', 'unit'],
            'core_integration': ['integration', 'api'], 
            'service_integration': ['websocket', 'integration'],
            'e2e_performance': ['e2e', 'performance']
        }
        
        return level_categories.get(level_name, all_categories[:2])


# Example usage and demonstrations

async def demo_console_progress():
    """Demonstrate console progress streaming"""
    print("=== Console Progress Streaming Demo ===")
    
    orchestrator = IntegratedProgressOrchestrator()
    await orchestrator.initialize_with_console_output()
    
    success = await orchestrator.execute_comprehensive_test_suite(
        test_levels=['fast_feedback', 'core_integration'],
        categories=['smoke', 'unit', 'integration'],
        use_real_services=False
    )
    
    print(f"Demo completed with success: {success}")


async def demo_json_progress():
    """Demonstrate JSON progress streaming for CI/CD"""
    print("=== JSON Progress Streaming Demo ===")
    
    orchestrator = IntegratedProgressOrchestrator()
    await orchestrator.initialize_with_json_output()
    
    success = await orchestrator.execute_comprehensive_test_suite(
        test_levels=['fast_feedback'],
        categories=['smoke', 'unit'],
        use_real_services=False
    )
    
    print(f"JSON demo completed with success: {success}")


async def demo_websocket_progress():
    """Demonstrate WebSocket progress streaming"""
    print("=== WebSocket Progress Streaming Demo ===")
    
    if not WEBSOCKET_AVAILABLE:
        print("WebSocket integration not available - skipping demo")
        return
    
    # Create mock WebSocket manager for demo
    class MockWebSocketManager:
        def __init__(self):
            self.messages = []
        
        async def send_to_thread(self, thread_id: str, message: Dict) -> bool:
            self.messages.append({'thread_id': thread_id, 'message': message})
            print(f"WebSocket -> {thread_id}: {message.get('type', 'unknown')}")
            return True
        
        async def broadcast(self, message: Dict) -> bool:
            self.messages.append({'thread_id': 'broadcast', 'message': message})
            return True
    
    mock_ws_manager = MockWebSocketManager()
    
    orchestrator = IntegratedProgressOrchestrator()
    await orchestrator.initialize_with_websocket_output(mock_ws_manager, "demo_thread")
    
    success = await orchestrator.execute_comprehensive_test_suite(
        test_levels=['fast_feedback'],
        categories=['smoke'],
        use_real_services=False
    )
    
    print(f"WebSocket demo completed with success: {success}")
    print(f"Total WebSocket messages sent: {len(mock_ws_manager.messages)}")


async def demo_full_integration():
    """Demonstrate full integration with all features"""
    print("=== Full Integration Demo ===")
    
    orchestrator = IntegratedProgressOrchestrator()
    await orchestrator.initialize_with_console_output()
    
    # Full test suite
    success = await orchestrator.execute_comprehensive_test_suite(
        test_levels=['fast_feedback', 'core_integration', 'service_integration', 'e2e_performance'],
        categories=['smoke', 'unit', 'integration', 'api', 'websocket', 'e2e'],
        use_real_services=False,
        use_real_llm=False
    )
    
    print(f"Full integration demo completed with success: {success}")


# CLI interface for running demos
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Progress Streaming Integration Examples")
    parser.add_argument("--demo", choices=['console', 'json', 'websocket', 'full'], 
                       default='console', help="Demo type to run")
    parser.add_argument("--real-services", action="store_true", 
                       help="Use real services (requires proper setup)")
    parser.add_argument("--real-llm", action="store_true",
                       help="Use real LLM (requires API keys)")
    
    args = parser.parse_args()
    
    async def run_selected_demo():
        if args.demo == 'console':
            await demo_console_progress()
        elif args.demo == 'json':  
            await demo_json_progress()
        elif args.demo == 'websocket':
            await demo_websocket_progress()
        elif args.demo == 'full':
            await demo_full_integration()
    
    print(f"Running {args.demo} progress streaming demo...")
    asyncio.run(run_selected_demo())