#!/usr/bin/env python3
"""
Issue #1278 Infrastructure Problems - Simple Validation Test

MISSION: Simple test to validate basic infrastructure connectivity
EXPECTED: Should FAIL - reproducing Issue #1278 problems
"""
import os
import pytest
import logging
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotBaseTestCase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestIssue1278SimpleValidation(SSotBaseTestCase):
    """Simple test to reproduce Issue #1278 problems"""
    
    def setup_method(self, method):
        """Set up each test method"""
        super().setup_method(method)
        logger.info(f"Setting up test method: {method.__name__}")
        
        # Issue #1278 reproduction: Environment management confusion
        try:
            # This should be the correct way but may fail
            self.env = IsolatedEnvironment()  # Singleton pattern
            logger.info(f"Environment initialized for: {self.env.get_env_var('ENVIRONMENT', 'unknown')}")
        except Exception as e:
            logger.error(f"Issue #1278 reproduction: Environment initialization failed - {e}")
            self.env = None
    
    def test_basic_environment_validation(self):
        """Test basic environment variable validation"""
        logger.info("Testing basic environment validation")
        
        try:
            # Check if environment is available
            if not self.env:
                raise AssertionError("Environment not available - Issue #1278 reproduction")
            
            # Test basic environment variables
            required_vars = [
                "DATABASE_URL",
                "BACKEND_URL", 
                "FRONTEND_URL"
            ]
            
            missing_vars = []
            for var in required_vars:
                value = self.env.get_env_var(var)
                if not value:
                    missing_vars.append(var)
                else:
                    logger.info(f"CHECK {var}: {value[:50]}...")
            
            if missing_vars:
                logger.error(f"X Missing environment variables: {missing_vars}")
                raise AssertionError(f"Issue #1278 reproduction: Missing vars - {missing_vars}")
            
            logger.info("CHECK Basic environment validation passed")
            
        except Exception as e:
            logger.error(f"X Basic environment validation failed: {e}")
            raise AssertionError(f"Issue #1278 reproduction: Environment validation failure - {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--log-cli-level=INFO"])