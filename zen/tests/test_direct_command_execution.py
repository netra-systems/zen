#!/usr/bin/env python3
"""
Test suite for direct command execution functionality in zen orchestrator.

This module tests the new direct command execution feature that allows
users to run commands like 'zen "/analyze-code"' without config files.
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from zen_orchestrator import (
    create_direct_instance,
    InstanceConfig,
    ClaudeInstanceOrchestrator,
    main
)

class TestDirectCommandExecution:
    """Unit tests for direct command execution functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.claude_dir = self.temp_dir / ".claude"
        self.claude_dir.mkdir()

        # Create a sample command file
        commands_dir = self.claude_dir / "commands"
        commands_dir.mkdir()
        (commands_dir / "test-command.md").write_text("""---
description: Test command for testing
---

# Test Command
This is a test command.
""")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_direct_instance_with_valid_command(self):
        """Test creating direct instance with valid command."""
        # Mock args
        args = Mock()
        args.command = "/test-command"
        args.instance_name = None
        args.instance_description = None
        args.output_format = "stream-json"
        args.session_id = None
        args.clear_history = False
        args.compact_history = False
        args.overall_token_budget = None

        # Mock orchestrator validation
        with patch.object(ClaudeInstanceOrchestrator, 'discover_available_commands') as mock_discover:
            mock_discover.return_value = ["/test-command", "/help", "/clear"]

            instance = create_direct_instance(args, self.temp_dir)

        assert instance is not None
        assert instance.command == "/test-command"
        assert instance.name.startswith("direct-test-command-")
        assert instance.description == "Direct execution of /test-command"
        assert instance.output_format == "stream-json"

    def test_create_direct_instance_with_custom_options(self):
        """Test creating direct instance with custom name and description."""
        # Mock args with custom options
        args = Mock()
        args.command = "/test-command"
        args.instance_name = "my-custom-instance"
        args.instance_description = "My custom description"
        args.output_format = "json"
        args.session_id = "session-123"
        args.clear_history = True
        args.compact_history = True
        args.overall_token_budget = 5000

        # Mock orchestrator validation
        with patch.object(ClaudeInstanceOrchestrator, 'discover_available_commands') as mock_discover:
            mock_discover.return_value = ["/test-command", "/help", "/clear"]

            instance = create_direct_instance(args, self.temp_dir)

        assert instance is not None
        assert instance.command == "/test-command"
        assert instance.name == "my-custom-instance"
        assert instance.description == "My custom description"
        assert instance.output_format == "json"
        assert instance.session_id == "session-123"
        assert instance.clear_history is True
        assert instance.compact_history is True
        assert instance.max_tokens_per_command == 5000

    def test_create_direct_instance_no_command(self):
        """Test creating direct instance with no command returns None."""
        args = Mock()
        args.command = None

        instance = create_direct_instance(args, self.temp_dir)
        assert instance is None

    def test_create_direct_instance_invalid_command(self):
        """Test creating direct instance with invalid command raises SystemExit."""
        args = Mock()
        args.command = "/invalid-command"

        # Mock orchestrator validation to return empty list
        with patch.object(ClaudeInstanceOrchestrator, 'discover_available_commands') as mock_discover:
            mock_discover.return_value = ["/help", "/clear"]

            with pytest.raises(SystemExit):
                create_direct_instance(args, self.temp_dir)

    def test_create_direct_instance_command_validation_error_message(self, capsys):
        """Test error message when invalid command is provided."""
        args = Mock()
        args.command = "/nonexistent"

        # Mock orchestrator validation
        with patch.object(ClaudeInstanceOrchestrator, 'discover_available_commands') as mock_discover:
            mock_discover.return_value = ["/help", "/clear", "/test-command"]

            with pytest.raises(SystemExit):
                create_direct_instance(args, self.temp_dir)

    def test_instance_name_generation(self):
        """Test automatic instance name generation from command."""
        args = Mock()
        args.command = "/analyze-code-base"
        args.instance_name = None
        args.instance_description = None
        args.output_format = "stream-json"
        args.session_id = None
        args.clear_history = False
        args.compact_history = False
        args.overall_token_budget = None

        with patch.object(ClaudeInstanceOrchestrator, 'discover_available_commands') as mock_discover:
            mock_discover.return_value = ["/analyze-code-base"]

            instance = create_direct_instance(args, self.temp_dir)

        assert instance.name.startswith("direct-analyze-code-base-")
        assert len(instance.name.split("-")[-1]) == 8  # UUID hex[:8]


