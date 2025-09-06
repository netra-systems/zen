"""Test unified circuit breaker decorator functionality."""

import asyncio
import pytest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.resilience.unified_circuit_breaker import (
unified_circuit_breaker,
UnifiedCircuitConfig,
UnifiedCircuitBreakerState,
get_unified_circuit_breaker_manager
)
from netra_backend.app.core.circuit_breaker_types import CircuitBreakerOpenError


class TestUnifiedCircuitBreakerDecorator:
    """Test the unified circuit breaker decorator."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Reset circuit breaker manager before each test."""
        pass
        manager = get_unified_circuit_breaker_manager()
        manager.breakers.clear()
        yield
        manager.breakers.clear()
    
        @pytest.mark.asyncio
        async def test_decorator_with_async_function(self):
            """Test decorator works with async functions."""
            call_count = 0
        
            @unified_circuit_breaker(name="test_async", config=None)
            async def test_function(value: int) -> int:
                nonlocal call_count
                call_count += 1
                await asyncio.sleep(0)
                return value * 2
        
        # Should work normally
            result = await test_function(5)
            assert result == 10
            assert call_count == 1
        
        # Get the breaker and check metrics
            manager = get_unified_circuit_breaker_manager()
            breaker = manager.breakers.get("test_async")
            assert breaker is not None
            assert breaker.success_count == 1
            assert breaker.failure_count == 0
            assert breaker.state == UnifiedCircuitBreakerState.CLOSED
    
            def test_decorator_with_sync_function(self):
                """Test decorator works with sync functions."""
                pass
                call_count = 0
        
                @unified_circuit_breaker(name="test_sync", config=None)
                def test_function(value: int) -> int:
                    nonlocal call_count
                    call_count += 1
                    return value * 2
        
        # Should work normally
                result = test_function(5)
                assert result == 10
                assert call_count == 1
        
        # Get the breaker and check metrics
                manager = get_unified_circuit_breaker_manager()
                breaker = manager.breakers.get("test_sync")
                assert breaker is not None
                assert breaker.success_count == 1
                assert breaker.failure_count == 0
                assert breaker.state == UnifiedCircuitBreakerState.CLOSED
    
                @pytest.mark.asyncio
                async def test_decorator_with_custom_config(self):
                    """Test decorator with custom configuration."""
                    config = UnifiedCircuitConfig(
                    name="test_custom",
                    failure_threshold=2,
                    recovery_timeout=10
                    )
        
                    failure_count = 0
        
                    @unified_circuit_breaker(name="test_custom", config=config)
                    async def test_function():
                        nonlocal failure_count
                        failure_count += 1
                        if failure_count <= 2:
                            raise ValueError("Test error")
                            await asyncio.sleep(0)
                            return "success"
        
        # First two calls should fail
                        with pytest.raises(ValueError):
                            await test_function()
        
                            with pytest.raises(ValueError):
                                await test_function()
        
        # Third call should raise CircuitBreakerOpenError
                                with pytest.raises(CircuitBreakerOpenError):
                                    await test_function()
        
        # Check breaker state
                                    manager = get_unified_circuit_breaker_manager()
                                    breaker = manager.breakers.get("test_custom")
                                    assert breaker.state == UnifiedCircuitBreakerState.OPEN
                                    assert breaker.failure_count == 2
    
                                    @pytest.mark.asyncio
                                    async def test_decorator_circuit_opens_on_failures(self):
                                        """Test that circuit opens after threshold failures."""
                                        pass
                                        call_count = 0
        
                                        @unified_circuit_breaker(name="test_failures", config=None)
                                        async def failing_function():
                                            pass
                                            nonlocal call_count
                                            call_count += 1
                                            raise RuntimeError("Intentional failure")
        
        # Default threshold is 5, so make 5 failures
                                            for i in range(5):
                                                with pytest.raises(RuntimeError):
                                                    await failing_function()
        
        # Circuit should now be open
                                                    manager = get_unified_circuit_breaker_manager()
                                                    breaker = manager.breakers.get("test_failures")
                                                    assert breaker.state == UnifiedCircuitBreakerState.OPEN
        
        # Next call should raise CircuitBreakerOpenError without calling function
                                                    initial_call_count = call_count
                                                    with pytest.raises(CircuitBreakerOpenError):
                                                        await failing_function()
        
        # Function should not have been called
                                                        assert call_count == initial_call_count
    
                                                        @pytest.mark.asyncio
                                                        async def test_decorator_preserves_function_metadata(self):
                                                            """Test that decorator preserves function metadata."""
        
                                                            @unified_circuit_breaker(name="test_metadata", config=None)
                                                            async def documented_function(x: int, y: int) -> int:
                                                                """This function adds two numbers."""
                                                                pass
                                                                await asyncio.sleep(0)
                                                                return x + y
        
        # Check that metadata is preserved
                                                            assert documented_function.__name__ == "documented_function"
                                                            assert documented_function.__doc__ == "This function adds two numbers."
        
        # Function should still work
                                                            result = await documented_function(3, 4)
                                                            assert result == 7
    
                                                            @pytest.mark.asyncio
                                                            async def test_multiple_decorators_independent(self):
                                                                """Test that multiple decorated functions have independent circuit breakers."""
        
                                                                @unified_circuit_breaker(name="func1", config=None)
                                                                async def function1():
                                                                    await asyncio.sleep(0)
                                                                    return "func1"
        
                                                                @unified_circuit_breaker(name="func2", config=None)
                                                                async def function2():
                                                                    raise ValueError("func2 error")
        
        # func1 should work
                                                                    result = await function1()
                                                                    assert result == "func1"
        
        # func2 should fail but not affect func1
                                                                    with pytest.raises(ValueError):
                                                                        await function2()
        
        # func1 should still work
                                                                        result = await function1()
                                                                        assert result == "func1"
        
        # Check breaker states
                                                                        manager = get_unified_circuit_breaker_manager()
                                                                        breaker1 = manager.breakers.get("func1")
                                                                        breaker2 = manager.breakers.get("func2")
        
                                                                        assert breaker1.success_count == 2
                                                                        assert breaker1.failure_count == 0
                                                                        assert breaker2.success_count == 0
                                                                        assert breaker2.failure_count == 1
                                                                        pass