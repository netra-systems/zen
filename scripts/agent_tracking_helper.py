#!/usr/bin/env python3
"""
Agent Modification Tracking Helper

This script helps AI coding agents add or update tracking headers in modified files
according to the specification in SPEC/agent_tracking.xml.

Usage:
    python scripts/agent_tracking_helper.py <file_path> --agent "Claude Code" --model "claude-opus-4-1" --task-id "conv_123" --prompt "Fix database query" --changes "Optimized query performance"
"""

import argparse
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple


class AgentTrackingHelper:
    """Helper class for managing agent modification tracking headers."""
    
    # File extensions to language mapping
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'jsx',
        '.tsx': 'tsx',
        '.html': 'html',
        '.vue': 'vue',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.rb': 'ruby',
        '.go': 'go',
        '.rs': 'rust',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.php': 'php',
        '.sql': 'sql',
        '.sh': 'bash',
        '.yaml': 'yaml',
        '.yml': 'yaml'
    }
    
    # Files to exclude from tracking
    EXCLUDED_PATTERNS = [
        'package.json', 'package-lock.json',
        'requirements.txt', 'poetry.lock', 'Pipfile.lock',
        '*.min.js', '*.min.css',
        '*.pyc', '*.pyo', '*.pyd',
        '*.so', '*.dll', '*.dylib',
        '*.exe', '*.bin',
        '*.jpg', '*.jpeg', '*.png', '*.gif', '*.ico', '*.svg',
        '*.pdf', '*.doc', '*.docx',
        '*.zip', '*.tar', '*.gz',
        '*.log', '*.csv', '*.json', '*.xml',
        '.gitignore', '.dockerignore',
        'LICENSE', 'README.md', 'CHANGELOG.md'
    ]
    
    def __init__(self):
        """Initialize the helper."""
        self.git_info = self._get_git_info()
    
    def _get_git_info(self) -> Dict[str, str]:
        """Get current git branch and commit hash."""
        try:
            branch = subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                text=True
            ).strip()
            
            commit = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                text=True
            ).strip()
            
            return {'branch': branch, 'commit': commit}
        except subprocess.CalledProcessError:
            return {'branch': 'unknown', 'commit': 'unknown'}
    
    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded from tracking."""
        file_name = file_path.name
        
        # Check exact matches and patterns
        for pattern in self.EXCLUDED_PATTERNS:
            if '*' in pattern:
                # Simple wildcard matching
                if pattern.startswith('*'):
                    if file_name.endswith(pattern[1:]):
                        return True
                elif pattern.endswith('*'):
                    if file_name.startswith(pattern[:-1]):
                        return True
            elif file_name == pattern:
                return True
        
        # Check if file is in .gitignore
        try:
            subprocess.check_output(
                ['git', 'check-ignore', str(file_path)],
                stderr=subprocess.DEVNULL
            )
            return True  # File is ignored by git
        except subprocess.CalledProcessError:
            pass  # File is not ignored
        
        return False
    
    def _get_language(self, file_path: Path) -> Optional[str]:
        """Determine the language based on file extension."""
        ext = file_path.suffix.lower()
        return self.LANGUAGE_MAP.get(ext)
    
    def _create_header_lines(self, metadata):
        """Create base metadata lines for header"""
        timestamp = datetime.now().astimezone().isoformat()
        return [
            f"Last Modified: {timestamp}",
            f"Agent: {metadata['agent']} ({metadata['model']})",
            f"Task ID: {metadata['task_id']}",
            f"Git Branch: {self.git_info['branch']}",
            f"Git Commit: {self.git_info['commit']}",
            f"Prompt Summary: {metadata['prompt_summary'][:200]}",
            f"Changes: {metadata['changes'][:200]}"
        ]

    def _format_hash_comment_header(self, header_lines):
        """Format header with hash comments for Python/Ruby/Bash/YAML/SQL"""
        header = "# Agent Modification Tracking\n"
        header += "# " + "=" * 27 + "\n"
        for line in header_lines:
            header += f"# {line}\n"
        header += "# " + "=" * 27 + "\n"
        return header

    def _format_block_comment_header(self, header_lines):
        """Format header with block comments for JS/TS/Java/C/etc"""
        header = "/**\n"
        header += " * Agent Modification Tracking\n"
        header += " * " + "=" * 27 + "\n"
        for line in header_lines:
            header += f" * {line}\n"
        header += " * " + "=" * 27 + "\n"
        header += " */\n"
        return header

    def _format_jsx_comment_header(self, header_lines):
        """Format header with JSX comments for JSX/TSX/HTML/Vue"""
        header = "{/* \n"
        header += "  Agent Modification Tracking\n"
        header += "  " + "=" * 27 + "\n"
        for line in header_lines:
            header += f"  {line}\n"
        header += "  " + "=" * 27 + "\n"
        header += "*/}\n"
        return header

    def _format_header(self, language: str, metadata: Dict[str, str]) -> str:
        """Format the tracking header based on language."""
        header_lines = self._create_header_lines(metadata)
        if language in ['javascript', 'typescript', 'java', 'c', 'cpp', 'csharp', 'go', 'rust', 'swift', 'kotlin', 'php']:
            return self._format_block_comment_header(header_lines)
        elif language in ['jsx', 'tsx', 'html', 'vue']:
            return self._format_jsx_comment_header(header_lines)
        else:
            return self._format_hash_comment_header(header_lines)
    
    def _extract_existing_header(self, content: str, language: str) -> Tuple[Optional[str], str]:
        """Extract existing agent tracking header if present."""
        # Define patterns based on language
        if language == 'python' or language in ['ruby', 'bash', 'yaml', 'sql']:
            pattern = r'(# Agent Modification Tracking\n# =+\n(?:# .*\n)*# =+\n)'
        elif language in ['javascript', 'typescript', 'java', 'c', 'cpp', 'csharp', 'go', 'rust', 'swift', 'kotlin', 'php']:
            pattern = r'(/\*\*\n \* Agent Modification Tracking\n \* =+\n(?: \* .*\n)* \* =+\n \*/\n)'
        elif language in ['jsx', 'tsx', 'html', 'vue']:
            pattern = r'(\{/\* \n  Agent Modification Tracking\n  =+\n(?:  .*\n)*  =+\n\*/\}\n)'
        else:
            pattern = r'(# Agent Modification Tracking\n# =+\n(?:# .*\n)*# =+\n)'
        
        match = re.search(pattern, content)
        if match:
            header = match.group(1)
            content_without_header = content[:match.start()] + content[match.end():]
            return header, content_without_header
        
        return None, content
    
    def _extract_history(self, existing_header: str, language: str) -> List[str]:
        """Extract history entries from existing header."""
        history = []
        
        # Find history section if it exists
        if language == 'python' or language in ['ruby', 'bash', 'yaml', 'sql']:
            history_pattern = r'# Agent Modification History\n# =+\n((?:# Entry \d+:.*\n)*)'
        elif language in ['javascript', 'typescript', 'java', 'c', 'cpp', 'csharp', 'go', 'rust', 'swift', 'kotlin', 'php']:
            history_pattern = r' \* Agent Modification History\n \* =+\n((?:  \* Entry \d+:.*\n)*)'
        else:
            history_pattern = r'# Agent Modification History\n# =+\n((?:# Entry \d+:.*\n)*)'
        
        match = re.search(history_pattern, existing_header)
        if match:
            history_text = match.group(1)
            # Extract individual entries
            entry_pattern = r'Entry \d+: (.+)'
            entries = re.findall(entry_pattern, history_text)
            history = entries[:4]  # Keep max 4 entries (we'll add current as 5th)
        
        return history
    
    def _format_history(self, history: List[str], current_entry: str, language: str) -> str:
        """Format the history section."""
        if not history and not current_entry:
            return ""
        
        all_entries = [current_entry] + history
        all_entries = all_entries[:5]  # Keep max 5 entries
        
        if language == 'python' or language in ['ruby', 'bash', 'yaml', 'sql']:
            history_section = "\n# Agent Modification History\n"
            history_section += "# " + "=" * 27 + "\n"
            for i, entry in enumerate(all_entries, 1):
                history_section += f"# Entry {i}: {entry}\n"
            history_section += "# " + "=" * 27 + "\n"
        
        elif language in ['javascript', 'typescript', 'java', 'c', 'cpp', 'csharp', 'go', 'rust', 'swift', 'kotlin', 'php']:
            history_section = "\n/**\n"
            history_section += " * Agent Modification History\n"
            history_section += " * " + "=" * 27 + "\n"
            for i, entry in enumerate(all_entries, 1):
                history_section += f" * Entry {i}: {entry}\n"
            history_section += " * " + "=" * 27 + "\n"
            history_section += " */\n"
        
        else:
            history_section = "\n# Agent Modification History\n"
            history_section += "# " + "=" * 27 + "\n"
            for i, entry in enumerate(all_entries, 1):
                history_section += f"# Entry {i}: {entry}\n"
            history_section += "# " + "=" * 27 + "\n"
        
        return history_section
    
    def _validate_and_prepare_file(self, file_path):
        """Validate file path and determine language"""
        path = Path(file_path)
        if self._should_exclude(path):
            print(f"Skipping excluded file: {file_path}")
            return None, None
        language = self._get_language(path) or 'default'
        if not self._get_language(path):
            print(f"Unknown file type, using default format: {file_path}")
        return path, language

    def _read_file_content(self, path, file_path):
        """Read file content safely"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None

    def _extract_header_and_history(self, content, language):
        """Extract existing header and history"""
        existing_header, content_without_header = self._extract_existing_header(content, language)
        history = self._extract_history(existing_header, language) if existing_header else []
        return existing_header, content_without_header, history

    def _create_tracking_metadata(self, agent, model, task_id, prompt_summary, changes):
        """Create metadata dictionary for tracking header"""
        return {
            'agent': agent, 'model': model, 'task_id': task_id,
            'prompt_summary': prompt_summary, 'changes': changes
        }

    def _generate_new_header(self, language, metadata):
        """Generate new tracking header"""
        return self._format_header(language, metadata)

    def _create_history_entry(self, agent, changes):
        """Create history entry for current modification"""
        timestamp = datetime.now().astimezone().isoformat()
        return f"{timestamp} - {agent} - {changes[:50]}"

    def _add_history_section(self, new_header, history, existing_header, current_entry, language):
        """Add history section if needed"""
        if history or existing_header:
            history_section = self._format_history(history, current_entry, language)
            return new_header + history_section
        return new_header

    def _finalize_content(self, new_header, content_without_header, dry_run, path, file_path):
        """Finalize and write content"""
        new_content = new_header + "\n" + content_without_header
        if dry_run:
            print(f"=== DRY RUN for {file_path} ===")
            print(new_content[:500] + "...")
            return True
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated tracking header in: {file_path}")
            return True
        except Exception as e:
            print(f"Error writing file {file_path}: {e}")
            return False

    def add_tracking_header(
        self, file_path: str, agent: str, model: str, task_id: str,
        prompt_summary: str, changes: str, dry_run: bool = False
    ) -> bool:
        """Add or update tracking header in a file."""
        path, language = self._validate_and_prepare_file(file_path)
        if not path: return False
        content = self._read_file_content(path, file_path)
        if not content: return False
        existing_header, content_without_header, history = self._extract_header_and_history(content, language)
        metadata = self._create_tracking_metadata(agent, model, task_id, prompt_summary, changes)
        new_header = self._generate_new_header(language, metadata)
        current_entry = self._create_history_entry(agent, changes)
        new_header = self._add_history_section(new_header, history, existing_header, current_entry, language)
        return self._finalize_content(new_header, content_without_header, dry_run, path, file_path)
    
    def create_audit_log_entry(
        self,
        file_path: str,
        agent: str,
        model: str,
        task_id: str,
        prompt_hash: str,
        lines_added: int = 0,
        lines_removed: int = 0,
        functions_modified: List[str] = None
    ) -> Dict:
        """Create an audit log entry for the modification."""
        return {
            'timestamp': datetime.now().astimezone().isoformat(),
            'agent': agent,
            'model': model,
            'task_id': task_id,
            'file_path': str(file_path),
            'git_branch': self.git_info['branch'],
            'git_commit': self.git_info['commit'],
            'prompt_hash': prompt_hash,
            'changes': {
                'lines_added': lines_added,
                'lines_removed': lines_removed,
                'functions_modified': functions_modified or []
            }
        }


