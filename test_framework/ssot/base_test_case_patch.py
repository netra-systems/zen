#!/usr/bin/env python3
"""
Patch script to add create_authenticated_test_user method to SSotBaseTestCase
for Issue #622 remediation.
"""

import re

def patch_base_test_case():
    """Add the missing method to base test case."""
    
    file_path = "test_framework/ssot/base_test_case.py"
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the insertion point - before the SSotAsyncTestCase class
    insertion_point = content.find("class SSotAsyncTestCase(SSotBaseTestCase):")
    
    if insertion_point == -1:
        raise ValueError("Could not find SSotAsyncTestCase class definition")
    
    # Method to insert
    method_code = '''
    # === E2E AUTHENTICATION SUPPORT ===
    
    async def create_authenticated_test_user(self, **kwargs):
        """
        Create authenticated test user for E2E tests.
        
        This method provides SSOT compatibility for E2E tests that need authenticated users.
        It delegates to the centralized E2EAuthHelper to ensure consistent authentication.
        
        Args:
            **kwargs: Additional arguments passed to E2EAuthHelper.create_authenticated_user()
                     Common options: name, email, permissions, environment
        
        Returns:
            AuthenticatedUser: Created user with JWT token and authentication data
            
        Example:
            user = await self.create_authenticated_test_user(
                name="Test User",
                email="test@example.com", 
                permissions=["read", "write"]
            )
        """
        try:
            from test_framework.ssot.e2e_auth_helper import create_authenticated_user
            return await create_authenticated_user(**kwargs)
        except ImportError as e:
            raise ImportError(
                f"E2E authentication helper not available: {e}. "
                f"Ensure test_framework.ssot.e2e_auth_helper is accessible."
            )


'''
    
    # Insert the method before the SSotAsyncTestCase class
    new_content = content[:insertion_point] + method_code + content[insertion_point:]
    
    # Write back to file
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print("✅ Successfully added create_authenticated_test_user method to SSotBaseTestCase")

if __name__ == "__main__":
    patch_base_test_case()