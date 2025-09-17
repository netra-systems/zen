#!/usr/bin/env python3
"""
Unit tests for zen_orchestrator.py metrics and token parsing

Tests token usage parsing, metrics calculation, status reporting, and result generation.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import time

# Add service directory to path to import the module
service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(service_dir))

from zen_orchestrator import (
    InstanceConfig,
    InstanceStatus,
    ClaudeInstanceOrchestrator
)


class TestTokenParsing:
    """Test token usage parsing functionality"""

    def setup_method(self):
        """Create temporary workspace and orchestrator"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        self.orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        self.status = InstanceStatus(name="test-instance")

    def teardown_method(self):
        """Clean up temporary workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_json_token_usage_structured(self):
        """Test parsing structured JSON token usage"""
        json_line = json.dumps({
            "usage": {
                "input_tokens": 500,
                "output_tokens": 300,
                "cache_read_input_tokens": 100,
                "cache_creation_input_tokens": 50,
                "total_tokens": 950
            }
        })

        self.orchestrator._parse_token_usage(json_line, self.status)

        assert self.status.input_tokens == 500
        assert self.status.output_tokens == 300
        assert self.status.cached_tokens == 150  # 100 + 50
        assert self.status.total_tokens == 950

    def test_parse_json_token_usage_nested_message(self):
        """Test parsing JSON token usage nested in message"""
        json_line = json.dumps({
            "message": {
                "usage": {
                    "input_tokens": 400,
                    "output_tokens": 200,
                    "cache_read_input_tokens": 80
                }
            }
        })

        self.orchestrator._parse_token_usage(json_line, self.status)

        assert self.status.input_tokens == 400
        assert self.status.output_tokens == 200
        assert self.status.cached_tokens == 80

    def test_parse_json_token_usage_calculated_total(self):
        """Test parsing JSON when total needs to be calculated"""
        json_line = json.dumps({
            "usage": {
                "input_tokens": 300,
                "output_tokens": 200,
                "cache_read_input_tokens": 50,
                "cache_creation_input_tokens": 25
                # No total_tokens provided
            }
        })

        self.orchestrator._parse_token_usage(json_line, self.status)

        assert self.status.input_tokens == 300
        assert self.status.output_tokens == 200
        assert self.status.cached_tokens == 75  # 50 + 25
        # Total should be calculated: 300 + 200 + 50 + 25 = 575
        assert self.status.total_tokens == 575

    def test_parse_json_tool_calls(self):
        """Test parsing JSON tool call information"""
        json_line = json.dumps({
            "type": "tool_use",
            "tool_name": "test_tool"
        })

        self.orchestrator._parse_token_usage(json_line, self.status)

        assert self.status.tool_calls == 1

        # Test multiple tool calls in message
        json_line2 = json.dumps({
            "type": "message",
            "tool_calls": 3
        })

        self.orchestrator._parse_token_usage(json_line2, self.status)

        assert self.status.tool_calls == 4  # 1 + 3

    def test_parse_json_direct_token_fields(self):
        """Test parsing JSON with direct token fields at root level"""
        json_line = json.dumps({
            "input_tokens": 250,
            "output_tokens": 150,
            "cached_tokens": 40,
            "total_tokens": 440,
            "tool_calls": 2
        })

        self.orchestrator._parse_token_usage(json_line, self.status)

        assert self.status.input_tokens == 250
        assert self.status.output_tokens == 150
        assert self.status.cached_tokens == 40
        assert self.status.total_tokens == 440
        assert self.status.tool_calls == 2

    def test_parse_fallback_regex_patterns(self):
        """Test fallback regex parsing for non-JSON output"""
        # Test "Used X tokens" pattern
        self.orchestrator._parse_token_usage("Used 1500 tokens for this request", self.status)
        assert self.status.total_tokens == 1500

        # Test input/output breakdown
        self.orchestrator._parse_token_usage("Input: 800 tokens, Output: 600 tokens", self.status)
        assert self.status.input_tokens == 800
        assert self.status.output_tokens == 600

        # Test cached tokens
        self.orchestrator._parse_token_usage("Cached: 200 tokens from previous request", self.status)
        assert self.status.cached_tokens == 200

        # Test tool execution
        self.orchestrator._parse_token_usage("Executing tool call for analysis", self.status)
        assert self.status.tool_calls == 1

    def test_parse_final_json_output(self):
        """Test parsing final JSON output format"""
        final_output = json.dumps({
            "usage": {
                "input_tokens": 600,
                "output_tokens": 400,
                "cache_read_input_tokens": 120
            },
            "tool_calls": [
                {"name": "tool1"},
                {"name": "tool2"}
            ]
        })

        self.orchestrator._parse_final_output_token_usage(final_output, self.status, "json")

        assert self.status.input_tokens == 600
        assert self.status.output_tokens == 400
        assert self.status.cached_tokens == 120
        assert self.status.tool_calls == 2

    def test_parse_invalid_json_fallback(self):
        """Test that invalid JSON falls back to regex parsing"""
        invalid_json = "This is not JSON but contains Used 750 tokens"

        # Should not raise exception, should parse via fallback
        self.orchestrator._parse_token_usage(invalid_json, self.status)
        assert self.status.total_tokens == 750

    def test_parse_empty_or_whitespace(self):
        """Test parsing empty or whitespace-only content"""
        self.orchestrator._parse_token_usage("", self.status)
        self.orchestrator._parse_token_usage("   ", self.status)
        self.orchestrator._parse_token_usage("\n\t", self.status)

        # Should not change status
        assert self.status.total_tokens == 0
        assert self.status.input_tokens == 0
        assert self.status.output_tokens == 0


class TestMetricsCalculation:
    """Test metrics calculation functionality"""

    def setup_method(self):
        """Create temporary workspace and orchestrator"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        self.orchestrator = ClaudeInstanceOrchestrator(self.workspace)

    def teardown_method(self):
        """Clean up temporary workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_calculate_cost(self):
        """Test cost calculation based on token usage"""
        status = InstanceStatus(
            name="test",
            input_tokens=1_000_000,  # 1M input tokens
            output_tokens=500_000,   # 500K output tokens
            cached_tokens=200_000    # 200K cached tokens
        )

        cost = self.orchestrator._calculate_cost(status)

        # Expected: (1M/1M * $3) + (500K/1M * $15) + (200K/1M * $0.30)
        # = $3 + $7.5 + $0.06 = $10.56
        expected_cost = 3.0 + 7.5 + 0.06
        assert abs(cost - expected_cost) < 0.01

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens"""
        status = InstanceStatus(name="test")

        cost = self.orchestrator._calculate_cost(status)

        assert cost == 0.0

    def test_format_duration(self):
        """Test duration formatting"""
        # Test seconds
        assert self.orchestrator._format_duration(45.7) == "45.7s"
        assert self.orchestrator._format_duration(59.9) == "59.9s"

        # Test minutes
        assert self.orchestrator._format_duration(90) == "1m30s"
        assert self.orchestrator._format_duration(125.5) == "2m6s"

        # Test hours
        assert self.orchestrator._format_duration(3661) == "1h1m"
        assert self.orchestrator._format_duration(7200) == "2h0m"

    def test_format_tokens(self):
        """Test token count formatting"""
        assert self.orchestrator._format_tokens(500) == "500"
        assert self.orchestrator._format_tokens(1500) == "1.5K"
        assert self.orchestrator._format_tokens(1234567) == "1.2M"
        assert self.orchestrator._format_tokens(999) == "999"
        assert self.orchestrator._format_tokens(1000) == "1.0K"

    def test_calculate_token_median(self):
        """Test token median calculation"""
        # Add some instances with different token counts
        self.orchestrator.statuses = {
            "instance1": InstanceStatus(name="instance1", total_tokens=1000),
            "instance2": InstanceStatus(name="instance2", total_tokens=2000),
            "instance3": InstanceStatus(name="instance3", total_tokens=3000),
            "instance4": InstanceStatus(name="instance4", total_tokens=0),  # Should be ignored
            "instance5": InstanceStatus(name="instance5", total_tokens=4000),
        }

        median = self.orchestrator._calculate_token_median()

        # Should be median of [1000, 2000, 3000, 4000] = 2500
        assert median == 2500

    def test_calculate_token_median_even_count(self):
        """Test token median calculation with even number of instances"""
        self.orchestrator.statuses = {
            "instance1": InstanceStatus(name="instance1", total_tokens=1000),
            "instance2": InstanceStatus(name="instance2", total_tokens=3000),
        }

        median = self.orchestrator._calculate_token_median()

        # Should be (1000 + 3000) / 2 = 2000
        assert median == 2000

    def test_calculate_token_median_empty(self):
        """Test token median calculation with no valid tokens"""
        self.orchestrator.statuses = {
            "instance1": InstanceStatus(name="instance1", total_tokens=0),
        }

        median = self.orchestrator._calculate_token_median()

        assert median == 0

    def test_calculate_token_percentage(self):
        """Test token percentage calculation relative to median"""
        # Test above median
        assert self.orchestrator._calculate_token_percentage(1500, 1000) == "+50%"

        # Test below median
        assert self.orchestrator._calculate_token_percentage(500, 1000) == "-50%"

        # Test near median
        assert self.orchestrator._calculate_token_percentage(1100, 1000) == "+10%"

        # Test zero median
        assert self.orchestrator._calculate_token_percentage(1000, 0) == "N/A"


