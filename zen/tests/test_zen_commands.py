#!/usr/bin/env python3
"""
Unit tests for zen_orchestrator.py command functionality

Tests command discovery, validation, Claude command building, and file inspection.
"""

import pytest
import tempfile
import shutil
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add service directory to path to import the module
service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(service_dir))

from zen_orchestrator import (
    InstanceConfig,
    ClaudeInstanceOrchestrator
)


class TestCommandDiscovery:
    """Test command discovery functionality"""

    def setup_method(self):
        """Create temporary workspace with .claude/commands directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        self.commands_dir = self.workspace / ".claude" / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up temporary workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_discover_commands_empty_directory(self):
        """Test discovering commands from empty directory"""
        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        commands = orchestrator.discover_available_commands()

        # Should contain built-in commands even when no custom commands exist
        assert "/compact" in commands
        assert "/clear" in commands
        assert "/help" in commands
        assert isinstance(commands, list)

    def test_discover_commands_with_custom_commands(self):
        """Test discovering custom commands from .claude/commands"""
        # Create some test command files
        (self.commands_dir / "test-command.md").write_text("# Test Command\nTest content")
        (self.commands_dir / "another-command.md").write_text("# Another Command")
        (self.commands_dir / "third.md").write_text("# Third Command")

        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        commands = orchestrator.discover_available_commands()

        # Should contain both built-in and custom commands
        assert "/test-command" in commands
        assert "/another-command" in commands
        assert "/third" in commands
        assert "/compact" in commands
        assert "/clear" in commands
        assert "/help" in commands

    def test_discover_commands_sorts_alphabetically(self):
        """Test that commands are sorted alphabetically"""
        # Create commands that would be unsorted by default
        (self.commands_dir / "zebra.md").write_text("# Zebra Command")
        (self.commands_dir / "alpha.md").write_text("# Alpha Command")
        (self.commands_dir / "beta.md").write_text("# Beta Command")

        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        commands = orchestrator.discover_available_commands()

        # Find our custom commands
        custom_commands = [cmd for cmd in commands if cmd in ["/zebra", "/alpha", "/beta"]]
        assert custom_commands == ["/alpha", "/beta", "/zebra"]

    def test_discover_commands_ignores_non_md_files(self):
        """Test that only .md files are recognized as commands"""
        # Create various file types
        (self.commands_dir / "command.md").write_text("# Valid Command")
        (self.commands_dir / "not-command.txt").write_text("Not a command")
        (self.commands_dir / "also-not.py").write_text("# Not a command")
        (self.commands_dir / "README").write_text("Not a command")

        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        commands = orchestrator.discover_available_commands()

        assert "/command" in commands
        assert "/not-command" not in commands
        assert "/also-not" not in commands
        assert "/README" not in commands

    def test_discover_commands_no_claude_directory(self):
        """Test discovering commands when .claude directory doesn't exist"""
        # Don't create the .claude directory
        workspace = Path(self.temp_dir) / "no-claude"
        workspace.mkdir()

        orchestrator = ClaudeInstanceOrchestrator(workspace)
        commands = orchestrator.discover_available_commands()

        # Should still return built-in commands
        assert "/compact" in commands
        assert "/clear" in commands
        assert "/help" in commands
        assert len(commands) == 3  # Only built-ins


