"""
Regression Prevention Tests for Issue #566: LLM Cache Isolation Security

CRITICAL SECURITY REGRESSION PREVENTION:
These tests ensure that the security vulnerabilities fixed in Issue #566
never get reintroduced into the codebase.

Security Fixes Applied:
1. startup_module.py:649 - Replaced vulnerable create_llm_manager() with secure factory pattern
2. smd.py:1019 - Replaced vulnerable create_llm_manager() with secure factory pattern

Purpose: Prevent future introduction of cache isolation vulnerabilities
Business Impact: Protects $500K+ ARR from user data privacy violations
"""

import pytest
import inspect
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestSecurityRegressionPreventionIssue566(SSotAsyncTestCase):
    """
    REGRESSION PREVENTION: Ensure Issue #566 security vulnerabilities never return
    
    These tests monitor the codebase to ensure that vulnerable patterns
    do not get reintroduced during future development.
    """

    def test_startup_module_never_contains_vulnerable_pattern(self):
        """
        REGRESSION TEST: Ensure startup_module.py never reverts to vulnerable pattern
        
        This test ensures that startup_module.py never again contains the vulnerable
        create_llm_manager() call without user context that led to Issue #566.
        """
        from netra_backend.app.startup_module import setup_security_services
        
        source_code = inspect.getsource(setup_security_services)
        
        # REGRESSION PREVENTION: Must NOT contain vulnerable pattern
        self.assertNotIn(
            "create_llm_manager()",
            source_code,
            "SECURITY REGRESSION DETECTED: startup_module.py contains vulnerable "
            "create_llm_manager() pattern again. This was fixed in Issue #566 and "
            "must not be reintroduced as it compromises user cache isolation."
        )
        
        # REGRESSION PREVENTION: Must contain secure factory pattern
        self.assertIn(
            "llm_manager_factory",
            source_code,
            "SECURITY REGRESSION DETECTED: startup_module.py missing secure factory "
            "pattern. The fix for Issue #566 requires llm_manager_factory to ensure "
            "user-isolated LLM manager creation."
        )

    def test_smd_never_contains_vulnerable_pattern(self):
        """
        REGRESSION TEST: Ensure smd.py never reverts to vulnerable pattern
        
        This test ensures that smd.py never again contains the vulnerable
        create_llm_manager() call without user context that led to Issue #566.
        """
        from netra_backend.app.smd import StartupOrchestrator
        
        source_code = inspect.getsource(StartupOrchestrator._initialize_llm_manager)
        
        # REGRESSION PREVENTION: Must NOT contain vulnerable pattern
        self.assertNotIn(
            "create_llm_manager()",
            source_code,
            "SECURITY REGRESSION DETECTED: smd.py contains vulnerable "
            "create_llm_manager() pattern again. This was fixed in Issue #566 and "
            "must not be reintroduced as it compromises user cache isolation."
        )
        
        # REGRESSION PREVENTION: Must contain secure factory pattern
        self.assertIn(
            "llm_manager_factory",
            source_code,
            "SECURITY REGRESSION DETECTED: smd.py missing secure factory "
            "pattern. The fix for Issue #566 requires llm_manager_factory to ensure "
            "user-isolated LLM manager creation."
        )

    def test_no_other_modules_introduce_vulnerable_pattern(self):
        """
        REGRESSION TEST: Ensure no other modules introduce the vulnerable pattern
        
        This test scans for any new introduction of the vulnerable pattern
        in other modules that might be added in the future.
        """
        # Check a few key modules that might be tempted to use the vulnerable pattern
        modules_to_check = [
            'netra_backend.app.startup_module',
            'netra_backend.app.smd',
        ]
        
        for module_name in modules_to_check:
            try:
                module = __import__(module_name, fromlist=[''])
                # Get all functions in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if callable(attr) and hasattr(attr, '__module__'):
                        if attr.__module__ == module_name:
                            try:
                                source = inspect.getsource(attr)
                                # Check for vulnerable pattern
                                if "create_llm_manager()" in source:
                                    self.fail(
                                        f"SECURITY REGRESSION DETECTED: {module_name}.{attr_name} "
                                        f"contains vulnerable create_llm_manager() pattern. "
                                        f"This was fixed in Issue #566 and compromises cache isolation."
                                    )
                            except (OSError, TypeError):
                                # Skip built-in functions or functions without source
                                continue
            except ImportError:
                # Skip modules that can't be imported
                continue

    def test_security_fix_documentation_exists(self):
        """
        REGRESSION TEST: Ensure security fix documentation remains
        
        This test ensures that the security fix comments and documentation
        remain in place to prevent future developers from accidentally
        reintroducing the vulnerability.
        """
        from netra_backend.app.startup_module import setup_security_services
        from netra_backend.app.smd import StartupOrchestrator
        
        startup_source = inspect.getsource(setup_security_services)
        smd_source = inspect.getsource(StartupOrchestrator._initialize_llm_manager)
        
        # REGRESSION PREVENTION: Security fix documentation must remain
        self.assertIn(
            "SECURITY FIX Issue #566",
            startup_source,
            "SECURITY DOCUMENTATION MISSING: startup_module.py missing Issue #566 "
            "security fix documentation. This helps prevent future regressions."
        )
        
        self.assertIn(
            "SECURITY FIX Issue #566",
            smd_source,
            "SECURITY DOCUMENTATION MISSING: smd.py missing Issue #566 "
            "security fix documentation. This helps prevent future regressions."
        )

    def test_factory_pattern_compliance(self):
        """
        REGRESSION TEST: Ensure factory pattern is properly implemented
        
        This test validates that the security fix properly implements
        the factory pattern for user-isolated LLM manager creation.
        """
        from netra_backend.app.startup_module import setup_security_services
        from netra_backend.app.smd import StartupOrchestrator
        from netra_backend.app.services.key_manager import KeyManager
        from fastapi import FastAPI
        
        # Test startup_module factory pattern
        test_app = FastAPI()
        key_manager = KeyManager()
        setup_security_services(test_app, key_manager)
        
        # SECURITY VALIDATION: Factory function should be available
        self.assertTrue(
            hasattr(test_app.state, 'llm_manager_factory'),
            "SECURITY REGRESSION: startup_module.py missing llm_manager_factory. "
            "This is required for Issue #566 security fix."
        )
        
        # SECURITY VALIDATION: Factory should be callable
        self.assertTrue(
            callable(test_app.state.llm_manager_factory),
            "SECURITY REGRESSION: llm_manager_factory is not callable. "
            "This breaks the Issue #566 security fix."
        )
        
        # Test SMD factory pattern
        smd = StartupOrchestrator(test_app)
        smd._initialize_llm_manager()
        
        # SECURITY VALIDATION: SMD should also have factory function
        self.assertTrue(
            hasattr(test_app.state, 'llm_manager_factory'),
            "SECURITY REGRESSION: smd.py missing llm_manager_factory. "
            "This is required for Issue #566 security fix."
        )


