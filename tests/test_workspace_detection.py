#!/usr/bin/env python3
"""
Test script to verify zen workspace auto-detection logic
"""
import sys
from pathlib import Path

# Test the auto-detection logic from zen_orchestrator.py
zen_script_path = Path(__file__).resolve()
zen_dir = zen_script_path.parent

print(f"Zen script path: {zen_script_path}")
print(f"Zen directory: {zen_dir}")

# Check if zen is in a subdirectory of a larger project
potential_root = zen_dir.parent
print(f"Potential root: {potential_root}")

# Look for common project indicators in parent directory
project_indicators = ['.git', '.claude', 'package.json', 'setup.py', 'pyproject.toml', 'Cargo.toml']

found_indicators = []
for indicator in project_indicators:
    if (potential_root / indicator).exists():
        found_indicators.append(indicator)

print(f"Found project indicators: {found_indicators}")

if found_indicators:
    workspace = potential_root
    print(f"Auto-detected project root as workspace: {workspace}")
else:
    workspace = Path.cwd().resolve()
    print(f"Using current working directory as workspace: {workspace}")

# If workspace is still the zen directory itself, use parent or current directory
if workspace == zen_dir:
    workspace = zen_dir.parent if zen_dir.parent != zen_dir else Path.cwd().resolve()
    print(f"Adjusted workspace to: {workspace}")

# Check for .claude/commands directory
claude_commands_dir = workspace / ".claude" / "commands"
print(f"Looking for commands in: {claude_commands_dir}")
print(f"Commands directory exists: {claude_commands_dir.exists()}")

if claude_commands_dir.exists():
    commands = []
    for cmd_file in claude_commands_dir.glob("*.md"):
        cmd_name = f"/{cmd_file.stem}"
        commands.append(cmd_name)

    print(f"Found {len(commands)} commands:")
    for cmd in sorted(commands)[:10]:  # Show first 10
        print(f"  {cmd}")
    if len(commands) > 10:
        print(f"  ... and {len(commands) - 10} more")