class TestCommandValidation:
    """Test command validation functionality"""

    def setup_method(self):
        """Create temporary workspace with test commands"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        self.commands_dir = self.workspace / ".claude" / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)

        # Create test commands
        (self.commands_dir / "valid-command.md").write_text("# Valid Command")
        (self.commands_dir / "another-valid.md").write_text("# Another Valid")

    def teardown_method(self):
        """Clean up temporary workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_existing_command(self):
        """Test validating an existing command"""
        orchestrator = ClaudeInstanceOrchestrator(self.workspace)

        assert orchestrator.validate_command("/valid-command") is True
        assert orchestrator.validate_command("/another-valid") is True

    def test_validate_builtin_command(self):
        """Test validating built-in commands"""
        orchestrator = ClaudeInstanceOrchestrator(self.workspace)

        assert orchestrator.validate_command("/compact") is True
        assert orchestrator.validate_command("/clear") is True
        assert orchestrator.validate_command("/help") is True

    def test_validate_nonexistent_command(self):
        """Test validating non-existent command"""
        orchestrator = ClaudeInstanceOrchestrator(self.workspace)

        assert orchestrator.validate_command("/nonexistent") is False
        assert orchestrator.validate_command("/not-a-command") is False

    def test_validate_command_with_arguments(self):
        """Test validating command with arguments (should extract base command)"""
        orchestrator = ClaudeInstanceOrchestrator(self.workspace)

        # Should validate the base command part
        assert orchestrator.validate_command("/valid-command arg1 arg2") is True
        assert orchestrator.validate_command("/compact --force") is True
        assert orchestrator.validate_command("/nonexistent arg1 arg2") is False

    def test_validate_empty_command(self):
        """Test validating empty or malformed commands"""
        orchestrator = ClaudeInstanceOrchestrator(self.workspace)

        assert orchestrator.validate_command("") is False
        assert orchestrator.validate_command("   ") is False
        assert orchestrator.validate_command("not-slash-command") is False


class TestCommandInspection:
    """Test command file inspection functionality"""

    def setup_method(self):
        """Create temporary workspace with test command files"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        self.commands_dir = self.workspace / ".claude" / "commands"
        self.commands_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up temporary workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_inspect_command_with_yaml_frontmatter(self):
        """Test inspecting command file with YAML frontmatter"""
        command_content = """---
description: "Test command for validation"
author: "Test Author"
version: "1.0"
tags: ["test", "validation"]
---

# Test Command

This is a test command for validation purposes.
It does various test-related tasks.
"""
        (self.commands_dir / "test-command.md").write_text(command_content)

        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        info = orchestrator.inspect_command("/test-command")

        assert info["exists"] is True
        assert "frontmatter" in info
        assert info["frontmatter"]["description"] == "Test command for validation"
        assert info["frontmatter"]["author"] == "Test Author"
        assert info["frontmatter"]["version"] == "1.0"
        assert info["frontmatter"]["tags"] == ["test", "validation"]
        assert "file_path" in info
        assert info["file_path"].endswith("test-command.md")
        assert "content_preview" in info

    def test_inspect_command_without_frontmatter(self):
        """Test inspecting command file without YAML frontmatter"""
        command_content = """# Simple Command

This is a simple command without frontmatter.
It just has regular markdown content.
"""
        (self.commands_dir / "simple-command.md").write_text(command_content)

        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        info = orchestrator.inspect_command("/simple-command")

        assert info["exists"] is True
        assert info["frontmatter"] == {}
        assert "file_path" in info
        assert "content_preview" in info
        assert "Simple Command" in info["content_preview"]

    def test_inspect_command_invalid_yaml(self):
        """Test inspecting command file with invalid YAML frontmatter"""
        command_content = """---