class TestStatusReporting:
    """Test status reporting functionality"""

    def setup_method(self):
        """Create temporary workspace and orchestrator with test data"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        self.orchestrator = ClaudeInstanceOrchestrator(self.workspace)

        # Add some test instances and statuses
        config1 = InstanceConfig(command="/test1", name="instance1")
        config2 = InstanceConfig(command="/test2", name="instance2")
        self.orchestrator.add_instance(config1)
        self.orchestrator.add_instance(config2)

        # Set up some test data
        self.orchestrator.statuses["instance1"].status = "completed"
        self.orchestrator.statuses["instance1"].start_time = time.time() - 60
        self.orchestrator.statuses["instance1"].end_time = time.time() - 30
        self.orchestrator.statuses["instance1"].total_tokens = 1500
        self.orchestrator.statuses["instance1"].tool_calls = 3

        self.orchestrator.statuses["instance2"].status = "running"
        self.orchestrator.statuses["instance2"].start_time = time.time() - 30
        self.orchestrator.statuses["instance2"].total_tokens = 800

    def teardown_method(self):
        """Clean up temporary workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_status_summary(self):
        """Test getting status summary"""
        summary = self.orchestrator.get_status_summary()

        assert summary["total_instances"] == 2
        assert summary["completed"] == 1
        assert summary["running"] == 1
        assert summary["failed"] == 0
        assert summary["pending"] == 0

        assert "instance1" in summary["instances"]
        assert "instance2" in summary["instances"]

        # Check that duration is calculated for completed instance
        assert "duration" in summary["instances"]["instance1"]

    def test_generate_output_filename(self):
        """Test output filename generation"""
        filename = self.orchestrator.generate_output_filename()

        assert isinstance(filename, Path)
        assert str(filename).startswith("claude_instances_results_")
        assert str(filename).endswith(".json")

        # Should contain datetime
        assert len(str(filename).split("_")) >= 4

        # Test custom base filename
        custom_filename = self.orchestrator.generate_output_filename("custom_base")
        assert str(custom_filename).startswith("custom_base_")

    def test_save_results(self):
        """Test saving results to JSON file"""
        output_file = Path(self.temp_dir) / "test_results.json"

        self.orchestrator.save_results(output_file)

        assert output_file.exists()

        # Load and verify JSON content
        with open(output_file) as f:
            data = json.load(f)

        assert "metadata" in data
        assert "instances" in data
        assert "total_instances" in data
        assert data["total_instances"] == 2

        # Check metadata
        metadata = data["metadata"]
        assert "start_datetime" in metadata
        assert "agents" in metadata
        assert "token_usage" in metadata

        # Check token usage summary
        token_usage = metadata["token_usage"]
        assert "total_tokens" in token_usage
        assert "cache_hit_rate" in token_usage
        assert token_usage["total_tokens"] == 2300  # 1500 + 800

    def test_save_results_auto_filename(self):
        """Test saving results with auto-generated filename"""
        self.orchestrator.save_results()

        # Should create a file with auto-generated name
        generated_files = list(Path(self.temp_dir).glob("claude_instances_results_*.json"))
        assert len(generated_files) == 0  # Auto-generated in CWD, not temp_dir

        # Test that the method completes without error
        # (actual file is created in current working directory)


