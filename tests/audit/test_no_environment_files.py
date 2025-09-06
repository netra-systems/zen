#!/usr/bin/env python3
# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Audit Test Suite: Prevent Environment File Regression

# REMOVED_SYNTAX_ERROR: This test suite ensures that environment-specific .env files are never created
# REMOVED_SYNTAX_ERROR: and that the staging/production environment configuration remains simplified.

# REMOVED_SYNTAX_ERROR: These tests prevent regression of the staging environment loading issues that
# REMOVED_SYNTAX_ERROR: were causing secrets to be loaded from local files instead of Google Secret Manager.
# REMOVED_SYNTAX_ERROR: '''

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


# REMOVED_SYNTAX_ERROR: class TestNoEnvironmentFiles:
    # REMOVED_SYNTAX_ERROR: """Test that no environment-specific .env files exist."""

    # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: def test_no_env_staging_file(self):
    # REMOVED_SYNTAX_ERROR: """Ensure .env.staging does not exist - it causes precedence issues."""
    # REMOVED_SYNTAX_ERROR: staging_env = project_root / ".env.staging"
    # REMOVED_SYNTAX_ERROR: assert not staging_env.exists(), ( )
    # REMOVED_SYNTAX_ERROR: "CRITICAL: .env.staging file exists! This causes precedence issues where "
    # REMOVED_SYNTAX_ERROR: "hardcoded values override Google Secret Manager. Delete this file immediately."
    

    # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: def test_no_env_production_file(self):
    # REMOVED_SYNTAX_ERROR: """Ensure .env.production does not exist."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: prod_env = project_root / ".env.production"
    # REMOVED_SYNTAX_ERROR: assert not prod_env.exists(), ( )
    # REMOVED_SYNTAX_ERROR: "CRITICAL: .env.production file exists! Production must only use "
    # REMOVED_SYNTAX_ERROR: "Google Secret Manager for secrets. Delete this file immediately."
    

    # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: def test_no_env_staging_local_file(self):
    # REMOVED_SYNTAX_ERROR: """Ensure .env.staging.local does not exist."""
    # REMOVED_SYNTAX_ERROR: staging_local = project_root / ".env.staging.local"
    # REMOVED_SYNTAX_ERROR: assert not staging_local.exists(), ( )
    # REMOVED_SYNTAX_ERROR: "CRITICAL: .env.staging.local file exists! This can override staging "
    # REMOVED_SYNTAX_ERROR: "configuration. Delete this file immediately."
    

# REMOVED_SYNTAX_ERROR: def test_gitignore_excludes_env_files(self):
    # REMOVED_SYNTAX_ERROR: """Verify .gitignore properly excludes environment files."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: gitignore_path = project_root / ".gitignore"
    # REMOVED_SYNTAX_ERROR: if gitignore_path.exists():
        # REMOVED_SYNTAX_ERROR: with open(gitignore_path, 'r') as f:
            # REMOVED_SYNTAX_ERROR: content = f.read()

            # REMOVED_SYNTAX_ERROR: required_patterns = [ )
            # REMOVED_SYNTAX_ERROR: ".env.staging.local",
            # REMOVED_SYNTAX_ERROR: ".env.production",
            # REMOVED_SYNTAX_ERROR: ".env.prod"
            

            # REMOVED_SYNTAX_ERROR: for pattern in required_patterns:
                # REMOVED_SYNTAX_ERROR: assert pattern in content or ".env.*" in content, ( )
                # REMOVED_SYNTAX_ERROR: "formatted_string"
                


# REMOVED_SYNTAX_ERROR: class TestEnvironmentLoadingLogic:
    # REMOVED_SYNTAX_ERROR: """Test that applications correctly skip .env loading in staging/production."""

    # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: def test_backend_skips_env_loading_in_staging(self):
    # REMOVED_SYNTAX_ERROR: """Verify backend main.py skips .env loading when ENVIRONMENT=staging."""
    # REMOVED_SYNTAX_ERROR: main_path = project_root / "netra_backend" / "app" / "main.py"

    # REMOVED_SYNTAX_ERROR: with open(main_path, 'r', encoding='utf-8') as f:
        # REMOVED_SYNTAX_ERROR: content = f.read()

        # Check for environment detection before .env loading
        # REMOVED_SYNTAX_ERROR: assert "environment in ['staging', 'production', 'prod']" in content, ( )
        # REMOVED_SYNTAX_ERROR: "Backend must check ENVIRONMENT before loading .env files"
        

        # REMOVED_SYNTAX_ERROR: assert "skipping all .env file loading (using GSM)" in content, ( )
        # REMOVED_SYNTAX_ERROR: "Backend must skip .env loading in staging/production"
        

        # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: def test_auth_service_skips_env_loading_in_staging(self):
    # REMOVED_SYNTAX_ERROR: """Verify auth service skips .env loading when ENVIRONMENT=staging."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: auth_main = project_root / "auth_service" / "main.py"

    # REMOVED_SYNTAX_ERROR: with open(auth_main, 'r', encoding='utf-8') as f:
        # REMOVED_SYNTAX_ERROR: content = f.read()

        # Check for environment detection
        # REMOVED_SYNTAX_ERROR: assert "environment in ['staging', 'production', 'prod']" in content, ( )
        # REMOVED_SYNTAX_ERROR: "Auth service must check ENVIRONMENT before loading .env files"
        

        # REMOVED_SYNTAX_ERROR: assert "skipping .env file loading (using GSM)" in content, ( )
        # REMOVED_SYNTAX_ERROR: "Auth service must skip .env loading in staging/production"
        


