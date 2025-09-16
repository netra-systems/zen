#!/usr/bin/env python3
"""
Unit tests for claude-instance-orchestrator.py

Tests the core functionality of the Claude instance orchestrator script
focusing on dataclasses, initialization, and core business logic.
"""

import pytest
import json
import yaml
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict
import sys
import os
from datetime import datetime, timedelta

# Add service directory to path to import the module
service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(service_dir))

from claude_instance_orchestrator import (
    InstanceConfig,
    InstanceStatus,
    ClaudeInstanceOrchestrator,
    parse_start_time,
    create_default_instances
)


class TestInstanceConfig:
    """Test InstanceConfig dataclass functionality"""

    def test_instance_config_basic_creation(self):
        """Test basic InstanceConfig creation"""
        config = InstanceConfig(command="/test-command")

        assert config.command == "/test-command"
        assert config.name == "/test-command"  # Default name
        assert config.description == "Execute /test-command"  # Default description
        assert config.permission_mode == "acceptEdits"
        assert config.output_format == "stream-json"
        assert config.session_id is None
        assert config.clear_history is False
        assert config.compact_history is False
        assert config.pre_commands is None
        assert config.allowed_tools is None

    def test_instance_config_custom_values(self):
        """Test InstanceConfig with custom values"""
        config = InstanceConfig(
            command="/custom-command",
            name="CustomName",
            description="Custom description",
            allowed_tools=["tool1", "tool2"],
            permission_mode="acceptAll",
            output_format="json",
            session_id="test-session",
            clear_history=True,
            compact_history=True,
            pre_commands=["/setup", "/config"]
        )

        assert config.command == "/custom-command"
        assert config.name == "CustomName"
        assert config.description == "Custom description"
        assert config.allowed_tools == ["tool1", "tool2"]
        assert config.permission_mode == "acceptAll"
        assert config.output_format == "json"
        assert config.session_id == "test-session"
        assert config.clear_history is True
        assert config.compact_history is True
        assert config.pre_commands == ["/setup", "/config"]

    def test_instance_config_post_init(self):
        """Test InstanceConfig __post_init__ default value setting"""
        # Test name defaults to command when None
        config = InstanceConfig(command="/test")
        assert config.name == "/test"

        # Test description defaults when None
        assert config.description == "Execute /test"

        # Test custom name is preserved
        config = InstanceConfig(command="/test", name="MyTest")
        assert config.name == "MyTest"
        assert config.description == "Execute /test"


class TestInstanceStatus:
    """Test InstanceStatus dataclass functionality"""

    def test_instance_status_creation(self):
        """Test basic InstanceStatus creation"""
        status = InstanceStatus(name="test-instance")

        assert status.name == "test-instance"
        assert status.pid is None
        assert status.status == "pending"
        assert status.start_time is None
        assert status.end_time is None
        assert status.output == ""
        assert status.error == ""
        assert status.total_tokens == 0
        assert status.input_tokens == 0
        assert status.output_tokens == 0
        assert status.cached_tokens == 0
        assert status.tool_calls == 0

    def test_instance_status_with_values(self):
        """Test InstanceStatus with actual values"""
        status = InstanceStatus(
            name="test-instance",
            pid=12345,
            status="running",
            start_time=1234567890.0,
            end_time=1234567950.0,
            output="Test output",
            error="Test error",
            total_tokens=1000,
            input_tokens=500,
            output_tokens=400,
            cached_tokens=100,
            tool_calls=5
        )

        assert status.name == "test-instance"
        assert status.pid == 12345
        assert status.status == "running"
        assert status.start_time == 1234567890.0
        assert status.end_time == 1234567950.0
        assert status.output == "Test output"
        assert status.error == "Test error"
        assert status.total_tokens == 1000
        assert status.input_tokens == 500
        assert status.output_tokens == 400
        assert status.cached_tokens == 100
        assert status.tool_calls == 5

    def test_instance_status_serialization(self):
        """Test InstanceStatus can be serialized to dict"""
        status = InstanceStatus(
            name="test-instance",
            pid=12345,
            status="completed",
            total_tokens=1000
        )

        status_dict = asdict(status)
        assert isinstance(status_dict, dict)
        assert status_dict["name"] == "test-instance"
        assert status_dict["pid"] == 12345
        assert status_dict["status"] == "completed"
        assert status_dict["total_tokens"] == 1000


