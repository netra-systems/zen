#!/usr/bin/env python3
"""
NetraOptimizer - Practical Usage Examples

Run this file to see NetraOptimizer in action!
"""

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch, AsyncMock

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from netraoptimizer import NetraOptimizerClient
from netraoptimizer.analytics import parse_command, extract_features


async def example_1_basic_usage():
    """Example 1: Basic command execution with metrics"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Command Execution")
    print("="*60)

    client = NetraOptimizerClient()

    # Mock the subprocess to avoid calling real Claude
    with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
        mock_process = AsyncMock()
        mock_output = b'''{
            "usage": {
                "input_tokens": 1500,
                "output_tokens": 2000,
                "cache_read_input_tokens": 500000
            },
            "tool_calls": 5,
            "status": "completed",
            "message": "Successfully analyzed issues"
        }'''
        mock_process.communicate = AsyncMock(return_value=(mock_output, b''))
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        # Execute command
        result = await client.run("/gitissueprogressorv3 p0 agents")

        # Display results
        print(f"\nCommand: /gitissueprogressorv3 p0 agents")
        print(f"Status: {result['status']}")
        print(f"\nToken Metrics:")
        print(f"  Total: {result['tokens']['total']:,}")
        print(f"  Input: {result['tokens']['input']:,}")
        print(f"  Output: {result['tokens']['output']:,}")
        print(f"  Cached: {result['tokens']['cached']:,}")
        print(f"  Cache Hit Rate: {result['tokens']['cache_hit_rate']:.1f}%")
        print(f"\nCost Analysis:")
        print(f"  Cost: ${result['cost_usd']:.4f}")
        print(f"  Cache Savings: ${result['cache_savings_usd']:.2f}")
        print(f"\nPerformance:")
        print(f"  Execution Time: {result['execution_time_ms']}ms")
        print(f"  Tool Calls: {result['tool_calls']}")


async def example_2_batch_execution():
    """Example 2: Batch execution with shared context"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Batch Execution")
    print("="*60)

    client = NetraOptimizerClient()
    batch_id = str(uuid4())

    commands = [
        "/gitissueprogressorv3 critical",
        "/gitissueprogressorv3 p0",
        "/gitissueprogressorv3 p1",
        "/createtestsv2 agent unit",
    ]

    print(f"\nBatch ID: {batch_id}")
    print(f"Commands to execute: {len(commands)}")

    results = []
    with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
        # Different token usage for each command to simulate variance
        token_configs = [
            {"input": 2000, "output": 1500, "cached": 100000},
            {"input": 1800, "output": 2200, "cached": 950000},
            {"input": 1500, "output": 1000, "cached": 1200000},
            {"input": 3000, "output": 2500, "cached": 50000},
        ]

        for i, (cmd, tokens) in enumerate(zip(commands, token_configs)):
            mock_process = AsyncMock()
            mock_output = f'''{{
                "usage": {{
                    "input_tokens": {tokens['input']},
                    "output_tokens": {tokens['output']},
                    "cache_read_input_tokens": {tokens['cached']}
                }},
                "status": "completed"
            }}'''.encode()
            mock_process.communicate = AsyncMock(return_value=(mock_output, b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await client.run(
                cmd,
                batch_id=batch_id,
                execution_sequence=i,
                workspace_context={
                    'workspace': '/test/project',
                    'batch_size': len(commands)
                }
            )
            results.append(result)

            print(f"\n[{i+1}/{len(commands)}] {cmd}")
            print(f"  Tokens: {result['tokens']['total']:,}")
            print(f"  Cache Rate: {result['tokens']['cache_hit_rate']:.1f}%")
            print(f"  Cost: ${result['cost_usd']:.4f}")

    # Batch summary
    total_tokens = sum(r['tokens']['total'] for r in results)
    total_cost = sum(r['cost_usd'] for r in results)
    avg_cache_rate = sum(r['tokens']['cache_hit_rate'] for r in results) / len(results)

    print(f"\n{'='*40}")
    print("BATCH SUMMARY")
    print(f"{'='*40}")
    print(f"Total Tokens: {total_tokens:,}")
    print(f"Total Cost: ${total_cost:.4f}")
    print(f"Average Cache Rate: {avg_cache_rate:.1f}%")
    print(f"Commands Executed: {len(results)}")


async def example_3_command_analysis():
    """Example 3: Command parsing and feature extraction"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Command Analysis")
    print("="*60)

    test_commands = [
        "/gitissueprogressorv3 p0 agents critical",
        "/createtestsv2 websocket auth integration",
        "/refreshgardener --force",
        "/deploy staging --rollback",
    ]

    for cmd in test_commands:
        print(f"\n{'='*40}")
        print(f"Command: {cmd}")
        print(f"{'='*40}")

        # Parse command
        parsed = parse_command(cmd)
        print("\nParsed Structure:")
        print(f"  Base: {parsed['base']}")
        print(f"  Targets: {parsed['targets']}")
        if parsed.get('priority'):
            print(f"  Priority: {parsed['priority']}")
        if parsed.get('components'):
            print(f"  Components: {parsed['components']}")
        if parsed['flags']:
            print(f"  Flags: {parsed['flags']}")

        # Extract features
        features = extract_features(cmd)
        print("\nExtracted Features:")
        print(f"  Complexity Score: {features['estimated_complexity']:.1f}/10")
        print(f"  Scope: {features['scope_breadth']}")
        print(f"  Operation Type: {features['operation_type']}")
        print(f"  Cache-Heavy: {features['cache_heavy']}")
        print(f"  Parallel-Friendly: {features['parallel_friendly']}")
        print(f"  High Priority: {features['is_high_priority']}")


async def example_4_error_handling():
    """Example 4: Error handling and failure scenarios"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Error Handling")
    print("="*60)

    client = NetraOptimizerClient()

    # Simulate different failure scenarios
    scenarios = [
        ("Rate limit exceeded", 1, "rate_limit_error"),
        ("Command not found", 127, "command_not_found"),
        ("Timeout", None, "timeout"),
    ]

    for error_msg, return_code, scenario in scenarios:
        print(f"\n[Scenario: {scenario}]")

        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()

            if scenario == "timeout":
                # Simulate timeout
                async def timeout_comm():
                    await asyncio.sleep(2)
                    return (b'', b'')
                mock_process.communicate = timeout_comm
                mock_process.returncode = None
                client.timeout = 0.1  # Set very short timeout
            else:
                # Simulate other errors
                mock_process.communicate = AsyncMock(return_value=(b'', error_msg.encode()))
                mock_process.returncode = return_code

            mock_subprocess.return_value = mock_process

            try:
                result = await client.run(f"/test_{scenario}")
                print(f"  Status: {result['status']}")
                if result.get('error'):
                    print(f"  Error: {result['error']}")
            except asyncio.TimeoutError:
                print(f"  Status: timeout")
                print(f"  Error: Command timed out after {client.timeout}s")

        # Reset timeout
        client.timeout = 600


async def example_5_cost_optimization():
    """Example 5: Cost optimization insights"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Cost Optimization Insights")
    print("="*60)

    client = NetraOptimizerClient()

    # Simulate running the same command with different cache rates
    command = "/gitissueprogressorv3 p0 agents"
    cache_scenarios = [
        ("First Run (No Cache)", 0),
        ("Second Run (Partial Cache)", 500000),
        ("Third Run (Warm Cache)", 2000000),
        ("Fourth Run (Hot Cache)", 5000000),
    ]

    print(f"\nCommand: {command}")
    print("\nCache Warming Effect:")

    for scenario_name, cached_tokens in cache_scenarios:
        with patch('netraoptimizer.client.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_output = f'''{{
                "usage": {{
                    "input_tokens": 2000,
                    "output_tokens": 1500,
                    "cache_read_input_tokens": {cached_tokens}
                }},
                "status": "completed"
            }}'''.encode()
            mock_process.communicate = AsyncMock(return_value=(mock_output, b''))
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            result = await client.run(command)

            cache_rate = result['tokens']['cache_hit_rate']
            cost = result['cost_usd']
            savings = result['cache_savings_usd']

            print(f"\n{scenario_name}:")
            print(f"  Cache Rate: {cache_rate:.1f}%")
            print(f"  Cost: ${cost:.4f}")
            print(f"  Savings: ${savings:.4f}")

    print("\n💡 Insight: Running similar commands sequentially maximizes cache benefits!")


async def main():
    """Run all examples"""
    print("="*60)
    print(" NetraOptimizer - Practical Usage Examples")
    print(" Run Time:", datetime.now(timezone.utc).isoformat())
    print("="*60)

    # Run examples
    await example_1_basic_usage()
    await example_2_batch_execution()
    await example_3_command_analysis()
    await example_4_error_handling()
    await example_5_cost_optimization()

    print("\n" + "="*60)
    print(" Examples Complete!")
    print("="*60)
    print("\n📝 Next Steps:")
    print("1. Set up PostgreSQL database")
    print("2. Run: python netraoptimizer/database/setup.py")
    print("3. Integrate with your orchestrator")
    print("4. Start collecting real metrics!")
    print("\n💡 Pro Tip: Every execution through NetraOptimizer")
    print("   automatically saves metrics to the database for analysis!")


if __name__ == "__main__":
    asyncio.run(main())