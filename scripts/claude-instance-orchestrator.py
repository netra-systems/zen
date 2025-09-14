#!/usr/bin/env python3
"""
Claude Code Instance Orchestrator
Simple orchestrator for running 3 Claude Code instances in headless mode,
each executing specific slash commands.

Multi-platform support with enhanced Mac compatibility for local directories.

Mac-specific improvements:
- Auto-detects Claude executable in common Homebrew paths (/opt/homebrew/bin, /usr/local/bin)
- Adds Mac-specific paths to PATH environment automatically
- Enhanced workspace directory validation with tilde expansion
- Better error messages for Claude installation on Mac

Auto runs a set of parallel claude code instance commands
Saves having to manually sping up terminal windows
Path towards integration and automation
collects more data than human readable output, e.g. token use, tool use names etc

Usage Examples:
  python3 claude-instance-orchestrator.py --workspace ~/my-project --dry-run
  python3 claude-instance-orchestrator.py --list-commands
  python3 claude-instance-orchestrator.py --config config.json
  python3 claude-instance-orchestrator.py --startup-delay 2.0  # 2 second delay between launches
  python3 claude-instance-orchestrator.py --startup-delay 0.5  # 0.5 second delay between launches
  python3 claude-instance-orchestrator.py --max-line-length 1000  # Longer output lines
  python3 claude-instance-orchestrator.py --status-report-interval 60  # Status reports every 60s
  python3 claude-instance-orchestrator.py --quiet  # Minimal output, errors only

Features:
  - Soft startup: Configurable delay between instance launches to prevent resource contention
  - Rolling status reports: Periodic updates showing instance status, uptime, and token usage
  - Token tracking: Automatic parsing and tracking of Claude token usage per instance
    * Total tokens, input/output tokens, cached tokens, and cache hit rates
    * Real-time token consumption monitoring across all instances
  - Formatted output: Clear visual separation between instances with truncated lines
  - Tool call tracking: Counts tool executions across all instances

IDEAS
    Record and contrast tool use by command 
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
from datetime import datetime

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
    cached_tokens: int = 0
    tool_calls: int = 0

class ClaudeInstanceOrchestrator:
    """Orchestrator for managing multiple Claude Code instances"""

    def __init__(self, workspace_dir: Path, max_console_lines: int = 5, startup_delay: float = 1.0, max_line_length: int = 500, status_report_interval: int = 30):
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
                    status.output += stdout.decode() if isinstance(stdout, bytes) else stdout
                if stderr:
                    status.error += stderr.decode() if isinstance(stderr, bytes) else stderr

            status.end_time = time.time()

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

        def format_instance_line_for_display(content: str, prefix: str = "") -> str:
            """Format a line for VISUAL DISPLAY ONLY - does not affect background data collection"""
            # Create a copy for display formatting (original content preserved in status.output)
            display_content = content

            # Truncate ONLY for visual display - background keeps full content
            if len(display_content) > self.max_line_length:
                # Smart truncation for display - preserve important content
                if any(keyword in display_content.lower() for keyword in ['tokens', 'tool', 'completed', 'error', 'success']):
                    # Keep important lines longer for display
                    if len(display_content) > self.max_line_length * 2:
                        display_content = display_content[:self.max_line_length*2-3] + "..."
                else:
                    display_content = display_content[:self.max_line_length-3] + "..."

            # Create clear visual separation
            instance_header = f"╔═[{name}]" + "═" * (20 - len(name) - 4) if len(name) < 16 else f"╔═[{name}]═"
            if prefix:
                instance_header += f" {prefix} "

            return f"{instance_header}\n║ {display_content}\n╚" + "═" * (len(instance_header) - 1)

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

                    # FIRST: Always accumulate FULL output in status (background data collection)
                    # This happens REGARDLESS of display settings - captures everything
                    if prefix == "STDOUT":
                        status.output += line_str  # Full line with all content
                        # Parse token usage from the COMPLETE line
                        self._parse_token_usage(clean_line, status)
                    else:
                        status.error += line_str  # Full error content

                    # SECOND: Handle visual display (separate from data collection)
                    # Format line for display only (doesn't affect background data)
                    display_line = format_instance_line_for_display(clean_line, prefix)
                    recent_lines_buffer.append(display_line)

                    # Keep only the most recent display lines (visual buffer management)
                    if len(recent_lines_buffer) > self.max_console_lines:
                        recent_lines_buffer.pop(0)

                    # Determine if this line should be shown (visual display decision)
                    if self.max_console_lines > 0:
                        should_display = (
                            line_count % 5 == 0 or  # Every 5th line (increased frequency)
                            prefix == "STDERR" or    # All error lines
                            "completed" in clean_line.lower() or
                            "error" in clean_line.lower() or
                            "failed" in clean_line.lower() or
                            "success" in clean_line.lower() or
                            "tokens" in clean_line.lower() or  # Show token information
                            "tool" in clean_line.lower() or    # Show tool usage
                            len(clean_line) > 50  # Show substantial content
                        )

                        if should_display:
                            print(f"\n{display_line}\n", flush=True)
                    elif prefix == "STDERR":
                        # In quiet mode, still show errors (but background still captures all)
                        error_display = format_instance_line_for_display(clean_line, "ERROR")
                        print(f"\n{error_display}\n", flush=True)
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

    async def _print_status_report(self, final: bool = False):
        """Print a formatted status report of all instances"""
        if not self.statuses:
            return

        current_time = time.time()
        report_type = "FINAL STATUS" if final else "STATUS REPORT"

        # Create status summary
        status_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0}
        instance_details = []

        for name, status in self.statuses.items():
            status_counts[status.status] += 1

            # Calculate uptime/duration
            if status.start_time:
                if status.end_time:
                    duration = status.end_time - status.start_time
                    time_info = f"{duration:.1f}s"
                else:
                    uptime = current_time - status.start_time
                    time_info = f"{uptime:.1f}s uptime"
            else:
                time_info = "not started"

            # Status emoji
            emoji_map = {
                "pending": "⏳",
                "running": "🏃",
                "completed": "✅",
                "failed": "❌"
            }
            emoji = emoji_map.get(status.status, "❓")

            instance_details.append(f"  {emoji} {name:<20} {status.status:<10} {time_info}")

        # Print the report
        header = f"╔═══ {report_type} [{datetime.now().strftime('%H:%M:%S')}] ═══╗"
        print(f"\n{header}")
        print(f"║ Total: {len(self.statuses)} instances")
        print(f"║ Running: {status_counts['running']}, Completed: {status_counts['completed']}, Failed: {status_counts['failed']}, Pending: {status_counts['pending']}")

        # Show token usage summary
        total_tokens_all = sum(s.total_tokens for s in self.statuses.values())
        total_cached_all = sum(s.cached_tokens for s in self.statuses.values())
        total_tools_all = sum(s.tool_calls for s in self.statuses.values())
        print(f"║ Tokens: {total_tokens_all:,} total, {total_cached_all:,} cached | Tools: {total_tools_all}")
        print(f"║")

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
                    time_info = f"{duration:.1f}s"
                else:
                    uptime = current_time - status.start_time
                    time_info = f"{uptime:.1f}s up"
            else:
                time_info = "waiting"

            # Create detailed line with tokens and cache info
            token_info = f"{status.total_tokens:,}t" if status.total_tokens > 0 else "0t"
            cache_info = f"{status.cached_tokens:,}c" if status.cached_tokens > 0 else "0c"
            tool_info = f"{status.tool_calls}tc" if status.tool_calls > 0 else "0tc"

            detail = f"  {emoji} {name:<16} {status.status:<8} {time_info:<8} {token_info:<7} {cache_info:<6} {tool_info}"

            # Ensure the line fits within a reasonable width
            if len(detail) > 75:
                detail = detail[:72] + "..."
            print(f"║{detail}")

        footer = "╚" + "═" * (len(header) - 2) + "╝"
        print(f"{footer}\n")

    def _parse_token_usage(self, line: str, status: InstanceStatus):
        """Parse token usage information from Claude output lines"""
        line_lower = line.lower()

        # Look for various token usage patterns in Claude output
        import re

        # Pattern 1: "Used X tokens" or "X tokens used"
        token_match = re.search(r'(?:used|consumed)\s+(\d+)\s+tokens?|(?:(\d+)\s+tokens?\s+(?:used|consumed))', line_lower)
        if token_match:
            tokens = int(token_match.group(1) or token_match.group(2))
            status.total_tokens += tokens

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
            status.cached_tokens += int(cached_match.group(1))

        # Pattern 2c: Cache hit patterns
        cache_hit_match = re.search(r'cache\s+hit[:\s]+(\d+)\s+tokens?', line_lower)
        if cache_hit_match:
            status.cached_tokens += int(cache_hit_match.group(1))

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

        # Pattern 5: JSON format token usage (for stream-json output)
        if 'tokens' in line_lower and '{' in line and '}' in line:
            try:
                # Try to extract JSON and parse token info
                import json
                # Look for JSON-like structures containing token info
                json_match = re.search(r'\{[^{}]*"tokens"[^{}]*\}', line)
                if json_match:
                    json_data = json.loads(json_match.group())
                    if 'tokens' in json_data and isinstance(json_data['tokens'], (int, float)):
                        status.total_tokens += int(json_data['tokens'])
                    if 'cached_tokens' in json_data and isinstance(json_data['cached_tokens'], (int, float)):
                        status.cached_tokens += int(json_data['cached_tokens'])
                    if 'input_tokens' in json_data and isinstance(json_data['input_tokens'], (int, float)):
                        status.input_tokens += int(json_data['input_tokens'])
                    if 'output_tokens' in json_data and isinstance(json_data['output_tokens'], (int, float)):
                        status.output_tokens += int(json_data['output_tokens'])
            except (json.JSONDecodeError, ValueError):
                pass  # Ignore JSON parsing errors

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



def create_default_instances(output_format: str = "stream-json") -> List[InstanceConfig]:
    """Create default instance configurations"""
    return [
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
            command="/gitissueprogressorv3 agents p0",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            command="/gitissueprogressorv3 tests p0",
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
    parser.add_argument("--max-line-length", type=int, default=1500,
                       help="Maximum characters per line in console output (default: 1500)")
    parser.add_argument("--status-report-interval", type=int, default=5,
                       help="Seconds between rolling status reports (default: 30)")

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
        status_report_interval=args.status_report_interval
    )

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
        return

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
            # Show preview of FULL captured output (not truncated)
            output_preview = status.output[:500].replace('\n', ' ').strip()
            print(f"  Output Preview: {output_preview}...")

        if status.error:
            print(f"  Errors: {status.error[:200]}...")

    # Show the actual filename used (important when auto-generated)
    final_output_file = args.output or orchestrator.generate_output_filename()
    print(f"\nFull results saved to: {final_output_file}")

    # Exit with appropriate code
    sys.exit(0 if summary['failed'] == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())