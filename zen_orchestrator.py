#!/usr/bin/env python3
"""
Usage Examples:

  zen -h  # Help

Direct Command Execution:
  zen "/single-command-in-claude-commands"  # Execute single command directly
  zen "/analyze-code" --workspace ~/my-project
  zen "/debug-issue" --instance-name "debug-session"
  zen "/optimize-performance" --session-id "perf-1"
  zen "/generate-docs" --clear-history --compact-history

Configuration File Mode:
  zen --config config.json
  zen --config config.json --workspace ~/my-project

Default Instances Mode:
  zen --dry-run  # Auto-detects workspace from project root
  zen --workspace ~/my-project --dry-run  # Override workspace
  zen --startup-delay 2.0  # 2 second delay between launches
  zen --startup-delay 0.5  # 0.5 second delay between launches
  zen --max-line-length 1000  # Longer output lines
  zen --status-report-interval 60  # Status reports every 60s
  zen --quiet  # Minimal output, errors only

Command Discovery:
  zen --list-commands  # Show all available commands
  zen --inspect-command "/analyze-code"  # Inspect specific command

Scheduling:
  zen "/analyze-code" --start-at "2h"  # Start 2 hours from now
  zen "/debug-issue" --start-at "30m"  # Start in 30 minutes
  zen "/optimize" --start-at "1am"  # Start at 1 AM (today or tomorrow)
  zen "/review-code" --start-at "14:30"  # Start at 2:30 PM (today or tomorrow)
  zen "/generate-docs" --start-at "10:30pm"  # Start at 10:30 PM (today or tomorrow)

Precedence Rules:
  1. Direct command (highest) - zen "/command"
  2. Config file (medium) - zen --config file.json    # expected default usage pattern
  3. Default instances (lowest) - zen
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
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
from datetime import datetime, timedelta
import re
from uuid import uuid4, UUID
from enum import Enum

try:
    from zen.telemetry import telemetry_manager
except Exception:  # pragma: no cover - telemetry optional
    telemetry_manager = None

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

# Add token transparency imports
try:
    from token_transparency import ClaudePricingEngine, TokenUsageData
except ImportError as e:
    # Graceful fallback if token transparency package is not available
    ClaudePricingEngine = None
    TokenUsageData = None


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LogLevel(Enum):
    """Log level configuration for zen orchestrator output"""
    SILENT = "silent"      # Errors and final summary only
    CONCISE = "concise"    # Essential progress + budget alerts (DEFAULT)
    DETAILED = "detailed"  # All current logging

def determine_log_level(args) -> LogLevel:
    """Determine log level from arguments with backward compatibility."""
    # Check explicit log_level first (highest priority)
    if hasattr(args, 'log_level') and args.log_level:
        return LogLevel[args.log_level.upper()]
    elif hasattr(args, 'quiet') and args.quiet:
        return LogLevel.SILENT
    elif hasattr(args, 'verbose') and args.verbose:
        return LogLevel.DETAILED
    else:
        return LogLevel.CONCISE  # New default

@dataclass
class InstanceConfig:
    """Configuration for a Claude Code instance"""
    command: Optional[str] = None  # For slash commands like /help
    prompt: Optional[str] = None   # For raw prompts like "What are the available commands?"
    name: Optional[str] = None
    description: Optional[str] = None
    allowed_tools: List[str] = None
    permission_mode: str = None  # Will be set based on platform
    output_format: str = "stream-json"  # Default to stream-json for real-time output
    session_id: Optional[str] = None
    clear_history: bool = False
    compact_history: bool = False
    pre_commands: List[str] = None  # Commands to run before main command
    max_tokens_per_command: Optional[int] = None  # Token budget for this specific command

    def __post_init__(self):
        """Set defaults after initialization"""
        # Validate that either command or prompt is provided
        if not self.command and not self.prompt:
            raise ValueError("Either 'command' or 'prompt' must be provided")

        # If both are provided, prioritize command over prompt
        if self.command and self.prompt:
            # Use command, but log that prompt is being ignored
            pass  # This is valid - command takes precedence

        # If only prompt is provided, treat it as the command for execution
        elif self.prompt and not self.command:
            self.command = self.prompt

        # Set default name
        if self.name is None:
            if self.command and self.command.startswith('/'):
                self.name = self.command
            else:
                # For prompts, create a shorter name
                display_text = self.prompt or self.command
                self.name = display_text[:30] + "..." if len(display_text) > 30 else display_text

        # Set default description
        if self.description is None:
            if self.command and self.command.startswith('/'):
                self.description = f"Execute {self.command}"
            else:
                self.description = f"Execute prompt: {(self.prompt or self.command)[:50]}..."

        # Set permission mode if not explicitly set
        if self.permission_mode is None:
            # Default to bypassPermissions for all platforms to avoid approval prompts
            # This is not OS-specific - it's a general permission configuration
            self.permission_mode = "bypassPermissions"

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

    # NEW: Model tracking for transparency
    model_used: str = "claude-sonnet-4"  # Default model

    # NEW: Tool usage details
    tool_details: Dict[str, int] = None  # Tool name -> usage count
    tool_tokens: Dict[str, int] = None   # Tool name -> token usage
    tool_id_mapping: Dict[str, str] = field(default_factory=dict)  # tool_use_id -> tool name mapping
    telemetry_recorded: bool = False

    def __post_init__(self):
        """Initialize fields that need special handling"""
        if self.processed_message_ids is None:
            self.processed_message_ids = set()
        if self.tool_details is None:
            self.tool_details = {}
        if self.tool_tokens is None:
            self.tool_tokens = {}
        if self.tool_id_mapping is None:
            self.tool_id_mapping = {}

class ClaudeInstanceOrchestrator:
    """Orchestrator for managing multiple Claude Code instances"""

    def __init__(self, workspace_dir: Path, max_console_lines: int = 5, startup_delay: float = 1.0,
                 max_line_length: int = 500, status_report_interval: int = 30,
                 quiet: bool = False,
                 overall_token_budget: Optional[int] = None,
                 overall_cost_budget: Optional[float] = None,
                 budget_type: str = "tokens",
                 budget_enforcement_mode: str = "warn",
                 enable_budget_visuals: bool = True,
                 has_command_budgets: bool = False,
                 log_level: LogLevel = LogLevel.CONCISE):
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
        self.quiet = quiet
        self.log_level = log_level
        self.batch_id = str(uuid4())  # Generate batch ID for this orchestration run
        
        self.optimizer = None

        # Initialize budget manager if any budget settings are provided
        needs_budget_manager = (overall_token_budget is not None) or (overall_cost_budget is not None) or has_command_budgets
        if TokenBudgetManager and needs_budget_manager:
            # Cost budget takes precedence over token budget
            if overall_cost_budget is not None:
                self.budget_manager = TokenBudgetManager(
                    overall_cost_budget=overall_cost_budget,
                    enforcement_mode=budget_enforcement_mode,
                    budget_type=budget_type
                )
                logger.info(f"🎯 COST BUDGET MANAGER initialized with ${overall_cost_budget} overall budget")
            else:
                self.budget_manager = TokenBudgetManager(
                    overall_budget=overall_token_budget,  # Can be None
                    enforcement_mode=budget_enforcement_mode,
                    budget_type=budget_type
                )
                if overall_token_budget:
                    logger.info(f"🎯 TOKEN BUDGET MANAGER initialized with {overall_token_budget} token overall budget")
        else:
            self.budget_manager = None
        self.enable_budget_visuals = enable_budget_visuals

        # Initialize token transparency pricing engine
        if ClaudePricingEngine:
            self.pricing_engine = ClaudePricingEngine()
            logger.info("🎯 Token transparency pricing engine enabled - Claude pricing compliance active")
        else:
            self.pricing_engine = None
            logger.debug("Token transparency pricing engine disabled (module not available)")

        # Log budget configuration status
        if self.budget_manager:
            budget_msg = f"Overall: {overall_token_budget:,} tokens" if overall_token_budget else "No overall limit"
            logger.info(f"🎯 Token budget tracking enabled - {budget_msg} | Mode: {budget_enforcement_mode.upper()}")
        else:
            logger.debug("Token budget tracking disabled (no budget specified)")


    def log_at_level(self, level: LogLevel, message: str, log_func=None):
        """Log message only if current log level permits."""
        if log_func is None:
            log_func = logger.info

        if self.log_level == LogLevel.SILENT and log_func != logger.error:
            return
        elif self.log_level == LogLevel.CONCISE and level == LogLevel.DETAILED:
            return

        log_func(message)

    def add_instance(self, config: InstanceConfig):
        """Add a new instance configuration"""
        # Determine if this is a slash command or raw prompt
        is_slash_command = config.command and config.command.startswith('/')
        is_raw_prompt = config.prompt and not is_slash_command

        if is_slash_command:
            # Validate slash command exists
            if not self.validate_command(config.command):
                logger.warning(f"Command '{config.command}' not found in available commands")
                logger.info(f"Available commands: {', '.join(self.discover_available_commands())}")
        elif is_raw_prompt:
            logger.info(f"Using raw prompt: {config.prompt[:50]}{'...' if len(config.prompt) > 50 else ''}")

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
        # IMPORTANT: Use direct paths to avoid shell functions that may have database dependencies
        possible_paths = [
            "/opt/homebrew/bin/claude",  # Mac Homebrew ARM - prefer direct path
            "/usr/local/bin/claude",     # Mac Homebrew Intel
            "~/.local/bin/claude",       # User local install
            "/usr/bin/claude",           # System install
            "claude.cmd",                # Windows
            "claude.exe",                # Windows
        ]

        claude_cmd = None
        for path in possible_paths:
            # Expand user path if needed
            expanded_path = Path(path).expanduser()
            if expanded_path.exists() and expanded_path.is_file():
                claude_cmd = str(expanded_path)
                logger.info(f"Found Claude executable at: {claude_cmd}")
                break

        # Only use shutil.which as fallback if no direct path found
        if not claude_cmd:
            claude_cmd = shutil.which("claude")
            if claude_cmd:
                logger.info(f"Found Claude executable via which: {claude_cmd}")

        if not claude_cmd:
            logger.warning("Claude command not found in PATH or common locations")
            logger.warning("Please ensure Claude Code is installed and in your PATH")
            logger.warning("Install with: npm install -g @anthropic/claude-code")
            claude_cmd = "/opt/homebrew/bin/claude"  # Default fallback to most likely location

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
            # ISSUE #1348 FIX: Use consistent command matching logic for budget checking
            # Match the same logic used in _update_budget_tracking for consistency
            if config.command and config.command.strip().startswith('/'):
                # For slash commands, check if budget exists for base command vs full command
                base_command_part = config.command.split()[0] if config.command else config.command
                # Check if budget exists for base command, otherwise use full command
                if base_command_part in self.budget_manager.command_budgets:
                    budget_check_key = base_command_part
                else:
                    budget_check_key = config.command
            else:
                # For non-slash commands/prompts, always use the full command text as budget key
                budget_check_key = config.command if config.command else config.command

            base_command = budget_check_key

            logger.info(f"🎯 Budget check for {name}: command={base_command}, estimated={estimated_tokens} tokens")

            can_run, reason = self.budget_manager.check_budget(base_command, estimated_tokens)
            if not can_run:
                message = f"Budget exceeded for instance {name}: {reason}. Skipping."
                if self.budget_manager.enforcement_mode == "block":
                    logger.error(f"🚫 BLOCK MODE: {message}")
                    status.status = "failed"
                    status.error = f"Blocked by budget limit - {reason}"
                    timestamp = time.time()
                    if status.start_time is None:
                        status.start_time = timestamp
                    status.end_time = timestamp
                    self._emit_instance_telemetry(name, config, status)
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
            logger.info(f"Permission mode: {config.permission_mode} (Platform: {platform.system()})")

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
            # Database persistence disabled - metrics preserved in local display only
            if False:  # CloudSQL functionality removed
                await self._save_metrics_to_database(name, config, status)

            if returncode == 0:
                status.status = "completed"
                logger.info(f"Instance {name} completed successfully")
                self._emit_instance_telemetry(name, config, status)
                return True
            else:
                status.status = "failed"
                logger.error(f"Instance {name} failed with return code {returncode}")
                if status.error:
                    logger.error(f"Error output: {status.error}")
                self._emit_instance_telemetry(name, config, status)
                return False

        except Exception as e:
            status.status = "failed"
            status.error = str(e)
            logger.error(f"Exception running instance {name}: {e}")
            status.end_time = status.end_time or time.time()
            self._emit_instance_telemetry(name, config, status)
            return False

    async def _save_metrics_to_database(self, name: str, config: InstanceConfig, status: InstanceStatus):
        """Database persistence has been removed for security. Metrics are displayed locally only."""
        # CloudSQL functionality removed for security and simplicity
        # Token metrics are preserved in the local display
        logger.debug(f"Metrics for {name} available in local display only (database persistence disabled)")

    def _calculate_cost(self, status: InstanceStatus) -> float:
        """Calculate cost with Claude pricing compliance engine and proper cache handling"""

        # Use authoritative cost if available (preferred)
        if status.total_cost_usd is not None:
            return status.total_cost_usd

        # Use pricing engine if available
        if self.pricing_engine and TokenUsageData:
            # Create usage data from status
            usage_data = TokenUsageData(
                input_tokens=status.input_tokens,
                output_tokens=status.output_tokens,
                cache_read_tokens=status.cache_read_tokens,
                cache_creation_tokens=status.cache_creation_tokens,
                total_tokens=status.total_tokens,
                cache_type="5min",  # Default to 5min cache
                model=status.model_used  # Use detected model
            )

            cost_breakdown = self.pricing_engine.calculate_cost(
                usage_data,
                status.total_cost_usd,
                status.tool_tokens  # Include tool token costs
            )
            return cost_breakdown.total_cost

        # Fallback calculation with current pricing (legacy support)
        # Claude 3.5 Sonnet current rates (as of 2024-2025)
        input_cost = (status.input_tokens / 1_000_000) * 3.00    # $3 per M input tokens
        output_cost = (status.output_tokens / 1_000_000) * 15.00  # $15 per M output tokens

        # Cache costs with CORRECTED pricing based on Claude documentation
        cache_read_cost = (status.cache_read_tokens / 1_000_000) * (3.00 * 0.1)  # 10% of input rate
        cache_creation_cost = (status.cache_creation_tokens / 1_000_000) * (3.00 * 1.25)  # 5min cache: 25% premium

        # Tool costs (fallback calculation)
        tool_cost = 0.0
        if status.tool_tokens:
            for tool_name, tokens in status.tool_tokens.items():
                tool_cost += (tokens / 1_000_000) * 3.00  # Tool tokens at input rate

        return input_cost + output_cost + cache_read_cost + cache_creation_cost + tool_cost

    def _emit_instance_telemetry(self, name: str, config: InstanceConfig, status: InstanceStatus) -> None:
        """Send telemetry span with token usage and cost metadata."""

        if telemetry_manager is None or not hasattr(telemetry_manager, "is_enabled"):
            return

        if getattr(status, "telemetry_recorded", False):
            return

        if not telemetry_manager.is_enabled():
            return

        cost_usd: Optional[float]
        try:
            cost_usd = self._calculate_cost(status)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.debug(f"Cost calculation failed for telemetry span ({name}): {exc}")
            cost_usd = None

        try:
            telemetry_manager.record_instance_span(
                batch_id=self.batch_id,
                instance_name=name,
                status=status,
                config=config,
                cost_usd=cost_usd,
                workspace=str(self.workspace_dir),
            )
            status.telemetry_recorded = True
        except Exception as exc:  # pragma: no cover - Network/export errors
            logger.debug(f"Telemetry emission failed for {name}: {exc}")

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
            instance_header = f"+=[{name}]" + "=" * (20 - len(name) - 4) if len(name) < 16 else f"+=[{name}]="
            if prefix:
                instance_header += f" {prefix} "

            return f"{instance_header}\n| {content}\n+" + "=" * (len(instance_header) - 1)

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
                final_header = f"+=== FINAL OUTPUT [{name}] ===+"
                print(f"\n{final_header}")
                print(f"| Last {len(recent_lines_buffer)} lines of {line_count} total")
                print(f"| Status: {status.status}")
                if status.start_time:
                    duration = time.time() - status.start_time
                    print(f"| Duration: {duration:.1f}s")
                print("+" + "=" * (len(final_header) - 2) + "+\n")

            # Always show completion message with clear formatting
            completion_msg = f"🏁 [{name}] COMPLETED - {line_count} lines processed, output saved"
            print(f"\n{'='*60}")
            print(f"{completion_msg}")
            print(f"{'='*60}\n")

            # Note: StreamReader objects in asyncio don't have .close() method
            # They are automatically closed when the process terminates

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
        # NOTE: Do NOT add status reporter to main tasks list - it runs indefinitely
        if len(tasks) > 0 and not self.max_console_lines == 0:  # Don't show status in quiet mode
            self.status_report_task = asyncio.create_task(self._rolling_status_reporter())

        # Wait for all instance tasks to complete (not the status reporter)
        logger.debug(f"⏳ Waiting for {len(tasks)} instance tasks to complete...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug("✅ All instance tasks completed")

        # Stop the status reporter - CRITICAL: This prevents hanging
        if hasattr(self, 'status_report_task') and self.status_report_task and not self.status_report_task.done():
            logger.debug("🛑 Cancelling status reporter task...")
            self.status_report_task.cancel()
            try:
                await self.status_report_task
                logger.debug("✅ Status reporter task cancelled successfully")
            except asyncio.CancelledError:
                logger.debug("✅ Status reporter task cancellation confirmed")
                pass
            except Exception as e:
                logger.warning(f"⚠️ Error cancelling status reporter: {e}")
        else:
            logger.debug("ℹ️ No status reporter task to cancel")

        # Ensure all processes are cleaned up
        await self._cleanup_all_processes()

        final_results = {}
        for name, result in zip(self.instances.keys(), results):
            if isinstance(result, asyncio.TimeoutError):
                logger.error(f"Instance {name} timed out after {timeout}s")
                status = self.statuses[name]
                status.status = "failed"
                status.error = f"Timeout after {timeout}s"
                status.end_time = time.time()
                self._emit_instance_telemetry(name, self.instances[name], status)
                final_results[name] = False
            elif isinstance(result, Exception):
                logger.error(f"Instance {name} failed with exception: {result}")
                status = self.statuses[name]
                status.status = "failed"
                status.error = str(result)
                status.end_time = time.time()
                self._emit_instance_telemetry(name, self.instances[name], status)
                final_results[name] = False
            else:
                final_results[name] = result

        return final_results

    async def _cleanup_all_processes(self):
        """Ensure all processes are properly cleaned up to prevent hanging"""
        logger.debug("🧹 Cleaning up all processes...")

        for name, status in self.statuses.items():
            if status.pid and status.status == "running":
                try:
                    import signal
                    import os
                    logger.debug(f"🛑 Cleaning up hanging process for {name} (PID: {status.pid})")
                    os.kill(status.pid, signal.SIGTERM)
                except (OSError, ProcessLookupError):
                    # Process already terminated
                    pass
                except Exception as e:
                    logger.warning(f"⚠️ Error cleaning up process {status.pid}: {e}")

        # Clear the processes dict
        if hasattr(self, 'processes'):
            self.processes.clear()

        logger.debug("✅ Process cleanup completed")

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

    def _get_budget_display(self, instance_name: str) -> str:
        """Get budget display string for an instance (e.g., '1.2K/5K' or '-' if no budget)"""
        if not self.budget_manager:
            return "-"

        # Get the command for this instance
        if instance_name not in self.instances:
            return "-"

        command = self.instances[instance_name].command

        # ISSUE #1348 FIX: Use same command matching logic as _update_budget_tracking
        if command and command.strip().startswith('/'):
            # For slash commands, check if budget exists for base command vs full command
            base_command_part = command.rstrip(';').split()[0] if command else command
            # Check if budget exists for base command, otherwise use full command
            if base_command_part in self.budget_manager.command_budgets:
                budget_display_key = base_command_part
            else:
                budget_display_key = command.rstrip(';')
        else:
            # For non-slash commands/prompts, always use the full command text as budget key
            budget_display_key = command.rstrip(';') if command else command

        base_command = budget_display_key

        # Check if this command has a budget
        if base_command not in self.budget_manager.command_budgets:
            return "-"

        budget_info = self.budget_manager.command_budgets[base_command]
        used_formatted = self._format_tokens(budget_info.used)
        limit_formatted = self._format_tokens(budget_info.limit)

        return f"{used_formatted}/{limit_formatted}"

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
        header = f"+=== {report_type} [{datetime.now().strftime('%H:%M:%S')}] ===+"
        print(f"\n{header}")
        print(f"| Total: {len(self.statuses)} instances")
        print(f"| Running: {status_counts['running']}, Completed: {status_counts['completed']}, Failed: {status_counts['failed']}, Pending: {status_counts['pending']}")

        # Show token usage summary
        total_tokens_all = sum(s.total_tokens for s in self.statuses.values())
        total_cached_all = sum(s.cached_tokens for s in self.statuses.values())
        total_tools_all = sum(s.tool_calls for s in self.statuses.values())
        median_str = self._format_tokens(int(token_median)) if token_median > 0 else "0"
        print(f"| Tokens: {self._format_tokens(total_tokens_all)} total, {self._format_tokens(total_cached_all)} cached | Median: {median_str} | Tools: {total_tools_all}")

        # --- ADD COST TRANSPARENCY SECTION ---
        if self.pricing_engine:
            total_cost = sum(self._calculate_cost(s) for s in self.statuses.values())
            avg_cost_per_instance = total_cost / len(self.statuses) if self.statuses else 0
            print(f"| 💰 Cost: ${total_cost:.4f} total, ${avg_cost_per_instance:.4f} avg/instance | Pricing: Claude compliant")

        # --- ADD BUDGET STATUS SECTION ---
        if self.budget_manager and self.enable_budget_visuals and render_progress_bar:
            bm = self.budget_manager
            used_formatted = self._format_tokens(bm.total_usage)

            print(f"|")
            print(f"| TOKEN BUDGET STATUS |")

            if bm.overall_budget is not None:
                overall_bar = render_progress_bar(bm.total_usage, bm.overall_budget)
                total_formatted = self._format_tokens(bm.overall_budget)
                print(f"| Overall: {overall_bar} {used_formatted}/{total_formatted}")
            else:
                print(f"| Overall: [UNLIMITED] {used_formatted} used")

            if bm.command_budgets:
                print(f"| Command Budgets:")
                for name, budget_info in bm.command_budgets.items():
                    bar = render_progress_bar(budget_info.used, budget_info.limit)
                    limit_formatted = self._format_tokens(budget_info.limit)
                    used_cmd_formatted = self._format_tokens(budget_info.used)
                    print(f"|\t\t\t {name:<20} {bar} {used_cmd_formatted}/{limit_formatted}")
            else:
                print(f"| Command Budgets: None configured")

        print(f"| ")
        print(f"|  📝 Model shows actual Claude model used (critical for accurate cost tracking)")
        print(f"|  💡 Tip: Model may differ from your config - Claude routes requests intelligently")        
        # Print column headers with separated cache metrics
        print(f"|  {'Status':<8} {'Name':<30} {'Model':<10} {'Duration':<10} {'Overall':<8} {'Tokens':<8} {'Cache Cr':<8} {'Cache Rd':<8} {'Tools':<6} {'Budget':<10}")
        print(f"|  {'-'*8} {'-'*30} {'-'*10} {'-'*10} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*6} {'-'*10}")


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

            # Format separated token information for user-friendly display
            # CHANGE LOG (v1.2.0): Separated cache metrics display for better cost visibility
            # - Overall: Shows complete token count (input + output + cache_read + cache_creation)
            # - Tokens: Shows only core processing tokens (input + output)
            # - Cache Cr: Shows cache creation tokens (expensive - the "golden ticket")
            # - Cache Rd: Shows cache read tokens (cheap)
            # - Formula: Overall = Tokens + Cache Cr + Cache Rd (detailed breakdown)

            # Overall = total_tokens (which includes input + output + cache_read + cache_creation)
            overall_tokens = self._format_tokens(status.total_tokens) if status.total_tokens > 0 else "0"

            # Tokens = input + output only (core processing tokens)
            core_tokens = status.input_tokens + status.output_tokens
            tokens_info = self._format_tokens(core_tokens) if core_tokens > 0 else "0"

            # Cache Creation = cache_creation_tokens (expensive "golden ticket" tokens)
            cache_creation_info = self._format_tokens(status.cache_creation_tokens) if status.cache_creation_tokens > 0 else "0"

            # Cache Read = cache_read_tokens (cheap cache hits)
            cache_read_info = self._format_tokens(status.cache_read_tokens) if status.cache_read_tokens > 0 else "0"

            tool_info = str(status.tool_calls) if status.tool_calls > 0 else "0"

            # Format model name for display
            model_short = status.model_used.replace('claude-', '').replace('-', '') if status.model_used else "unknown"

            # Get budget information for this instance
            budget_info = self._get_budget_display(name)

            # Create detailed line with separated cache metrics
            detail = f"  {emoji:<8} {name:<30} {model_short:<10} {time_info:<10} {overall_tokens:<8} {tokens_info:<8} {cache_creation_info:<8} {cache_read_info:<8} {tool_info:<6} {budget_info:<10}"

            print(f"|{detail}")

        footer = "+" + "=" * (len(header) - 2) + "+"
        print(f"{footer}")

        # --- ADD DETAILED TOOL USAGE TABLE WITH TOKENS AND COSTS ---
        all_tools = {}
        for status in self.statuses.values():
            for tool_name, count in status.tool_details.items():
                if tool_name not in all_tools:
                    all_tools[tool_name] = {"count": 0, "tokens": 0, "instances": []}
                all_tools[tool_name]["count"] += count
                all_tools[tool_name]["tokens"] += status.tool_tokens.get(tool_name, 0)

                # Format instance info with tokens if available
                tool_tokens = status.tool_tokens.get(tool_name, 0)
                if tool_tokens > 0:
                    all_tools[tool_name]["instances"].append(f"{status.name}({count} uses, {tool_tokens} tok)")
                else:
                    all_tools[tool_name]["instances"].append(f"{status.name}({count} uses)")


        if all_tools:
            print(f"\n+=== TOOL USAGE DETAILS ===+")
            print(f"| {'Tool Name':<20} {'Uses':<8} {'Tokens':<10} {'Cost ($)':<10} {'Used By':<35}")
            print(f"| {'-'*20} {'-'*8} {'-'*10} {'-'*10} {'-'*35}")

            total_tool_uses = 0
            total_tool_tokens = 0
            total_tool_cost = 0.0

            for tool_name, details in sorted(all_tools.items()):
                tool_count = details["count"]
                tool_tokens = details["tokens"]

                # Calculate tool cost at current model rates (3.5 sonnet input rate)
                tool_cost = (tool_tokens / 1_000_000) * 3.00 if tool_tokens > 0 else 0.0

                instances_str = ", ".join(details["instances"][:2])  # Show first 2 instances
                if len(details["instances"]) > 2:
                    instances_str += f" +{len(details['instances'])-2} more"

                token_str = f"{tool_tokens:,}" if tool_tokens > 0 else "0"
                cost_str = f"{tool_cost:.4f}" if tool_cost > 0 else "0"

                print(f"| {tool_name:<20} {tool_count:<8} {token_str:<10} {cost_str:<10} {instances_str:<35}")

                total_tool_uses += tool_count
                total_tool_tokens += tool_tokens
                total_tool_cost += tool_cost

            print(f"| {'-'*20} {'-'*8} {'-'*10} {'-'*10} {'-'*35}")
            total_tokens_str = f"{total_tool_tokens:,}" if total_tool_tokens > 0 else "0"
            total_cost_str = f"{total_tool_cost:.4f}" if total_tool_cost > 0 else "0"
            print(f"| {'TOTAL':<20} {total_tool_uses:<8} {total_tokens_str:<10} {total_cost_str:<10}")
            print(f"+{'='*95}+")

        print()

    def _detect_permission_error(self, line: str, status: InstanceStatus, instance_name: str) -> bool:
        """Detect permission errors and command blocking issues - Issue #1320 fix"""
        line_stripped = line.strip()
        if not line_stripped:
            return False

        # Try to parse as JSON first
        if line_stripped.startswith('{'):
            try:
                json_data = json.loads(line_stripped)

                # Check for permission errors in tool results
                if json_data.get('type') == 'user' and 'message' in json_data:
                    message = json_data.get('message', {})
                    if isinstance(message, dict) and 'content' in message:
                        content_list = message.get('content', [])
                        if isinstance(content_list, list):
                            for item in content_list:
                                if isinstance(item, dict) and item.get('type') == 'tool_result':
                                    if item.get('is_error'):
                                        error_content = item.get('content', '')
                                        if any(phrase in error_content.lower() for phrase in [
                                            'requires approval',
                                            'permission denied',
                                            'haven\'t granted it yet',
                                            'claude requested permissions'
                                        ]):
                                            # CRITICAL ERROR - Make it VERY visible
                                            error_msg = f"""
+============================================================================+
| 🚨🚨🚨 PERMISSION ERROR DETECTED - COMMAND BLOCKED 🚨🚨🚨                  |
| Instance: {instance_name:<60}|
| Error: {error_content[:68]:<68}|
+============================================================================+
| SOLUTION: zen_orchestrator.py now uses bypassPermissions by default:        |
|   • Default: bypassPermissions (avoids approval prompts on all platforms)   |
|   • Users can override via permission_mode in config if needed              |
|                                                                              |
| Current platform: {platform.system():<58}|
| Using permission mode: {self.instances[instance_name].permission_mode:<52}|
+============================================================================+
"""
                                            print(error_msg, flush=True)
                                            logger.critical(f"PERMISSION ERROR in {instance_name}: {error_content}")
                                            status.error += f"\n[PERMISSION ERROR]: {error_content}\n"
                                            return True
            except json.JSONDecodeError:
                pass

        # Check for text-based error patterns
        line_lower = line.lower()
        if any(phrase in line_lower for phrase in [
            'this command requires approval',
            'permission denied',
            'access denied',
            'not authorized',
            'insufficient permissions'
        ]):
            error_msg = f"""
+============================================================================+
| ⚠️  PERMISSION WARNING DETECTED                                             |
| Instance: {instance_name:<60}|
| Line: {line_stripped[:70]:<70}|
+============================================================================+
"""
            print(error_msg, flush=True)
            logger.warning(f"Permission warning in {instance_name}: {line_stripped}")
            return True

        return False

    def _parse_token_usage(self, line: str, status: InstanceStatus, instance_name: str):
        """Parse token usage information from Claude Code JSON output lines"""
        # FIRST: Check for permission errors (Issue #1320)
        if self._detect_permission_error(line, status, instance_name):
            return  # Don't parse tokens if there's an error

        # DEBUG: Log lines with potential token information
        if line.strip() and any(keyword in line.lower() for keyword in ['token', 'usage', 'total', 'input', 'output']):
            self.log_at_level(LogLevel.DETAILED, f"🔍 TOKEN PARSE [{instance_name}]: {line[:100]}{'...' if len(line) > 100 else ''}", logger.debug)

        # Track previous total for delta detection
        prev_total = status.total_tokens

        # First try to parse as JSON - this is the modern approach for stream-json format
        if self._try_parse_json_token_usage(line, status):
            # Check if tokens actually changed
            if status.total_tokens != prev_total:
                self.log_at_level(LogLevel.DETAILED, f"✅ JSON PARSE SUCCESS [{instance_name}]: tokens {prev_total} → {status.total_tokens}")
            self._update_budget_tracking(status, instance_name)
            return

        # Fallback to regex parsing for backward compatibility or non-JSON output
        self._parse_token_usage_fallback(line, status)

        # Check if tokens changed in fallback parsing
        if status.total_tokens != prev_total:
            logger.info(f"✅ REGEX PARSE SUCCESS [{instance_name}]: tokens {prev_total} → {status.total_tokens}")

        self._update_budget_tracking(status, instance_name)

    def _update_budget_tracking(self, status: InstanceStatus, instance_name: str):
        """Update budget tracking with token deltas and check for runtime budget violations"""
        # Use total_tokens which already includes all token types (input + output + cache_read + cache_creation)
        current_billable_tokens = status.total_tokens

        # Extract command information
        command = self.instances[instance_name].command
        # ISSUE #1348 FIX: Use full command as budget key to match config file command_budgets
        # This ensures tokens are recorded under the same key that budgets are configured with
        if command and command.strip().startswith('/'):
            # For slash commands, check if budget exists for base command vs full command
            base_command_part = command.rstrip(';').split()[0] if command else command
            # Check if budget exists for base command, otherwise use full command
            if self.budget_manager and base_command_part in self.budget_manager.command_budgets:
                budget_key = base_command_part
                logger.debug(f"🎯 SLASH COMMAND: Using base command '{base_command_part}' for budget (found in budgets)")
            else:
                budget_key = command.rstrip(';')
                logger.debug(f"🎯 SLASH COMMAND: Using full command '{budget_key}' for budget (base not found)")
        else:
            # For non-slash commands/prompts, always use the full command text as budget key
            budget_key = command.rstrip(';') if command else command
            logger.debug(f"🎯 RAW COMMAND: Using full command '{budget_key}' for budget tracking")

        # Use budget_key for all operations instead of base_command
        base_command = budget_key

        # ENHANCED DEBUG: Log budget tracking state
        logger.debug(f"🔍 BUDGET DEBUG [{instance_name}]: command='{base_command}', current_tokens={current_billable_tokens}, last_known={status._last_known_total_tokens}")

        # Check if this command has a budget configured
        if self.budget_manager and base_command in self.budget_manager.command_budgets:
            budget_info = self.budget_manager.command_budgets[base_command]
            logger.debug(f"🎯 BUDGET FOUND [{instance_name}]: {base_command} has budget {budget_info.used}/{budget_info.limit} ({budget_info.percentage:.1f}%)")
        elif self.budget_manager:
            logger.debug(f"⚠️ NO BUDGET [{instance_name}]: command '{base_command}' not in budget keys: {list(self.budget_manager.command_budgets.keys())}")

        if self.budget_manager and current_billable_tokens > status._last_known_total_tokens:
            new_tokens = current_billable_tokens - status._last_known_total_tokens

            self.log_at_level(LogLevel.CONCISE, f"💰 BUDGET UPDATE [{instance_name}]: Recording {new_tokens} tokens for command '{base_command}'")

            # Record the usage
            self.budget_manager.record_usage(base_command, new_tokens)
            status._last_known_total_tokens = current_billable_tokens

            # Log the new budget state
            if base_command in self.budget_manager.command_budgets:
                budget_info = self.budget_manager.command_budgets[base_command]
                self.log_at_level(LogLevel.CONCISE, f"📊 BUDGET STATE [{instance_name}]: {base_command} now at {budget_info.used}/{budget_info.limit} tokens ({budget_info.percentage:.1f}%)")

            # RUNTIME BUDGET ENFORCEMENT - Check if we've exceeded budgets during execution
            self._check_runtime_budget_violation(status, instance_name, base_command)
        elif self.budget_manager and current_billable_tokens == 0:
            logger.warning(f"🚫 NO TOKENS [{instance_name}]: total_tokens is still 0 - token detection may be failing")

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
                logger.error(f"🚫 🔴 RUNTIME TERMINATION: {message}")
                self._terminate_instance(status, instance_name, f"Terminated due to budget violation - {violation_reason}")
            else:  # warn mode
                # EXPLICIT YELLOW WARNING SYMBOLS FOR VISIBILITY
                logger.warning(f"🔶 ⚠️  🟡 BUDGET EXCEEDED WARNING: {message}")
                print(f"\n{'='*80}")
                print(f"🔶 ⚠️  🟡 BUDGET VIOLATION WARNING 🟡 ⚠️  🔶")
                print(f"Instance: {instance_name}")
                print(f"Reason: {violation_reason}")
                print(f"{'='*80}\n")

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

            # ADD DEBUG LOGGING FOR TOKEN PARSING
            logger.debug(f"🔍 TOKEN PARSING: Analyzing JSON line with keys: {list(json_data.keys())}")

            # Special debug for tool detection
            if 'type' in json_data:
                logger.debug(f"🎯 JSON TYPE: {json_data['type']}")
                if json_data['type'] == 'assistant' and 'message' in json_data:
                    message = json_data.get('message', {})
                    if isinstance(message, dict) and 'content' in message:
                        content = message.get('content', [])
                        if isinstance(content, list):
                            tool_types = [item.get('type') for item in content if isinstance(item, dict)]
                            logger.info(f"🎯 CONTENT TYPES: {tool_types}")

            # Check if this looks like a tool usage line
            if 'name' in json_data and ('type' in json_data and json_data['type'] in ['tool_use', 'tool_call']):
                logger.info(f"🎯 POTENTIAL TOOL: type={json_data.get('type')}, name={json_data.get('name')}")

            # Extract message ID for deduplication
            message_id = self._extract_message_id(json_data)

            if message_id:
                # SDK Rule: Skip if already processed this message ID
                if message_id in status.processed_message_ids:
                    logger.debug(f"Skipping duplicate message ID: {message_id}")
                    return True

                # Mark as processed
                status.processed_message_ids.add(message_id)

            # DETECT AND STORE MODEL NAME
            if self.pricing_engine:
                detected_model = self.pricing_engine.detect_model_from_response(json_data)
                if detected_model != status.model_used:
                    logger.debug(f"🤖 MODEL DETECTED: {detected_model} (was {status.model_used})")
                    status.model_used = detected_model

            # Process usage data (only once per message ID)
            usage_data = None
            if 'usage' in json_data:
                usage_data = json_data['usage']
                self.log_at_level(LogLevel.DETAILED, f"📊 TOKEN DATA: Found usage data: {usage_data}")
            elif 'message' in json_data and isinstance(json_data['message'], dict) and 'usage' in json_data['message']:
                usage_data = json_data['message']['usage']
                self.log_at_level(LogLevel.DETAILED, f"📊 TOKEN DATA: Found nested usage data: {usage_data}")
            elif 'tokens' in json_data and isinstance(json_data['tokens'], dict):
                # Handle structured token data format
                usage_data = json_data['tokens']
                self.log_at_level(LogLevel.DETAILED, f"📊 TOKEN DATA: Found tokens data: {usage_data}")
            else:
                # Check for direct token fields at the top level
                direct_tokens = {}
                for key in ['input_tokens', 'output_tokens', 'total_tokens', 'input', 'output', 'total']:
                    if key in json_data and isinstance(json_data[key], (int, float)):
                        direct_tokens[key] = json_data[key]

                if direct_tokens:
                    usage_data = direct_tokens
                    self.log_at_level(LogLevel.DETAILED, f"📊 TOKEN DATA: Found direct token fields: {usage_data}")
                else:
                    self.log_at_level(LogLevel.DETAILED, f"❌ NO TOKEN DATA: No usage fields found in JSON with keys: {list(json_data.keys())}", logger.debug)

            if usage_data and isinstance(usage_data, dict):
                # FIXED: Use cumulative addition for progressive token counts, not max()
                prev_input = status.input_tokens
                prev_output = status.output_tokens

                if 'input_tokens' in usage_data:
                    new_input = int(usage_data['input_tokens'])
                    status.input_tokens = max(status.input_tokens, new_input)  # Keep max for final totals
                elif 'input' in usage_data:  # Alternative format
                    new_input = int(usage_data['input'])
                    status.input_tokens = max(status.input_tokens, new_input)

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
                    prev_total = status.total_tokens

                    # BUDGET FIX: Handle both cumulative and individual message tokens
                    # If this looks like individual message tokens (has message_id), accumulate
                    # If this looks like cumulative session tokens (no message_id), use max
                    if message_id:
                        # Individual message - accumulate if it represents new work
                        status.total_tokens += total
                        logger.debug(f"🎯 TOTAL from 'total_tokens' (individual): {prev_total} + {total} → {status.total_tokens}")
                    else:
                        # Cumulative session total - use max to handle running totals
                        status.total_tokens = max(status.total_tokens, total)
                        logger.debug(f"🎯 TOTAL from 'total_tokens' (cumulative): {prev_total} → {status.total_tokens}")
                elif 'total' in usage_data:  # Alternative format
                    total = int(usage_data['total'])
                    prev_total = status.total_tokens

                    # BUDGET FIX: Same logic for alternative format
                    if message_id:
                        # Individual message - accumulate
                        status.total_tokens += total
                        logger.debug(f"🎯 TOTAL from 'total' (individual): {prev_total} + {total} → {status.total_tokens}")
                    else:
                        # Cumulative session total - use max
                        status.total_tokens = max(status.total_tokens, total)
                        logger.debug(f"🎯 TOTAL from 'total' (cumulative): {prev_total} → {status.total_tokens}")
                else:
                    # Calculate total from components if not provided
                    calculated_total = (status.input_tokens + status.output_tokens +
                                      status.cache_read_tokens + status.cache_creation_tokens)
                    prev_total = status.total_tokens
                    status.total_tokens = max(status.total_tokens, calculated_total)
                    logger.debug(f"🎯 TOTAL calculated: {prev_total} → {status.total_tokens} (input:{status.input_tokens} + output:{status.output_tokens} + cache_read:{status.cache_read_tokens} + cache_creation:{status.cache_creation_tokens})")

                # Store authoritative cost if available
                if 'total_cost_usd' in usage_data:
                    status.total_cost_usd = max(status.total_cost_usd or 0, float(usage_data['total_cost_usd']))

                # Update backward compatibility field
                self._update_cache_tokens_for_compatibility(status)

                # ADD DETAILED LOGGING FOR TOKEN UPDATES
                logger.debug(f"✅ TOKEN UPDATE: input={status.input_tokens}, output={status.output_tokens}, "
                           f"total={status.total_tokens}, cached={status.cached_tokens}")

                return True

            # Handle tool calls with detailed tracking
            if 'type' in json_data:
                logger.info(f"🔍 TOOL DETECTION: Found type='{json_data['type']}', checking for tool usage...")

                if json_data['type'] in ['tool_use', 'tool_call', 'tool_execution']:
                    # Extract tool name for detailed tracking (ALWAYS track, even without message_id)
                    tool_name = json_data.get('name', json_data.get('tool_name', 'unknown_tool'))
                    status.tool_details[tool_name] = status.tool_details.get(tool_name, 0) + 1
                    status.tool_calls += 1

                    logger.info(f"🔧 TOOL FOUND: {tool_name} (message_id={message_id})")

                    # Track tool token usage if available
                    tool_tokens = 0
                    if 'usage' in json_data and isinstance(json_data['usage'], dict):
                        tool_usage = json_data['usage']
                        tool_tokens = tool_usage.get('total_tokens',
                                    tool_usage.get('input_tokens', 0) + tool_usage.get('output_tokens', 0))
                    elif 'tokens' in json_data:
                        tool_tokens = int(json_data.get('tokens', 0))
                    elif 'token_usage' in json_data:
                        tool_tokens = int(json_data.get('token_usage', 0))

                    if tool_tokens > 0:
                        status.tool_tokens[tool_name] = status.tool_tokens.get(tool_name, 0) + tool_tokens
                        logger.info(f"🔧 TOOL TRACKED: {tool_name} (uses: {status.tool_details[tool_name]}, tokens: {status.tool_tokens[tool_name]})")
                    else:
                        logger.info(f"🔧 TOOL TRACKED: {tool_name} (uses: {status.tool_details[tool_name]}, no tokens)")
                    return True
                elif json_data['type'] == 'message' and 'tool_calls' in json_data:
                    # Count tool calls in message with token tracking
                    tool_calls = json_data['tool_calls']
                    logger.info(f"🔧 TOOL MESSAGE: Found tool_calls in message: {tool_calls}")
                    if isinstance(tool_calls, list):
                        for tool in tool_calls:
                            if isinstance(tool, dict):
                                tool_name = tool.get('name', tool.get('function', {}).get('name', 'unknown_tool'))
                                status.tool_details[tool_name] = status.tool_details.get(tool_name, 0) + 1

                                # Track tool tokens if available in tool data
                                tool_tokens = 0
                                if 'tokens' in tool:
                                    tool_tokens = int(tool['tokens'])
                                elif 'usage' in tool and isinstance(tool['usage'], dict):
                                    tool_usage = tool['usage']
                                    tool_tokens = tool_usage.get('total_tokens', 0)

                                if tool_tokens > 0:
                                    status.tool_tokens[tool_name] = status.tool_tokens.get(tool_name, 0) + tool_tokens
                                    logger.info(f"🔧 TOOL FROM MESSAGE: {tool_name} (tokens: {tool_tokens})")

                        status.tool_calls += len(tool_calls)
                    elif isinstance(tool_calls, (int, float)):
                        # When tool_calls is just a number, add generic tool entries
                        tool_count = int(tool_calls)
                        status.tool_calls += tool_count
                        # Add generic tool details so the table appears
                        generic_tool_name = "Claude_Tool"  # Generic name when specific name unavailable
                        status.tool_details[generic_tool_name] = status.tool_details.get(generic_tool_name, 0) + tool_count
                    return True
                elif json_data['type'] == 'assistant' and 'message' in json_data:
                    # Handle Claude Code format: {"type":"assistant","message":{"content":[{"type":"tool_use","name":"Task",...}]}}
                    message = json_data['message']
                    if isinstance(message, dict) and 'content' in message:
                        content = message['content']
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get('type') == 'tool_use':
                                    tool_name = item.get('name', 'unknown_tool')
                                    tool_use_id = item.get('id', '')

                                    # Store the mapping for later tool_result processing
                                    if tool_use_id:
                                        status.tool_id_mapping[tool_use_id] = tool_name

                                    status.tool_details[tool_name] = status.tool_details.get(tool_name, 0) + 1
                                    status.tool_calls += 1
                                    logger.info(f"🔧 TOOL FROM ASSISTANT CONTENT: {tool_name} (id: {tool_use_id})")
                            return True
                elif json_data['type'] == 'user' and 'message' in json_data:
                    # Handle Claude Code user messages with tool results: {"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"..."}]}}
                    message = json_data['message']
                    if isinstance(message, dict) and 'content' in message:
                        content = message['content']
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict):
                                    # Tool result indicates a tool was used
                                    if item.get('type') == 'tool_result' and 'tool_use_id' in item:
                                        # Use stored mapping if available, otherwise extract from content
                                        tool_use_id = item['tool_use_id']
                                        if tool_use_id in status.tool_id_mapping:
                                            tool_name = status.tool_id_mapping[tool_use_id]
                                        else:
                                            tool_name = self._extract_tool_name_from_result(item, tool_use_id)

                                        # Don't double-count if we already counted this in tool_use
                                        if tool_use_id not in status.tool_id_mapping:
                                            status.tool_details[tool_name] = status.tool_details.get(tool_name, 0) + 1
                                            status.tool_calls += 1

                                        # Estimate tool token usage based on content size
                                        tool_tokens = self._estimate_tool_tokens(item)
                                        if tool_tokens > 0:
                                            status.tool_tokens[tool_name] = status.tool_tokens.get(tool_name, 0) + tool_tokens
                                            logger.info(f"🔧 TOOL FROM USER CONTENT: {tool_name} (tool_use_id: {tool_use_id}, estimated_tokens: {tool_tokens})")
                                        else:
                                            logger.info(f"🔧 TOOL FROM USER CONTENT: {tool_name} (tool_use_id: {tool_use_id})")
                                    # Tool use in user message (request)
                                    elif item.get('type') == 'tool_use' and 'name' in item:
                                        tool_name = item.get('name', 'unknown_tool')
                                        status.tool_details[tool_name] = status.tool_details.get(tool_name, 0) + 1
                                        status.tool_calls += 1

                                        # Estimate tool token usage for tool use (typically smaller than results)
                                        tool_tokens = self._estimate_tool_tokens(item, is_tool_use=True)
                                        if tool_tokens > 0:
                                            status.tool_tokens[tool_name] = status.tool_tokens.get(tool_name, 0) + tool_tokens
                                            logger.info(f"🔧 TOOL USE FROM USER CONTENT: {tool_name} (estimated_tokens: {tool_tokens})")
                                        else:
                                            logger.info(f"🔧 TOOL USE FROM USER CONTENT: {tool_name}")
                            return True

            # Handle direct token fields at root level (without message ID - treat as individual message tokens)
            token_fields_found = False
            if not message_id:  # Only process these if no message ID (prevents double counting)
                if 'input_tokens' in json_data:
                    # BUDGET FIX: For direct fields without message_id, accumulate as individual messages
                    new_input = int(json_data['input_tokens'])
                    status.input_tokens += new_input
                    token_fields_found = True
                    logger.debug(f"🎯 DIRECT input_tokens: +{new_input} → {status.input_tokens}")
                if 'output_tokens' in json_data:
                    new_output = int(json_data['output_tokens'])
                    status.output_tokens += new_output
                    token_fields_found = True
                    logger.debug(f"🎯 DIRECT output_tokens: +{new_output} → {status.output_tokens}")
                if 'cached_tokens' in json_data:
                    cached_total = int(json_data['cached_tokens'])
                    status.cache_read_tokens += cached_total  # Accumulate cache tokens too
                    self._update_cache_tokens_for_compatibility(status)
                    token_fields_found = True
                    logger.debug(f"🎯 DIRECT cached_tokens: +{cached_total} → {status.cache_read_tokens}")
                if 'total_tokens' in json_data:
                    total = int(json_data['total_tokens'])
                    prev_total = status.total_tokens
                    status.total_tokens += total  # Accumulate total tokens
                    token_fields_found = True
                    logger.debug(f"🎯 DIRECT total_tokens: {prev_total} + {total} → {status.total_tokens}")
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
                
                logger.info(f"Parsed JSON final output: tokens={status.total_tokens}, tools={status.tool_calls}")
                
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

    def _extract_tool_name_from_result(self, tool_result: dict, tool_use_id: str) -> str:
        """Extract meaningful tool name from tool result using comprehensive Claude Code tool patterns"""
        try:
            content = tool_result.get('content', '')

            if isinstance(content, str):
                # Handle empty content first (successful commands with no output)
                if content == "" or content.strip() == "":
                    return 'Bash'

                content_lower = content.lower()

                # =============================================================================
                # PRIORITY PATTERNS - Check these FIRST before other tool patterns
                # =============================================================================

                # Permission/MCP Tools - Check this FIRST before other patterns that might match
                if any(pattern in content_lower for pattern in [
                    'claude requested permissions', 'haven\'t granted it yet',
                    'but you haven\'t granted it yet'
                ]):
                    return 'permission_request'

                # =============================================================================
                # CLAUDE CODE OFFICIAL TOOLS - Comprehensive Detection Patterns
                # =============================================================================

                # Task Tool - Agent spawning and management
                if any(pattern in content_lower for pattern in [
                    'agent', 'subagent', 'spawned', 'task completed', 'agent completed',
                    'general-purpose', 'statusline-setup', 'output-style-setup'
                ]):
                    return 'Task'

                # Bash Tool - Command execution (most comprehensive patterns)
                if (any(pattern in content_lower for pattern in [
                    # Git operations
                    'on branch', 'nothing to commit', 'git pull', 'working tree clean',
                    'commit', 'staged', 'untracked files', 'changes not staged',
                    'your branch', 'ahead of', 'behind', 'diverged',
                    'file changed', 'insertions', 'deletions', 'files changed',
                    'develop-', 'main-', 'feature-', 'bugfix-',
                    # Command outputs
                    'command', 'executed', 'permission denied', 'no such file or directory',
                    'command not found', 'usage:', 'process completed', 'exit code',
                    'killed', 'terminated',
                    # File system outputs
                    'rw-r--r--', 'drwxr-xr-x'
                ]) or content.startswith('$') or
                (content.startswith('total ') and '\n-rw' in content)):
                    return 'Bash'

                # Glob Tool - File pattern matching
                if (any(pattern in content_lower for pattern in [
                    'files found', 'pattern matching', 'glob', 'file pattern'
                ]) or (
                    # Single file path results (like "zen/zen_orchestrator.py")
                    len(content.strip()) < 200 and '/' in content and content.count('\n') == 0 and
                    not content.startswith('/') and any(content.endswith(ext) for ext in [
                        '.py', '.js', '.ts', '.json', '.md', '.txt', '.html', '.css', '.yml', '.yaml'
                    ])
                ) or (
                    # Multiple file listings
                    content.count('\n') > 5 and '/' in content and
                    not content.startswith('<!DOCTYPE') and not content.startswith('<html')
                )):
                    return 'Glob'

                # Grep Tool - Search operations
                if any(pattern in content_lower for pattern in [
                    'matches found', 'pattern', 'searched', 'grep', 'ripgrep', 'no matches',
                    'search', 'found', 'regex'
                ]):
                    return 'Grep'

                # LS Tool - Directory listings
                if (any(pattern in content_lower for pattern in [
                    'list_dir', 'directory listing', 'listing files'
                ]) or (content.startswith('total ') and '\n-rw' in content and 'drwx' in content)):
                    return 'LS'

                # Read Tool - File reading (comprehensive patterns)
                if (content.startswith('#!/usr/bin/env') or
                    any(pattern in content for pattern in [
                        'import ', 'def ', 'class ', 'function', 'const ', 'var ', 'let ',
                        'export ', 'module.exports', 'require(', '#include', 'package ',
                        'use ', 'fn ', 'struct ', 'impl ', 'trait '
                    ]) or
                    (len(content) > 1000 and any(word in content_lower for word in [
                        'function', 'class', 'import', 'def', 'module', 'export', 'const'
                    ])) or
                    (len(content) > 500 and not any(pattern in content_lower for pattern in [
                        'html', 'http', 'www', 'commit', 'staged', 'branch'
                    ]))):
                    return 'Read'

                # Edit Tool - File editing
                if (any(pattern in content_lower for pattern in [
                    'file has been updated', 'result of running', 'has been updated successfully'
                ]) or (
                    'edit' in content_lower and any(pattern in content_lower for pattern in [
                        'success', 'updated', 'modified', 'changed'
                    ])
                )):
                    return 'Edit'

                # MultiEdit Tool - Multiple file edits
                if any(pattern in content_lower for pattern in [
                    'edits have been applied', 'multiple edits', 'multiedit'
                ]) and 'edit' in content_lower:
                    return 'MultiEdit'

                # Write Tool - File creation
                if any(pattern in content_lower for pattern in [
                    'file created successfully', 'file written', 'written to', 'created successfully'
                ]):
                    return 'Write'

                # NotebookEdit Tool - Jupyter operations
                if any(pattern in content_lower for pattern in [
                    'notebook', 'jupyter', 'ipynb'
                ]) or (
                    'cell' in content_lower and any(pattern in content_lower for pattern in [
                        'executed', 'output', 'edit', 'code', 'markdown'
                    ])
                ):
                    return 'NotebookEdit'

                # WebFetch Tool - Web content fetching
                if (content.startswith('<!DOCTYPE') or content.startswith('<html') or
                    any(pattern in content_lower for pattern in [
                        'http://', 'https://', 'web content', 'webpage', 'url', 'website'
                    ]) or (
                        any(pattern in content_lower for pattern in ['http', 'web', 'fetch', 'url']) and
                        any(pattern in content_lower for pattern in ['request', 'response', 'content', 'page'])
                    )):
                    return 'WebFetch'

                # TodoWrite Tool - Task management (already has good patterns)
                if any(pattern in content_lower for pattern in [
                    'todos have been modified', 'todo list', 'task list', 'progress',
                    'todo', 'task', 'completed', 'in_progress', 'pending'
                ]):
                    return 'TodoWrite'

                # WebSearch Tool - Web searching
                if any(pattern in content_lower for pattern in [
                    'search results', 'web search', 'search query', 'internet search'
                ]) and any(pattern in content_lower for pattern in ['web', 'search', 'internet', 'query']):
                    return 'WebSearch'

                # BashOutput Tool - Background shell output
                if any(pattern in content_lower for pattern in [
                    'shell output', 'background', 'stdout', 'stderr', 'bash output'
                ]):
                    return 'BashOutput'

                # KillBash Tool - Shell termination
                if any(pattern in content_lower for pattern in [
                    'shell killed', 'terminated', 'killed shell', 'bash killed'
                ]):
                    return 'KillBash'

                # ExitPlanMode Tool - Plan mode exit
                if any(pattern in content_lower for pattern in [
                    'exit plan', 'plan mode', 'ready to code', 'plan', 'implementation'
                ]):
                    return 'ExitPlanMode'

                # MCP Tools - Model Context Protocol tools
                if 'mcp__' in content:
                    import re
                    mcp_match = re.search(r'mcp__[a-zA-Z_]+__[a-zA-Z_]+', content)
                    if mcp_match:
                        return mcp_match.group(0)


                # Code execution results
                if any(pattern in content_lower for pattern in [
                    'traceback', 'error:', 'exception', 'stack trace'
                ]):
                    return 'Execute'

                # Error-specific tool identification
                if any(pattern in content_lower for pattern in [
                    'eisdir: illegal operation on a directory', 'directory, read',
                    'is a directory', 'illegal operation on a directory'
                ]):
                    return 'Read'  # Read tool trying to read directory

                # Command approval/permission errors (often from Task tools)
                if any(pattern in content_lower for pattern in [
                    'this command requires approval', 'requires approval',
                    'command contains multiple operations'
                ]):
                    return 'Bash'

                # File size limit errors (Read tool)
                if any(pattern in content_lower for pattern in [
                    'file content', 'exceeds maximum allowed tokens',
                    'use offset and limit parameters'
                ]):
                    return 'Read'

                # =============================================================================
                # DEFAULT FALLBACK - Try to infer from content characteristics
                # =============================================================================

                # Very long text content - likely Read
                if len(content) > 3000:
                    return 'Read'

                # Medium text with code patterns - likely Read
                elif len(content) > 200 and any(pattern in content for pattern in [
                    '{', '}', '[', ']', '(', ')', ';', '=', '->', '=>'
                ]):
                    return 'Read'

                # Short technical content - likely command output (Bash)
                elif len(content) < 100 and any(char in content for char in ['$', '/', '-', '=']):
                    return 'Bash'

            # Check for error indicators
            if tool_result.get('is_error'):
                error_content = tool_result.get('content', '')
                if 'permission' in error_content.lower():
                    return 'permission_denied'
                elif 'not found' in error_content.lower():
                    return 'file_not_found'

        except Exception as e:
            # If pattern matching fails, fall back to tool_use_id
            pass

        # Enhanced fallback patterns for simple/minimal outputs before generic fallback
        content = tool_result.get('content', '')
        if isinstance(content, str) and content.strip():
            content_stripped = content.strip()
            content_lower = content_stripped.lower()

            # Simple git branch names (common in GitIssueProgressor)
            if (len(content_stripped) < 50 and
                any(branch in content_lower for branch in ['develop', 'main', 'feature', 'bugfix', 'release']) and
                '-' in content_stripped and not ' ' in content_stripped):
                return 'Bash'

            # Simple file paths or single values
            if (len(content_stripped) < 100 and
                ('/' in content_stripped or '.' in content_stripped) and
                not ' ' in content_stripped and not '\n' in content_stripped):
                return 'Bash'

            # Very short responses that are likely command outputs
            if len(content_stripped) < 20 and not any(char in content_stripped for char in ['<', '>', '{', '}']):
                return 'Bash'

            # GitHub issue URLs or numbers (from GitIssueProgressor)
            if ('github.com' in content_lower and 'issues' in content_lower) or \
               (content_stripped.isdigit() and len(content_stripped) <= 4):
                return 'WebFetch'

            # Date/time formats (common command outputs)
            if any(pattern in content_stripped for pattern in [
                '-', ':', 'UTC', 'GMT', 'AM', 'PM'
            ]) and (len(content_stripped.split()) <= 5):
                # Simple date/time patterns
                if any(char.isdigit() for char in content_stripped):
                    return 'Bash'

            # Import/success messages (from Python imports or similar)
            if any(pattern in content_lower for pattern in [
                'import', 'successful', 'successfully', '✅', 'completed', 'finished'
            ]):
                return 'Bash'

            # Absolute file paths
            if content_stripped.startswith('/') and len(content_stripped.split()) == 1:
                return 'Bash'

            # Any other single-line simple responses (catch-all for remaining cases)
            if '\n' not in content_stripped and len(content_stripped) < 100:
                return 'Bash'

        # Fallback to generic name with partial tool_use_id for tracking
        short_id = tool_use_id[-8:] if len(tool_use_id) > 8 else tool_use_id
        return f"tool_{short_id}"

    def _estimate_tool_tokens(self, tool_data: dict, is_tool_use: bool = False) -> int:
        """Estimate token usage for a tool based on content size"""
        try:
            if is_tool_use:
                # For tool_use, estimate based on input parameters
                input_data = tool_data.get('input', {})
                if isinstance(input_data, dict):
                    # Rough estimation: ~4 characters per token
                    text_content = str(input_data)
                    return max(10, len(text_content) // 4)  # Minimum 10 tokens for tool invocation
                return 10  # Base cost for tool invocation
            else:
                # For tool_result, estimate based on content size
                content = tool_data.get('content', '')
                if isinstance(content, str):
                    # Rough estimation: ~4 characters per token for output
                    base_tokens = len(content) // 4

                    # Add overhead for tool processing
                    overhead = 20  # Base overhead for tool execution

                    # Adjust based on content type
                    if len(content) > 5000:  # Large content (like file reads)
                        overhead += 50
                    elif len(content) > 1000:  # Medium content (like directory listings)
                        overhead += 20

                    return max(base_tokens + overhead, 25)  # Minimum 25 tokens for any tool result

                return 25  # Base tokens for tool result

        except Exception as e:
            # Fallback to base estimation if any errors occur
            return 15 if is_tool_use else 30

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
            status_dict = asdict(status)

            # Convert set to list for JSON serialization
            if isinstance(status_dict.get("processed_message_ids"), set):
                status_dict["processed_message_ids"] = list(status_dict["processed_message_ids"])

            summary["instances"][name] = status_dict
            summary[status.status] += 1

            # Add duration if completed
            if status.start_time and status.end_time:
                duration = status.end_time - status.start_time
                summary["instances"][name]["duration"] = f"{duration:.2f}s"

        return summary




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
            name="analyze-repo",
            command="/analyze-repository",
            description="Analyze the repository structure and codebase",
            # permission_mode will be auto-set based on platform
            output_format=output_format,
            max_tokens_per_command=5000
        ),
        InstanceConfig(
            name="help-overview",
            command="/README",
            description="Show project README and overview information",
            # permission_mode will be auto-set based on platform
            output_format=output_format,
            max_tokens_per_command=1000
        )
    ]

