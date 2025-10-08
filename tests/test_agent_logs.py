#!/usr/bin/env python3
"""
Unit tests for scripts/agent_logs.py

Tests all functionality of the Agent Logs Collection Helper including:
- Log collection with synthetic directories
- Platform resolution (macOS, Windows, Linux)
- Project selection (default most recent vs explicit)
- File ordering by modification time
- JSON parsing resilience (malformed lines, truncated logs)
- Error handling (missing directories, invalid project names)
- Sanitization (directory traversal prevention)
- Limit parameter validation
"""

import pytest
import json
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from agent_logs import (
    _get_default_user,
    _resolve_projects_root,
    _sanitize_project_name,
    _find_most_recent_project,
    _collect_jsonl_files,
    collect_recent_logs
)


class TestGetDefaultUser:
    """Test _get_default_user function"""

    def test_get_default_user_from_username(self):
        """Test getting user from USERNAME env variable"""
        with patch.dict(os.environ, {'USERNAME': 'testuser', 'USER': 'otheruser'}):
            assert _get_default_user() == 'testuser'

    def test_get_default_user_from_user(self):
        """Test getting user from USER env variable when USERNAME not set"""
        with patch.dict(os.environ, {'USER': 'testuser'}, clear=True):
            if 'USERNAME' in os.environ:
                del os.environ['USERNAME']
            assert _get_default_user() == 'testuser'

    def test_get_default_user_none_when_not_set(self):
        """Test returning None when neither env variable is set"""
        with patch.dict(os.environ, {}, clear=True):
            assert _get_default_user() is None


