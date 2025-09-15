#!/usr/bin/env python3
"""
Claude Terminal Launcher
A Python program that launches multiple Claude terminals with specific arguments.
"""

import subprocess
import sys
import time
import argparse
from typing import List, Dict, Optional
import json
import os
from pathlib import Path
import logging
import signal
import threading
from datetime import datetime


class ClaudeTerminalLauncher:
    """Launches multiple Claude terminals with specific configurations."""

    def __init__(self, config_file: Optional[str] = None, headless: bool = False):
        self.config_file = config_file
        self.headless = headless
        self.terminals = []
        self.log_dir = Path("claude_logs")
        self.log_dir.mkdir(exist_ok=True)
        self.setup_logging()
        self.default_config = {
            "terminals": [
                {
                    "name": "Main Development",
                    "args": ["--project", "netra-apex"],
                    "working_dir": None
                },
                {
                    "name": "Testing Terminal",
                    "args": ["--project", "netra-apex", "--context", "testing"],
                    "working_dir": None
                },
                {
                    "name": "Debugging Session",
                    "args": ["--project", "netra-apex", "--context", "debug"],
                    "working_dir": None
                }
            ],
            "terminal_type": "auto",  # auto, cmd, powershell, wt (Windows Terminal), headless
            "delay_between_launches": 1.0,
            "headless_options": {
                "log_output": True,
                "log_level": "INFO",
                "auto_restart": False,
                "restart_delay": 30,
                "max_restarts": 3
            }
        }

    def load_config(self) -> Dict:
        """Load configuration from file or use defaults."""
        if self.config_file and Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config file: {e}")
                print("Using default configuration...")

        return self.default_config

    def setup_logging(self):
        """Setup logging for the launcher."""
        log_file = self.log_dir / f"launcher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout) if not self.headless else logging.NullHandler()
            ]
        )

        self.logger = logging.getLogger('ClaudeLauncher')

    def save_default_config(self, filename: str = "claude_terminals_config.json"):
        """Save the default configuration to a file."""
        with open(filename, 'w') as f:
            json.dump(self.default_config, f, indent=2)
        print(f"Default configuration saved to {filename}")

    def detect_terminal_type(self) -> str:
        """Auto-detect the best terminal type for the current platform."""
        if self.headless:
            return "headless"

        if sys.platform == "win32":
            # Check if Windows Terminal is available
            try:
                subprocess.run(["wt", "--help"], capture_output=True, check=True)
                return "wt"
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

            # Check if PowerShell is available
            try:
                subprocess.run(["powershell", "-Command", "Get-Host"], capture_output=True, check=True)
                return "powershell"
            except (subprocess.CalledProcessError, FileNotFoundError):
                return "cmd"

        elif sys.platform == "darwin":
            return "terminal_mac"
        else:
            return "gnome-terminal"

    def build_command(self, terminal_type: str, claude_args: List[str], working_dir: Optional[str] = None) -> List[str]:
        """Build the command to launch Claude in the specified terminal."""
        claude_cmd = ["claude"] + claude_args

        if terminal_type == "wt":
            # Windows Terminal
            cmd = ["wt", "new-tab"]
            if working_dir:
                cmd.extend(["--startingDirectory", working_dir])
            cmd.extend(["--", "claude"] + claude_args)
            return cmd

        elif terminal_type == "powershell":
            # PowerShell
            claude_cmd_str = " ".join([f'"{arg}"' if " " in arg else arg for arg in claude_cmd])
            ps_cmd = f"Start-Process -FilePath claude -ArgumentList {claude_args} -NoNewWindow"
            if working_dir:
                ps_cmd = f"cd '{working_dir}'; {ps_cmd}"
            return ["powershell", "-Command", ps_cmd]

        elif terminal_type == "cmd":
            # Command Prompt
            cmd = ["cmd", "/c", "start", "cmd", "/k"]
            if working_dir:
                cmd.extend([f"cd /d {working_dir} &&"])
            cmd.extend(claude_cmd)
            return cmd

        elif terminal_type == "terminal_mac":
            # macOS Terminal
            script = f"tell application \"Terminal\" to do script \"cd {working_dir or os.getcwd()} && {' '.join(claude_cmd)}\""
            return ["osascript", "-e", script]

        elif terminal_type == "gnome-terminal":
            # Linux GNOME Terminal
            cmd = ["gnome-terminal", "--"]
            if working_dir:
                cmd.extend(["bash", "-c", f"cd '{working_dir}' && {' '.join(claude_cmd)}; exec bash"])
            else:
                cmd.extend(claude_cmd)
            return cmd

        elif terminal_type == "headless":
            # Headless mode - direct process execution
            return claude_cmd

        else:
            raise ValueError(f"Unsupported terminal type: {terminal_type}")

    def launch_terminal(self, name: str, args: List[str], working_dir: Optional[str] = None, terminal_type: str = "auto"):
        """Launch a single Claude terminal."""
        if terminal_type == "auto":
            terminal_type = self.detect_terminal_type()

        try:
            # Use current directory if working_dir is None
            work_dir = working_dir or os.getcwd()

            cmd = self.build_command(terminal_type, args, work_dir)

            if terminal_type == "headless":
                return self.launch_headless_session(name, cmd, work_dir, args)
            else:
                self.logger.info(f"Launching terminal '{name}' with command: {' '.join(cmd)}")
                process = subprocess.Popen(cmd, cwd=work_dir)

                self.terminals.append({
                    "name": name,
                    "process": process,
                    "args": args,
                    "working_dir": work_dir,
                    "type": "terminal",
                    "restart_count": 0
                })

            return True

        except Exception as e:
            self.logger.error(f"Failed to launch terminal '{name}': {e}")
            return False

    def launch_headless_session(self, name: str, cmd: List[str], work_dir: str, args: List[str]) -> bool:
        """Launch Claude in headless mode."""
        try:
            log_file = self.log_dir / f"{name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

            self.logger.info(f"Launching headless session '{name}' with command: {' '.join(cmd)}")

            with open(log_file, 'w') as log_handle:
                process = subprocess.Popen(
                    cmd,
                    cwd=work_dir,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                )

            terminal_info = {
                "name": name,
                "process": process,
                "args": args,
                "working_dir": work_dir,
                "type": "headless",
                "log_file": str(log_file),
                "restart_count": 0,
                "start_time": datetime.now()
            }

            self.terminals.append(terminal_info)

            # Start monitoring thread for this process
            monitor_thread = threading.Thread(
                target=self.monitor_headless_process,
                args=(terminal_info,),
                daemon=True
            )
            monitor_thread.start()

            self.logger.info(f"Headless session '{name}' started with PID {process.pid}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to launch headless session '{name}': {e}")
            return False

    def monitor_headless_process(self, terminal_info: Dict):
        """Monitor a headless process and handle restarts if configured."""
        config = self.load_config()
        headless_opts = config.get("headless_options", {})
        auto_restart = headless_opts.get("auto_restart", False)
        max_restarts = headless_opts.get("max_restarts", 3)
        restart_delay = headless_opts.get("restart_delay", 30)

        while True:
            try:
                # Wait for process to complete
                exit_code = terminal_info["process"].wait()

                self.logger.info(f"Process '{terminal_info['name']}' exited with code {exit_code}")

                if auto_restart and terminal_info["restart_count"] < max_restarts:
                    self.logger.info(f"Restarting '{terminal_info['name']}' in {restart_delay} seconds...")
                    time.sleep(restart_delay)

                    # Restart the process
                    cmd = self.build_command("headless", terminal_info["args"], terminal_info["working_dir"])
                    log_file = self.log_dir / f"{terminal_info['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_restart{terminal_info['restart_count'] + 1}.log"

                    with open(log_file, 'w') as log_handle:
                        new_process = subprocess.Popen(
                            cmd,
                            cwd=terminal_info["working_dir"],
                            stdout=log_handle,
                            stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                        )

                    terminal_info["process"] = new_process
                    terminal_info["log_file"] = str(log_file)
                    terminal_info["restart_count"] += 1
                    terminal_info["start_time"] = datetime.now()

                    self.logger.info(f"Restarted '{terminal_info['name']}' with new PID {new_process.pid}")
                else:
                    break

            except Exception as e:
                self.logger.error(f"Error monitoring process '{terminal_info['name']}': {e}")
                break

    def launch_all(self):
        """Launch all configured terminals."""
        config = self.load_config()
        terminal_type = config.get("terminal_type", "auto")
        delay = config.get("delay_between_launches", 1.0)

        print(f"Launching {len(config['terminals'])} Claude terminals...")

        for i, terminal_config in enumerate(config["terminals"]):
            name = terminal_config.get("name", f"Terminal {i+1}")
            args = terminal_config.get("args", [])
            working_dir = terminal_config.get("working_dir")

            success = self.launch_terminal(name, args, working_dir, terminal_type)

            if success:
                print(f"✓ Launched: {name}")
            else:
                print(f"✗ Failed: {name}")

            # Add delay between launches to prevent overwhelming the system
            if i < len(config["terminals"]) - 1:
                time.sleep(delay)

        self.logger.info(f"Launched {len([t for t in self.terminals if t['process']])} terminals successfully.")

    def list_terminals(self):
        """List all launched terminals and their status."""
        if not self.terminals:
            msg = "No terminals have been launched yet."
            if self.headless:
                self.logger.info(msg)
            else:
                print(msg)
            return

        output_lines = ["\nActive terminals:"]
        for i, terminal in enumerate(self.terminals):
            status = "Running" if terminal["process"].poll() is None else "Terminated"
            term_type = terminal.get("type", "terminal")

            output_lines.append(f"{i+1}. {terminal['name']}: {status} ({term_type})")
            output_lines.append(f"   Args: {' '.join(terminal['args'])}")
            output_lines.append(f"   Working Dir: {terminal['working_dir']}")

            if term_type == "headless":
                output_lines.append(f"   Log File: {terminal.get('log_file', 'N/A')}")
                output_lines.append(f"   PID: {terminal['process'].pid}")
                output_lines.append(f"   Restarts: {terminal.get('restart_count', 0)}")
                if 'start_time' in terminal:
                    runtime = datetime.now() - terminal['start_time']
                    output_lines.append(f"   Runtime: {str(runtime).split('.')[0]}")

        output = "\n".join(output_lines)
        if self.headless:
            self.logger.info(output)
        else:
            print(output)

    def cleanup(self):
        """Clean up any remaining processes."""
        for terminal in self.terminals:
            if terminal["process"].poll() is None:
                try:
                    terminal["process"].terminate()
                except:
                    pass