def create_direct_instance(args, workspace: Path) -> Optional[InstanceConfig]:
    """Create InstanceConfig from direct command arguments.

    Args:
        args: Parsed command line arguments
        workspace: Working directory path

    Returns:
        InstanceConfig if direct command provided, None otherwise

    Raises:
        SystemExit: If command validation fails
    """
    if not args.command:
        return None

    # Create temporary orchestrator to validate command
    # Note: We use minimal initialization since we only need command validation
    temp_orchestrator = ClaudeInstanceOrchestrator(
        workspace,
        max_console_lines=0,  # Minimal console output for validation
        startup_delay=0,
        quiet=True  # Suppress output during validation
    )

    # Validate command exists or allow as ad-hoc command
    available_commands = temp_orchestrator.discover_available_commands()
    is_predefined_command = args.command in available_commands

    if not is_predefined_command:
        # Allow as ad-hoc command - log for transparency
        logger.info(f"Using ad-hoc command: {args.command}")
        logger.info(f"Note: This is not a predefined command from .claude/commands/")
        logger.info(f"Available predefined commands: {', '.join(sorted(available_commands))}")
        logger.info("Use 'zen --list-commands' to see all predefined commands with descriptions")
    else:
        logger.debug(f"Using predefined command: {args.command}")

    # Generate instance name if not provided
    instance_name = args.instance_name
    if not instance_name:
        # Create readable name from command
        clean_command = args.command.strip('/')
        instance_name = f"direct-{clean_command}-{uuid4().hex[:8]}"

    # Generate description if not provided
    instance_description = args.instance_description
    if not instance_description:
        instance_description = f"Direct execution of {args.command}"

    # Create and return InstanceConfig
    return InstanceConfig(
        command=args.command,
        name=instance_name,
        description=instance_description,
        output_format=args.output_format,
        session_id=args.session_id,
        clear_history=args.clear_history,
        compact_history=args.compact_history,
        max_tokens_per_command=args.overall_token_budget
    )