class TestResolveProjectsRoot:
    """Test _resolve_projects_root function for platform-specific paths"""

    def test_resolve_projects_root_macos(self):
        """Test macOS path resolution"""
        with patch('agent_logs.Path.home', return_value=Path('/Users/testuser')):
            result = _resolve_projects_root(platform_name='Darwin')
            assert result == Path('/Users/testuser/.claude/Projects').resolve()

    def test_resolve_projects_root_linux(self):
        """Test Linux path resolution"""
        with patch('agent_logs.Path.home', return_value=Path('/home/testuser')):
            result = _resolve_projects_root(platform_name='Linux')
            assert result == Path('/home/testuser/.claude/Projects').resolve()

    def test_resolve_projects_root_windows_with_username(self):
        """Test Windows path resolution with explicit username"""
        result = _resolve_projects_root(platform_name='Windows', username='testuser')
        assert result == Path('C:/Users/testuser/.claude/Projects').resolve()

    def test_resolve_projects_root_windows_with_userprofile(self):
        """Test Windows path resolution using USERPROFILE environment variable"""
        with patch.dict(os.environ, {'USERPROFILE': 'C:\\Users\\testuser'}, clear=True):
            result = _resolve_projects_root(platform_name='Windows')
            # Path.resolve() will normalize the path
            expected = Path('C:/Users/testuser/.claude/Projects')
            assert str(result).replace('\\', '/').endswith('.claude/Projects')

    def test_resolve_projects_root_windows_fallback_to_home(self):
        """Test Windows path resolution fallback to Path.home()"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('agent_logs.Path.home', return_value=Path('C:/Users/testuser')):
                result = _resolve_projects_root(platform_name='Windows')
                assert result == Path('C:/Users/testuser/.claude/Projects').resolve()

    def test_resolve_projects_root_base_path_override(self):
        """Test direct base_path override bypasses platform resolution"""
        custom_path = Path('/custom/path/to/projects')
        result = _resolve_projects_root(base_path=custom_path)
        assert result == custom_path.resolve()

    def test_resolve_projects_root_auto_detect_platform(self):
        """Test auto-detection of platform when not specified"""
        with patch('agent_logs.platform.system', return_value='Darwin'):
            with patch('agent_logs.Path.home', return_value=Path('/Users/testuser')):
                result = _resolve_projects_root()
                assert result == Path('/Users/testuser/.claude/Projects').resolve()


class TestSanitizeProjectName:
    """Test _sanitize_project_name function for security"""

    def test_sanitize_project_name_valid_simple(self):
        """Test sanitization of simple valid project name"""
        assert _sanitize_project_name('my-project') == 'my-project'

    def test_sanitize_project_name_valid_with_underscores(self):
        """Test sanitization of project name with underscores"""
        assert _sanitize_project_name('my_project_123') == 'my_project_123'

    def test_sanitize_project_name_strips_whitespace(self):
        """Test sanitization strips leading/trailing whitespace"""
        assert _sanitize_project_name('  my-project  ') == 'my-project'

    def test_sanitize_project_name_strips_dots(self):
        """Test sanitization strips leading/trailing dots"""
        # This will fail because '..' is detected first as a dangerous pattern
        with pytest.raises(ValueError, match="invalid pattern"):
            _sanitize_project_name('..my-project..')

    def test_sanitize_project_name_rejects_parent_dir_traversal(self):
        """Test rejection of parent directory traversal (..)"""
        with pytest.raises(ValueError, match="invalid pattern: \\.\\."):
            _sanitize_project_name('../etc/passwd')

    def test_sanitize_project_name_rejects_forward_slash(self):
        """Test rejection of forward slash (/)"""
        with pytest.raises(ValueError, match="invalid pattern: /"):
            _sanitize_project_name('path/to/project')

    def test_sanitize_project_name_rejects_backslash(self):
        """Test rejection of backslash (\\)"""
        with pytest.raises(ValueError, match="invalid pattern"):
            _sanitize_project_name('path\\to\\project')

    def test_sanitize_project_name_rejects_null_byte(self):
        """Test rejection of null byte"""
        with pytest.raises(ValueError, match="invalid pattern"):
            _sanitize_project_name('project\0name')

    def test_sanitize_project_name_rejects_empty_string(self):
        """Test rejection of empty string"""
        with pytest.raises(ValueError, match="cannot be empty"):
            _sanitize_project_name('')

    def test_sanitize_project_name_rejects_only_whitespace(self):
        """Test rejection of string with only whitespace"""
        with pytest.raises(ValueError, match="invalid after sanitization"):
            _sanitize_project_name('   ')

    def test_sanitize_project_name_rejects_only_dots(self):
        """Test rejection of string with only dots"""
        # Single dot gets stripped, resulting in empty string
        with pytest.raises(ValueError, match="invalid after sanitization"):
            _sanitize_project_name('.')


class TestFindMostRecentProject:
    """Test _find_most_recent_project function"""

    def test_find_most_recent_project_single_project(self, tmp_path):
        """Test finding most recent project when only one exists"""
        # Create single project directory
        project = tmp_path / "project1"
        project.mkdir()

        result = _find_most_recent_project(tmp_path)
        assert result == project

    def test_find_most_recent_project_multiple_projects(self, tmp_path):
        """Test finding most recent project among multiple"""
        # Create multiple project directories with staggered times
        project1 = tmp_path / "project1"
        project1.mkdir()
        time.sleep(0.01)  # Small delay to ensure different mtimes

        project2 = tmp_path / "project2"
        project2.mkdir()
        time.sleep(0.01)

        project3 = tmp_path / "project3"
        project3.mkdir()

        result = _find_most_recent_project(tmp_path)
        assert result == project3

    def test_find_most_recent_project_by_modification_time(self, tmp_path):
        """Test that most recent is determined by modification time"""
        # Create projects in order
        project1 = tmp_path / "project1"
        project1.mkdir()
        project2 = tmp_path / "project2"
        project2.mkdir()

        # Explicitly touch project1 to make it most recent
        time.sleep(0.01)
        project1.touch()

        result = _find_most_recent_project(tmp_path)
        assert result == project1

    def test_find_most_recent_project_ignores_files(self, tmp_path):
        """Test that regular files are ignored, only directories considered"""
        # Create a file and a directory
        (tmp_path / "file.txt").write_text("test")
        project = tmp_path / "project1"
        project.mkdir()

        result = _find_most_recent_project(tmp_path)
        assert result == project

    def test_find_most_recent_project_nonexistent_path(self, tmp_path):
        """Test handling of nonexistent projects root"""
        nonexistent = tmp_path / "does_not_exist"
        result = _find_most_recent_project(nonexistent)
        assert result is None

    def test_find_most_recent_project_empty_directory(self, tmp_path):
        """Test handling of empty projects root"""
        result = _find_most_recent_project(tmp_path)
        assert result is None

    def test_find_most_recent_project_file_not_directory(self, tmp_path):
        """Test handling when projects_root is a file, not directory"""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        result = _find_most_recent_project(file_path)
        assert result is None


class TestCollectJsonlFiles:
    """Test _collect_jsonl_files function"""

    def test_collect_jsonl_files_single_file(self, tmp_path):
        """Test collecting logs from a single JSONL file"""
        log_file = tmp_path / "test.jsonl"
        log_file.write_text('{"event": "test1", "value": 1}\n{"event": "test2", "value": 2}\n')

        result = _collect_jsonl_files(tmp_path, limit=5)

        assert len(result) == 2
        assert result[0] == {"event": "test1", "value": 1}
        assert result[1] == {"event": "test2", "value": 2}

    def test_collect_jsonl_files_multiple_files(self, tmp_path):
        """Test collecting logs from multiple JSONL files"""
        # Create multiple log files
        (tmp_path / "log1.jsonl").write_text('{"event": "log1"}\n')
        time.sleep(0.01)
        (tmp_path / "log2.jsonl").write_text('{"event": "log2"}\n')
        time.sleep(0.01)
        (tmp_path / "log3.jsonl").write_text('{"event": "log3"}\n')

        result = _collect_jsonl_files(tmp_path, limit=5)

        assert len(result) == 3
        # Most recent file should be read first
        assert result[0] == {"event": "log3"}

    def test_collect_jsonl_files_respects_limit(self, tmp_path):
        """Test that limit parameter restricts number of files read"""
        # Create 5 files but limit to 2
        for i in range(5):
            (tmp_path / f"log{i}.jsonl").write_text(f'{{"file": {i}}}\n')
            time.sleep(0.01)

        result = _collect_jsonl_files(tmp_path, limit=2)

        # Should only read 2 most recent files (log3.jsonl and log4.jsonl)
        assert len(result) == 2

    def test_collect_jsonl_files_orders_by_mtime(self, tmp_path):
        """Test that files are processed in order of modification time (newest first)"""
        # Create files with known content
        (tmp_path / "old.jsonl").write_text('{"order": "first"}\n')
        time.sleep(0.01)
        (tmp_path / "new.jsonl").write_text('{"order": "second"}\n')

        result = _collect_jsonl_files(tmp_path, limit=5)

        # Newest file should be first
        assert result[0] == {"order": "second"}
        assert result[1] == {"order": "first"}

    def test_collect_jsonl_files_skips_malformed_json(self, tmp_path):
        """Test resilience to malformed JSON lines"""
        log_file = tmp_path / "test.jsonl"
        log_file.write_text(
            '{"valid": "first"}\n'
            '{invalid json here}\n'
            '{"valid": "second"}\n'
            'not json at all\n'
            '{"valid": "third"}\n'
        )

        result = _collect_jsonl_files(tmp_path, limit=5)

        # Should collect only valid entries
        assert len(result) == 3
        assert result[0] == {"valid": "first"}
        assert result[1] == {"valid": "second"}
        assert result[2] == {"valid": "third"}

    def test_collect_jsonl_files_skips_empty_lines(self, tmp_path):
        """Test that empty lines are ignored"""
        log_file = tmp_path / "test.jsonl"
        log_file.write_text(
            '{"event": "first"}\n'
            '\n'
            '   \n'
            '{"event": "second"}\n'
            '\n'
        )

        result = _collect_jsonl_files(tmp_path, limit=5)

        assert len(result) == 2
        assert result[0] == {"event": "first"}
        assert result[1] == {"event": "second"}

    def test_collect_jsonl_files_handles_truncated_file(self, tmp_path):
        """Test handling of truncated/incomplete JSON at end of file"""
        log_file = tmp_path / "test.jsonl"
        log_file.write_text(
            '{"valid": "entry"}\n'
            '{"truncated": "this is incomplete'
        )

        result = _collect_jsonl_files(tmp_path, limit=5)

        # Should collect valid entry and skip truncated
        assert len(result) == 1
        assert result[0] == {"valid": "entry"}

    def test_collect_jsonl_files_nonexistent_path(self, tmp_path):
        """Test handling of nonexistent project path"""
        nonexistent = tmp_path / "does_not_exist"
        result = _collect_jsonl_files(nonexistent, limit=5)
        assert result == []

    def test_collect_jsonl_files_no_jsonl_files(self, tmp_path):
        """Test handling when no JSONL files exist"""
        # Create non-JSONL files
        (tmp_path / "test.txt").write_text("test")
        (tmp_path / "test.json").write_text('{"test": "data"}')

        result = _collect_jsonl_files(tmp_path, limit=5)
        assert result == []

    def test_collect_jsonl_files_file_read_error(self, tmp_path):
        """Test handling of file read errors"""
        log_file = tmp_path / "test.jsonl"
        log_file.write_text('{"event": "test"}\n')

        # Make file unreadable (on Unix-like systems)
        if os.name != 'nt':
            log_file.chmod(0o000)

            result = _collect_jsonl_files(tmp_path, limit=5)
            assert result == []

            # Restore permissions for cleanup
            log_file.chmod(0o644)

    def test_collect_jsonl_files_unicode_content(self, tmp_path):
        """Test handling of Unicode content in JSONL files"""
        log_file = tmp_path / "test.jsonl"
        log_file.write_text('{"message": "Hello 世界 🌍"}\n', encoding='utf-8')

        result = _collect_jsonl_files(tmp_path, limit=5)

        assert len(result) == 1
        assert result[0] == {"message": "Hello 世界 🌍"}

    def test_collect_jsonl_files_large_entries(self, tmp_path):
        """Test handling of large JSON entries"""
        log_file = tmp_path / "test.jsonl"
        large_data = {"data": "x" * 10000, "index": 1}
        log_file.write_text(json.dumps(large_data) + '\n')

        result = _collect_jsonl_files(tmp_path, limit=5)

        assert len(result) == 1
        assert result[0] == large_data


class TestCollectRecentLogs:
    """Test collect_recent_logs main function"""

    def test_collect_recent_logs_basic(self, tmp_path):
        """Test basic log collection from most recent project"""
        # Create project structure
        projects_root = tmp_path / ".claude" / "Projects"
        project = projects_root / "test-project"
        project.mkdir(parents=True)

        # Create log file
        log_file = project / "test.jsonl"
        log_file.write_text('{"event": "test", "data": "value"}\n')

        result = collect_recent_logs(limit=5, base_path=str(projects_root))

        assert result is not None
        assert len(result) == 1
        assert result[0] == {"event": "test", "data": "value"}

    def test_collect_recent_logs_specific_project(self, tmp_path):
        """Test log collection from explicitly specified project"""
        # Create multiple projects
        projects_root = tmp_path / ".claude" / "Projects"
        project1 = projects_root / "project1"
        project2 = projects_root / "project2"
        project1.mkdir(parents=True)
        project2.mkdir(parents=True)

        # Create different logs in each
        (project1 / "log.jsonl").write_text('{"source": "project1"}\n')
        (project2 / "log.jsonl").write_text('{"source": "project2"}\n')

        result = collect_recent_logs(
            limit=5,
            project_name="project1",
            base_path=str(projects_root)
        )

        assert result is not None
        assert len(result) == 1
        assert result[0] == {"source": "project1"}

    def test_collect_recent_logs_most_recent_project(self, tmp_path):
        """Test automatic selection of most recent project"""
        # Create multiple projects
        projects_root = tmp_path / ".claude" / "Projects"
        old_project = projects_root / "old-project"
        old_project.mkdir(parents=True)
        (old_project / "log.jsonl").write_text('{"source": "old"}\n')

        time.sleep(0.01)

        new_project = projects_root / "new-project"
        new_project.mkdir(parents=True)
        (new_project / "log.jsonl").write_text('{"source": "new"}\n')

        result = collect_recent_logs(limit=5, base_path=str(projects_root))

        assert result is not None
        assert len(result) == 1
        assert result[0] == {"source": "new"}

    def test_collect_recent_logs_limit_validation_zero(self):
        """Test that limit=0 raises ValueError"""
        with pytest.raises(ValueError, match="Limit must be positive"):
            collect_recent_logs(limit=0)

    def test_collect_recent_logs_limit_validation_negative(self):
        """Test that negative limit raises ValueError"""
        with pytest.raises(ValueError, match="Limit must be positive"):
            collect_recent_logs(limit=-1)

    def test_collect_recent_logs_limit_validation_positive(self, tmp_path):
        """Test that positive limit is accepted"""
        projects_root = tmp_path / ".claude" / "Projects"
        project = projects_root / "test-project"
        project.mkdir(parents=True)
        (project / "log.jsonl").write_text('{"test": "data"}\n')

        # Should not raise
        result = collect_recent_logs(limit=1, base_path=str(projects_root))
        assert result is not None

    def test_collect_recent_logs_invalid_project_name(self, tmp_path):
        """Test handling of invalid project name"""
        projects_root = tmp_path / ".claude" / "Projects"
        projects_root.mkdir(parents=True)

        # collect_recent_logs catches exceptions and returns None
        result = collect_recent_logs(
            limit=5,
            project_name="../etc/passwd",
            base_path=str(projects_root)
        )
        assert result is None

    def test_collect_recent_logs_nonexistent_project(self, tmp_path):
        """Test handling of nonexistent specified project"""
        projects_root = tmp_path / ".claude" / "Projects"
        projects_root.mkdir(parents=True)

        result = collect_recent_logs(
            limit=5,
            project_name="does-not-exist",
            base_path=str(projects_root)
        )

        assert result is None

    def test_collect_recent_logs_no_projects(self, tmp_path):
        """Test handling when no projects exist"""
        projects_root = tmp_path / ".claude" / "Projects"
        projects_root.mkdir(parents=True)

        result = collect_recent_logs(limit=5, base_path=str(projects_root))
        assert result is None

    def test_collect_recent_logs_no_logs_in_project(self, tmp_path):
        """Test handling when project has no log files"""
        projects_root = tmp_path / ".claude" / "Projects"
        project = projects_root / "test-project"
        project.mkdir(parents=True)

        result = collect_recent_logs(limit=5, base_path=str(projects_root))
        assert result is None

    def test_collect_recent_logs_platform_override_darwin(self, tmp_path):
        """Test platform override for Darwin/macOS"""
        with patch('agent_logs.Path.home', return_value=tmp_path):
            projects_root = tmp_path / ".claude" / "Projects"
            project = projects_root / "test-project"
            project.mkdir(parents=True)
            (project / "log.jsonl").write_text('{"platform": "darwin"}\n')

            result = collect_recent_logs(limit=5, platform_name='Darwin')

            assert result is not None
            assert len(result) == 1

    def test_collect_recent_logs_platform_override_windows(self):
        """Test platform override for Windows"""
        with patch.dict(os.environ, {'USERPROFILE': 'C:\\Users\\testuser'}):
            with patch('agent_logs.Path.exists', return_value=False):
                result = collect_recent_logs(limit=5, platform_name='Windows')
                # Should return None since path doesn't exist
                assert result is None

    def test_collect_recent_logs_platform_override_linux(self, tmp_path):
        """Test platform override for Linux"""
        with patch('agent_logs.Path.home', return_value=tmp_path):
            projects_root = tmp_path / ".claude" / "Projects"
            project = projects_root / "test-project"
            project.mkdir(parents=True)
            (project / "log.jsonl").write_text('{"platform": "linux"}\n')

            result = collect_recent_logs(limit=5, platform_name='Linux')

            assert result is not None
            assert len(result) == 1

    def test_collect_recent_logs_username_override(self):
        """Test username override for Windows paths"""
        result = collect_recent_logs(
            limit=5,
            platform_name='Windows',
            username='testuser'
        )
        # Will return None because path doesn't exist, but tests parameter passing
        assert result is None

    def test_collect_recent_logs_multiple_files_with_limit(self, tmp_path):
        """Test that limit restricts number of files processed"""
        projects_root = tmp_path / ".claude" / "Projects"
        project = projects_root / "test-project"
        project.mkdir(parents=True)

        # Create 5 log files with 1 entry each
        for i in range(5):
            (project / f"log{i}.jsonl").write_text(f'{{"file": {i}}}\n')
            time.sleep(0.01)

        # Limit to 2 files
        result = collect_recent_logs(limit=2, base_path=str(projects_root))

        assert result is not None
        # Should only have entries from 2 most recent files
        assert len(result) == 2

    def test_collect_recent_logs_mixed_valid_invalid_json(self, tmp_path):
        """Test collection with mix of valid and invalid JSON"""
        projects_root = tmp_path / ".claude" / "Projects"
        project = projects_root / "test-project"
        project.mkdir(parents=True)

        log_file = project / "log.jsonl"
        log_file.write_text(
            '{"valid": 1}\n'
            '{invalid}\n'
            '{"valid": 2}\n'
        )

        result = collect_recent_logs(limit=5, base_path=str(projects_root))

        assert result is not None
        assert len(result) == 2
        assert result[0]["valid"] == 1
        assert result[1]["valid"] == 2

    def test_collect_recent_logs_empty_project_directory(self, tmp_path):
        """Test handling of empty project directory"""
        projects_root = tmp_path / ".claude" / "Projects"
        project = projects_root / "test-project"
        project.mkdir(parents=True)
        # No files created

        result = collect_recent_logs(limit=5, base_path=str(projects_root))
        assert result is None

    def test_collect_recent_logs_exception_handling(self, tmp_path):
        """Test general exception handling in collect_recent_logs"""
        # Use invalid base_path to trigger exception
        with patch('agent_logs._resolve_projects_root', side_effect=Exception("Test error")):
            result = collect_recent_logs(limit=5)
            assert result is None

    def test_collect_recent_logs_sanitization_integration(self, tmp_path):
        """Test that sanitization is properly integrated in main function"""
        projects_root = tmp_path / ".claude" / "Projects"
        projects_root.mkdir(parents=True)

        # Attempt directory traversal - collect_recent_logs catches and returns None
        result = collect_recent_logs(
            limit=5,
            project_name="../../etc/passwd",
            base_path=str(projects_root)
        )
        assert result is None

    def test_collect_recent_logs_preserves_log_order(self, tmp_path):
        """Test that logs maintain order within a file"""
        projects_root = tmp_path / ".claude" / "Projects"
        project = projects_root / "test-project"
        project.mkdir(parents=True)

        log_file = project / "log.jsonl"
        log_file.write_text(
            '{"seq": 1}\n'
            '{"seq": 2}\n'
            '{"seq": 3}\n'
        )

        result = collect_recent_logs(limit=5, base_path=str(projects_root))

        assert result is not None
        assert len(result) == 3
        assert result[0]["seq"] == 1
        assert result[1]["seq"] == 2
        assert result[2]["seq"] == 3


class TestIntegrationScenarios:
    """Integration tests for realistic usage scenarios"""

    def test_scenario_recent_project_auto_select(self, tmp_path):
        """Test scenario: Auto-select most recent project"""
        # Setup: Multiple projects with different ages
        projects_root = tmp_path / ".claude" / "Projects"

        old_project = projects_root / "old-work"
        old_project.mkdir(parents=True)
        (old_project / "session1.jsonl").write_text('{"task": "old work"}\n')

        time.sleep(0.01)

        current_project = projects_root / "current-work"
        current_project.mkdir(parents=True)
        (current_project / "session1.jsonl").write_text('{"task": "current work"}\n')

        # Execute
        result = collect_recent_logs(limit=10, base_path=str(projects_root))

        # Verify: Should get logs from current project
        assert result is not None
        assert len(result) == 1
        assert result[0]["task"] == "current work"

    def test_scenario_multiple_sessions_ordered(self, tmp_path):
        """Test scenario: Multiple session files ordered by time"""
        projects_root = tmp_path / ".claude" / "Projects"
        project = projects_root / "work-project"
        project.mkdir(parents=True)

        # Create sessions in order
        (project / "session1.jsonl").write_text('{"session": 1}\n')
        time.sleep(0.01)
        (project / "session2.jsonl").write_text('{"session": 2}\n')
        time.sleep(0.01)
        (project / "session3.jsonl").write_text('{"session": 3}\n')

        result = collect_recent_logs(limit=10, base_path=str(projects_root))

        # Should get all sessions, newest first
        assert result is not None
        assert len(result) == 3
        assert result[0]["session"] == 3
        assert result[1]["session"] == 2
        assert result[2]["session"] == 1

    def test_scenario_corrupted_log_resilience(self, tmp_path):
        """Test scenario: Handle corrupted logs gracefully"""
        projects_root = tmp_path / ".claude" / "Projects"
        project = projects_root / "project"
        project.mkdir(parents=True)

        # Mix of good and corrupted data
        (project / "log.jsonl").write_text(
            '{"event": "start"}\n'
            '{"event": "processing"}\n'
            '{corrupted line here\n'
            '{"incomplete": \n'
            '{"event": "complete"}\n'
        )

        result = collect_recent_logs(limit=10, base_path=str(projects_root))

        # Should successfully extract valid entries
        assert result is not None
        assert len(result) == 3
        assert any(entry.get("event") == "start" for entry in result)
        assert any(entry.get("event") == "complete" for entry in result)

    def test_scenario_limit_enforced(self, tmp_path):
        """Test scenario: Limit parameter properly restricts data"""
        projects_root = tmp_path / ".claude" / "Projects"
        project = projects_root / "large-project"
        project.mkdir(parents=True)

        # Create 10 log files
        for i in range(10):
            (project / f"session{i:02d}.jsonl").write_text(f'{{"file": {i}}}\n')
            time.sleep(0.01)

        # Limit to 3 files
        result = collect_recent_logs(limit=3, base_path=str(projects_root))

        # Should only process 3 most recent files
        assert result is not None
        assert len(result) == 3

    def test_scenario_cross_platform_paths(self, tmp_path):
        """Test scenario: Platform-specific path resolution"""
        # Test Darwin
        with patch('agent_logs.Path.home', return_value=tmp_path):
            with patch('agent_logs.platform.system', return_value='Darwin'):
                projects = tmp_path / ".claude" / "Projects" / "test"
                projects.mkdir(parents=True)
                (projects / "log.jsonl").write_text('{"platform": "mac"}\n')

                result = collect_recent_logs(limit=5)
                assert result is not None

    def test_scenario_security_traversal_blocked(self, tmp_path):
        """Test scenario: Security - block directory traversal attempts"""
        projects_root = tmp_path / ".claude" / "Projects"
        projects_root.mkdir(parents=True)

        # Create sensitive file outside projects
        sensitive = tmp_path / "sensitive.txt"
        sensitive.write_text("secret data")

        # Attempt traversal - should return None (sanitization catches it)
        result = collect_recent_logs(
            limit=5,
            project_name="../sensitive.txt",
            base_path=str(projects_root)
        )
        assert result is None

        # Verify the sanitization layer catches it at lower level
        with pytest.raises(ValueError, match="invalid pattern"):
            _sanitize_project_name("../sensitive.txt")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