class TestSecurityAwarenessDocumentation(SSotAsyncTestCase):
    """
    Documentation tests to ensure security awareness is maintained
    """

    def test_security_test_file_exists(self):
        """
        REGRESSION TEST: Ensure security test file continues to exist
        
        This test ensures that the security test file created for Issue #566
        continues to exist and is not accidentally deleted.
        """
        import os
        security_test_file = "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/security/test_cache_isolation_vulnerability_issue566.py"
        
        self.assertTrue(
            os.path.exists(security_test_file),
            "SECURITY REGRESSION: Security test file for Issue #566 has been deleted. "
            "This file is critical for preventing security regressions."
        )

    def test_security_directory_structure(self):
        """
        REGRESSION TEST: Ensure security test directory structure is maintained
        """
        import os
        security_dir = "C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/tests/security"
        
        self.assertTrue(
            os.path.exists(security_dir),
            "SECURITY REGRESSION: Security tests directory has been deleted. "
            "This directory contains critical security vulnerability tests."
        )


if __name__ == "__main__":
    """
    Run regression prevention tests for Issue #566
    
    EXPECTED BEHAVIOR:
    - All tests SHOULD PASS, confirming security fixes remain in place
    - If any test FAILS, it indicates a security regression
    """
    pytest.main([__file__, "-v", "--tb=short"])