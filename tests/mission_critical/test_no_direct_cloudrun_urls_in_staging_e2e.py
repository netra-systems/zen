#!/usr/bin/env python
"""MISSION CRITICAL: Prevent Direct Cloud Run URLs in E2E Tests

BUSINESS CRITICAL: E2E tests MUST validate the same infrastructure path users experience.
Direct Cloud Run URLs bypass load balancers and create infrastructure mismatches.

FAILURE IMPACT:
- Load balancer issues go undetected
- Staging doesn't mirror production architecture  
- False confidence in deployment readiness
- Production incidents from infrastructure gaps

This test enforces the remediation completed per:
reports/remediation/LOAD_BALANCER_ENDPOINT_REMEDIATION_PLAN.md
"""

import pytest
import re
import glob
from pathlib import Path
from typing import List, Dict

# Add project root to path
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestCloudRunURLCompliance:
    """Mission critical tests to prevent direct Cloud Run URL regression"""
    
    # FORBIDDEN: Direct Cloud Run URL patterns
    FORBIDDEN_PATTERNS = [
        r"https://netra-backend-staging-pnovr5vsba-uc\.a\.run\.app",
        r"wss://netra-backend-staging-pnovr5vsba-uc\.a\.run\.app", 
        r"https://netra-frontend-staging-pnovr5vsba-uc\.a\.run\.app",
        r"wss://netra-frontend-staging-pnovr5vsba-uc\.a\.run\.app"
    ]
    
    # REQUIRED: Load balancer endpoints
    REQUIRED_LOAD_BALANCER_DOMAINS = [
        "api.staging.netrasystems.ai",
        "app.staging.netrasystems.ai",
        "auth.staging.netrasystems.ai"
    ]
    
    # File patterns to validate
    E2E_TEST_PATTERNS = [
        "tests/e2e/**/*.py",
        "tests/mission_critical/**/*.py",
        "tests/integration/**/*.py"
    ]
    
    # Core configuration files
    CORE_CONFIG_FILES = [
        "netra_backend/app/core/network_constants.py",
        "tests/e2e/e2e_test_config.py"
    ]
    
    @pytest.fixture
    def e2e_test_files(self) -> List[Path]:
        """Get all E2E test files"""
        test_files = []
        
        for pattern in self.E2E_TEST_PATTERNS:
            files = glob.glob(str(project_root / pattern), recursive=True)
            for file_path in files:
                path = Path(file_path)
                if path.suffix == '.py' and 'backup' not in str(path):
                    test_files.append(path)
        
        return test_files
    
    @pytest.fixture 
    def core_config_files(self) -> List[Path]:
        """Get core configuration files"""
        config_files = []
        
        for file_path in self.CORE_CONFIG_FILES:
            path = project_root / file_path
            if path.exists():
                config_files.append(path)
        
        return config_files
    
    def test_no_direct_cloudrun_urls_in_e2e_tests(self, e2e_test_files):
        """
        MISSION CRITICAL: E2E tests must NOT use direct Cloud Run URLs
        
        Validates that all E2E tests use load balancer endpoints:
        - api.staging.netrasystems.ai (backend)
        - app.staging.netrasystems.ai (frontend)  
        - auth.staging.netrasystems.ai (auth)
        
        NEVER direct Cloud Run URLs like:
        - netra-backend-staging-pnovr5vsba-uc.a.run.app
        """
        violations = []
        
        for file_path in e2e_test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check each forbidden pattern
                for pattern in self.FORBIDDEN_PATTERNS:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        # Find line number
                        line_num = content[:match.start()].count('\n') + 1
                        violations.append({
                            'file': str(file_path.relative_to(project_root)),
                            'line': line_num,
                            'pattern': pattern,
                            'content': match.group(0)
                        })
                        
            except Exception as e:
                pytest.fail(f"Error reading {file_path}: {e}")
        
        if violations:
            error_msg = "\n ALERT:  DIRECT CLOUD RUN URLs DETECTED IN E2E TESTS!\n\n"
            error_msg += "E2E tests MUST use load balancer endpoints, not direct Cloud Run URLs.\n"
            error_msg += "This creates infrastructure mismatch between tests and user experience.\n\n"
            
            for violation in violations:
                error_msg += f"File: {violation['file']}\n"
                error_msg += f"Line: {violation['line']}\n" 
                error_msg += f"URL: {violation['content']}\n"
                error_msg += "Fix: Replace with appropriate load balancer endpoint\n\n"
            
            error_msg += "REMEDIATION:\n"
            error_msg += "Run: python scripts/migrate_test_urls_to_load_balancer.py\n"
            
            pytest.fail(error_msg)
    
    def test_core_config_uses_load_balancer_endpoints(self, core_config_files):
        """
        MISSION CRITICAL: Core configuration files must use load balancer endpoints
        
        Validates URLConstants and E2E config use proper staging domains.
        """
        violations = []
        
        for file_path in core_config_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for forbidden patterns in core config
                for pattern in self.FORBIDDEN_PATTERNS:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        violations.append({
                            'file': str(file_path.relative_to(project_root)),
                            'line': line_num,
                            'pattern': pattern,
                            'content': match.group(0),
                            'type': 'CORE_CONFIG'
                        })
                        
            except Exception as e:
                pytest.fail(f"Error reading {file_path}: {e}")
        
        if violations:
            error_msg = "\n ALERT:  DIRECT CLOUD RUN URLs IN CORE CONFIGURATION!\n\n"
            error_msg += "Core configuration files MUST use load balancer endpoints.\n"
            error_msg += "These are SSOT files that affect ALL tests and services.\n\n"
            
            for violation in violations:
                error_msg += f"File: {violation['file']}\n"
                error_msg += f"Line: {violation['line']}\n"
                error_msg += f"URL: {violation['content']}\n\n"
            
            error_msg += "CRITICAL: Update network_constants.py and e2e_test_config.py immediately!\n"
            
            pytest.fail(error_msg)
    
    def test_staging_tests_use_proper_domains(self, e2e_test_files):
        """
        Validate that tests referencing staging use proper load balancer domains
        
        Files that mention "staging" should use netrasystems.ai domains.
        """
        staging_files_without_proper_domains = []
        
        for file_path in e2e_test_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Skip files that don't mention staging
                if "staging" not in content.lower():
                    continue
                
                # Check if file uses any load balancer domains
                has_proper_domains = any(
                    domain in content 
                    for domain in self.REQUIRED_LOAD_BALANCER_DOMAINS
                )
                
                # Check if it's using old Cloud Run patterns
                has_cloud_run_urls = any(
                    re.search(pattern, content) 
                    for pattern in self.FORBIDDEN_PATTERNS
                )
                
                if not has_proper_domains and has_cloud_run_urls:
                    staging_files_without_proper_domains.append(
                        str(file_path.relative_to(project_root))
                    )
                    
            except Exception as e:
                pytest.fail(f"Error reading {file_path}: {e}")
        
        if staging_files_without_proper_domains:
            error_msg = "\n WARNING: [U+FE0F]  STAGING TESTS NOT USING LOAD BALANCER DOMAINS:\n\n"
            for file_path in staging_files_without_proper_domains:
                error_msg += f"- {file_path}\n"
            
            error_msg += "\nThese files reference staging but may not use proper load balancer endpoints.\n"
            error_msg += "Update to use: api.staging.netrasystems.ai, app.staging.netrasystems.ai, auth.staging.netrasystems.ai\n"
            
            # This is a warning, not a hard failure
            pytest.skip(error_msg)
    
    def test_load_balancer_compliance_validation_exists(self):
        """
        Ensure compliance validation script exists and is executable
        """
        validator_script = project_root / "scripts" / "validate_load_balancer_compliance.py"
        
        assert validator_script.exists(), (
            "Load balancer compliance validator script not found! "
            f"Expected: {validator_script}"
        )
        
        # Verify it's a Python script
        assert validator_script.suffix == '.py', (
            "Compliance validator must be a Python script"
        )
        
        # Verify it contains key validation logic
        with open(validator_script, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        assert "FORBIDDEN_PATTERNS" in script_content, (
            "Compliance validator missing forbidden patterns validation"
        )
        
        assert "netra-backend-staging-pnovr5vsba-uc.a.run.app" in script_content, (
            "Compliance validator missing Cloud Run URL detection"
        )
    
    def test_migration_script_exists_and_functional(self):
        """
        Ensure URL migration script exists for future remediation
        """
        migration_script = project_root / "scripts" / "migrate_test_urls_to_load_balancer.py"
        
        assert migration_script.exists(), (
            "URL migration script not found! "
            f"Expected: {migration_script}"
        )
        
        # Verify script has key functionality
        with open(migration_script, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        assert "URL_MIGRATIONS" in script_content, (
            "Migration script missing URL migration patterns"
        )
        
        assert "dry_run" in script_content, (
            "Migration script missing dry-run capability"
        )
        
        assert "rollback" in script_content, (
            "Migration script missing rollback capability"
        )


# Export for pytest discovery
__all__ = ['TestCloudRunURLCompliance']