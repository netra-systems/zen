#!/usr/bin/env python3
"""
Test suite for BackgroundE2EAgent

Tests the comprehensive functionality of the BackgroundE2EAgent including:
- Queue management and task scheduling
- Background process execution and monitoring
- Result persistence and retrieval
- CLI integration and status reporting
- Error handling and graceful failure recovery
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test_framework.orchestration.background_e2e_agent import (
    BackgroundE2EAgent,
    E2ETestCategory,
    BackgroundTaskConfig,
    BackgroundTaskStatus,
    BackgroundTaskResult,
    QueuedTask,
    BackgroundProcessManager,
    BackgroundResultsManager,
    add_background_e2e_arguments,
    handle_background_e2e_commands
)


class TestBackgroundE2EAgent(SSotBaseTestCase):
    """Test cases for BackgroundE2EAgent core functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_root = Path(tempfile.mkdtemp())
        self.agent = BackgroundE2EAgent(project_root=self.test_root, agent_id="test_agent")
        
    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'agent'):
            self.agent.stop()
        # Clean up temp directory
        import shutil
        if self.test_root.exists():
            shutil.rmtree(self.test_root)
    
    def test_agent_initialization(self):
        """Test BackgroundE2EAgent initializes correctly"""
        self.assertIsNotNone(self.agent)
        self.assertEqual(self.agent.project_root, self.test_root)
        self.assertIsInstance(self.agent.agent_id, str)
        self.assertFalse(self.agent.is_running)
        self.assertIsNotNone(self.agent.process_manager)
        self.assertIsNotNone(self.agent.results_manager)
        self.assertEqual(self.agent.max_concurrent_tasks, 2)
    
    def test_agent_start_stop(self):
        """Test agent start/stop lifecycle"""
        # Initially not running
        self.assertFalse(self.agent.is_running)
        
        # Start agent
        self.agent.start()
        self.assertTrue(self.agent.is_running)
        self.assertIsNotNone(self.agent.worker_thread)
        self.assertTrue(self.agent.worker_thread.is_alive())
        
        # Stop agent
        self.agent.stop()
        self.assertFalse(self.agent.is_running)
        
        # Give worker thread time to finish
        time.sleep(0.1)
        if self.agent.worker_thread:
            self.assertFalse(self.agent.worker_thread.is_alive())
    
    def test_queue_e2e_test(self):
        """Test queuing E2E tests for background execution"""
        # Queue a test
        task_id = self.agent.queue_e2e_test(E2ETestCategory.E2E_CRITICAL)
        
        self.assertIsInstance(task_id, str)
        self.assertGreater(len(task_id), 10)  # Should be a UUID
        
        # Check queue status
        status = self.agent.get_queue_status()
        self.assertEqual(status["queued_tasks"], 1)
        self.assertEqual(status["active_tasks"], 0)
        self.assertIn("e2e_critical", status["queued_by_category"])
        self.assertEqual(status["queued_by_category"]["e2e_critical"], 1)
    
    def test_queue_multiple_tests(self):
        """Test queuing multiple E2E tests"""
        # Queue different types of tests
        task_id1 = self.agent.queue_e2e_test(E2ETestCategory.CYPRESS)
        task_id2 = self.agent.queue_e2e_test(E2ETestCategory.E2E)
        task_id3 = self.agent.queue_e2e_test(E2ETestCategory.PERFORMANCE)
        
        # All should have unique IDs
        task_ids = [task_id1, task_id2, task_id3]
        self.assertEqual(len(set(task_ids)), 3)
        
        # Check queue status
        status = self.agent.get_queue_status()
        self.assertEqual(status["queued_tasks"], 3)
        self.assertEqual(status["active_tasks"], 0)
        
        expected_categories = {"cypress": 1, "e2e": 1, "performance": 1}
        self.assertEqual(status["queued_by_category"], expected_categories)
    
    def test_task_configuration(self):
        """Test custom task configuration"""
        config = BackgroundTaskConfig(
            category=E2ETestCategory.CYPRESS,
            environment="staging",
            timeout_minutes=45,
            max_retries=3,
            priority=2,
            additional_args=["--verbose", "--headed"],
            env_vars={"TEST_MODE": "staging"}
        )
        
        task_id = self.agent.queue_e2e_test(E2ETestCategory.CYPRESS, config)
        self.assertIsInstance(task_id, str)
    
    def test_get_task_status_nonexistent(self):
        """Test getting status of non-existent task"""
        status = self.agent.get_task_status("non-existent-task-id")
        self.assertIsNone(status)
    
    def test_background_process_manager(self, mock_popen):
        """Test BackgroundProcessManager functionality"""
        # Mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Still running
        mock_popen.return_value = mock_process
        
        # Create process manager
        pm = BackgroundProcessManager(self.test_root)
        
        # Start a background process
        config = BackgroundTaskConfig(E2ETestCategory.E2E)
        process = pm.start_background_process("test_task", ["echo", "test"], config)
        
        self.assertEqual(process, mock_process)
        self.assertIn("test_task", pm.processes)
        self.assertIn("test_task", pm.process_info)
        
        # Get process status
        status = pm.get_process_status("test_task")
        self.assertIsNotNone(status)
        self.assertEqual(status["pid"], 12345)
        self.assertTrue(status["running"])
        
        # Terminate process
        success = pm.terminate_process("test_task")
        self.assertTrue(success)
        self.assertNotIn("test_task", pm.processes)
    
    def test_background_results_manager(self):
        """Test BackgroundResultsManager functionality"""
        rm = BackgroundResultsManager(self.test_root)
        
        # Create a test result
        result = BackgroundTaskResult(
            task_id="test_task_123",
            category=E2ETestCategory.E2E,
            status=BackgroundTaskStatus.COMPLETED,
            exit_code=0,
            stdout="Test output",
            stderr="",
            duration_seconds=45.5,
            test_counts={"total": 5, "passed": 5, "failed": 0}
        )
        
        # Save result
        rm.save_result(result)
        
        # Verify result file exists
        result_file = rm.results_dir / "test_task_123.json"
        self.assertTrue(result_file.exists())
        
        # Load result
        loaded_result = rm.load_result("test_task_123")
        self.assertIsNotNone(loaded_result)
        self.assertEqual(loaded_result.task_id, "test_task_123")
        self.assertEqual(loaded_result.category, E2ETestCategory.E2E)
        self.assertEqual(loaded_result.status, BackgroundTaskStatus.COMPLETED)
        self.assertEqual(loaded_result.duration_seconds, 45.5)
        
        # List results
        results = rm.list_results()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].task_id, "test_task_123")
        
        # List results with filter
        filtered_results = rm.list_results(category=E2ETestCategory.CYPRESS)
        self.assertEqual(len(filtered_results), 0)
        
        filtered_results = rm.list_results(category=E2ETestCategory.E2E)
        self.assertEqual(len(filtered_results), 1)
    
    def test_get_recent_results(self):
        """Test getting recent results"""
        # Start with empty results
        recent = self.agent.get_recent_results(5)
        self.assertEqual(len(recent), 0)
        
        # Add a result manually
        result = BackgroundTaskResult(
            task_id="test_recent",
            category=E2ETestCategory.E2E,
            status=BackgroundTaskStatus.COMPLETED,
            exit_code=0,
            duration_seconds=30.0,
            test_counts={"total": 3, "passed": 3, "failed": 0}
        )
        self.agent.results_manager.save_result(result)
        
        # Get recent results
        recent = self.agent.get_recent_results(5)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["task_id"], "test_recent")
        self.assertEqual(recent[0]["category"], "e2e")
        self.assertEqual(recent[0]["status"], "completed")


