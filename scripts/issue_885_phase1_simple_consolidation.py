#!/usr/bin/env python3
"""
Issue #885 Phase 1: Simple WebSocket Manager Import Path Consolidation

This script safely consolidates WebSocket Manager import paths in key files only.
It focuses on high-impact, low-risk changes to improve SSOT compliance.

Business Value Justification:
- Segment: Platform/Infrastructure
- Business Goal: Achieve SSOT compliance without breaking changes
- Value Impact: Reduce critical import path violations
- Revenue Impact: Protect $500K+ ARR by maintaining Golden Path stability
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Set
import tempfile
import shutil
from dataclasses import dataclass

@dataclass
class ImportReplacement:
    """Represents a single import path replacement."""
    old_pattern: str
    new_pattern: str
    description: str
    files_affected: List[str]

class SimpleWebSocketImportConsolidator:
    """Consolidates WebSocket Manager import paths in key files."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.backup_dir = None
        self.changes_made = []

        # Define targeted import replacements for key files only
        self.replacements = [
            ImportReplacement(
                old_pattern=r"from netra_backend\.app\.websocket_core\.manager import (\w+)",
                new_pattern=r"from netra_backend.app.websocket_core.canonical_import_patterns import \1",
                description="Legacy manager.py import → canonical SSOT",
                files_affected=[
                    "netra_backend/app/agents/registry.py",
                    "netra_backend/app/agents/supervisor/execution_engine.py"
                ]
            ),
            ImportReplacement(
                old_pattern=r"from netra_backend\.app\.websocket_core\.websocket_manager import (\w+)",
                new_pattern=r"from netra_backend.app.websocket_core.canonical_import_patterns import \1",
                description="Direct websocket_manager.py import → canonical SSOT",
                files_affected=[
                    "netra_backend/app/agents/registry.py"
                ]
            ),
            ImportReplacement(
                old_pattern=r"from netra_backend\.app\.websocket_core import WebSocketManager",
                new_pattern=r"from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager as WebSocketManager",
                description="Package-level import → canonical SSOT",
                files_affected=[
                    "netra_backend/app/tools/enhanced_dispatcher.py"
                ]
            )
        ]

    def create_backup(self) -> str:
        """Create backup of critical files before making changes."""
        timestamp = subprocess.check_output(['powershell', 'Get-Date -Format "yyyyMMdd_HHmmss"'],
                                          text=True).strip()
        self.backup_dir = self.repo_path / "backups" / f"websocket_import_simple_backup_{timestamp}"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        print(f"Creating backup at: {self.backup_dir}")

        # Backup only specific key files
        target_files = [
            "netra_backend/app/agents/registry.py",
            "netra_backend/app/agents/supervisor/execution_engine.py",
            "netra_backend/app/tools/enhanced_dispatcher.py",
            "netra_backend/app/websocket_core/canonical_import_patterns.py"
        ]

        for file_path in target_files:
            source_path = self.repo_path / file_path
            if source_path.exists():
                dest_path = self.backup_dir / file_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, dest_path)

        print(f"Backup created: {self.backup_dir}")
        return str(self.backup_dir)

    def apply_import_replacements(self) -> bool:
        """Apply import replacements to specific key files."""
        print("\\nApplying import replacements...")

        files_modified = 0
        total_replacements = 0

        # Target specific files only
        target_files = [
            "netra_backend/app/agents/registry.py",
            "netra_backend/app/agents/supervisor/execution_engine.py",
            "netra_backend/app/tools/enhanced_dispatcher.py"
        ]

        for file_path in target_files:
            full_path = self.repo_path / file_path

            if not full_path.exists():
                print(f"File not found: {file_path}, skipping")
                continue

            try:
                # Read current content with multiple encoding attempts
                content = None
                encoding_used = None

                for encoding in ['utf-8', 'cp1252', 'latin-1']:
                    try:
                        with open(full_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        encoding_used = encoding
                        break
                    except UnicodeDecodeError:
                        continue

                if content is None:
                    print(f"ERROR: Could not decode {file_path} with any encoding")
                    return False

                original_content = content
                file_replacements = 0

                # Apply each replacement pattern
                for replacement in self.replacements:
                    if file_path in replacement.files_affected:
                        matches = re.findall(replacement.old_pattern, content)
                        if matches:
                            content = re.sub(replacement.old_pattern, replacement.new_pattern, content)
                            file_replacements += len(matches)
                            print(f"  {file_path}: {len(matches)} × {replacement.description}")

                # Write back if changes were made
                if content != original_content:
                    with open(full_path, 'w', encoding='utf-8', newline='\\n') as f:
                        f.write(content)

                    files_modified += 1
                    total_replacements += file_replacements
                    self.changes_made.append((file_path, file_replacements))

                    # Validate Python syntax
                    if not self.validate_python_syntax(full_path):
                        print(f"ERROR: Syntax error in {file_path} after replacement!")
                        return False

            except Exception as e:
                print(f"ERROR: Failed to process {file_path}: {e}")
                return False

        print(f"\\nCompleted: {files_modified} files modified, {total_replacements} total replacements")
        return True

    def validate_python_syntax(self, file_path: Path) -> bool:
        """Validate Python syntax of modified file."""
        try:
            # Try multiple encodings for reading
            source = None
            for encoding in ['utf-8', 'cp1252', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        source = f.read()
                    break
                except UnicodeDecodeError:
                    continue

            if source is None:
                print(f"ERROR: Could not decode {file_path} for syntax validation")
                return False

            compile(source, str(file_path), 'exec')
            return True
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return False

    def run_validation_tests(self) -> bool:
        """Run validation tests to ensure changes don't break functionality."""
        print("\\nRunning validation tests...")

        test_commands = [
            # Basic import test
            [sys.executable, "-c", "from netra_backend.app.agents.registry import AgentRegistry; print('Registry import: OK')"],
            # Syntax validation for key files
            [sys.executable, "-m", "py_compile", str(self.repo_path / "netra_backend/app/agents/registry.py")]
        ]

        for cmd in test_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True,
                                      cwd=self.repo_path, timeout=30)
                if result.returncode != 0:
                    print(f"FAILED: {' '.join(cmd)}")
                    print(f"Error: {result.stderr}")
                    return False
                else:
                    print(f"PASSED: {' '.join(cmd)}")
            except subprocess.TimeoutExpired:
                print(f"TIMEOUT: {' '.join(cmd)}")
                return False
            except Exception as e:
                print(f"ERROR running {' '.join(cmd)}: {e}")
                return False

        return True

    def rollback_changes(self, backup_path: str) -> bool:
        """Rollback changes from backup."""
        print(f"Rolling back changes from backup: {backup_path}")
        backup_dir = Path(backup_path)

        if not backup_dir.exists():
            print(f"Backup directory not found: {backup_path}")
            return False

        try:
            for backup_file in backup_dir.rglob("*.py"):
                relative_path = backup_file.relative_to(backup_dir)
                target_file = self.repo_path / relative_path

                if target_file.exists():
                    shutil.copy2(backup_file, target_file)
                    print(f"Restored: {relative_path}")

            print("Rollback completed successfully")
            return True
        except Exception as e:
            print(f"Rollback failed: {e}")
            return False

def main():
    """Main execution function."""
    if len(sys.argv) != 2:
        print("Usage: python issue_885_phase1_simple_consolidation.py <repo_path>")
        sys.exit(1)

    repo_path = sys.argv[1]
    consolidator = SimpleWebSocketImportConsolidator(repo_path)

    try:
        # Phase 1: Create backup
        backup_path = consolidator.create_backup()

        # Phase 2: Apply import replacements
        if not consolidator.apply_import_replacements():
            print("Import replacement failed, rolling back...")
            consolidator.rollback_changes(backup_path)
            sys.exit(1)

        # Phase 3: Validate changes
        if not consolidator.run_validation_tests():
            print("Validation failed, rolling back...")
            consolidator.rollback_changes(backup_path)
            sys.exit(1)

        # Phase 4: Report success
        print("\\nSUCCESS: Phase 1 Import Consolidation completed successfully!")
        print(f"Files modified: {len(consolidator.changes_made)}")
        for file_path, count in consolidator.changes_made:
            print(f"  - {file_path}: {count} replacements")

        print(f"\\nBackup available at: {backup_path}")
        print("\\nNext steps:")
        print("1. Run SSOT compliance tests to measure improvement")
        print("2. Commit changes in atomic batches")
        print("3. Proceed to Phase 2 (Factory Pattern Consolidation)")

    except KeyboardInterrupt:
        print("\\nOperation cancelled by user")
        if consolidator.backup_dir:
            consolidator.rollback_changes(str(consolidator.backup_dir))
        sys.exit(1)
    except Exception as e:
        print(f"\\nUnexpected error: {e}")
        if consolidator.backup_dir:
            consolidator.rollback_changes(str(consolidator.backup_dir))
        sys.exit(1)

if __name__ == "__main__":
    main()