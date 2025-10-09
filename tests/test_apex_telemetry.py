"""Tests for apex telemetry tracking."""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import zen module
sys.path.insert(0, str(Path(__file__).parent.parent))

from zen.telemetry.apex_telemetry import ApexTelemetryWrapper


class TestApexTelemetryWrapper:
    """Test suite for ApexTelemetryWrapper."""

    def test_extract_message_with_long_flag(self):
        """Test extracting message from --message flag."""
        wrapper = ApexTelemetryWrapper()
        argv = ["--message", "test message", "--env", "staging"]
        message = wrapper._extract_message(argv)
        assert message == "test message"

    def test_extract_message_with_short_flag(self):
        """Test extracting message from -m flag."""
        wrapper = ApexTelemetryWrapper()
        argv = ["-m", "another test", "--env", "production"]
        message = wrapper._extract_message(argv)
        assert message == "another test"

    def test_extract_message_default(self):
        """Test default message when no flag present."""
        wrapper = ApexTelemetryWrapper()
        argv = ["--env", "staging"]
        message = wrapper._extract_message(argv)
        assert message == "apex-instance"

    def test_extract_env_with_flag(self):
        """Test extracting environment from --env flag."""
        wrapper = ApexTelemetryWrapper()
        argv = ["--message", "test", "--env", "production"]
        env = wrapper._extract_env(argv)
        assert env == "production"

    def test_extract_env_default(self):
        """Test default environment when no flag present."""
        wrapper = ApexTelemetryWrapper()
        argv = ["--message", "test"]
        env = wrapper._extract_env(argv)
        assert env == "staging"

    def test_truncate_message_short(self):
        """Test that short messages are not truncated."""
        wrapper = ApexTelemetryWrapper()
        message = "short message"
        truncated = wrapper._truncate_message(message)
        assert truncated == "short message"

    def test_truncate_message_long(self):
        """Test that long messages are truncated."""
        wrapper = ApexTelemetryWrapper()
        message = "x" * 300
        truncated = wrapper._truncate_message(message, max_length=200)
        assert len(truncated) == 203  # 200 + "..."
        assert truncated.endswith("...")

    def test_parse_json_output_valid(self):
        """Test parsing valid JSON output."""
        wrapper = ApexTelemetryWrapper()
        wrapper.stdout = 'Some text\n{"run_id": "123", "status": "success"}\nMore text'
        result = wrapper._parse_json_output()
        assert result is not None
        assert result["run_id"] == "123"
        assert result["status"] == "success"

    def test_parse_json_output_invalid(self):
        """Test parsing invalid JSON output."""
        wrapper = ApexTelemetryWrapper()
        wrapper.stdout = "No JSON here\nJust plain text"
        result = wrapper._parse_json_output()
        assert result is None

    def test_add_json_metrics_usage(self):
        """Test adding usage metrics from JSON output."""
        wrapper = ApexTelemetryWrapper()
        attributes = {}
        json_output = {
            "usage": {
                "total_tokens": 1000,
                "input_tokens": 600,
                "output_tokens": 400,
                "cache_read_tokens": 100,
                "cache_creation_tokens": 50
            }
        }
        wrapper._add_json_metrics(attributes, json_output)

        assert attributes["zen.tokens.total"] == 1000
        assert attributes["zen.tokens.input"] == 600
        assert attributes["zen.tokens.output"] == 400
        assert attributes["zen.tokens.cache.read"] == 100
        assert attributes["zen.tokens.cache.creation"] == 50

    def test_add_json_metrics_cost(self):
        """Test adding cost metrics from JSON output."""
        wrapper = ApexTelemetryWrapper()
        attributes = {}
        json_output = {
            "cost": {
                "total_usd": 0.123456789
            }
        }
        wrapper._add_json_metrics(attributes, json_output)

        assert "zen.cost.usd_total" in attributes
        assert attributes["zen.cost.usd_total"] == 0.123457  # Rounded to 6 decimals

    def test_add_json_metrics_run_id(self):
        """Test adding run_id from JSON output."""
        wrapper = ApexTelemetryWrapper()
        attributes = {}
        json_output = {
            "run_id": "test-run-123"
        }
        wrapper._add_json_metrics(attributes, json_output)

        assert attributes["zen.apex.run_id"] == "test-run-123"

    def test_add_json_metrics_validation(self):
        """Test adding validation status from JSON output."""
        wrapper = ApexTelemetryWrapper()
        attributes = {}
        json_output = {
            "validation": {
                "passed": True
            }
        }
        wrapper._add_json_metrics(attributes, json_output)

        assert attributes["zen.apex.validation.passed"] is True

    @patch('subprocess.run')
    def test_run_apex_with_telemetry_success(self, mock_run):
        """Test running apex with successful execution."""
        # Mock subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Success output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        wrapper = ApexTelemetryWrapper()

        # Mock telemetry emission
        with patch.object(wrapper, '_emit_telemetry') as mock_emit:
            exit_code = wrapper.run_apex_with_telemetry(
                "/path/to/agent_cli.py",
                ["--message", "test", "--env", "staging"],
                env={}
            )

            assert exit_code == 0
            assert wrapper.message == "test"
            assert wrapper.env == "staging"
            assert wrapper.exit_code == 0
            mock_emit.assert_called_once()

    @patch('subprocess.run')
    def test_run_apex_with_telemetry_failure(self, mock_run):
        """Test running apex with failed execution."""
        # Mock subprocess result
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error output"
        mock_run.return_value = mock_result

        wrapper = ApexTelemetryWrapper()

        # Mock telemetry emission
        with patch.object(wrapper, '_emit_telemetry') as mock_emit:
            exit_code = wrapper.run_apex_with_telemetry(
                "/path/to/agent_cli.py",
                ["--message", "test"],
                env={}
            )

            assert exit_code == 1
            assert wrapper.exit_code == 1
            mock_emit.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