def main():
    parser = argparse.ArgumentParser(description="Launch multiple Claude terminals with specific arguments")
    parser.add_argument("--config", "-c", help="Configuration file path")
    parser.add_argument("--generate-config", "-g", action="store_true",
                       help="Generate a default configuration file")
    parser.add_argument("--list", "-l", action="store_true",
                       help="List active terminals")
    parser.add_argument("--terminal-type", "-t",
                       choices=["auto", "wt", "powershell", "cmd", "terminal_mac", "gnome-terminal", "headless"],
                       help="Force specific terminal type")
    parser.add_argument("--headless", "-H", action="store_true",
                       help="Run in headless mode (no GUI terminals)")
    parser.add_argument("--daemon", "-d", action="store_true",
                       help="Run as daemon in background")

    args = parser.parse_args()

    # Determine headless mode
    headless_mode = args.headless or args.terminal_type == "headless" or args.daemon

    launcher = ClaudeTerminalLauncher(args.config, headless=headless_mode)

    try:
        if args.generate_config:
            launcher.save_default_config()
            return

        if args.list:
            launcher.list_terminals()
            return

        # Override terminal type if specified
        if args.terminal_type:
            config = launcher.load_config()
            config["terminal_type"] = args.terminal_type
            launcher.default_config = config

        launcher.launch_all()

        # Handle daemon mode
        if args.daemon:
            launcher.logger.info("Running in daemon mode. Check logs for status.")
            # Create a PID file for daemon management
            pid_file = Path("claude_launcher.pid")
            with open(pid_file, 'w') as f:
                f.write(str(os.getpid()))

            # Setup signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                launcher.logger.info(f"Received signal {signum}, shutting down...")
                launcher.cleanup()
                if pid_file.exists():
                    pid_file.unlink()
                sys.exit(0)

            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)

            try:
                while True:
                    time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                signal_handler(signal.SIGINT, None)

        elif headless_mode:
            launcher.logger.info("Running in headless mode. Press Ctrl+C to exit and cleanup...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                launcher.logger.info("Cleaning up...")
                launcher.cleanup()
        else:
            # Keep the script running to monitor terminals
            print("\nPress Ctrl+C to exit and cleanup...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nCleaning up...")
                launcher.cleanup()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()