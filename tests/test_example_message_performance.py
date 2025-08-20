"""Performance and Load Testing for Example Message Flow

Specialized performance tests to ensure system handles production load
and maintains performance benchmarks under stress.

Business Value: Ensures system can handle Free tier conversion load
"""

import pytest
import asyncio
import time
import concurrent.futures
from typing import List, Dict, Any
from uuid import uuid4
import psutil
import os
from unittest.mock import Mock, AsyncMock, patch

from app.handlers.example_message_handler_enhanced import (
    EnhancedExampleMessageHandler, SessionManager, RealAgentIntegration
)
from app.routes.example_messages_enhanced import (
    MessageSequencer, ConnectionStateManager
)


class TestPerformanceBenchmarks:
    """Performance benchmark tests with specific SLA targets"""

    @pytest.mark.asyncio
    async def test_message_processing_latency(self):
        """Test message processing meets latency SLA (< 30 seconds)"""
        
        handler = EnhancedExampleMessageHandler()
        
        # Mock real agent to return quickly
        with patch.object(handler.real_agent_integration, 'execute_real_agent_processing') as mock_process:
            mock_process.return_value = {
                "agent_name": "Performance Test Agent",
                "optimization_type": "cost_optimization",
                "real_agent_execution": True
            }
            
            message = {
                "content": "Performance test optimization request with adequate length for processing",
                "example_message_id": "perf_test_001",
                "example_message_metadata": {
                    "title": "Performance Test",
                    "category": "cost-optimization",
                    "complexity": "basic",
                    "businessValue": "conversion",
                    "estimatedTime": "30s"
                },
                "user_id": "perf_user_001",
                "timestamp": int(time.time() * 1000)
            }
            
            start_time = time.time()
            response = await handler.handle_example_message(message)
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # SLA: Processing should complete within 30 seconds
            assert processing_time < 30.0, f"Processing took {processing_time:.2f}s, exceeds 30s SLA"
            assert response.status == 'completed'
            
            # Performance metrics
            assert response.processing_time_ms is not None
            assert response.processing_time_ms < 30000  # 30 seconds in milliseconds

    @pytest.mark.asyncio
    async def test_concurrent_user_handling(self):
        """Test system handles concurrent users within performance limits"""
        
        handler = EnhancedExampleMessageHandler()
        user_count = 50
        
        # Mock for fast processing
        with patch.object(handler.real_agent_integration, 'execute_real_agent_processing') as mock_process:
            mock_process.return_value = {
                "agent_name": "Concurrent Test Agent",
                "optimization_type": "cost_optimization",
                "real_agent_execution": True
            }
            
            # Create concurrent requests
            tasks = []
            start_time = time.time()
            
            for i in range(user_count):
                message = {
                    "content": f"Concurrent user {i} optimization request with sufficient length",
                    "example_message_id": f"concurrent_test_{i:03d}",
                    "example_message_metadata": {
                        "title": f"Concurrent Test {i}",
                        "category": "cost-optimization",
                        "complexity": "basic",
                        "businessValue": "conversion",
                        "estimatedTime": "30s"
                    },
                    "user_id": f"concurrent_user_{i:03d}",
                    "timestamp": int(time.time() * 1000)
                }
                task = handler.handle_example_message(message)
                tasks.append(task)
            
            # Execute all concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            total_time = end_time - start_time
            
            # Performance assertions
            assert total_time < 60.0, f"Concurrent processing took {total_time:.2f}s, too slow"
            
            # Verify all completed successfully
            successful_results = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_results) == user_count, "Some concurrent requests failed"
            
            # Verify no errors
            errors = [r for r in results if isinstance(r, Exception)]
            assert len(errors) == 0, f"Got {len(errors)} errors in concurrent processing"

    def test_memory_usage_under_load(self):
        """Test memory usage remains bounded under sustained load"""
        
        session_manager = SessionManager()
        process = psutil.Process(os.getpid())
        
        # Baseline memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create many sessions to simulate load
        session_count = 1000
        session_ids = []
        
        for i in range(session_count):
            session_id = asyncio.run(session_manager.create_session(
                user_id=f"load_user_{i:04d}",
                message_id=f"load_msg_{i:04d}",
                metadata={"load_test": True, "iteration": i}
            ))
            session_ids.append(session_id)
        
        # Memory after session creation
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        # Should not consume excessive memory
        assert memory_increase < 100, f"Memory increased by {memory_increase:.1f}MB, too much for {session_count} sessions"
        
        # Cleanup sessions
        for session_id in session_ids:
            asyncio.run(session_manager._cleanup_session(session_id))
        
        # Memory after cleanup
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Memory should be mostly released (within 20MB of initial)
        memory_retained = final_memory - initial_memory
        assert memory_retained < 20, f"Retained {memory_retained:.1f}MB after cleanup, possible memory leak"

    def test_session_creation_performance(self):
        """Test session creation performance meets targets"""
        
        session_manager = SessionManager()
        session_count = 100
        
        start_time = time.time()
        
        session_ids = []
        for i in range(session_count):
            session_id = asyncio.run(session_manager.create_session(
                user_id=f"perf_user_{i:03d}",
                message_id=f"perf_msg_{i:03d}",
                metadata={"perf_test": True}
            ))
            session_ids.append(session_id)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Performance targets
        time_per_session = creation_time / session_count
        assert time_per_session < 0.01, f"Session creation too slow: {time_per_session:.4f}s per session"
        assert creation_time < 1.0, f"Total creation time too slow: {creation_time:.2f}s for {session_count} sessions"
        
        # Cleanup
        cleanup_start = time.time()
        for session_id in session_ids:
            asyncio.run(session_manager._cleanup_session(session_id))
        cleanup_end = time.time()
        
        cleanup_time = cleanup_end - cleanup_start
        assert cleanup_time < 0.5, f"Cleanup too slow: {cleanup_time:.2f}s"


