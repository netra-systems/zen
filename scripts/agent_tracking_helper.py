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
    
    def _format_header(self, language: str, metadata: Dict[str, str]) -> str:
        """Format the tracking header based on language."""
        timestamp = datetime.now().astimezone().isoformat()
        
        # Base metadata
        header_lines = [
            f"Last Modified: {timestamp}",
            f"Agent: {metadata['agent']} ({metadata['model']})",
            f"Task ID: {metadata['task_id']}",
            f"Git Branch: {self.git_info['branch']}",
            f"Git Commit: {self.git_info['commit']}",
            f"Prompt Summary: {metadata['prompt_summary'][:200]}",
            f"Changes: {metadata['changes'][:200]}"
        ]
        
        # Format based on language
        if language == 'python':
            header = "# Agent Modification Tracking\n"
            header += "# " + "=" * 27 + "\n"
            for line in header_lines:
                header += f"# {line}\n"
            header += "# " + "=" * 27 + "\n"
        
        elif language in ['javascript', 'typescript', 'java', 'c', 'cpp', 'csharp', 'go', 'rust', 'swift', 'kotlin', 'php']:
            header = "/**\n"
            header += " * Agent Modification Tracking\n"
            header += " * " + "=" * 27 + "\n"
            for line in header_lines:
                header += f" * {line}\n"
            header += " * " + "=" * 27 + "\n"
            header += " */\n"
        
        elif language in ['jsx', 'tsx', 'html', 'vue']:
            header = "{/* \n"
            header += "  Agent Modification Tracking\n"
            header += "  " + "=" * 27 + "\n"
            for line in header_lines:
                header += f"  {line}\n"
            header += "  " + "=" * 27 + "\n"
            header += "*/}\n"
        
        elif language == 'ruby':
            header = "# Agent Modification Tracking\n"
            header += "# " + "=" * 27 + "\n"
            for line in header_lines:
                header += f"# {line}\n"
            header += "# " + "=" * 27 + "\n"
        
        elif language in ['bash', 'yaml', 'sql']:
            header = "# Agent Modification Tracking\n"
            header += "# " + "=" * 27 + "\n"
            for line in header_lines:
                header += f"# {line}\n"
            header += "# " + "=" * 27 + "\n"
        
        else:
            # Default to hash comment style
            header = "# Agent Modification Tracking\n"
            header += "# " + "=" * 27 + "\n"
            for line in header_lines:
                header += f"# {line}\n"
            header += "# " + "=" * 27 + "\n"
        
        return header
    
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
    
    def add_tracking_header(
        self,
        file_path: str,
        agent: str,
        model: str,
        task_id: str,
        prompt_summary: str,
        changes: str,
        dry_run: bool = False
    ) -> bool:
        """Add or update tracking header in a file."""
        path = Path(file_path)
        
        # Check if file should be excluded
        if self._should_exclude(path):
            print(f"Skipping excluded file: {file_path}")
            return False
        
        # Determine language
        language = self._get_language(path)
        if not language:
            print(f"Unknown file type, using default format: {file_path}")
            language = 'default'
        
        # Read file content
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return False
        
        # Extract existing header and history
        existing_header, content_without_header = self._extract_existing_header(content, language)
        history = []
        
        if existing_header:
            history = self._extract_history(existing_header, language)
        
        # Create new header
        metadata = {
            'agent': agent,
            'model': model,
            'task_id': task_id,
            'prompt_summary': prompt_summary,
            'changes': changes
        }
        
        new_header = self._format_header(language, metadata)
        
        # Create history entry for current modification
        timestamp = datetime.now().astimezone().isoformat()
        current_entry = f"{timestamp} - {agent} - {changes[:50]}"
        
        # Add history section if there are previous modifications
        if history or existing_header:
            history_section = self._format_history(history, current_entry, language)
            new_header += history_section
        
        # Combine header with content
        new_content = new_header + "\n" + content_without_header
        
        # Write or display result
        if dry_run:
            print(f"=== DRY RUN for {file_path} ===")
            print(new_content[:500])  # Show first 500 chars
            print("...")
            return True
        else:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated tracking header in: {file_path}")
                return True
            except Exception as e:
                print(f"Error writing file {file_path}: {e}")
                return False
    
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


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Add or update agent tracking headers in modified files'
    )
    
    parser.add_argument(
        'file_path',
        help='Path to the file to update'
    )
    
    parser.add_argument(
        '--agent',
        required=True,
        help='Name of the AI agent (e.g., "Claude Code")'
    )
    
    parser.add_argument(
        '--model',
        required=True,
        help='Model version (e.g., "claude-opus-4-1-20250805")'
    )
    
    parser.add_argument(
        '--task-id',
        required=True,
        help='Task or conversation ID'
    )
    
    parser.add_argument(
        '--prompt',
        required=True,
        dest='prompt_summary',
        help='Brief summary of the prompt (max 200 chars)'
    )
    
    parser.add_argument(
        '--changes',
        required=True,
        help='Brief description of changes (max 200 chars)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without modifying files'
    )
    
    args = parser.parse_args()
    
    # Create helper and process file
    helper = AgentTrackingHelper()
    success = helper.add_tracking_header(
        file_path=args.file_path,
        agent=args.agent,
        model=args.model,
        task_id=args.task_id,
        prompt_summary=args.prompt_summary[:200],
        changes=args.changes[:200],
        dry_run=args.dry_run
    )
    
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())