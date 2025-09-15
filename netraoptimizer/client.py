"""
NetraOptimizer Client - The Core Instrumented Execution Client

This is the CRITICAL component of the NetraOptimizer system.
It encapsulates all logic for running a command and persisting its data.
ALL interactions with Claude Code MUST go through this client.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from uuid import UUID, uuid4

from .config import config
from .cloud_config import cloud_config
from .database import DatabaseClient, ExecutionRecord

logger = logging.getLogger(__name__)


class NetraOptimizerClient:
    """
    The centralized, instrumented client for all Claude Code interactions.
    This client ensures every execution is automatically measured and optimized.
    """

    def __init__(
        self,
        database_client: Optional[DatabaseClient] = None,
        timeout: Optional[int] = None,
        claude_executable: Optional[str] = None,
        use_cloud_sql: bool = None
    ):
        """
        Initialize the NetraOptimizerClient.

        Args:
            database_client: Optional DatabaseClient instance
            timeout: Command timeout in seconds
            claude_executable: Path to claude executable
            use_cloud_sql: If True, use CloudSQL configuration. If None, auto-detect
        """
        # Initialize database client with CloudSQL support
        if database_client is None:
            database_client = DatabaseClient(use_cloud_sql=use_cloud_sql)
        self.database_client = database_client

        self.timeout = timeout or config.claude_timeout
        self.claude_executable = claude_executable or config.claude_executable

    async def run(
        self,
        command_raw: str,
        batch_id: Optional[str] = None,
        execution_sequence: Optional[int] = None,
        workspace_context: Optional[Dict[str, Any]] = None,
        session_context: Optional[Dict[str, Any]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a Claude Code command and persist all metrics.

        This is the PRIMARY method that orchestrates the entire data collection process:
        1. Record start_time
        2. Construct and execute the claude subprocess
        3. Record end_time and status
        4. Parse output for token metrics
        5. Populate ExecutionRecord
        6. Persist to database
        7. Return result to caller

        Args:
            command_raw: The complete command string to execute
            batch_id: Optional batch identifier for grouped commands
            execution_sequence: Optional sequence number within batch
            workspace_context: Optional workspace state information
            session_context: Optional session state information
            env: Optional environment variables
            cwd: Optional working directory

        Returns:
            Dictionary containing execution results and metrics
        """
        # Initialize execution record
        execution_id = uuid4()
        start_time = datetime.now(timezone.utc)
        start_time_ms = time.perf_counter() * 1000

        # Extract command base
        command_base = self._extract_command_base(command_raw)

        # Create initial execution record
        record = ExecutionRecord(
            id=execution_id,
            timestamp=start_time,
            batch_id=UUID(batch_id) if batch_id else None,
            execution_sequence=execution_sequence,
            command_raw=command_raw,
            command_base=command_base,
            workspace_context=workspace_context,
            session_context=session_context,
            status="pending"
        )

        try:
            # Execute the command
            output, error, returncode = await self._execute_subprocess(
                command_raw, env, cwd
            )

            # Calculate execution time
            end_time_ms = time.perf_counter() * 1000
            execution_time_ms = int(end_time_ms - start_time_ms)
            record.execution_time_ms = execution_time_ms

            # Parse output and update record
            if returncode == 0:
                self._parse_output(output, record)
                record.status = "completed"
            else:
                record.status = "failed"
                record.error_message = error or "Command failed with non-zero exit code"

        except asyncio.TimeoutError:
            # Handle timeout
            end_time_ms = time.perf_counter() * 1000
            record.execution_time_ms = int(end_time_ms - start_time_ms)
            record.status = "timeout"
            record.error_message = f"Command timed out after {self.timeout} seconds"

            # Re-raise for test compatibility
            await self._persist_record(record)
            raise

        except Exception as e:
            # Handle unexpected errors
            end_time_ms = time.perf_counter() * 1000
            record.execution_time_ms = int(end_time_ms - start_time_ms)
            record.status = "failed"
            record.error_message = str(e)
            logger.error(f"Unexpected error executing command: {e}")

        # Calculate derived metrics
        record.calculate_derived_metrics()

        # Persist to database
        await self._persist_record(record)

        # Return formatted result
        return self._format_result(record)

    async def _execute_subprocess(
        self,
        command_raw: str,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> Tuple[str, str, int]:
        """
        Execute the Claude subprocess and capture output.

        Args:
            command_raw: The command to execute
            env: Optional environment variables
            cwd: Optional working directory

        Returns:
            Tuple of (stdout, stderr, returncode)
        """
        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        # Prepare command arguments
        cmd_args = [self.claude_executable]

        # Parse command - remove leading slash if present
        if command_raw.startswith('/'):
            command_raw = command_raw[1:]

        # Add command and its arguments
        cmd_args.extend(command_raw.split())

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
                timeout=self.timeout
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

    def _extract_command_base(self, command_raw: str) -> str:
        """
        Extract the base command from the full command string.

        Args:
            command_raw: The complete command string

        Returns:
            The base command without arguments
        """
        # Remove leading/trailing whitespace
        command = command_raw.strip()

        # Handle commands starting with slash
        if command.startswith('/'):
            # Extract first word (the command itself)
            parts = command.split()
            if parts:
                return parts[0]

        # For other commands, extract first word
        parts = command.split()
        if parts:
            return parts[0]

        return command

    def _parse_output(self, output: str, record: ExecutionRecord) -> None:
        """
        Parse the command output to extract token metrics.

        Args:
            output: The command stdout
            record: The ExecutionRecord to update
        """
        try:
            # Try to parse as JSON (stream-json format)
            data = json.loads(output)

            # Extract usage metrics
            if 'usage' in data:
                usage = data['usage']
                record.input_tokens = usage.get('input_tokens', 0)
                record.output_tokens = usage.get('output_tokens', 0)
                record.cached_tokens = usage.get('cache_read_input_tokens', 0)

                # Calculate total tokens
                record.total_tokens = (
                    record.input_tokens +
                    record.output_tokens +
                    record.cached_tokens
                )

            # Extract tool calls
            if 'tool_calls' in data:
                record.tool_calls = data['tool_calls']

            # Extract any output characteristics
            if 'message' in data:
                record.output_characteristics = {
                    'message': data['message']
                }

        except json.JSONDecodeError:
            # If not JSON, try to extract metrics from text output
            logger.debug("Output is not JSON, attempting text parsing")
            self._parse_text_output(output, record)

    def _parse_text_output(self, output: str, record: ExecutionRecord) -> None:
        """
        Parse text output for token metrics (fallback parser).

        Args:
            output: The command stdout as text
            record: The ExecutionRecord to update
        """
        # Look for common patterns in text output
        lines = output.split('\n')
        for line in lines:
            line_lower = line.lower()

            # Look for token counts
            if 'tokens' in line_lower:
                # Extract numbers from the line
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    # Assume first number is token count
                    try:
                        tokens = int(numbers[0])
                        if 'input' in line_lower:
                            record.input_tokens = tokens
                        elif 'output' in line_lower:
                            record.output_tokens = tokens
                        elif 'total' in line_lower:
                            record.total_tokens = tokens
                        elif 'cached' in line_lower or 'cache' in line_lower:
                            record.cached_tokens = tokens
                    except (ValueError, IndexError):
                        pass

    async def _persist_record(self, record: ExecutionRecord) -> None:
        """
        Persist the execution record to the database.

        Args:
            record: The ExecutionRecord to persist
        """
        try:
            success = await self.database_client.insert_execution(record)
            if not success:
                logger.error(f"Failed to persist execution record: {record.id}")
        except Exception as e:
            logger.error(f"Error persisting record: {e}")

    def _format_result(self, record: ExecutionRecord) -> Dict[str, Any]:
        """
        Format the execution record as a result dictionary.

        Args:
            record: The ExecutionRecord to format

        Returns:
            Dictionary containing execution results
        """
        return {
            'status': record.status,
            'execution_id': str(record.id),
            'command': record.command_raw,
            'tokens': {
                'total': record.total_tokens,
                'input': record.input_tokens,
                'output': record.output_tokens,
                'cached': record.cached_tokens,
                'fresh': record.fresh_tokens,
                'cache_hit_rate': record.cache_hit_rate
            },
            'execution_time_ms': record.execution_time_ms,
            'cost_usd': record.cost_usd,
            'cache_savings_usd': record.cache_savings_usd,
            'tool_calls': record.tool_calls,
            'error': record.error_message
        }

    async def get_insights(self, command_base: Optional[str] = None) -> Dict[str, Any]:
        """
        Get analytics insights for commands.

        Args:
            command_base: Optional command to filter by

        Returns:
            Dictionary of insights and statistics
        """
        # This will be implemented in Phase 4
        raise NotImplementedError("Analytics insights coming in Phase 4")

    async def predict(self, command_raw: str) -> Dict[str, Any]:
        """
        Predict token usage for a command.

        Args:
            command_raw: The command to predict for

        Returns:
            Dictionary containing predictions
        """
        # This will be implemented in Phase 5
        raise NotImplementedError("Prediction capabilities coming in Phase 5")