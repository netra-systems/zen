#!/usr/bin/env python3
"""
Agent Logs Collection Helper
Collects recent JSONL logs from .claude/Projects for agent CLI integration
"""

import json
import logging
import os
import platform
from pathlib import Path
from typing import Optional, List, Dict, Any

# Configure module logger
logger = logging.getLogger(__name__)


def _get_default_user() -> Optional[str]:
    """
    Get default username for Windows path resolution.

    Returns:
        Username from environment or None if not available
    """
    return os.environ.get('USERNAME') or os.environ.get('USER')


def _resolve_projects_root(
    platform_name: Optional[str] = None,
    username: Optional[str] = None,
    base_path: Optional[Path] = None
) -> Path:
    """
    Resolve the .claude/Projects root directory based on platform.

    Args:
        platform_name: Platform identifier ('Darwin', 'Windows', 'Linux') or None for auto-detect
        username: Windows username override
        base_path: Direct path override (bypasses platform resolution)

    Returns:
        Path to .claude/Projects directory

    Raises:
        ValueError: If path cannot be resolved
    """
    if base_path:
        return Path(base_path).resolve()

    platform_name = platform_name or platform.system()

    if platform_name == 'Windows':
        # Windows: C:\Users\<username>\.claude\Projects
        if username:
            user_home = Path(f"C:/Users/{username}")
        else:
            user_home = Path(os.environ.get('USERPROFILE', Path.home()))
    else:
        # macOS/Linux: ~/.claude/Projects
        user_home = Path.home()

    projects_root = user_home / ".claude" / "Projects"

    return projects_root.resolve()


def _sanitize_project_name(project_name: str) -> str:
    """
    Sanitize project name to prevent directory traversal attacks.

    Args:
        project_name: Raw project name

    Returns:
        Sanitized project name safe for path construction

    Raises:
        ValueError: If project name contains dangerous patterns
    """
    if not project_name:
        raise ValueError("Project name cannot be empty")

    # Remove path separators and parent directory references
    dangerous_patterns = ['..', '/', '\\', '\0']
    for pattern in dangerous_patterns:
        if pattern in project_name:
            raise ValueError(f"Project name contains invalid pattern: {pattern}")

    # Remove leading/trailing whitespace and dots
    sanitized = project_name.strip().strip('.')

    if not sanitized:
        raise ValueError("Project name invalid after sanitization")

    return sanitized


def _find_most_recent_project(projects_root: Path) -> Optional[Path]:
    """
    Find the most recently modified project directory.

    Args:
        projects_root: Path to .claude/Projects directory

    Returns:
        Path to most recent project directory or None if no projects found
    """
    if not projects_root.exists() or not projects_root.is_dir():
        logger.warning(f"Projects root does not exist: {projects_root}")
        return None

    try:
        # Get all subdirectories
        project_dirs = [p for p in projects_root.iterdir() if p.is_dir()]

        if not project_dirs:
            logger.warning(f"No project directories found in {projects_root}")
            return None

        # Sort by modification time, most recent first
        project_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        return project_dirs[0]

    except Exception as e:
        logger.error(f"Error finding most recent project: {e}")
        return None


def _collect_jsonl_files(project_path: Path, limit: int) -> List[Dict[str, Any]]:
    """
    Collect and parse JSONL files from project directory.

    Args:
        project_path: Path to project directory
        limit: Maximum number of log files to read

    Returns:
        List of parsed log entries (dicts)
    """
    if not project_path.exists() or not project_path.is_dir():
        logger.warning(f"Project path does not exist: {project_path}")
        return []

    try:
        # Find all .jsonl files
        jsonl_files = list(project_path.glob("*.jsonl"))

        if not jsonl_files:
            logger.info(f"No .jsonl files found in {project_path}")
            return []

        # Sort by modification time, most recent first
        jsonl_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        # Limit number of files to read
        jsonl_files = jsonl_files[:limit]

        all_logs = []

        for jsonl_file in jsonl_files:
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            log_entry = json.loads(line)
                            all_logs.append(log_entry)
                        except json.JSONDecodeError as e:
                            logger.debug(
                                f"Skipping malformed JSON in {jsonl_file.name}:{line_num}: {e}"
                            )
                            continue

            except Exception as e:
                logger.warning(f"Error reading {jsonl_file.name}: {e}")
                continue

        logger.info(f"Collected {len(all_logs)} log entries from {len(jsonl_files)} files")
        return all_logs

    except Exception as e:
        logger.error(f"Error collecting JSONL files: {e}")
        return []


def collect_recent_logs(
    limit: int = 5,
    project_name: Optional[str] = None,
    base_path: Optional[str] = None,
    username: Optional[str] = None,
    platform_name: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Collect recent JSONL logs from .claude/Projects directory.

    Args:
        limit: Maximum number of log files to read (default: 5)
        project_name: Specific project name or None for most recent
        base_path: Direct path override to logs directory
        username: Windows username override
        platform_name: Platform override for testing ('Darwin', 'Windows', 'Linux')

    Returns:
        List of log entry dicts or None if no logs found

    Raises:
        ValueError: If limit is not positive or project_name is invalid
    """
    if limit < 1:
        raise ValueError(f"Limit must be positive, got {limit}")

    try:
        # Resolve projects root
        base = Path(base_path) if base_path else None
        projects_root = _resolve_projects_root(
            platform_name=platform_name,
            username=username,
            base_path=base
        )

        # Determine target project
        if project_name:
            sanitized_name = _sanitize_project_name(project_name)
            project_path = projects_root / sanitized_name

            if not project_path.exists():
                logger.warning(f"Specified project does not exist: {project_path}")
                return None
        else:
            # Auto-detect most recent project
            project_path = _find_most_recent_project(projects_root)
            if not project_path:
                return None

        # Collect logs
        logs = _collect_jsonl_files(project_path, limit)

        if not logs:
            return None

        return logs

    except Exception as e:
        logger.error(f"Failed to collect logs: {e}")
        return None