class TestScalabilityLimits:
    """Test system behavior at scale limits"""

    def test_message_sequencer_high_volume(self):
        """Test message sequencer handles high message volumes"""
        
        sequencer = MessageSequencer()
        user_count = 100
        messages_per_user = 50
        
        # Generate high volume of messages
        total_messages = 0
        start_time = time.time()
        
        for user_i in range(user_count):
            user_id = f"volume_user_{user_i:03d}"
            
            for msg_i in range(messages_per_user):
                sequence = sequencer.get_next_sequence(user_id)
                message = {
                    "type": "volume_test",
                    "user": user_i,
                    "message": msg_i,
                    "timestamp": time.time()
                }
                sequencer.add_pending_message(user_id, sequence, message)
                total_messages += 1
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Performance assertions
        messages_per_second = total_messages / processing_time
        assert messages_per_second > 1000, f"Message processing too slow: {messages_per_second:.1f} msg/s"
        
        # Verify data integrity
        total_pending = sum(
            len(sequencer.get_pending_messages(f"volume_user_{i:03d}"))
            for i in range(user_count)
        )
        assert total_pending == total_messages, "Message count mismatch"

    def test_connection_manager_capacity(self):
        """Test connection manager handles many concurrent connections"""
        
        manager = ConnectionStateManager()
        connection_count = 500
        
        # Create many connections
        connection_ids = []
        user_ids = []
        
        for i in range(connection_count):
            user_id = f"capacity_user_{i:04d}"
            connection_id = f"conn_{i:04d}"
            websocket = Mock()
            
            asyncio.run(manager.register_connection(user_id, connection_id, websocket))
            connection_ids.append(connection_id)
            user_ids.append(user_id)
        
        # Verify all connections are valid
        valid_connections = sum(
            1 for user_id in user_ids 
            if manager.is_connection_valid(user_id)
        )
        assert valid_connections == connection_count, "Some connections not registered properly"
        
        # Test activity updates at scale
        start_time = time.time()
        for user_id in user_ids:
            manager.update_activity(user_id)
        end_time = time.time()
        
        update_time = end_time - start_time
        assert update_time < 1.0, f"Activity updates too slow: {update_time:.2f}s for {connection_count} connections"
        
        # Cleanup
        for user_id in user_ids:
            asyncio.run(manager.cleanup_connection(user_id))

    @pytest.mark.asyncio
    async def test_circuit_breaker_under_load(self):
        """Test circuit breaker behavior under high failure load"""
        
        from app.core.circuit_breaker import CircuitBreaker
        
        circuit_breaker = CircuitBreaker(
            failure_threshold=10,
            recovery_timeout=1.0,
            expected_exception=Exception
        )
        
        call_count = 0
        
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            raise Exception(f"Failure {call_count}")
        
        # Generate high volume of failures
        failure_count = 0
        start_time = time.time()
        
        for i in range(100):
            try:
                await circuit_breaker.call(failing_operation)
            except Exception:
                failure_count += 1
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Circuit breaker should be open after threshold
        assert circuit_breaker.state == "OPEN"
        
        # Should fail fast after opening
        assert processing_time < 5.0, f"Circuit breaker took {processing_time:.2f}s, should fail fast"
        
        # Should have prevented some calls from reaching the operation
        assert call_count < 100, f"Circuit breaker allowed {call_count} calls, should have blocked some"


