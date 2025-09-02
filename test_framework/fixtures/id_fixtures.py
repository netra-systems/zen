"""
Test fixtures for valid ID generation - SSOT compliant.

This module provides standardized test fixtures for generating valid
thread_id and run_id pairs that comply with the SSOT patterns.
"""
import pytest
from typing import Tuple
from netra_backend.app.core.id_manager import IDManager, IDPair


class IDFixtures:
    """Centralized test fixtures for ID generation."""
    
    @staticmethod
    def create_valid_ids(thread_id: str = "test_thread") -> Tuple[str, str]:
        """
        Create a valid pair of thread_id and run_id.
        
        Args:
            thread_id: Thread identifier (default: "test_thread")
            
        Returns:
            Tuple of (thread_id, run_id)
        """
        run_id = IDManager.generate_run_id(thread_id)
        return thread_id, run_id
    
    @staticmethod
    def create_id_pair(thread_id: str = "test_thread") -> IDPair:
        """
        Create a validated IDPair for testing.
        
        Args:
            thread_id: Thread identifier (default: "test_thread")
            
        Returns:
            IDPair with validated IDs
        """
        return IDManager.create_test_ids(thread_id)
    
    @staticmethod
    def create_execution_context_ids() -> dict:
        """
        Create IDs suitable for ExecutionContext initialization.
        
        Returns:
            Dict with run_id and thread_id keys
        """
        thread_id, run_id = IDFixtures.create_valid_ids()
        return {
            "run_id": run_id,
            "thread_id": thread_id  # Optional, for backwards compatibility
        }
    
    @staticmethod
    def create_websocket_event_ids() -> dict:
        """
        Create IDs for WebSocket event routing.
        
        Returns:
            Dict with run_id and extracted thread_id
        """
        thread_id = "websocket_thread"
        run_id = IDManager.generate_run_id(thread_id)
        
        return {
            "run_id": run_id,
            "thread_id": thread_id,
            "routing_key": thread_id  # For WebSocket routing
        }
    
    @staticmethod
    def create_agent_execution_ids(agent_name: str = "test_agent") -> dict:
        """
        Create IDs for agent execution.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dict with all required IDs for agent execution
        """
        thread_id = f"{agent_name}_thread"
        run_id = IDManager.generate_run_id(thread_id)
        
        return {
            "run_id": run_id,
            "thread_id": thread_id,
            "agent_name": agent_name
        }


# Pytest fixtures for direct use in tests
@pytest.fixture
def valid_ids():
    """Pytest fixture for valid ID pair."""
    return IDFixtures.create_valid_ids()


@pytest.fixture
def valid_id_pair():
    """Pytest fixture for validated IDPair."""
    return IDFixtures.create_id_pair()


@pytest.fixture
def execution_context_ids():
    """Pytest fixture for ExecutionContext IDs."""
    return IDFixtures.create_execution_context_ids()


@pytest.fixture
def websocket_ids():
    """Pytest fixture for WebSocket event IDs."""
    return IDFixtures.create_websocket_event_ids()


@pytest.fixture
def agent_ids():
    """Pytest fixture for agent execution IDs."""
    return IDFixtures.create_agent_execution_ids()


# Legacy ID migration helpers
class LegacyIDMigration:
    """Helper class for migrating legacy ID patterns."""
    
    @staticmethod
    def migrate_test_run_id(old_id: str) -> str:
        """
        Migrate legacy test run IDs to valid format.
        
        Args:
            old_id: Legacy ID like "test-run" or "test_run_123"
            
        Returns:
            Valid run_id following SSOT pattern
        """
        # Common legacy patterns
        if old_id == "test-run":
            return IDManager.generate_run_id("test_thread")
        elif old_id.startswith("test_run_"):
            # Extract any suffix and use as part of thread_id
            suffix = old_id[9:] if len(old_id) > 9 else "default"
            return IDManager.generate_run_id(f"test_thread_{suffix}")
        elif old_id.startswith("test-"):
            # Convert hyphenated format
            thread_part = old_id[5:].replace("-", "_") if len(old_id) > 5 else "thread"
            return IDManager.generate_run_id(f"test_{thread_part}")
        else:
            # For other patterns, try to extract a thread_id or use the whole thing
            thread_id = old_id.replace("-", "_").replace(" ", "_")
            if not thread_id or not IDManager.validate_thread_id(thread_id):
                thread_id = "migrated_thread"
            return IDManager.generate_run_id(thread_id)
    
    @staticmethod
    def validate_and_fix_id_pair(run_id: str, thread_id: str) -> Tuple[str, str]:
        """
        Validate and fix inconsistent ID pairs.
        
        Args:
            run_id: Existing run_id
            thread_id: Existing thread_id
            
        Returns:
            Tuple of (fixed_run_id, fixed_thread_id)
        """
        # Check if they're already consistent
        if IDManager.validate_id_pair(run_id, thread_id):
            return run_id, thread_id
        
        # If run_id is valid format, extract thread_id from it
        if IDManager.validate_run_id(run_id):
            extracted = IDManager.extract_thread_id(run_id)
            if extracted:
                return run_id, extracted
        
        # If thread_id is valid, generate new run_id
        if thread_id and IDManager.validate_thread_id(thread_id):
            new_run_id = IDManager.generate_run_id(thread_id)
            return new_run_id, thread_id
        
        # Both invalid, create new valid pair
        return IDFixtures.create_valid_ids("fixed_thread")


# Commonly used test ID sets
TEST_ID_SETS = {
    "basic": IDFixtures.create_valid_ids("basic_test"),
    "integration": IDFixtures.create_valid_ids("integration_test"),
    "e2e": IDFixtures.create_valid_ids("e2e_test"),
    "unit": IDFixtures.create_valid_ids("unit_test"),
    "websocket": IDFixtures.create_valid_ids("websocket_test"),
    "agent": IDFixtures.create_valid_ids("agent_test"),
}