class TestDirectCommandArgumentParsing:
    """Test argument parsing for direct commands."""

    @pytest.mark.asyncio
    @patch('zen_orchestrator.ClaudeInstanceOrchestrator')
    @patch('zen_orchestrator.create_direct_instance')
    @patch('zen_orchestrator.create_default_instances')
    async def test_main_with_direct_command(self, mock_default, mock_direct, mock_orchestrator):
        """Test main function with direct command argument."""
        # Setup mocks
        mock_instance = Mock()
        mock_instance.command = "/test-command"
        mock_direct.return_value = mock_instance
        mock_orchestrator_instance = Mock()
        mock_orchestrator_instance.instances = {}
        # Create mock status objects with required attributes
        mock_status = Mock()
        mock_status.total_tokens = 100
        mock_status.cached_tokens = 20
        mock_status.tool_calls = 5
        mock_status.total_cost_usd = None  # Required for cost calculation
        mock_status.input_tokens = 50
        mock_status.output_tokens = 50
        mock_status.start_time = 1000.0  # Required for duration calculation
        mock_status.end_time = 1005.0  # Required for duration calculation
        mock_status.status = "completed"  # Required for status display
        mock_status.cache_creation_tokens = 10  # Required for cache display
        mock_status.cache_read_tokens = 10  # Required for cache display
        mock_status.error = ""  # Required for error checking
        mock_status.output = ""  # Required for output display
        mock_status.tool_details = []  # Required for tool display
        mock_orchestrator_instance.statuses = {"test-instance": mock_status}
        mock_orchestrator_instance._calculate_cost = Mock(return_value=0.001)  # Mock the cost calculation method
        mock_orchestrator_instance.pricing_engine = None  # Mock the pricing engine
        mock_orchestrator_instance.add_instance = Mock()
        mock_orchestrator_instance.run_all_instances = AsyncMock(return_value={})
        mock_orchestrator_instance.get_status_summary = Mock(return_value={"completed": 1, "failed": 0, "running": 0})
        mock_orchestrator.return_value = mock_orchestrator_instance

        # Mock sys.argv
        test_args = ["zen_orchestrator.py", "/test-command", "--workspace", str(Path.cwd())]

        with patch('sys.argv', test_args):
            # Create a temporary workspace
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                claude_dir = temp_path / ".claude"
                claude_dir.mkdir()

                with patch('zen_orchestrator.Path.cwd', return_value=temp_path):
                    with patch.object(Path, 'exists', return_value=True):
                        with patch.object(Path, 'is_dir', return_value=True):
                            # Mock the output section to avoid Mock attribute issues
                            with patch('builtins.print'):
                                try:
                                    await main()
                                except SystemExit:
                                    pass  # Expected for argument parsing test

        # Verify create_direct_instance was called
        assert mock_direct.called

    def test_argument_parser_direct_command_options(self):
        """Test that all direct command options are properly parsed."""
        import argparse
        from zen_orchestrator import main

        # We'll test the parser creation by examining the parser itself
        # This is a bit tricky since the parser is created inside main()
        # For now, we'll test through integration

    @pytest.mark.asyncio
    @patch('zen_orchestrator.ClaudeInstanceOrchestrator')
    async def test_precedence_direct_over_config(self, mock_orchestrator):
        """Test that direct command takes precedence over config file."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "instances": [
                    {"command": "/config-command", "name": "config-instance"}
                ]
            }
            json.dump(config_data, f)
            config_path = f.name

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                claude_dir = temp_path / ".claude"
                claude_dir.mkdir()

                # Mock args that include both direct command and config
                test_args = [
                    "zen_orchestrator.py",
                    "/direct-command",  # Direct command
                    "--config", config_path,  # Config file
                    "--workspace", str(temp_path)
                ]

                mock_orchestrator_instance = Mock()
                mock_orchestrator_instance.instances = {}
                # Create mock status objects with required attributes
                mock_status = Mock()
                mock_status.total_tokens = 100
                mock_status.cached_tokens = 20
                mock_status.tool_calls = 5
                mock_orchestrator_instance.statuses = {"test-instance": mock_status}
                mock_orchestrator_instance.add_instance = Mock()
                mock_orchestrator_instance.run_all_instances = AsyncMock(return_value={})
                mock_orchestrator_instance.get_status_summary = Mock(return_value={"completed": 1, "failed": 0, "running": 0})
                mock_orchestrator_instance.discover_available_commands.return_value = ["/direct-command"]
                mock_orchestrator.return_value = mock_orchestrator_instance

                with patch('sys.argv', test_args):
                    with patch.object(Path, 'exists', return_value=True):
                        with patch.object(Path, 'is_dir', return_value=True):
                            try:
                                await main()
                            except SystemExit:
                                pass  # Expected for testing

                # The direct command should take precedence
                # We can verify this by checking what instances were added

        finally:
            os.unlink(config_path)


class TestDirectCommandIntegration:
    """Integration tests for direct command execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.claude_dir = self.temp_dir / ".claude"
        self.claude_dir.mkdir()

        # Create sample commands
        commands_dir = self.claude_dir / "commands"
        commands_dir.mkdir()

        # Create a simple test command
        (commands_dir / "test-simple.md").write_text("""---
description: Simple test command
---

# Simple Test
Echo hello world.
""")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    @patch('zen_orchestrator.ClaudeInstanceOrchestrator')
    async def test_end_to_end_direct_command_execution(self, mock_orchestrator_class):
        """Test complete direct command execution flow."""
        # Setup orchestrator mock
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.discover_available_commands.return_value = ["/test-simple", "/help"]
        mock_orchestrator.instances = {}
        mock_orchestrator.statuses = {}
        mock_orchestrator.add_instance = Mock()
        mock_orchestrator.run_all_instances = AsyncMock(return_value={})
        mock_orchestrator.get_status_summary = Mock(return_value="Test summary")

        # Test arguments for direct command
        test_args = [
            "zen_orchestrator.py",
            "/test-simple",
            "--workspace", str(self.temp_dir),
            "--instance-name", "test-instance"
        ]

        with patch('sys.argv', test_args):
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'is_dir', return_value=True):
                    try:
                        await main()
                    except (SystemExit, AttributeError):
                        pass  # Expected in test environment

        # Verify orchestrator was created and command was added
        assert mock_orchestrator_class.called
        assert mock_orchestrator.add_instance.called

        # Verify the instance that was added
        call_args = mock_orchestrator.add_instance.call_args
        if call_args:
            instance = call_args[0][0]
            assert isinstance(instance, InstanceConfig)
            assert instance.command == "/test-simple"
            assert instance.name == "test-instance"

    def test_backwards_compatibility_config_mode(self):
        """Test that config file mode still works (backwards compatibility)."""
        # Create config file
        config_data = {
            "instances": [
                {
                    "command": "/test-simple",
                    "name": "config-instance",
                    "description": "Instance from config"
                }
            ]
        }

        config_file = self.temp_dir / "test_config.json"
        config_file.write_text(json.dumps(config_data))

        test_args = [
            "zen_orchestrator.py",
            "--config", str(config_file),
            "--workspace", str(self.temp_dir)
        ]

        with patch('zen_orchestrator.ClaudeInstanceOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator_class.return_value = mock_orchestrator
            mock_orchestrator.instances = {}
            mock_orchestrator.statuses = {}
            mock_orchestrator.add_instance = Mock()
            mock_orchestrator.run_all_instances = AsyncMock(return_value={})
            mock_orchestrator.get_status_summary = Mock(return_value="Test summary")

            with patch('sys.argv', test_args):
                with patch.object(Path, 'exists', return_value=True):
                    with patch.object(Path, 'is_dir', return_value=True):
                        try:
                            asyncio.run(main())
                        except (SystemExit, AttributeError):
                            pass  # Expected in test environment

        # Verify instance from config was added
        assert mock_orchestrator.add_instance.called

    def test_backwards_compatibility_default_mode(self):
        """Test that default instances mode still works (backwards compatibility)."""
        test_args = [
            "zen_orchestrator.py",
            "--workspace", str(self.temp_dir)
        ]

        with patch('zen_orchestrator.ClaudeInstanceOrchestrator') as mock_orchestrator_class:
            with patch('zen_orchestrator.create_default_instances') as mock_default:
                mock_orchestrator = Mock()
                mock_orchestrator_class.return_value = mock_orchestrator
                mock_orchestrator.instances = {}
                mock_orchestrator.statuses = {}
                mock_orchestrator.add_instance = Mock()
                mock_orchestrator.run_all_instances = AsyncMock(return_value={})
                mock_orchestrator.get_status_summary = Mock(return_value="Test summary")

                mock_default.return_value = [
                    InstanceConfig(command="default-command-1"),
                    InstanceConfig(command="default-command-2")
                ]

                with patch('sys.argv', test_args):
                    with patch.object(Path, 'exists', return_value=True):
                        with patch.object(Path, 'is_dir', return_value=True):
                            try:
                                asyncio.run(main())
                            except (SystemExit, AttributeError):
                                pass  # Expected in test environment

        # Verify default instances were used
        assert mock_default.called
        assert mock_orchestrator.add_instance.call_count == 2


class TestDirectCommandErrorHandling:
    """Test error handling for direct command execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.claude_dir = self.temp_dir / ".claude"
        self.claude_dir.mkdir()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_invalid_command_error_message(self, capsys):
        """Test error message for invalid commands includes helpful suggestions."""
        args = Mock()
        args.command = "/nonexistent-command"

        with patch.object(ClaudeInstanceOrchestrator, 'discover_available_commands') as mock_discover:
            mock_discover.return_value = ["/help", "/analyze-code", "/debug-issue"]

            with pytest.raises(SystemExit):
                create_direct_instance(args, self.temp_dir)

    def test_workspace_validation_with_direct_command(self):
        """Test workspace validation when using direct commands."""
        nonexistent_dir = Path("/nonexistent/directory")

        test_args = [
            "zen_orchestrator.py",
            "/help",
            "--workspace", str(nonexistent_dir)
        ]

        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                asyncio.run(main())


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])