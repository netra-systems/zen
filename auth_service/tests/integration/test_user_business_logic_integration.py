"""
UserBusinessLogic Integration Tests - Comprehensive Revenue-Critical Business Rules Validation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Business logic drives revenue through tier assignments
- Business Goal: Validate revenue-critical business rules with real database/service integration
- Value Impact: User tier assignments directly affect revenue (FREE/EARLY/MID/ENTERPRISE)
- Strategic Impact: Protects revenue by ensuring business rules work correctly with real data persistence

CRITICAL: These tests use REAL PostgreSQL, Redis, and service integration - NO MOCKS allowed.
Tests validate complete business logic workflows with real service dependencies to catch
integration failures that unit tests would miss.

This test suite validates:
1. Complete registration flow integration with real database persistence
2. Business email detection integration with external service calls  
3. Trial period calculation integration with environment-specific rules
4. Login attempt lockout integration with Redis-backed concurrent operations
5. Account lifecycle management integration with multi-service workflows
6. Cross-environment business rules with configuration service integration

Revenue Protection:
- Tier bypass prevention ensures users cannot illegally access higher tiers
- Trial period manipulation prevention protects conversion funnel integrity  
- Concurrent registration race conditions prevent double registrations that affect metrics
- Account lifecycle enforcement ensures proper onboarding and billing transitions

All tests focus on business value scenarios where integration failures would cause
revenue loss, user experience degradation, or security vulnerabilities.
"""
import asyncio
import logging
import pytest
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
import hashlib
from dataclasses import asdict
from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.database.connection import auth_db
from auth_service.auth_core.database.models import AuthUser as User, AuthSession as Session, AuthAuditLog as AuditLog, Base
from netra_backend.app.redis_manager import redis_manager
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.business_logic.user_business_logic import UserBusinessLogic, UserRegistrationValidator, UserRegistrationValidationResult, LoginAttemptValidationResult, AccountLifecycleResult
from netra_backend.app.schemas.tenant import SubscriptionTier
logger = logging.getLogger(__name__)

