"""
P0 MISSION CRITICAL: Database Manager SSOT Compliance Test

Business Impact: Prevents data integrity issues and transaction failures affecting $500K+ ARR.
Database Manager SSOT violations can cause:
- Data corruption from competing database connections
- Transaction isolation failures leading to data inconsistency
- Connection pool exhaustion causing service outages
- Database configuration inconsistencies across environments
- Silent data loss from uncoordinated transactions
- Complete service failures from database connection chaos

This test ensures ONLY the canonical database manager handles ALL database operations
and prevents the critical data integrity issues that could corrupt user data.

SSOT Requirements:
- DatabaseManager at /netra_backend/app/db/database_manager.py is the ONLY database manager
- ALL database access must use canonical DatabaseManager methods
- NO direct SQLAlchemy engine/connection creation outside the manager
- ALL database URLs must be constructed through DatabaseURLBuilder SSOT
- NO bypassing of canonical database connection patterns
"""

import ast
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)


@pytest.mark.mission_critical
@pytest.mark.ssot
@pytest.mark.database_ssot
class TestDatabaseManagerSSot(SSotBaseTestCase):
    """CRITICAL: Database Manager SSOT compliance testing.
    
    Business Impact: Prevents data integrity issues and transaction failures.
    Violations in Database Manager SSOT can cause:
    - Data corruption from competing database connections
    - Transaction isolation failures leading to data inconsistency
    - Connection pool exhaustion causing service outages
    - Database configuration inconsistencies across environments
    - Silent data loss from uncoordinated transactions
    """
    
    def setup_method(self, method=None):
        """Set up test with database patterns to detect."""
        super().setup_method(method)
        
        # Define the canonical database manager path
        self.canonical_database_manager_path = "netra_backend/app/db/database_manager.py"
        
        # Define allowed database integration paths
        self.allowed_database_integration_paths = {
            "netra_backend/app/db/database_manager.py",  # Canonical manager
            "shared/database_url_builder.py",  # URL construction SSOT
            "netra_backend/app/core/config.py",  # Configuration interface
            "netra_backend/app/core/configuration/database.py",  # Database config
        }
        
        # Forbidden direct database connection patterns
        self.forbidden_direct_connection_patterns = [
            r'create_engine\s*\(',
            r'create_async_engine\s*\(',
            r'psycopg2\.connect\s*\(',
            r'asyncpg\.connect\s*\(',
            r'psycopg\.connect\s*\(',
            r'psycopg2\.pool\.',
            r'asyncpg\.create_pool\s*\(',
            r'sqlalchemy\.create_engine',
            r'Engine\s*=\s*create_engine',
            r'engine\s*=\s*create_engine',
            r'async_engine\s*=\s*create_async_engine',
        ]
        
        # Forbidden duplicate database manager patterns (FIXED to handle both : and ( endings)
        self.forbidden_duplicate_manager_patterns = [
            r'class\s+DatabaseManager\s*[:\(]',
            r'class\s+.*DatabaseManager.*[:\(]',
            r'class\s+.*DBManager.*[:\(]', 
            r'class\s+.*DbManager.*[:\(]',
            r'class\s+.*DatabaseConnection.*Manager.*[:\(]',
            r'class\s+.*ConnectionManager.*[:\(]',
            r'class\s+.*SessionManager.*[:\(]',  # In database context
        ]
        
        # Forbidden direct URL construction patterns
        self.forbidden_url_construction_patterns = [
            r'postgresql\+asyncpg://.*format\(',
            r'postgresql://.*format\(',
            r'f["\']postgresql\+asyncpg://',
            r'f["\']postgresql://',
            r'DATABASE_URL.*\+.*\+',
            r'database_url\s*=\s*f["\']',
            r'db_url\s*=\s*f["\']',
            r'connection_string\s*=\s*f["\']',
            r'\.replace\(["\']postgresql["\'],',
            r'url\.replace\(',
            r'database_url\.replace\(',
        ]
        
        # Forbidden configuration bypass patterns
        self.forbidden_config_bypass_patterns = [
            r'os\.environ\[["\']POSTGRES_',
            r'os\.environ\[["\']DATABASE_',
            r'getenv\s*\(\s*["\']POSTGRES_',
            r'getenv\s*\(\s*["\']DATABASE_',
            r'env\[["\']POSTGRES_',  # Direct env access
            r'env\[["\']DATABASE_',
        ]
        
        # Define paths to scan for violations
        self.scan_paths = [
            "netra_backend/app",
            "auth_service",
            "shared",
            "test_framework",
        ]
        
        # Define paths that are allowed to have database operations
        self.exempt_paths = {
            "test_framework/fixtures",  # Test fixtures
            "test_framework/ssot/database_test_utility.py",  # SSOT test utilities
            "database_scripts",  # Setup scripts
            "migrations",  # Migration scripts
            "alembic",  # Alembic migration framework
        }
        
    def test_no_duplicate_database_managers(self):
        """Test that only ONE DatabaseManager class exists in the codebase.
        
        Business Impact: Multiple database managers cause:
        - Connection pool conflicts leading to resource exhaustion
        - Inconsistent transaction handling causing data corruption
        - Configuration drift between managers
        """
        logger.info("Scanning for duplicate DatabaseManager implementations...")
        
        duplicate_managers = []
        canonical_manager_found = False
        
        for scan_path in self.scan_paths:
            for file_path in self._get_python_files(scan_path):
                if self._should_skip_file(file_path):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check for DatabaseManager class definitions
                    for pattern in self.forbidden_duplicate_manager_patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            relative_path = str(Path(file_path).relative_to(Path.cwd())).replace("\\", "/")
                            
                            if relative_path == self.canonical_database_manager_path:
                                canonical_manager_found = True
                                logger.info(f"✓ Found canonical DatabaseManager at {relative_path}")
                            else:
                                duplicate_managers.append({
                                    'file': relative_path,
                                    'line': self._get_line_number(content, match.start()),
                                    'pattern': pattern,
                                    'match': match.group()
                                })
                                logger.warning(f"⚠ Found duplicate manager at {relative_path}:{self._get_line_number(content, match.start())}")
                                
                except Exception as e:
                    logger.warning(f"Failed to scan {file_path}: {e}")
                    
        # Record findings
        self.record_metric("canonical_manager_found", canonical_manager_found)
        self.record_metric("duplicate_managers_count", len(duplicate_managers))
        self.record_metric("duplicate_managers", duplicate_managers)
        
        # Assert canonical manager exists
        assert canonical_manager_found, (
            f"Canonical DatabaseManager not found at {self.canonical_database_manager_path}. "
            "This indicates a critical SSOT violation - the canonical database manager is missing."
        )
        
        # Assert no duplicates exist
        if duplicate_managers:
            violation_details = "\n".join([
                f"  - {dup['file']}:{dup['line']} - {dup['match']}"
                for dup in duplicate_managers
            ])
            assert False, (
                f"CRITICAL: Found {len(duplicate_managers)} duplicate DatabaseManager implementations.\n"
                f"This violates SSOT principles and can cause data integrity issues:\n"
                f"{violation_details}\n\n"
                f"REMEDIATION:\n"
                f"1. Remove all duplicate DatabaseManager classes\n"
                f"2. Import from canonical path: {self.canonical_database_manager_path}\n"
                f"3. Ensure all database access uses the canonical manager"
            )
            
        logger.info("✓ No duplicate DatabaseManager implementations found")
        
    def test_canonical_database_access_patterns(self):
        """Test that all database access uses canonical DatabaseManager patterns.
        
        Business Impact: Direct database access bypassing the manager causes:
        - Uncoordinated transactions leading to data corruption
        - Connection leaks causing service degradation
        - Inconsistent error handling and recovery
        """
        logger.info("Scanning for canonical database access pattern violations...")
        
        violations = []
        
        for scan_path in self.scan_paths:
            for file_path in self._get_python_files(scan_path):
                if self._should_skip_file(file_path):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    relative_path = str(Path(file_path).relative_to(Path.cwd())).replace("\\", "/")
                    
                    # Skip the canonical manager itself
                    if relative_path == self.canonical_database_manager_path:
                        continue
                        
                    # Check for proper database manager imports
                    has_proper_import = self._check_proper_database_import(content)
                    has_database_usage = self._check_database_usage(content)
                    
                    if has_database_usage and not has_proper_import:
                        violations.append({
                            'file': relative_path,
                            'type': 'missing_canonical_import',
                            'description': 'Uses database operations without importing canonical DatabaseManager'
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to scan {file_path}: {e}")
                    
        # Record findings
        self.record_metric("canonical_access_violations_count", len(violations))
        self.record_metric("canonical_access_violations", violations)
        
        if violations:
            violation_details = "\n".join([
                f"  - {viol['file']}: {viol['description']}"
                for viol in violations
            ])
            assert False, (
                f"CRITICAL: Found {len(violations)} canonical database access violations.\n"
                f"These can cause uncoordinated database operations:\n"
                f"{violation_details}\n\n"
                f"REMEDIATION:\n"
                f"1. Import DatabaseManager from canonical path:\n"
                f"   from netra_backend.app.db.database_manager import DatabaseManager\n"
                f"2. Use manager methods instead of direct database operations\n"
                f"3. Remove any custom database connection code"
            )
            
        logger.info("✓ All database access uses canonical patterns")
        
    def test_no_direct_database_connections(self):
        """Test that no code creates direct database connections bypassing the manager.
        
        Business Impact: Direct connections cause:
        - Connection pool exhaustion from unmanaged connections
        - Transaction isolation failures
        - Configuration inconsistencies
        - Resource leaks leading to service outages
        """
        logger.info("Scanning for direct database connection violations...")
        
        violations = []
        
        for scan_path in self.scan_paths:
            for file_path in self._get_python_files(scan_path):
                if self._should_skip_file(file_path):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    relative_path = str(Path(file_path).relative_to(Path.cwd())).replace("\\", "/")
                    
                    # Skip canonical manager and allowed integration paths
                    if relative_path in self.allowed_database_integration_paths:
                        continue
                        
                    # Check for forbidden direct connection patterns
                    for pattern in self.forbidden_direct_connection_patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            violations.append({
                                'file': relative_path,
                                'line': self._get_line_number(content, match.start()),
                                'pattern': pattern,
                                'match': match.group(),
                                'type': 'direct_database_connection'
                            })
                            
                except Exception as e:
                    logger.warning(f"Failed to scan {file_path}: {e}")
                    
        # Record findings
        self.record_metric("direct_connection_violations_count", len(violations))
        self.record_metric("direct_connection_violations", violations)
        
        if violations:
            violation_details = "\n".join([
                f"  - {viol['file']}:{viol['line']} - {viol['match']}"
                for viol in violations
            ])
            assert False, (
                f"CRITICAL: Found {len(violations)} direct database connection violations.\n"
                f"These bypass the canonical manager and can cause data integrity issues:\n"
                f"{violation_details}\n\n"
                f"REMEDIATION:\n"
                f"1. Remove direct database connection code\n"
                f"2. Use DatabaseManager methods: get_connection(), get_session()\n"
                f"3. Ensure all database operations go through the canonical manager"
            )
            
        logger.info("✓ No direct database connections found")
        
    def test_database_configuration_ssot(self):
        """Test that database configuration comes from single source.
        
        Business Impact: Multiple configuration sources cause:
        - Environment-specific failures from config drift
        - Security vulnerabilities from inconsistent access patterns
        - Debugging difficulties from unclear configuration flow
        """
        logger.info("Scanning for database configuration SSOT violations...")
        
        violations = []
        
        for scan_path in self.scan_paths:
            for file_path in self._get_python_files(scan_path):
                if self._should_skip_file(file_path):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    relative_path = str(Path(file_path).relative_to(Path.cwd())).replace("\\", "/")
                    
                    # Skip allowed configuration paths
                    if relative_path in self.allowed_database_integration_paths:
                        continue
                        
                    # Check for forbidden configuration bypass patterns
                    for pattern in self.forbidden_config_bypass_patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            violations.append({
                                'file': relative_path,
                                'line': self._get_line_number(content, match.start()),
                                'pattern': pattern,
                                'match': match.group(),
                                'type': 'config_bypass'
                            })
                            
                    # Check for forbidden URL construction patterns
                    for pattern in self.forbidden_url_construction_patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            violations.append({
                                'file': relative_path,
                                'line': self._get_line_number(content, match.start()),
                                'pattern': pattern,
                                'match': match.group(),
                                'type': 'direct_url_construction'
                            })
                            
                except Exception as e:
                    logger.warning(f"Failed to scan {file_path}: {e}")
                    
        # Record findings
        self.record_metric("config_ssot_violations_count", len(violations))
        self.record_metric("config_ssot_violations", violations)
        
        if violations:
            violation_details = "\n".join([
                f"  - {viol['file']}:{viol['line']} - {viol['match']} ({viol['type']})"
                for viol in violations
            ])
            assert False, (
                f"CRITICAL: Found {len(violations)} database configuration SSOT violations.\n"
                f"These bypass canonical configuration and can cause environment issues:\n"
                f"{violation_details}\n\n"
                f"REMEDIATION:\n"
                f"1. Use get_config() for database configuration access\n"
                f"2. Use DatabaseURLBuilder for URL construction\n"
                f"3. Remove direct environment variable access\n"
                f"4. Remove manual URL construction code"
            )
            
        logger.info("✓ Database configuration follows SSOT patterns")
        
    # Helper methods
    
    def _get_python_files(self, scan_path: str) -> List[Path]:
        """Get all Python files in scan path."""
        base_path = Path.cwd() / scan_path
        if not base_path.exists():
            return []
            
        python_files = []
        for file_path in base_path.rglob("*.py"):
            if not any(exempt in str(file_path) for exempt in self.exempt_paths):
                python_files.append(file_path)
                
        return python_files
        
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped from scanning."""
        file_str = str(file_path)
        
        # Skip test files (they have different patterns)
        if "/test" in file_str or "test_" in file_path.name:
            return True
            
        # Skip exempt paths
        if any(exempt in file_str for exempt in self.exempt_paths):
            return True
            
        # Skip __pycache__ and similar
        if "__pycache__" in file_str or ".pyc" in file_str:
            return True
            
        return False
        
    def _get_line_number(self, content: str, position: int) -> int:
        """Get line number for position in content."""
        return content[:position].count('\n') + 1
        
    def _check_proper_database_import(self, content: str) -> bool:
        """Check if content has proper DatabaseManager import."""
        import_patterns = [
            r'from\s+netra_backend\.app\.db\.database_manager\s+import\s+DatabaseManager',
            r'from\s+netra_backend\.app\.db\s+import\s+.*DatabaseManager',
        ]
        
        for pattern in import_patterns:
            if re.search(pattern, content):
                return True
                
        return False
        
    def _check_database_usage(self, content: str) -> bool:
        """Check if content uses database operations."""
        usage_patterns = [
            r'DatabaseManager\(',
            r'\.get_session\(',
            r'\.get_connection\(',
            r'\.execute\(',
            r'session\.',
            r'async\s+with.*session',
        ]
        
        for pattern in usage_patterns:
            if re.search(pattern, content):
                return True
                
        return False