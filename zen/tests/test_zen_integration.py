#!/usr/bin/env python3
"""
Integration tests for zen_orchestrator.py

Tests the orchestrator workflow, async execution, and process management
with real subprocess execution (using safe commands).
"""

import pytest
import asyncio
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
import os

# Add service directory to path to import the module
service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(service_dir))

from zen_orchestrator import (
    InstanceConfig,
    InstanceStatus,
    ClaudeInstanceOrchestrator,
    main
)


class TestOrchestratorWorkflow:
    """Test orchestrator workflow integration"""

    def setup_method(self):
        """Create temporary workspace with mock commands"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        self.commands_dir = self.workspace / ".claude" / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)

        # Create mock commands
        self.create_mock_commands()

        self.orchestrator = ClaudeInstanceOrchestrator(
            self.workspace,
            max_console_lines=0,  # Quiet mode for tests
            startup_delay=0.1,    # Fast startup for tests
            quiet=True
        )

    def teardown_method(self):
        """Clean up temporary workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_mock_commands(self):
        """Create mock command files for testing"""
        commands = {
            "test-command.md": """---
description: "Test command for integration testing"
---

# Test Command

This is a test command that does nothing harmful.
""",
            "quick-command.md": """---
description: "Quick test command"
---

# Quick Command

Another test command.
""",
            "slow-command.md": """---
description: "Slow test command"
---

# Slow Command

A command that might take longer.
"""
        }

        for filename, content in commands.items():
            (self.commands_dir / filename).write_text(content)

    def test_add_and_validate_instances(self):
        """Test adding and validating multiple instances"""
        config1 = InstanceConfig(command="/test-command", name="test1")
        config2 = InstanceConfig(command="/quick-command", name="test2")
        config3 = InstanceConfig(command="/nonexistent", name="test3")

        self.orchestrator.add_instance(config1)
        self.orchestrator.add_instance(config2)
        self.orchestrator.add_instance(config3)

        assert len(self.orchestrator.instances) == 3
        assert len(self.orchestrator.statuses) == 3

        # Check validation
        assert self.orchestrator.validate_command("/test-command") is True
        assert self.orchestrator.validate_command("/quick-command") is True
        assert self.orchestrator.validate_command("/nonexistent") is False

    def test_command_discovery_integration(self):
        """Test command discovery with real file system"""
        commands = self.orchestrator.discover_available_commands()

        # Should find our mock commands plus built-ins
        assert "/test-command" in commands
        assert "/quick-command" in commands
        assert "/slow-command" in commands
        assert "/compact" in commands
        assert "/clear" in commands
        assert "/help" in commands

        # Should be sorted
        custom_commands = [cmd for cmd in commands if cmd.startswith("/test") or cmd.startswith("/quick") or cmd.startswith("/slow")]
        assert custom_commands == sorted(custom_commands)

    def test_command_inspection_integration(self):
        """Test command inspection with real files"""
        info = self.orchestrator.inspect_command("/test-command")

        assert info["exists"] is True
        assert info["frontmatter"]["description"] == "Test command for integration testing"
        assert "file_path" in info
        assert info["file_path"].endswith("test-command.md")
        assert "Test Command" in info["content_preview"]

    @patch('subprocess.Popen')
    def test_build_and_mock_execution(self, mock_popen):
        """Test building commands and mocking execution"""
        # Mock successful process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Mock output", b"")
        mock_popen.return_value = mock_process

        config = InstanceConfig(
            command="/test-command",
            name="test-instance",
            permission_mode="read",
            output_format="json"
        )

        cmd = self.orchestrator.build_claude_command(config)

        # Verify command structure
        assert "-p" in cmd
        assert "/test-command" in cmd
        assert "--output-format=json" in cmd
        assert "--permission-mode=read" in cmd

    def test_status_summary_workflow(self):
        """Test complete status summary workflow"""
        # Add instances in different states
        config1 = InstanceConfig(command="/test-command", name="completed")
        config2 = InstanceConfig(command="/quick-command", name="running")
        config3 = InstanceConfig(command="/slow-command", name="failed")

        self.orchestrator.add_instance(config1)
        self.orchestrator.add_instance(config2)
        self.orchestrator.add_instance(config3)

        # Set different statuses
        self.orchestrator.statuses["completed"].status = "completed"
        self.orchestrator.statuses["completed"].start_time = time.time() - 60
        self.orchestrator.statuses["completed"].end_time = time.time() - 30
        self.orchestrator.statuses["completed"].total_tokens = 1500

        self.orchestrator.statuses["running"].status = "running"
        self.orchestrator.statuses["running"].start_time = time.time() - 30
        self.orchestrator.statuses["running"].total_tokens = 800

        self.orchestrator.statuses["failed"].status = "failed"
        self.orchestrator.statuses["failed"].error = "Mock error"

        # Get summary
        summary = self.orchestrator.get_status_summary()

        assert summary["total_instances"] == 3
        assert summary["completed"] == 1
        assert summary["running"] == 1
        assert summary["failed"] == 1
        assert summary["pending"] == 0

        # Check instance details
        assert "duration" in summary["instances"]["completed"]
        assert summary["instances"]["failed"]["error"] == "Mock error"

    def test_save_and_load_results_workflow(self):
        """Test complete save and load results workflow"""
        # Add and configure instances
        config = InstanceConfig(command="/test-command", name="test-instance")
        self.orchestrator.add_instance(config)

        # Set up some test data
        status = self.orchestrator.statuses["test-instance"]
        status.status = "completed"
        status.start_time = time.time() - 60
        status.end_time = time.time() - 30
        status.total_tokens = 1200
        status.input_tokens = 700
        status.output_tokens = 400
        status.cached_tokens = 100
        status.tool_calls = 2

        # Save results
        output_file = Path(self.temp_dir) / "test_results.json"
        self.orchestrator.save_results(output_file)

        assert output_file.exists()

        # Load and verify
        with open(output_file) as f:
            data = json.load(f)

        assert data["total_instances"] == 1
        assert data["completed"] == 1
        assert data["instances"]["test-instance"]["total_tokens"] == 1200
        assert data["instances"]["test-instance"]["tool_calls"] == 2

        # Check metadata
        metadata = data["metadata"]
        assert metadata["token_usage"]["total_tokens"] == 1200
        assert metadata["token_usage"]["cache_hit_rate"] == round(100/1200*100, 2)

    def test_filename_generation_workflow(self):
        """Test filename generation with real instance names"""
        # Add instances with various names
        config1 = InstanceConfig(command="/test-command", name="Test-Instance_1")
        config2 = InstanceConfig(command="/quick-command", name="Quick@Command#2")

        self.orchestrator.add_instance(config1)
        self.orchestrator.add_instance(config2)

        filename = self.orchestrator.generate_output_filename("test_base")

        # Verify structure
        assert str(filename).startswith("test_base_")
        assert str(filename).endswith(".json")

        # Should clean special characters in names
        filename_str = str(filename)
        assert "@" not in filename_str
        assert "#" not in filename_str


