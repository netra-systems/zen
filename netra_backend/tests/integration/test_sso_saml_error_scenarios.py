"""
SSO/SAML Error Scenarios Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise ($200K+ MRR protection) 
- Business Goal: Error handling for enterprise authentication failures
- Value Impact: Prevents revenue loss from SSO/SAML edge cases
- Strategic Impact: Comprehensive error scenario coverage

Architecture Requirements: File ≤300 lines, Functions ≤8 lines
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import base64
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict

import pytest

# Add project root to path
from tests.sso_saml_components import (
    EnterpriseTokenManager,
    MockIdPErrorGenerator,
    # Add project root to path
    SAMLAssertionValidator,
)


@pytest.fixture
async def saml_validator():
    """SAML assertion validator fixture"""
    return SAMLAssertionValidator()


@pytest.fixture
async def token_manager():
    """Enterprise token manager fixture"""
    return EnterpriseTokenManager()


@pytest.fixture
async def enterprise_tenant_id():
    """Enterprise tenant ID fixture"""
    return "enterprise_tenant_12345"


@pytest.fixture
async def valid_saml_assertion():
    """Valid SAML assertion for testing"""
    assertion_data = {
        "issuer": "https://enterprise-idp.example.com",
        "subject": "admin@enterprise.com",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "attributes": {
            "enterprise_id": "ent_12345",
            "email": "admin@enterprise.com",
            "permissions": ["admin", "user"],
            "mfa_verified": True
        }
    }
    return base64.b64encode(json.dumps(assertion_data).encode()).decode()


@pytest.mark.asyncio  
class TestSSLSAMLErrorScenarios:
    """Test error scenarios and edge cases for SSO/SAML integration"""

    async def test_malformed_assertion_handling(self, saml_validator):
        """Test handling of malformed SAML assertions"""
        malformed_assertion = "invalid.base64.data"
        
        with pytest.raises((ValueError, json.JSONDecodeError)):
            await saml_validator.validate_saml_assertion(malformed_assertion)

    async def test_missing_enterprise_claims(self, saml_validator):
        """Test handling of SAML assertions missing enterprise claims"""
        minimal_assertion = await self._create_minimal_assertion()
        
        assertion = await saml_validator.validate_saml_assertion(minimal_assertion)
        claims = await saml_validator.extract_enterprise_claims(assertion)
        
        # Should provide defaults for missing claims
        await self._validate_default_claims(claims)

    async def _create_minimal_assertion(self):
        """Create SAML assertion with minimal claims"""
        minimal_assertion = {
            "issuer": "https://enterprise-idp.example.com",
            "subject": "user@enterprise.com",
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "attributes": {}  # Missing enterprise claims
        }
        
        return base64.b64encode(json.dumps(minimal_assertion).encode()).decode()

    async def _validate_default_claims(self, claims):
        """Validate default values for missing claims"""
        assert claims["enterprise_id"] is None
        assert claims["permissions"] == []
        assert claims["mfa_verified"] is False

    async def test_token_expiration_handling(self, token_manager, enterprise_tenant_id):
        """Test handling of expired JWT tokens"""
        # Create expired token manually
        expired_token_id = str(uuid.uuid4())
        expired_payload = await self._create_expired_token_payload(expired_token_id, enterprise_tenant_id)
        
        await self._store_expired_token(token_manager, enterprise_tenant_id, expired_token_id, expired_payload)
        
        # Attempt validation (should fail)
        validation_result = await token_manager.validate_jwt_with_tenant_check(expired_token_id, enterprise_tenant_id)
        assert validation_result is None

    async def _create_expired_token_payload(self, expired_token_id, enterprise_tenant_id):
        """Create expired JWT token payload"""
        return {
            "sub": "user@enterprise.com", 
            "tenant_id": enterprise_tenant_id,
            "permissions": ["user"],
            "auth_method": "saml_sso",
            "token_id": expired_token_id,
            "iat": int(time.time()) - 3600,
            "exp": int(time.time()) - 1  # Expired 1 second ago
        }

    async def _store_expired_token(self, token_manager, enterprise_tenant_id, expired_token_id, expired_payload):
        """Store expired token for testing"""
        if enterprise_tenant_id not in token_manager.tenant_tokens:
            token_manager.tenant_tokens[enterprise_tenant_id] = {}
        
        token_manager.tenant_tokens[enterprise_tenant_id][expired_token_id] = expired_payload

    async def test_concurrent_tenant_isolation(self, token_manager, saml_validator, valid_saml_assertion):
        """Test tenant isolation under concurrent access"""
        import asyncio
        
        tenants = [f"tenant_{i}" for i in range(5)]
        
        assertion = await saml_validator.validate_saml_assertion(valid_saml_assertion)
        claims = await saml_validator.extract_enterprise_claims(assertion)
        
        # Create tokens for multiple tenants concurrently
        tasks = [token_manager.exchange_saml_for_jwt(claims, tenant) for tenant in tenants]
        tokens = await asyncio.gather(*tasks)
        
        # Validate each token only works with its tenant
        await self._validate_concurrent_tenant_isolation(token_manager, tenants, tokens)

    async def _validate_concurrent_tenant_isolation(self, token_manager, tenants, tokens):
        """Validate tenant isolation across concurrent tokens"""
        for i, token in enumerate(tokens):
            correct_tenant = tenants[i]
            token_data = await token_manager.validate_jwt_with_tenant_check(token, correct_tenant)
            assert token_data is not None
            assert token_data["tenant_id"] == correct_tenant
            
            # Test cross-tenant validation fails
            wrong_tenant = tenants[(i + 1) % len(tenants)]
            cross_validation = await token_manager.validate_jwt_with_tenant_check(token, wrong_tenant)
            assert cross_validation is None

    async def test_invalid_issuer_rejection(self, saml_validator):
        """Test rejection of SAML assertions from invalid issuers"""
        invalid_assertion = await MockIdPErrorGenerator.create_invalid_assertion()
        
        with pytest.raises(ValueError, match="Invalid issuer"):
            await saml_validator.validate_saml_assertion(invalid_assertion)

    async def test_expired_assertion_rejection(self, saml_validator):
        """Test rejection of expired SAML assertions"""
        expired_assertion = await MockIdPErrorGenerator.create_expired_assertion()
        
        with pytest.raises(ValueError, match="Assertion expired"):
            await saml_validator.validate_saml_assertion(expired_assertion)

    async def test_empty_assertion_handling(self, saml_validator):
        """Test handling of empty SAML assertions"""
        empty_assertion = ""
        
        with pytest.raises(Exception):  # Should raise some form of error
            await saml_validator.validate_saml_assertion(empty_assertion)

    async def test_non_json_assertion_handling(self, saml_validator):
        """Test handling of non-JSON SAML assertions"""
        non_json_data = "not-json-data"
        non_json_assertion = base64.b64encode(non_json_data.encode()).decode()
        
        with pytest.raises(json.JSONDecodeError):
            await saml_validator.validate_saml_assertion(non_json_assertion)

    async def test_missing_required_fields(self, saml_validator):
        """Test handling of assertions missing required fields"""
        incomplete_assertion = {
            # Missing issuer
            "subject": "user@enterprise.com",
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "attributes": {}
        }
        
        assertion_data = base64.b64encode(json.dumps(incomplete_assertion).encode()).decode()
        
        with pytest.raises(KeyError):
            await saml_validator.validate_saml_assertion(assertion_data)

    async def test_invalid_tenant_access_patterns(self, token_manager, enterprise_tenant_id):
        """Test various invalid tenant access patterns"""
        # Test access with non-existent tenant
        non_existent_tenant = "non_existent_tenant"
        fake_token = str(uuid.uuid4())
        
        validation_result = await token_manager.validate_jwt_with_tenant_check(fake_token, non_existent_tenant)
        assert validation_result is None
        
        # Test access with empty tenant
        empty_tenant_validation = await token_manager.validate_jwt_with_tenant_check(fake_token, "")
        assert empty_tenant_validation is None
        
        # Test access with None tenant
        none_tenant_validation = await token_manager.validate_jwt_with_tenant_check(fake_token, None)
        assert none_tenant_validation is None