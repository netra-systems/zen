#!/usr/bin/env python3
"""
Usage Examples:
  python3 claude-instance-orchestrator.py --workspace ~/my-project --dry-run
  python3 claude-instance-orchestrator.py --list-commands
  python3 claude-instance-orchestrator.py --config config.json
  python3 claude-instance-orchestrator.py --startup-delay 2.0  # 2 second delay between launches
  python3 claude-instance-orchestrator.py --startup-delay 0.5  # 0.5 second delay between launches
  python3 claude-instance-orchestrator.py --max-line-length 1000  # Longer output lines
  python3 claude-instance-orchestrator.py --status-report-interval 60  # Status reports every 60s
  python3 claude-instance-orchestrator.py --quiet  # Minimal output, errors only
  python3 claude-instance-orchestrator.py --start-at "2h"  # Start 2 hours from now
  python3 claude-instance-orchestrator.py --start-at "30m"  # Start in 30 minutes
  python3 claude-instance-orchestrator.py --start-at "1am"  # Start at 1 AM (today or tomorrow)
  python3 claude-instance-orchestrator.py --start-at "14:30"  # Start at 2:30 PM (today or tomorrow)
  python3 claude-instance-orchestrator.py --start-at "10:30pm"  # Start at 10:30 PM (today or tomorrow)
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
import yaml
import shutil
import os
import platform
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
from datetime import datetime, timedelta
import re
from uuid import uuid4, UUID

# Add token budget imports with proper path handling
sys.path.insert(0, str(Path(__file__).parent))
try:
    from token_budget.budget_manager import TokenBudgetManager
    from token_budget.visualization import render_progress_bar
except ImportError as e:
    # Graceful fallback if token budget package is not available
    TokenBudgetManager = None
    render_progress_bar = None
    # Note: logger is not yet defined here, will log warning after logger setup

# Optional NetraOptimizer imports
DatabaseClient = None
ExecutionRecord = None
try:
    from netraoptimizer import NetraOptimizerClient, DatabaseClient
    from netraoptimizer.database import ExecutionRecord
except ImportError:
    pass  # NetraOptimizer is optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class InstanceConfig:
    """Configuration for a Claude Code instance"""
    command: str
    name: Optional[str] = None
    description: Optional[str] = None
    allowed_tools: List[str] = None
    permission_mode: str = "acceptEdits"
    output_format: str = "stream-json"  # Default to stream-json for real-time output
    session_id: Optional[str] = None
    clear_history: bool = False
    compact_history: bool = False
    pre_commands: List[str] = None  # Commands to run before main command
    max_tokens_per_command: Optional[int] = None  # Token budget for this specific command

    def __post_init__(self):
        """Set defaults after initialization"""
        if self.name is None:
            self.name = self.command
        if self.description is None:
            self.description = f"Execute {self.command}"

@dataclass
class InstanceStatus:
    """Status of a Claude Code instance"""
    name: str
    pid: Optional[int] = None
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    output: str = ""
    error: str = ""
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0  # Backward compatibility - sum of cache_read + cache_creation
    cache_read_tokens: int = 0      # NEW: Separate cache read tracking
    cache_creation_tokens: int = 0  # NEW: Separate cache creation tracking
    tool_calls: int = 0
    _last_known_total_tokens: int = 0  # For delta tracking in budget management

    # NEW: Message ID deduplication tracking
    processed_message_ids: set = None  # Will be initialized as empty set

    # NEW: Authoritative cost from SDK when available
    total_cost_usd: Optional[float] = None

    def __post_init__(self):
        """Initialize fields that need special handling"""
        if self.processed_message_ids is None:
            self.processed_message_ids = set()

class ClaudeInstanceOrchestrator:
    """Orchestrator for managing multiple Claude Code instances"""

    def __init__(self, workspace_dir: Path, max_console_lines: int = 5, startup_delay: float = 1.0,
                 max_line_length: int = 500, status_report_interval: int = 30,
                 use_cloud_sql: bool = False, quiet: bool = False,
                 overall_token_budget: Optional[int] = None,
                 budget_enforcement_mode: str = "warn",
                 enable_budget_visuals: bool = True):
        self.workspace_dir = workspace_dir
        self.instances: Dict[str, InstanceConfig] = {}
        self.statuses: Dict[str, InstanceStatus] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self.start_datetime = datetime.now()
        self.max_console_lines = max_console_lines  # Max lines to show per instance
        self.startup_delay = startup_delay  # Delay between instance launches in seconds
        self.max_line_length = max_line_length  # Max characters per line in console output
        self.status_report_interval = status_report_interval  # Seconds between status reports
        self.last_status_report = time.time()
        self.status_report_task = None  # For the rolling status report task
        self.use_cloud_sql = use_cloud_sql
        self.quiet = quiet
        self.batch_id = str(uuid4())  # Generate batch ID for this orchestration run
        self.db_client = None
        self.optimizer = None

        # Initialize budget manager if any budget settings are provided
        if TokenBudgetManager and overall_token_budget is not None:
            self.budget_manager = TokenBudgetManager(
                overall_budget=overall_token_budget,
                enforcement_mode=budget_enforcement_mode
            )
        else:
            self.budget_manager = None
        self.enable_budget_visuals = enable_budget_visuals

        # Log budget configuration status
        if self.budget_manager:
            budget_msg = f"Overall: {overall_token_budget:,} tokens" if overall_token_budget else "No overall limit"
            logger.info(f"🎯 Token budget tracking enabled - {budget_msg} | Mode: {budget_enforcement_mode.upper()}")
        else:
            logger.debug("Token budget tracking disabled (no budget specified)")

        # Configure CloudSQL if requested
        if use_cloud_sql:
            os.environ['POSTGRES_PORT'] = '5434'
            os.environ['POSTGRES_HOST'] = 'localhost'
            os.environ['POSTGRES_DB'] = 'netra_optimizer'
            os.environ['POSTGRES_USER'] = 'postgres'
            os.environ['POSTGRES_PASSWORD'] = 'DTprdt5KoQXlEG4Gh9lF'
            os.environ['ENVIRONMENT'] = 'staging'
            logger.info("Configured for CloudSQL on port 5434")

            # Initialize database client if available
            if DatabaseClient:
                try:
                    self.db_client = DatabaseClient(use_cloud_sql=True)
                    logger.info("NetraOptimizer database client configured")
                except Exception as e:
                    logger.warning(f"Failed to initialize database client: {e}")

    def add_instance(self, config: InstanceConfig):
        """Add a new instance configuration"""
        # Validate slash command exists
        if not self.validate_command(config.command):
            logger.warning(f"Command '{config.command}' not found in available commands")
            logger.info(f"Available commands: {', '.join(self.discover_available_commands())}")

        self.instances[config.name] = config
        self.statuses[config.name] = InstanceStatus(name=config.name)
        logger.info(f"Added instance: {config.name} - {config.description}")

    def build_claude_command(self, config: InstanceConfig) -> List[str]:
        """Build the Claude Code command for an instance"""
        # Build the full command including pre-commands and session management
        full_command = []

        # Add session management commands first
        if config.clear_history:
            full_command.append("/clear")

        if config.compact_history:
            full_command.append("/compact")

        # Add any pre-commands
        if config.pre_commands:
            full_command.extend(config.pre_commands)

        # Add the main command
        full_command.append(config.command)

        # Join commands with semicolon for sequential execution
        command_string = "; ".join(full_command)

        # Find the claude executable with Mac-specific paths
        claude_cmd = shutil.which("claude")
        if not claude_cmd:
            # Try common paths on different platforms
            possible_paths = [
                "claude.cmd",  # Windows
                "claude.exe",  # Windows
                "/opt/homebrew/bin/claude",  # Mac Homebrew ARM
                "/usr/local/bin/claude",     # Mac Homebrew Intel
                "~/.local/bin/claude",       # User local install
                "/usr/bin/claude",           # System install
                "claude"                     # Final fallback
            ]
            
            for path in possible_paths:
                # Expand user path if needed
                expanded_path = Path(path).expanduser()
                if expanded_path.exists():
                    claude_cmd = str(expanded_path)
                    logger.info(f"Found Claude executable at: {claude_cmd}")
                    break
                elif shutil.which(path):
                    claude_cmd = path
                    logger.info(f"Found Claude executable via which: {claude_cmd}")
                    break

            if not claude_cmd or claude_cmd == "claude":
                logger.warning("Claude command not found in PATH or common locations")
                logger.warning("Please ensure Claude Code is installed and in your PATH")
                logger.warning("Install with: npm install -g @anthropic/claude-code")
                claude_cmd = "claude"  # Fallback

        # New approach: slash commands can be included directly in prompt
        cmd = [
            claude_cmd,
            "-p",  # headless mode
            command_string,  # Full command sequence
            f"--output-format={config.output_format}",
            f"--permission-mode={config.permission_mode}"
        ]

        # Add --verbose if using stream-json (required by Claude Code)
        if config.output_format == "stream-json":
            cmd.append("--verbose")

        if config.allowed_tools:
            cmd.append(f"--allowedTools={','.join(config.allowed_tools)}")

        if config.session_id:
            cmd.extend(["--session-id", config.session_id])

        return cmd

    def discover_available_commands(self) -> List[str]:
        """Discover available slash commands from .claude/commands/"""
        commands = []
        commands_dir = self.workspace_dir / ".claude" / "commands"

        if commands_dir.exists():
            for cmd_file in commands_dir.glob("*.md"):
                # Command name is filename without .md extension
                cmd_name = f"/{cmd_file.stem}"
                commands.append(cmd_name)
                logger.debug(f"Found command: {cmd_name}")

        # Add built-in commands
        builtin_commands = ["/compact", "/clear", "/help"]
        commands.extend(builtin_commands)

        return sorted(commands)

    def validate_command(self, command: str) -> bool:
        """Validate that a slash command exists"""
        available_commands = self.discover_available_commands()

        # Extract base command (remove arguments)
        base_command = command.split()[0] if command.split() else command

        return base_command in available_commands

    def inspect_command(self, command_name: str) -> Dict[str, Any]:
        """Inspect a slash command file for YAML frontmatter and configuration"""
        # Remove leading slash and any arguments
        base_name = command_name.lstrip('/').split()[0]
        command_file = self.workspace_dir / ".claude" / "commands" / f"{base_name}.md"

        if not command_file.exists():
            return {"exists": False}

        try:
            content = command_file.read_text(encoding='utf-8')

            # Check for YAML frontmatter
            if content.startswith('---\n'):
                parts = content.split('---\n', 2)
                if len(parts) >= 3:
                    frontmatter_text = parts[1]
                    try:
                        frontmatter = yaml.safe_load(frontmatter_text)
                        return {
                            "exists": True,
                            "file_path": str(command_file),
                            "frontmatter": frontmatter,
                            "content_preview": parts[2][:200] + "..." if len(parts[2]) > 200 else parts[2]
                        }
                    except yaml.YAMLError as e:
                        logger.warning(f"Invalid YAML frontmatter in {command_file}: {e}")

            return {
                "exists": True,
                "file_path": str(command_file),
                "frontmatter": {},
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            }

        except Exception as e:
            logger.error(f"Error reading command file {command_file}: {e}")
            return {"exists": False, "error": str(e)}

    async def run_instance(self, name: str) -> bool:
        """Run a single Claude Code instance asynchronously"""
        if name not in self.instances:
            logger.error(f"Instance {name} not found")
            return False

        config = self.instances[name]
        status = self.statuses[name]

        # --- PRE-EXECUTION BUDGET CHECK ---
        if self.budget_manager:
            # V1: Use a simple placeholder or the configured max. Future versions can predict.
            estimated_tokens = config.max_tokens_per_command or 1000  # Default estimate
            # CRITICAL: Use base command for budget checking
            base_command = config.command.split()[0] if config.command else config.command

            logger.info(f"🎯 Budget check for {name}: command={base_command}, estimated={estimated_tokens} tokens")

            can_run, reason = self.budget_manager.check_budget(base_command, estimated_tokens)
            if not can_run:
                message = f"Budget exceeded for instance {name}: {reason}. Skipping."
                if self.budget_manager.enforcement_mode == "block":
                    logger.error(f"🚫 BLOCK MODE: {message}")
                    status.status = "failed"
                    status.error = f"Blocked by budget limit - {reason}"
                    return False
                else:  # warn mode
                    logger.warning(f"⚠️  WARN MODE: {message}")
            else:
                logger.info(f"✅ Budget check passed for {name}: {reason}")

        try:
            logger.info(f"Starting instance: {name}")
            status.status = "running"
            status.start_time = time.time()

            cmd = self.build_claude_command(config)
            logger.info(f"Command: {' '.join(cmd)}")

            # Create the async process with Mac-friendly environment
            env = os.environ.copy()
            
            # Add common Mac paths to PATH if not present
            if platform.system() == "Darwin":  # macOS
                mac_paths = [
                    "/opt/homebrew/bin",      # Homebrew ARM
                    "/usr/local/bin",         # Homebrew Intel
                    "/usr/bin",               # System binaries
                    str(Path.home() / ".local" / "bin"),  # User local
                ]
                current_path = env.get("PATH", "")
                for mac_path in mac_paths:
                    if mac_path not in current_path:
                        env["PATH"] = f"{mac_path}:{current_path}"
                        current_path = env["PATH"]
            
            # Create the async process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_dir,
                env=env
            )

            status.pid = process.pid
            logger.info(f"Instance {name} started with PID {process.pid}")

            # For stream-json format, stream output in parallel with process execution
            if config.output_format == "stream-json":
                # Create streaming task but don't await it yet
                stream_task = asyncio.create_task(self._stream_output_parallel(name, process))

                # Wait for process to complete
                returncode = await process.wait()

                # Now wait for streaming to complete
                await stream_task
            else:
                # For non-streaming formats, use traditional communicate
                stdout, stderr = await process.communicate()
                returncode = process.returncode

                if stdout:
                    stdout_str = stdout.decode() if isinstance(stdout, bytes) else stdout
                    status.output += stdout_str
                    # Parse token usage from final output
                    self._parse_final_output_token_usage(stdout_str, status, config.output_format, name)
                if stderr:
                    status.error += stderr.decode() if isinstance(stderr, bytes) else stderr

            status.end_time = time.time()

            # Save metrics to database if CloudSQL is enabled
            if self.use_cloud_sql and self.db_client:
                await self._save_metrics_to_database(name, config, status)

            if returncode == 0:
                status.status = "completed"
                logger.info(f"Instance {name} completed successfully")
                return True
            else:
                status.status = "failed"
                logger.error(f"Instance {name} failed with return code {returncode}")
                if status.error:
                    logger.error(f"Error output: {status.error}")
                return False

        except Exception as e:
            status.status = "failed"
            status.error = str(e)
            logger.error(f"Exception running instance {name}: {e}")
            return False

    async def _save_metrics_to_database(self, name: str, config: InstanceConfig, status: InstanceStatus):
        """Save execution metrics to CloudSQL database"""
        if not self.db_client or not ExecutionRecord:
            return

        try:
            # Initialize database if not already done
            if not hasattr(self.db_client, '_initialized'):
                await self.db_client.initialize()
                self.db_client._initialized = True

            # Create execution record
            execution_id = uuid4()
            command_string = config.command
            start_time = datetime.fromtimestamp(status.start_time) if status.start_time else datetime.now()

            # Calculate cache metrics
            cache_read = 0
            cache_creation = 0

            # Try to extract cache metrics from cached_tokens
            # In claude-instance-orchestrator.py, cached_tokens combines both read and creation
            # We'll need to parse from the output to get accurate breakdown

            record = ExecutionRecord(
                id=execution_id,
                timestamp=start_time,
                command_base='claude',  # Always 'claude' for consistency
                command_raw=command_string,
                batch_id=UUID(self.batch_id) if self.batch_id else None,
                execution_sequence=list(self.instances.keys()).index(name),
                workspace_context={
                    'instance_name': name,
                    'workspace_dir': str(self.workspace_dir),
                    'description': config.description,
                    'orchestration_run': self.start_datetime.isoformat()
                },
                input_tokens=status.input_tokens,
                output_tokens=status.output_tokens,
                cached_tokens=status.cached_tokens,  # Combined cache_read + cache_creation
                fresh_tokens=0,  # Will be set if we can parse cache_creation separately
                total_tokens=status.total_tokens,
                cache_hit_rate=(status.cached_tokens / status.total_tokens * 100) if status.total_tokens > 0 else 0,
                cost_usd=self._calculate_cost(status),
                cache_savings_usd=0,  # Will calculate if we have cache_read data
                execution_time_ms=int((status.end_time - status.start_time) * 1000) if status.start_time else 0,
                status=status.status,
                error_message=status.error if status.error else None
            )

            # Save to database
            await self.db_client.insert_execution(record)
            logger.info(f"Saved metrics to CloudSQL for {name}")

        except Exception as e:
            logger.warning(f"Failed to save metrics to database for {name}: {e}")

    def _calculate_cost(self, status: InstanceStatus) -> float:
        """Calculate cost with current Claude 3.5 Sonnet pricing and proper cache handling"""

        # Use authoritative cost if available (preferred)
        if status.total_cost_usd is not None:
            return status.total_cost_usd

        # Fallback calculation with current pricing
        # Claude 3.5 Sonnet current rates (as of 2024-2025)
        input_cost = (status.input_tokens / 1_000_000) * 3.00    # $3 per M input tokens
        output_cost = (status.output_tokens / 1_000_000) * 15.00  # $15 per M output tokens

        # Cache costs (differentiated by type)
        cache_read_cost = (status.cache_read_tokens / 1_000_000) * 0.30      # $0.30 per M cache read
        cache_creation_cost = (status.cache_creation_tokens / 1_000_000) * 0.75  # 25% of input rate for cache creation

        return input_cost + output_cost + cache_read_cost + cache_creation_cost

    async def _stream_output(self, name: str, process):
        """Stream output in real-time for stream-json format (DEPRECATED - use _stream_output_parallel)"""
        status = self.statuses[name]

        async def read_stream(stream, prefix):
            while True:
                line = await stream.readline()
                if not line:
                    break
                line_str = line.decode() if isinstance(line, bytes) else line
                print(f"[{name}] {prefix}: {line_str.strip()}")

                # Accumulate output
                if prefix == "STDOUT":
                    status.output += line_str
                else:
                    status.error += line_str

        # Run both stdout and stderr reading concurrently
        await asyncio.gather(
            read_stream(process.stdout, "STDOUT"),
            read_stream(process.stderr, "STDERR"),
            return_exceptions=True
        )

    async def _stream_output_parallel(self, name: str, process):
        """Stream output in real-time for stream-json format with proper parallel execution"""
        status = self.statuses[name]
        # Rolling buffer to show only recent lines (prevent console overflow)
        recent_lines_buffer = []
        line_count = 0

        def format_instance_line(content: str, prefix: str = "") -> str:
            """Format a line with clear instance separation and truncation"""
            # Truncate content to max_line_length
            if len(content) > self.max_line_length:
                content = content[:self.max_line_length-3] + "..."

            # Create clear visual separation
            instance_header = f"╔═[{name}]" + "═" * (20 - len(name) - 4) if len(name) < 16 else f"╔═[{name}]═"
            if prefix:
                instance_header += f" {prefix} "

            return f"{instance_header}\n║ {content}\n╚" + "═" * (len(instance_header) - 1)

        async def read_stream(stream, prefix):
            nonlocal line_count
            try:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    line_str = line.decode() if isinstance(line, bytes) else line
                    line_count += 1

                    # Clean the line
                    clean_line = line_str.strip()

                    # Add to rolling buffer with formatted display
                    display_line = format_instance_line(clean_line, prefix)
                    recent_lines_buffer.append(display_line)

                    # Keep only the most recent lines
                    if len(recent_lines_buffer) > self.max_console_lines:
                        recent_lines_buffer.pop(0)

                    # Only show periodic updates to prevent spam
                    # Show every 10th line, or important lines (errors, completions)
                    # Respect quiet mode
                    if self.max_console_lines > 0:
                        should_display = (
                            line_count % 10 == 0 or  # Every 10th line
                            prefix == "STDERR" or    # All error lines
                            "completed" in clean_line.lower() or
                            "error" in clean_line.lower() or
                            "failed" in clean_line.lower() or
                            "success" in clean_line.lower()
                        )

                        if should_display:
                            print(f"\n{display_line}\n", flush=True)
                    elif prefix == "STDERR":
                        # In quiet mode, still show errors
                        error_display = format_instance_line(clean_line, "ERROR")
                        print(f"\n{error_display}\n", flush=True)

                    # Accumulate output in status (keep full output for saving)
                    if prefix == "STDOUT":
                        status.output += line_str
                        # Parse token usage from Claude output if present
                        self._parse_token_usage(clean_line, status, name)
                    else:
                        status.error += line_str
            except Exception as e:
                logger.error(f"Error reading {prefix} for instance {name}: {e}")

        # Create tasks for reading both streams concurrently
        stdout_task = asyncio.create_task(read_stream(process.stdout, "STDOUT"))
        stderr_task = asyncio.create_task(read_stream(process.stderr, "STDERR"))

        # Wait for both streams to be consumed
        try:
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error in stream reading for instance {name}: {e}")
        finally:
            # Show final summary of recent lines for this instance
            if recent_lines_buffer and self.max_console_lines > 0:
                final_header = f"╔═══ FINAL OUTPUT [{name}] ═══╗"
                print(f"\n{final_header}")
                print(f"║ Last {len(recent_lines_buffer)} lines of {line_count} total")
                print(f"║ Status: {status.status}")
                if status.start_time:
                    duration = time.time() - status.start_time
                    print(f"║ Duration: {duration:.1f}s")
                print("╚" + "═" * (len(final_header) - 2) + "╝\n")

            # Always show completion message with clear formatting
            completion_msg = f"🏁 [{name}] COMPLETED - {line_count} lines processed, output saved"
            print(f"\n{'='*60}")
            print(f"{completion_msg}")
            print(f"{'='*60}\n")

            # Ensure streams are properly closed
            if process.stdout and not process.stdout.at_eof():
                process.stdout.close()
            if process.stderr and not process.stderr.at_eof():
                process.stderr.close()

    async def run_all_instances(self, timeout: int = 300) -> Dict[str, bool]:
        """Run all instances with configurable soft startup delay between launches"""
        instance_names = list(self.instances.keys())
        logger.info(f"Starting {len(instance_names)} instances with {self.startup_delay}s delay between launches (timeout: {timeout}s each)")

        # Create tasks with staggered startup
        tasks = []
        for i, name in enumerate(instance_names):
            # Calculate delay for this instance (i * startup_delay seconds)
            delay = i * self.startup_delay
            if delay > 0:
                logger.info(f"Instance '{name}' will start in {delay}s")

            # Create a task that waits for its turn, then starts the instance
            task = asyncio.create_task(self._run_instance_with_delay(name, delay, timeout))
            tasks.append(task)

        # Start the rolling status report task if we have instances to monitor
        if len(tasks) > 0 and not self.max_console_lines == 0:  # Don't show status in quiet mode
            self.status_report_task = asyncio.create_task(self._rolling_status_reporter())
            tasks.append(self.status_report_task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Stop the status reporter
        if self.status_report_task and not self.status_report_task.done():
            self.status_report_task.cancel()
            try:
                await self.status_report_task
            except asyncio.CancelledError:
                pass

        final_results = {}
        for name, result in zip(self.instances.keys(), results):
            if isinstance(result, asyncio.TimeoutError):
                logger.error(f"Instance {name} timed out after {timeout}s")
                self.statuses[name].status = "failed"
                self.statuses[name].error = f"Timeout after {timeout}s"
                final_results[name] = False
            elif isinstance(result, Exception):
                logger.error(f"Instance {name} failed with exception: {result}")
                self.statuses[name].status = "failed"
                self.statuses[name].error = str(result)
                final_results[name] = False
            else:
                final_results[name] = result

        return final_results

    async def _run_instance_with_delay(self, name: str, delay: float, timeout: int) -> bool:
        """Run an instance after a specified delay"""
        if delay > 0:
            logger.info(f"Waiting {delay}s before starting instance '{name}'")
            await asyncio.sleep(delay)

        logger.info(f"Now starting instance '{name}' (after {delay}s delay)")
        return await asyncio.wait_for(self.run_instance(name), timeout=timeout)

    async def _rolling_status_reporter(self):
        """Provide periodic status updates for all running instances"""
        try:
            while True:
                await asyncio.sleep(self.status_report_interval)
                await self._print_status_report()
        except asyncio.CancelledError:
            # Final status report when cancelled
            await self._print_status_report(final=True)
            raise
        except Exception as e:
            logger.error(f"Error in status reporter: {e}")

    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to a readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m{remaining_seconds:.0f}s"
        else:
            hours = int(seconds // 3600)
            remaining_minutes = int((seconds % 3600) // 60)
            return f"{hours}h{remaining_minutes}m"

    def _format_tokens(self, tokens: int) -> str:
        """Format token count with thousands separator"""
        if tokens >= 1000000:
            return f"{tokens/1000000:.1f}M"
        elif tokens >= 1000:
            return f"{tokens/1000:.1f}K"
        else:
            return str(tokens)

    def _calculate_token_median(self) -> float:
        """Calculate median token usage across all instances"""
        token_counts = [status.total_tokens for status in self.statuses.values() if status.total_tokens > 0]
        if not token_counts:
            return 0
        
        token_counts.sort()
        n = len(token_counts)
        if n % 2 == 0:
            return (token_counts[n//2 - 1] + token_counts[n//2]) / 2
        else:
            return token_counts[n//2]

    def _calculate_token_percentage(self, tokens: int, median: float) -> str:
        """Calculate percentage relative to median"""
        if median == 0:
            return "N/A"
        percentage = (tokens / median) * 100
        if percentage >= 150:
            return f"+{percentage-100:.0f}%"
        elif percentage <= 50:
            return f"-{100-percentage:.0f}%"
        else:
            return f"{percentage-100:+.0f}%"

    async def _print_status_report(self, final: bool = False):
        """Print a formatted status report of all instances"""
        if not self.statuses:
            return

        current_time = time.time()
        report_type = "FINAL STATUS" if final else "STATUS REPORT"

        # Create status summary
        status_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0}

        for name, status in self.statuses.items():
            status_counts[status.status] += 1

        # Calculate token median
        token_median = self._calculate_token_median()

        # Print the report header
        header = f"╔═══ {report_type} [{datetime.now().strftime('%H:%M:%S')}] ═══╗"
        print(f"\n{header}")
        print(f"║ Total: {len(self.statuses)} instances")
        print(f"║ Running: {status_counts['running']}, Completed: {status_counts['completed']}, Failed: {status_counts['failed']}, Pending: {status_counts['pending']}")

        # Show token usage summary
        total_tokens_all = sum(s.total_tokens for s in self.statuses.values())
        total_cached_all = sum(s.cached_tokens for s in self.statuses.values())
        total_tools_all = sum(s.tool_calls for s in self.statuses.values())
        median_str = self._format_tokens(int(token_median)) if token_median > 0 else "0"
        print(f"║ Tokens: {self._format_tokens(total_tokens_all)} total, {self._format_tokens(total_cached_all)} cached | Median: {median_str} | Tools: {total_tools_all}")

        # --- ADD BUDGET STATUS SECTION ---
        if self.budget_manager and self.enable_budget_visuals and render_progress_bar:
            bm = self.budget_manager
            used_formatted = self._format_tokens(bm.total_usage)

            print(f"|")
            print(f"| TOKEN BUDGET STATUS |")

            if bm.overall_budget is not None:
                overall_bar = render_progress_bar(bm.total_usage, bm.overall_budget)
                total_formatted = self._format_tokens(bm.overall_budget)
                print(f"║ Overall: {overall_bar} {used_formatted}/{total_formatted}")
            else:
                print(f"║ Overall: [UNLIMITED] {used_formatted} used")

            if bm.command_budgets:
                print(f"║ Command Budgets:")
                for name, budget_info in bm.command_budgets.items():
                    bar = render_progress_bar(budget_info.used, budget_info.limit)
                    limit_formatted = self._format_tokens(budget_info.limit)
                    used_cmd_formatted = self._format_tokens(budget_info.used)
                    print(f"║   {name:<20} {bar} {used_cmd_formatted}/{limit_formatted}")
            else:
                print(f"║ Command Budgets: None configured")

        print(f"║")
        
        # Print column headers with wider name column
        print(f"║  {'Status':<8} {'Name':<35} {'Duration':<10} {'Tokens':<8} {'vs Med':<8} {'Cache':<8} {'Tools':<6}")
        print(f"║  {'─'*8} {'─'*35} {'─'*10} {'─'*8} {'─'*8} {'─'*8} {'─'*6}")

        for name, status in self.statuses.items():
            # Status emoji
            emoji_map = {
                "pending": "⏳",
                "running": "🏃",
                "completed": "✅",
                "failed": "❌"
            }
            emoji = emoji_map.get(status.status, "❓")

            # Calculate uptime/duration
            if status.start_time:
                if status.end_time:
                    duration = status.end_time - status.start_time
                    time_info = self._format_duration(duration)
                else:
                    uptime = current_time - status.start_time
                    time_info = self._format_duration(uptime)
            else:
                time_info = "waiting"

            # Format token information
            token_info = self._format_tokens(status.total_tokens) if status.total_tokens > 0 else "0"
            cache_info = self._format_tokens(status.cached_tokens) if status.cached_tokens > 0 else "0"
            tool_info = str(status.tool_calls) if status.tool_calls > 0 else "0"
            
            # Calculate percentage relative to median
            token_pct = self._calculate_token_percentage(status.total_tokens, token_median)

            # Create detailed line with consistent spacing and wider name column
            detail = f"  {emoji:<8} {name:<35} {time_info:<10} {token_info:<8} {token_pct:<8} {cache_info:<8} {tool_info:<6}"

            print(f"║{detail}")

        footer = "╚" + "═" * (len(header) - 2) + "╝"
        print(f"{footer}\n")

    def _parse_token_usage(self, line: str, status: InstanceStatus, instance_name: str):
        """Parse token usage information from Claude Code JSON output lines"""
        # First try to parse as JSON - this is the modern approach for stream-json format
        if self._try_parse_json_token_usage(line, status):
            self._update_budget_tracking(status, instance_name)
            return

        # Fallback to regex parsing for backward compatibility or non-JSON output
        self._parse_token_usage_fallback(line, status)
        self._update_budget_tracking(status, instance_name)

    def _update_budget_tracking(self, status: InstanceStatus, instance_name: str):
        """Update budget tracking with token deltas and check for runtime budget violations"""
        if self.budget_manager and status.total_tokens > status._last_known_total_tokens:
            new_tokens = status.total_tokens - status._last_known_total_tokens
            # Extract base command without arguments
            command = self.instances[instance_name].command
            base_command = command.split()[0] if command else command

            # Record the usage
            self.budget_manager.record_usage(base_command, new_tokens)
            status._last_known_total_tokens = status.total_tokens

            # RUNTIME BUDGET ENFORCEMENT - Check if we've exceeded budgets during execution
            self._check_runtime_budget_violation(status, instance_name, base_command)

    def _check_runtime_budget_violation(self, status: InstanceStatus, instance_name: str, base_command: str):
        """Check for budget violations during runtime and terminate instances if needed"""
        if not self.budget_manager:
            return

        # Check if current usage violates any budget
        violation_detected = False
        violation_reason = ""

        # Check overall budget
        if (self.budget_manager.overall_budget is not None and
            self.budget_manager.total_usage > self.budget_manager.overall_budget):
            violation_detected = True
            violation_reason = f"Overall budget exceeded: {self.budget_manager.total_usage}/{self.budget_manager.overall_budget} tokens"

        # Check command budget (only if overall budget check didn't fail)
        elif (base_command in self.budget_manager.command_budgets):
            command_budget = self.budget_manager.command_budgets[base_command]
            if command_budget.used > command_budget.limit:
                violation_detected = True
                violation_reason = f"Command '{base_command}' budget exceeded: {command_budget.used}/{command_budget.limit} tokens"

        if violation_detected:
            message = f"Runtime budget violation for {instance_name}: {violation_reason}"

            if self.budget_manager.enforcement_mode == "block":
                logger.error(f"🚫 RUNTIME TERMINATION: {message}")
                self._terminate_instance(status, instance_name, f"Terminated due to budget violation - {violation_reason}")
            else:  # warn mode
                logger.warning(f"⚠️  RUNTIME WARNING: {message}")

    def _terminate_instance(self, status: InstanceStatus, instance_name: str, reason: str):
        """Terminate a running instance due to budget violation"""
        try:
            if status.pid and status.status == "running":
                logger.info(f"Terminating instance {instance_name} (PID: {status.pid}): {reason}")

                # Try graceful termination first
                import signal
                import os
                try:
                    os.kill(status.pid, signal.SIGTERM)
                    logger.info(f"Sent SIGTERM to {instance_name} (PID: {status.pid})")
                except (OSError, ProcessLookupError) as e:
                    logger.warning(f"Could not send SIGTERM to {status.pid}: {e}")

                # Update status
                status.status = "failed"
                status.error = reason
                status.end_time = time.time()

            else:
                logger.warning(f"Cannot terminate {instance_name}: no PID or not running (status: {status.status})")

        except Exception as e:
            logger.error(f"Failed to terminate instance {instance_name}: {e}")

    def _extract_message_id(self, json_data: dict) -> Optional[str]:
        """Extract message ID from JSON data for deduplication tracking"""
        # Try multiple common locations where message ID might be stored
        message_id = (
            json_data.get('id') or
            json_data.get('message_id') or
            (json_data.get('message', {}).get('id') if isinstance(json_data.get('message'), dict) else None) or
            (json_data.get('response', {}).get('id') if isinstance(json_data.get('response'), dict) else None)
        )
        return message_id

    def _update_cache_tokens_for_compatibility(self, status: InstanceStatus):
        """Update legacy cached_tokens field for backward compatibility"""
        # Maintain backward compatibility by updating the combined cached_tokens field
        status.cached_tokens = status.cache_read_tokens + status.cache_creation_tokens

    def _try_parse_json_token_usage(self, line: str, status: InstanceStatus) -> bool:
        """SDK-compliant token usage parsing with message ID deduplication"""
        line = line.strip()
        if not line.startswith('{'):
            return False

        try:
            json_data = json.loads(line)

            # Extract message ID for deduplication
            message_id = self._extract_message_id(json_data)

            if message_id:
                # SDK Rule: Skip if already processed this message ID
                if message_id in status.processed_message_ids:
                    logger.debug(f"Skipping duplicate message ID: {message_id}")
                    return True

                # Mark as processed
                status.processed_message_ids.add(message_id)

            # Process usage data (only once per message ID)
            usage_data = None
            if 'usage' in json_data:
                usage_data = json_data['usage']
            elif 'message' in json_data and isinstance(json_data['message'], dict) and 'usage' in json_data['message']:
                usage_data = json_data['message']['usage']
            elif 'tokens' in json_data and isinstance(json_data['tokens'], dict):
                # Handle structured token data format
                usage_data = json_data['tokens']

            if usage_data and isinstance(usage_data, dict):
                # Use max() instead of += to handle same-ID messages correctly
                if 'input_tokens' in usage_data:
                    status.input_tokens = max(status.input_tokens, int(usage_data['input_tokens']))
                elif 'input' in usage_data:  # Alternative format
                    status.input_tokens = max(status.input_tokens, int(usage_data['input']))

                if 'output_tokens' in usage_data:
                    status.output_tokens = max(status.output_tokens, int(usage_data['output_tokens']))
                elif 'output' in usage_data:  # Alternative format
                    status.output_tokens = max(status.output_tokens, int(usage_data['output']))

                # Separate cache types for accurate billing
                if 'cache_read_input_tokens' in usage_data:
                    status.cache_read_tokens = max(status.cache_read_tokens, int(usage_data['cache_read_input_tokens']))
                if 'cache_creation_input_tokens' in usage_data:
                    status.cache_creation_tokens = max(status.cache_creation_tokens, int(usage_data['cache_creation_input_tokens']))

                # Handle legacy cached field
                if 'cached' in usage_data:
                    # If we don't have separate cache data, use the combined field
                    if 'cache_read_input_tokens' not in usage_data and 'cache_creation_input_tokens' not in usage_data:
                        cached_total = int(usage_data['cached'])
                        status.cache_read_tokens = max(status.cache_read_tokens, cached_total)

                # Use authoritative total when available
                if 'total_tokens' in usage_data:
                    total = int(usage_data['total_tokens'])
                    status.total_tokens = max(status.total_tokens, total)
                elif 'total' in usage_data:  # Alternative format
                    total = int(usage_data['total'])
                    status.total_tokens = max(status.total_tokens, total)

                # Store authoritative cost if available
                if 'total_cost_usd' in usage_data:
                    status.total_cost_usd = max(status.total_cost_usd or 0, float(usage_data['total_cost_usd']))

                # Update backward compatibility field
                self._update_cache_tokens_for_compatibility(status)

                return True

            # Handle tool calls with same ID deduplication
            if 'type' in json_data:
                if json_data['type'] in ['tool_use', 'tool_call', 'tool_execution']:
                    if message_id:
                        # Only count tools once per message ID
                        status.tool_calls += 1
                    return True
                elif json_data['type'] == 'message' and 'tool_calls' in json_data:
                    # Count tool calls in message
                    tool_calls = json_data['tool_calls']
                    if isinstance(tool_calls, list):
                        status.tool_calls += len(tool_calls)
                    elif isinstance(tool_calls, (int, float)):
                        status.tool_calls += int(tool_calls)
                    return True

            # Handle direct token fields at root level (without message ID - always accumulate)
            token_fields_found = False
            if not message_id:  # Only process these if no message ID (prevents double counting)
                if 'input_tokens' in json_data:
                    status.input_tokens = max(status.input_tokens, int(json_data['input_tokens']))
                    token_fields_found = True
                if 'output_tokens' in json_data:
                    status.output_tokens = max(status.output_tokens, int(json_data['output_tokens']))
                    token_fields_found = True
                if 'cached_tokens' in json_data:
                    cached_total = int(json_data['cached_tokens'])
                    status.cache_read_tokens = max(status.cache_read_tokens, cached_total)
                    self._update_cache_tokens_for_compatibility(status)
                    token_fields_found = True
                if 'total_tokens' in json_data:
                    total = int(json_data['total_tokens'])
                    status.total_tokens = max(status.total_tokens, total)
                    token_fields_found = True
                if 'tool_calls' in json_data and isinstance(json_data['tool_calls'], (int, float)):
                    status.tool_calls += int(json_data['tool_calls'])
                    token_fields_found = True

            return token_fields_found

        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            # Not valid JSON or doesn't contain expected fields
            logger.debug(f"JSON parsing failed for line: {e}")
            return False
    
    def _parse_token_usage_fallback(self, line: str, status: InstanceStatus):
        """Fallback regex-based token parsing for backward compatibility"""
        line_lower = line.lower()
        
        # Import regex here to avoid overhead when JSON parsing succeeds
        import re
        
        # Pattern 1: "Used X tokens" or "X tokens used"
        token_match = re.search(r'(?:used|consumed)\s+(\d+)\s+tokens?|(?:(\d+)\s+tokens?\s+(?:used|consumed))', line_lower)
        if token_match:
            tokens = int(token_match.group(1) or token_match.group(2))
            status.total_tokens += tokens
            return
        
        # Pattern 2: Input/Output/Cached token breakdown
        input_match = re.search(r'input[:\s]+(\d+)\s+tokens?', line_lower)
        if input_match:
            status.input_tokens += int(input_match.group(1))
        
        output_match = re.search(r'output[:\s]+(\d+)\s+tokens?', line_lower)
        if output_match:
            status.output_tokens += int(output_match.group(1))
        
        # Pattern 2b: Cached tokens
        cached_match = re.search(r'cached[:\s]+(\d+)\s+tokens?', line_lower)
        if cached_match:
            # Add to cache_read_tokens and update backward compatibility
            cached_tokens = int(cached_match.group(1))
            status.cache_read_tokens = max(status.cache_read_tokens, cached_tokens)
            self._update_cache_tokens_for_compatibility(status)

        # Pattern 2c: Cache hit patterns
        cache_hit_match = re.search(r'cache\s+hit[:\s]+(\d+)\s+tokens?', line_lower)
        if cache_hit_match:
            # Add to cache_read_tokens and update backward compatibility
            cached_tokens = int(cache_hit_match.group(1))
            status.cache_read_tokens = max(status.cache_read_tokens, cached_tokens)
            self._update_cache_tokens_for_compatibility(status)
        
        # Pattern 3: Total token counts "Total: X tokens"
        total_match = re.search(r'total[:\s]+(\d+)\s+tokens?', line_lower)
        if total_match:
            total_tokens = int(total_match.group(1))
            # Only update if this is larger than current total (avoid double counting)
            if total_tokens > status.total_tokens:
                status.total_tokens = total_tokens
        
        # Pattern 4: Tool calls - look for tool execution indicators
        if any(phrase in line_lower for phrase in ['tool call', 'executing tool', 'calling tool', 'tool execution']):
            status.tool_calls += 1
    
    def _parse_final_output_token_usage(self, output: str, status: InstanceStatus, output_format: str, instance_name: str):
        """Parse token usage from final Claude Code output for non-streaming formats"""
        if output_format == "json":
            # For standard JSON format, try to parse the entire output as JSON
            self._parse_json_final_output(output, status, instance_name)
        else:
            # For other formats, parse line by line
            for line in output.split('\n'):
                line = line.strip()
                if line:
                    self._parse_token_usage(line, status, instance_name)
    
    def _parse_json_final_output(self, output: str, status: InstanceStatus, instance_name: str):
        """Parse token usage from complete JSON output"""
        try:
            # Try to parse the entire output as JSON
            json_data = json.loads(output)
            
            # Extract token information from the final JSON response
            if isinstance(json_data, dict):
                # Look for usage information in various locations
                
                # Check for usage stats in root
                if 'usage' in json_data:
                    self._extract_usage_stats(json_data['usage'], status)
                
                # Check for usage nested in message (common Claude Code format)
                if 'message' in json_data and isinstance(json_data['message'], dict):
                    message = json_data['message']
                    if 'usage' in message:
                        self._extract_usage_stats(message['usage'], status)
                
                # Check for token info in metadata
                if 'metadata' in json_data and 'usage' in json_data['metadata']:
                    self._extract_usage_stats(json_data['metadata']['usage'], status)
                
                # Check for response-level token info
                if 'tokens' in json_data:
                    self._extract_token_info(json_data['tokens'], status)
                
                # Check for turns/conversations with token info
                if 'turns' in json_data:
                    for turn in json_data['turns']:
                        if isinstance(turn, dict) and 'usage' in turn:
                            self._extract_usage_stats(turn['usage'], status)
                
                # Check for tool calls
                if 'tool_calls' in json_data:
                    tool_calls = json_data['tool_calls']
                    if isinstance(tool_calls, list):
                        status.tool_calls += len(tool_calls)
                    elif isinstance(tool_calls, (int, float)):
                        status.tool_calls += int(tool_calls)
                
                logger.debug(f"Parsed JSON final output: tokens={status.total_tokens}, tools={status.tool_calls}")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Failed to parse final output as JSON: {e}")
            # Fallback to line-by-line parsing
            for line in output.split('\n'):
                line = line.strip()
                if line:
                    self._parse_token_usage(line, status, instance_name)
    
    def _extract_usage_stats(self, usage_data: dict, status: InstanceStatus):
        """Extract usage statistics from a usage object"""
        if not isinstance(usage_data, dict):
            return
            
        # Standard Claude API usage fields (use max to handle same message IDs)
        if 'input_tokens' in usage_data:
            status.input_tokens = max(status.input_tokens, int(usage_data['input_tokens']))
        if 'output_tokens' in usage_data:
            status.output_tokens = max(status.output_tokens, int(usage_data['output_tokens']))
        if 'cache_read_input_tokens' in usage_data:
            status.cache_read_tokens = max(status.cache_read_tokens, int(usage_data['cache_read_input_tokens']))

        # Handle cache_creation_input_tokens separately
        if 'cache_creation_input_tokens' in usage_data:
            status.cache_creation_tokens = max(status.cache_creation_tokens, int(usage_data['cache_creation_input_tokens']))

        # Update backward compatibility field
        self._update_cache_tokens_for_compatibility(status)
        
        # Calculate or use provided total
        if 'total_tokens' in usage_data:
            total = int(usage_data['total_tokens'])
            if total > status.total_tokens:
                status.total_tokens = total
        else:
            # Calculate total from all components including cache creation
            cache_creation = int(usage_data.get('cache_creation_input_tokens', 0))
            cache_read = int(usage_data.get('cache_read_input_tokens', 0))
            calculated_total = status.input_tokens + status.output_tokens + cache_creation + cache_read
            if calculated_total > status.total_tokens:
                status.total_tokens = calculated_total
    
    def _extract_token_info(self, token_data, status: InstanceStatus):
        """Extract token information from various token data formats"""
        if isinstance(token_data, dict):
            # Structured token data
            if 'total' in token_data:
                total = int(token_data['total'])
                if total > status.total_tokens:
                    status.total_tokens = total
            if 'input' in token_data:
                status.input_tokens += int(token_data['input'])
            if 'output' in token_data:
                status.output_tokens += int(token_data['output'])
            if 'cached' in token_data:
                cached_tokens = int(token_data['cached'])
                status.cache_read_tokens = max(status.cache_read_tokens, cached_tokens)
                self._update_cache_tokens_for_compatibility(status)
        elif isinstance(token_data, (int, float)):
            # Simple token count
            status.total_tokens += int(token_data)

    def get_status_summary(self) -> Dict:
        """Get summary of all instance statuses"""
        summary = {
            "total_instances": len(self.instances),
            "completed": 0,
            "failed": 0,
            "running": 0,
            "pending": 0,
            "instances": {}
        }

        for name, status in self.statuses.items():
            summary["instances"][name] = asdict(status)
            summary[status.status] += 1

            # Add duration if completed
            if status.start_time and status.end_time:
                duration = status.end_time - status.start_time
                summary["instances"][name]["duration"] = f"{duration:.2f}s"

        return summary

    def generate_output_filename(self, base_filename: str = None) -> Path:
        """Generate output filename with datetime and agent names"""
        if base_filename is None:
            base_filename = "claude_instances_results"

        # Format datetime as YYYYMMDD_HHMMSS
        datetime_str = self.start_datetime.strftime("%Y%m%d_%H%M%S")

        # Get agent names, clean them for filename
        agent_names = []
        for name in self.instances.keys():
            # Clean name for filename (remove special characters)
            clean_name = "".join(c for c in name if c.isalnum() or c in "_-")
            agent_names.append(clean_name)

        agents_str = "_".join(sorted(agent_names))

        # Create filename: base_DATETIME_agents.json
        filename = f"{base_filename}_{datetime_str}_{agents_str}.json"

        return Path(filename)

    def save_results(self, output_file: Path = None):
        """Save results to JSON file with datetime and agent names"""
        if output_file is None:
            output_file = self.generate_output_filename()

        results = self.get_status_summary()

        # Add metadata to results including token summary
        total_tokens = sum(status.total_tokens for status in self.statuses.values())
        total_input_tokens = sum(status.input_tokens for status in self.statuses.values())
        total_output_tokens = sum(status.output_tokens for status in self.statuses.values())
        total_cached_tokens = sum(status.cached_tokens for status in self.statuses.values())
        total_tool_calls = sum(status.tool_calls for status in self.statuses.values())

        results["metadata"] = {
            "start_datetime": self.start_datetime.isoformat(),
            "agents": list(self.instances.keys()),
            "generated_filename": str(output_file),
            "token_usage": {
                "total_tokens": total_tokens,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cached_tokens": total_cached_tokens,
                "total_tool_calls": total_tool_calls,
                "cache_hit_rate": round(total_cached_tokens / max(total_tokens, 1) * 100, 2)
            }
        }

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to {output_file}")



def parse_start_time(start_at_str: str) -> datetime:
    """Parse start time specification into a datetime object"""
    if not start_at_str:
        return datetime.now()

    start_at_str = start_at_str.strip().lower()
    now = datetime.now()

    # Relative time patterns (e.g., "2h", "30m", "45s")
    relative_match = re.match(r'^(\d+(?:\.\d+)?)\s*([hms])$', start_at_str)
    if relative_match:
        value = float(relative_match.group(1))
        unit = relative_match.group(2)

        if unit == 'h':
            target_time = now + timedelta(hours=value)
        elif unit == 'm':
            target_time = now + timedelta(minutes=value)
        elif unit == 's':
            target_time = now + timedelta(seconds=value)

        return target_time

    # Named time patterns (e.g., "1am", "2:30pm", "14:30")
    # Handle formats like "1am", "2pm", "10:30am", "14:30"
    time_patterns = [
        (r'^(\d{1,2})\s*am$', lambda h: (int(h) % 12, 0)),  # 1am -> (1, 0)
        (r'^(\d{1,2})\s*pm$', lambda h: ((int(h) % 12) + 12, 0)),  # 1pm -> (13, 0)
        (r'^(\d{1,2}):(\d{2})\s*am$', lambda h, m: (int(h) % 12, int(m))),  # 10:30am -> (10, 30)
        (r'^(\d{1,2}):(\d{2})\s*pm$', lambda h, m: ((int(h) % 12) + 12, int(m))),  # 2:30pm -> (14, 30)
        (r'^(\d{1,2}):(\d{2})$', lambda h, m: (int(h), int(m)))  # 14:30 -> (14, 30)
    ]

    for pattern, time_func in time_patterns:
        match = re.match(pattern, start_at_str)
        if match:
            if len(match.groups()) == 1:
                hour, minute = time_func(match.group(1))
            else:
                hour, minute = time_func(match.group(1), match.group(2))

            # Create target time for today
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # If the time has already passed today, schedule for tomorrow
            if target_time <= now:
                target_time += timedelta(days=1)

            return target_time

    # If no pattern matches, raise an error
    raise ValueError(f"Invalid start time format: '{start_at_str}'. "
                    f"Supported formats: '2h' (2 hours), '30m' (30 minutes), '14:30' (2:30 PM), '1am', '2:30pm'")

def create_default_instances(output_format: str = "stream-json") -> List[InstanceConfig]:
    """Create default instance configurations"""
    return [
        InstanceConfig(
            command="/gitcommitgardener",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/refreshgardener",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/createtestsv2 agent goldenpath messages work, unit",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/gcploggardener",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/createtestsv2 agent goldenpath messages work, integration",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/createtestsv2 agent goldenpath messages work, e2e",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/ssotgardener message routing",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/ssotgardener websockets or auth",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/ssotgardener tests",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/ssotgardener removing legacy",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/ssotgardener agent goldenpath messages work",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/gcploggardener",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/gitissueprogressorv3 agents",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/gitissueprogressorv3 p0",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/gitissueprogressorv3 agents",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/gitissueprogressorv3 goldenpath",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/gitissueprogressorv3 tests p1",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/failingtestsgardener agents",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/failingtestsgardener critical",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/gcploggardener",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/ssotgardener removing legacy",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/gitissueprogressorv3 removing legacy",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/testgardener",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/runtests all, unit",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/runtests critical, e2e",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/runtests all, integration",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/runtests agents, e2e gcp",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/prmergergit",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/gitcommitgardener",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/gcploggardener",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/ultimate-test-deploy-loop",
            permission_mode="acceptEdits",
            output_format=output_format
        )
    ]

async def main():
    """Main orchestrator function"""
    parser = argparse.ArgumentParser(description="Claude Code Instance Orchestrator")
    parser.add_argument("--workspace", type=str, default=None,
                       help="Workspace directory (default: current directory)")
    parser.add_argument("--output", type=Path, default=None,
                       help="Output file for results (default: auto-generated with datetime and agents)")
    parser.add_argument("--config", type=Path, help="Custom instance configuration file")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without running")
    parser.add_argument("--list-commands", action="store_true", help="List all available slash commands and exit")
    parser.add_argument("--inspect-command", type=str, help="Inspect a specific slash command and exit")
    parser.add_argument("--output-format", choices=["json", "stream-json"], default="stream-json",
                       help="Output format for Claude instances (default: stream-json)")
    parser.add_argument("--timeout", type=int, default=10000,
                       help="Timeout in seconds for each instance (default: 10000)")
    parser.add_argument("--max-console-lines", type=int, default=5,
                       help="Maximum recent lines to show per instance on console (default: 5)")
    parser.add_argument("--quiet", action="store_true",
                       help="Minimize console output, show only errors and final summaries")
    parser.add_argument("--startup-delay", type=float, default=5.0,
                       help="Delay in seconds between launching each instance (default: 5.0)")
    parser.add_argument("--max-line-length", type=int, default=800,
                       help="Maximum characters per line in console output (default: 500)")
    parser.add_argument("--status-report-interval", type=int, default=5,
                       help="Seconds between rolling status reports (default: 5)")
    parser.add_argument("--start-at", type=str, default=None,
                       help="Schedule orchestration to start at specific time. Examples: '2h' (2 hours from now), '30m' (30 minutes), '14:30' (2:30 PM today), '1am' (1 AM today/tomorrow)")
    parser.add_argument("--use-cloud-sql", action="store_true",
                       help="Save metrics to CloudSQL database (NetraOptimizer integration)")

    # Token budget arguments
    parser.add_argument("--overall-token-budget", type=int, default=None,
                       help="Global token budget for the entire session.")
    parser.add_argument("--command-budget", action='append',
                       help="Per-command budget in format: '/command_name=limit'. Can be used multiple times.")
    parser.add_argument("--budget-enforcement-mode", choices=["warn", "block"], default="warn",
                       help="Action to take when a budget is exceeded: 'warn' (log and continue) or 'block' (prevent new instances).")
    parser.add_argument("--disable-budget-visuals", action="store_true",
                       help="Disable budget visualization in status reports")

    args = parser.parse_args()

    # Determine workspace directory with better Mac compatibility
    if args.workspace:
        workspace = Path(args.workspace).expanduser().resolve()
    else:
        workspace = Path.cwd().resolve()
    
    # Verify workspace exists and is accessible
    if not workspace.exists():
        logger.error(f"Workspace directory does not exist: {workspace}")
        sys.exit(1)
    
    if not workspace.is_dir():
        logger.error(f"Workspace path is not a directory: {workspace}")
        sys.exit(1)
    
    # Check if it looks like a Claude Code workspace
    claude_dir = workspace / ".claude"
    if not claude_dir.exists():
        logger.warning(f"No .claude directory found in workspace: {workspace}")
        logger.warning("This might not be a Claude Code workspace")
    
    logger.info(f"Using workspace: {workspace}")

    # Initialize orchestrator with console output settings
    max_lines = 0 if args.quiet else args.max_console_lines
    orchestrator = ClaudeInstanceOrchestrator(
        workspace,
        max_console_lines=max_lines,
        startup_delay=args.startup_delay,
        max_line_length=args.max_line_length,
        status_report_interval=args.status_report_interval,
        use_cloud_sql=args.use_cloud_sql,
        quiet=args.quiet,
        overall_token_budget=args.overall_token_budget,
        budget_enforcement_mode=args.budget_enforcement_mode,
        enable_budget_visuals=not args.disable_budget_visuals
    )

    # Process per-command budgets
    if orchestrator.budget_manager and args.command_budget:
        for budget_str in args.command_budget:
            try:
                command_name, limit = budget_str.split('=', 1)
                # Keep command name as is - don't let it be expanded as path
                command_name = command_name.strip()
                orchestrator.budget_manager.set_command_budget(command_name, int(limit))
                logger.info(f"Set budget for {command_name} to {limit} tokens.")
            except ValueError:
                logger.error(f"Invalid format for --command-budget: '{budget_str}'. Use '/command=limit'.")

    # Handle command inspection modes
    if args.list_commands:
        print("Available Slash Commands:")
        print("=" * 50)
        commands = orchestrator.discover_available_commands()
        for cmd in commands:
            cmd_info = orchestrator.inspect_command(cmd)
            if cmd_info.get("exists"):
                frontmatter = cmd_info.get("frontmatter", {})
                description = frontmatter.get("description", "No description available")
                print(f"{cmd:25} - {description}")
            else:
                print(f"{cmd:25} - Built-in command")
        return

    if args.inspect_command:
        cmd_info = orchestrator.inspect_command(args.inspect_command)
        print(f"Command: {args.inspect_command}")
        print("=" * 50)
        if cmd_info.get("exists"):
            print(f"File: {cmd_info.get('file_path')}")
            if cmd_info.get("frontmatter"):
                print("Configuration:")
                for key, value in cmd_info["frontmatter"].items():
                    print(f"  {key}: {value}")
            print("\nContent Preview:")
            print(cmd_info.get("content_preview", "No content available"))
        else:
            print("Command not found or is a built-in command")
        return

    # Load instance configurations
    if args.config and args.config.exists():
        logger.info(f"Loading config from {args.config}")
        with open(args.config) as f:
            config_data = json.load(f)
        instances = [InstanceConfig(**inst) for inst in config_data["instances"]]
    else:
        logger.info("Using default instance configurations")
        instances = create_default_instances(args.output_format)

    # Add instances to orchestrator
    for instance in instances:
        orchestrator.add_instance(instance)

    if args.dry_run:
        logger.info("DRY RUN MODE - Commands that would be executed:")
        for name, config in orchestrator.instances.items():
            cmd = orchestrator.build_claude_command(config)
            print(f"{name}: {' '.join(cmd)}")

        # Show budget configuration if enabled
        if orchestrator.budget_manager:
            from token_budget.visualization import render_progress_bar
            bm = orchestrator.budget_manager
            print(f"\n=== TOKEN BUDGET CONFIGURATION ===")

            if bm.overall_budget:
                print(f"Overall Budget: {bm.overall_budget:,} tokens")
            else:
                print(f"Overall Budget: Unlimited")

            print(f"Enforcement Mode: {bm.enforcement_mode.upper()}")

            if bm.command_budgets:
                print(f"Command Budgets:")
                for name, budget_info in bm.command_budgets.items():
                    print(f"  {name:<30} {budget_info.limit:,} tokens")
            else:
                print(f"Command Budgets: None configured")

            print(f"=====================================\n")

        # Show scheduled start time if provided
        if args.start_at:
            try:
                target_time = parse_start_time(args.start_at)
                wait_seconds = (target_time - datetime.now()).total_seconds()
                logger.info(f"Orchestration would be scheduled to start at: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"Wait time would be: {wait_seconds:.1f} seconds ({wait_seconds/3600:.1f} hours)")
            except ValueError as e:
                logger.error(f"Invalid start time: {e}")
        return

    # Handle scheduled start time
    if args.start_at:
        try:
            target_time = parse_start_time(args.start_at)
            now = datetime.now()
            wait_seconds = (target_time - now).total_seconds()

            if wait_seconds <= 0:
                logger.warning(f"Target time {target_time.strftime('%Y-%m-%d %H:%M:%S')} is in the past, starting immediately")
            else:
                logger.info(f"Orchestration scheduled to start at: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"Waiting {wait_seconds:.1f} seconds ({wait_seconds/3600:.1f} hours) until start time...")

                # Show countdown for long waits
                if wait_seconds > 60:
                    # Show periodic countdown updates
                    countdown_intervals = [3600, 1800, 900, 300, 60, 30, 10]  # 1h, 30m, 15m, 5m, 1m, 30s, 10s

                    while wait_seconds > 0:
                        # Find the next appropriate countdown interval
                        next_update = None
                        for interval in countdown_intervals:
                            if wait_seconds > interval:
                                next_update = interval
                                break

                        if next_update:
                            sleep_time = wait_seconds - next_update
                            await asyncio.sleep(sleep_time)
                            wait_seconds = next_update
                            hours = wait_seconds // 3600
                            minutes = (wait_seconds % 3600) // 60
                            seconds = wait_seconds % 60
                            if hours > 0:
                                logger.info(f"Orchestration starts in {int(hours)}h {int(minutes)}m")
                            elif minutes > 0:
                                logger.info(f"Orchestration starts in {int(minutes)}m {int(seconds)}s")
                            else:
                                logger.info(f"Orchestration starts in {int(seconds)}s")
                        else:
                            # Final countdown
                            await asyncio.sleep(wait_seconds)
                            wait_seconds = 0
                else:
                    # For short waits, just sleep
                    await asyncio.sleep(wait_seconds)

                logger.info("Scheduled start time reached - beginning orchestration")
        except ValueError as e:
            logger.error(f"Invalid start time: {e}")
            sys.exit(1)

    # Run all instances
    logger.info("Starting Claude Code instance orchestration")
    if args.use_cloud_sql:
        logger.info(f"Batch ID: {orchestrator.batch_id}")
        logger.info("Metrics will be saved to CloudSQL")
    start_time = time.time()

    results = await orchestrator.run_all_instances(args.timeout)

    end_time = time.time()
    total_duration = end_time - start_time

    # Print summary with token usage
    summary = orchestrator.get_status_summary()
    total_tokens = sum(status.total_tokens for status in orchestrator.statuses.values())
    total_cached = sum(status.cached_tokens for status in orchestrator.statuses.values())
    total_tool_calls = sum(status.tool_calls for status in orchestrator.statuses.values())
    cache_rate = round(total_cached / max(total_tokens, 1) * 100, 1) if total_tokens > 0 else 0

    logger.info(f"Orchestration completed in {total_duration:.2f}s")
    logger.info(f"Results: {summary['completed']} completed, {summary['failed']} failed")
    logger.info(f"Token Usage: {total_tokens:,} total ({total_cached:,} cached, {cache_rate}% hit rate), {total_tool_calls} tool calls")

    # Save results (will auto-generate filename if args.output is None)
    orchestrator.save_results(args.output)

    # Print detailed results
    print("\n" + "="*60)
    print("CLAUDE CODE INSTANCE ORCHESTRATOR RESULTS")
    print("="*60)

    for name, status in orchestrator.statuses.items():
        print(f"\n{name.upper()}:")
        print(f"  Status: {status.status}")
        if status.start_time and status.end_time:
            duration = status.end_time - status.start_time
            print(f"  Duration: {duration:.2f}s")

        # Show token usage
        if status.total_tokens > 0 or status.input_tokens > 0 or status.output_tokens > 0 or status.cached_tokens > 0:
            print(f"  Tokens: {status.total_tokens:,} total")
            if status.input_tokens > 0 or status.output_tokens > 0:
                print(f"          {status.input_tokens:,} input, {status.output_tokens:,} output")
            if status.cached_tokens > 0:
                print(f"          {status.cached_tokens:,} cached")

        if status.tool_calls > 0:
            print(f"  Tool Calls: {status.tool_calls}")

        if status.output:
            print(f"  Output Preview: {status.output[:200]}...")

        if status.error:
            print(f"  Errors: {status.error[:200]}...")

    # Show the actual filename used (important when auto-generated)
    final_output_file = args.output or orchestrator.generate_output_filename()
    print(f"\nFull results saved to: {final_output_file}")

    # Show CloudSQL info if enabled
    if args.use_cloud_sql:
        print(f"\n📊 Metrics saved to CloudSQL")
        print(f"   Batch ID: {orchestrator.batch_id}")
        print(f"   View metrics with:")
        print(f"   psql -h localhost -p 5434 -U postgres -d netra_optimizer -c \"SELECT * FROM command_executions WHERE batch_id = '{orchestrator.batch_id}';\"")

    # Exit with appropriate code
    sys.exit(0 if summary['failed'] == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())