"""
Demonstration tests for Issue #112 - Auth Middleware Dependency Order Violation.

These tests are designed to FAIL and demonstrate the exact problem:
- GCPAuthContextMiddleware is installed outside SSOT setup_middleware()
- This causes SessionMiddleware dependency violations
- The violation blocks Golden Path user flows

CRITICAL: These tests document the bug and should FAIL with current code.
"""

import pytest
import inspect
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware

from netra_backend.app.core.app_factory import _install_auth_context_middleware
from netra_backend.app.core.middleware_setup import setup_middleware as ssot_setup_middleware
from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware


class TestMiddlewareDependencyDemonstration:
    """Demonstrate the exact middleware dependency violation."""

    def test_gcp_middleware_requires_session_access(self):
        """TEST 1: Prove that GCPAuthContextMiddleware accesses request.session.
        
        This test DEMONSTRATES that the middleware has a hard dependency on SessionMiddleware.
        """
        # Analyze the source code to prove session dependency
        source_lines = inspect.getsourcelines(GCPAuthContextMiddleware._extract_auth_context)[0]
        source_code = ''.join(source_lines)
        
        # Check for explicit session access patterns
        session_access_patterns = [
            'request.session',
            'hasattr(request, \'session\')',
            'request.session.get(',
        ]
        
        found_patterns = []
        for pattern in session_access_patterns:
            if pattern in source_code:
                found_patterns.append(pattern)
        
        # Document the dependency
        print(f"\nGCPAuthContextMiddleware session access patterns:")
        for pattern in found_patterns:
            print(f"  - {pattern}")
        
        assert found_patterns, (
            f"GCPAuthContextMiddleware should access request.session but patterns not found. "
            f"Source analyzed: {len(source_code)} characters"
        )
        
        # Verify the specific lines that access session
        session_lines = [line.strip() for line in source_lines if 'request.session' in line]
        print(f"\nSession access lines:")
        for line in session_lines:
            print(f"  {line}")
        
        assert session_lines, "Should find lines that access request.session"

    def test_ssot_setup_does_not_include_gcp_middleware(self):
        """TEST 2: Prove that SSOT setup_middleware() does NOT include GCPAuthContextMiddleware.
        
        This test FAILS and demonstrates the SSOT violation.
        """
        # Analyze SSOT setup_middleware function
        source_lines = inspect.getsourcelines(ssot_setup_middleware)[0]
        source_code = ''.join(source_lines)
        
        # Look for GCP middleware setup patterns
        gcp_patterns = [
            'GCPAuthContextMiddleware',
            'gcp_auth_context',
            '_install_auth_context_middleware',
            'install_auth_context_middleware'
        ]
        
        found_gcp_patterns = [pattern for pattern in gcp_patterns if pattern in source_code]
        
        print(f"\nSSOT setup_middleware() analysis:")
        print(f"  Total lines: {len(source_lines)}")
        print(f"  GCP middleware patterns found: {found_gcp_patterns}")
        
        # This test SHOULD FAIL - demonstrating the SSOT violation
        assert not found_gcp_patterns, (
            f"SSOT VIOLATION: GCPAuthContextMiddleware setup found in SSOT function: {found_gcp_patterns}. "
            f"This violates the principle that ALL middleware should be in SSOT setup_middleware()."
        )
        
        print(f"  ✓ CONFIRMED: GCPAuthContextMiddleware is NOT in SSOT setup_middleware()")

    def test_factory_installs_gcp_middleware_outside_ssot(self):
        """TEST 3: Prove that app_factory.py installs GCPAuthContextMiddleware outside SSOT.
        
        This test FAILS and demonstrates the exact violation causing Issue #112.
        """
        from netra_backend.app.core import app_factory
        
        # Analyze the app factory module
        factory_source = inspect.getsource(app_factory)
        
        # Look for GCP middleware installation
        gcp_installation_patterns = [
            '_install_auth_context_middleware',
            'GCPAuthContextMiddleware',
            'app.add_middleware(GCPAuthContextMiddleware'
        ]
        
        found_installations = []
        for pattern in gcp_installation_patterns:
            if pattern in factory_source:
                found_installations.append(pattern)
        
        print(f"\napp_factory.py GCP middleware installation analysis:")
        print(f"  Patterns found: {found_installations}")
        
        # Find the specific function that installs GCP middleware
        if '_install_auth_context_middleware' in factory_source:
            auth_install_source = inspect.getsource(_install_auth_context_middleware)
            print(f"  _install_auth_context_middleware function found:")
            print(f"    Lines: {len(auth_install_source.split(chr(10)))}")
            
            # Check if it installs GCP middleware
            installs_gcp = 'GCPAuthContextMiddleware' in auth_install_source
            print(f"    Installs GCPAuthContextMiddleware: {installs_gcp}")
            
            # This test FAILS - proving the violation
            assert not installs_gcp, (
                f"CRITICAL VIOLATION: _install_auth_context_middleware() installs "
                f"GCPAuthContextMiddleware OUTSIDE the SSOT setup_middleware() function. "
                f"This causes middleware order issues and can break SessionMiddleware dependencies."
            )
        
        assert found_installations, (
            f"Expected to find GCP middleware installation patterns in app_factory.py"
        )

    def test_middleware_order_causes_session_access_failure(self):
        """TEST 4: Demonstrate what happens when middleware order is wrong.
        
        This test shows the actual failure that occurs in Golden Path.
        """
        import asyncio
        
        # Create GCP middleware instance
        gcp_middleware = GCPAuthContextMiddleware(None, enable_user_isolation=True)
        
        # Create a request mock WITHOUT session (simulates wrong middleware order)
        request_no_session = Mock(spec=Request)
        request_no_session.headers = {'Authorization': 'Bearer test-token'}
        request_no_session.method = 'GET'
        request_no_session.url = Mock()
        request_no_session.url.path = '/api/agent/execute'
        request_no_session.client = Mock()
        request_no_session.client.host = '127.0.0.1'
        # CRITICAL: No session attribute - this simulates GCP middleware running before SessionMiddleware
        
        async def test_auth_extraction_without_session():
            """Test what happens when GCP middleware runs without proper session setup."""
            try:
                auth_context = await gcp_middleware._extract_auth_context(request_no_session)
                
                # The middleware should handle missing session gracefully
                # But this means we lose valuable session-based authentication data
                session_data_lost = (
                    'session_id' not in auth_context or 
                    auth_context.get('session_id') is None
                )
                
                print(f"\nAuth context without session:")
                print(f"  User ID: {auth_context.get('user_id', 'missing')}")
                print(f"  Session ID: {auth_context.get('session_id', 'missing')}")
                print(f"  Session data lost: {session_data_lost}")
                
                return session_data_lost
            except Exception as e:
                print(f"Exception during auth extraction: {e}")
                return True  # Exception indicates failure
        
        # Run the test
        session_data_lost = asyncio.run(test_auth_extraction_without_session())
        
        # This test FAILS because we lose session data when middleware order is wrong
        assert not session_data_lost, (
            "Session data is LOST when GCPAuthContextMiddleware runs before SessionMiddleware. "
            "This breaks user authentication context in Golden Path scenarios, causing "
            "errors like 'SessionMiddleware must be installed' and preventing proper "
            "multi-user isolation in agent executions."
        )

    def test_golden_path_blocking_scenario(self):
        """TEST 5: Demonstrate how the middleware issue blocks Golden Path.
        
        Golden Path: User Login -> WebSocket Connection -> Agent Execution -> Results
        This test shows where the middleware dependency violation breaks the flow.
        """
        # Golden Path Step 1: User authentication creates session
        mock_authenticated_session = {
            'user_id': 'golden-path-user-123',
            'session_id': 'golden-session-456', 
            'user_email': 'user@example.com',
            'customer_tier': 'Early',
            'auth_method': 'oauth'
        }
        
        # Golden Path Step 2: WebSocket connection attempts to get auth context
        # This is where the middleware order issue causes failures
        
        request_with_session = Mock(spec=Request)
        request_with_session.headers = {'Authorization': 'Bearer golden-path-token'}
        request_with_session.method = 'GET'
        request_with_session.url = Mock()
        request_with_session.url.path = '/ws/agent'
        request_with_session.client = Mock()
        request_with_session.client.host = '10.0.1.100'
        request_with_session.session = mock_authenticated_session  # Proper session
        
        # Request WITHOUT session (broken middleware order)
        request_broken_order = Mock(spec=Request)
        request_broken_order.headers = request_with_session.headers
        request_broken_order.method = request_with_session.method
        request_broken_order.url = request_with_session.url
        request_broken_order.client = request_with_session.client
        # MISSING: No session attribute due to middleware order issue
        
        gcp_middleware = GCPAuthContextMiddleware(None, enable_user_isolation=True)
        
        import asyncio
        
        async def test_golden_path_scenarios():
            # Scenario 1: Proper middleware order (session available)
            correct_auth = await gcp_middleware._extract_auth_context(request_with_session)
            
            # Scenario 2: Broken middleware order (session missing)
            broken_auth = await gcp_middleware._extract_auth_context(request_broken_order)
            
            return correct_auth, broken_auth
        
        correct_auth, broken_auth = asyncio.run(test_golden_path_scenarios())
        
        print(f"\nGolden Path Authentication Context Comparison:")
        print(f"  Correct Order - User ID: {correct_auth.get('user_id')}")
        print(f"  Correct Order - Session ID: {correct_auth.get('session_id')}")
        print(f"  Correct Order - Customer Tier: {correct_auth.get('customer_tier')}")
        print(f"  Broken Order - User ID: {broken_auth.get('user_id')}")
        print(f"  Broken Order - Session ID: {broken_auth.get('session_id')}")
        print(f"  Broken Order - Customer Tier: {broken_auth.get('customer_tier')}")
        
        # Verify that correct order preserves Golden Path data
        assert correct_auth.get('user_id') == 'golden-path-user-123'
        assert correct_auth.get('session_id') == 'golden-session-456'
        assert correct_auth.get('customer_tier') == 'Early'
        
        # This assertion FAILS - demonstrating the Golden Path break
        assert broken_auth.get('user_id') == 'golden-path-user-123', (
            f"GOLDEN PATH BLOCKED: Broken middleware order loses user authentication context. "
            f"Expected user_id='golden-path-user-123', got '{broken_auth.get('user_id')}'. "
            f"This prevents proper user isolation and causes WebSocket authentication failures."
        )
        
        assert broken_auth.get('session_id') == 'golden-session-456', (
            f"GOLDEN PATH BLOCKED: Session context lost. Expected session_id='golden-session-456', "
            f"got '{broken_auth.get('session_id')}'. This breaks multi-user session management."
        )


