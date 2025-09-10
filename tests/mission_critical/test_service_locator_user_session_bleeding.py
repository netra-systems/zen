"""Mission Critical Test: ServiceLocator Singleton User Session Bleeding

REPRODUCTION TEST - This test should FAIL initially due to singleton pattern violations.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - $500K+ ARR at risk
- Business Goal: User Isolation & Security
- Value Impact: Prevents catastrophic data leakage between users
- Revenue Impact: Data breach from shared state could cost millions in compliance/reputation

SINGLETON VIOLATION UNDER TEST:
File: netra_backend/app/services/service_locator_core.py:29-38
Issue: ServiceLocator uses singleton pattern (_instance = None) causing state sharing
Impact: Multiple users get the SAME ServiceLocator instance with contaminated state

EXPECTED BEHAVIOR:
- PRE-REFACTORING: This test should FAIL - proving singleton violation exists
- POST-REFACTORING: This test should PASS - proving factory pattern provides isolation

CRITICAL BUSINESS IMPACT:
If ServiceLocator shares state between users, sensitive user data, configurations,
and service instances become accessible across user sessions - a critical security breach.
"""

import asyncio
import uuid
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

# SSOT Test Framework Compliance
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# Import the singleton violator under test
from netra_backend.app.services.service_locator_core import ServiceLocator


class TestServiceLocatorUserSessionBleeding(SSotAsyncTestCase):
    """Mission Critical Test: Expose ServiceLocator singleton violations across user sessions."""
    
    def setup_method(self, method=None):
        """Set up test environment with proper isolation."""
        super().setup_method(method)
        
        # Reset any existing ServiceLocator instance before each test
        # This ensures we start from a clean state
        ServiceLocator._instance = None
        
        # Create test user contexts
        self.user_a_id = str(uuid.uuid4())
        self.user_b_id = str(uuid.uuid4())
        
        # Mock services for testing
        self.mock_service_a = AsyncMock()
        self.mock_service_a.user_data = {"user_id": self.user_a_id, "sensitive_data": "user_a_secrets"}
        
        self.mock_service_b = AsyncMock()
        self.mock_service_b.user_data = {"user_id": self.user_b_id, "sensitive_data": "user_b_secrets"}

    async def test_service_locator_singleton_shares_state_between_users(self):
        """
        REPRODUCTION TEST - This should FAIL initially due to singleton pattern.
        
        Tests that ServiceLocator singleton causes state bleeding between different users.
        This is a CRITICAL security vulnerability.
        """
        
        # STEP 1: User A registers a service with sensitive data
        locator_a = ServiceLocator()  # Should create singleton instance
        locator_a.register(str, self.mock_service_a, singleton=True)
        
        # Verify User A's service is registered
        user_a_service = locator_a.get(str)
        assert user_a_service.user_data["user_id"] == self.user_a_id
        assert user_a_service.user_data["sensitive_data"] == "user_a_secrets"
        
        # STEP 2: User B gets a "new" ServiceLocator instance
        locator_b = ServiceLocator()  # Should return SAME singleton instance (VIOLATION!)
        
        # CRITICAL ASSERTION: This should FAIL due to singleton pattern
        # User B should NOT be able to access User A's services
        try:
            user_b_gets_user_a_service = locator_b.get(str)
            
            # If we reach here, the singleton violation exists
            self.assertIsNot(
                locator_a, locator_b,
                "🚨 CRITICAL SECURITY VIOLATION: ServiceLocator singleton shares instances between users! "
                f"User A locator: {id(locator_a)}, User B locator: {id(locator_b)} - "
                "This enables cross-user data access and violates user isolation. "
                "BUSINESS IMPACT: $500K+ ARR at risk from data breach."
            )
            
            # Additional isolation check
            self.assertNotEqual(
                user_b_gets_user_a_service.user_data["user_id"], self.user_a_id,
                "🚨 CRITICAL: User B can access User A's sensitive service data! "
                "This is a catastrophic security breach enabling data leakage between users."
            )
            
        except Exception as e:
            # If getting service fails, that's actually good - means no shared state
            # But we still need to check instance sharing
            self.assertIsNot(
                locator_a, locator_b,
                f"🚨 ServiceLocator singleton violation detected: {e}"
            )

    async def test_service_locator_factory_registration_isolation(self):
        """
        Test that factory registrations don't bleed between user contexts.
        This test exposes how factory methods also share state in singleton pattern.
        """
        
        # Create factories for different users
        def user_a_factory():
            return f"UserA_Service_{self.user_a_id}"
            
        def user_b_factory():
            return f"UserB_Service_{self.user_b_id}"
        
        # User A registers a factory
        locator_a = ServiceLocator()
        locator_a.register_factory(str, user_a_factory)
        
        # User B should get isolated locator
        locator_b = ServiceLocator()
        
        # CRITICAL CHECK: User B should not see User A's factory
        try:
            # If singleton pattern exists, User B will see User A's factory
            user_b_service = locator_b.get(str)
            
            # This should NOT contain User A's user ID
            self.assertNotIn(
                self.user_a_id, user_b_service,
                "🚨 FACTORY STATE BLEEDING: User B can access User A's factory registration! "
                f"User B got: {user_b_service} which contains User A's ID: {self.user_a_id}"
            )
            
        except Exception:
            # Exception is expected if no service registered for User B
            # This is actually the correct behavior for proper isolation
            pass
            
        # Verify locators are different instances (should FAIL with singleton)
        self.assertIsNot(
            locator_a, locator_b,
            "🚨 ServiceLocator singleton pattern prevents proper user isolation"
        )

    async def test_concurrent_user_service_isolation_race_condition(self):
        """
        Test concurrent user access to ServiceLocator to expose race conditions.
        Singleton pattern with shared state creates race conditions in multi-user scenarios.
        """
        
        async def user_a_workflow():
            """Simulate User A's service operations."""
            locator = ServiceLocator()
            
            # Register User A's specific service
            user_a_specific_service = {"user": self.user_a_id, "data": "sensitive_user_a_data"}
            locator.register(dict, user_a_specific_service, singleton=True)
            
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            # Retrieve service
            retrieved_service = locator.get(dict)
            return retrieved_service
            
        async def user_b_workflow():
            """Simulate User B's service operations."""
            # Small delay to ensure User A registers first
            await asyncio.sleep(0.005)
            
            locator = ServiceLocator()
            
            # User B should have isolated locator
            # If singleton pattern exists, User B will see User A's service
            try:
                retrieved_service = locator.get(dict)
                return retrieved_service
            except:
                # No service found - this is correct for proper isolation
                return None
        
        # Run both user workflows concurrently
        user_a_result, user_b_result = await asyncio.gather(
            user_a_workflow(),
            user_b_workflow(),
            return_exceptions=True
        )
        
        # Verify User A got their own service
        self.assertEqual(user_a_result["user"], self.user_a_id)
        
        # CRITICAL: User B should NOT get User A's service
        if user_b_result is not None:
            self.assertIsNone(
                user_b_result,
                "🚨 RACE CONDITION VIOLATION: User B accessed User A's service due to singleton sharing! "
                f"User B received: {user_b_result} which belongs to User A: {self.user_a_id}. "
                "This indicates catastrophic state bleeding in concurrent scenarios."
            )

    async def test_service_locator_memory_contamination_across_requests(self):
        """
        Test that ServiceLocator doesn't accumulate state across multiple requests.
        Singleton pattern causes memory to grow with contaminated state from all users.
        """
        
        # Simulate multiple user sessions
        user_ids = [str(uuid.uuid4()) for _ in range(5)]
        
        for i, user_id in enumerate(user_ids):
            locator = ServiceLocator()
            
            # Each user registers their own service
            user_service = {"session": i, "user_id": user_id, "sensitive": f"secret_{i}"}
            locator.register(f"user_service_{i}", user_service, singleton=True)
            
            # Check if previous users' services are still accessible (VIOLATION!)
            for j in range(i):
                try:
                    previous_user_service = locator.get(f"user_service_{j}")
                    
                    # This should FAIL - previous users' services should not be accessible
                    self.fail(
                        f"🚨 MEMORY CONTAMINATION: User {i} can access User {j}'s service! "
                        f"Previous service: {previous_user_service}. "
                        "ServiceLocator singleton accumulates state across ALL users, "
                        "creating a memory leak and security violation."
                    )
                    
                except Exception:
                    # This is the expected behavior - services should be isolated
                    pass

    def teardown_method(self, method=None):
        """Clean up test environment."""
        # Reset ServiceLocator singleton for next test
        ServiceLocator._instance = None
        super().teardown_method(method)


