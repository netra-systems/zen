#!/usr/bin/env python3
"""
Demonstration of log collection from .claude/Projects

This script shows how the zen --apex --send-logs functionality works
"""
import sys
from pathlib import Path
import json

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.agent_logs import collect_recent_logs


def demo_log_collection():
    """Demonstrate log collection with various scenarios"""

    print("=" * 60)
    print("Zen Apex Log Collection Demo")
    print("=" * 60)
    print()

    # Check if .claude/Projects exists
    claude_path = Path.home() / ".claude" / "Projects"

    if not claude_path.exists():
        print("❌ .claude/Projects does not exist")
        print(f"   Expected location: {claude_path}")
        print()
        print("Creating test directory...")
        claude_path.mkdir(parents=True, exist_ok=True)
        test_project = claude_path / "demo-project"
        test_project.mkdir(exist_ok=True)

        # Create sample log
        sample_log = {
            "type": "demo_event",
            "timestamp": "2025-01-08T12:00:00",
            "message": "This is a demo log entry",
            "data": {"key": "value"}
        }
        (test_project / "demo-session.jsonl").write_text(json.dumps(sample_log) + "\n")
        print(f"✅ Created demo project at {test_project}")
        print()

    # Scenario 1: Collect with defaults
    print("Scenario 1: Collect logs with defaults (limit=1, auto-detect project)")
    print("-" * 60)
    logs = collect_recent_logs(limit=1)

    if logs:
        print(f"✅ Collected {len(logs)} log entries")
        print(f"   Total entries: {len(logs)}")
        print()
        print("   Sample entry (first):")
        print(f"   {json.dumps(logs[0], indent=4)}")
    else:
        print("⚠️  No logs found")
        print("   Tip: Run Claude Code with some commands to generate logs")
    print()

    # Scenario 2: List available projects
    print("Scenario 2: List available projects")
    print("-" * 60)
    if claude_path.exists():
        projects = [p for p in claude_path.iterdir() if p.is_dir()]
        if projects:
            print(f"Found {len(projects)} project(s):")
            for proj in sorted(projects, key=lambda p: p.stat().st_mtime, reverse=True):
                jsonl_count = len(list(proj.glob("*.jsonl")))
                mtime = proj.stat().st_mtime
                from datetime import datetime
                mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                marker = "  ← most recent" if proj == projects[0] else ""
                print(f"  • {proj.name}: {jsonl_count} .jsonl files (modified: {mtime_str}){marker}")
        else:
            print("  No projects found")
    print()

    # Scenario 3: Collect from specific project
    if claude_path.exists():
        projects = [p for p in claude_path.iterdir() if p.is_dir()]
        if projects:
            specific_project = projects[0].name
            print(f"Scenario 3: Collect from specific project '{specific_project}'")
            print("-" * 60)
            logs = collect_recent_logs(limit=3, project_name=specific_project)
            if logs:
                print(f"✅ Collected {len(logs)} entries from '{specific_project}'")
                print(f"   Entry types: {[log.get('type', 'unknown') for log in logs[:3]]}")
            else:
                print(f"⚠️  No logs in '{specific_project}'")
            print()

    # Scenario 4: Show what would be sent with --send-logs
    print("Scenario 4: What gets sent with 'zen --apex --send-logs --message \"..\"'")
    print("-" * 60)
    logs = collect_recent_logs(limit=1)
    if logs:
        payload_preview = {
            "type": "user_message",
            "payload": {
                "content": "your message here",
                "run_id": "cli_20250108_120000_12345",
                "thread_id": "cli_thread_abc123def456",
                "timestamp": "2025-01-08T12:00:00",
                "jsonl_logs": logs  # This is what gets attached
            }
        }
        print("Payload structure:")
        print(json.dumps(payload_preview, indent=2)[:500] + "...")
        print()
        print(f"✅ {len(logs)} log entries would be attached to the message")
    else:
        print("⚠️  No logs would be attached (none found)")
    print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()
    print("To use log forwarding with zen --apex:")
    print()
    print("  # Basic usage (default: 1 log file for best results)")
    print("  zen --apex --send-logs --message \"analyze these sessions\"")
    print()
    print("  # Custom number of logs (default: 1 for best results)")
    print("  zen --apex --send-logs --message \"review recent log\" (analyzes 1 file)")
    print("  # Multiple files (use with caution - keep payload under 1MB)")
    print("  zen --apex --send-logs --logs-count 2 --message \"review last 2\"")
    print()
    print("  # Specific project")
    if claude_path.exists() and list(claude_path.iterdir()):
        first_project = list(p for p in claude_path.iterdir() if p.is_dir())[0].name
        print(f"  zen --apex --send-logs --logs-project {first_project} --message \"...\"")
    else:
        print("  zen --apex --send-logs --logs-project PROJECT_NAME --message \"...\"")
    print()
    print("=" * 60)


if __name__ == "__main__":
    demo_log_collection()
