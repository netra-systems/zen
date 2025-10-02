#!/usr/bin/env python3
"""
Regression tests for tool token cache tracking (Issue #15)

Tests that tool usage includes cache_read and cache_creation tokens in both
parsing and display, ensuring consistency with command token metrics.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
from io import StringIO

# Add service directory to path to import the module
service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(service_dir))

from zen_orchestrator import (
    InstanceConfig,
    InstanceStatus,
    ClaudeInstanceOrchestrator
)


class TestToolCacheTokens:
    """Test tool token cache tracking functionality"""

    def setup_method(self):
        """Create temporary workspace and orchestrator"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)
        self.orchestrator = ClaudeInstanceOrchestrator(self.workspace)
        self.status = InstanceStatus(name="test-instance")

    def teardown_method(self):
        """Clean up temporary workspace"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tool_token_structured_breakdown_initialization(self):
        """Test that tool tokens are initialized with structured breakdown"""
        tool_name = "Task"
        breakdown = self.status.get_tool_token_breakdown(tool_name)

        assert isinstance(breakdown, dict)
        assert breakdown['input'] == 0
        assert breakdown['output'] == 0
        assert breakdown['cache_read'] == 0
        assert breakdown['cache_creation'] == 0
        assert breakdown['total'] == 0

    def test_parse_tool_with_cache_tokens(self):
        """Test parsing tool usage with cache tokens from SDK format"""
        json_line = json.dumps({
            "type": "tool_use",
            "name": "Bash",
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_read_input_tokens": 200,
                "cache_creation_input_tokens": 100,
                "total_tokens": 1800
            }
        })

        self.orchestrator._try_parse_json_token_usage(json_line, self.status)

        assert "Bash" in self.status.tool_details
        assert self.status.tool_details["Bash"] == 1

        breakdown = self.status.tool_tokens["Bash"]
        assert breakdown['input'] == 1000
        assert breakdown['output'] == 500
        assert breakdown['cache_read'] == 200
        assert breakdown['cache_creation'] == 100
        assert breakdown['total'] == 1800

    def test_parse_tool_without_total_calculates_correctly(self):
        """Test that total is calculated when SDK omits it"""
        json_line = json.dumps({
            "type": "tool_use",
            "name": "Read",
            "usage": {
                "input_tokens": 800,
                "output_tokens": 400,
                "cache_read_input_tokens": 150,
                "cache_creation_input_tokens": 50
                # No total_tokens provided
            }
        })

        self.orchestrator._try_parse_json_token_usage(json_line, self.status)

        breakdown = self.status.tool_tokens["Read"]
        assert breakdown['total'] == 1400  # 800 + 400 + 150 + 50

    def test_parse_multiple_tool_calls_accumulate_tokens(self):
        """Test that multiple calls to same tool accumulate tokens correctly"""
        # First call
        json_line1 = json.dumps({
            "type": "tool_use",
            "name": "Write",
            "usage": {
                "input_tokens": 500,
                "output_tokens": 200,
                "cache_read_input_tokens": 50,
                "cache_creation_input_tokens": 25
            }
        })
        self.orchestrator._try_parse_json_token_usage(json_line1, self.status)

        # Second call to same tool
        json_line2 = json.dumps({
            "type": "tool_use",
            "name": "Write",
            "usage": {
                "input_tokens": 300,
                "output_tokens": 100,
                "cache_read_input_tokens": 30,
                "cache_creation_input_tokens": 15
            }
        })
        self.orchestrator._try_parse_json_token_usage(json_line2, self.status)

        breakdown = self.status.tool_tokens["Write"]
        assert breakdown['input'] == 800  # 500 + 300
        assert breakdown['output'] == 300  # 200 + 100
        assert breakdown['cache_read'] == 80  # 50 + 30
        assert breakdown['cache_creation'] == 40  # 25 + 15
        assert breakdown['total'] == 1220  # Sum of all

    def test_tool_usage_details_display_cache_columns(self):
        """Test that Tool Usage Details table shows cache columns"""
        # Setup test data
        self.orchestrator.statuses["instance1"] = InstanceStatus(name="instance1")
        status1 = self.orchestrator.statuses["instance1"]

        # Add tool with cache tokens
        status1.tool_details["Task"] = 3
        status1.tool_tokens["Task"] = {
            'input': 1000,
            'output': 500,
            'cache_read': 200,
            'cache_creation': 100,
            'total': 1800
        }

        # Capture output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            self.orchestrator.display_status()

        output = captured_output.getvalue()

        # Check for cache columns in header
        assert "Cache Cr" in output
        assert "Cache Rd" in output
        assert "Overall" in output

        # Check that values are displayed
        assert "200" in output  # cache_read
        assert "100" in output  # cache_creation

    def test_tool_usage_sorted_by_total_tokens(self):
        """Test that tools are sorted by total token usage"""
        self.orchestrator.statuses["instance1"] = InstanceStatus(name="instance1")
        status1 = self.orchestrator.statuses["instance1"]

        # Add multiple tools with different totals
        status1.tool_details["SmallTool"] = 1
        status1.tool_tokens["SmallTool"] = {
            'input': 100, 'output': 50, 'cache_read': 0,
            'cache_creation': 0, 'total': 150
        }

        status1.tool_details["LargeTool"] = 1
        status1.tool_tokens["LargeTool"] = {
            'input': 5000, 'output': 2000, 'cache_read': 500,
            'cache_creation': 250, 'total': 7750
        }

        status1.tool_details["MediumTool"] = 1
        status1.tool_tokens["MediumTool"] = {
            'input': 1000, 'output': 500, 'cache_read': 100,
            'cache_creation': 50, 'total': 1650
        }

        # Capture output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            self.orchestrator.display_status()

        output = captured_output.getvalue()
        lines = output.split('\n')

        # Find tool lines
        tool_lines = []
        in_tool_section = False
        for line in lines:
            if "TOOL USAGE DETAILS" in line:
                in_tool_section = True
            elif in_tool_section and line.startswith('|') and not line.startswith('| -'):
                if 'Tool Name' not in line and 'TOTAL' not in line:
                    tool_lines.append(line)

        # Tools should be in order: LargeTool, MediumTool, SmallTool
        assert len(tool_lines) >= 3
        assert "LargeTool" in tool_lines[0]
        assert "MediumTool" in tool_lines[1]
        assert "SmallTool" in tool_lines[2]

    def test_calculate_cost_with_structured_tool_tokens(self):
        """Test that _calculate_cost handles structured tool tokens correctly"""
        self.status.input_tokens = 1000
        self.status.output_tokens = 500
        self.status.cache_read_tokens = 100
        self.status.cache_creation_tokens = 50

        # Add tool with structured tokens
        self.status.tool_tokens["Task"] = {
            'input': 200,
            'output': 100,
            'cache_read': 20,
            'cache_creation': 10,
            'total': 330
        }

        cost = self.orchestrator._calculate_cost(self.status)

        # Verify cost includes tool cache tokens
        # Base: input=$3/M, output=$15/M, cache_read=$0.30/M, cache_creation=$3.75/M
        expected_input = (1000 / 1_000_000) * 3.00
        expected_output = (500 / 1_000_000) * 15.00
        expected_cache_read = (100 / 1_000_000) * 0.30
        expected_cache_creation = (50 / 1_000_000) * 3.75

        # Tool costs
        expected_tool_input = (200 / 1_000_000) * 3.00
        expected_tool_output = (100 / 1_000_000) * 15.00
        expected_tool_cache_read = (20 / 1_000_000) * 0.30
        expected_tool_cache_creation = (10 / 1_000_000) * 3.75

        expected_total = (expected_input + expected_output + expected_cache_read +
                         expected_cache_creation + expected_tool_input + expected_tool_output +
                         expected_tool_cache_read + expected_tool_cache_creation)

        assert abs(cost - expected_total) < 0.0001  # Allow for float precision

    def test_legacy_tool_token_format_compatibility(self):
        """Test that legacy flat token format is still handled"""
        json_line = json.dumps({
            "type": "tool_use",
            "name": "LegacyTool",
            "tokens": 500  # Old flat format
        })

        self.orchestrator._try_parse_json_token_usage(json_line, self.status)

        breakdown = self.status.tool_tokens["LegacyTool"]
        assert breakdown['input'] == 500  # Legacy assumed as input
        assert breakdown['output'] == 0
        assert breakdown['cache_read'] == 0
        assert breakdown['cache_creation'] == 0
        assert breakdown['total'] == 500

    def test_tool_calls_in_message_with_cache(self):
        """Test parsing tool_calls array in message with cache tokens"""
        json_line = json.dumps({
            "type": "message",
            "tool_calls": [
                {
                    "name": "Grep",
                    "usage": {
                        "input_tokens": 400,
                        "output_tokens": 200,
                        "cache_read_input_tokens": 50,
                        "cache_creation_input_tokens": 25
                    }
                }
            ]
        })

        self.orchestrator._try_parse_json_token_usage(json_line, self.status)

        assert "Grep" in self.status.tool_details
        breakdown = self.status.tool_tokens["Grep"]
        assert breakdown['input'] == 400
        assert breakdown['output'] == 200
        assert breakdown['cache_read'] == 50
        assert breakdown['cache_creation'] == 25
        assert breakdown['total'] == 675


if __name__ == "__main__":
    pytest.main([__file__, "-v"])