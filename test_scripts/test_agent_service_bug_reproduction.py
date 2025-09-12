"""
Test to reproduce agent_service AttributeError bug.
This test demonstrates the failure when app.state.agent_service is not initialized.
"""
import pytest
import asyncio
from fastapi import FastAPI, Request
from starlette.datastructures import State
from shared.isolated_environment import IsolatedEnvironment


def test_agent_service_missing_attribute_error():
    """Test that reproduces the AttributeError when agent_service is missing."""
    
    # Create a mock FastAPI app with state
    app = FastAPI()
    app.state = State()
    
    # Create a mock request that references the app
    request = Mock(spec=Request)
    request.app = app
    
    # Simulate the scenario where agent_service was never set
    # (This happens when startup fails before _setup_agent_state)
    
    # Try to access agent_service as the dependency function does
    from netra_backend.app.dependencies import get_agent_service
    
    # This should raise AttributeError
    with pytest.raises(AttributeError) as exc_info:
        service = get_agent_service(request)
    
    # Verify the error message
    assert "'State' object has no attribute 'agent_service'" in str(exc_info.value)
    print(f"[U+2713] Successfully reproduced bug: {exc_info.value}")


def test_agent_service_with_proper_initialization():
    """Test that agent_service works when properly initialized."""
    
    # Create a mock FastAPI app with state
    app = FastAPI()
    app.state = State()
    
    # Properly initialize agent_service (as should happen in startup)
    mock_agent_service = Mock()
    app.state.agent_service = mock_agent_service
    
    # Create a mock request
    request = Mock(spec=Request)
    request.app = app
    
    # Access agent_service
    from netra_backend.app.dependencies import get_agent_service
    
    service = get_agent_service(request)
    
    # Should return the mock service without error
    assert service == mock_agent_service
    print("[U+2713] Agent service accessible when properly initialized")


def test_startup_sequence_validation():
    """Test that validates critical services are initialized during startup."""
    
    app = FastAPI()
    app.state = State()
    
    # Simulate partial startup (some services initialized, others not)
    app.state.llm_manager = Mock()  # Initialized
    app.state.agent_supervisor = Mock()  # Initialized
    # app.state.agent_service is NOT initialized (simulating the bug)
    
    # Check for missing critical services
    critical_services = [
        'agent_service',
        'thread_service', 
        'corpus_service',
        'agent_supervisor'
    ]
    
    missing_services = []
    for service_name in critical_services:
        if not hasattr(app.state, service_name):
            missing_services.append(service_name)
    
    # This test should find agent_service is missing
    assert 'agent_service' in missing_services
    print(f"[U+2713] Detected missing critical services: {missing_services}")
    
    # In a proper startup, this should cause startup failure
    if missing_services:
        error_msg = f"CRITICAL: Startup incomplete - missing services: {missing_services}"
        print(f"[U+2717] {error_msg}")
        # In real code, this would raise DeterministicStartupError


async def test_graceful_vs_deterministic_startup():
    """Test demonstrating the difference between graceful and deterministic startup."""
    
    # Graceful startup (current bug scenario)
    print("\n=== GRACEFUL STARTUP (BUG SCENARIO) ===")
    app_graceful = FastAPI()
    app_graceful.state = State()
    
    try:
        # Simulate early startup failure
        raise Exception("Database connection failed")
    except Exception as e:
        # Graceful mode: log and continue
        print(f" WARNING:  Warning: {e} - continuing in graceful mode")
        # Agent service never gets initialized
        pass
    
    # App starts without agent_service
    assert not hasattr(app_graceful.state, 'agent_service')
    print("[U+2717] App started in degraded state without agent_service")
    
    # Deterministic startup (proper behavior)
    print("\n=== DETERMINISTIC STARTUP (CORRECT) ===")
    app_deterministic = FastAPI()
    app_deterministic.state = State()
    
    class DeterministicStartupError(Exception):
        pass
    
    with pytest.raises(DeterministicStartupError):
        try:
            # Simulate early startup failure
            raise Exception("Database connection failed")
        except Exception as e:
            # Deterministic mode: fail immediately
            print(f"[U+2717] Critical failure: {e}")
            raise DeterministicStartupError(f"STARTUP HALTED: {e}")
    
    print("[U+2713] App startup correctly halted on critical failure")


if __name__ == "__main__":
    print("Running agent_service bug reproduction tests...\n")
    
    # Run synchronous tests
    test_agent_service_missing_attribute_error()
    test_agent_service_with_proper_initialization()
    test_startup_sequence_validation()
    
    # Run async test
    asyncio.run(test_graceful_vs_deterministic_startup())
    
    print("\n PASS:  All bug reproduction tests completed!")
    print("\nSUMMARY: The bug occurs when startup fails before agent_service initialization")
    print("but the app continues running in 'graceful' mode, causing runtime AttributeError.")