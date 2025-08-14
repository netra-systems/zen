"""
WebSocketManager Singleton Pattern Tests
Tests singleton pattern implementation, thread safety, and initialization
"""

import pytest
import threading
import time
from app.ws_manager import WebSocketManager


class TestSingletonPattern:
    """Test singleton pattern implementation"""
    
    def test_singleton_instance(self):
        """Test singleton pattern creates same instance"""
        WebSocketManager._instance = None
        
        mgr1 = WebSocketManager()
        mgr2 = WebSocketManager()
        
        assert mgr1 is mgr2, "Should return same instance"
        assert id(mgr1) == id(mgr2), "Should have same memory address"
    
    def test_thread_safety(self):
        """Test singleton pattern is thread-safe"""
        WebSocketManager._instance = None
        instances = []
        
        def create_manager():
            mgr = WebSocketManager()
            instances.append(mgr)
            time.sleep(0.1)  # Simulate some work
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_manager)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All instances should be the same
        first_instance = instances[0]
        for instance in instances:
            assert instance is first_instance, "All instances should be the same"
    
    def test_initialization_only_once(self):
        """Test manager is only initialized once"""
        WebSocketManager._instance = None
        WebSocketManager._initialized = False
        
        mgr1 = WebSocketManager()
        initial_connections = len(mgr1.active_connections)
        
        # Add a connection to verify state persistence
        mgr1.active_connections["test_user"] = []
        
        mgr2 = WebSocketManager()
        
        # Should be same instance with preserved state
        assert mgr1 is mgr2
        assert "test_user" in mgr2.active_connections
        assert len(mgr2.active_connections) == len(mgr1.active_connections)