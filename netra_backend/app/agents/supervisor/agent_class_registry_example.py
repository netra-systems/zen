"""
Example usage of AgentClassRegistry.

This file demonstrates the proper usage patterns for the AgentClassRegistry
during application startup and runtime operations.

CRITICAL: This example shows the correct lifecycle:
1. Registration phase (startup only)
2. Freeze phase (startup completion)
3. Runtime phase (concurrent access, read-only)
"""

import asyncio
from typing import Dict, Any
from netra_backend.app.agents.supervisor.agent_class_registry import (
    get_agent_class_registry,
    create_test_registry
)
from netra_backend.app.agents.supervisor.agent_class_initialization import (
    initialize_agent_class_registry,
    get_agent_types_summary,
    list_available_agents
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def demonstrate_startup_phase():
    """Demonstrate the startup registration phase."""
    print("=== STARTUP PHASE: Agent Class Registration ===")
    
    # Create a test registry (in real app, use get_agent_class_registry())
    registry = create_test_registry()
    
    # Import some agents for demonstration
    from netra_backend.app.agents.base_agent import BaseAgent
    
    class DemoAgent(BaseAgent):
        def __init__(self, name="DemoAgent"):
            super().__init__(name=name)
            
        async def execute_core_logic(self, context) -> Dict[str, Any]:
            return {"status": "demo_completed"}
    
    # Register agent classes during startup
    try:
        registry.register(
            "demo_agent", 
            DemoAgent, 
            "Demonstration agent for examples",
            version="1.0.0",
            dependencies=[],
            metadata={"category": "example", "priority": "low"}
        )
        
        registry.register(
            "another_demo", 
            DemoAgent,
            "Another demo agent", 
            version="1.1.0",
            dependencies=["demo_agent"],
            metadata={"category": "example", "priority": "medium"}
        )
        
        print(f" PASS:  Registered {len(registry)} agent classes")
        print(f"   Agent names: {registry.list_agent_names()}")
        
    except Exception as e:
        print(f" FAIL:  Registration failed: {e}")
        return None
    
    return registry


def demonstrate_freeze_phase(registry):
    """Demonstrate the freeze phase (startup completion)."""
    print("\n=== FREEZE PHASE: Making Registry Immutable ===")
    
    print(f"Before freeze: frozen={registry.is_frozen()}")
    
    # Freeze the registry to make it immutable
    registry.freeze()
    
    print(f"After freeze: frozen={registry.is_frozen()}")
    
    # Try to register after freezing (should fail)
    try:
        from netra_backend.app.agents.base_agent import BaseAgent
        
        class PostFreezeAgent(BaseAgent):
            pass
            
        registry.register("post_freeze", PostFreezeAgent, "Should fail")
        print(" FAIL:  Registration after freeze should have failed!")
        
    except RuntimeError as e:
        print(f" PASS:  Correctly prevented post-freeze registration: {e}")


def demonstrate_runtime_phase(registry):
    """Demonstrate runtime operations (read-only, thread-safe)."""
    print("\n=== RUNTIME PHASE: Using Registry for Agent Instantiation ===")
    
    # Get agent class for instantiation
    demo_agent_class = registry.get_agent_class("demo_agent")
    if demo_agent_class:
        print(f" PASS:  Retrieved agent class: {demo_agent_class.__name__}")
        
        # Instantiate the agent (this is what happens at runtime)
        agent_instance = demo_agent_class("runtime_demo_instance")
        print(f" PASS:  Created agent instance: {agent_instance.name}")
    else:
        print(" FAIL:  Failed to retrieve demo_agent class")
    
    # Get agent information
    agent_info = registry.get_agent_info("demo_agent")
    if agent_info:
        print(f" PASS:  Agent info: {agent_info.name} v{agent_info.version}")
        print(f"   Description: {agent_info.description}")
        print(f"   Metadata: {agent_info.metadata}")
    
    # List all available agents
    all_agents = registry.get_all_agent_classes()
    print(f" PASS:  Available agent classes: {len(all_agents)}")
    
    # Check dependencies
    missing_deps = registry.validate_dependencies()
    if missing_deps:
        print(f" WARNING: [U+FE0F]  Missing dependencies: {missing_deps}")
    else:
        print(" PASS:  All dependencies satisfied")
    
    # Get registry statistics
    stats = registry.get_registry_stats()
    print(f" PASS:  Registry health: {stats['health_status']}")
    print(f"   Total agents: {stats['total_agent_classes']}")


def demonstrate_thread_safety(registry):
    """Demonstrate thread-safe concurrent access."""
    print("\n=== THREAD SAFETY: Concurrent Access Test ===")
    
    import threading
    import time
    
    results = []
    errors = []
    
    def concurrent_access_worker(worker_id: int):
        """Worker function for concurrent access test."""
        try:
            for i in range(10):
                # Perform various read operations
                agent_class = registry.get_agent_class("demo_agent")
                agent_names = registry.list_agent_names()
                has_agent = registry.has_agent_class("another_demo")
                
                results.append({
                    "worker_id": worker_id,
                    "iteration": i,
                    "agent_class": agent_class.__name__ if agent_class else None,
                    "agent_count": len(agent_names),
                    "has_agent": has_agent
                })
                
                time.sleep(0.001)  # Small delay to increase concurrency
                
        except Exception as e:
            errors.append(f"Worker {worker_id}: {e}")
    
    # Start multiple threads
    threads = []
    start_time = time.time()
    
    for worker_id in range(5):
        thread = threading.Thread(target=concurrent_access_worker, args=(worker_id,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    
    if errors:
        print(f" FAIL:  Thread safety test failed with {len(errors)} errors:")
        for error in errors[:3]:  # Show first 3 errors
            print(f"   {error}")
    else:
        print(f" PASS:  Thread safety test passed!")
        print(f"   {len(results)} operations completed by {len(threads)} threads")
        print(f"   Duration: {end_time - start_time:.3f} seconds")
        
        # Verify consistent results
        first_result = results[0]
        inconsistent = False
        for result in results[1:]:
            if (result["agent_class"] != first_result["agent_class"] or
                result["agent_count"] != first_result["agent_count"] or
                result["has_agent"] != first_result["has_agent"]):
                inconsistent = True
                break
        
        if inconsistent:
            print(" FAIL:  Results were inconsistent across threads")
        else:
            print(" PASS:  All thread results were consistent")


def demonstrate_error_handling(registry):
    """Demonstrate error handling scenarios."""
    print("\n=== ERROR HANDLING: Testing Edge Cases ===")
    
    # Test non-existent agent
    nonexistent = registry.get_agent_class("nonexistent_agent")
    if nonexistent is None:
        print(" PASS:  Correctly returned None for non-existent agent")
    else:
        print(" FAIL:  Should return None for non-existent agent")
    
    # Test agent info for non-existent agent
    info = registry.get_agent_info("nonexistent_agent")
    if info is None:
        print(" PASS:  Correctly returned None for non-existent agent info")
    else:
        print(" FAIL:  Should return None for non-existent agent info")
    
    # Test has_agent_class for non-existent agent
    has_agent = registry.has_agent_class("nonexistent_agent")
    if not has_agent:
        print(" PASS:  Correctly returned False for non-existent agent")
    else:
        print(" FAIL:  Should return False for non-existent agent")
    
    # Test 'in' operator
    if "nonexistent_agent" not in registry:
        print(" PASS:  'in' operator works correctly")
    else:
        print(" FAIL:  'in' operator should return False")


async def demonstrate_full_lifecycle():
    """Demonstrate the complete lifecycle of AgentClassRegistry."""
    print("[U+1F680] AgentClassRegistry Demonstration")
    print("="*50)
    
    # Phase 1: Startup Registration
    registry = demonstrate_startup_phase()
    if not registry:
        print(" FAIL:  Startup phase failed, aborting demonstration")
        return
    
    # Phase 2: Freeze (Startup Completion)
    demonstrate_freeze_phase(registry)
    
    # Phase 3: Runtime Operations
    demonstrate_runtime_phase(registry)
    
    # Phase 4: Thread Safety
    demonstrate_thread_safety(registry)
    
    # Phase 5: Error Handling
    demonstrate_error_handling(registry)
    
    print("\n" + "="*50)
    print(" PASS:  AgentClassRegistry demonstration completed successfully!")
    print(f"Final registry state: {registry}")


def demonstrate_real_initialization():
    """Demonstrate initialization with real agent classes."""
    print("\n[U+1F527] Real Agent Initialization Example")
    print("="*40)
    
    try:
        # This would be called during app startup
        # registry = initialize_agent_class_registry()
        
        # For demo, just show what would happen
        print("In a real application, you would call:")
        print("  registry = initialize_agent_class_registry()")
        print("  # This registers all core, specialized, and auxiliary agents")
        
        # Show available functions
        print("\nAvailable utility functions:")
        print("  - list_available_agents() -> List[str]")
        print("  - get_agent_class_by_name(name) -> Optional[Type[BaseAgent]]")
        print("  - is_agent_type_available(name) -> bool")
        print("  - get_agent_types_summary() -> Dict[str, Any]")
        
        print("\n PASS:  Real initialization example completed")
        
    except Exception as e:
        print(f" FAIL:  Real initialization example failed: {e}")


if __name__ == "__main__":
    # Run the complete demonstration
    asyncio.run(demonstrate_full_lifecycle())
    
    # Show real initialization example
    demonstrate_real_initialization()
    
    print("\n TARGET:  Key Takeaways:")
    print("1. Register agent classes ONLY during startup")
    print("2. Freeze registry after registration to make it immutable")
    print("3. Use registry for thread-safe, concurrent agent class retrieval")
    print("4. No per-user state stored in registry - it's infrastructure only")
    print("5. Registry provides complete type safety and validation")