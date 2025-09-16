"""
Claude Code CLI Adapter for NetraOptimizer

This adapter properly interfaces with Claude Code's CLI,
ensuring correct flags and output format for metrics extraction.
"""

import asyncio
import json
import logging
from typing import Tuple, Optional, Dict

logger = logging.getLogger(__name__)


async def execute_claude_command(
    command_raw: str,
    claude_executable: str = "claude",
    timeout: int = 600,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None
) -> Tuple[str, str, int]:
    """
    Execute a Claude Code CLI command with proper flags.

    Args:
        command_raw: The command to execute (e.g., "/gitissueprogressorv3 p0")
        claude_executable: Path to claude executable
        timeout: Command timeout in seconds
        env: Optional environment variables
        cwd: Optional working directory

    Returns:
        Tuple of (stdout, stderr, returncode)
    """
    import os

    # Prepare environment
    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    # Build proper Claude Code CLI command
    cmd_args = [
        claude_executable,
        "-p",  # headless mode (required for programmatic use)
        "--output-format=stream-json",  # JSON output for parsing metrics
        "--permission-mode=acceptEdits",  # Accept edits automatically
        "--verbose"  # Include usage metrics in output
    ]

    # Add the actual command
    # Note: Claude Code CLI expects the command without leading slash in -p mode
    if command_raw.startswith('/'):
        cmd_args.append(command_raw[1:])  # Remove leading slash for -p mode
    else:
        cmd_args.append(command_raw)

    logger.info(f"Executing Claude command: {' '.join(cmd_args)}")

    try:
        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=process_env,
            cwd=cwd
        )

        # Wait for completion with timeout
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )

        # Decode output
        stdout_str = stdout.decode('utf-8') if stdout else ""
        stderr_str = stderr.decode('utf-8') if stderr else ""

        return stdout_str, stderr_str, process.returncode or 0

    except asyncio.TimeoutError:
        # Kill process if it times out
        if 'process' in locals():
            process.kill()
            await process.wait()
        raise


def parse_claude_output(output: str) -> Dict[str, any]:
    """
    Parse Claude Code's stream-json output to extract metrics.

    Args:
        output: The stdout from Claude command

    Returns:
        Dictionary with parsed metrics
    """
    metrics = {
        'input_tokens': 0,
        'output_tokens': 0,
        'cached_tokens': 0,
        'total_tokens': 0,
        'tool_calls': 0
    }

    # Claude Code outputs multiple JSON objects in stream-json format
    # Each line might be a separate JSON object
    for line in output.split('\n'):
        if not line.strip():
            continue

        try:
            data = json.loads(line)

            # Look for usage metrics
            if 'usage' in data:
                usage = data['usage']
                metrics['input_tokens'] = usage.get('input_tokens', 0)
                metrics['output_tokens'] = usage.get('output_tokens', 0)
                metrics['cached_tokens'] = usage.get('cache_read_input_tokens', 0)
                metrics['total_tokens'] = (
                    metrics['input_tokens'] +
                    metrics['output_tokens'] +
                    metrics['cached_tokens']
                )

            # Count tool calls
            if 'tool_calls' in data:
                metrics['tool_calls'] = data.get('tool_calls', 0)
            elif 'tool_use' in data:
                metrics['tool_calls'] += 1

        except json.JSONDecodeError:
            # Not all lines are JSON, skip non-JSON lines
            continue

    return metrics