async def main():
    """Main orchestrator function"""
    parser = argparse.ArgumentParser(description="Claude Code Instance Orchestrator")

    # Direct command argument (positional)
    parser.add_argument("command", nargs="?", help="Direct command to execute (e.g., '/analyze-code')")

    parser.add_argument("--workspace", type=str, default=None,
                       help="Workspace directory (default: auto-detect project root or current directory)")
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
    parser.add_argument("--log-level", choices=["silent", "concise", "detailed"], default=None,
                       help="Set log level: 'silent' (errors only), 'concise' (essential progress + budget alerts, default), 'detailed' (all logging)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable detailed logging (equivalent to --log-level detailed)")
    parser.add_argument("--startup-delay", type=float, default=5.0,
                       help="Delay in seconds between launching each instance (default: 5.0)")
    parser.add_argument("--max-line-length", type=int, default=800,
                       help="Maximum characters per line in console output (default: 500)")
    parser.add_argument("--status-report-interval", type=int, default=5,
                       help="Seconds between rolling status reports (default: 5)")
    parser.add_argument("--start-at", type=str, default=None,
                       help="Schedule orchestration to start at specific time. Examples: '2h' (2 hours from now), '30m' (30 minutes), '14:30' (2:30 PM today), '1am' (1 AM today/tomorrow)")

    # Direct command options
    parser.add_argument("--instance-name", type=str, help="Instance name for direct command execution")
    parser.add_argument("--instance-description", type=str, help="Instance description for direct command execution")
    parser.add_argument("--session-id", type=str, help="Session ID for direct command execution")
    parser.add_argument("--clear-history", action="store_true", help="Clear history before direct command execution")
    parser.add_argument("--compact-history", action="store_true", help="Compact history before direct command execution")

    # Token budget arguments
    parser.add_argument("--overall-token-budget", type=int, default=None,
                       help="Global token budget for the entire session.")
    parser.add_argument("--command-budget", action='append',
                       help="Per-command budget in format: '/command_name=limit'. Can be used multiple times.")
    parser.add_argument("--budget-enforcement-mode", choices=["warn", "block"], default="warn",
                       help="Action to take when a budget is exceeded: 'warn' (log and continue) or 'block' (prevent new instances).")
    parser.add_argument("--disable-budget-visuals", action="store_true",
                       help="Disable budget visualization in status reports")

    # Cost budget arguments (Issue #1347)
    parser.add_argument("--overall-cost-budget", type=float, default=None,
                       help="Global cost budget for the entire session in USD (e.g., --overall-cost-budget 10.50).")
    parser.add_argument("--command-cost-budget", action='append',
                       help="Per-command cost budget in format: '/command_name=cost'. Can be used multiple times (e.g., --command-cost-budget '/analyze=5.0').")
    parser.add_argument("--budget-parameter-type", choices=["tokens", "cost", "mixed"], default="tokens",
                       help="Type of budget parameters to use: 'tokens' (default, backward compatible), 'cost' (USD-based), or 'mixed' (both).")

    # New example and template commands
    parser.add_argument("--generate-example", type=str, metavar="TYPE",
                       help="Generate example configuration (data_analysis, code_review, content_creation, testing_workflow, migration_workflow, debugging_workflow)")
    parser.add_argument("--list-examples", action="store_true",
                       help="List all available example configurations")
    parser.add_argument("--show-prompt-template", action="store_true",
                       help="Show LLM prompt template for configuration generation")
    parser.add_argument("--apex", "-a", action="store_true",
                       help="Invoke Apex agent CLI (passes remaining args to scripts.agent_cli)")

    args = parser.parse_args()

    # Initialize config budget settings (will be populated if config file is loaded)
    config_budget_settings = {}

    # Determine workspace directory with auto-detection
    if args.workspace:
        workspace = Path(args.workspace).expanduser().resolve()
    else:
        # Auto-detect workspace: use parent directory of zen directory as default
        zen_script_path = Path(__file__).resolve()
        zen_dir = zen_script_path.parent

        # Check if zen is in a subdirectory of a larger project
        potential_root = zen_dir.parent

        # Look for common project indicators in parent directory
        project_indicators = ['.git', '.claude', 'package.json', 'setup.py', 'pyproject.toml', 'Cargo.toml']

        if any((potential_root / indicator).exists() for indicator in project_indicators):
            workspace = potential_root
            logger.info(f"Auto-detected project root as workspace: {workspace}")
        else:
            # Fallback to current working directory if no project indicators found
            workspace = Path.cwd().resolve()
            logger.info(f"Using current working directory as workspace: {workspace}")

        # If workspace is still the zen directory itself, use parent or current directory
        if workspace == zen_dir:
            workspace = zen_dir.parent if zen_dir.parent != zen_dir else Path.cwd().resolve()
    
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


    # Load instance configurations with direct command precedence
    direct_instance = create_direct_instance(args, workspace)

    if direct_instance:
        # Direct command mode - highest precedence
        instances = [direct_instance]
        logger.info(f"Executing direct command: {direct_instance.command}")

        # Load budget settings from config file if available (for direct command mode)
        if args.config and args.config.exists():
            logger.info(f"Loading budget configuration from {args.config} (direct command mode)")
            with open(args.config) as f:
                config_data = json.load(f)
            budget_config = config_data.get("budget", {})
            if budget_config:
                config_budget_settings = budget_config
                logger.info(f"Loaded budget configuration from config file: {budget_config}")
    elif args.config and args.config.exists():
        # Config file mode - second precedence
        logger.info(f"Loading config from {args.config}")
        with open(args.config) as f:
            config_data = json.load(f)
        instances = [InstanceConfig(**inst) for inst in config_data["instances"]]

        # Extract budget configuration from config file
        budget_config = config_data.get("budget", {})
        if budget_config:
            config_budget_settings = budget_config
            logger.info(f"Loaded budget configuration from config file: {budget_config}")
    else:
        # Default instances mode - lowest precedence
        logger.info("Using default instance configurations")
        instances = create_default_instances(args.output_format)

    # Determine final budget settings - CLI args override config file
    final_overall_budget = args.overall_token_budget
    final_overall_cost_budget = args.overall_cost_budget
    final_budget_type = args.budget_parameter_type
    final_enforcement_mode = args.budget_enforcement_mode
    final_enable_visuals = not args.disable_budget_visuals

    # Use config file values if CLI args weren't provided
    if final_overall_budget is None and "overall_budget" in config_budget_settings:
        final_overall_budget = config_budget_settings["overall_budget"]
        logger.info(f"Using overall token budget from config file: {final_overall_budget}")

    if final_overall_cost_budget is None and "overall_cost_budget" in config_budget_settings:
        final_overall_cost_budget = config_budget_settings["overall_cost_budget"]
        logger.info(f"Using overall cost budget from config file: ${final_overall_cost_budget}")

    if args.budget_parameter_type == "tokens" and "budget_type" in config_budget_settings:
        # Only use config if user didn't explicitly set CLI arg (default is "tokens")
        final_budget_type = config_budget_settings["budget_type"]
        logger.info(f"Using budget type from config file: {final_budget_type}")

    if args.budget_enforcement_mode == "warn" and "enforcement_mode" in config_budget_settings:
        # Only use config if user didn't explicitly set CLI arg (default is "warn")
        final_enforcement_mode = config_budget_settings["enforcement_mode"]
        logger.info(f"Using enforcement mode from config file: {final_enforcement_mode}")

    if not args.disable_budget_visuals and "disable_visuals" in config_budget_settings:
        # Only use config if user didn't explicitly disable visuals
        final_enable_visuals = not config_budget_settings["disable_visuals"]
        logger.info(f"Using budget visuals setting from config file: {final_enable_visuals}")

    # Cost budget takes precedence over token budget if both are specified
    final_budget_for_manager = final_overall_cost_budget if final_overall_cost_budget is not None else final_overall_budget
    final_budget_type_for_manager = "cost" if final_overall_cost_budget is not None else final_budget_type

    # Determine log level from arguments
    log_level = determine_log_level(args)

    # Initialize orchestrator with console output settings
    max_lines = 0 if args.quiet else args.max_console_lines

    # Check if command budgets are configured from config file or CLI args
    has_config_command_budgets = bool(config_budget_settings.get("command_budgets"))
    has_config_cost_budgets = bool(config_budget_settings.get("command_cost_budgets"))
    has_cli_command_budgets = bool(args.command_budget)
    has_cli_cost_budgets = bool(args.command_cost_budget)
    has_command_budgets = has_config_command_budgets or has_cli_command_budgets or has_config_cost_budgets or has_cli_cost_budgets

    orchestrator = ClaudeInstanceOrchestrator(
        workspace,
        max_console_lines=max_lines,
        startup_delay=args.startup_delay,
        max_line_length=args.max_line_length,
        status_report_interval=args.status_report_interval,
        quiet=args.quiet,
        overall_token_budget=final_overall_budget,
        overall_cost_budget=final_overall_cost_budget,
        budget_type=final_budget_type_for_manager,
        budget_enforcement_mode=final_enforcement_mode,
        enable_budget_visuals=final_enable_visuals,
        has_command_budgets=has_command_budgets,
        log_level=log_level
    )

    # Process per-command budgets from config file first, then CLI args (CLI overrides config)
    if orchestrator.budget_manager:
        # Load command budgets from config file
        config_command_budgets = config_budget_settings.get("command_budgets", {})
        for command_name, limit in config_command_budgets.items():
            try:
                orchestrator.budget_manager.set_command_budget(command_name, int(limit))
                logger.info(f"🎯 CONFIG BUDGET SET: {command_name} = {limit} tokens")
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid command budget in config file: '{command_name}={limit}': {e}")

        # Load command budgets from CLI args (these override config file)
        if args.command_budget:
            for budget_str in args.command_budget:
                try:
                    command_name, limit = budget_str.split('=', 1)
                    # Normalize command name by ensuring it starts with '/'
                    command_name = command_name.strip()
                    if not command_name.startswith('/'):
                        command_name = '/' + command_name

                    orchestrator.budget_manager.set_command_budget(command_name, int(limit))
                    logger.info(f"🎯 CLI BUDGET SET: {command_name} = {limit} tokens (overrides config)")

                    # DEBUG: Log all budget keys after setting
                    logger.debug(f"📋 ALL BUDGET KEYS: {list(orchestrator.budget_manager.command_budgets.keys())}")
                except ValueError:
                    logger.error(f"Invalid format for --command-budget: '{budget_str}'. Use '/command=limit'.")

        # Load cost budgets from config file
        config_command_cost_budgets = config_budget_settings.get("command_cost_budgets", {})
        for command_name, limit in config_command_cost_budgets.items():
            try:
                orchestrator.budget_manager.set_command_cost_budget(command_name, float(limit))
                logger.info(f"🎯 CONFIG COST BUDGET SET: {command_name} = ${limit}")
            except (ValueError, TypeError, AttributeError) as e:
                logger.error(f"Invalid command cost budget in config file: '{command_name}=${limit}': {e}")

        # Load cost budgets from CLI args (these override config file)
        if args.command_cost_budget:
            for budget_str in args.command_cost_budget:
                try:
                    command_name, limit = budget_str.split('=', 1)
                    # Normalize command name by ensuring it starts with '/'
                    command_name = command_name.strip()
                    if not command_name.startswith('/'):
                        command_name = '/' + command_name

                    orchestrator.budget_manager.set_command_cost_budget(command_name, float(limit))
                    logger.info(f"🎯 CLI COST BUDGET SET: {command_name} = ${limit} (overrides config)")

                    # DEBUG: Log all budget keys after setting
                    logger.debug(f"📋 ALL COST BUDGET KEYS: {list(orchestrator.budget_manager.command_budgets.keys())}")
                except ValueError:
                    logger.error(f"Invalid format for --command-cost-budget: '{budget_str}'. Use '/command=cost' (e.g., '/analyze=5.0').")
                except AttributeError:
                    logger.error("Cost budgets require enhanced TokenBudgetManager - feature may not be available.")

        # AUTO-BUDGET CREATION: Create command budgets from instance max_tokens_per_command
        # This ensures that max_tokens_per_command values from JSON configs automatically
        # create command budgets, solving the "None Configured" display issue
        logger.info("🔍 AUTO-BUDGET: Scanning instances for max_tokens_per_command values...")
        auto_created_count = 0
        for instance in instances:
            if instance.max_tokens_per_command is not None:
                # ISSUE #1348 FIX: Use the SAME logic as _update_budget_tracking for consistency
                # This is critical - the budget key must match what budget tracking uses
                if instance.command and instance.command.strip().startswith('/'):
                    # For slash commands, use base command for auto-budget (most common case)
                    command_key = instance.command.rstrip(';').split()[0] if instance.command else instance.command
                    logger.debug(f"🎯 AUTO-BUDGET: Slash command using base key: '{command_key}'")
                else:
                    # For non-slash commands/prompts, always use the full command text as budget key
                    command_key = instance.command.rstrip(';') if instance.command else instance.command
                    logger.info(f"🎯 AUTO-BUDGET: Raw command will use full text as key: '{instance.command[:50]}...'")

                # Only create auto-budget if no explicit budget already exists
                if command_key not in orchestrator.budget_manager.command_budgets:
                    orchestrator.budget_manager.set_command_budget(command_key, instance.max_tokens_per_command)
                    logger.info(f"🎯 AUTO-BUDGET CREATED: {command_key} = {instance.max_tokens_per_command} tokens (from max_tokens_per_command)")
                    auto_created_count += 1
                else:
                    logger.debug(f"🔄 AUTO-BUDGET SKIPPED: {command_key} already has explicit budget")

        if auto_created_count > 0:
            logger.info(f"✅ AUTO-BUDGET: Created {auto_created_count} automatic command budgets from max_tokens_per_command")
        else:
            logger.debug("📋 AUTO-BUDGET: No auto-budgets created (no max_tokens_per_command values found)")

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

    # Add cost transparency to final summary
    if orchestrator.pricing_engine:
        total_cost = sum(orchestrator._calculate_cost(status) for status in orchestrator.statuses.values())
        logger.info(f"💰 Total Cost: ${total_cost:.4f} (Claude pricing compliant)")

    # Note: ZEN provides summary only - upgrade to Apex for detailed data access

    # Print detailed results in table format
    print("\n" + "="*120)
    print("NETRA ZEN RESULTS")
    print("="*120)

    if orchestrator.statuses:
        # Table headers with separated cache metrics
        headers = ["Instance", "Status", "Duration", "Total Tokens", "Input", "Output", "Cache Cr", "Cache Rd", "Tools", "Cost"]
        col_widths = [20, 10, 10, 12, 8, 8, 8, 8, 6, 10]

        # Print header
        header_row = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, col_widths)) + " |"
        print("+" + "=" * (len(header_row) - 2) + "+")
        print(header_row)
        print("+" + "-" * (len(header_row) - 2) + "+")

        # Print data rows
        for name, status in orchestrator.statuses.items():
            # Prepare row data
            instance_name = name[:19] if len(name) > 19 else name
            status_str = status.status
            duration_str = f"{status.end_time - status.start_time:.1f}s" if status.start_time and status.end_time else "N/A"
            total_tokens_str = f"{status.total_tokens:,}" if status.total_tokens > 0 else "0"
            input_tokens_str = f"{status.input_tokens:,}" if status.input_tokens > 0 else "0"
            output_tokens_str = f"{status.output_tokens:,}" if status.output_tokens > 0 else "0"
            cache_creation_str = f"{status.cache_creation_tokens:,}" if status.cache_creation_tokens > 0 else "0"
            cache_read_str = f"{status.cache_read_tokens:,}" if status.cache_read_tokens > 0 else "0"
            tools_str = str(status.tool_calls) if status.tool_calls > 0 else "0"
            # Calculate cost - use the pricing engine
            if status.total_cost_usd is not None:
                cost_str = f"${status.total_cost_usd:.4f}"
            else:
                # Calculate cost using the pricing engine
                calculated_cost = orchestrator._calculate_cost(status)
                cost_str = f"${calculated_cost:.4f}" if calculated_cost > 0 else "N/A"

            row_data = [instance_name, status_str, duration_str, total_tokens_str, input_tokens_str,
                       output_tokens_str, cache_creation_str, cache_read_str, tools_str, cost_str]

            row = "| " + " | ".join(data.ljust(w) for data, w in zip(row_data, col_widths)) + " |"
            print(row)

        print("+" + "=" * (len(header_row) - 2) + "+")

        # Check for permission errors FIRST - Issue #1320
        permission_errors = []
        for name, status in orchestrator.statuses.items():
            if status.error and any(phrase in status.error.lower() for phrase in [
                'permission error', 'requires approval', 'permission denied'
            ]):
                permission_errors.append((name, status))

        # Display CRITICAL permission errors prominently
        if permission_errors:
            print(f"""
+============================================================================================+
| 🚨🚨🚨 CRITICAL: {len(permission_errors)} PERMISSION ERROR(S) DETECTED - COMMANDS WERE BLOCKED! 🚨🚨🚨    |
+============================================================================================+
| Platform: {platform.system():<80}|
| Permission Mode Used: {orchestrator.instances[permission_errors[0][0]].permission_mode if permission_errors else 'Unknown':<68}|
+============================================================================================+
""")
            for name, status in permission_errors:
                error_preview = status.error.replace('\n', ' ')[:70]
                print(f"| ❌ {name:<20} | {error_preview:<68} |")
            print(f"""+============================================================================================+
| SOLUTION: zen_orchestrator.py defaults to bypassPermissions to avoid approval prompts       |
|   • Default: bypassPermissions (works on all platforms)                                     |
|   • Users can override via permission_mode in config if needed                              |
|                                                                                              |
| If still seeing errors, manually set permission mode in your config or update Claude Code.  |
+============================================================================================+
""")

        # Print additional details if there are outputs or errors
        print("\nAdditional Details:")
        print("-" * 40)
        for name, status in orchestrator.statuses.items():
            has_details = False

            if status.output:
                if not has_details:
                    print(f"\n{name.upper()}:")
                    has_details = True
                print(f"  Output Preview: {status.output[:150]}...")

            if status.error:
                if not has_details:
                    print(f"\n{name.upper()}:")
                    has_details = True
                # Highlight permission errors differently
                if any(phrase in status.error.lower() for phrase in ['permission error', 'requires approval']):
                    print(f"  ⚠️  PERMISSION ERROR: {status.error[:150]}...")
                else:
                    print(f"  Errors: {status.error[:150]}...")

            if status.tool_calls > 0 and status.tool_details:
                if not has_details:
                    print(f"\n{name.upper()}:")
                    has_details = True
                print(f"  Tools Used ({status.tool_calls}): {', '.join(status.tool_details)}")
    else:
        print("No instances were processed.")

    # For detailed data access
    print("\n" + "="*80)
    print("🚀 Looking for more?")
    print("="*80)
    print("Explore Zen with Apex for the most effective AI Ops value for production AI.")
    print("")
    print("🌐 Learn more: https://netrasystems.ai/")
    print("="*80)


    # Flush telemetry before exit
    if telemetry_manager is not None and hasattr(telemetry_manager, "shutdown"):
        telemetry_manager.shutdown()

    # Exit with appropriate code
    sys.exit(0 if summary['failed'] == 0 else 1)

