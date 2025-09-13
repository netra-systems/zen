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
    name: str
    command: str
    description: str
    allowed_tools: List[str] = None
    permission_mode: str = "acceptEdits"
    output_format: str = "stream-json"  # Default to stream-json for real-time output
    session_id: Optional[str] = None
    clear_history: bool = False
    compact_history: bool = False
    pre_commands: List[str] = None  # Commands to run before main command

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

class ClaudeInstanceOrchestrator:
    """Orchestrator for managing multiple Claude Code instances"""

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.instances: Dict[str, InstanceConfig] = {}
        self.statuses: Dict[str, InstanceStatus] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self.start_datetime = datetime.now()

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

        async def read_stream(stream, prefix):
            try:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    line_str = line.decode() if isinstance(line, bytes) else line

                    # Print with instance name prefix for clarity
                    print(f"[{name}] {prefix}: {line_str.strip()}", flush=True)

                    # Accumulate output in status
                    if prefix == "STDOUT":
                        status.output += line_str
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
            # Ensure streams are properly closed
            if process.stdout and not process.stdout.at_eof():
                process.stdout.close()
            if process.stderr and not process.stderr.at_eof():
                process.stderr.close()

    async def run_all_instances(self, timeout: int = 300) -> Dict[str, bool]:
        """Run all instances concurrently with timeout"""
        logger.info(f"Starting {len(self.instances)} instances concurrently (timeout: {timeout}s)")

        tasks = [
            asyncio.wait_for(self.run_instance(name), timeout=timeout)
            for name in self.instances.keys()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

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

        # Add metadata to results
        results["metadata"] = {
            "start_datetime": self.start_datetime.isoformat(),
            "agents": list(self.instances.keys()),
            "generated_filename": str(output_file)
        }

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to {output_file}")

def create_default_instances(output_format: str = "stream-json") -> List[InstanceConfig]:
    """Create default instance configurations"""
    return [
        InstanceConfig(
            name="/createtestsv2 goldenpath, unit",
            command="/createtestsv2 goldenpath, unit",
            description="createtestsv2",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            name="createtestsv2, goldenpath, integration",
            command="/createtestsv2 goldenpath, integration",
            description="createtestsv2",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            name="ssot",
            command="/ssotgardener",
            description="ssot",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            name="gitissueprogressorv2 goldenpath",
            command="/gitissueprogressorv2 goldenpath",
            description="ssot",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
        InstanceConfig(
            name="gitissueprogressorv2 tests",
            command="/gitissueprogressorv2 tests",
            description="ssot",
            permission_mode="acceptEdits",
            output_format=output_format
        ),
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
    parser.add_argument("--timeout", type=int, default=300,
                       help="Timeout in seconds for each instance (default: 300)")

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

    # Initialize orchestrator
    orchestrator = ClaudeInstanceOrchestrator(workspace)

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

    # Print summary
    summary = orchestrator.get_status_summary()
    logger.info(f"Orchestration completed in {total_duration:.2f}s")
    logger.info(f"Results: {summary['completed']} completed, {summary['failed']} failed")

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

        if status.output:
            print(f"  Output Preview: {status.output[:200]}...")

        if status.error:
            print(f"  Errors: {status.error[:200]}...")

    # Show the actual filename used (important when auto-generated)
    final_output_file = args.output or orchestrator.generate_output_filename()
    print(f"\nFull results saved to: {final_output_file}")

    # Exit with appropriate code
    sys.exit(0 if summary['failed'] == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())