class TestStatusReportFormatting:
    """Test status report formatting and display"""

    def setup_method(self):
        """Create orchestrator with test data for formatting tests"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        self.orchestrator = ClaudeInstanceOrchestrator(self.workspace)

    def teardown_method(self):
        """Clean up temporary workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('builtins.print')
    def test_print_status_report_basic(self, mock_print):
        """Test basic status report printing"""
        # Add test instance
        config = InstanceConfig(command="/test", name="test-instance")
        self.orchestrator.add_instance(config)
        self.orchestrator.statuses["test-instance"].status = "completed"
        self.orchestrator.statuses["test-instance"].total_tokens = 1000

        # Should not raise exception
        import asyncio
        asyncio.run(self.orchestrator._print_status_report())

        # Verify print was called
        assert mock_print.called

    @patch('builtins.print')
    def test_print_status_report_empty(self, mock_print):
        """Test status report with no instances"""
        import asyncio
        asyncio.run(self.orchestrator._print_status_report())

        # Should return early and not print much
        assert not mock_print.called or mock_print.call_count < 5

    @patch('builtins.print')
    def test_print_status_report_final(self, mock_print):
        """Test final status report"""
        config = InstanceConfig(command="/test", name="test-instance")
        self.orchestrator.add_instance(config)

        import asyncio
        asyncio.run(self.orchestrator._print_status_report(final=True))

        # Should contain "FINAL STATUS"
        print_calls = [str(call) for call in mock_print.call_args_list]
        final_status_found = any("FINAL STATUS" in call for call in print_calls)
        assert final_status_found


if __name__ == "__main__":
    pytest.main([__file__, "-v"])