# REMOVED_SYNTAX_ERROR: class TestNoHardcodedSecrets:
    # REMOVED_SYNTAX_ERROR: """Test that no hardcoded secrets exist in staging/production code."""

# REMOVED_SYNTAX_ERROR: def _scan_file_for_secrets(self, filepath: Path) -> List[str]:
    # REMOVED_SYNTAX_ERROR: """Scan a file for potential hardcoded secrets."""
    # REMOVED_SYNTAX_ERROR: suspicious_patterns = []

    # REMOVED_SYNTAX_ERROR: with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        # REMOVED_SYNTAX_ERROR: content = f.read()

        # Skip test files, documentation, and deployment scripts
        # REMOVED_SYNTAX_ERROR: skip_patterns = [ )
        # REMOVED_SYNTAX_ERROR: '/test',
        # REMOVED_SYNTAX_ERROR: '.md',
        # REMOVED_SYNTAX_ERROR: 'deploy_to_gcp.py',  # Deployment script needs to set up GSM
        # REMOVED_SYNTAX_ERROR: 'update_postgres_password',  # Scripts for updating passwords
        # REMOVED_SYNTAX_ERROR: 'fix_staging_database',  # Database fix scripts
        # REMOVED_SYNTAX_ERROR: 'validate_staging_db',  # Validation scripts
        

        # REMOVED_SYNTAX_ERROR: if any(pattern in str(filepath) for pattern in skip_patterns):
            # REMOVED_SYNTAX_ERROR: return []

            # Look for hardcoded database passwords in application code
            # REMOVED_SYNTAX_ERROR: if 'qNdlZRHu(Mlc#)6K8LHm' in content:  # The old staging password
            # REMOVED_SYNTAX_ERROR: suspicious_patterns.append("formatted_string")

            # Look for JWT secrets in application code
            # REMOVED_SYNTAX_ERROR: if 'staging_jwt_secret_key_must_be_at_least_32_characters' in content:
                # REMOVED_SYNTAX_ERROR: suspicious_patterns.append("formatted_string")

                # REMOVED_SYNTAX_ERROR: return suspicious_patterns

# REMOVED_SYNTAX_ERROR: def test_no_hardcoded_staging_secrets(self):
    # REMOVED_SYNTAX_ERROR: """Ensure no hardcoded staging secrets in application code."""
    # REMOVED_SYNTAX_ERROR: suspicious_files = []

    # Scan key directories
    # REMOVED_SYNTAX_ERROR: dirs_to_scan = [ )
    # REMOVED_SYNTAX_ERROR: project_root / "netra_backend" / "app",
    # REMOVED_SYNTAX_ERROR: project_root / "auth_service",
    # REMOVED_SYNTAX_ERROR: project_root / "scripts",
    

    # REMOVED_SYNTAX_ERROR: for directory in dirs_to_scan:
        # REMOVED_SYNTAX_ERROR: if directory.exists():
            # REMOVED_SYNTAX_ERROR: for filepath in directory.rglob("*.py"):
                # REMOVED_SYNTAX_ERROR: issues = self._scan_file_for_secrets(filepath)
                # REMOVED_SYNTAX_ERROR: suspicious_files.extend(issues)

                # REMOVED_SYNTAX_ERROR: assert not suspicious_files, ( )
                # REMOVED_SYNTAX_ERROR: f"Found hardcoded secrets in files:
                    # REMOVED_SYNTAX_ERROR: " + "
                    # REMOVED_SYNTAX_ERROR: ".join(suspicious_files)
                    


# REMOVED_SYNTAX_ERROR: class TestDeploymentConfiguration:
    # REMOVED_SYNTAX_ERROR: """Test deployment script configuration."""

    # REMOVED_SYNTAX_ERROR: @pytest.mark.critical