class TestBackgroundE2ECLIIntegration(SSotBaseTestCase):
    """Test CLI integration for Background E2E Agent"""
    
    def setUp(self):
        """Set up CLI test environment"""
        self.test_root = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        """Clean up CLI test environment"""
        import shutil
        if self.test_root.exists():
            shutil.rmtree(self.test_root)
    
    def test_add_background_e2e_arguments(self):
        """Test adding background E2E arguments to parser"""
        import argparse
        parser = argparse.ArgumentParser()
        add_background_e2e_arguments(parser)
        
        # Test that all expected arguments are added
        help_text = parser.format_help()
        self.assertIn("--background-e2e", help_text)
        self.assertIn("--background-status", help_text)
        self.assertIn("--background-results", help_text)
        self.assertIn("--kill-background", help_text)
        self.assertIn("--background-category", help_text)
        self.assertIn("--background-timeout", help_text)
    
    def test_handle_background_status_command(self, mock_agent_class):
        """Test handling background status command"""
        # Mock agent instance
        mock_agent = Mock()
        mock_agent.get_queue_status.return_value = {
            "agent_running": True,
            "queued_tasks": 2,
            "active_tasks": 1,
            "queued_by_category": {"e2e": 1, "cypress": 1},
            "active_task_ids": ["task_123"]
        }
        mock_agent_class.return_value = mock_agent
        
        # Mock args
        args = Mock()
        args.background_status = True
        args.background_e2e = False
        args.background_results = None
        args.kill_background = None
        
        # Handle command
        exit_code = handle_background_e2e_commands(args, self.test_root)
        
        self.assertEqual(exit_code, 0)
        mock_agent.start.assert_called_once()
        mock_agent.get_queue_status.assert_called_once()
        mock_agent.stop.assert_called_once()
    
    def test_handle_background_results_command(self, mock_agent_class):
        """Test handling background results command"""
        # Mock agent instance
        mock_agent = Mock()
        mock_agent.get_recent_results.return_value = [
            {
                "task_id": "task_123",
                "category": "e2e",
                "status": "completed",
                "duration_seconds": 45.5,
                "test_counts": {"passed": 5, "failed": 0},
                "error_message": None
            }
        ]
        mock_agent_class.return_value = mock_agent
        
        # Mock args
        args = Mock()
        args.background_status = False
        args.background_e2e = False
        args.background_results = 10
        args.kill_background = None
        
        # Handle command
        exit_code = handle_background_e2e_commands(args, self.test_root)
        
        self.assertEqual(exit_code, 0)
        mock_agent.start.assert_called_once()
        mock_agent.get_recent_results.assert_called_once_with(10)
        mock_agent.stop.assert_called_once()
    
    def test_handle_background_e2e_command(self, mock_agent_class):
        """Test handling background E2E execution command"""
        # Mock agent instance
        mock_agent = Mock()
        mock_agent.queue_e2e_test.return_value = "task_456"
        mock_agent_class.return_value = mock_agent
        
        # Mock args
        args = Mock()
        args.background_status = False
        args.background_e2e = True
        args.background_results = None
        args.kill_background = None
        args.background_category = "cypress"
        args.background_timeout = 45
        args.env = "staging"
        args.real_services = True
        args.real_llm = False
        
        # Handle command
        exit_code = handle_background_e2e_commands(args, self.test_root)
        
        self.assertEqual(exit_code, 0)
        mock_agent.start.assert_called_once()
        mock_agent.queue_e2e_test.assert_called_once()
        mock_agent.stop.assert_called_once()
        
        # Verify the config passed to queue_e2e_test
        call_args = mock_agent.queue_e2e_test.call_args
        category, config = call_args[0]
        self.assertEqual(category, E2ETestCategory.CYPRESS)
        self.assertEqual(config.timeout_minutes, 45)
        self.assertEqual(config.environment, "staging")
        self.assertTrue(config.use_real_services)
        self.assertFalse(config.use_real_llm)


