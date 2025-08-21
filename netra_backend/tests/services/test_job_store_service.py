"""Test job store service for background task management."""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from enum import Enum

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.job_store import JobStore, job_store

# Add project root to path
class TestJobStore:
    """Test basic job store functionality."""

    async def test_job_store_initialization(self):
        """Test job store can be initialized."""
        store = JobStore()
        assert store._jobs == {}

    async def test_set_and_get_job(self):
        """Test setting and getting job data."""
        store = JobStore()
        
        job_data = {
            "id": "test_job_123",
            "name": "test_job",
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        await store.set("test_job_123", job_data)
        retrieved = await store.get("test_job_123")
        
        assert retrieved == job_data
        assert retrieved["id"] == "test_job_123"
        assert retrieved["status"] == "pending"

    async def test_update_job_status(self):
        """Test updating job status."""
        store = JobStore()
        
        job_data = {
            "id": "test_job_456",
            "status": "pending"
        }
        
        await store.set("test_job_456", job_data)
        await store.update("test_job_456", "running", started_at=datetime.now().isoformat())
        
        updated = await store.get("test_job_456")
        assert updated["status"] == "running"
        assert "started_at" in updated

    async def test_nonexistent_job(self):
        """Test getting a job that doesn't exist."""
        store = JobStore()
        result = await store.get("nonexistent_job")
        assert result == None

    async def test_global_job_store(self):
        """Test the global job store instance."""
        assert job_store != None
        assert isinstance(job_store, JobStore)
        
        # Test global store works
        await job_store.set("global_test", {"status": "test"})
        result = await job_store.get("global_test")
        assert result["status"] == "test"