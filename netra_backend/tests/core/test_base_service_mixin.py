"""Tests for BaseServiceMixin functionality."""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio

import pytest

from netra_backend.app.core.service_interfaces import BaseServiceMixin, ServiceMetrics

class TestBaseServiceMixin:
    """Test BaseServiceMixin functionality."""
    
    def test_initialization(self):
        """Test BaseServiceMixin initialization."""
        mixin = BaseServiceMixin()
        
        assert not mixin.is_initialized
        assert isinstance(mixin.metrics, ServiceMetrics)
        assert len(mixin._background_tasks) == 0
    
    def test_update_metrics_success(self):
        """Test updating metrics for successful operation."""
        mixin = BaseServiceMixin()
        initial_total = mixin.metrics.requests_total
        initial_successful = mixin.metrics.requests_successful
        
        mixin._update_metrics(success=True, response_time=0.5)
        
        assert mixin.metrics.requests_total == initial_total + 1
        assert mixin.metrics.requests_successful == initial_successful + 1
        assert mixin.metrics.requests_failed == 0
        assert mixin.metrics.average_response_time == 0.5
    
    def test_update_metrics_failure(self):
        """Test updating metrics for failed operation."""
        mixin = BaseServiceMixin()
        initial_total = mixin.metrics.requests_total
        initial_failed = mixin.metrics.requests_failed
        
        mixin._update_metrics(success=False, response_time=1.0)
        
        assert mixin.metrics.requests_total == initial_total + 1
        assert mixin.metrics.requests_failed == initial_failed + 1
        assert mixin.metrics.requests_successful == 0
        assert mixin.metrics.average_response_time == 1.0
    
    def test_update_metrics_average_calculation(self):
        """Test average response time calculation."""
        mixin = BaseServiceMixin()
        
        mixin._update_metrics(success=True, response_time=1.0)
        assert mixin.metrics.average_response_time == 1.0
        
        mixin._update_metrics(success=True, response_time=3.0)
        assert mixin.metrics.average_response_time == 2.0  # (1.0 + 3.0) / 2

    async def _create_dummy_task(self):
        """Helper: Create dummy async task."""
        await asyncio.sleep(0.1)
        return "done"

    def _verify_task_in_background(self, mixin, task):
        """Helper: Verify task is tracked in background tasks."""
        assert task in mixin._background_tasks

    async def test_create_background_task(self):
        """Test creating background tasks."""
        mixin = BaseServiceMixin()
        
        task = mixin._create_background_task(self._create_dummy_task())
        self._verify_task_in_background(mixin, task)
        
        # Task should be removed when done
        result = await task
        assert result == "done"

    async def _create_long_task(self):
        """Helper: Create long-running task."""
        await asyncio.sleep(10)  # Long task

    def _verify_tasks_count(self, mixin, expected_count):
        """Helper: Verify background tasks count."""
        assert len(mixin._background_tasks) == expected_count

    def _verify_tasks_cancelled(self, task1, task2):
        """Helper: Verify tasks are cancelled."""
        assert task1.cancelled()
        assert task2.cancelled()

    async def test_cancel_background_tasks(self):
        """Test cancelling background tasks."""
        mixin = BaseServiceMixin()
        
        # Create some background tasks
        task1 = mixin._create_background_task(self._create_long_task())
        task2 = mixin._create_background_task(self._create_long_task())
        
        self._verify_tasks_count(mixin, 2)
        
        # Cancel all tasks
        await mixin._cancel_background_tasks()
        
        self._verify_tasks_count(mixin, 0)
        self._verify_tasks_cancelled(task1, task2)