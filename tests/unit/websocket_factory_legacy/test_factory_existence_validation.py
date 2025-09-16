"""
Test suite to EXPOSE WebSocket Factory Legacy Detection - Issue #1098 Phase 2

This test suite is designed to FAIL initially, proving that the WebSocket factory
migration was never actually completed despite claims. These tests will expose
the false completion pattern identified in Issue #1098.

Expected Results:
- ALL tests should FAIL initially
- Proves factory files still exist (1,001+ lines)
- Demonstrates false completion claims
- Provides concrete evidence for Issue #1098

Test Strategy: FAIL FIRST to prove false completion, then guide real remediation.
"""

import os
import unittest
from pathlib import Path


class TestWebSocketFactoryExistenceValidation(unittest.TestCase):
    """
    Tests to validate that WebSocket factory files have been completely removed.

    CRITICAL: These tests are DESIGNED TO FAIL initially to expose false completion.
    Once they fail, they provide the roadmap for actual remediation.
    """

    def setUp(self):
        """Set up test environment with project root path."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.factory_files_that_should_be_deleted = [
            "netra_backend/app/websocket_core/websocket_manager_factory.py",
            "netra_backend/app/factories/websocket_bridge_factory.py",
            "netra_backend/app/services/websocket_bridge_factory.py",
            "netra_backend/app/routes/websocket_factory.py",
            "netra_backend/app/websocket_core/websocket_manager_factory_compat.py"
        ]
        self.backup_files_that_should_be_cleaned = [
            "netra_backend/app/factories/websocket_bridge_factory.py.backup.issue1104",
            "netra_backend/app/services/websocket_bridge_factory.py.backup_await_fix",
            "netra_backend/app/websocket_core/websocket_manager_factory.py.ssot_elimination_backup"
        ]

    def test_main_factory_file_should_be_deleted(self):
        """
        Test that the main WebSocket manager factory file has been removed.

        EXPECTED: FAIL - File exists with 1,001+ lines
        EVIDENCE: Proves Issue #1098 false completion claim
        """
        main_factory_path = self.project_root / "netra_backend/app/websocket_core/websocket_manager_factory.py"

        # This SHOULD pass (file should not exist) but will FAIL because file exists
        self.assertFalse(
            main_factory_path.exists(),
            f"CRITICAL VIOLATION: Main factory file still exists at {main_factory_path}. "
            f"This proves the WebSocket factory migration was never completed. "
            f"Expected: File deleted. Actual: File exists. "
            f"Issue #1098 false completion confirmed."
        )

    def test_factory_file_sizes_prove_no_deletion(self):
        """
        Test that factory files don't exist by checking their sizes.

        EXPECTED: FAIL - Files exist with substantial line counts
        EVIDENCE: Proves substantial factory code still present
        """
        for factory_file in self.factory_files_that_should_be_deleted:
            factory_path = self.project_root / factory_file

            if factory_path.exists():
                # Count lines to prove substantial content still exists
                with open(factory_path, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for line in f)

                # This assertion will FAIL for existing files, proving false completion
                self.fail(
                    f"CRITICAL VIOLATION: Factory file {factory_file} still exists "
                    f"with {line_count} lines. This proves Issue #1098 false completion. "
                    f"Expected: File deleted. Actual: {line_count} lines of factory code."
                )

    def test_all_factory_files_removed_comprehensive(self):
        """
        Comprehensive test that ALL factory files have been removed.

        EXPECTED: FAIL - Multiple factory files still exist
        EVIDENCE: Complete inventory of remaining factory violations
        """
        existing_factory_files = []

        for factory_file in self.factory_files_that_should_be_deleted:
            factory_path = self.project_root / factory_file
            if factory_path.exists():
                with open(factory_path, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for line in f)
                existing_factory_files.append(f"{factory_file} ({line_count} lines)")

        # This assertion will FAIL, providing complete evidence
        self.assertEqual(
            len(existing_factory_files), 0,
            f"CRITICAL VIOLATION: {len(existing_factory_files)} factory files still exist. "
            f"This proves Issue #1098 false completion. Files: {existing_factory_files}. "
            f"Expected: 0 factory files. Actual: {len(existing_factory_files)} files."
        )

    def test_backup_files_cleaned_up(self):
        """
        Test that factory backup files have been properly cleaned up.

        EXPECTED: FAIL - Backup files still exist
        EVIDENCE: Proves incomplete cleanup process
        """
        existing_backup_files = []

        for backup_file in self.backup_files_that_should_be_cleaned:
            backup_path = self.project_root / backup_file
            if backup_path.exists():
                existing_backup_files.append(backup_file)

        # This assertion will FAIL, proving incomplete cleanup
        self.assertEqual(
            len(existing_backup_files), 0,
            f"CLEANUP VIOLATION: {len(existing_backup_files)} backup files still exist. "
            f"Files: {existing_backup_files}. This indicates incomplete migration cleanup. "
            f"Expected: All backups cleaned. Actual: {len(existing_backup_files)} backups remain."
        )

    def test_factory_class_definitions_removed(self):
        """
        Test that factory class definitions have been removed from codebase.

        EXPECTED: FAIL - Factory classes still defined
        EVIDENCE: Proves factory patterns still implemented
        """
        factory_classes_found = []

        # Check main factory file for class definitions
        main_factory_path = self.project_root / "netra_backend/app/websocket_core/websocket_manager_factory.py"

        if main_factory_path.exists():
            with open(main_factory_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if "class WebSocketManagerFactory" in content:
                    factory_classes_found.append("WebSocketManagerFactory in websocket_manager_factory.py")
                if "class WebSocketBridgeFactory" in content:
                    factory_classes_found.append("WebSocketBridgeFactory in websocket_manager_factory.py")

        # This assertion will FAIL, proving factory classes still exist
        self.assertEqual(
            len(factory_classes_found), 0,
            f"CLASS DEFINITION VIOLATION: {len(factory_classes_found)} factory classes still defined. "
            f"Classes: {factory_classes_found}. This proves factory patterns not removed. "
            f"Expected: 0 factory classes. Actual: {len(factory_classes_found)} classes."
        )

    def test_cached_python_files_cleaned(self):
        """
        Test that Python cache files for factories have been cleaned.

        EXPECTED: FAIL - Cache files still exist
        EVIDENCE: Proves factory modules still cached in system
        """
        cache_files_found = []

        # Look for __pycache__ files related to factories
        for root, dirs, files in os.walk(self.project_root):
            if "__pycache__" in root:
                for file in files:
                    if "websocket" in file and "factory" in file and file.endswith(".pyc"):
                        cache_files_found.append(os.path.join(root, file))

        # This assertion will FAIL, proving cached factory files exist
        self.assertEqual(
            len(cache_files_found), 0,
            f"CACHE VIOLATION: {len(cache_files_found)} cached factory files still exist. "
            f"Files: {cache_files_found}. This proves factory modules still cached. "
            f"Expected: 0 cache files. Actual: {len(cache_files_found)} cached files."
        )


if __name__ == "__main__":
    print("=" * 80)
    print("WEBSOCKET FACTORY EXISTENCE VALIDATION TESTS - ISSUE #1098 PHASE 2")
    print("=" * 80)
    print("CRITICAL: These tests are DESIGNED TO FAIL initially")
    print("PURPOSE: Expose false completion claims in WebSocket factory migration")
    print("EXPECTED: ALL tests should FAIL, proving factory files still exist")
    print("=" * 80)

    unittest.main(verbosity=2)