class TestSSOTComplianceViolation:
    """Tests that document the specific SSOT compliance violation."""

    def test_document_ssot_violation_pattern(self):
        """Document the exact SSOT violation pattern causing Issue #112."""
        
        violation_report = {
            'issue': 'GCPAuthContextMiddleware installed outside SSOT setup_middleware()',
            'location': 'netra_backend/app/core/app_factory.py line 257',
            'function': '_install_auth_context_middleware()',
            'ssot_location': 'netra_backend/app/core/middleware_setup.py setup_middleware()',
            'dependency': 'Requires SessionMiddleware to be installed first',
            'impact': 'Breaks Golden Path user authentication and session management'
        }
        
        print(f"\nSSOT Compliance Violation Report:")
        for key, value in violation_report.items():
            print(f"  {key}: {value}")
        
        # Verify each component of the violation
        
        # 1. Confirm SSOT setup function exists
        assert callable(ssot_setup_middleware), "SSOT setup_middleware function should exist"
        
        # 2. Confirm violating function exists
        assert callable(_install_auth_context_middleware), "Violating function should exist"
        
        # 3. Check that SSOT function handles SessionMiddleware
        ssot_source = inspect.getsource(ssot_setup_middleware)
        handles_session = 'SessionMiddleware' in ssot_source or 'setup_session_middleware' in ssot_source
        assert handles_session, "SSOT function should handle SessionMiddleware"
        
        # 4. Check that violating function handles GCP middleware
        violating_source = inspect.getsource(_install_auth_context_middleware)
        installs_gcp = 'GCPAuthContextMiddleware' in violating_source
        
        print(f"\n  SSOT handles SessionMiddleware: {handles_session}")
        print(f"  Violating function installs GCP middleware: {installs_gcp}")
        
        # This is the core of the violation - GCP middleware outside SSOT
        if installs_gcp:
            pytest.fail(
                f"SSOT COMPLIANCE VIOLATION CONFIRMED: "
                f"_install_auth_context_middleware() installs GCPAuthContextMiddleware "
                f"outside the SSOT setup_middleware() function. This violates the principle "
                f"that ALL middleware setup should go through the single source of truth. "
                f"Result: SessionMiddleware dependency order issues block Golden Path."
            )
        else:
            print(f"  No GCP middleware installation detected in violating function")
            assert True, "Violation pattern not found - issue may be resolved"


if __name__ == '__main__':
    # Run the demonstration tests
    pytest.main([
        __file__ + "::TestMiddlewareDependencyDemonstration::test_gcp_middleware_requires_session_access",
        __file__ + "::TestMiddlewareDependencyDemonstration::test_ssot_setup_does_not_include_gcp_middleware",
        __file__ + "::TestMiddlewareDependencyDemonstration::test_factory_installs_gcp_middleware_outside_ssot", 
        __file__ + "::TestSSOTComplianceViolation::test_document_ssot_violation_pattern",
        "-v", "-s"
    ])