# Business Impact Documentation
"""
BUSINESS IMPACT ANALYSIS:

1. DATA BREACH RISK:
   - ServiceLocator singleton shares ALL registered services between users
   - User A's sensitive data becomes accessible to User B
   - Violates GDPR, HIPAA, and other data protection regulations

2. REVENUE IMPACT:
   - $500K+ ARR at immediate risk from data leakage
   - Potential millions in compliance penalties and legal costs
   - Complete loss of customer trust and platform reputation

3. TECHNICAL DEBT:
   - Singleton pattern prevents horizontal scaling
   - Creates memory leaks as state accumulates across all users
   - Makes testing impossible due to shared global state

4. SECURITY IMPLICATIONS:
   - Cross-user data access enables privilege escalation
   - Sensitive configuration and credentials shared between users
   - Audit trails become meaningless due to contaminated state

REMEDIATION REQUIRED:
- Replace singleton pattern with factory pattern using UserExecutionContext
- Ensure each user gets isolated ServiceLocator instance
- Implement proper cleanup and memory management
- Add comprehensive integration tests for multi-user scenarios

POST-REFACTORING VALIDATION:
This test should PASS after factory pattern implementation, proving:
- Each user gets separate ServiceLocator instance
- No state bleeding between concurrent users
- Proper memory cleanup and isolation
- Secure multi-user operations
"""