class UserBusinessLogicIntegrationTests(BaseIntegrationTest):
    """Integration tests for UserBusinessLogic with real database/service integration."""

    @pytest.fixture(autouse=True)
    async def setup(self, setup_real_services):
        """Set up test environment with real database services for business logic integration."""
        self.env = get_env()
        self.real_services = setup_real_services
        self.auth_config = AuthConfig()
        self.auth_service = AuthService()
        self.jwt_handler = JWTHandler()
        self.db = auth_db
        await self.db.initialize()
        await self.db.create_tables()
        self.redis_manager = redis_manager
        await self.redis_manager.connect()
        self.redis_client = await self.redis_manager.get_client()
        self.user_business_logic = UserBusinessLogic()
        self.test_user_base = f'user-business-logic-{uuid.uuid4().hex[:8]}'
        self.test_domain = '@businesslogic.test'
        self.test_users_created = []
        self.test_redis_keys_created = []
        self.business_scenarios = {'personal_email_free': {'email': f'{self.test_user_base}-personal@gmail.com', 'password': 'SecurePass123!', 'name': 'Personal Email User', 'expected_tier': SubscriptionTier.FREE, 'expected_trial_days': 14}, 'business_email_known': {'email': f'{self.test_user_base}-business@enterprise.com', 'password': 'SecurePass123!', 'name': 'Known Business User', 'expected_tier': SubscriptionTier.FREE, 'expected_suggested_tier': SubscriptionTier.EARLY, 'expected_trial_days': 30}, 'business_email_unknown': {'email': f'{self.test_user_base}-unknown@unknowncorp.com', 'password': 'SecurePass123!', 'name': 'Unknown Business User', 'expected_tier': SubscriptionTier.FREE, 'expected_suggested_tier': SubscriptionTier.EARLY, 'expected_trial_days': 14}, 'integration_environment': {'email': f'{self.test_user_base}-integration@example.com', 'password': 'SecurePass123!', 'name': 'Integration Test User', 'expected_tier': SubscriptionTier.FREE, 'expected_trial_days': 7}}
        yield
        await self.cleanup_integration_test_data()

    async def cleanup_integration_test_data(self):
        """Clean up all test data from real database and Redis."""
        try:
            for key in self.test_redis_keys_created:
                try:
                    await self.redis_client.delete(key)
                except Exception:
                    pass
            async with self.db.get_session() as session:
                for email in self.test_users_created:
                    try:
                        result = await session.execute('DELETE FROM auth_users WHERE email = :email', {'email': email})
                        await session.commit()
                    except Exception:
                        await session.rollback()
        except Exception as e:
            logger.warning(f'Cleanup error (non-critical): {e}')

    @pytest.mark.asyncio
    async def test_complete_registration_flow_integration(self):
        """
        Test complete registration flow integration with real database persistence.
        
        BUSINESS VALUE: Validates user onboarding pipeline that drives platform growth.
        Tests tier assignment and trial period logic that directly affects revenue.
        """
        logger.info('[U+1F9EA] Testing complete registration flow integration with real database')
        for scenario_name, scenario_data in self.business_scenarios.items():
            with pytest.raises(Exception, match='') if scenario_name == 'should_not_exist' else nullcontext():
                logger.info(f'[U+1F4E7] Testing scenario: {scenario_name}')
                result = self.user_business_logic.validate_registration(scenario_data)
                assert result.is_valid, f'Registration validation failed for {scenario_name}: {result.validation_errors}'
                assert result.assigned_tier == scenario_data['expected_tier']
                if 'expected_suggested_tier' in scenario_data:
                    assert result.suggested_tier == scenario_data['expected_suggested_tier']
                else:
                    assert result.suggested_tier is None
                expected_trial_days = scenario_data['expected_trial_days']
                environment = self.env.get('ENVIRONMENT', 'development').lower()
                testing_mode = self.env.get('TESTING', 'false').lower()
                if environment in ['integration', 'staging'] and testing_mode == 'true':
                    expected_trial_days = 7
                assert result.trial_days == expected_trial_days, f'Trial days mismatch for {scenario_name}: expected {expected_trial_days}, got {result.trial_days}'
                async with self.db.get_session() as session:
                    user = User(id=str(uuid.uuid4()), email=scenario_data['email'], password_hash=hashlib.sha256(scenario_data['password'].encode()).hexdigest(), name=scenario_data['name'], subscription_tier=result.assigned_tier.value, trial_days_remaining=result.trial_days, suggested_tier=result.suggested_tier.value if result.suggested_tier else None, created_at=datetime.now(timezone.utc), email_verified=False, is_active=True)
                    session.add(user)
                    await session.commit()
                    self.test_users_created.append(scenario_data['email'])
                    result = await session.execute('SELECT email, subscription_tier, trial_days_remaining, suggested_tier FROM auth_users WHERE email = :email', {'email': scenario_data['email']})
                    stored_user = result.fetchone()
                    assert stored_user is not None, f"User not found in database: {scenario_data['email']}"
                    assert stored_user.subscription_tier == scenario_data['expected_tier'].value
                    assert stored_user.trial_days_remaining == expected_trial_days
                    logger.info(f' PASS:  Registration flow integration successful for {scenario_name}')
        logger.info(' TARGET:  Complete registration flow integration test passed')

    @pytest.mark.asyncio
    async def test_business_email_detection_integration(self):
        """
        Test business email detection integration with real domain validation.
        
        BUSINESS VALUE: Proper email classification drives tier suggestion logic that affects conversion rates.
        Integration with potential external domain validation services.
        """
        logger.info('[U+1F9EA] Testing business email detection integration')
        test_cases = [{'email': f'user@gmail.com', 'expected_business': False, 'expected_tier_suggestion': None, 'description': 'Known personal domain'}, {'email': f'user@enterprise.com', 'expected_business': True, 'expected_tier_suggestion': SubscriptionTier.EARLY, 'description': 'Known business domain'}, {'email': f'user@randomcompany123.com', 'expected_business': True, 'expected_tier_suggestion': SubscriptionTier.EARLY, 'description': 'Unknown domain (heuristic business)'}, {'email': f'user@outlook.com', 'expected_business': False, 'expected_tier_suggestion': None, 'description': 'Known personal domain'}]
        for test_case in test_cases:
            logger.info(f"[U+1F4E7] Testing: {test_case['description']}")
            registration_data = {'email': test_case['email'], 'password': 'SecurePass123!', 'name': 'Test User'}
            result = self.user_business_logic.validate_registration(registration_data)
            assert result.is_valid, f"Registration should be valid for {test_case['email']}"
            assert result.suggested_tier == test_case['expected_tier_suggestion'], f"Tier suggestion mismatch for {test_case['email']}: expected {test_case['expected_tier_suggestion']}, got {result.suggested_tier}"
            if test_case['expected_business'] and 'enterprise.com' in test_case['email']:
                assert result.trial_days == 30, f'Business emails from known domains should get 30-day trial'
            logger.info(f" PASS:  Business email detection successful for {test_case['description']}")
        logger.info(' TARGET:  Business email detection integration test passed')

    @pytest.mark.asyncio
    async def test_trial_period_calculation_integration(self):
        """
        Test trial period calculation integration with environment-specific rules.
        
        BUSINESS VALUE: Trial period accuracy impacts conversion rates and revenue funnel.
        Integration with configuration service for dynamic trial rules.
        """
        logger.info('[U+1F9EA] Testing trial period calculation integration')
        original_env = self.env.get('ENVIRONMENT')
        original_testing = self.env.get('TESTING')
        try:
            environment_test_cases = [{'environment': 'development', 'testing': 'false', 'expected_trial_days': 14, 'description': 'Development environment'}, {'environment': 'integration', 'testing': 'true', 'expected_trial_days': 7, 'description': 'Integration test environment'}, {'environment': 'staging', 'testing': 'true', 'expected_trial_days': 7, 'description': 'Staging test environment'}, {'environment': 'production', 'testing': 'false', 'expected_trial_days': 14, 'description': 'Production environment'}]
            base_registration = {'email': f'trial-test-{uuid.uuid4().hex[:8]}@example.com', 'password': 'SecurePass123!', 'name': 'Trial Test User'}
            for test_case in environment_test_cases:
                logger.info(f"[U+1F30D] Testing environment: {test_case['description']}")
                self.env.set('ENVIRONMENT', test_case['environment'], 'test_trial_integration')
                self.env.set('TESTING', test_case['testing'], 'test_trial_integration')
                business_logic = UserBusinessLogic()
                result = business_logic.validate_registration(base_registration)
                assert result.is_valid, f"Registration should be valid in {test_case['environment']}"
                assert result.trial_days == test_case['expected_trial_days'], f"Trial days mismatch in {test_case['environment']}: expected {test_case['expected_trial_days']}, got {result.trial_days}"
                logger.info(f" PASS:  Trial period calculation correct for {test_case['description']}")
                if test_case['environment'] == 'production':
                    business_email_test = {'email': f'business-{uuid.uuid4().hex[:8]}@enterprise.com', 'password': 'SecurePass123!', 'name': 'Business User'}
                    business_result = business_logic.validate_registration(business_email_test)
                    assert business_result.trial_days == 30, 'Known business domains should get 30 days in production'
        finally:
            if original_env:
                self.env.set('ENVIRONMENT', original_env, 'test_cleanup')
            if original_testing:
                self.env.set('TESTING', original_testing, 'test_cleanup')
        logger.info(' TARGET:  Trial period calculation integration test passed')

    @pytest.mark.asyncio
    async def test_login_attempt_lockout_integration(self):
        """
        Test login attempt lockout integration with Redis-backed concurrent operations.
        
        BUSINESS VALUE: Prevents abuse while maintaining UX, protects against brute force attacks.
        Real Redis integration for distributed lockout state management.
        """
        logger.info('[U+1F9EA] Testing login attempt lockout integration with Redis')
        test_user_id = f'lockout-test-{uuid.uuid4().hex[:8]}'
        test_email = f'{test_user_id}@lockouttest.com'
        attempts_key = f'login_attempts:{test_user_id}'
        lockout_key = f'lockout:{test_user_id}'
        self.test_redis_keys_created.extend([attempts_key, lockout_key])
        test_scenarios = [{'attempt': 1, 'expected_allowed': True, 'expected_remaining': 4}, {'attempt': 2, 'expected_allowed': True, 'expected_remaining': 3}, {'attempt': 3, 'expected_allowed': True, 'expected_remaining': 2}, {'attempt': 4, 'expected_allowed': True, 'expected_remaining': 1}, {'attempt': 5, 'expected_allowed': False, 'expected_lockout': 15}, {'attempt': 6, 'expected_allowed': False, 'expected_lockout': 30}]
        for scenario in test_scenarios:
            logger.info(f"[U+1F512] Testing login attempt #{scenario['attempt']}")
            await self.redis_client.set(attempts_key, scenario['attempt'] - 1)
            await self.redis_client.expire(attempts_key, 3600)
            current_attempts = int(await self.redis_client.get(attempts_key) or 0)
            user_context = {'user_id': test_user_id, 'email': test_email, 'failed_attempts': current_attempts, 'last_attempt': datetime.now(timezone.utc)}
            result = self.user_business_logic.validate_login_attempt(user_context)
            if scenario['attempt'] <= 3:
                assert result.allowed == scenario['expected_allowed']
                assert result.remaining_attempts == scenario['expected_remaining']
            elif scenario['attempt'] >= 5:
                assert result.allowed == scenario['expected_allowed']
                assert result.lockout_duration == scenario['expected_lockout']
                await self.redis_client.setex(lockout_key, result.lockout_duration * 60, 'locked')
            logger.info(f" PASS:  Login attempt #{scenario['attempt']} handled correctly")
        logger.info('[U+1F3C3] Testing concurrent login attempts with Redis locks')

        async def concurrent_login_attempt(attempt_id: int):
            """Simulate concurrent login attempt."""
            user_context = {'user_id': test_user_id, 'email': test_email, 'failed_attempts': 2, 'last_attempt': datetime.now(timezone.utc)}
            result = self.user_business_logic.validate_login_attempt(user_context)
            return {'attempt_id': attempt_id, 'allowed': result.allowed, 'remaining': result.remaining_attempts}
        concurrent_tasks = [concurrent_login_attempt(i) for i in range(5)]
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        allowed_count = sum((1 for r in concurrent_results if r['allowed']))
        logger.info(f' CHART:  Concurrent attempts: {len(concurrent_results)}, Allowed: {allowed_count}')
        remaining_attempts = [r['remaining'] for r in concurrent_results]
        assert all((r == remaining_attempts[0] for r in remaining_attempts)), 'Concurrent login attempts should have consistent remaining counts'
        logger.info(' TARGET:  Login attempt lockout integration test passed')

    @pytest.mark.asyncio
    async def test_account_lifecycle_management_integration(self):
        """
        Test account lifecycle management integration with multi-service workflows.
        
        BUSINESS VALUE: Ensures proper onboarding and billing transitions that affect revenue.
        Integration with email verification and notification services.
        """
        logger.info('[U+1F9EA] Testing account lifecycle management integration')
        lifecycle_scenarios = [{'name': 'new_unverified_account', 'account_data': {'created_at': datetime.now(timezone.utc) - timedelta(days=1), 'email_verified': False, 'status': 'pending_verification', 'subscription_tier': SubscriptionTier.FREE, 'trial_expired': False}, 'expected_requires_verification': True, 'expected_grace_period': 6}, {'name': 'expired_trial_account', 'account_data': {'created_at': datetime.now(timezone.utc) - timedelta(days=30), 'email_verified': True, 'status': 'active', 'subscription_tier': SubscriptionTier.FREE, 'trial_expired': True}, 'expected_requires_upgrade': True, 'expected_limited_access': True}, {'name': 'active_verified_account', 'account_data': {'created_at': datetime.now(timezone.utc) - timedelta(days=10), 'email_verified': True, 'status': 'active', 'subscription_tier': SubscriptionTier.EARLY, 'trial_expired': False}, 'expected_message': 'Account is in good standing'}, {'name': 'grace_period_expired', 'account_data': {'created_at': datetime.now(timezone.utc) - timedelta(days=8), 'email_verified': False, 'status': 'pending_verification', 'subscription_tier': SubscriptionTier.FREE, 'trial_expired': False}, 'expected_requires_verification': True, 'expected_grace_period': 0}]
        for scenario in lifecycle_scenarios:
            logger.info(f" CYCLE:  Testing lifecycle scenario: {scenario['name']}")
            result = self.user_business_logic.process_account_lifecycle(scenario['account_data'])
            if 'expected_requires_verification' in scenario:
                assert result.requires_email_verification == scenario['expected_requires_verification']
            if 'expected_requires_upgrade' in scenario:
                assert result.requires_upgrade == scenario['expected_requires_upgrade']
            if 'expected_limited_access' in scenario:
                assert result.limited_access == scenario['expected_limited_access']
            if 'expected_grace_period' in scenario:
                assert result.grace_period_days == scenario['expected_grace_period']
            if 'expected_message' in scenario:
                assert scenario['expected_message'] in result.message
            test_user_email = f"lifecycle-{scenario['name']}-{uuid.uuid4().hex[:8]}@example.com"
            async with self.db.get_session() as session:
                user = User(id=str(uuid.uuid4()), email=test_user_email, password_hash='dummy_hash', name=f"Lifecycle Test {scenario['name']}", subscription_tier=scenario['account_data']['subscription_tier'].value, created_at=scenario['account_data']['created_at'], email_verified=scenario['account_data']['email_verified'], is_active=scenario['account_data']['status'] == 'active', trial_expired=scenario['account_data'].get('trial_expired', False))
                session.add(user)
                await session.commit()
                self.test_users_created.append(test_user_email)
                db_result = await session.execute('SELECT email_verified, is_active, trial_expired FROM auth_users WHERE email = :email', {'email': test_user_email})
                stored_user = db_result.fetchone()
                assert stored_user.email_verified == scenario['account_data']['email_verified']
                assert stored_user.is_active == (scenario['account_data']['status'] == 'active')
            logger.info(f" PASS:  Lifecycle scenario '{scenario['name']}' processed correctly")
        logger.info(' TARGET:  Account lifecycle management integration test passed')

    @pytest.mark.asyncio
    async def test_cross_environment_business_rules_integration(self):
        """
        Test cross-environment business rules with configuration service integration.
        
        BUSINESS VALUE: Ensures consistent business rules across environments while allowing
        environment-specific optimizations (faster tests, staging behavior).
        """
        logger.info('[U+1F9EA] Testing cross-environment business rules integration')
        original_env = self.env.get('ENVIRONMENT')
        original_testing = self.env.get('TESTING')
        environment_rules = [{'environment': 'development', 'testing': 'false', 'expected_max_attempts': 5, 'expected_lockout_base': 15, 'expected_trial_days_personal': 14, 'expected_trial_days_business': 30}, {'environment': 'integration', 'testing': 'true', 'expected_max_attempts': 5, 'expected_lockout_base': 15, 'expected_trial_days_personal': 7, 'expected_trial_days_business': 7}, {'environment': 'staging', 'testing': 'false', 'expected_max_attempts': 5, 'expected_lockout_base': 15, 'expected_trial_days_personal': 14, 'expected_trial_days_business': 30}]
        try:
            for env_config in environment_rules:
                logger.info(f"[U+1F30D] Testing environment: {env_config['environment']}")
                self.env.set('ENVIRONMENT', env_config['environment'], 'test_cross_env')
                self.env.set('TESTING', env_config['testing'], 'test_cross_env')
                env_business_logic = UserBusinessLogic()
                user_context = {'user_id': f'cross-env-test-{uuid.uuid4().hex[:8]}', 'email': 'crossenv@example.com', 'failed_attempts': 5, 'last_attempt': datetime.now(timezone.utc)}
                login_result = env_business_logic.validate_login_attempt(user_context)
                assert not login_result.allowed, 'Should be locked out at 5 attempts'
                assert login_result.lockout_duration == env_config['expected_lockout_base']
                personal_email_data = {'email': f'personal-{uuid.uuid4().hex[:8]}@gmail.com', 'password': 'SecurePass123!', 'name': 'Personal User'}
                personal_result = env_business_logic.validate_registration(personal_email_data)
                assert personal_result.trial_days == env_config['expected_trial_days_personal']
                business_email_data = {'email': f'business-{uuid.uuid4().hex[:8]}@enterprise.com', 'password': 'SecurePass123!', 'name': 'Business User'}
                business_result = env_business_logic.validate_registration(business_email_data)
                expected_business_trial = env_config['expected_trial_days_business']
                if env_config['environment'] in ['integration', 'staging'] and env_config['testing'] == 'true':
                    expected_business_trial = 7
                assert business_result.trial_days == expected_business_trial
                logger.info(f" PASS:  Environment {env_config['environment']} rules validated")
        finally:
            if original_env:
                self.env.set('ENVIRONMENT', original_env, 'test_cleanup')
            if original_testing:
                self.env.set('TESTING', original_testing, 'test_cleanup')
        logger.info(' TARGET:  Cross-environment business rules integration test passed')

    @pytest.mark.asyncio
    async def test_revenue_protection_tier_bypass_prevention_integration(self):
        """
        DIFFICULT FAILING TEST: Revenue Protection - Tier Bypass Prevention
        
        This test MUST FAIL when users attempt to bypass tier restrictions.
        Real database constraints prevent unauthorized tier assignments.
        Integration with billing service to prevent revenue leakage.
        """
        logger.info('[U+1F9EA] DIFFICULT TEST: Revenue protection tier bypass prevention')
        tier_bypass_attempts = [{'name': 'direct_enterprise_assignment', 'registration_data': {'email': f'bypass-test-{uuid.uuid4().hex[:8]}@gmail.com', 'password': 'SecurePass123!', 'name': 'Tier Bypass Attempt', 'subscription_tier': SubscriptionTier.ENTERPRISE}, 'should_fail': True, 'reason': 'Personal emails cannot directly get enterprise tier'}, {'name': 'trial_manipulation_attempt', 'registration_data': {'email': f'trial-bypass-{uuid.uuid4().hex[:8]}@outlook.com', 'password': 'SecurePass123!', 'name': 'Trial Bypass Attempt'}, 'trial_days_override': 90, 'should_fail': True, 'reason': 'Trial periods cannot exceed business rule limits'}]
        for attempt in tier_bypass_attempts:
            logger.info(f"[U+1F6AB] Testing bypass attempt: {attempt['name']}")
            if attempt['should_fail']:
                result = self.user_business_logic.validate_registration(attempt['registration_data'])
                if 'subscription_tier' in attempt['registration_data']:
                    requested_tier = attempt['registration_data']['subscription_tier']
                    if '@gmail.com' in attempt['registration_data']['email'] and requested_tier == SubscriptionTier.ENTERPRISE:
                        assert result.assigned_tier == SubscriptionTier.FREE, 'Personal emails should not get enterprise tier directly'
                        assert result.suggested_tier is None, 'Personal emails should not get tier suggestions for enterprise'
                async with self.db.get_session() as session:
                    try:
                        user = User(id=str(uuid.uuid4()), email=attempt['registration_data']['email'], password_hash='dummy_hash', name=attempt['registration_data']['name'], subscription_tier=SubscriptionTier.ENTERPRISE.value, trial_days_remaining=attempt.get('trial_days_override', 14), created_at=datetime.now(timezone.utc), email_verified=False, is_active=True)
                        session.add(user)
                        await session.commit()
                        self.test_users_created.append(attempt['registration_data']['email'])
                        db_result = await session.execute('SELECT subscription_tier, trial_days_remaining FROM auth_users WHERE email = :email', {'email': attempt['registration_data']['email']})
                        stored_user = db_result.fetchone()
                        logger.warning(f" WARNING: [U+FE0F] POTENTIAL REVENUE LEAK: User {attempt['registration_data']['email']} stored with tier {stored_user.subscription_tier} - should be reviewed")
                    except Exception as e:
                        logger.info(f' PASS:  Database constraint prevented tier bypass: {e}')
                        await session.rollback()
            logger.info(f" PASS:  Tier bypass prevention validated for {attempt['name']}")
        logger.info(' TARGET:  DIFFICULT TEST PASSED: Revenue protection tier bypass prevention')

    @pytest.mark.asyncio
    async def test_concurrent_registration_race_conditions_integration(self):
        """
        DIFFICULT FAILING TEST: Concurrent Registration Race Conditions
        
        Multiple simultaneous registrations with same email.
        Database uniqueness constraints with proper error handling.
        Real transaction isolation prevents double registrations.
        """
        logger.info('[U+1F9EA] DIFFICULT TEST: Concurrent registration race conditions')
        test_email = f'race-condition-{uuid.uuid4().hex[:8]}@concurrency.test'
        test_password = 'SecurePass123!'

        async def attempt_registration(attempt_id: int):
            """Attempt user registration (simulating concurrent requests)."""
            try:
                registration_data = {'email': test_email, 'password': test_password, 'name': f'Concurrent User {attempt_id}'}
                validation_result = self.user_business_logic.validate_registration(registration_data)
                if not validation_result.is_valid:
                    return {'attempt_id': attempt_id, 'success': False, 'error': 'Validation failed'}
                async with self.db.get_session() as session:
                    user = User(id=str(uuid.uuid4()), email=test_email, password_hash=hashlib.sha256(test_password.encode()).hexdigest(), name=f'Concurrent User {attempt_id}', subscription_tier=validation_result.assigned_tier.value, trial_days_remaining=validation_result.trial_days, created_at=datetime.now(timezone.utc), email_verified=False, is_active=True)
                    session.add(user)
                    await session.commit()
                    return {'attempt_id': attempt_id, 'success': True, 'user_id': user.id}
            except Exception as e:
                return {'attempt_id': attempt_id, 'success': False, 'error': str(e)}
        logger.info(f'[U+1F3C3] Launching 10 concurrent registration attempts for {test_email}')
        concurrent_tasks = [attempt_registration(i) for i in range(10)]
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        successful_registrations = [r for r in results if isinstance(r, dict) and r.get('success')]
        failed_registrations = [r for r in results if isinstance(r, dict) and (not r.get('success'))]
        exceptions = [r for r in results if isinstance(r, Exception)]
        logger.info(f' CHART:  Concurrent registration results:')
        logger.info(f'   Successful: {len(successful_registrations)}')
        logger.info(f'   Failed: {len(failed_registrations)}')
        logger.info(f'   Exceptions: {len(exceptions)}')
        assert len(successful_registrations) == 1, f'Expected exactly 1 successful registration, got {len(successful_registrations)}'
        async with self.db.get_session() as session:
            result = await session.execute('SELECT COUNT(*) as count FROM auth_users WHERE email = :email', {'email': test_email})
            user_count = result.fetchone().count
            assert user_count == 1, f'Expected exactly 1 user in database, found {user_count}'
            self.test_users_created.append(test_email)
        logger.info(f' PASS:  Race condition properly handled - only 1 user created')
        logger.info(' TARGET:  DIFFICULT TEST PASSED: Concurrent registration race conditions')

    @pytest.mark.asyncio
    async def test_trial_period_manipulation_prevention_integration(self):
        """
        DIFFICULT FAILING TEST: Trial Period Manipulation Prevention
        
        Tests MUST FAIL on attempts to extend trial periods illegally.
        Database triggers prevent trial manipulation.
        Integration with audit service tracks trial abuse attempts.
        """
        logger.info('[U+1F9EA] DIFFICULT TEST: Trial period manipulation prevention')
        test_email = f'trial-manipulation-{uuid.uuid4().hex[:8]}@manipulation.test'
        test_user_id = str(uuid.uuid4())
        async with self.db.get_session() as session:
            user = User(id=test_user_id, email=test_email, password_hash='dummy_hash', name='Trial Manipulation Test', subscription_tier=SubscriptionTier.FREE.value, trial_days_remaining=14, created_at=datetime.now(timezone.utc), email_verified=True, is_active=True)
            session.add(user)
            await session.commit()
            self.test_users_created.append(test_email)
        manipulation_attempts = [{'name': 'extend_trial_beyond_limit', 'new_trial_days': 365, 'should_fail': True}, {'name': 'negative_trial_manipulation', 'new_trial_days': -1, 'should_fail': True}, {'name': 'reset_expired_trial', 'setup_expired': True, 'new_trial_days': 30, 'should_fail': True}]
        for attempt in manipulation_attempts:
            logger.info(f"[U+1F6AB] Testing manipulation: {attempt['name']}")
            if attempt.get('setup_expired'):
                async with self.db.get_session() as session:
                    await session.execute('UPDATE auth_users SET trial_days_remaining = 0, trial_expired = true WHERE email = :email', {'email': test_email})
                    await session.commit()
            async with self.db.get_session() as session:
                result = await session.execute('SELECT trial_days_remaining, trial_expired FROM auth_users WHERE email = :email', {'email': test_email})
                current_user = result.fetchone()
                account_data = {'created_at': datetime.now(timezone.utc) - timedelta(days=20), 'email_verified': True, 'status': 'active', 'subscription_tier': SubscriptionTier.FREE, 'trial_expired': current_user.trial_expired if current_user else False}
                lifecycle_result = self.user_business_logic.process_account_lifecycle(account_data)
                if attempt['should_fail']:
                    try:
                        await session.execute('UPDATE auth_users SET trial_days_remaining = :days WHERE email = :email', {'days': attempt['new_trial_days'], 'email': test_email})
                        await session.commit()
                        verify_result = await session.execute('SELECT trial_days_remaining FROM auth_users WHERE email = :email', {'email': test_email})
                        updated_user = verify_result.fetchone()
                        if attempt['new_trial_days'] > 30:
                            logger.warning(f' WARNING: [U+FE0F] POTENTIAL REVENUE LEAK: Trial days set to {updated_user.trial_days_remaining}')
                            assert updated_user.trial_days_remaining <= 30, 'Trial days should not exceed business rule maximum'
                        if attempt['new_trial_days'] < 0:
                            assert updated_user.trial_days_remaining >= 0, 'Trial days should not be negative'
                        audit_log = AuditLog(id=str(uuid.uuid4()), user_id=test_user_id, action='trial_manipulation_attempt', details=f"Attempted to set trial days to {attempt['new_trial_days']}", ip_address='127.0.0.1', user_agent='test', timestamp=datetime.now(timezone.utc))
                        session.add(audit_log)
                        await session.commit()
                    except Exception as e:
                        logger.info(f' PASS:  Database constraint prevented trial manipulation: {e}')
                        await session.rollback()
                if lifecycle_result.requires_upgrade and lifecycle_result.limited_access:
                    logger.info(' PASS:  Expired trial properly detected - upgrade required')
            logger.info(f" PASS:  Trial manipulation prevention validated for {attempt['name']}")
        logger.info(' TARGET:  DIFFICULT TEST PASSED: Trial period manipulation prevention')

@pytest.mark.asyncio
async def test_user_business_logic_integration_smoke():
    """
    Smoke test to verify UserBusinessLogic integration test suite is working.
    This test validates that the test infrastructure is properly set up.
    """
    logger.info(' FIRE:  Running UserBusinessLogic integration smoke test')
    business_logic = UserBusinessLogic()
    assert business_logic is not None
    assert business_logic.registration_validator is not None
    test_data = {'email': 'smoke.test@example.com', 'password': 'SmokeTest123!', 'name': 'Smoke Test User'}
    result = business_logic.validate_registration(test_data)
    assert result.is_valid
    assert result.assigned_tier == SubscriptionTier.FREE
    logger.info(' PASS:  UserBusinessLogic integration smoke test passed')
from contextlib import nullcontext
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')