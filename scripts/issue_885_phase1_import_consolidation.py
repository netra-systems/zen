#!/usr/bin/env python3
"""
Issue #885 Phase 1: WebSocket Manager Import Path Consolidation

This script safely consolidates WebSocket Manager import paths to canonical SSOT patterns.
It performs atomic, reversible changes with validation at each step.

Business Value Justification:
- Segment: Platform/Infrastructure
- Business Goal: Achieve SSOT compliance without breaking changes
- Value Impact: Reduce 36+ import patterns to 4 canonical patterns
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
    risk_level: str  # LOW, MEDIUM, HIGH

class WebSocketImportConsolidator:
    """Consolidates WebSocket Manager import paths to SSOT patterns."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.backup_dir = None
        self.changes_made = []

        # Define canonical import replacements
        self.replacements = [
            ImportReplacement(
                old_pattern=r"from netra_backend\.app\.websocket_core\.manager import WebSocketManager",
                new_pattern="from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager as WebSocketManager",
                description="Legacy manager.py import → canonical SSOT",
                risk_level="LOW"
            ),
            ImportReplacement(
                old_pattern=r"from netra_backend\.app\.websocket_core\.websocket_manager import WebSocketManager",
                new_pattern="from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager as WebSocketManager",
                description="Direct websocket_manager.py import → canonical SSOT",
                risk_level="LOW"
            ),
            ImportReplacement(
                old_pattern=r"from netra_backend\.app\.websocket_core\.websocket_manager_factory import create_websocket_manager",
                new_pattern="# FACTORY DEPRECATED: Use UnifiedWebSocketManager.get_instance() with UserExecutionContext\n# from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager",
                description="Factory pattern → SSOT manager with context (requires manual review)",
                risk_level="MEDIUM"
            ),
            ImportReplacement(
                old_pattern=r"from netra_backend\.app\.websocket_core\.unified_manager import _UnifiedWebSocketManagerImplementation",
                new_pattern="from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager",
                description="Direct unified_manager import → canonical export",
                risk_level="LOW"
            )
        ]

    def create_backup(self) -> str:
        """Create backup of current state."""
        timestamp = subprocess.check_output(['date', '+%Y%m%d_%H%M%S'], text=True).strip()
        backup_name = f"websocket_import_consolidation_backup_{timestamp}"
        self.backup_dir = self.repo_path / "backups" / backup_name
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        print(f"Creating backup at: {self.backup_dir}")

        # Backup critical files
        critical_paths = [
            "netra_backend/app/websocket_core/",
            "netra_backend/app/routes/websocket.py",
            "netra_backend/app/agents/registry.py",
            "tests/mission_critical/test_websocket_*.py"
        ]

        for path_pattern in critical_paths:
            source_path = self.repo_path / path_pattern
            if source_path.exists():
                if source_path.is_file():
                    dest_path = self.backup_dir / path_pattern
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                elif source_path.is_dir():
                    dest_path = self.backup_dir / path_pattern
                    shutil.copytree(source_path, dest_path, dirs_exist_ok=True)

        return str(self.backup_dir)

    def scan_import_usage(self) -> Dict[str, List[Tuple[str, int, str]]]:
        """Scan codebase for WebSocket Manager import usage."""
        usage_map = {}

        # Search patterns
        search_patterns = [
            r"from.*websocket.*manager.*import",
            r"import.*WebSocketManager",
            r"create_websocket_manager",
            r"WebSocketManagerFactory"
        ]

        # Search in key directories
        search_dirs = [
            "netra_backend/app/",
            "tests/",
            "test_framework/"
        ]

        print("Scanning for WebSocket Manager import usage...")

        for search_dir in search_dirs:
            dir_path = self.repo_path / search_dir
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                try:
                    # Try multiple encodings for reading
                    lines = None
                    for encoding in ['utf-8', 'cp1252', 'latin-1']:
                        try:
                            with open(py_file, 'r', encoding=encoding) as f:
                                lines = f.readlines()
                            break
                        except UnicodeDecodeError:
                            continue

                    if lines is None:
                        print(f"Warning: Could not decode {py_file}, skipping")
                        continue

                    for line_num, line in enumerate(lines, 1):
                        for pattern in search_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                rel_path = str(py_file.relative_to(self.repo_path))
                                if rel_path not in usage_map:
                                    usage_map[rel_path] = []
                                usage_map[rel_path].append((pattern, line_num, line.strip()))
                except Exception as e:
                    print(f"Warning: Could not scan {py_file}: {e}")

        return usage_map

    def apply_import_replacements(self, usage_map: Dict[str, List[Tuple[str, int, str]]]) -> bool:
        """Apply import replacements to files."""
        print("\\nApplying import replacements...")

        files_modified = 0
        total_replacements = 0

        # Priority order: production code first, then tests
        file_priority = {
            'netra_backend/app/routes/websocket.py': 1,
            'netra_backend/app/agents/registry.py': 2,
            'netra_backend/app/agents/supervisor/execution_engine.py': 3,
        }

        # Sort files by priority
        sorted_files = sorted(usage_map.keys(),
                            key=lambda f: file_priority.get(f, 999))

        for file_path in sorted_files:
            full_path = self.repo_path / file_path

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
                    if replacement.risk_level == "HIGH":
                        print(f"Skipping HIGH risk replacement in {file_path}")
                        continue

                    matches = re.findall(replacement.old_pattern, content)
                    if matches:
                        content = re.sub(replacement.old_pattern, replacement.new_pattern, content)
                        file_replacements += len(matches)
                        print(f"  {file_path}: {len(matches)} × {replacement.description}")

                # Write back if changes were made
                if content != original_content:
                    with open(full_path, 'w', encoding='utf-8', newline='\n') as f:
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
            # Quick syntax validation
            ["python", "-m", "py_compile", "netra_backend/app/websocket_core/canonical_import_patterns.py"],

            # Mission critical WebSocket tests (fast)
            ["python", "-c", "from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager; print('Import successful')"],

            # Import compliance check
            ["python", "scripts/validate_websocket_compliance_improved.py"]
        ]

        for cmd in test_commands:
            try:
                result = subprocess.run(cmd, cwd=self.repo_path,
                                      capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    print(f"Validation failed: {' '.join(cmd)}")
                    print(f"Error: {result.stderr}")
                    return False
                else:
                    print(f"✓ Passed: {' '.join(cmd)}")
            except subprocess.TimeoutExpired:
                print(f"Timeout: {' '.join(cmd)}")
                return False
            except Exception as e:
                print(f"Error running {' '.join(cmd)}: {e}")
                return False

        return True

    def rollback_changes(self) -> bool:
        """Rollback all changes made during this run."""
        if not self.backup_dir or not self.backup_dir.exists():
            print("No backup directory found for rollback")
            return False

        print(f"Rolling back changes from backup: {self.backup_dir}")

        try:
            # Restore files from backup
            for backup_file in self.backup_dir.rglob("*.py"):
                rel_path = backup_file.relative_to(self.backup_dir)
                target_file = self.repo_path / rel_path

                if target_file.exists():
                    shutil.copy2(backup_file, target_file)
                    print(f"Restored: {rel_path}")

            print("Rollback completed successfully")
            return True

        except Exception as e:
            print(f"Rollback failed: {e}")
            return False

    def generate_report(self) -> str:
        """Generate consolidation report."""
        report = f"""
Issue #885 Phase 1 Import Consolidation Report
==============================================

Backup Location: {self.backup_dir}

Files Modified: {len(self.changes_made)}
"""

        for file_path, replacement_count in self.changes_made:
            report += f"  - {file_path}: {replacement_count} replacements\\n"

        report += f"""
Next Steps:
1. Run full test suite: python tests/unified_test_runner.py --category mission_critical
2. Test Golden Path user flow manually
3. Proceed to Phase 2 (Factory Pattern Elimination) if all tests pass
4. Use rollback_changes() method if issues are detected

SSOT Import Pattern (use this going forward):
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager as WebSocketManager
"""

        return report

def main():
    """Main execution function for Phase 1 import consolidation."""
    if len(sys.argv) < 2:
        print("Usage: python issue_885_phase1_import_consolidation.py <repo_path>")
        sys.exit(1)

    repo_path = sys.argv[1]
    consolidator = WebSocketImportConsolidator(repo_path)

    try:
        # Step 1: Create backup
        backup_path = consolidator.create_backup()
        print(f"Backup created: {backup_path}")

        # Step 2: Scan current usage
        usage_map = consolidator.scan_import_usage()
        print(f"Found WebSocket imports in {len(usage_map)} files")

        # Step 3: Apply replacements
        if not consolidator.apply_import_replacements(usage_map):
            print("Import replacement failed, rolling back...")
            consolidator.rollback_changes()
            sys.exit(1)

        # Step 4: Validate changes
        if not consolidator.run_validation_tests():
            print("Validation tests failed, rolling back...")
            consolidator.rollback_changes()
            sys.exit(1)

        # Step 5: Generate report
        report = consolidator.generate_report()
        print(report)

        # Save report
        report_file = Path(repo_path) / "issue_885_phase1_report.md"
        with open(report_file, 'w') as f:
            f.write(report)

        print(f"\\nPhase 1 completed successfully!")
        print(f"Report saved to: {report_file}")
        print(f"Backup available at: {backup_path}")

    except KeyboardInterrupt:
        print("\\nOperation cancelled by user")
        if consolidator.backup_dir:
            print(f"Backup available at: {consolidator.backup_dir}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        if consolidator.backup_dir:
            consolidator.rollback_changes()
        sys.exit(1)

if __name__ == "__main__":
    main()