class TestAsyncExecution:
    """Test async execution and process management"""

    def setup_method(self):
        """Create temporary workspace for async tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        self.orchestrator = ClaudeInstanceOrchestrator(
            self.workspace,
            max_console_lines=0,  # Quiet mode
            startup_delay=0.05,   # Very fast for tests
            quiet=True
        )

    def teardown_method(self):
        """Clean up temporary workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_run_instance_with_delay(self):
        """Test running instance with delay"""
        config = InstanceConfig(command="/help", name="test-delay")
        self.orchestrator.add_instance(config)

        start_time = time.time()

        # Mock the actual run_instance to avoid subprocess
        with patch.object(self.orchestrator, 'run_instance', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = True

            result = await self.orchestrator._run_instance_with_delay("test-delay", 0.1, 10)

            end_time = time.time()

            # Should have waited at least 0.1 seconds
            assert end_time - start_time >= 0.1
            assert result is True
            mock_run.assert_called_once_with("test-delay")

    @pytest.mark.asyncio
    async def test_run_instance_timeout(self):
        """Test instance timeout handling"""
        config = InstanceConfig(command="/help", name="test-timeout")
        self.orchestrator.add_instance(config)

        # Mock a long-running process that times out
        with patch.object(self.orchestrator, 'run_instance', new_callable=AsyncMock) as mock_run:
            async def slow_run(*args):
                await asyncio.sleep(1)  # Longer than timeout
                return True

            mock_run.side_effect = slow_run

            with pytest.raises(asyncio.TimeoutError):
                await self.orchestrator._run_instance_with_delay("test-timeout", 0, 0.1)

    @pytest.mark.asyncio
    async def test_multiple_instances_staggered_startup(self):
        """Test multiple instances with staggered startup"""
        configs = [
            InstanceConfig(command="/help", name="instance1"),
            InstanceConfig(command="/help", name="instance2"),
            InstanceConfig(command="/help", name="instance3")
        ]

        for config in configs:
            self.orchestrator.add_instance(config)

        start_time = time.time()

        # Mock the actual run_instance to avoid subprocess
        with patch.object(self.orchestrator, 'run_instance', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = True

            # Set very short startup delay for test speed
            self.orchestrator.startup_delay = 0.05

            results = await self.orchestrator.run_all_instances(timeout=1)

            end_time = time.time()

            # Should take at least 2 * startup_delay (0.1s) for 3 instances
            # (instance1: 0s, instance2: 0.05s, instance3: 0.1s)
            assert end_time - start_time >= 0.1

            # All should succeed
            assert all(results.values())
            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_status_reporter_task(self):
        """Test rolling status reporter task"""
        config = InstanceConfig(command="/help", name="test-status")
        self.orchestrator.add_instance(config)

        # Set very short report interval for testing
        self.orchestrator.status_report_interval = 0.1

        with patch.object(self.orchestrator, 'run_instance', new_callable=AsyncMock) as mock_run:
            with patch.object(self.orchestrator, '_print_status_report', new_callable=AsyncMock) as mock_print:
                async def slow_run(*args):
                    await asyncio.sleep(0.3)  # Long enough for status reports
                    return True

                mock_run.side_effect = slow_run

                results = await self.orchestrator.run_all_instances(timeout=1)

                # Status report should have been called multiple times
                assert mock_print.call_count >= 2

    @pytest.mark.asyncio
    @patch('shutil.which', return_value='echo')  # Use 'echo' as safe substitute for claude
    async def test_real_subprocess_execution(self, mock_which):
        """Test real subprocess execution with safe command"""
        config = InstanceConfig(
            command="Hello World",  # Will be passed to echo
            name="test-real",
            output_format="json"
        )
        self.orchestrator.add_instance(config)

        # This will actually run 'echo -p "Hello World" --output-format=json --permission-mode=bypassPermissions'
        # which is safe and should complete quickly
        result = await self.orchestrator.run_instance("test-real")

        # Should complete successfully
        assert result is True
        assert self.orchestrator.statuses["test-real"].status == "completed"
        assert self.orchestrator.statuses["test-real"].pid is not None

    @pytest.mark.asyncio
    async def test_process_error_handling(self):
        """Test process error handling"""
        config = InstanceConfig(command="/help", name="test-error")
        self.orchestrator.add_instance(config)

        # Mock a process that fails
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.wait.return_value = asyncio.create_task(asyncio.coroutine(lambda: 1)())  # Non-zero exit
            mock_process.communicate.return_value = asyncio.create_task(
                asyncio.coroutine(lambda: (b"", b"Mock error"))()
            )
            mock_subprocess.return_value = mock_process

            result = await self.orchestrator.run_instance("test-error")

            assert result is False
            assert self.orchestrator.statuses["test-error"].status == "failed"
            assert "Mock error" in self.orchestrator.statuses["test-error"].error

    @pytest.mark.asyncio
    async def test_exception_handling_in_run_instance(self):
        """Test exception handling during instance execution"""
        config = InstanceConfig(command="/help", name="test-exception")
        self.orchestrator.add_instance(config)

        # Mock subprocess to raise exception
        with patch('asyncio.create_subprocess_exec', side_effect=Exception("Mock exception")):
            result = await self.orchestrator.run_instance("test-exception")

            assert result is False
            assert self.orchestrator.statuses["test-exception"].status == "failed"
            assert "Mock exception" in self.orchestrator.statuses["test-exception"].error


class TestMainFunction:
    """Test main function integration"""

    def setup_method(self):
        """Setup for main function tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('sys.argv', ['script', '--workspace', 'test_workspace', '--dry-run'])
    @patch('pathlib.Path.cwd')
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_dir', return_value=True)
    def test_main_dry_run(self, mock_is_dir, mock_exists, mock_cwd):
        """Test main function in dry run mode"""
        mock_cwd.return_value = self.workspace

        # Should not raise exception
        try:
            asyncio.run(main())
        except SystemExit as e:
            # Dry run should exit with code 0
            assert e.code == 0

    @patch('sys.argv', ['script', '--list-commands'])
    @patch('pathlib.Path.cwd')
    def test_main_list_commands(self, mock_cwd):
        """Test main function list commands mode"""
        mock_cwd.return_value = self.workspace

        # Create minimal .claude structure
        commands_dir = self.workspace / ".claude" / "commands"
        commands_dir.mkdir(parents=True, exist_ok=True)

        try:
            asyncio.run(main())
        except SystemExit:
            pass  # Expected to exit after listing

    @patch('sys.argv', ['script', '--inspect-command', '/help'])
    @patch('pathlib.Path.cwd')
    def test_main_inspect_command(self, mock_cwd):
        """Test main function inspect command mode"""
        mock_cwd.return_value = self.workspace

        try:
            asyncio.run(main())
        except SystemExit:
            pass  # Expected to exit after inspection

    @patch('sys.argv', ['script', '--workspace', '/nonexistent'])
    def test_main_invalid_workspace(self):
        """Test main function with invalid workspace"""
        try:
            asyncio.run(main())
        except SystemExit as e:
            # Should exit with error code
            assert e.code == 1

    @patch('sys.argv', ['script', '--start-at', 'invalid_time'])
    @patch('pathlib.Path.cwd')
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_dir', return_value=True)
    def test_main_invalid_start_time(self, mock_is_dir, mock_exists, mock_cwd):
        """Test main function with invalid start time"""
        mock_cwd.return_value = self.workspace

        try:
            asyncio.run(main())
        except SystemExit as e:
            # Should exit with error code
            assert e.code == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])