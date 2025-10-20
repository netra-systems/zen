#!/usr/bin/env python3
"""
Agent Logs Collection Helper
Collects recent JSONL logs from .claude/Projects for agent CLI integration
Supports multiple AI CLI tools: Claude, Codex, Gemini
"""

import hashlib
import json
import logging
import os
import platform
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any

# Configure module logger
logger = logging.getLogger(__name__)


class LogProvider(Enum):
    """Supported AI CLI tool providers."""
    CLAUDE = "claude"
    CODEX = "codex"
    GEMINI = "gemini"


def convert_to_jsonl_format(logs: List[Dict[str, Any]]) -> str:
    """
    Convert a list of log entries to JSONL format for WebSocket transmission.

    JSONL (JSON Lines) format has one JSON object per line, which is more efficient
    for streaming and processing large log files.

    Args:
        logs: List of log entry dictionaries

    Returns:
        String in JSONL format (one JSON object per line)

    Example:
        >>> logs = [{"event": "start"}, {"event": "end"}]
        >>> result = convert_to_jsonl_format(logs)
        >>> print(result)
        {"event": "start"}
        {"event": "end"}
    """
    if not logs:
        return ""

    jsonl_lines = []
    for log_entry in logs:
        try:
            # Serialize each log entry as a single-line JSON string
            json_line = json.dumps(log_entry, ensure_ascii=False, separators=(',', ':'))
            jsonl_lines.append(json_line)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize log entry: {e}")
            # Skip malformed entries
            continue

    # Join with newlines to create JSONL format
    return '\n'.join(jsonl_lines)


def parse_jsonl_format(jsonl_string: str) -> List[Dict[str, Any]]:
    """
    Parse JSONL format string back into a list of log entries.

    This is the inverse operation of convert_to_jsonl_format(), useful for
    receiving and processing JSONL data from WebSocket or other sources.

    Args:
        jsonl_string: String in JSONL format (one JSON object per line)

    Returns:
        List of log entry dictionaries

    Example:
        >>> jsonl = '{"event": "start"}\\n{"event": "end"}'
        >>> logs = parse_jsonl_format(jsonl)
        >>> print(logs)
        [{'event': 'start'}, {'event': 'end'}]
    """
    if not jsonl_string or not jsonl_string.strip():
        return []

    logs = []
    for line_num, line in enumerate(jsonl_string.split('\n'), 1):
        line = line.strip()
        if not line:
            continue

        try:
            log_entry = json.loads(line)
            logs.append(log_entry)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSONL line {line_num}: {e}")
            # Skip malformed lines
            continue

    return logs


def _get_provider_paths(provider: LogProvider, platform_name: str) -> List[Path]:
    """
    Get log paths for CLI-based AI tools.

    Args:
        provider: AI tool provider
        platform_name: Platform name ('Darwin', 'Windows', 'Linux')

    Returns:
        List of paths to check (in priority order)
    """
    user_home = Path.home()

    provider_paths = {
        LogProvider.CLAUDE: {
            # Claude Code CLI - stores project sessions in ~/.claude/Projects
            'Darwin': [user_home / ".claude" / "Projects"],
            'Windows': [Path(os.environ.get('USERPROFILE', user_home)) / ".claude" / "Projects"],
            'Linux': [user_home / ".claude" / "Projects"],
        },
        LogProvider.CODEX: {
            # OpenAI Codex CLI - stores sessions in ~/.codex/sessions/YYYY/MM/DD/*.jsonl
            'Darwin': [
                user_home / ".codex" / "sessions",
                user_home / ".codex" / "log",
            ],
            'Windows': [
                Path(os.environ.get('USERPROFILE', user_home)) / ".codex" / "sessions",
                Path(os.environ.get('USERPROFILE', user_home)) / ".codex" / "log",
            ],
            'Linux': [
                user_home / ".codex" / "sessions",
                user_home / ".codex" / "log",
            ],
        },
        LogProvider.GEMINI: {
            # Google Gemini CLI - stores chat sessions in ~/.gemini/tmp/<hash>/chats/*.json
            'Darwin': [
                user_home / ".gemini" / "tmp",
                user_home / ".gemini",
            ],
            'Windows': [
                Path(os.environ.get('USERPROFILE', user_home)) / ".gemini" / "tmp",
                Path(os.environ.get('USERPROFILE', user_home)) / ".gemini",
            ],
            'Linux': [
                user_home / ".gemini" / "tmp",
                user_home / ".gemini",
            ],
        },
    }

    return provider_paths.get(provider, {}).get(platform_name, [])


def _get_log_file_patterns(provider: LogProvider) -> List[str]:
    """
    Get glob patterns for log files from different providers.

    Args:
        provider: AI tool provider

    Returns:
        List of glob patterns to match log files
    """
    patterns = {
        LogProvider.CLAUDE: ["*.jsonl"],
        LogProvider.CODEX: [
            "**/*.jsonl",
            "**/rollout-*.jsonl",
        ],
        LogProvider.GEMINI: [
            "**/chats/session-*.json",
            "**/logs.json",
            "**/chats/*.json",
        ],
    }

    return patterns.get(provider, ["*.jsonl"])