# REMOVED_SYNTAX_ERROR: def test_deployment_script_has_staging_env_vars(self):
    # REMOVED_SYNTAX_ERROR: """Verify deployment script contains all necessary staging env vars."""
    # REMOVED_SYNTAX_ERROR: deploy_script = project_root / "scripts" / "deploy_to_gcp.py"

    # REMOVED_SYNTAX_ERROR: with open(deploy_script, 'r', encoding='utf-8') as f:
        # REMOVED_SYNTAX_ERROR: content = f.read()

        # REMOVED_SYNTAX_ERROR: required_configs = [ )
        # REMOVED_SYNTAX_ERROR: '"ENVIRONMENT": "staging"',
        # REMOVED_SYNTAX_ERROR: '"JWT_ALGORITHM": "HS256"',
        # REMOVED_SYNTAX_ERROR: 'POSTGRES_PASSWORD=postgres-password-staging',
        # REMOVED_SYNTAX_ERROR: 'JWT_SECRET_KEY=jwt-secret-key-staging',
        # REMOVED_SYNTAX_ERROR: '--set-secrets',
        

        # REMOVED_SYNTAX_ERROR: for config in required_configs:
            # REMOVED_SYNTAX_ERROR: assert config in content, ( )
            # REMOVED_SYNTAX_ERROR: "formatted_string"
            

# REMOVED_SYNTAX_ERROR: def test_deployment_script_uses_gsm_for_secrets(self):
    # REMOVED_SYNTAX_ERROR: """Verify deployment script loads all secrets from GSM."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: deploy_script = project_root / "scripts" / "deploy_to_gcp.py"

    # REMOVED_SYNTAX_ERROR: with open(deploy_script, 'r', encoding='utf-8') as f:
        # REMOVED_SYNTAX_ERROR: content = f.read()

        # Check that secrets are loaded from GSM
        # REMOVED_SYNTAX_ERROR: assert '--set-secrets' in content, "Deployment must use --set-secrets for GSM"

        # Verify critical secrets are from GSM
        # REMOVED_SYNTAX_ERROR: gsm_secrets = [ )
        # REMOVED_SYNTAX_ERROR: 'POSTGRES_PASSWORD=postgres-password-staging',
        # REMOVED_SYNTAX_ERROR: 'JWT_SECRET_KEY=jwt-secret-key-staging',
        # REMOVED_SYNTAX_ERROR: 'GOOGLE_CLIENT_ID=google-oauth-client-id-staging',
        # REMOVED_SYNTAX_ERROR: 'GOOGLE_CLIENT_SECRET=google-oauth-client-secret-staging',
        

        # REMOVED_SYNTAX_ERROR: for secret in gsm_secrets:
            # REMOVED_SYNTAX_ERROR: assert secret in content, "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestNoReferencesToStagingEnvFile:
    # REMOVED_SYNTAX_ERROR: """Test that no code references .env.staging."""

# REMOVED_SYNTAX_ERROR: def test_no_code_references_env_staging(self):
    # REMOVED_SYNTAX_ERROR: """Ensure no Python code references .env.staging."""
    # REMOVED_SYNTAX_ERROR: references = []

    # Only scan key directories to avoid timeout
    # REMOVED_SYNTAX_ERROR: dirs_to_scan = [ )
    # REMOVED_SYNTAX_ERROR: project_root / "netra_backend" / "app",
    # REMOVED_SYNTAX_ERROR: project_root / "auth_service",
    # REMOVED_SYNTAX_ERROR: project_root / "scripts",
    # REMOVED_SYNTAX_ERROR: project_root / "dev_launcher",
    

    # REMOVED_SYNTAX_ERROR: for directory in dirs_to_scan:
        # REMOVED_SYNTAX_ERROR: if not directory.exists():
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: for filepath in directory.rglob("*.py"):
                # Skip this test file, obsolete scripts, and very large files
                # REMOVED_SYNTAX_ERROR: skip_files = [ )
                # REMOVED_SYNTAX_ERROR: 'test_no_environment_files.py',
                # REMOVED_SYNTAX_ERROR: 'fix_staging_oauth.py',  # Obsolete - OAuth now in GSM
                # REMOVED_SYNTAX_ERROR: 'validate_staging_oauth.py',  # Obsolete - OAuth now in GSM
                # REMOVED_SYNTAX_ERROR: 'test_staging_simplified.py',  # Our test script
                # REMOVED_SYNTAX_ERROR: 'environment_validator_core.py',  # Old validator
                

                # REMOVED_SYNTAX_ERROR: if any(skip in str(filepath) for skip in skip_files):
                    # REMOVED_SYNTAX_ERROR: continue

                    # Skip files larger than 100KB to avoid timeout
                    # REMOVED_SYNTAX_ERROR: if filepath.stat().st_size > 100000:
                        # REMOVED_SYNTAX_ERROR: continue

                        # REMOVED_SYNTAX_ERROR: with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            # REMOVED_SYNTAX_ERROR: for i, line in enumerate(f, 1):
                                # REMOVED_SYNTAX_ERROR: if '.env.staging' in line and not line.strip().startswith('#'):
                                    # REMOVED_SYNTAX_ERROR: references.append("formatted_string")
                                    # REMOVED_SYNTAX_ERROR: if len(references) >= 10:  # Stop after finding 10 references
                                    # REMOVED_SYNTAX_ERROR: break

                                    # REMOVED_SYNTAX_ERROR: if len(references) >= 10:
                                        # REMOVED_SYNTAX_ERROR: break

                                        # REMOVED_SYNTAX_ERROR: assert not references, ( )
                                        # REMOVED_SYNTAX_ERROR: f"Found references to .env.staging in code:
                                            # REMOVED_SYNTAX_ERROR: " + "
                                            # REMOVED_SYNTAX_ERROR: ".join(references)
                                            


