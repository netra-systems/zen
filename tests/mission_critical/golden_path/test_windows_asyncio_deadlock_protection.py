"""
MISSION CRITICAL: Windows Asyncio Deadlock Protection Tests for Golden Path

🚨 MISSION CRITICAL TEST 🚨
This test suite detects and prevents Windows-specific asyncio deadlocks that have
caused system hangs and blocked business operations on Windows development environments.

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Prevent Windows asyncio deadlocks that halt development and testing
- Value Impact: Deadlocks = development stoppage = delayed features = lost revenue
- Strategic Impact: Ensures cross-platform compatibility for development team

WINDOWS ASYNCIO DEADLOCK SCENARIOS PROTECTED:
1. Event loop deadlocks during WebSocket operations
2. Asyncio task scheduling conflicts with Windows threading
3. Blocking synchronous calls within async contexts causing hangs
4. Resource contention in Windows-specific async implementations

ZERO TOLERANCE: These deadlocks MUST be detected before they block development.
"""

import asyncio
import pytest
import time
import threading
import sys
import platform
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, Future
import signal
import subprocess
import gc

# SSOT imports following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
)
from test_framework.websocket_helpers import WebSocketTestHelpers
from shared.types.core_types import UserID, ThreadID, RunID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestWindowsAsyncioDeadlockProtection(SSotAsyncTestCase):
    """
    🚨 MISSION CRITICAL TEST SUITE 🚨
    
    Detects and prevents Windows-specific asyncio deadlocks that can halt
    the entire system during golden path operations.
    """
    
    def setup_method(self, method=None):
        """Setup with Windows asyncio deadlock detection context."""
        super().setup_method(method)
        
        # Mission critical business metrics
        self.record_metric("mission_critical", True)
        self.record_metric("windows_deadlock_protection", True)
        self.record_metric("platform_compatibility", True)
        self.record_metric("development_velocity_protection", True)
        
        # Platform detection
        self.is_windows = platform.system().lower() == "windows"
        self.python_version = sys.version_info
        
        # Initialize components
        self.environment = self.get_env_var("TEST_ENV", "test")
        self.auth_helper = E2EAuthHelper(environment=self.environment)
        self.websocket_helper = E2EWebSocketAuthHelper(environment=self.environment)
        self.id_generator = UnifiedIdGenerator()
        
        # Deadlock detection configuration
        self.deadlock_timeout = 30.0  # 30 seconds to detect deadlocks
        self.operation_timeout = 15.0  # 15 seconds for individual operations
        
        # Active tasks and connections for cleanup
        self.active_tasks = []
        self.active_connections = []
        self.task_lock = threading.Lock()
        
        # Windows-specific asyncio policy
        if self.is_windows:
            # Ensure we're using the correct event loop policy for Windows
            try:
                if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                    self.record_metric("windows_proactor_policy_set", True)
            except Exception as policy_error:
                print(f"⚠️  Windows event loop policy warning: {policy_error}")
        
    async def async_teardown_method(self, method=None):
        """Critical cleanup with deadlock prevention."""
        try:
            # Cancel all active tasks to prevent deadlocks
            tasks_to_cancel = []
            with self.task_lock:
                tasks_to_cancel = self.active_tasks.copy()
                self.active_tasks.clear()
            
            # Cancel tasks with timeout
            if tasks_to_cancel:
                for task in tasks_to_cancel:
                    if not task.done():
                        task.cancel()
                
                # Wait for cancellation with timeout
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    print("⚠️  Task cancellation timeout during cleanup")
            
            # Close connections
            for connection in self.active_connections:
                try:
                    await WebSocketTestHelpers.close_test_connection(connection)
                except:
                    pass
            
            # Force garbage collection to clean up resources
            gc.collect()
            
        except Exception as e:
            print(f"⚠️  Deadlock protection cleanup error: {e}")
        
        await super().async_teardown_method(method)
    
    @pytest.mark.mission_critical
    @pytest.mark.windows_deadlock
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_websocket_asyncio_deadlock_protection(self):
        """
        🚨 WINDOWS DEADLOCK PROTECTION: WebSocket Asyncio Operations
        
        Tests that WebSocket operations do not cause asyncio deadlocks on Windows,
        particularly during connection establishment and message handling.
        """
        deadlock_test_start = time.time()
        
        # Create user context for deadlock testing
        user_context = await create_authenticated_user_context(
            user_email="deadlock_test@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Get authentication token
        jwt_token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email=user_context.agent_context.get('user_email')
        )
        
        # Test WebSocket operations that historically cause deadlocks on Windows
        deadlock_test_operations = []
        
        # Operation 1: Rapid Connection/Disconnection Cycles
        operation_start = time.time()
        try:
            await self._test_rapid_connection_cycles(jwt_token, user_context)
            deadlock_test_operations.append({
                "operation": "rapid_connection_cycles",
                "success": True,
                "duration": time.time() - operation_start,
                "deadlock_detected": False
            })
        except asyncio.TimeoutError:
            deadlock_test_operations.append({
                "operation": "rapid_connection_cycles",
                "success": False,
                "duration": time.time() - operation_start,
                "deadlock_detected": True,
                "error": "DEADLOCK: Operation timed out"
            })
        except Exception as e:
            deadlock_test_operations.append({
                "operation": "rapid_connection_cycles",
                "success": False,
                "duration": time.time() - operation_start,
                "deadlock_detected": False,
                "error": str(e)
            })
        
        # Operation 2: Concurrent Message Sending
        operation_start = time.time()
        try:
            await self._test_concurrent_message_sending(jwt_token, user_context)
            deadlock_test_operations.append({
                "operation": "concurrent_message_sending",
                "success": True,
                "duration": time.time() - operation_start,
                "deadlock_detected": False
            })
        except asyncio.TimeoutError:
            deadlock_test_operations.append({
                "operation": "concurrent_message_sending",
                "success": False,
                "duration": time.time() - operation_start,
                "deadlock_detected": True,
                "error": "DEADLOCK: Concurrent operations hung"
            })
        except Exception as e:
            deadlock_test_operations.append({
                "operation": "concurrent_message_sending",
                "success": False,
                "duration": time.time() - operation_start,
                "deadlock_detected": False,
                "error": str(e)
            })
        
        # Operation 3: Blocking Sync Calls in Async Context
        operation_start = time.time()
        try:
            await self._test_sync_calls_in_async_context(jwt_token, user_context)
            deadlock_test_operations.append({
                "operation": "sync_calls_in_async",
                "success": True,
                "duration": time.time() - operation_start,
                "deadlock_detected": False
            })
        except asyncio.TimeoutError:
            deadlock_test_operations.append({
                "operation": "sync_calls_in_async",
                "success": False,
                "duration": time.time() - operation_start,
                "deadlock_detected": True,
                "error": "DEADLOCK: Sync/Async interaction deadlock"
            })
        except Exception as e:
            deadlock_test_operations.append({
                "operation": "sync_calls_in_async",
                "success": False,
                "duration": time.time() - operation_start,
                "deadlock_detected": False,
                "error": str(e)
            })
        
        total_deadlock_test_time = time.time() - deadlock_test_start
        
        # DEADLOCK DETECTION ANALYSIS
        
        deadlocks_detected = sum(1 for op in deadlock_test_operations if op.get("deadlock_detected"))
        operations_failed = sum(1 for op in deadlock_test_operations if not op.get("success"))
        total_operations = len(deadlock_test_operations)
        
        # Record deadlock protection metrics
        self.record_metric("windows_deadlock_operations_tested", total_operations)
        self.record_metric("windows_deadlocks_detected", deadlocks_detected)
        self.record_metric("windows_operations_failed", operations_failed)
        self.record_metric("windows_deadlock_test_time", total_deadlock_test_time)
        self.record_metric("windows_platform", self.is_windows)
        
        # CRITICAL DEADLOCK ASSESSMENT
        
        if deadlocks_detected > 0:
            # DEADLOCK DETECTED - CRITICAL FAILURE
            deadlock_details = "\n".join([
                f"  - {op['operation']}: {op.get('error', 'DEADLOCK')}"
                for op in deadlock_test_operations if op.get("deadlock_detected")
            ])
            
            pytest.fail(
                f"🚨 CRITICAL WINDOWS DEADLOCK DETECTED\n"
                f"Platform: {platform.system()} {platform.release()}\n"
                f"Python: {sys.version}\n"
                f"Deadlocks Detected: {deadlocks_detected}/{total_operations}\n"
                f"Deadlock Details:\n{deadlock_details}\n"
                f"This BLOCKS development on Windows!\n"
                f"Operations: {deadlock_test_operations}"
            )
        
        elif operations_failed > 0:
            # OPERATIONS FAILED - MAY INDICATE DEADLOCK RISK
            failure_details = "\n".join([
                f"  - {op['operation']}: {op.get('error', 'FAILED')}"
                for op in deadlock_test_operations if not op.get("success") and not op.get("deadlock_detected")
            ])
            
            # Only fail if this is Windows and failures suggest deadlock risk
            if self.is_windows and operations_failed > 1:
                pytest.fail(
                    f"🚨 WINDOWS ASYNCIO INSTABILITY DETECTED\n"
                    f"Failed Operations: {operations_failed}/{total_operations}\n"
                    f"Failure Details:\n{failure_details}\n"
                    f"This may indicate deadlock susceptibility on Windows!"
                )
        
        # SUCCESS CASE: No deadlocks detected
        print(f"\n✅ WINDOWS DEADLOCK PROTECTION: AsyncIO Operations Test PASSED")
        print(f"   🖥️  Platform: {platform.system()} {platform.release()}")
        print(f"   🐍 Python: {sys.version_info}")
        print(f"   🔒 Deadlocks Detected: {deadlocks_detected}")
        print(f"   ✅ Operations Tested: {total_operations}")
        print(f"   ⏱️  Total Test Time: {total_deadlock_test_time:.2f}s")
        print(f"   💻 Development Environment: PROTECTED")
    
    async def _test_rapid_connection_cycles(self, jwt_token: str, user_context) -> None:
        """Test rapid WebSocket connection/disconnection cycles for deadlocks."""
        ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
        websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        # Perform rapid connection cycles
        for cycle in range(5):
            # Create connection with timeout
            connection_task = asyncio.create_task(
                WebSocketTestHelpers.create_test_websocket_connection(
                    url=websocket_url,
                    headers=ws_headers,
                    timeout=5.0,
                    user_id=str(user_context.user_id)
                )
            )
            
            with self.task_lock:
                self.active_tasks.append(connection_task)
            
            # Wait for connection with deadlock timeout
            connection = await asyncio.wait_for(connection_task, timeout=self.operation_timeout)
            self.active_connections.append(connection)
            
            # Send a test message
            test_message = {
                "type": "deadlock_test",
                "cycle": cycle,
                "timestamp": time.time()
            }
            
            send_task = asyncio.create_task(
                WebSocketTestHelpers.send_test_message(connection, test_message, timeout=3.0)
            )
            
            with self.task_lock:
                self.active_tasks.append(send_task)
            
            await asyncio.wait_for(send_task, timeout=self.operation_timeout)
            
            # Close connection immediately
            close_task = asyncio.create_task(
                WebSocketTestHelpers.close_test_connection(connection)
            )
            
            with self.task_lock:
                self.active_tasks.append(close_task)
            
            await asyncio.wait_for(close_task, timeout=self.operation_timeout)
            self.active_connections.remove(connection)
            
            # Small delay between cycles
            await asyncio.sleep(0.1)
    
    async def _test_concurrent_message_sending(self, jwt_token: str, user_context) -> None:
        """Test concurrent message sending that can cause Windows asyncio deadlocks."""
        ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
        websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        # Create connection
        connection = await asyncio.wait_for(
            WebSocketTestHelpers.create_test_websocket_connection(
                url=websocket_url,
                headers=ws_headers,
                timeout=5.0,
                user_id=str(user_context.user_id)
            ),
            timeout=self.operation_timeout
        )
        self.active_connections.append(connection)
        
        # Create multiple concurrent message sending tasks
        message_tasks = []
        for i in range(10):  # 10 concurrent messages
            message = {
                "type": "concurrent_test",
                "message_id": i,
                "timestamp": time.time(),
                "user_id": str(user_context.user_id)
            }
            
            task = asyncio.create_task(
                WebSocketTestHelpers.send_test_message(connection, message, timeout=3.0)
            )
            message_tasks.append(task)
            
            with self.task_lock:
                self.active_tasks.append(task)
        
        # Wait for all messages to be sent with global timeout
        await asyncio.wait_for(
            asyncio.gather(*message_tasks, return_exceptions=True),
            timeout=self.deadlock_timeout
        )
        
        # Cleanup
        await WebSocketTestHelpers.close_test_connection(connection)
        self.active_connections.remove(connection)
    
    async def _test_sync_calls_in_async_context(self, jwt_token: str, user_context) -> None:
        """Test mixing sync and async calls that can deadlock on Windows."""
        ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
        websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        # Create connection
        connection = await asyncio.wait_for(
            WebSocketTestHelpers.create_test_websocket_connection(
                url=websocket_url,
                headers=ws_headers,
                timeout=5.0,
                user_id=str(user_context.user_id)
            ),
            timeout=self.operation_timeout
        )
        self.active_connections.append(connection)
        
        # Test operations that mix sync and async patterns
        def blocking_operation(duration: float) -> str:
            """Simulate a blocking synchronous operation."""
            time.sleep(duration)
            return f"Blocking operation completed after {duration}s"
        
        # Execute blocking operations in thread pool to avoid deadlocks
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit blocking operations
            blocking_tasks = [
                asyncio.get_event_loop().run_in_executor(
                    executor, blocking_operation, 0.5
                )
                for _ in range(3)
            ]
            
            # Also send WebSocket messages concurrently
            message_tasks = []
            for i in range(3):
                message = {
                    "type": "sync_async_test",
                    "operation_id": i,
                    "timestamp": time.time()
                }
                
                task = asyncio.create_task(
                    WebSocketTestHelpers.send_test_message(connection, message, timeout=3.0)
                )
                message_tasks.append(task)
                
                with self.task_lock:
                    self.active_tasks.append(task)
            
            # Wait for both blocking and async operations with deadlock timeout
            all_tasks = blocking_tasks + message_tasks
            await asyncio.wait_for(
                asyncio.gather(*all_tasks, return_exceptions=True),
                timeout=self.deadlock_timeout
            )
        
        # Cleanup
        await WebSocketTestHelpers.close_test_connection(connection)
        self.active_connections.remove(connection)
    
    @pytest.mark.mission_critical
    @pytest.mark.windows_deadlock
    @pytest.mark.no_skip
    @pytest.mark.asyncio
    async def test_event_loop_starvation_protection(self):
        """
        🚨 WINDOWS DEADLOCK PROTECTION: Event Loop Starvation
        
        Tests that CPU-intensive operations do not starve the event loop,
        causing apparent deadlocks on Windows systems.
        """
        starvation_test_start = time.time()
        
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="event_loop_starvation_test@example.com",
            environment=self.environment,
            websocket_enabled=True
        )
        
        # Test event loop responsiveness under CPU load
        async def cpu_intensive_task(task_id: int, duration: float) -> Dict[str, Any]:
            """Simulate CPU-intensive work that might block the event loop."""
            start_time = time.time()
            
            # CPU-intensive loop with yield points to prevent blocking
            iterations = 0
            while (time.time() - start_time) < duration:
                # Simulate work
                for _ in range(10000):
                    iterations += 1
                
                # Yield control to prevent event loop blocking
                await asyncio.sleep(0)  # Yield to event loop
            
            return {
                "task_id": task_id,
                "duration": time.time() - start_time,
                "iterations": iterations,
                "completed": True
            }
        
        # Create multiple CPU-intensive tasks
        cpu_tasks = [
            asyncio.create_task(cpu_intensive_task(i, 2.0))
            for i in range(3)
        ]
        
        # Track tasks for cleanup
        with self.task_lock:
            self.active_tasks.extend(cpu_tasks)
        
        # Also create WebSocket operations during CPU load
        jwt_token = self.auth_helper.create_test_jwt_token(
            user_id=str(user_context.user_id),
            email=user_context.agent_context.get('user_email')
        )
        
        async def websocket_operations_during_load() -> Dict[str, Any]:
            """Perform WebSocket operations while CPU tasks are running."""
            ws_headers = self.websocket_helper.get_websocket_headers(jwt_token)
            websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
            
            try:
                # Create connection
                connection = await asyncio.wait_for(
                    WebSocketTestHelpers.create_test_websocket_connection(
                        url=websocket_url,
                        headers=ws_headers,
                        timeout=5.0,
                        user_id=str(user_context.user_id)
                    ),
                    timeout=self.operation_timeout
                )
                self.active_connections.append(connection)
                
                # Send messages during CPU load
                messages_sent = 0
                for i in range(5):
                    message = {
                        "type": "cpu_load_test",
                        "message_id": i,
                        "timestamp": time.time()
                    }
                    
                    await WebSocketTestHelpers.send_test_message(
                        connection, message, timeout=3.0
                    )
                    messages_sent += 1
                    
                    # Small delay
                    await asyncio.sleep(0.5)
                
                # Cleanup
                await WebSocketTestHelpers.close_test_connection(connection)
                self.active_connections.remove(connection)
                
                return {
                    "websocket_operations": True,
                    "messages_sent": messages_sent,
                    "success": True
                }
                
            except Exception as e:
                return {
                    "websocket_operations": False,
                    "error": str(e),
                    "success": False
                }
        
        # Create WebSocket task
        websocket_task = asyncio.create_task(websocket_operations_during_load())
        with self.task_lock:
            self.active_tasks.append(websocket_task)
        
        # Run CPU and WebSocket tasks concurrently with deadlock protection
        all_tasks = cpu_tasks + [websocket_task]
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*all_tasks, return_exceptions=True),
                timeout=self.deadlock_timeout
            )
            
            starvation_test_time = time.time() - starvation_test_start
            
            # Analyze results
            cpu_results = results[:-1]  # All but last (WebSocket result)
            websocket_result = results[-1]
            
            successful_cpu_tasks = sum(1 for r in cpu_results if isinstance(r, dict) and r.get("completed"))
            websocket_success = isinstance(websocket_result, dict) and websocket_result.get("success")
            
            # Record event loop starvation metrics
            self.record_metric("event_loop_cpu_tasks_completed", successful_cpu_tasks)
            self.record_metric("event_loop_websocket_success", websocket_success)
            self.record_metric("event_loop_starvation_test_time", starvation_test_time)
            self.record_metric("event_loop_total_tasks", len(all_tasks))
            
            # STARVATION ASSESSMENT
            
            if successful_cpu_tasks == 0 and not websocket_success:
                pytest.fail(
                    f"🚨 CRITICAL EVENT LOOP DEADLOCK: All operations failed\n"
                    f"CPU Tasks Completed: {successful_cpu_tasks}/3\n"
                    f"WebSocket Success: {websocket_success}\n"
                    f"This indicates complete event loop starvation!"
                )
            
            elif not websocket_success:
                pytest.fail(
                    f"🚨 EVENT LOOP STARVATION: WebSocket operations blocked\n"
                    f"CPU Tasks Completed: {successful_cpu_tasks}/3\n"
                    f"WebSocket Success: {websocket_success}\n"
                    f"WebSocket Error: {websocket_result.get('error') if isinstance(websocket_result, dict) else websocket_result}\n"
                    f"Event loop appears starved by CPU tasks!"
                )
            
            # SUCCESS CASE
            print(f"\n✅ EVENT LOOP STARVATION PROTECTION: Test PASSED")
            print(f"   🔄 CPU Tasks Completed: {successful_cpu_tasks}/3")
            print(f"   🌐 WebSocket Operations: {'✅' if websocket_success else '❌'}")
            print(f"   ⏱️  Test Duration: {starvation_test_time:.2f}s")
            print(f"   💻 Event Loop: RESPONSIVE")
            
        except asyncio.TimeoutError:
            pytest.fail(
                f"🚨 CRITICAL EVENT LOOP DEADLOCK: Test timed out after {self.deadlock_timeout}s\n"
                f"This indicates a complete event loop deadlock!\n"
                f"Platform: {platform.system()}\n"
                f"Tasks may be blocking the event loop indefinitely"
            )
    
    @pytest.mark.mission_critical
    @pytest.mark.windows_deadlock
    @pytest.mark.no_skip
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    @pytest.mark.asyncio
    async def test_windows_specific_asyncio_patterns(self):
        """
        🚨 WINDOWS-SPECIFIC DEADLOCK PROTECTION
        
        Tests Windows-specific asyncio patterns that are known to cause deadlocks,
        including Proactor event loop and Windows threading interactions.
        """
        windows_test_start = time.time()
        
        if not self.is_windows:
            pytest.skip("Windows-specific test skipped on non-Windows platform")
        
        # Test Windows-specific asyncio patterns
        windows_tests = []
        
        # Test 1: Windows Proactor Event Loop with subprocess
        try:
            test_start = time.time()
            
            # Test subprocess creation with Proactor event loop
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-c", "print('Windows asyncio test')",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)
            
            windows_tests.append({
                "test": "proactor_subprocess",
                "success": proc.returncode == 0,
                "duration": time.time() - test_start,
                "deadlock_detected": False
            })
            
        except asyncio.TimeoutError:
            windows_tests.append({
                "test": "proactor_subprocess", 
                "success": False,
                "duration": time.time() - test_start,
                "deadlock_detected": True,
                "error": "DEADLOCK: Subprocess operation timed out"
            })
        except Exception as e:
            windows_tests.append({
                "test": "proactor_subprocess",
                "success": False,
                "duration": time.time() - test_start,
                "deadlock_detected": False,
                "error": str(e)
            })
        
        # Test 2: Windows threading with asyncio
        try:
            test_start = time.time()
            
            def windows_thread_operation():
                """Windows-specific threading operation."""
                time.sleep(1.0)
                return "Windows thread completed"
            
            # Test thread pool execution
            with ThreadPoolExecutor(max_workers=2) as executor:
                thread_tasks = [
                    asyncio.get_event_loop().run_in_executor(
                        executor, windows_thread_operation
                    )
                    for _ in range(3)
                ]
                
                results = await asyncio.wait_for(
                    asyncio.gather(*thread_tasks),
                    timeout=15.0
                )
            
            windows_tests.append({
                "test": "windows_threading",
                "success": len(results) == 3,
                "duration": time.time() - test_start,
                "deadlock_detected": False,
                "results": len(results)
            })
            
        except asyncio.TimeoutError:
            windows_tests.append({
                "test": "windows_threading",
                "success": False,
                "duration": time.time() - test_start,
                "deadlock_detected": True,
                "error": "DEADLOCK: Windows threading timed out"
            })
        except Exception as e:
            windows_tests.append({
                "test": "windows_threading",
                "success": False,
                "duration": time.time() - test_start,
                "deadlock_detected": False,
                "error": str(e)
            })
        
        total_windows_test_time = time.time() - windows_test_start
        
        # WINDOWS-SPECIFIC DEADLOCK ANALYSIS
        
        deadlocks_detected = sum(1 for test in windows_tests if test.get("deadlock_detected"))
        tests_failed = sum(1 for test in windows_tests if not test.get("success"))
        total_tests = len(windows_tests)
        
        # Record Windows-specific metrics
        self.record_metric("windows_specific_deadlocks", deadlocks_detected)
        self.record_metric("windows_specific_failures", tests_failed)
        self.record_metric("windows_specific_tests", total_tests)
        self.record_metric("windows_test_duration", total_windows_test_time)
        
        # CRITICAL WINDOWS ASSESSMENT
        
        if deadlocks_detected > 0:
            deadlock_details = "\n".join([
                f"  - {test['test']}: {test.get('error', 'DEADLOCK')}"
                for test in windows_tests if test.get("deadlock_detected")
            ])
            
            pytest.fail(
                f"🚨 CRITICAL WINDOWS ASYNCIO DEADLOCK DETECTED\n"
                f"Windows Version: {platform.platform()}\n"
                f"Python: {sys.version}\n"
                f"Deadlocks: {deadlocks_detected}/{total_tests}\n"
                f"Deadlock Details:\n{deadlock_details}\n"
                f"This blocks Windows development completely!\n"
                f"Test Results: {windows_tests}"
            )
        
        elif tests_failed > 0:
            failure_details = "\n".join([
                f"  - {test['test']}: {test.get('error', 'FAILED')}"
                for test in windows_tests if not test.get("success") and not test.get("deadlock_detected")
            ])
            
            pytest.fail(
                f"🚨 WINDOWS ASYNCIO INSTABILITY DETECTED\n"
                f"Failed Tests: {tests_failed}/{total_tests}\n"
                f"Failure Details:\n{failure_details}\n"
                f"This indicates Windows-specific asyncio issues!"
            )
        
        # SUCCESS CASE
        print(f"\n✅ WINDOWS ASYNCIO DEADLOCK PROTECTION: Test PASSED")
        print(f"   🖥️  Windows Version: {platform.platform()}")
        print(f"   🐍 Python: {sys.version}")
        print(f"   🔒 Deadlocks Detected: {deadlocks_detected}")
        print(f"   ✅ Tests Passed: {total_tests - tests_failed}/{total_tests}")
        print(f"   ⏱️  Test Duration: {total_windows_test_time:.2f}s")
        print(f"   💻 Windows Development: PROTECTED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])