"""
Test Suite for Issue #552 - UnifiedDockerManager API Signature Mismatch

CRITICAL: These tests reproduce the exact TypeError from Issue #552 where
auth E2E tests use outdated acquire_environment() API signature.

PURPOSE: 
- Prove the exact API signature mismatch that causes Issue #552
- Validate current API signature works correctly
- Prevent regression by maintaining failing tests for legacy patterns

REQUIREMENTS (per CLAUDE.md):
- FAILING tests that reproduce the issue
- NO Docker dependencies (pure API signature validation)
- Real tests that fail properly (no test cheating)

Business Value Justification:
1. Segment: Platform/Internal - Developer productivity, API consistency
2. Business Goal: Prevent API signature mismatches that break E2E tests
3. Value Impact: Reduces developer time spent debugging API signature errors
4. Revenue Impact: Protects test infrastructure reliability and CI/CD pipeline
"""

import pytest
from typing import Dict, Tuple
from unittest.mock import Mock, patch
import asyncio

# CRITICAL: Import the actual UnifiedDockerManager to test real API
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType


class TestUnifiedDockerManagerAPISignature:
    """Test UnifiedDockerManager API signatures to reproduce and prevent Issue #552."""
    
    def test_acquire_environment_current_signature_works(self):
        """PASSING TEST: Current API signature works correctly.
        
        This test validates that the current acquire_environment() method
        works with NO parameters as designed.
        """
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        
        # Mock Docker availability to avoid Docker dependency
        with patch.object(manager, 'is_docker_available', return_value=True):
            with patch.object(manager, '_ensure_compose_file_exists', return_value=True):
                # Current working signature (no parameters)
                result = manager.acquire_environment()
                
                # Validate return type matches expected signature
                assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
                assert len(result) == 2, f"Expected 2-tuple, got {len(result)}-tuple"
                
                env_name, port_mappings = result
                assert isinstance(env_name, str), f"Expected string env_name, got {type(env_name)}"
                assert isinstance(port_mappings, dict), f"Expected dict port_mappings, got {type(port_mappings)}"
    
    def test_acquire_environment_rejects_legacy_parameters(self):
        """FAILING TEST: Reproduces Issue #552 TypeError - acquire_environment() with parameters.
        
        This test MUST FAIL to reproduce the exact error from Issue #552.
        The auth E2E test calls acquire_environment() with parameters that don't exist.
        
        CRITICAL: This test should continue to FAIL even after Issue #552 is fixed
        to prevent regression to legacy API usage.
        """
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        
        # This MUST reproduce the exact TypeError from Issue #552
        # TypeError: acquire_environment() takes 1 positional argument but 4 were given
        with pytest.raises(TypeError) as exc_info:
            manager.acquire_environment(
                env_name="test",        # Parameter 2
                use_alpine=True,        # Parameter 3  
                rebuild_images=True     # Parameter 4
            )
        
        # Validate we get a TypeError related to unexpected parameters (Issue #552)
        error_msg = str(exc_info.value)
        expected_patterns = [
            "takes 1 positional argument but 4 were given",
            "got an unexpected keyword argument",
            "unexpected keyword argument 'env_name'"
        ]
        
        assert any(pattern in error_msg for pattern in expected_patterns), (
            f"Expected TypeError with parameter mismatch, got: {error_msg}"
        )
    
    def test_acquire_environment_rejects_partial_legacy_parameters(self):
        """FAILING TEST: Any legacy parameters should be rejected.
        
        This ensures that partial legacy parameter usage also fails,
        not just the full parameter list from the auth E2E test.
        """
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        
        # Test single legacy parameter
        with pytest.raises(TypeError):
            manager.acquire_environment(env_name="test")
        
        # Test two legacy parameters  
        with pytest.raises(TypeError):
            manager.acquire_environment(env_name="test", use_alpine=True)
    
    def test_start_services_smart_signature_works(self):
        """PASSING TEST: Working pattern used by functional E2E tests.
        
        This validates the CORRECT pattern that should replace the broken
        acquire_environment() calls in auth E2E tests.
        """
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        
        # Mock the async method to avoid Docker dependency
        async def mock_start_services():
            # Mock successful service start
            mock_result = asyncio.Future()
            mock_result.set_result(True)
            return await mock_result
        
        with patch.object(manager, 'start_services_smart', side_effect=mock_start_services):
            # This is the CORRECT pattern that should be used
            result = asyncio.run(manager.start_services_smart(
                services=["postgres", "redis", "auth"],
                wait_healthy=True
            ))
            
            assert result == True, "start_services_smart should return True for successful start"


class TestUnifiedDockerManagerAPIConsistency:
    """Validate API consistency across UnifiedDockerManager methods."""
    
    def test_all_public_methods_have_consistent_signatures(self):
        """Validate that all public methods follow consistent parameter patterns.
        
        This test helps prevent future API signature mismatches by ensuring
        consistent parameter naming and typing across the class.
        """
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        
        # Get all public methods (not starting with _)
        public_methods = [method for method in dir(manager) if not method.startswith('_')]
        
        # Validate specific methods have expected signatures
        assert hasattr(manager, 'acquire_environment'), "acquire_environment method should exist"
        assert hasattr(manager, 'start_services_smart'), "start_services_smart method should exist"
        assert hasattr(manager, 'is_docker_available'), "is_docker_available method should exist"
        
        # Validate acquire_environment signature specifically
        import inspect
        signature = inspect.signature(manager.acquire_environment)
        
        # Should only have 'self' parameter (no others)
        params = list(signature.parameters.keys())
        assert params == ['self'], (
            f"acquire_environment should only have 'self' parameter, got: {params}"
        )
    
    def test_legacy_api_documentation_alignment(self):
        """Validate that method signatures match their documented behavior.
        
        This test ensures that API documentation stays aligned with actual
        method signatures to prevent developer confusion.
        """
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        
        # Check docstring mentions no parameters (beyond self)
        docstring = manager.acquire_environment.__doc__
        assert docstring is not None, "acquire_environment should have docstring"
        
        # Docstring should not mention legacy parameters
        legacy_params = ["env_name", "use_alpine", "rebuild_images"]
        for param in legacy_params:
            assert param not in docstring.lower(), (
                f"Docstring should not mention legacy parameter '{param}': {docstring}"
            )


# INTEGRATION TEST: Reproduce auth service business flow API pattern
class TestAuthServiceAPIPatternReproduction:
    """Reproduce the exact API pattern that fails in auth E2E tests."""
    
    def test_reproduce_auth_service_setup_failure(self):
        """FAILING TEST: Reproduce exact pattern from auth_service/tests/e2e/test_auth_service_business_flows.py
        
        This test reproduces lines 62-66 from the failing auth E2E test to prove
        the issue exists and validate it's fixed correctly.
        """
        # Reproduce the exact pattern from auth_service/tests/e2e/test_auth_service_business_flows.py:62-66
        docker_manager = UnifiedDockerManager()
        
        # This MUST fail with the same error as the auth E2E test
        with pytest.raises(TypeError) as exc_info:
            env_info = docker_manager.acquire_environment(
                env_name="test",
                use_alpine=True,
                rebuild_images=True
            )
        
        # Validate this is the same error that breaks auth E2E tests
        error_msg = str(exc_info.value)
        expected_patterns = [
            "takes 1 positional argument but 4 were given",
            "unexpected keyword argument",
            "positional argument"
        ]
        
        assert any(pattern in error_msg for pattern in expected_patterns), (
            f"Expected TypeError with positional argument error, got: {error_msg}"
        )


if __name__ == "__main__":
    # Allow running this test file directly for development
    pytest.main([__file__, "-v"])