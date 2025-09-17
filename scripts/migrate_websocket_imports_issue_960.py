#!/usr/bin/env python3
"""WebSocket Import Migration Script for Issue #960

This script implements the automated import path migration for Issue #960
WebSocket Manager SSOT fragmentation crisis remediation.

Business Value: Protects $500K+ ARR by systematically migrating 38 files
with dual imports to canonical SSOT patterns.

Usage:
    python scripts/migrate_websocket_imports_issue_960.py --phase1  # Compatibility layer
    python scripts/migrate_websocket_imports_issue_960.py --phase2  # Full migration
    python scripts/migrate_websocket_imports_issue_960.py --validate # Validation only
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import shutil
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class WebSocketImportMigrator:
    """Automated migration tool for WebSocket import SSOT consolidation."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backup_dir = project_root / "backups" / f"websocket_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.migration_stats = {
            'files_processed': 0,
            'imports_migrated': 0,
            'errors': [],
            'warnings': []
        }

        # Import migration patterns for SSOT consolidation
        self.import_patterns = {
            # Phase 1: Add deprecation warnings but keep compatibility
            'phase1': [
                # Legacy manager.py imports
                {
                    'pattern': r'from\s+netra_backend\.app\.websocket_core\.manager\s+import\s+([^\n]+)',
                    'replacement': 'from netra_backend.app.websocket_core.websocket_manager import \\1  # MIGRATED: Phase 1 SSOT',
                    'deprecation_warning': True
                },
                # Direct unified_manager imports (implementation detail)
                {
                    'pattern': r'from\s+netra_backend\.app\.websocket_core\.unified_manager\s+import\s+([^\n]+)',
                    'replacement': 'from netra_backend.app.websocket_core.websocket_manager import \\1  # MIGRATED: Phase 1 SSOT',
                    'deprecation_warning': True
                }
            ],
            # Phase 2: Full migration to canonical SSOT paths
            'phase2': [
                # Consolidate all WebSocket manager imports to canonical path
                {
                    'pattern': r'from\s+netra_backend\.app\.websocket_core\.manager\s+import\s+([^\n]+)',
                    'replacement': 'from netra_backend.app.websocket_core.websocket_manager import \\1',
                    'canonical': True
                },
                {
                    'pattern': r'from\s+netra_backend\.app\.websocket_core\.unified_manager\s+import\s+([^\n]+)',
                    'replacement': 'from netra_backend.app.websocket_core.websocket_manager import \\1',
                    'canonical': True
                },
                # Factory pattern consolidation
                {
                    'pattern': r'from\s+netra_backend\.app\.websocket_core\.websocket_manager_factory\s+import\s+([^\n]+)',
                    'replacement': 'from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager  # SSOT Factory',
                    'canonical': True
                },
                # Remove deprecated test imports
                {
                    'pattern': r'from\s+test_framework\.fixtures\.websocket_manager_mock\s+import\s+([^\n]+)',
                    'replacement': 'from test_framework.ssot.mock_factory import create_websocket_manager_mock',
                    'canonical': True
                }
            ]
        }

        # Files to exclude from migration (already SSOT compliant)
        self.exclude_patterns = [
            '*.backup*',
            '*.bak*',
            '__pycache__',
            '.git',
            'venv',
            'node_modules',
            # Keep SSOT source files unchanged
            'netra_backend/app/websocket_core/websocket_manager.py',
            'netra_backend/app/websocket_core/unified_manager.py',
            'netra_backend/app/websocket_core/types.py',
            'netra_backend/app/websocket_core/protocols.py'
        ]

    def create_backup(self) -> bool:
        """Create backup of current state before migration."""
        try:
            logger.info(f"Creating backup at: {self.backup_dir}")
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Backup key WebSocket files
            websocket_core = self.project_root / "netra_backend" / "app" / "websocket_core"
            if websocket_core.exists():
                backup_websocket = self.backup_dir / "websocket_core"
                shutil.copytree(websocket_core, backup_websocket)
                logger.info("✓ WebSocket core files backed up")

            # Backup test framework
            test_framework = self.project_root / "test_framework"
            if test_framework.exists():
                backup_test = self.backup_dir / "test_framework"
                shutil.copytree(test_framework, backup_test)
                logger.info("✓ Test framework files backed up")

            return True

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False

    def scan_for_dual_imports(self) -> List[Tuple[Path, List[str]]]:
        """Scan codebase for files with dual WebSocket manager imports."""
        logger.info("Scanning for dual WebSocket manager imports...")

        dual_import_files = []

        # Search patterns for dual imports
        search_patterns = [
            r'from\s+netra_backend\.app\.websocket_core\.manager\s+import',
            r'from\s+netra_backend\.app\.websocket_core\.unified_manager\s+import',
            r'from\s+netra_backend\.app\.websocket_core\.websocket_manager_factory\s+import',
            r'import.*websocket.*manager',
            r'WebSocketManager.*=',
        ]

        for python_file in self.project_root.rglob("*.py"):
            # Skip excluded files
            if self._should_exclude_file(python_file):
                continue

            try:
                content = python_file.read_text(encoding='utf-8')
                found_imports = []

                for pattern in search_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    if matches:
                        # Find the actual import lines
                        import_lines = re.findall(f'{pattern}[^\n]*', content, re.MULTILINE)
                        found_imports.extend(import_lines)

                if found_imports:
                    dual_import_files.append((python_file, found_imports))
                    logger.info(f"Found dual imports in: {python_file.relative_to(self.project_root)}")
                    for import_line in found_imports:
                        logger.info(f"  - {import_line.strip()}")

            except Exception as e:
                logger.warning(f"Could not read {python_file}: {e}")

        logger.info(f"Found {len(dual_import_files)} files with dual WebSocket imports")
        return dual_import_files

    def migrate_imports_phase1(self) -> bool:
        """Phase 1: Add compatibility layer and deprecation warnings."""
        logger.info("🚀 Starting Phase 1: SSOT compatibility layer migration")

        dual_import_files = self.scan_for_dual_imports()

        for file_path, imports in dual_import_files:
            try:
                self._migrate_file_phase1(file_path)
                self.migration_stats['files_processed'] += 1
            except Exception as e:
                error_msg = f"Phase 1 migration failed for {file_path}: {e}"
                logger.error(error_msg)
                self.migration_stats['errors'].append(error_msg)

        # Update websocket_manager.py with compatibility layer
        self._create_ssot_compatibility_layer()

        logger.info(f"✓ Phase 1 complete: {self.migration_stats['files_processed']} files processed")
        return len(self.migration_stats['errors']) == 0

    def migrate_imports_phase2(self) -> bool:
        """Phase 2: Full migration to canonical SSOT imports."""
        logger.info("🚀 Starting Phase 2: Full SSOT import migration")

        dual_import_files = self.scan_for_dual_imports()

        for file_path, imports in dual_import_files:
            try:
                self._migrate_file_phase2(file_path)
                self.migration_stats['files_processed'] += 1
            except Exception as e:
                error_msg = f"Phase 2 migration failed for {file_path}: {e}"
                logger.error(error_msg)
                self.migration_stats['errors'].append(error_msg)

        # Remove deprecated files
        self._cleanup_deprecated_files()

        logger.info(f"✓ Phase 2 complete: {self.migration_stats['files_processed']} files processed")
        return len(self.migration_stats['errors']) == 0

    def validate_migration(self) -> bool:
        """Validate migration results and SSOT compliance."""
        logger.info("🔍 Validating WebSocket SSOT migration...")

        validation_results = {
            'dual_imports_remaining': 0,
            'canonical_imports_found': 0,
            'deprecated_files_remaining': 0,
            'ssot_compliance_score': 0.0
        }

        # Check for remaining dual imports
        dual_imports = self.scan_for_dual_imports()
        validation_results['dual_imports_remaining'] = len(dual_imports)

        # Check for canonical imports
        canonical_pattern = r'from\s+netra_backend\.app\.websocket_core\.websocket_manager\s+import'
        canonical_count = 0

        for python_file in self.project_root.rglob("*.py"):
            if self._should_exclude_file(python_file):
                continue

            try:
                content = python_file.read_text(encoding='utf-8')
                matches = re.findall(canonical_pattern, content)
                canonical_count += len(matches)
            except Exception as e:
                logger.warning(f"Could not validate {python_file}: {e}")

        validation_results['canonical_imports_found'] = canonical_count

        # Check for deprecated files
        deprecated_files = [
            'netra_backend/app/websocket_core/manager.py',
            'netra_backend/app/websocket_core/websocket_manager_factory.py'
        ]

        for dep_file in deprecated_files:
            file_path = self.project_root / dep_file
            if file_path.exists():
                validation_results['deprecated_files_remaining'] += 1

        # Calculate SSOT compliance score
        total_imports = validation_results['dual_imports_remaining'] + validation_results['canonical_imports_found']
        if total_imports > 0:
            validation_results['ssot_compliance_score'] = (
                validation_results['canonical_imports_found'] / total_imports * 100
            )

        # Log validation results
        logger.info("📊 Validation Results:")
        logger.info(f"  Dual imports remaining: {validation_results['dual_imports_remaining']}")
        logger.info(f"  Canonical imports found: {validation_results['canonical_imports_found']}")
        logger.info(f"  Deprecated files remaining: {validation_results['deprecated_files_remaining']}")
        logger.info(f"  SSOT compliance score: {validation_results['ssot_compliance_score']:.1f}%")

        # Determine validation success
        success = (
            validation_results['dual_imports_remaining'] == 0 and
            validation_results['canonical_imports_found'] > 0 and
            validation_results['ssot_compliance_score'] >= 95.0
        )

        if success:
            logger.info("✅ Migration validation PASSED - SSOT consolidation successful")
        else:
            logger.error("❌ Migration validation FAILED - Manual review required")

        return success

    def _migrate_file_phase1(self, file_path: Path) -> None:
        """Migrate a single file for Phase 1 (compatibility)."""
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        for pattern_config in self.import_patterns['phase1']:
            pattern = pattern_config['pattern']
            replacement = pattern_config['replacement']

            # Apply replacement
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

            # Add deprecation warning if specified
            if pattern_config.get('deprecation_warning') and content != original_content:
                self._add_deprecation_warning(content, file_path)

        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            logger.info(f"✓ Phase 1 migrated: {file_path.relative_to(self.project_root)}")
            self.migration_stats['imports_migrated'] += 1

    def _migrate_file_phase2(self, file_path: Path) -> None:
        """Migrate a single file for Phase 2 (full SSOT)."""
        content = file_path.read_text(encoding='utf-8')
        original_content = content

        for pattern_config in self.import_patterns['phase2']:
            pattern = pattern_config['pattern']
            replacement = pattern_config['replacement']

            # Apply replacement
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            logger.info(f"✓ Phase 2 migrated: {file_path.relative_to(self.project_root)}")
            self.migration_stats['imports_migrated'] += 1

    def _create_ssot_compatibility_layer(self) -> None:
        """Create SSOT compatibility layer in websocket_manager.py."""
        websocket_manager_file = (
            self.project_root / "netra_backend" / "app" / "websocket_core" / "websocket_manager.py"
        )

        compatibility_layer = '''
# SSOT Compatibility Layer - Issue #960 Remediation
# This layer provides backward compatibility during WebSocket SSOT consolidation

import warnings
from netra_backend.app.websocket_core.websocket_manager import (
    _UnifiedWebSocketManagerImplementation as UnifiedWebSocketManager
)

# Create canonical SSOT alias
WebSocketManager = UnifiedWebSocketManager

def get_websocket_manager(user_context=None):
    """SSOT factory function for WebSocket manager instances.

    Business Value: Ensures user isolation and prevents cross-contamination.
    """
    return UnifiedWebSocketManager(user_context=user_context)

# Deprecation warning for non-canonical imports
def _deprecated_import_warning():
    warnings.warn(
        "DEPRECATED: Non-canonical WebSocket manager import detected. "
        "Use 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager' "
        "for SSOT compliance.",
        DeprecationWarning,
        stacklevel=3
    )

__all__ = ['WebSocketManager', 'get_websocket_manager']
'''

        try:
            current_content = websocket_manager_file.read_text(encoding='utf-8')
            if "SSOT Compatibility Layer" not in current_content:
                # Append compatibility layer
                with websocket_manager_file.open('a', encoding='utf-8') as f:
                    f.write(compatibility_layer)
                logger.info("✓ SSOT compatibility layer added to websocket_manager.py")
        except Exception as e:
            logger.error(f"Failed to create compatibility layer: {e}")

    def _cleanup_deprecated_files(self) -> None:
        """Remove deprecated files after Phase 2 migration."""
        deprecated_files = [
            'netra_backend/app/websocket_core/manager.py',
            'netra_backend/app/websocket_core/websocket_manager_factory.py.backup',
            'netra_backend/app/websocket_core/websocket_manager_factory.py.bak',
            'netra_backend/app/websocket_core/websocket_manager_factory.py.ssot_elimination_backup'
        ]

        for dep_file in deprecated_files:
            file_path = self.project_root / dep_file
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.info(f"✓ Removed deprecated file: {dep_file}")
                except Exception as e:
                    logger.warning(f"Could not remove {dep_file}: {e}")

    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from migration."""
        file_str = str(file_path.relative_to(self.project_root))

        for pattern in self.exclude_patterns:
            if pattern in file_str:
                return True

        return False

    def _add_deprecation_warning(self, content: str, file_path: Path) -> str:
        """Add deprecation warning to migrated file."""
        warning_comment = (
            "# MIGRATION WARNING: This file contains deprecated WebSocket imports that will be "
            "removed in Phase 3 of SSOT consolidation. Update to canonical imports.\n"
        )

        if warning_comment not in content:
            lines = content.split('\n')
            # Add warning after any existing header comments
            insert_index = 0
            for i, line in enumerate(lines):
                if not line.strip().startswith('#') and line.strip():
                    insert_index = i
                    break

            lines.insert(insert_index, warning_comment)
            return '\n'.join(lines)

        return content

    def print_migration_report(self) -> None:
        """Print comprehensive migration report."""
        logger.info("📊 WebSocket SSOT Migration Report:")
        logger.info(f"  Files processed: {self.migration_stats['files_processed']}")
        logger.info(f"  Imports migrated: {self.migration_stats['imports_migrated']}")
        logger.info(f"  Errors: {len(self.migration_stats['errors'])}")
        logger.info(f"  Warnings: {len(self.migration_stats['warnings'])}")

        if self.migration_stats['errors']:
            logger.error("❌ Migration Errors:")
            for error in self.migration_stats['errors']:
                logger.error(f"  - {error}")

        if self.migration_stats['warnings']:
            logger.warning("⚠️ Migration Warnings:")
            for warning in self.migration_stats['warnings']:
                logger.warning(f"  - {warning}")


def main():
    """Main entry point for WebSocket import migration."""
    parser = argparse.ArgumentParser(
        description="WebSocket Import Migration for Issue #960 SSOT Consolidation"
    )
    parser.add_argument(
        '--phase1', action='store_true',
        help='Run Phase 1: Create compatibility layer and add deprecation warnings'
    )
    parser.add_argument(
        '--phase2', action='store_true',
        help='Run Phase 2: Full migration to canonical SSOT imports'
    )
    parser.add_argument(
        '--validate', action='store_true',
        help='Validate migration results and SSOT compliance'
    )
    parser.add_argument(
        '--backup', action='store_true', default=True,
        help='Create backup before migration (default: True)'
    )

    args = parser.parse_args()

    if not any([args.phase1, args.phase2, args.validate]):
        logger.error("Must specify --phase1, --phase2, or --validate")
        return 1

    migrator = WebSocketImportMigrator(project_root)

    try:
        # Create backup if requested
        if args.backup and (args.phase1 or args.phase2):
            if not migrator.create_backup():
                logger.error("Backup creation failed - aborting migration")
                return 1

        success = True

        if args.phase1:
            success = migrator.migrate_imports_phase1()

        if args.phase2:
            success = migrator.migrate_imports_phase2()

        if args.validate:
            success = migrator.validate_migration()

        migrator.print_migration_report()

        if success:
            logger.info("✅ WebSocket SSOT migration completed successfully")
            return 0
        else:
            logger.error("❌ WebSocket SSOT migration failed - check errors above")
            return 1

    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())