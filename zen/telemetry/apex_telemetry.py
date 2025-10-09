"""Telemetry wrapper for apex instance tracking.

This module provides a lightweight wrapper around agent_cli.py subprocess calls
to emit OpenTelemetry spans for apex instances without modifying agent_cli.py.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from typing import Any, Dict, Optional

from .manager import telemetry_manager

logger = logging.getLogger(__name__)


class ApexTelemetryWrapper:
    """Wrapper to track apex instance telemetry."""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.exit_code: Optional[int] = None
        self.message: Optional[str] = None
        self.env: str = "staging"
        self.stdout: str = ""
        self.stderr: str = ""

    def run_apex_with_telemetry(
        self,
        agent_cli_path: str,
        filtered_argv: list,
        env: Optional[Dict[str, str]] = None
    ) -> int:
        """Run agent_cli.py subprocess and emit telemetry span.

        Args:
            agent_cli_path: Path to agent_cli.py script
            filtered_argv: Command-line arguments (without 'zen' and '--apex')
            env: Environment variables to pass to subprocess

        Returns:
            Exit code from agent_cli subprocess
        """
        self.start_time = time.time()

        # Extract message from argv for telemetry
        self.message = self._extract_message(filtered_argv)
        self.env = self._extract_env(filtered_argv)

        # Build command
        cmd = [sys.executable, agent_cli_path] + filtered_argv

        try:
            # Use Popen for real-time streaming while still capturing output for telemetry
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered for real-time output
            )

            # Collect output while streaming in real-time
            stdout_lines = []
            stderr_lines = []

            # Stream stdout in real-time
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        print(line, end='')  # Print immediately for real-time display
                        stdout_lines.append(line)

            # Wait for process to complete and get stderr
            stderr_output = process.stderr.read() if process.stderr else ""
            if stderr_output:
                print(stderr_output, end='', file=sys.stderr)
                stderr_lines.append(stderr_output)

            # Wait for process to complete
            self.exit_code = process.wait()

            # Store captured output for telemetry parsing
            self.stdout = ''.join(stdout_lines)
            self.stderr = ''.join(stderr_lines)

        except Exception as e:
            logger.warning(f"Failed to run apex subprocess: {e}")
            self.exit_code = 1
            self.stderr = str(e)

        finally:
            self.end_time = time.time()
            self._emit_telemetry()

        return self.exit_code or 0

    def _extract_message(self, argv: list) -> str:
        """Extract message from command-line arguments."""
        try:
            if '--message' in argv:
                idx = argv.index('--message')
                if idx + 1 < len(argv):
                    return argv[idx + 1]
            elif '-m' in argv:
                idx = argv.index('-m')
                if idx + 1 < len(argv):
                    return argv[idx + 1]
        except (ValueError, IndexError):
            pass
        return "apex-instance"

    def _extract_env(self, argv: list) -> str:
        """Extract environment from command-line arguments."""
        try:
            if '--env' in argv:
                idx = argv.index('--env')
                if idx + 1 < len(argv):
                    return argv[idx + 1]
        except (ValueError, IndexError):
            pass
        return "staging"

    def _emit_telemetry(self) -> None:
        """Emit OpenTelemetry span for apex instance."""
        if telemetry_manager is None or not hasattr(telemetry_manager, "is_enabled"):
            logger.debug("Telemetry manager not available")
            return

        if not telemetry_manager.is_enabled():
            logger.debug("Telemetry is not enabled")
            return

        # Calculate duration
        duration_ms = 0
        if self.start_time and self.end_time:
            duration_ms = int((self.end_time - self.start_time) * 1000)

        # Determine status
        status = "completed" if self.exit_code == 0 else "failed"
        success = self.exit_code == 0

        # Build attributes for apex.instance span
        attributes: Dict[str, Any] = {
            "zen.instance.type": "apex",
            "zen.instance.name": "apex.instance",
            "zen.instance.status": status,
            "zen.instance.success": success,
            "zen.instance.duration_ms": duration_ms,
            "zen.instance.exit_code": self.exit_code or 0,
            "zen.apex.environment": self.env,
            "zen.apex.message": self._truncate_message(self.message or ""),
        }

        # Parse JSON output if available (contains token/cost info)
        json_output = self._parse_json_output()
        if json_output:
            self._add_json_metrics(attributes, json_output)

        # Emit span using the telemetry manager's tracer (same way as regular zen instances)
        try:
            # Access the tracer the same way telemetry_manager.record_instance_span() does
            if not hasattr(telemetry_manager, '_tracer') or telemetry_manager._tracer is None:
                logger.warning("Telemetry manager has no tracer configured")
                return

            from opentelemetry.trace import SpanKind
            from google.api_core.exceptions import GoogleAPICallError

            with telemetry_manager._tracer.start_as_current_span(
                "apex.instance", kind=SpanKind.INTERNAL
            ) as span:
                for key, value in attributes.items():
                    span.set_attribute(key, value)

            logger.info(f"✅ Emitted apex telemetry span with {len(attributes)} attributes")
            logger.debug(f"Apex span attributes: {attributes}")

            # Note: Removed force_flush to prevent blocking event streaming
            # Spans will still be sent via the normal batch export process

        except Exception as exc:
            logger.error(f"❌ Failed to emit apex telemetry span: {exc}")
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")

    def _truncate_message(self, message: str, max_length: int = 200) -> str:
        """Truncate message for telemetry attributes."""
        if len(message) <= max_length:
            return message
        return message[:max_length] + "..."

    def _parse_json_output(self) -> Optional[Dict[str, Any]]:
        """Parse JSON output from agent_cli stdout if available."""
        if not self.stdout:
            return None

        # Try to find JSON in stdout
        for line in self.stdout.split('\n'):
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue

        return None

    def _add_json_metrics(self, attributes: Dict[str, Any], json_output: Dict[str, Any]) -> None:
        """Add metrics from JSON output to telemetry attributes."""
        # Extract token usage if available
        if 'usage' in json_output:
            usage = json_output['usage']
            attributes['zen.tokens.total'] = usage.get('total_tokens', 0)
            attributes['zen.tokens.input'] = usage.get('input_tokens', 0)
            attributes['zen.tokens.output'] = usage.get('output_tokens', 0)
            attributes['zen.tokens.cache.read'] = usage.get('cache_read_tokens', 0)
            attributes['zen.tokens.cache.creation'] = usage.get('cache_creation_tokens', 0)

        # Extract cost if available
        if 'cost' in json_output:
            cost = json_output['cost']
            if 'total_usd' in cost:
                attributes['zen.cost.usd_total'] = round(float(cost['total_usd']), 6)

        # Extract run_id if available
        if 'run_id' in json_output:
            attributes['zen.apex.run_id'] = json_output['run_id']

        # Extract validation status
        if 'validation' in json_output:
            validation = json_output['validation']
            attributes['zen.apex.validation.passed'] = validation.get('passed', False)


def run_apex_with_telemetry(
    agent_cli_path: str,
    filtered_argv: list,
    env: Optional[Dict[str, str]] = None
) -> int:
    """Convenience function to run apex with telemetry tracking.

    Args:
        agent_cli_path: Path to agent_cli.py script
        filtered_argv: Command-line arguments (without 'zen' and '--apex')
        env: Environment variables to pass to subprocess

    Returns:
        Exit code from agent_cli subprocess
    """
    wrapper = ApexTelemetryWrapper()
    return wrapper.run_apex_with_telemetry(agent_cli_path, filtered_argv, env)
