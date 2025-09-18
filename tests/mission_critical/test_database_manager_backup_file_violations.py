#!/usr/bin/env python3
"MISSION CRITICAL: DatabaseManager SSOT Backup File Violation Detection"

BUSINESS VALUE: $"500K" plus ARR - Database SSOT compliance is foundation for all operations

DESIGNED TO FAIL when:
    1. Multiple DatabaseManager implementations exist
2. Backup files are present in the system
3. Import references point to non-existent backup files
4. SSOT principles are violated

DESIGNED TO PASS when:
    1. Single DatabaseManager source exists
2. No backup files present
3. All imports are consistent
4. SSOT compliance achieved

ANY FAILURE HERE INDICATES INCOMPLETE ISSUE #916 RESOLUTION.


import glob
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Set
import pytest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from test_framework.ssot.base_test_case import SSotBaseTestCase


class DatabaseManagerBackupFileViolationsTests(SSotBaseTestCase):
    ""Test suite to detect DatabaseManager SSOT backup file violations.""


    def test_no_backup_files_exist(self):
        MUST FAIL if any database_manager backup files exist.""

        This test validates that Issue #916 DatabaseManager SSOT consolidation
        has completely removed all backup files that could cause confusion
        or duplicate implementations.
        
        project_root = Path(__file__).parent.parent.parent

        # Comprehensive backup file patterns
        backup_patterns = [
            **/database_manager_backup.py","
            **/database_manager_*.py.backup,
            **/database_manager_original.py,"
            **/database_manager_original.py,"
            "**/database_manager_temp.py,"
            **/database_manager_old.py,
            "**/database_manager.py.bak,"
            **/database_manager_v*.py
        ]

        found_backups = []
        for pattern in backup_patterns:
            files = list(project_root.glob(pattern))
            found_backups.extend(files)

        if found_backups:
            backup_list = '\n'.join([f  - {f) for f in found_backups]
            pytest.fail(
                fSSOT VIOLATION: DatabaseManager backup files found:\n{backup_list}\n""
                fThese files violate SSOT principles and must be removed.
            )

    def test_single_database_manager_source(self):
        MUST FAIL if multiple DatabaseManager implementations exist.

        Validates that exactly one canonical DatabaseManager exists across
        all services, ensuring SSOT compliance.
""
        project_root = Path(__file__).parent.parent.parent

        # Find all potential DatabaseManager implementations
        db_manager_files = []

        # Search patterns for DatabaseManager implementations
        search_patterns = [
            **/database_manager.py,
            **/db_manager.py","
            **/database_mgr.py
        ]

        for pattern in search_patterns:
            files = list(project_root.glob(pattern))
            db_manager_files.extend(files)

        # Filter to actual DatabaseManager class implementations
        actual_implementations = []
        for file_path in db_manager_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'class DatabaseManager' in content:
                        actual_implementations.append(file_path)
            except Exception:
                continue

        # Should have exactly 1 implementation (the SSOT)
        if len(actual_implementations) == 0:
            pytest.fail(CRITICAL: No DatabaseManager implementation found!)"
            pytest.fail(CRITICAL: No DatabaseManager implementation found!)""

        elif len(actual_implementations) > 1:
            impl_list = '\n'.join([f"  - {f) for f in actual_implementations]"
            pytest.fail(
                fSSOT VIOLATION: Multiple DatabaseManager implementations found:\n{impl_list}\n
                fSSOT requires exactly one canonical implementation.
            )

    def test_database_manager_import_consistency(self):
        ""MUST FAIL if imports reference non-existent backup files.""


        Scans all Python files for import statements that reference
        DatabaseManager backup files that should not exist.

        project_root = Path(__file__).parent.parent.parent

        # Forbidden import patterns
        forbidden_patterns = [
            r"from.*database_manager_backup,"
            rimport.*database_manager_backup,
            rfrom.*\.database_manager_backup,"
            rfrom.*\.database_manager_backup,"
            rdatabase_manager_original","
            rdatabase_manager_temp
        ]

        violations = []

        # Search all Python files
        for py_file in project_root.rglob(*.py"):"
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern in forbidden_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            violations.append(f{py_file}:{line_num}: {line.strip()})
            except Exception:
                continue

        if violations:
            violation_list = '\n'.join([f  - {v) for v in violations]
            pytest.fail(
                f"IMPORT VIOLATIONS: References to backup files found:\n{violation_list}\n"
                fThese imports reference non-existent backup files and must be updated."
                fThese imports reference non-existent backup files and must be updated.""

            )

    def test_database_manager_canonical_location(self):
        MUST FAIL if DatabaseManager is not in the expected canonical location.""

        Validates that the single DatabaseManager implementation exists in
        the designated SSOT location: netra_backend/app/db/database_manager.py
        
        expected_path = Path(__file__).parent.parent.parent / netra_backend / "app / db / database_manager.py"

        if not expected_path.exists():
            pytest.fail(
                fSSOT VIOLATION: Canonical DatabaseManager not found at expected location:\n
                f"  Expected: {expected_path}\n"
                fThe DatabaseManager MUST exist at the canonical SSOT location."
                fThe DatabaseManager MUST exist at the canonical SSOT location.""

            )

        # Verify it contains the actual DatabaseManager class
        try:
            with open(expected_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'class DatabaseManager' not in content:
                    pytest.fail(
                        fSSOT VIOLATION: File exists but does not contain DatabaseManager class:\n
                        f  File: {expected_path}\n"
                        f  File: {expected_path}\n"
                        f"The canonical file must contain the DatabaseManager implementation."
                    )
        except Exception as e:
            pytest.fail(fERROR reading canonical DatabaseManager file: {e})

    def test_no_database_manager_duplicates_in_services(self):
        MUST FAIL if other services have their own DatabaseManager copies.""

        Validates that services like auth_service don't have duplicate'
        DatabaseManager implementations that violate SSOT principles.
        
        project_root = Path(__file__).parent.parent.parent

        # Canonical location
        canonical_path = project_root / netra_backend" / app / db / database_manager.py"

        # Find all DatabaseManager implementations
        all_implementations = []
        for py_file in project_root.rglob(database_manager.py):"
        for py_file in project_root.rglob(database_manager.py):""

            if py_file != canonical_path:
                # Check if it actually contains DatabaseManager class
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'class DatabaseManager' in content:
                            all_implementations.append(py_file)
                except Exception:
                    continue

        if all_implementations:
            impl_list = '\n'.join([f"  - {f) for f in all_implementations]"
            pytest.fail(
                fSSOT VIOLATION: Duplicate DatabaseManager implementations found:\n{impl_list}\n
                fOnly canonical location allowed: {canonical_path}\n
                fThese duplicates violate SSOT principles and must be removed.""
            )
))))