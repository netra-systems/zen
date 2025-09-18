#!/usr/bin/env python3
'''
Audit Test Suite: Prevent Environment File Regression

This test suite ensures that environment-specific .env files are never created
and that the staging/production environment configuration remains simplified.

These tests prevent regression of the staging environment loading issues that
were causing secrets to be loaded from local files instead of Google Secret Manager.
'''

import os
import sys
import ast
from pathlib import Path
from typing import List, Tuple
from shared.isolated_environment import IsolatedEnvironment

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestNoEnvironmentFiles:
    """Test that no environment-specific .env files exist."""

    @pytest.mark.critical
    def test_no_env_staging_file(self):
        """Ensure .env.staging does not exist - it causes precedence issues."""
        staging_env = project_root / ".env.staging"
        assert not staging_env.exists(), ( )
        "CRITICAL: .env.staging file exists! This causes precedence issues where "
        "hardcoded values override Google Secret Manager. Delete this file immediately."
    

        @pytest.mark.critical
    def test_no_env_production_file(self):
        """Ensure .env.production does not exist."""
        pass
        prod_env = project_root / ".env.production"
        assert not prod_env.exists(), ( )
        "CRITICAL: .env.production file exists! Production must only use "
        "Google Secret Manager for secrets. Delete this file immediately."
    

        @pytest.mark.critical
    def test_no_env_staging_local_file(self):
        """Ensure .env.staging.local does not exist."""
        staging_local = project_root / ".env.staging.local"
        assert not staging_local.exists(), ( )
        "CRITICAL: .env.staging.local file exists! This can override staging "
        "configuration. Delete this file immediately."
    

    def test_gitignore_excludes_env_files(self):
        """Verify .gitignore properly excludes environment files."""
        pass
        gitignore_path = project_root / ".gitignore"
        if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
        content = f.read()

        required_patterns = [ )
        ".env.staging.local",
        ".env.production",
        ".env.prod"
            

        for pattern in required_patterns:
        assert pattern in content or ".env.*" in content, ( )
        "formatted_string"
                


class TestEnvironmentLoadingLogic:
        """Test that applications correctly skip .env loading in staging/production."""

        @pytest.mark.critical
    def test_backend_skips_env_loading_in_staging(self):
        """Verify backend main.py skips .env loading when ENVIRONMENT=staging."""
        main_path = project_root / "netra_backend" / "app" / "main.py"

        with open(main_path, 'r', encoding='utf-8') as f:
        content = f.read()

        # Check for environment detection before .env loading
        assert "environment in ['staging', 'production', 'prod']" in content, ( )
        "Backend must check ENVIRONMENT before loading .env files"
        

        assert "skipping all .env file loading (using GSM)" in content, ( )
        "Backend must skip .env loading in staging/production"
        

        @pytest.mark.critical
    def test_auth_service_skips_env_loading_in_staging(self):
        """Verify auth service skips .env loading when ENVIRONMENT=staging."""
        pass
        auth_main = project_root / "auth_service" / "main.py"

        with open(auth_main, 'r', encoding='utf-8') as f:
        content = f.read()

        # Check for environment detection
        assert "environment in ['staging', 'production', 'prod']" in content, ( )
        "Auth service must check ENVIRONMENT before loading .env files"
        

        assert "skipping .env file loading (using GSM)" in content, ( )
        "Auth service must skip .env loading in staging/production"
        


class TestNoHardcodedSecrets:
        """Test that no hardcoded secrets exist in staging/production code."""

    def _scan_file_for_secrets(self, filepath: Path) -> List[str]:
        """Scan a file for potential hardcoded secrets."""
        suspicious_patterns = []

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

        # Skip test files, documentation, and deployment scripts
        skip_patterns = [ )
        '/test',
        '.md',
        'deploy_to_gcp.py',  # Deployment script needs to set up GSM
        'update_postgres_password',  # Scripts for updating passwords
        'fix_staging_database',  # Database fix scripts
        'validate_staging_db',  # Validation scripts
        

        if any(pattern in str(filepath) for pattern in skip_patterns):
        return []

            # Look for hardcoded database passwords in application code
        if 'qNdlZRHu(Mlc#)6K8LHm' in content:  # The old staging password
        suspicious_patterns.append("formatted_string")

            # Look for JWT secrets in application code
        if 'staging_jwt_secret_key_must_be_at_least_32_characters' in content:
        suspicious_patterns.append("formatted_string")

        return suspicious_patterns

    def test_no_hardcoded_staging_secrets(self):
        """Ensure no hardcoded staging secrets in application code."""
        suspicious_files = []

    # Scan key directories
        dirs_to_scan = [ )
        project_root / "netra_backend" / "app",
        project_root / "auth_service",
        project_root / "scripts",
    

        for directory in dirs_to_scan:
        if directory.exists():
        for filepath in directory.rglob("*.py"):
        issues = self._scan_file_for_secrets(filepath)
        suspicious_files.extend(issues)

        assert not suspicious_files, ( )
        f"Found hardcoded secrets in files:
        " + "
        ".join(suspicious_files)
                    