invalid: yaml: content: [unclosed
---

# Command with Invalid YAML

This command has invalid YAML frontmatter.
"""
        (self.commands_dir / "invalid-yaml.md").write_text(command_content)

        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        info = orchestrator.inspect_command("/invalid-yaml")

        assert info["exists"] is True
        # Should handle invalid YAML gracefully
        assert "frontmatter" in info or "error" not in info

    def test_inspect_nonexistent_command(self):
        """Test inspecting non-existent command"""
        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        info = orchestrator.inspect_command("/nonexistent")

        assert info["exists"] is False

    def test_inspect_command_with_arguments(self):
        """Test inspecting command with arguments (should strip arguments)"""
        command_content = """---
description: "Command with args test"
---

# Command With Args

This command accepts arguments.
"""
        (self.commands_dir / "args-command.md").write_text(command_content)

        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        info = orchestrator.inspect_command("/args-command arg1 arg2")

        assert info["exists"] is True
        assert info["frontmatter"]["description"] == "Command with args test"

    def test_inspect_command_long_content(self):
        """Test inspecting command with long content (should preview only)"""
        long_content = "A" * 500  # Longer than 200 char preview
        command_content = f"""# Long Command

{long_content}
"""
        (self.commands_dir / "long-command.md").write_text(command_content)

        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        info = orchestrator.inspect_command("/long-command")

        assert info["exists"] is True
        assert "content_preview" in info
        # Should be truncated with "..."
        assert len(info["content_preview"]) <= 203  # 200 + "..."
        assert info["content_preview"].endswith("...")


class TestClaudeCommandBuilding:
    """Test Claude command building functionality"""

    def setup_method(self):
        """Create temporary workspace"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('shutil.which')
    def test_build_claude_command_basic(self, mock_which):
        """Test building basic Claude command"""
        mock_which.return_value = "/usr/local/bin/claude"

        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        config = InstanceConfig(command="/test-command")

        cmd = orchestrator.build_claude_command(config)

        assert cmd[0] == "/usr/local/bin/claude"
        assert "-p" in cmd
        assert "/test-command" in cmd
        assert "--output-format=stream-json" in cmd
        assert "--permission-mode=bypassPermissions" in cmd
        assert "--verbose" in cmd  # Required for stream-json

    @patch('shutil.which')
    def test_build_claude_command_with_pre_commands(self, mock_which):
        """Test building Claude command with pre-commands"""
        mock_which.return_value = "/usr/local/bin/claude"

        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        config = InstanceConfig(
            command="/main-command",
            pre_commands=["/setup", "/config"],
            clear_history=True,
            compact_history=True
        )

        cmd = orchestrator.build_claude_command(config)

        # Find the prompt argument
        prompt_index = cmd.index("-p") + 1
        prompt = cmd[prompt_index]

        # Should contain all commands in sequence
        assert "/clear" in prompt
        assert "/compact" in prompt
        assert "/setup" in prompt
        assert "/config" in prompt
        assert "/main-command" in prompt

    @patch('shutil.which')
    def test_build_claude_command_json_format(self, mock_which):
        """Test building Claude command with JSON format"""
        mock_which.return_value = "/usr/local/bin/claude"

        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        config = InstanceConfig(
            command="/test-command",
            output_format="json"
        )

        cmd = orchestrator.build_claude_command(config)

        assert "--output-format=json" in cmd
        assert "--verbose" not in cmd  # Not required for json format

    @patch('shutil.which')
    def test_build_claude_command_with_tools(self, mock_which):
        """Test building Claude command with allowed tools"""
        mock_which.return_value = "/usr/local/bin/claude"

        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        config = InstanceConfig(
            command="/test-command",
            allowed_tools=["tool1", "tool2", "tool3"]
        )

        cmd = orchestrator.build_claude_command(config)

        assert "--allowedTools=tool1,tool2,tool3" in cmd

    @patch('shutil.which')
    def test_build_claude_command_with_session(self, mock_which):
        """Test building Claude command with session ID"""
        mock_which.return_value = "/usr/local/bin/claude"

        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        config = InstanceConfig(
            command="/test-command",
            session_id="test-session-123"
        )

        cmd = orchestrator.build_claude_command(config)

        assert "--session-id" in cmd
        session_index = cmd.index("--session-id") + 1
        assert cmd[session_index] == "test-session-123"

    @patch('shutil.which')
    @patch('platform.system')
    def test_build_claude_command_mac_paths(self, mock_system, mock_which):
        """Test building Claude command with Mac-specific path detection"""
        mock_which.return_value = None  # Not found in PATH
        mock_system.return_value = "Darwin"

        # Mock Path.exists for Homebrew ARM path
        with patch('pathlib.Path.exists') as mock_exists:
            def path_exists_side_effect(path_obj):
                return str(path_obj) == "/opt/homebrew/bin/claude"
            mock_exists.side_effect = lambda: path_exists_side_effect(mock_exists.call_args[0][0])

            orchestrator = ClaudeInstanceOrchestrator(self.workspace)
            config = InstanceConfig(command="/test-command")

            cmd = orchestrator.build_claude_command(config)

            # Should use the found Mac path
            assert cmd[0] == "/opt/homebrew/bin/claude"

    @patch('shutil.which')
    def test_build_claude_command_not_found(self, mock_which):
        """Test building Claude command when executable not found"""
        mock_which.return_value = None

        with patch('pathlib.Path.exists', return_value=False):
            orchestrator = ClaudeInstanceOrchestrator(self.workspace)
            config = InstanceConfig(command="/test-command")

            cmd = orchestrator.build_claude_command(config)

            # Should fallback to "claude"
            assert cmd[0] == "claude"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])