class TestClaudeInstanceOrchestratorInit:
    """Test ClaudeInstanceOrchestrator initialization"""

    def setup_method(self):
        """Create temporary workspace for tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up temporary workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_orchestrator_basic_init(self):
        """Test basic orchestrator initialization"""
        orchestrator = ClaudeInstanceOrchestrator(self.workspace)

        assert orchestrator.workspace_dir == self.workspace
        assert isinstance(orchestrator.instances, dict)
        assert isinstance(orchestrator.statuses, dict)
        assert isinstance(orchestrator.processes, dict)
        assert len(orchestrator.instances) == 0
        assert orchestrator.max_console_lines == 5
        assert orchestrator.startup_delay == 1.0
        assert orchestrator.max_line_length == 500
        assert orchestrator.status_report_interval == 30
        assert orchestrator.use_cloud_sql is False
        assert orchestrator.quiet is False
        assert orchestrator.batch_id is not None
        assert len(orchestrator.batch_id) == 36  # UUID length

    def test_orchestrator_custom_init(self):
        """Test orchestrator initialization with custom parameters"""
        orchestrator = ClaudeInstanceOrchestrator(
            workspace_dir=self.workspace,
            max_console_lines=10,
            startup_delay=2.5,
            max_line_length=1000,
            status_report_interval=60,
            use_cloud_sql=True,
            quiet=True
        )

        assert orchestrator.workspace_dir == self.workspace
        assert orchestrator.max_console_lines == 10
        assert orchestrator.startup_delay == 2.5
        assert orchestrator.max_line_length == 1000
        assert orchestrator.status_report_interval == 60
        assert orchestrator.use_cloud_sql is True
        assert orchestrator.quiet is True

    def test_orchestrator_cloud_sql_init(self):
        """Test orchestrator initialization with CloudSQL configuration"""
        with patch.dict(os.environ, {}, clear=True):
            orchestrator = ClaudeInstanceOrchestrator(
                workspace_dir=self.workspace,
                use_cloud_sql=True
            )

            assert orchestrator.use_cloud_sql is True
            # Check that environment variables were set
            assert os.environ.get('POSTGRES_PORT') == '5434'
            assert os.environ.get('POSTGRES_HOST') == 'localhost'
            assert os.environ.get('POSTGRES_DB') == 'netra_optimizer'
            assert os.environ.get('POSTGRES_USER') == 'postgres'
            assert os.environ.get('ENVIRONMENT') == 'staging'

    def test_add_instance(self):
        """Test adding instances to orchestrator"""
        orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        config = InstanceConfig(command="/test-command", name="test-instance")

        orchestrator.add_instance(config)

        assert "test-instance" in orchestrator.instances
        assert "test-instance" in orchestrator.statuses
        assert orchestrator.instances["test-instance"] == config
        assert isinstance(orchestrator.statuses["test-instance"], InstanceStatus)
        assert orchestrator.statuses["test-instance"].name == "test-instance"

    def test_add_multiple_instances(self):
        """Test adding multiple instances"""
        orchestrator = ClaudeInstanceOrchestrator(self.workspace)

        config1 = InstanceConfig(command="/command1", name="instance1")
        config2 = InstanceConfig(command="/command2", name="instance2")

        orchestrator.add_instance(config1)
        orchestrator.add_instance(config2)

        assert len(orchestrator.instances) == 2
        assert len(orchestrator.statuses) == 2
        assert "instance1" in orchestrator.instances
        assert "instance2" in orchestrator.instances


class TestStartTimeParsing:
    """Test start time parsing functionality"""

    def test_parse_relative_time_hours(self):
        """Test parsing relative time in hours"""
        now = datetime.now()
        target = parse_start_time("2h")

        # Should be approximately 2 hours from now (within 1 second tolerance)
        expected = now + timedelta(hours=2)
        assert abs((target - expected).total_seconds()) < 1

    def test_parse_relative_time_minutes(self):
        """Test parsing relative time in minutes"""
        now = datetime.now()
        target = parse_start_time("30m")

        expected = now + timedelta(minutes=30)
        assert abs((target - expected).total_seconds()) < 1

    def test_parse_relative_time_seconds(self):
        """Test parsing relative time in seconds"""
        now = datetime.now()
        target = parse_start_time("45s")

        expected = now + timedelta(seconds=45)
        assert abs((target - expected).total_seconds()) < 1

    def test_parse_fractional_time(self):
        """Test parsing fractional time values"""
        now = datetime.now()
        target = parse_start_time("1.5h")

        expected = now + timedelta(hours=1.5)
        assert abs((target - expected).total_seconds()) < 1

    def test_parse_am_pm_time(self):
        """Test parsing AM/PM time formats"""
        target = parse_start_time("2pm")

        assert target.hour == 14
        assert target.minute == 0

        target = parse_start_time("10am")
        assert target.hour == 10
        assert target.minute == 0

    def test_parse_24_hour_time(self):
        """Test parsing 24-hour time format"""
        target = parse_start_time("14:30")

        assert target.hour == 14
        assert target.minute == 30

    def test_parse_invalid_time(self):
        """Test parsing invalid time formats"""
        with pytest.raises(ValueError):
            parse_start_time("invalid")

        with pytest.raises(ValueError):
            parse_start_time("25:00")

        with pytest.raises(ValueError):
            parse_start_time("abc123")

    def test_parse_empty_time(self):
        """Test parsing empty or None time"""
        now = datetime.now()
        target = parse_start_time("")

        # Should return approximately now
        assert abs((target - now).total_seconds()) < 1

        target = parse_start_time(None)
        assert abs((target - now).total_seconds()) < 1


class TestDefaultInstances:
    """Test default instance creation"""

    def test_create_default_instances(self):
        """Test creating default instances"""
        instances = create_default_instances()

        assert isinstance(instances, list)
        assert len(instances) > 0

        # Check that all instances are InstanceConfig objects
        for instance in instances:
            assert isinstance(instance, InstanceConfig)
            assert instance.command.startswith("/")  # All should be slash commands
            assert instance.permission_mode == "acceptEdits"
            assert instance.output_format == "stream-json"

    def test_create_default_instances_custom_format(self):
        """Test creating default instances with custom output format"""
        instances = create_default_instances(output_format="json")

        assert len(instances) > 0

        # Check that all instances use the custom output format
        for instance in instances:
            assert instance.output_format == "json"

    def test_default_instances_commands(self):
        """Test that default instances contain expected commands"""
        instances = create_default_instances()
        commands = [instance.command for instance in instances]

        # Check for some expected commands
        assert any("/gitcommitgardener" in cmd for cmd in commands)
        assert any("/testgardener" in cmd for cmd in commands)
        assert any("/runtests" in cmd for cmd in commands)
        assert any("/ultimate-test-deploy-loop" in cmd for cmd in commands)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])