def run():
    """Synchronous wrapper for the main function to be used as console script entry point."""
    # Import version and log it at startup
    __version__ = "unknown"

    # Try different import methods to get the version
    try:
        # When run as a package
        import zen
        __version__ = zen.__version__
    except (ImportError, AttributeError):
        try:
            # When run from the zen directory
            from __init__ import __version__
        except ImportError:
            try:
                # Try relative import
                from . import __version__
            except ImportError:
                # Try to read version from __init__.py directly as last resort
                try:
                    import os
                    init_path = Path(__file__).parent / "__init__.py"
                    if init_path.exists():
                        with open(init_path) as f:
                            for line in f:
                                if line.startswith('__version__'):
                                    # Extract version from line like: __version__ = "1.0.9"
                                    __version__ = line.split('=')[1].strip().strip('"').strip("'")
                                    break
                except Exception:
                    pass

    # Log version information at startup
    logger.info(f"Starting zen version {__version__}")

    # Early check for --apex flag to delegate to agent_cli before main() processing
    if '--apex' in sys.argv or '-a' in sys.argv:
        # Delegate to agent_cli via subprocess to avoid dependency conflicts
        import subprocess
        import os

        # Filter sys.argv to remove 'zen' and '--apex'/'-a' flags
        # Keep all other arguments to pass through to agent_cli
        filtered_argv = [arg for arg in sys.argv[1:] if arg not in ('--apex', '-a')]

        # Set PYTHONPATH for optional advanced backend features
        # Note: The minimal shared/ module is vendored in zen repo (no external dependency)
        # PYTHONPATH is only needed for advanced backend features beyond basic agent_cli
        env = os.environ.copy()

        # Check if APEX_BACKEND_PATH env var is set (for GCP deployment)
        # Otherwise try ../netra-apex (for local development with advanced features)
        if 'APEX_BACKEND_PATH' in env:
            backend_paths = [env['APEX_BACKEND_PATH']]
        else:
            # Try to find netra-apex in parent directory (development mode)
            zen_parent = Path(__file__).parent.parent
            netra_apex = zen_parent / "netra-apex"
            if netra_apex.exists():
                # Add both netra-apex root and netra-apex/scripts for imports
                backend_paths = [str(netra_apex), str(netra_apex / "scripts")]
            else:
                # In GCP, backend modules might be in PYTHONPATH already
                backend_paths = []

        if backend_paths:
            paths_to_add = ":".join(backend_paths)
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = f"{paths_to_add}:{env['PYTHONPATH']}"
            else:
                env['PYTHONPATH'] = paths_to_add

        # Try to use telemetry wrapper for apex instances
        try:
            from zen.telemetry import run_apex_with_telemetry

            # Find agent_cli.py path
            import importlib.util
            spec = importlib.util.find_spec("scripts.agent_cli")
            if spec and spec.origin:
                agent_cli_path = spec.origin
                # Run with telemetry tracking
                exit_code = run_apex_with_telemetry(agent_cli_path, filtered_argv, env)
                sys.exit(exit_code)
        except (ImportError, AttributeError) as e:
            # Fallback to direct subprocess if telemetry unavailable
            pass

        # Fallback: Run agent_cli.py as a module (works in packaged installations)
        result = subprocess.run(
            [sys.executable, "-m", "scripts.agent_cli"] + filtered_argv,
            env=env
        )

        sys.exit(result.returncode)

    asyncio.run(main())

if __name__ == "__main__":
    run()