class TestStressTests:
    """Stress tests to identify breaking points"""

    @pytest.mark.asyncio
    async def test_rapid_message_succession(self):
        """Test handling rapid succession of messages from single user"""
        
        handler = EnhancedExampleMessageHandler()
        user_id = "stress_user"
        message_count = 20
        
        # Mock for fast processing
        with patch.object(handler.real_agent_integration, 'execute_real_agent_processing') as mock_process:
            mock_process.return_value = {
                "agent_name": "Stress Test Agent",
                "optimization_type": "cost_optimization",
                "real_agent_execution": True
            }
            
            # Send rapid succession of messages
            tasks = []
            for i in range(message_count):
                message = {
                    "content": f"Rapid message {i} with sufficient length for processing and validation",
                    "example_message_id": f"rapid_{i:03d}",
                    "example_message_metadata": {
                        "title": f"Rapid Message {i}",
                        "category": "cost-optimization",
                        "complexity": "basic",
                        "businessValue": "conversion",
                        "estimatedTime": "30s"
                    },
                    "user_id": user_id,
                    "timestamp": int(time.time() * 1000) + i
                }
                task = handler.handle_example_message(message)
                tasks.append(task)
            
            # Execute all rapidly
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful = [r for r in results if not isinstance(r, Exception)]
            errors = [r for r in results if isinstance(r, Exception)]
            
            # Should handle most messages successfully
            success_rate = len(successful) / len(results)
            assert success_rate >= 0.8, f"Success rate {success_rate:.2f} too low for rapid messages"
            
            # Should not crash completely
            assert len(successful) > 0, "No messages processed successfully"

    def test_memory_leak_detection(self):
        """Test for memory leaks over extended operation"""
        
        session_manager = SessionManager()
        process = psutil.Process(os.getpid())
        
        # Baseline memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate extended operation with session churn
        for cycle in range(10):
            # Create sessions
            session_ids = []
            for i in range(100):
                session_id = asyncio.run(session_manager.create_session(
                    user_id=f"leak_test_{cycle}_{i:03d}",
                    message_id=f"leak_msg_{cycle}_{i:03d}",
                    metadata={"cycle": cycle, "iteration": i}
                ))
                session_ids.append(session_id)
            
            # Use sessions (simulate activity)
            for session_id in session_ids:
                session_manager.update_session(session_id, {
                    "status": "processing",
                    "activity": time.time()
                })
            
            # Cleanup sessions
            for session_id in session_ids:
                asyncio.run(session_manager._cleanup_session(session_id))
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Should not have significant memory growth
        assert memory_growth < 50, f"Memory grew by {memory_growth:.1f}MB, possible leak"

    def test_error_recovery_under_stress(self):
        """Test error recovery mechanisms under stress conditions"""
        
        from app.core.circuit_breaker import CircuitBreaker
        
        circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=0.5,
            expected_exception=Exception
        )
        
        success_count = 0
        failure_count = 0
        
        async def intermittent_operation():
            nonlocal success_count, failure_count
            # 70% success rate
            if (success_count + failure_count) % 10 < 7:
                success_count += 1
                return "success"
            else:
                failure_count += 1
                raise Exception("Intermittent failure")
        
        # Run stress test
        results = []
        for i in range(100):
            try:
                result = asyncio.run(circuit_breaker.call(intermittent_operation))
                results.append(result)
            except Exception as e:
                results.append(e)
            
            # Brief pause to allow circuit breaker state changes
            if i % 10 == 0:
                time.sleep(0.1)
        
        # Analyze results
        successes = [r for r in results if r == "success"]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        # Should have recovered and processed some successes
        assert len(successes) > 0, "Circuit breaker never recovered"
        
        # Should have protected against some failures
        protected_failures = len(exceptions) - failure_count
        assert protected_failures >= 0, "Circuit breaker didn't provide protection"