def _parse_provider_log(log_entry: Dict[str, Any], provider: LogProvider, file_path: Path) -> List[Dict[str, Any]]:
    """
    Parse and normalize log entries from different providers.

    Args:
        log_entry: Raw log entry
        provider: Provider that generated the log
        file_path: Path to the source file

    Returns:
        List of normalized log entries
    """
    normalized_logs = []

    if provider == LogProvider.CLAUDE:
        # Claude JSONL - each line is already a separate entry
        normalized_logs.append({
            **log_entry,
            '_provider': 'claude',
            '_source_file': file_path.name
        })

    elif provider == LogProvider.CODEX:
        # Codex JSONL - each line is a separate entry
        normalized_logs.append({
            **log_entry,
            '_provider': 'codex',
            '_source_file': file_path.name,
        })

    elif provider == LogProvider.GEMINI:
        # Gemini JSON - single file may contain entire session
        if 'messages' in log_entry:
            # Session file with multiple messages
            for idx, message in enumerate(log_entry.get('messages', [])):
                normalized_logs.append({
                    'timestamp': log_entry.get('timestamp') or message.get('timestamp'),
                    'session_id': log_entry.get('session_id'),
                    'model': log_entry.get('model', 'gemini-pro'),
                    'role': message.get('role'),
                    'content': message.get('content'),
                    'message_index': idx,
                    '_provider': 'gemini',
                    '_source_file': file_path.name,
                })
        else:
            # Single message or unknown format - keep as-is
            normalized_logs.append({
                **log_entry,
                '_provider': 'gemini',
                '_source_file': file_path.name
            })

    return normalized_logs


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


def _collect_jsonl_files(project_path: Path, limit: int, provider: LogProvider = LogProvider.CLAUDE) -> tuple[List[Dict[str, Any]], int, List[Dict[str, str]]]:
    """
    Collect and parse log files from directory (supports recursive patterns and multiple formats).

    Args:
        project_path: Path to project/logs directory
        limit: Maximum number of log files to read
        provider: AI tool provider (affects file patterns)

    Returns:
        Tuple of (list of parsed log entries, number of files read, list of file info dicts)
    """
    if not project_path.exists() or not project_path.is_dir():
        logger.warning(f"Project path does not exist: {project_path}")
        return [], 0, []

    try:
        # Get provider-specific file patterns
        patterns = _get_log_file_patterns(provider)

        # Find all matching log files
        log_files = []
        for pattern in patterns:
            log_files.extend(project_path.glob(pattern))

        if not log_files:
            logger.info(f"No log files found in {project_path} for provider {provider.value}")
            return [], 0, []

        # Remove duplicates and sort by modification time (most recent first)
        log_files = list(set(log_files))
        log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        # Limit number of files to read
        log_files = log_files[:limit]
        files_read = len(log_files)

        all_logs = []
        file_info = []

        for log_file in log_files:
            try:
                # Calculate file hash
                hasher = hashlib.sha256()
                entry_count = 0

                with open(log_file, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b''):
                        hasher.update(chunk)

                file_hash = hasher.hexdigest()[:8]

                # Parse based on file extension
                if log_file.suffix == '.jsonl':
                    # JSONL format - one JSON object per line (Claude, Codex)
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if not line:
                                continue

                            try:
                                log_entry = json.loads(line)
                                # Parse and normalize based on provider
                                normalized = _parse_provider_log(log_entry, provider, log_file)
                                all_logs.extend(normalized)
                                entry_count += len(normalized)
                            except json.JSONDecodeError as e:
                                logger.debug(
                                    f"Skipping malformed JSON in {log_file.name}:{line_num}: {e}"
                                )
                                continue

                elif log_file.suffix == '.json':
                    # Single JSON file (Gemini format)
                    with open(log_file, 'r', encoding='utf-8') as f:
                        try:
                            log_entry = json.load(f)
                            # Parse and normalize - may return multiple entries
                            normalized = _parse_provider_log(log_entry, provider, log_file)
                            all_logs.extend(normalized)
                            entry_count = len(normalized)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Could not parse JSON file {log_file.name}: {e}")

                # Calculate relative path for better tracking
                try:
                    relative_path = str(log_file.relative_to(project_path))
                except ValueError:
                    relative_path = log_file.name

                file_info.append({
                    'name': log_file.name,
                    'path': relative_path,
                    'hash': file_hash,
                    'entries': entry_count,
                    'format': 'jsonl' if log_file.suffix == '.jsonl' else 'json'
                })

            except Exception as e:
                logger.warning(f"Error reading {log_file.name}: {e}")
                continue

        logger.info(f"Collected {len(all_logs)} log entries from {files_read} files for provider {provider.value}")
        return all_logs, files_read, file_info

    except Exception as e:
        logger.error(f"Error collecting log files for {provider.value}: {e}")
        return [], 0, []