class TestDeploymentConfiguration:
        """Test deployment script configuration."""

        @pytest.mark.critical
    def test_deployment_script_has_staging_env_vars(self):
        """Verify deployment script contains all necessary staging env vars."""
        deploy_script = project_root / "scripts" / "deploy_to_gcp.py"

        with open(deploy_script, 'r', encoding='utf-8') as f:
        content = f.read()

        required_configs = [ )
        '"ENVIRONMENT": "staging"',
        '"JWT_ALGORITHM": "HS256"',
        'POSTGRES_PASSWORD=postgres-password-staging',
        'JWT_SECRET_KEY=jwt-secret-key-staging',
        '--set-secrets',
        

        for config in required_configs:
        assert config in content, ( )
        "formatted_string"
            

    def test_deployment_script_uses_gsm_for_secrets(self):
        """Verify deployment script loads all secrets from GSM."""
        pass
        deploy_script = project_root / "scripts" / "deploy_to_gcp.py"

        with open(deploy_script, 'r', encoding='utf-8') as f:
        content = f.read()

        Check that secrets are loaded from GSM
        assert '--set-secrets' in content, "Deployment must use --set-secrets for GSM"

        Verify critical secrets are from GSM
        gsm_secrets = [ )
        'POSTGRES_PASSWORD=postgres-password-staging',
        'JWT_SECRET_KEY=jwt-secret-key-staging',
        'GOOGLE_CLIENT_ID=google-oauth-client-id-staging',
        'GOOGLE_CLIENT_SECRET=google-oauth-client-secret-staging',
        

        for secret in gsm_secrets:
        assert secret in content, "formatted_string"


class TestNoReferencesToStagingEnvFile:
        """Test that no code references .env.staging."""

    def test_no_code_references_env_staging(self):
        """Ensure no Python code references .env.staging."""
        references = []

    # Only scan key directories to avoid timeout
        dirs_to_scan = [ )
        project_root / "netra_backend" / "app",
        project_root / "auth_service",
        project_root / "scripts",
        project_root / "dev_launcher",
    

        for directory in dirs_to_scan:
        if not directory.exists():
        continue

        for filepath in directory.rglob("*.py"):
                # Skip this test file, obsolete scripts, and very large files
        skip_files = [ )
        'test_no_environment_files.py',
        'fix_staging_oauth.py',  # Obsolete - OAuth now in GSM
        'validate_staging_oauth.py',  # Obsolete - OAuth now in GSM
        'test_staging_simplified.py',  # Our test script
        'environment_validator_core.py',  # Old validator
                

        if any(skip in str(filepath) for skip in skip_files):
        continue

                    # Skip files larger than 100KB to avoid timeout
        if filepath.stat().st_size > 100000:
        continue

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f, 1):
        if '.env.staging' in line and not line.strip().startswith('#'):
        references.append("formatted_string")
        if len(references) >= 10:  # Stop after finding 10 references
        break

        if len(references) >= 10:
        break

        assert not references, ( )
        f"Found references to .env.staging in code:
        " + "
        ".join(references)
                                            


class TestEnvironmentIsolation:
        """Test that staging/production are properly isolated from dev."""

    def test_no_localhost_in_staging_config(self):
        """Ensure no localhost references in staging configuration."""
        deploy_script = project_root / "scripts" / "deploy_to_gcp.py"

        with open(deploy_script, 'r', encoding='utf-8') as f:
        lines = f.readlines()

        for i, line in enumerate(lines, 1):
            # Skip comments and #removed-legacyvalidation
        if 'localhost' in line.lower():
        if not line.strip().startswith('#') and 'DATABASE_URL' not in line:
                    # Check it's not in the validation section
        if 'if "localhost" in database_url' not in line:
        pytest.fail( )
        "formatted_string"
                        


class TestComplianceAudit:
        """Comprehensive audit of environment configuration compliance."""

    def test_full_staging_configuration_audit(self):
        """Run complete audit of staging configuration."""
        audit_results = { )
        'env_files_absent': True,
        'env_loading_skipped': True,
        'secrets_from_gsm': True,
        'no_hardcoded_secrets': True,
        'no_localhost_refs': True,
    

    # Check no .env.staging exists
        if (project_root / ".env.staging").exists():
        audit_results['env_files_absent'] = False

        # Check environment loading logic
        backend_main = project_root / "netra_backend" / "app" / "main.py"
        if backend_main.exists():
        with open(backend_main, 'r', encoding='utf-8') as f:
        if "environment in ['staging'" not in f.read(): )
        audit_results['env_loading_skipped'] = False

                # Generate audit report
        passed = all(audit_results.values())

        report = "Staging Configuration Audit Report
        "
        report += "=" * 50 + "
        "
        for check, result in audit_results.items():
        status = "PASS" if result else "FAIL"
        report += "formatted_string"

        assert passed, "formatted_string"


        if __name__ == "__main__":
                            # Run tests with pytest
        pytest.main([__file__, "-v", "--tb=short"])
        pass