def _create_argument_parser():
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        description='Add or update agent tracking headers in modified files'
    )
    parser.add_argument('file_path', help='Path to the file to update')
    return parser

def _add_required_arguments(parser):
    """Add required arguments to parser"""
    parser.add_argument('--agent', required=True, help='Name of the AI agent (e.g., "Claude Code")')
    parser.add_argument('--model', required=True, help='Model version (e.g., "claude-opus-4-1-20250805")')
    parser.add_argument('--task-id', required=True, help='Task or conversation ID')
    parser.add_argument('--prompt', required=True, dest='prompt_summary', help='Brief summary of the prompt (max 200 chars)')
    parser.add_argument('--changes', required=True, help='Brief description of changes (max 200 chars)')

def _add_optional_arguments(parser):
    """Add optional arguments to parser"""
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')

def _process_tracking_header(args):
    """Process tracking header with parsed arguments"""
    helper = AgentTrackingHelper()
    success = helper.add_tracking_header(
        file_path=args.file_path, agent=args.agent, model=args.model,
        task_id=args.task_id, prompt_summary=args.prompt_summary[:200],
        changes=args.changes[:200], dry_run=args.dry_run
    )
    return success

def main():
    """Main entry point for the script."""
    parser = _create_argument_parser()
    _add_required_arguments(parser)
    _add_optional_arguments(parser)
    args = parser.parse_args()
    success = _process_tracking_header(args)
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())