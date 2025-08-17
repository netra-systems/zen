#!/usr/bin/env python3
"""
Git Hooks Manager - Handles git hook installation and management
Focused module for git hooks functionality
"""

import os
from pathlib import Path


class GitHooksManager:
    """Manages git hooks for metadata validation"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.git_hooks_dir = self._get_hooks_directory()

    def _get_hooks_directory(self) -> Path:
        """Get git hooks directory path"""
        return self.project_root / ".git" / "hooks"

    def _ensure_hooks_directory(self) -> None:
        """Ensure hooks directory exists"""
        self.git_hooks_dir.mkdir(parents=True, exist_ok=True)

    def _get_pre_commit_content(self) -> str:
        """Generate pre-commit hook content"""
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
        """Generate post-commit hook content"""
        return """#!/bin/bash
# AI Agent Metadata Archive Hook

echo "Archiving metadata to audit log..."

# Archive metadata
python scripts/metadata_archiver.py --archive

echo "✅ Metadata archived"
exit 0
"""

    def _create_hook_file(self, hook_name: str, content: str) -> bool:
        """Create hook file with content"""
        try:
            hook_path = self.git_hooks_dir / hook_name
            with open(hook_path, 'w') as f:
                f.write(content)
            self._make_executable(hook_path)
            return True
        except Exception:
            return False

    def _make_executable(self, file_path: Path) -> None:
        """Make file executable"""
        os.chmod(file_path, 0o755)

    def _install_pre_commit_hook(self) -> bool:
        """Install pre-commit hook"""
        content = self._get_pre_commit_content()
        return self._create_hook_file("pre-commit", content)

    def _install_post_commit_hook(self) -> bool:
        """Install post-commit hook"""
        content = self._get_post_commit_content()
        return self._create_hook_file("post-commit", content)

    def install_hooks(self) -> bool:
        """Install all git hooks for metadata validation"""
        try:
            self._ensure_hooks_directory()
            
            pre_commit_success = self._install_pre_commit_hook()
            post_commit_success = self._install_post_commit_hook()
            
            if pre_commit_success and post_commit_success:
                print("[SUCCESS] Git hooks installed successfully")
                return True
            else:
                print("[ERROR] Failed to install some git hooks")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to install git hooks: {e}")
            return False

    def hooks_exist(self) -> bool:
        """Check if hooks are properly installed"""
        pre_commit = self.git_hooks_dir / "pre-commit"
        post_commit = self.git_hooks_dir / "post-commit"
        
        if not (pre_commit.exists() and post_commit.exists()):
            return False
        
        return self._validate_hook_content(pre_commit)

    def _validate_hook_content(self, hook_path: Path) -> bool:
        """Validate hook contains expected content"""
        try:
            with open(hook_path, 'r') as f:
                content = f.read()
            return "metadata_validator" in content
        except Exception:
            return False