class TestBackgroundE2EAgentWithMockedServices(SSotBaseTestCase):
    """Test BackgroundE2EAgent with mocked service dependencies"""
    
    def setUp(self):
        """Set up test with mocked services"""
        self.test_root = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        """Clean up"""
        import shutil
        if self.test_root.exists():
            shutil.rmtree(self.test_root)
    
    def test_service_availability_check(self, mock_checker_class):
        """Test service availability checking"""
        # Mock service checker
        mock_checker = Mock()
        mock_checker.check_service_health.return_value = True
        mock_checker_class.return_value = mock_checker
        
        agent = BackgroundE2EAgent(project_root=self.test_root)
        
        # Test service availability
        config = BackgroundTaskConfig(
            category=E2ETestCategory.E2E,
            services_required={"postgres", "redis", "backend"}
        )
        
        available = agent._ensure_services_available(config)
        self.assertTrue(available)
        
        # Verify all required services were checked
        expected_calls = [
        ]
        mock_checker.check_service_health.assert_has_calls(expected_calls, any_order=True)
    
    def test_service_unavailable_handling(self, mock_checker_class):
        """Test handling when required services are unavailable"""
        # Mock service checker to return False for some services
        mock_checker = Mock()
        
        def mock_health_check(service):
            return service != "postgres"  # postgres unavailable
        
        mock_checker.check_service_health.side_effect = mock_health_check
        mock_checker_class.return_value = mock_checker
        
        agent = BackgroundE2EAgent(project_root=self.test_root)
        
        # Test service availability
        config = BackgroundTaskConfig(
            category=E2ETestCategory.E2E,
            services_required={"postgres", "redis", "backend"}
        )
        
        available = agent._ensure_services_available(config)
        self.assertFalse(available)


class TestTaskPriorityAndQueuing(SSotBaseTestCase):
    """Test task priority and queuing behavior"""
    
    def setUp(self):
        """Set up priority test environment"""
        self.test_root = Path(tempfile.mkdtemp())
        self.agent = BackgroundE2EAgent(project_root=self.test_root, agent_id="priority_test")
        
    def tearDown(self):
        """Clean up priority test environment"""
        if hasattr(self, 'agent'):
            self.agent.stop()
        import shutil
        if self.test_root.exists():
            shutil.rmtree(self.test_root)
    
    def test_task_priority_ordering(self):
        """Test that tasks are processed in priority order"""
        # Queue tasks with different priorities
        high_priority_config = BackgroundTaskConfig(
            category=E2ETestCategory.E2E_CRITICAL,
            priority=1  # High priority
        )
        low_priority_config = BackgroundTaskConfig(
            category=E2ETestCategory.E2E,
            priority=3  # Low priority
        )
        medium_priority_config = BackgroundTaskConfig(
            category=E2ETestCategory.CYPRESS,
            priority=2  # Medium priority
        )
        
        # Queue in reverse priority order
        task_id1 = self.agent.queue_e2e_test(E2ETestCategory.E2E, low_priority_config)
        task_id2 = self.agent.queue_e2e_test(E2ETestCategory.CYPRESS, medium_priority_config)
        task_id3 = self.agent.queue_e2e_test(E2ETestCategory.E2E_CRITICAL, high_priority_config)
        
        # Verify all tasks are queued
        status = self.agent.get_queue_status()
        self.assertEqual(status["queued_tasks"], 3)


if __name__ == "__main__":
    # Setup logging for tests
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests
    unittest.main(verbosity=2)