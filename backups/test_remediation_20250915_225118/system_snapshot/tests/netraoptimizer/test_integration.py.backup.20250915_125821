"""
Integration tests for NetraOptimizer

These tests verify the complete system works end-to-end.
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from netraoptimizer import NetraOptimizerClient
from netraoptimizer.analytics import parse_command, extract_features


class TestIntegration:
    """Integration tests for the complete NetraOptimizer system."""

    @pytest.mark.asyncio
    async def test_end_to_end_execution(self):
        """Test complete execution flow from command to database."""
        # Create a client
        client = NetraOptimizerClient()

        # Mock the subprocess execution to avoid calling real Claude
        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            # Setup mock process with realistic output
            mock_process = AsyncMock()
            mock_output = b'''{
                "usage": {
                    "input_tokens": 2500,
                    "output_tokens": 1800,
                    "cache_read_input_tokens": 3200000
                },
                "tool_calls": 12,
                "status": "completed",
                "message": "Successfully analyzed GitHub issues"
            }'''
            mock_process.communicate = AsyncMock(return_value=(mock_output, b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            # Execute a realistic command
            result = await client.run(
                "/gitissueprogressorv3 p0 agents",
                workspace_context={
                    "workspace_path": "/test/workspace",
                    "file_count": 500
                }
            )

            # Verify the result structure
            assert result['status'] == 'completed'
            assert result['execution_id'] is not None
            assert result['tokens']['total'] == 2500 + 1800 + 3200000
            assert result['tokens']['cache_hit_rate'] > 99  # High cache rate
            assert result['cost_usd'] > 0
            assert result['tool_calls'] == 12

    def test_command_parser(self):
        """Test the command parser with various commands."""
        test_cases = [
            ("/gitissueprogressorv3 p0 agents", {
                'base': '/gitissueprogressorv3',
                'priority': 'p0',
                'components': ['agents']
            }),
            ("/createtestsv2 agent goldenpath unit", {
                'base': '/createtestsv2',
                'test_type': 'unit',
                'targets': ['agent', 'goldenpath', 'unit']
            }),
            ("/refreshgardener", {
                'base': '/refreshgardener',
                'targets': []
            })
        ]

        for command, expected in test_cases:
            parsed = parse_command(command)
            assert parsed['base'] == expected['base']
            if 'priority' in expected:
                assert parsed['priority'] == expected['priority']
            if 'test_type' in expected:
                assert parsed['test_type'] == expected['test_type']

    def test_feature_extraction(self):
        """Test feature extraction for complexity analysis."""
        command = "/gitissueprogressorv3 p0 agents critical"
        features = extract_features(command)

        # Verify extracted features
        assert features['base_command'] == '/gitissueprogressorv3'
        assert features['is_high_priority'] is True  # p0 is high priority
        assert features['scope_breadth'] in ['narrow', 'medium', 'broad']
        assert features['estimated_complexity'] > 0
        assert features['cache_heavy'] is True  # This command benefits from cache
        assert features['parallel_friendly'] is True

    @pytest.mark.asyncio
    async def test_batch_execution(self):
        """Test batch execution with multiple commands."""
        from uuid import uuid4

        client = NetraOptimizerClient()
        batch_id = str(uuid4())
        commands = [
            "/gitissueprogressorv3 p0",
            "/gitissueprogressorv3 p1",
            "/createtestsv2 unit"
        ]

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b'{"status": "completed"}', b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            results = []
            for i, cmd in enumerate(commands):
                result = await client.run(
                    cmd,
                    batch_id=batch_id,
                    execution_sequence=i
                )
                results.append(result)

            # Verify batch execution
            assert len(results) == 3
            for result in results:
                assert result['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling throughout the system."""
        client = NetraOptimizerClient()

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            # Simulate a failure
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b'', b'Error: Rate limit exceeded'))
            mock_process.returncode = 1
            mock_subprocess.return_value = mock_process

            result = await client.run("/test failing command")

            # Verify error handling
            assert result['status'] == 'failed'
            assert result['error'] == 'Error: Rate limit exceeded'

    @pytest.mark.asyncio
    async def test_cost_calculation(self):
        """Test that costs are calculated correctly."""
        client = NetraOptimizerClient()

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            # High token usage for cost testing
            mock_output = b'''{
                "usage": {
                    "input_tokens": 10000,
                    "output_tokens": 5000,
                    "cache_read_input_tokens": 1000000
                }
            }'''
            mock_process.communicate = AsyncMock(return_value=(mock_output, b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await client.run("/expensive command")

            # Verify cost calculations
            assert result['cost_usd'] > 0
            assert result['cache_savings_usd'] > 0
            # Input: 10K * $0.015/1K = $0.15
            # Output: 5K * $0.075/1K = $0.375
            # Total fresh cost should be ~$0.525
            assert 0.5 < result['cost_usd'] < 0.6