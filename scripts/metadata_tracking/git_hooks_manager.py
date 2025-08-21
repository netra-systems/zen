#!/usr/bin/env python3
"""
Git Hooks Manager for Metadata Tracking
Handles installation and management of git hooks for AI metadata validation.
"""

import os
from pathlib import Path
from typing import Any, Dict


class GitHooksManager:
    """Manages git hooks for metadata tracking."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.git_hooks_dir = project_root / ".git" / "hooks"
    
    def install_hooks(self) -> bool:
        """Install git hooks for metadata validation."""
        try:
            self._create_hooks_directory()
            self._install_pre_commit_hook()
            self._install_post_commit_hook()
            
            print("[SUCCESS] Git hooks installed successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to install git hooks: {e}")
            return False
    
    def _create_hooks_directory(self) -> None:
        """Create hooks directory if it doesn't exist."""
        self.git_hooks_dir.mkdir(parents=True, exist_ok=True)
    
    def _install_pre_commit_hook(self) -> None:
        """Install pre-commit hook for metadata validation."""
        pre_commit_hook = self.git_hooks_dir / "pre-commit"
        content = self._get_pre_commit_content()
        
        with open(pre_commit_hook, 'w') as f:
            f.write(content)
        
        os.chmod(pre_commit_hook, 0o755)
    
    def _install_post_commit_hook(self) -> None:
        """Install post-commit hook for metadata archiving."""
        post_commit_hook = self.git_hooks_dir / "post-commit"
        content = self._get_post_commit_content()
        
        with open(post_commit_hook, 'w') as f:
            f.write(content)
        
        os.chmod(post_commit_hook, 0o755)
    
    def _get_pre_commit_content(self) -> str:
        """Get pre-commit hook content."""
        return """#!/bin/bash
# AI Agent Metadata Validation Hook

echo "Validating AI agent metadata headers..."

# Run metadata validator
python scripts/metadata_validator.py --validate-all

if [ $? -ne 0 ]; then
    echo "❌ Metadata validation failed. Please fix metadata headers before committing."
    exit 1
fi

echo "✅ Metadata validation passed"
exit 0
"""
    
    def _get_post_commit_content(self) -> str:
        """Get post-commit hook content."""
        return """#!/bin/bash
# AI Agent Metadata Archive Hook

echo "Archiving metadata to audit log..."

# Archive metadata
python scripts/metadata_archiver.py --archive

echo "✅ Metadata archived"
exit 0
"""
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of git hooks installation."""
        pre_commit_exists = (self.git_hooks_dir / "pre-commit").exists()
        post_commit_exists = (self.git_hooks_dir / "post-commit").exists()
        
        return {
            "git_hooks_installed": pre_commit_exists and post_commit_exists,
            "pre_commit_hook": pre_commit_exists,
            "post_commit_hook": post_commit_exists,
            "hooks_directory": str(self.git_hooks_dir)
        }