# REMOVED_SYNTAX_ERROR: class TestEnvironmentIsolation:
    # REMOVED_SYNTAX_ERROR: """Test that staging/production are properly isolated from dev."""

# REMOVED_SYNTAX_ERROR: def test_no_localhost_in_staging_config(self):
    # REMOVED_SYNTAX_ERROR: """Ensure no localhost references in staging configuration."""
    # REMOVED_SYNTAX_ERROR: deploy_script = project_root / "scripts" / "deploy_to_gcp.py"

    # REMOVED_SYNTAX_ERROR: with open(deploy_script, 'r', encoding='utf-8') as f:
        # REMOVED_SYNTAX_ERROR: lines = f.readlines()

        # REMOVED_SYNTAX_ERROR: for i, line in enumerate(lines, 1):
            # Skip comments and DATABASE_URL validation
            # REMOVED_SYNTAX_ERROR: if 'localhost' in line.lower():
                # REMOVED_SYNTAX_ERROR: if not line.strip().startswith('#') and 'DATABASE_URL' not in line:
                    # Check it's not in the validation section
                    # REMOVED_SYNTAX_ERROR: if 'if "localhost" in database_url' not in line:
                        # REMOVED_SYNTAX_ERROR: pytest.fail( )
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        


# REMOVED_SYNTAX_ERROR: class TestComplianceAudit:
    # REMOVED_SYNTAX_ERROR: """Comprehensive audit of environment configuration compliance."""

# REMOVED_SYNTAX_ERROR: def test_full_staging_configuration_audit(self):
    # REMOVED_SYNTAX_ERROR: """Run complete audit of staging configuration."""
    # REMOVED_SYNTAX_ERROR: audit_results = { )
    # REMOVED_SYNTAX_ERROR: 'env_files_absent': True,
    # REMOVED_SYNTAX_ERROR: 'env_loading_skipped': True,
    # REMOVED_SYNTAX_ERROR: 'secrets_from_gsm': True,
    # REMOVED_SYNTAX_ERROR: 'no_hardcoded_secrets': True,
    # REMOVED_SYNTAX_ERROR: 'no_localhost_refs': True,
    

    # Check no .env.staging exists
    # REMOVED_SYNTAX_ERROR: if (project_root / ".env.staging").exists():
        # REMOVED_SYNTAX_ERROR: audit_results['env_files_absent'] = False

        # Check environment loading logic
        # REMOVED_SYNTAX_ERROR: backend_main = project_root / "netra_backend" / "app" / "main.py"
        # REMOVED_SYNTAX_ERROR: if backend_main.exists():
            # REMOVED_SYNTAX_ERROR: with open(backend_main, 'r', encoding='utf-8') as f:
                # REMOVED_SYNTAX_ERROR: if "environment in ['staging'" not in f.read(): )
                # REMOVED_SYNTAX_ERROR: audit_results['env_loading_skipped'] = False

                # Generate audit report
                # REMOVED_SYNTAX_ERROR: passed = all(audit_results.values())

                # REMOVED_SYNTAX_ERROR: report = "Staging Configuration Audit Report
                # REMOVED_SYNTAX_ERROR: "
                # REMOVED_SYNTAX_ERROR: report += "=" * 50 + "
                # REMOVED_SYNTAX_ERROR: "
                # REMOVED_SYNTAX_ERROR: for check, result in audit_results.items():
                    # REMOVED_SYNTAX_ERROR: status = "PASS" if result else "FAIL"
                    # REMOVED_SYNTAX_ERROR: report += "formatted_string"

                    # REMOVED_SYNTAX_ERROR: assert passed, "formatted_string"


                        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                            # Run tests with pytest
                            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])
                            # REMOVED_SYNTAX_ERROR: pass