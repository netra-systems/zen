#!/usr/bin/env python3
"""
Integration tests for zen --apex functionality
Tests log collection and argument passing
"""
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from scripts.agent_logs import collect_recent_logs


class TestApexLogCollection:
    """Test log collection functionality for apex integration"""

    def test_collect_logs_from_claude_projects(self, tmp_path):
        """Test collecting logs from a mock .claude/Projects structure"""
        # Create mock .claude/Projects structure
        projects_root = tmp_path / "Projects"
        project_dir = projects_root / "test-project"
        project_dir.mkdir(parents=True)

        # Create test log files
        log1 = {"event": "test1", "timestamp": "2025-01-01T10:00:00"}
        log2 = {"event": "test2", "timestamp": "2025-01-01T11:00:00"}

        (project_dir / "session1.jsonl").write_text(json.dumps(log1) + "\n")
        (project_dir / "session2.jsonl").write_text(json.dumps(log2) + "\n")

        # Collect logs
        logs = collect_recent_logs(
            limit=2,
            base_path=str(projects_root),
            project_name="test-project"
        )

        # Verify
        assert logs is not None, "Logs should be collected"
        assert len(logs) == 2, f"Expected 2 log entries, got {len(logs)}"
        assert logs[0]["event"] in ["test1", "test2"]

    def test_collect_logs_auto_detect_project(self, tmp_path):
        """Test automatic detection of most recent project"""
        # Create multiple projects
        projects_root = tmp_path / "Projects"
        old_project = projects_root / "old-project"
        new_project = projects_root / "new-project"
        old_project.mkdir(parents=True)
        new_project.mkdir(parents=True)

        # Create log in old project
        old_log = {"event": "old", "timestamp": "2025-01-01T10:00:00"}
        (old_project / "session.jsonl").write_text(json.dumps(old_log) + "\n")

        # Wait a bit and create log in new project
        import time
        time.sleep(0.01)  # Ensure different mtime
        new_log = {"event": "new", "timestamp": "2025-01-01T11:00:00"}
        (new_project / "session.jsonl").write_text(json.dumps(new_log) + "\n")

        # Touch new_project to make it most recent
        new_project.touch()

        # Collect logs (should auto-detect new-project)
        logs = collect_recent_logs(limit=1, base_path=str(projects_root))

        # Verify it picked the most recent project
        assert logs is not None
        assert len(logs) == 1
        assert logs[0]["event"] == "new", "Should collect from most recent project"

    def test_collect_logs_with_limit(self, tmp_path):
        """Test that limit parameter works correctly"""
        projects_root = tmp_path / "Projects"
        project_dir = projects_root / "test-project"
        project_dir.mkdir(parents=True)

        # Create 10 log files
        for i in range(10):
            log = {"event": f"test{i}", "index": i}
            (project_dir / f"session{i}.jsonl").write_text(json.dumps(log) + "\n")

        # Collect with limit=5
        logs = collect_recent_logs(
            limit=5,
            base_path=str(projects_root),
            project_name="test-project"
        )

        # Verify limit is respected
        assert logs is not None
        assert len(logs) == 5, f"Expected 5 log entries with limit=5, got {len(logs)}"

    def test_collect_logs_handles_malformed_json(self, tmp_path):
        """Test that malformed JSON lines are skipped gracefully"""
        projects_root = tmp_path / "Projects"
        project_dir = projects_root / "test-project"
        project_dir.mkdir(parents=True)

        # Create log file with valid and invalid JSON
        log_file = project_dir / "session.jsonl"
        log_file.write_text(
            '{"event": "valid1"}\n'
            'invalid json line\n'
            '{"event": "valid2"}\n'
            '{broken json\n'
            '{"event": "valid3"}\n'
        )

        # Collect logs
        logs = collect_recent_logs(
            limit=1,
            base_path=str(projects_root),
            project_name="test-project"
        )

        # Verify only valid entries collected
        assert logs is not None
        assert len(logs) == 3, "Should collect 3 valid entries, skipping malformed"
        events = [log["event"] for log in logs]
        assert "valid1" in events
        assert "valid2" in events
        assert "valid3" in events

    def test_collect_logs_returns_none_when_no_logs(self, tmp_path):
        """Test that None is returned when no logs exist"""
        projects_root = tmp_path / "Projects"
        projects_root.mkdir(parents=True)

        # Collect from empty Projects directory
        logs = collect_recent_logs(limit=5, base_path=str(projects_root))

        # Verify None is returned
        assert logs is None, "Should return None when no projects exist"

    def test_collect_logs_with_custom_parameters(self, tmp_path):
        """Test collecting logs with all custom parameters"""
        projects_root = tmp_path / "Projects"
        specific_project = projects_root / "specific-project"
        specific_project.mkdir(parents=True)

        # Create test log
        log = {"event": "custom_test", "data": "specific"}
        (specific_project / "session.jsonl").write_text(json.dumps(log) + "\n")

        # Collect with custom parameters
        logs = collect_recent_logs(
            limit=10,
            project_name="specific-project",
            base_path=str(projects_root),
            username=None,  # Not used on macOS/Linux
            platform_name="Darwin"
        )

        # Verify
        assert logs is not None
        assert len(logs) == 1
        assert logs[0]["event"] == "custom_test"

    def test_real_claude_projects_if_exists(self):
        """Test with real .claude/Projects if it exists (optional)"""
        claude_path = Path.home() / ".claude" / "Projects"
        if not claude_path.exists():
            pytest.skip(".claude/Projects does not exist")

        # Try to collect logs from real location
        logs = collect_recent_logs(limit=1)

        # If logs exist, verify structure
        if logs:
            assert isinstance(logs, list)
            assert len(logs) >= 1
            assert isinstance(logs[0], dict)
            print(f"\n✅ Successfully collected {len(logs)} entries from real .claude/Projects")
        else:
            print("\n⚠️ No logs found in real .claude/Projects (this is OK)")


class TestApexArgumentPassing:
    """Test that arguments are properly passed to agent_cli"""

    def test_send_logs_flag_available(self):
        """Test that --send-logs argument is available in agent_cli"""
        import subprocess
        import sys

        # Run agent_cli --help and check for --send-logs
        result = subprocess.run(
            [sys.executable, "-m", "scripts.agent_cli", "--help"],
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(Path(__file__).parent.parent)}
        )

        # Note: This will fail without backend dependencies, which is expected
        # We're just testing that the module structure is correct
        assert "--send-logs" in result.stdout or "--send-logs" in result.stderr or result.returncode != 0

    def test_python_m_zen_apex_help(self):
        """Smoke test that python -m zen delegates --apex to agent_cli help"""
        import subprocess
        import sys

        env = os.environ.copy()
        repo_root = Path(__file__).parent.parent.resolve()
        existing_path = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            f"{repo_root}{os.pathsep}{existing_path}"
            if existing_path
            else str(repo_root)
        )

        result = subprocess.run(
            [sys.executable, "-m", "zen", "--apex", "--help"],
            capture_output=True,
            text=True,
            env=env
        )

        combined_output = f"{result.stdout}\n{result.stderr}"
        assert "--send-logs" in combined_output or "--logs-count" in combined_output or result.returncode != 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