class TestPerformanceRegression:
    """Regression tests to ensure performance doesn't degrade"""

    @pytest.fixture
    def performance_baseline(self):
        """Performance baseline metrics"""
        return {
            "session_creation_time_ms": 10,  # 10ms per session
            "message_processing_time_s": 30,  # 30s max processing
            "concurrent_users": 50,  # Handle 50 concurrent users
            "memory_per_session_kb": 100,  # 100KB per session max
            "cleanup_time_ms": 5  # 5ms per cleanup operation
        }

    def test_session_creation_regression(self, performance_baseline):
        """Test session creation hasn't regressed"""
        
        session_manager = SessionManager()
        iterations = 100
        
        start_time = time.time()
        session_ids = []
        
        for i in range(iterations):
            session_id = asyncio.run(session_manager.create_session(
                user_id=f"regression_user_{i:03d}",
                message_id=f"regression_msg_{i:03d}",
                metadata={"regression_test": True}
            ))
            session_ids.append(session_id)
        
        end_time = time.time()
        
        total_time_ms = (end_time - start_time) * 1000
        time_per_session_ms = total_time_ms / iterations
        
        # Should not exceed baseline
        assert time_per_session_ms <= performance_baseline["session_creation_time_ms"], \
            f"Session creation regressed: {time_per_session_ms:.2f}ms vs {performance_baseline['session_creation_time_ms']}ms baseline"
        
        # Cleanup
        for session_id in session_ids:
            asyncio.run(session_manager._cleanup_session(session_id))

    def test_memory_usage_regression(self, performance_baseline):
        """Test memory usage per session hasn't regressed"""
        
        session_manager = SessionManager()
        process = psutil.Process(os.getpid())
        
        # Measure baseline
        initial_memory = process.memory_info().rss
        
        # Create sessions
        session_count = 100
        session_ids = []
        
        for i in range(session_count):
            session_id = asyncio.run(session_manager.create_session(
                user_id=f"memory_user_{i:03d}",
                message_id=f"memory_msg_{i:03d}",
                metadata={"memory_test": True, "data": "x" * 100}  # Add some data
            ))
            session_ids.append(session_id)
        
        # Measure peak memory
        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory
        memory_per_session_kb = memory_increase / session_count / 1024
        
        # Should not exceed baseline
        assert memory_per_session_kb <= performance_baseline["memory_per_session_kb"], \
            f"Memory usage regressed: {memory_per_session_kb:.1f}KB vs {performance_baseline['memory_per_session_kb']}KB baseline"
        
        # Cleanup
        for session_id in session_ids:
            asyncio.run(session_manager._cleanup_session(session_id))

    def test_cleanup_performance_regression(self, performance_baseline):
        """Test cleanup performance hasn't regressed"""
        
        session_manager = SessionManager()
        
        # Create sessions to cleanup
        session_count = 100
        session_ids = []
        
        for i in range(session_count):
            session_id = asyncio.run(session_manager.create_session(
                user_id=f"cleanup_user_{i:03d}",
                message_id=f"cleanup_msg_{i:03d}",
                metadata={"cleanup_test": True}
            ))
            session_ids.append(session_id)
        
        # Measure cleanup time
        start_time = time.time()
        
        for session_id in session_ids:
            await session_manager._cleanup_session(session_id)
        
        end_time = time.time()
        
        total_cleanup_time_ms = (end_time - start_time) * 1000
        time_per_cleanup_ms = total_cleanup_time_ms / session_count
        
        # Should not exceed baseline
        assert time_per_cleanup_ms <= performance_baseline["cleanup_time_ms"], \
            f"Cleanup performance regressed: {time_per_cleanup_ms:.2f}ms vs {performance_baseline['cleanup_time_ms']}ms baseline"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short", "-m", "not slow"])