def collect_recent_logs(
    limit: int = 1,
    project_name: Optional[str] = None,
    base_path: Optional[str] = None,
    username: Optional[str] = None,
    platform_name: Optional[str] = None,
    provider: str = "claude"
) -> Optional[tuple[List[Dict[str, Any]], int, List[Dict[str, str]]]]:
    """
    Collect recent logs from AI CLI tools (Claude, Codex, Gemini).

    Args:
        limit: Maximum number of log files to read (default: 1). For best results, use 1 log at a time for focused analysis.
        project_name: Specific project name or None for most recent (Claude only)
        base_path: Direct path override to logs directory OR a specific log file
        username: Windows username override
        platform_name: Platform override for testing ('Darwin', 'Windows', 'Linux')
        provider: AI tool provider ('claude', 'codex', 'gemini')

    Returns:
        Tuple of (list of log entry dicts, number of files read, list of file info) or None if no logs found

    Raises:
        ValueError: If limit is not positive or project_name is invalid
    """
    if limit < 1:
        raise ValueError(f"Limit must be positive, got {limit}")

    try:
        # Convert provider string to enum
        try:
            provider_enum = LogProvider(provider.lower())
        except ValueError:
            logger.error(f"Unknown provider: {provider}. Using claude as default.")
            provider_enum = LogProvider.CLAUDE

        # Check if base_path points to a specific file
        if base_path:
            base_path_obj = Path(base_path)
            if base_path_obj.is_file():
                # Handle direct file path
                logger.info(f"Reading specific log file: {base_path_obj}")

                if not base_path_obj.exists():
                    logger.warning(f"Specified log file does not exist: {base_path_obj}")
                    return None

                # Read the single file
                all_logs = []
                file_info = []

                try:
                    # Calculate file hash
                    hasher = hashlib.sha256()
                    entry_count = 0

                    with open(base_path_obj, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b''):
                            hasher.update(chunk)

                    file_hash = hasher.hexdigest()[:8]

                    # Parse based on file extension
                    if base_path_obj.suffix == '.jsonl':
                        # JSONL format
                        with open(base_path_obj, 'r', encoding='utf-8') as f:
                            for line_num, line in enumerate(f, 1):
                                line = line.strip()
                                if not line:
                                    continue

                                try:
                                    log_entry = json.loads(line)
                                    normalized = _parse_provider_log(log_entry, provider_enum, base_path_obj)
                                    all_logs.extend(normalized)
                                    entry_count += len(normalized)
                                except json.JSONDecodeError as e:
                                    logger.debug(
                                        f"Skipping malformed JSON in {base_path_obj.name}:{line_num}: {e}"
                                    )
                                    continue

                    elif base_path_obj.suffix == '.json':
                        # Single JSON file
                        with open(base_path_obj, 'r', encoding='utf-8') as f:
                            try:
                                log_entry = json.load(f)
                                normalized = _parse_provider_log(log_entry, provider_enum, base_path_obj)
                                all_logs.extend(normalized)
                                entry_count = len(normalized)
                            except json.JSONDecodeError as e:
                                logger.warning(f"Could not parse JSON file {base_path_obj.name}: {e}")

                    file_info.append({
                        'name': base_path_obj.name,
                        'hash': file_hash,
                        'entries': entry_count
                    })

                    logger.info(f"Collected {len(all_logs)} log entries from {base_path_obj.name}")
                    return all_logs, 1, file_info

                except Exception as e:
                    logger.error(f"Error reading log file {base_path_obj}: {e}")
                    return None

        # Provider-based path resolution
        platform_name = platform_name or platform.system()

        if provider_enum == LogProvider.CLAUDE:
            # Original Claude logic with project-based structure
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
            logs, files_read, file_info = _collect_jsonl_files(project_path, limit, provider_enum)

        else:
            # For Codex and Gemini, use provider-specific paths
            provider_paths = _get_provider_paths(provider_enum, platform_name)

            logs = None
            files_read = 0
            file_info = []

            # Try each provider path until we find logs
            for provider_path in provider_paths:
                if base_path:
                    # Override with custom base path
                    provider_path = Path(base_path)

                if not provider_path.exists():
                    logger.debug(f"Path does not exist: {provider_path}")
                    continue

                logger.info(f"Searching for {provider_enum.value} logs in: {provider_path}")
                logs, files_read, file_info = _collect_jsonl_files(provider_path, limit, provider_enum)

                if logs:
                    break

            if not logs:
                logger.warning(f"No logs found for provider {provider_enum.value}")
                return None

        if not logs:
            return None

        return logs, files_read, file_info

    except Exception as e:
        logger.error(f"Failed to collect logs: {e}")
        return None
