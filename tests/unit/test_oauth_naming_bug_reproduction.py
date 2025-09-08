"""
Test to Reproduce OAuth Configuration Naming Bug

This test specifically reproduces the OAuth configuration bug where:
1. Backend service lacks OAuth configuration entirely  
2. Tests expect simplified OAuth naming (GOOGLE_CLIENT_ID) but it doesn't exist
3. Missing GSM mappings for simplified OAuth names
4. Missing oauth category in backend service secrets

This test is designed to FAIL initially, demonstrating the bug, then PASS after fix.

Created: 2025-09-07 as part of mandatory bug fixing process per CLAUDE.md section 3.5
"""

import pytest
from typing import Dict, List, Set
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from deployment.secrets_config import SecretConfig


class TestOAuthNamingBugReproduction:
    """Reproduction test suite for OAuth configuration naming bug."""
    
    def test_bug_reproduction_backend_missing_oauth_category(self):
        """REPRODUCES BUG: Backend service should have oauth category but doesn't.
        
        This test demonstrates the core bug - backend service completely lacks 
        OAuth configuration despite tests expecting it.
        """
        backend_secrets = SecretConfig.get_service_secrets("backend")
        
        # This assertion will FAIL initially, demonstrating the bug
        assert "oauth" in backend_secrets, (
            "BUG REPRODUCTION: Backend service missing oauth category. "
            "Tests expect OAuth configuration but backend has none defined. "
            "Available categories: " + str(list(backend_secrets.keys()))
        )
    
    def test_bug_reproduction_backend_missing_simplified_oauth_names(self):
        """REPRODUCES BUG: Backend service should have GOOGLE_CLIENT_ID but doesn't.
        
        Tests expect simplified OAuth naming for backend but no OAuth secrets exist.
        """
        backend_all_secrets = SecretConfig.get_all_service_secrets("backend")
        
        # These assertions will FAIL initially, demonstrating the bug
        assert "GOOGLE_CLIENT_ID" in backend_all_secrets, (
            "BUG REPRODUCTION: Backend missing GOOGLE_CLIENT_ID. "
            "Test expects simplified OAuth naming but backend has no OAuth secrets. "
            "Available secrets: " + str(backend_all_secrets[:10]) + "..."
        )
        
        assert "GOOGLE_CLIENT_SECRET" in backend_all_secrets, (
            "BUG REPRODUCTION: Backend missing GOOGLE_CLIENT_SECRET. "
            "Test expects simplified OAuth naming but backend has no OAuth secrets."
        )
    
    def test_bug_reproduction_missing_gsm_mappings_for_simplified_names(self):
        """REPRODUCES BUG: GSM mappings missing for simplified OAuth names.
        
        Even if backend had simplified OAuth names, they wouldn't map to GSM secrets.
        """
        # Check if simplified OAuth names have GSM mappings
        client_id_mapping = SecretConfig.get_gsm_mapping("GOOGLE_CLIENT_ID")
        client_secret_mapping = SecretConfig.get_gsm_mapping("GOOGLE_CLIENT_SECRET")
        
        # These assertions will FAIL initially, demonstrating missing GSM mappings
        assert client_id_mapping is not None, (
            "BUG REPRODUCTION: GOOGLE_CLIENT_ID has no GSM mapping. "
            "Tests expect this to map to google-oauth-client-id-staging but mapping doesn't exist."
        )
        
        assert client_secret_mapping is not None, (
            "BUG REPRODUCTION: GOOGLE_CLIENT_SECRET has no GSM mapping. "
            "Tests expect this to map to google-oauth-client-secret-staging but mapping doesn't exist."
        )
        
        # If mappings exist, they should point to staging secrets
        if client_id_mapping:
            assert client_id_mapping == "google-oauth-client-id-staging", (
                f"GOOGLE_CLIENT_ID should map to google-oauth-client-id-staging, got: {client_id_mapping}"
            )
            
        if client_secret_mapping:
            assert client_secret_mapping == "google-oauth-client-secret-staging", (
                f"GOOGLE_CLIENT_SECRET should map to google-oauth-client-secret-staging, got: {client_secret_mapping}"
            )
    
    def test_bug_reproduction_oauth_architecture_inconsistency(self):
        """REPRODUCES BUG: OAuth architecture inconsistency between services.
        
        Auth service has OAuth configuration but backend doesn't, yet tests expect both.
        This reveals the architectural disconnect.
        """
        auth_secrets = SecretConfig.get_service_secrets("auth")
        backend_secrets = SecretConfig.get_service_secrets("backend")
        
        # Auth service should have OAuth (this should PASS)
        assert "oauth" in auth_secrets, (
            "Auth service should have OAuth configuration"
        )
        
        auth_oauth_secrets = auth_secrets["oauth"]
        assert "GOOGLE_OAUTH_CLIENT_ID_STAGING" in auth_oauth_secrets, (
            "Auth service should have environment-specific OAuth client ID"
        )
        
        # Backend service should also have OAuth category (this will FAIL, showing the bug)
        assert "oauth" in backend_secrets, (
            "BUG REPRODUCTION: Backend service missing OAuth category. "
            "Architecture inconsistency: Auth has OAuth but backend doesn't. "
            "This creates unclear OAuth handling responsibilities."
        )
    
    def test_bug_reproduction_dual_naming_convention_expectations(self):
        """REPRODUCES BUG: Tests expect different naming conventions per service.
        
        This test shows the expected dual naming pattern:
        - Auth service: Environment-specific names (GOOGLE_OAUTH_CLIENT_ID_STAGING)
        - Backend service: Simplified names (GOOGLE_CLIENT_ID)
        
        Both should map to the same underlying GSM secrets.
        """
        # Get all secrets for both services
        auth_all_secrets = SecretConfig.get_all_service_secrets("auth")
        backend_all_secrets = SecretConfig.get_all_service_secrets("backend")
        
        # Auth service should have environment-specific OAuth names (should PASS)
        assert "GOOGLE_OAUTH_CLIENT_ID_STAGING" in auth_all_secrets, (
            "Auth service should have environment-specific OAuth client ID"
        )
        assert "GOOGLE_OAUTH_CLIENT_SECRET_STAGING" in auth_all_secrets, (
            "Auth service should have environment-specific OAuth client secret"
        )
        
        # Backend service should have simplified OAuth names (will FAIL, showing bug)
        assert "GOOGLE_CLIENT_ID" in backend_all_secrets, (
            "BUG REPRODUCTION: Backend service should have simplified OAuth client ID. "
            "Dual naming convention not implemented."
        )
        assert "GOOGLE_CLIENT_SECRET" in backend_all_secrets, (
            "BUG REPRODUCTION: Backend service should have simplified OAuth client secret. "
            "Dual naming convention not implemented."
        )
        
        # Both should NOT use the other's naming convention
        assert "GOOGLE_CLIENT_ID" not in auth_all_secrets, (
            "Auth service should NOT use simplified OAuth names (correct as-is)"
        )
        assert "GOOGLE_OAUTH_CLIENT_ID_STAGING" not in backend_all_secrets, (
            "Backend service should NOT use environment-specific OAuth names (will FAIL due to missing OAuth entirely)"
        )
    
    def test_bug_reproduction_secrets_string_generation_fails_for_oauth(self):
        """REPRODUCES BUG: Backend secrets string missing OAuth mappings.
        
        When generating deployment secrets string, backend will be missing OAuth
        configuration that tests expect.
        """
        backend_secrets_string = SecretConfig.generate_secrets_string("backend", "staging")
        
        # Backend secrets string should contain OAuth mappings (will FAIL)
        assert "GOOGLE_CLIENT_ID=" in backend_secrets_string, (
            "BUG REPRODUCTION: Backend deployment string missing OAuth client ID. "
            f"Generated string: {backend_secrets_string[:200]}..."
        )
        
        assert "GOOGLE_CLIENT_SECRET=" in backend_secrets_string, (
            "BUG REPRODUCTION: Backend deployment string missing OAuth client secret. "
            "OAuth configuration completely absent from backend deployment."
        )
    
    def test_bug_reproduction_critical_secrets_validation_oauth_missing(self):
        """Shows OAuth secrets are not marked as critical despite test expectations.
        
        If OAuth is expected by tests but not marked critical, deployment validation
        won't catch missing OAuth configuration.
        """
        backend_critical = SecretConfig.CRITICAL_SECRETS.get("backend", [])
        
        # OAuth secrets may or may not be critical, but their absence should be detectable
        # This test documents current state for analysis
        oauth_in_critical = any("OAUTH" in secret or "CLIENT_ID" in secret or "CLIENT_SECRET" in secret 
                               for secret in backend_critical)
        
        # Document the current state (this assertion designed to show current state)
        print(f"\nOAuth secrets in backend critical list: {oauth_in_critical}")
        print(f"Backend critical secrets: {backend_critical}")
        
        # If tests expect OAuth, there should be some OAuth-related critical secrets
        # This will vary based on architectural decision
        # For now, just document what we find
        
    def test_complete_oauth_bug_summary(self):
        """Complete summary of all OAuth configuration issues found.
        
        This test aggregates all the OAuth bugs into one comprehensive view.
        """
        issues_found = []
        
        # Check backend OAuth category
        backend_secrets = SecretConfig.get_service_secrets("backend")
        if "oauth" not in backend_secrets:
            issues_found.append("Backend service missing oauth category")
        
        # Check backend OAuth secrets
        backend_all_secrets = SecretConfig.get_all_service_secrets("backend")
        if "GOOGLE_CLIENT_ID" not in backend_all_secrets:
            issues_found.append("Backend missing GOOGLE_CLIENT_ID")
        if "GOOGLE_CLIENT_SECRET" not in backend_all_secrets:
            issues_found.append("Backend missing GOOGLE_CLIENT_SECRET")
        
        # Check GSM mappings
        if SecretConfig.get_gsm_mapping("GOOGLE_CLIENT_ID") is None:
            issues_found.append("Missing GSM mapping for GOOGLE_CLIENT_ID")
        if SecretConfig.get_gsm_mapping("GOOGLE_CLIENT_SECRET") is None:
            issues_found.append("Missing GSM mapping for GOOGLE_CLIENT_SECRET")
        
        # This assertion will FAIL initially with complete bug summary
        assert len(issues_found) == 0, (
            "BUG REPRODUCTION COMPLETE - Found OAuth configuration issues:\n" +
            "\n".join(f"  - {issue}" for issue in issues_found) +
            "\n\nThese issues cause test failures in staging deployment regression tests."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])