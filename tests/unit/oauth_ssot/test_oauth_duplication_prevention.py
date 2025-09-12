"""
OAuth Duplication Prevention Test Suite - Issue #213

CRITICAL: Tests to prevent OAuth validation implementation duplication.

These tests MUST FAIL before SSOT consolidation and PASS after consolidation.
They serve as regression protection against duplicate OAuth validation implementations.

Business Value: Platform/Internal - SSOT Compliance and Technical Debt Prevention
Prevents 500+ lines of duplicate OAuth validation code that blocks golden path.

Test Strategy:
- Scan codebase for duplicate OAuth validation implementations
- Validate SSOT import compliance across all services
- Ensure single source of truth for OAuth validation logic
- Detect regression to duplicate implementations

SAFETY: These tests detect real architectural violations without breaking existing functionality.
"""

import ast
import os
import re
import logging
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path

import pytest
from shared.configuration.central_config_validator import CentralConfigurationValidator

logger = logging.getLogger(__name__)


class TestOAuthDuplicationPrevention:
    """Test suite to prevent OAuth validation duplication - Issue #213."""
    
    def setup_method(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parents[3]  # /Users/anthony/Desktop/netra-apex
        self.known_duplicate_patterns = [
            "def get_oauth_client_id",
            "def get_oauth_credentials", 
            "def validate_oauth",
            "class.*OAuth.*Validator"
        ]
        # Known SSOT implementation (the only one that should exist)
        self.ssot_oauth_file = self.project_root / "shared" / "configuration" / "central_config_validator.py"
    
    def test_no_duplicate_oauth_validators_exist(self):
        """
        CRITICAL: Ensure only CentralConfigurationValidator handles OAuth validation.
        
        This test MUST FAIL if duplicate OAuth validation implementations exist.
        It's designed to detect Issue #213 OAuth duplication violations.
        """
        oauth_implementations = self._scan_for_oauth_implementations()
        
        # Filter out the SSOT implementation and test files
        non_ssot_implementations = [
            impl for impl in oauth_implementations 
            if not self._is_allowed_oauth_implementation(impl["file_path"])
        ]
        
        # CRITICAL ASSERTION: Only SSOT implementation should exist
        if non_ssot_implementations:
            duplicate_details = "\n".join([
                f"  - {impl['file_path']}:{impl['line_number']} -> {impl['function_name']}"
                for impl in non_ssot_implementations
            ])
            pytest.fail(
                f"SSOT VIOLATION: Found {len(non_ssot_implementations)} duplicate OAuth validation implementations.\n"
                f"Only CentralConfigurationValidator should handle OAuth validation.\n"
                f"Duplicate implementations found:\n{duplicate_details}\n\n"
                f"REQUIRED ACTION: Consolidate these into central_config_validator.py SSOT implementation."
            )
        
        logger.info(" PASS:  No duplicate OAuth validators found - SSOT compliance maintained")
        
        # Verify SSOT implementation exists
        assert self.ssot_oauth_file.exists(), \
            f"SSOT OAuth implementation not found at {self.ssot_oauth_file}"
        
        # Verify SSOT has required OAuth methods
        ssot_content = self.ssot_oauth_file.read_text()
        required_methods = ["get_oauth_credentials", "get_oauth_client_id"]
        for method in required_methods:
            assert method in ssot_content, \
                f"SSOT OAuth implementation missing required method: {method}"
    
    def test_oauth_ssot_import_compliance(self):
        """
        Test that all OAuth validation imports use SSOT.
        
        This test MUST FAIL if non-SSOT OAuth validation imports are found.
        Prevents import-level SSOT violations.
        """
        non_compliant_imports = self._scan_for_non_ssot_oauth_imports()
        
        if non_compliant_imports:
            import_details = "\n".join([
                f"  - {imp['file_path']}:{imp['line_number']} -> {imp['import_statement']}"
                for imp in non_compliant_imports
            ])
            pytest.fail(
                f"IMPORT VIOLATION: Found {len(non_compliant_imports)} non-SSOT OAuth imports.\n"
                f"All OAuth validation must import from shared.configuration.central_config_validator\n"
                f"Non-compliant imports:\n{import_details}\n\n"
                f"REQUIRED ACTION: Update imports to use SSOT OAuth validation."
            )
        
        logger.info(" PASS:  All OAuth imports use SSOT - import compliance maintained")
    
    def test_oauth_validation_single_source_truth(self):
        """
        Test OAuth validation happens in single location.
        
        This test MUST FAIL if OAuth validation logic found in multiple places.
        Ensures business logic centralization.
        """
        oauth_validation_logic = self._scan_for_oauth_validation_logic()
        
        # Filter out SSOT and test implementations
        non_ssot_logic = [
            logic for logic in oauth_validation_logic
            if not self._is_allowed_oauth_implementation(logic["file_path"])
        ]
        
        if non_ssot_logic:
            logic_details = "\n".join([
                f"  - {logic['file_path']}:{logic['line_number']} -> {logic['logic_type']}"
                for logic in non_ssot_logic
            ])
            pytest.fail(
                f"LOGIC VIOLATION: Found OAuth validation logic in {len(non_ssot_logic)} non-SSOT locations.\n"
                f"OAuth validation logic must exist only in CentralConfigurationValidator.\n"
                f"Duplicate logic found:\n{logic_details}\n\n"
                f"REQUIRED ACTION: Move OAuth validation logic to central_config_validator.py SSOT."
            )
        
        logger.info(" PASS:  OAuth validation logic exists only in SSOT - logic centralization maintained")
    
    def test_oauth_configuration_consistency_validation(self):
        """
        Test OAuth configuration access is consistent across all usage.
        
        This test MUST FAIL if inconsistent OAuth configuration patterns are found.
        Ensures configuration access patterns are unified.
        """
        oauth_config_access = self._scan_for_oauth_config_access()
        
        # Analyze access patterns for consistency
        inconsistent_patterns = self._analyze_oauth_config_consistency(oauth_config_access)
        
        if inconsistent_patterns:
            pattern_details = "\n".join([
                f"  - {pattern['file_path']}:{pattern['line_number']} -> {pattern['pattern']} (expected: {pattern['expected_pattern']})"
                for pattern in inconsistent_patterns
            ])
            pytest.fail(
                f"CONSISTENCY VIOLATION: Found {len(inconsistent_patterns)} inconsistent OAuth config access patterns.\n"
                f"OAuth configuration access must follow SSOT patterns.\n"
                f"Inconsistent patterns:\n{pattern_details}\n\n"
                f"REQUIRED ACTION: Update OAuth config access to use SSOT patterns."
            )
        
        logger.info(" PASS:  OAuth configuration access patterns are consistent - pattern compliance maintained")
    
    def _scan_for_oauth_implementations(self) -> List[Dict[str, str]]:
        """Scan codebase for OAuth implementation functions."""
        implementations = []
        
        for pattern in self.known_duplicate_patterns:
            for file_path in self._get_python_files():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Search for OAuth implementation patterns
                    for line_num, line in enumerate(content.splitlines(), 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            implementations.append({
                                "file_path": str(file_path),
                                "line_number": line_num,
                                "function_name": line.strip(),
                                "pattern": pattern
                            })
                except (UnicodeDecodeError, IOError):
                    # Skip binary files or files we can't read
                    continue
        
        return implementations
    
    def _scan_for_non_ssot_oauth_imports(self) -> List[Dict[str, str]]:
        """Scan for OAuth imports that don't use SSOT."""
        non_compliant_imports = []
        
        ssot_import_patterns = [
            "from shared.configuration.central_config_validator import",
            "import shared.configuration.central_config_validator"
        ]
        
        non_ssot_oauth_import_patterns = [
            r"from.*oauth.*import.*get_oauth",
            r"import.*oauth.*validator",
            r"from.*validator.*import.*oauth",
            r"from.*config.*import.*get_oauth"
        ]
        
        for file_path in self._get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if file uses OAuth but doesn't import from SSOT
                uses_oauth = bool(re.search(r"get_oauth|oauth.*validation", content, re.IGNORECASE))
                uses_ssot_import = any(pattern in content for pattern in ssot_import_patterns)
                
                if uses_oauth and not uses_ssot_import:
                    # Look for specific non-SSOT import patterns
                    for line_num, line in enumerate(content.splitlines(), 1):
                        for pattern in non_ssot_oauth_import_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                non_compliant_imports.append({
                                    "file_path": str(file_path),
                                    "line_number": line_num,
                                    "import_statement": line.strip()
                                })
                                
            except (UnicodeDecodeError, IOError):
                continue
        
        return non_compliant_imports
    
    def _scan_for_oauth_validation_logic(self) -> List[Dict[str, str]]:
        """Scan for OAuth validation business logic implementations."""
        validation_logic = []
        
        # Patterns that indicate OAuth validation logic (not just imports/calls)
        logic_patterns = [
            (r"client_id.*=.*env.*oauth", "OAuth client ID environment lookup"),
            (r"client_secret.*=.*env.*oauth", "OAuth client secret environment lookup"),
            (r"if.*oauth.*client", "OAuth client validation logic"),
            (r"raise.*oauth.*error", "OAuth error handling logic"),
            (r"oauth.*redirect.*uri", "OAuth redirect URI validation logic"),
            (r"oauth.*state.*validation", "OAuth state validation logic")
        ]
        
        for file_path in self._get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern, logic_type in logic_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            validation_logic.append({
                                "file_path": str(file_path),
                                "line_number": line_num,
                                "logic_type": logic_type,
                                "code_line": line.strip()
                            })
                            
            except (UnicodeDecodeError, IOError):
                continue
        
        return validation_logic
    
    def _scan_for_oauth_config_access(self) -> List[Dict[str, str]]:
        """Scan for OAuth configuration access patterns."""
        config_access = []
        
        access_patterns = [
            (r"get_oauth_client_id\(\)", "SSOT method call"),
            (r"get_oauth_credentials\(\)", "SSOT method call"),
            (r"os\.environ.*OAUTH", "Direct environment access"),
            (r"get_env.*OAUTH", "Environment wrapper access"),
            (r"config.*oauth", "Config object access")
        ]
        
        for file_path in self._get_python_files():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern, access_type in access_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            config_access.append({
                                "file_path": str(file_path),
                                "line_number": line_num,
                                "access_type": access_type,
                                "code_line": line.strip()
                            })
                            
            except (UnicodeDecodeError, IOError):
                continue
        
        return config_access
    
    def _analyze_oauth_config_consistency(self, config_access: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Analyze OAuth configuration access for consistency violations."""
        inconsistent_patterns = []
        
        for access in config_access:
            # Skip SSOT and test files
            if self._is_allowed_oauth_implementation(access["file_path"]):
                continue
            
            # Check for non-SSOT access patterns
            if access["access_type"] in ["Direct environment access", "Environment wrapper access", "Config object access"]:
                inconsistent_patterns.append({
                    "file_path": access["file_path"],
                    "line_number": access["line_number"],
                    "pattern": access["access_type"],
                    "expected_pattern": "SSOT method call",
                    "code_line": access["code_line"]
                })
        
        return inconsistent_patterns
    
    def _is_allowed_oauth_implementation(self, file_path: str) -> bool:
        """Check if file is allowed to have OAuth implementation."""
        allowed_patterns = [
            # SSOT implementation
            "shared/configuration/central_config_validator.py",
            # Test files
            "/test_",
            "/tests/",
            # Documentation
            "/docs/",
            # Backups
            "/backup/",
            # Development utilities
            "/scripts/",
            # Legacy files being migrated (temporary)
            "/auth_service/auth_core/oauth/"
        ]
        
        return any(pattern in file_path for pattern in allowed_patterns)
    
    def _get_python_files(self) -> List[Path]:
        """Get all Python files in the project."""
        python_files = []
        
        # Exclude certain directories to avoid noise
        exclude_dirs = {
            '.git', '__pycache__', 'node_modules', '.pytest_cache',
            'venv', 'env', '.venv', 'dist', 'build'
        }
        
        for root, dirs, files in os.walk(self.project_root):
            # Remove excluded directories from the search
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files


def test_oauth_duplication_detection_capability():
    """
    Verify test capability to detect OAuth duplication.
    
    This meta-test ensures our duplication detection tests work correctly.
    """
    test_instance = TestOAuthDuplicationPrevention()
    test_instance.setup_method()
    
    # Verify we can scan for implementations
    implementations = test_instance._scan_for_oauth_implementations()
    assert len(implementations) >= 1, \
        "Should find at least the SSOT implementation"
    
    # Verify SSOT file is recognized
    assert test_instance.ssot_oauth_file.exists(), \
        "SSOT OAuth file should exist"
    
    # Verify we can distinguish SSOT from duplicates
    ssot_path = str(test_instance.ssot_oauth_file)
    assert test_instance._is_allowed_oauth_implementation(ssot_path), \
        "SSOT file should be recognized as allowed implementation"
    
    logger.info(" PASS:  OAuth duplication detection capability verified")


if __name__ == "__main__":
    # Run the meta-test to verify detection capability
    test_oauth_duplication_detection_capability()
    print(" PASS:  OAuth duplication prevention tests created and capability verified!")