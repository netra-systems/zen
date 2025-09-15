"""
Unit tests for run database model
Coverage Target: 70%
Business Value: Long-term maintainability
"""

import pytest
import time
from netra_backend.app.db.models_agent import Run
from shared.isolated_environment import IsolatedEnvironment

class RunTests:
    """Test suite for Run database model"""
    
    @pytest.fixture
    def run_data(self):
        """Create test run data"""
        return {
            "id": "run_test_123",
            "object": "thread.run", 
            "created_at": int(time.time()),
            "thread_id": "thread_test_456",
            "assistant_id": "asst_test_789",
            "status": "in_progress",
            "required_action": None,
            "last_error": None,
            "expires_at": None,
            "started_at": int(time.time()),
            "cancelled_at": None,
            "failed_at": None,
            "completed_at": None,
            "instructions": "Test instructions for run",
            "tools": [],
            "metadata": {}
        }
    
    @pytest.fixture
    def instance(self, run_data):
        """Create test instance"""
        return Run(**run_data)
    
    def test_initialization(self, instance):
        """Test proper initialization"""
        assert instance is not None
        assert instance.id == "run_test_123"
        assert instance.object == "thread.run"
        assert instance.thread_id == "thread_test_456"
        assert instance.status == "in_progress"
    
    def test_required_fields(self):
        """Test required fields validation"""
        # Test with minimal required data
        minimal_data = {
            "id": "run_minimal_123",
            "created_at": int(time.time()),
            "thread_id": "thread_minimal_456",
            "assistant_id": "asst_minimal_123",
            "status": "queued"
        }
        run = Run(**minimal_data)
        assert run.id == "run_minimal_123"
        assert run.thread_id == "thread_minimal_456"
        assert run.assistant_id == "asst_minimal_123"
        assert run.status == "queued"
    
    def test_status_transitions(self, instance):
        """Test status field updates"""
        assert instance.status == "in_progress"
        instance.status = "completed"
        assert instance.status == "completed"
        
        instance.status = "failed" 
        assert instance.status == "failed"
    
    def test_timestamps(self, instance):
        """Test timestamp fields"""
        assert instance.created_at is not None
        assert instance.started_at is not None
        assert isinstance(instance.created_at, int)
        assert isinstance(instance.started_at, int)
    
    def test_relationships(self, instance):
        """Test foreign key relationships"""
        # Run should have a thread_id that references threads table
        assert instance.thread_id == "thread_test_456"
        assert hasattr(instance, 'thread_id')  # Foreign key field exists
