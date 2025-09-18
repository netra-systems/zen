"""
E2E GCP Staging Tests for UnifiedAuthInterface - FINAL PHASE
Real GCP IAM, OAuth providers, and production security testing

Business Value Protection:
- 500K+ ARR: Secure authentication prevents unauthorized access to customer data
- $15K+ MRR per Enterprise: SSO integration and advanced security features
- Platform trust: Multi-factor authentication and session security
- Compliance: SOC2, GDPR, and enterprise security requirements
"""
import asyncio
import pytest
import time
import uuid
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
from unittest.mock import patch
import secrets
import base64
import hashlib
from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService
from netra_backend.app.schemas.auth_types import AuthConfig
from enum import Enum

class SecurityLevel(str, Enum):
    """Security level classifications."""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'
from auth_service.auth_core.security.session_policy_validator import SessionPolicyValidator as SessionPolicy
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.models.oauth_user import OAuthUser
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotAsyncTestCase

class UnifiedAuthInterfaceGCPStagingTests(SSotAsyncTestCase):
    """
    E2E GCP Staging tests for UnifiedAuthInterface protecting business value.
    Tests real GCP IAM, OAuth providers, and production security scenarios.
    """

    @classmethod
    async def asyncSetUpClass(cls):
        """Set up real GCP authentication services."""
        await super().asyncSetUpClass()
        cls.env = IsolatedEnvironment()
        cls.id_manager = UnifiedIDManager()
        cls.auth_config = AuthConfig(enable_multi_factor=True, enable_sso=True, session_timeout_minutes=60, max_concurrent_sessions=5, require_password_complexity=True, enable_audit_logging=True, security_level=SecurityLevel.ENTERPRISE, oauth_providers=['google', 'github', 'azure', 'okta'], enable_rate_limiting=True, max_login_attempts=5, lockout_duration_minutes=15)
        cls.unified_auth = UnifiedAuthenticationService(config=cls.auth_config)
        cls.auth_service = AuthService()
        cls.jwt_secret = cls.env.get('JWT_SECRET_KEY')
        cls.jwt_algorithm = 'HS256'
        cls.oauth_configs = {'google': {'client_id': cls.env.get('GOOGLE_CLIENT_ID'), 'client_secret': cls.env.get('GOOGLE_CLIENT_SECRET'), 'redirect_uri': 'https://staging.netrasystems.ai/auth/callback/google'}, 'github': {'client_id': cls.env.get('GITHUB_CLIENT_ID'), 'client_secret': cls.env.get('GITHUB_CLIENT_SECRET'), 'redirect_uri': 'https://staging.netrasystems.ai/auth/callback/github'}, 'azure': {'client_id': cls.env.get('AZURE_CLIENT_ID'), 'client_secret': cls.env.get('AZURE_CLIENT_SECRET'), 'redirect_uri': 'https://staging.netrasystems.ai/auth/callback/azure'}, 'okta': {'client_id': cls.env.get('OKTA_CLIENT_ID'), 'client_secret': cls.env.get('OKTA_CLIENT_SECRET'), 'redirect_uri': 'https://staging.netrasystems.ai/auth/callback/okta'}}

    async def asyncTearDown(self):
        """Clean up test authentication data."""
        await self.unified_auth.cleanup_test_data()
        await super().asyncTearDown()

    @pytest.mark.e2e_gcp_staging
    @pytest.mark.high_difficulty
    async def test_enterprise_sso_integration_production(self):
        """
        HIGH DIFFICULTY: Test enterprise SSO integration with real providers.
        
        Business Value: $15K+ MRR per Enterprise - SSO is critical for enterprise sales.
        Validates: SAML/OIDC integration, multi-provider support, enterprise policies.
        """
        enterprise_domain = 'enterprise-test.netrasystems.ai'
        sso_config = {'domain': enterprise_domain, 'providers': ['azure', 'okta', 'google'], 'require_domain_verification': True, 'enforce_mfa': True, 'session_policies': {'max_idle_minutes': 30, 'require_device_trust': True, 'restrict_ip_ranges': ['10.0.0.0/8', '172.16.0.0/12']}, 'compliance_requirements': {'audit_all_logins': True, 'require_consent': True, 'data_residency': 'US'}}
        sso_deployment = await self.unified_auth.deploy_sso_configuration(domain=enterprise_domain, config=sso_config, validation_mode='production')
        self.assertTrue(sso_deployment.get('success', False), 'SSO configuration deployment failed')
        self.assertIsNotNone(sso_deployment.get('configuration_id'), 'No SSO configuration ID generated')
        test_users = [{'email': 'test.user.azure@enterprise-test.netrasystems.ai', 'provider': 'azure', 'enterprise_attributes': {'department': 'Engineering', 'role': 'Senior Developer', 'permissions': ['read', 'write', 'admin']}}, {'email': 'test.user.okta@enterprise-test.netrasystems.ai', 'provider': 'okta', 'enterprise_attributes': {'department': 'Finance', 'role': 'Analyst', 'permissions': ['read', 'write']}}, {'email': 'test.user.google@enterprise-test.netrasystems.ai', 'provider': 'google', 'enterprise_attributes': {'department': 'Marketing', 'role': 'Manager', 'permissions': ['read', 'write', 'reports']}}]
        authentication_results = []
        for test_user in test_users:
            auth_flow_start = time.time()
            sso_initiation = await self.unified_auth.initiate_sso_flow(domain=enterprise_domain, provider=test_user['provider'], user_email=test_user['email'], redirect_uri=f'https://staging.netrasystems.ai/dashboard')
            self.assertTrue(sso_initiation.get('success', False), f"SSO initiation failed for {test_user['provider']}")
            provider_auth = await self.unified_auth.simulate_provider_authentication(provider=test_user['provider'], flow_id=sso_initiation['flow_id'], user_attributes={'email': test_user['email'], 'verified': True, 'mfa_completed': True, **test_user['enterprise_attributes']})
            self.assertTrue(provider_auth.get('success', False), f"Provider authentication failed for {test_user['provider']}")
            session_creation = await self.unified_auth.complete_sso_callback(flow_id=sso_initiation['flow_id'], provider_token=provider_auth['auth_code'], domain=enterprise_domain)
            auth_flow_time = time.time() - auth_flow_start
            self.assertTrue(session_creation.get('success', False), f"Session creation failed for {test_user['provider']}")
            self.assertIsNotNone(session_creation.get('access_token'), f"No access token for {test_user['provider']}")
            self.assertIsNotNone(session_creation.get('user_id'), f"No user ID for {test_user['provider']}")
            self.assertLess(auth_flow_time, 10.0, f"SSO flow too slow for {test_user['provider']}: {auth_flow_time}s")
            authentication_results.append({'provider': test_user['provider'], 'user_id': session_creation['user_id'], 'access_token': session_creation['access_token'], 'auth_time': auth_flow_time, 'enterprise_attributes': test_user['enterprise_attributes']})
        policy_validations = []
        for auth_result in authentication_results:
            rbac_check = await self.unified_auth.validate_enterprise_permissions(user_id=auth_result['user_id'], required_permissions=['read', 'write'], domain=enterprise_domain)
            self.assertTrue(rbac_check.get('authorized', False), f"RBAC validation failed for {auth_result['provider']}")
            session_validation = await self.unified_auth.validate_session_policies(access_token=auth_result['access_token'], policies=sso_config['session_policies'])
            self.assertTrue(session_validation.get('compliant', False), f"Session policy validation failed for {auth_result['provider']}")
            policy_validations.append({'provider': auth_result['provider'], 'rbac_valid': rbac_check.get('authorized', False), 'session_valid': session_validation.get('compliant', False)})
        policy_success_rate = sum((1 for p in policy_validations if p['rbac_valid'] and p['session_valid'])) / len(policy_validations)
        self.assertEqual(policy_success_rate, 1.0, 'Enterprise policy enforcement incomplete')

    @pytest.mark.e2e_gcp_staging
    @pytest.mark.high_difficulty
    async def test_multi_factor_authentication_production_scale(self):
        """
        HIGH DIFFICULTY: Test MFA at production scale with real authenticators.
        
        Business Value: Platform security - prevents 99.9% of account takeovers.
        Validates: TOTP, SMS, push notifications, backup codes, device trust.
        """
        mfa_test_users = []
        for i in range(50):
            user_email = f'mfa.test.{i}@netrasystems.ai'
            user_id = self.id_manager.generate_user_id()
            user_registration = await self.unified_auth.register_user(email=user_email, password='SecureTestPassword123!', require_mfa=True, user_id=user_id, security_level=SecurityLevel.ENTERPRISE)
            self.assertTrue(user_registration.get('success', False), f'User registration failed: {user_email}')
            mfa_test_users.append({'user_id': user_id, 'email': user_email, 'registration_result': user_registration})
        mfa_methods = ['totp', 'sms', 'push', 'backup_codes']
        mfa_setup_results = []
        for user in mfa_test_users[:10]:
            user_mfa_results = {}
            for method in mfa_methods:
                setup_start_time = time.time()
                if method == 'totp':
                    totp_setup = await self.unified_auth.setup_totp_mfa(user_id=user['user_id'], authenticator_app='google_authenticator')
                    self.assertTrue(totp_setup.get('success', False), f"TOTP setup failed for {user['email']}")
                    self.assertIsNotNone(totp_setup.get('secret_key'), 'No TOTP secret key generated')
                    self.assertIsNotNone(totp_setup.get('qr_code'), 'No QR code generated for TOTP')
                    import pyotp
                    totp_generator = pyotp.TOTP(totp_setup['secret_key'])
                    current_otp = totp_generator.now()
                    totp_verification = await self.unified_auth.verify_totp_code(user_id=user['user_id'], otp_code=current_otp)
                    user_mfa_results['totp'] = {'setup_success': totp_setup.get('success', False), 'verification_success': totp_verification.get('valid', False), 'setup_time': time.time() - setup_start_time}
                elif method == 'sms':
                    test_phone = f"+1555010{user['user_id'][-4:]}"
                    sms_setup = await self.unified_auth.setup_sms_mfa(user_id=user['user_id'], phone_number=test_phone, verification_required=True)
                    if sms_setup.get('success', False):
                        test_verification_code = '123456'
                        sms_verification = await self.unified_auth.verify_sms_code(user_id=user['user_id'], verification_code=test_verification_code, test_mode=True)
                        user_mfa_results['sms'] = {'setup_success': True, 'verification_success': sms_verification.get('valid', False), 'setup_time': time.time() - setup_start_time}
                    else:
                        user_mfa_results['sms'] = {'setup_success': False, 'verification_success': False, 'setup_time': time.time() - setup_start_time}
                elif method == 'push':
                    push_setup = await self.unified_auth.setup_push_mfa(user_id=user['user_id'], device_token='test_device_token', device_name='Test iPhone 12', platform='ios')
                    if push_setup.get('success', False):
                        push_verification = await self.unified_auth.simulate_push_response(user_id=user['user_id'], response='approved', biometric_verified=True)
                        user_mfa_results['push'] = {'setup_success': True, 'verification_success': push_verification.get('valid', False), 'setup_time': time.time() - setup_start_time}
                    else:
                        user_mfa_results['push'] = {'setup_success': False, 'verification_success': False, 'setup_time': time.time() - setup_start_time}
                elif method == 'backup_codes':
                    backup_setup = await self.unified_auth.generate_backup_codes(user_id=user['user_id'], count=10, entropy_bits=128)
                    self.assertTrue(backup_setup.get('success', False), 'Backup codes generation failed')
                    self.assertEqual(len(backup_setup.get('codes', [])), 10, 'Incorrect number of backup codes')
                    test_backup_code = backup_setup['codes'][0]
                    backup_verification = await self.unified_auth.verify_backup_code(user_id=user['user_id'], backup_code=test_backup_code)
                    user_mfa_results['backup_codes'] = {'setup_success': True, 'verification_success': backup_verification.get('valid', False), 'setup_time': time.time() - setup_start_time, 'codes_generated': len(backup_setup.get('codes', []))}
            mfa_setup_results.append({'user_id': user['user_id'], 'email': user['email'], 'mfa_methods': user_mfa_results})
        method_success_rates = {}
        for method in mfa_methods:
            successful_setups = sum((1 for result in mfa_setup_results if result['mfa_methods'].get(method, {}).get('setup_success', False)))
            method_success_rates[method] = successful_setups / len(mfa_setup_results)
        for method, success_rate in method_success_rates.items():
            self.assertGreater(success_rate, 0.9, f'MFA {method} setup success rate too low: {success_rate}')
        concurrent_auth_tests = []
        for user in mfa_test_users:
            auth_task = self.unified_auth.authenticate_with_mfa(email=user['email'], password='SecureTestPassword123!', preferred_mfa_method='totp')
            concurrent_auth_tests.append(auth_task)
        auth_start_time = time.time()
        auth_results = await asyncio.gather(*concurrent_auth_tests, return_exceptions=True)
        total_auth_time = time.time() - auth_start_time
        successful_auths = [r for r in auth_results if not isinstance(r, Exception) and r.get('success', False)]
        auth_success_rate = len(successful_auths) / len(mfa_test_users)
        self.assertGreater(auth_success_rate, 0.95, f'MFA authentication success rate too low: {auth_success_rate}')
        self.assertLess(total_auth_time, 120.0, f'Concurrent MFA authentication too slow: {total_auth_time}s')

    @pytest.mark.e2e_gcp_staging
    @pytest.mark.high_difficulty
    async def test_advanced_session_management_enterprise(self):
        """
        HIGH DIFFICULTY: Test advanced session management for enterprise security.
        
        Business Value: 500K+ ARR protection - prevents session hijacking attacks.
        Validates: Session isolation, concurrent session limits, device fingerprinting.
        """
        enterprise_user_email = 'enterprise.security@netrasystems.ai'
        enterprise_user_id = self.id_manager.generate_user_id()
        enterprise_session_policy = SessionPolicy(max_concurrent_sessions=3, session_timeout_minutes=30, require_device_fingerprinting=True, enable_location_tracking=True, require_ip_validation=True, enable_session_binding=True, force_logout_on_suspicious_activity=True, enable_concurrent_session_monitoring=True)
        user_registration = await self.unified_auth.register_user(email=enterprise_user_email, password='EnterpriseSecurePassword123!', user_id=enterprise_user_id, security_level=SecurityLevel.ENTERPRISE, session_policy=enterprise_session_policy)
        self.assertTrue(user_registration.get('success', False), 'Enterprise user registration failed')
        session_scenarios = [{'device_name': 'MacBook Pro', 'device_type': 'desktop', 'platform': 'macOS', 'location': 'San Francisco, CA', 'ip_address': '192.168.1.100', 'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}, {'device_name': 'iPhone 12', 'device_type': 'mobile', 'platform': 'iOS', 'location': 'San Francisco, CA', 'ip_address': '192.168.1.101', 'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15'}, {'device_name': 'Windows Laptop', 'device_type': 'desktop', 'platform': 'Windows', 'location': 'New York, NY', 'ip_address': '10.0.0.50', 'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}, {'device_name': 'Android Phone', 'device_type': 'mobile', 'platform': 'Android', 'location': 'London, UK', 'ip_address': '172.16.0.25', 'user_agent': 'Mozilla/5.0 (Linux; Android 11; SM-G991U) AppleWebKit/537.36'}]
        created_sessions = []
        for i, scenario in enumerate(session_scenarios):
            session_creation_start = time.time()
            device_fingerprint = await self.unified_auth.generate_device_fingerprint(device_info=scenario, user_agent=scenario['user_agent'], additional_entropy=str(time.time()))
            session_result = await self.unified_auth.create_authenticated_session(email=enterprise_user_email, password='EnterpriseSecurePassword123!', device_fingerprint=device_fingerprint, location_info={'city': scenario['location'].split(', ')[0], 'country': scenario['location'].split(', ')[1] if ', ' in scenario['location'] else 'US', 'ip_address': scenario['ip_address']}, session_metadata={'device_name': scenario['device_name'], 'platform': scenario['platform'], 'device_type': scenario['device_type']})
            session_creation_time = time.time() - session_creation_start
            if i < 3:
                self.assertTrue(session_result.get('success', False), f"Session creation failed for device {i + 1}: {scenario['device_name']}")
                self.assertIsNotNone(session_result.get('access_token'), f'No access token for device {i + 1}')
                self.assertIsNotNone(session_result.get('session_id'), f'No session ID for device {i + 1}')
                created_sessions.append({'session_id': session_result['session_id'], 'access_token': session_result['access_token'], 'device_fingerprint': device_fingerprint, 'scenario': scenario, 'creation_time': session_creation_time})
            else:
                self.assertFalse(session_result.get('success', False), f'Session {i + 1} should have been rejected due to limit')
                self.assertIn('concurrent_session_limit', session_result.get('error_code', ''), 'Wrong rejection reason for session limit')
        self.assertEqual(len(created_sessions), 3, 'Concurrent session limit not properly enforced')
        session_activities = []
        for session in created_sessions:
            for activity_count in range(10):
                activity_result = await self.unified_auth.record_session_activity(session_id=session['session_id'], activity_type='api_call', activity_data={'endpoint': '/api/agents/execute', 'method': 'POST', 'timestamp': time.time(), 'user_agent': session['scenario']['user_agent'], 'ip_address': session['scenario']['ip_address']})
                self.assertTrue(activity_result.get('recorded', False), f"Activity recording failed for session {session['session_id']}")
                session_activities.append(activity_result)
        suspicious_session = created_sessions[0]
        suspicious_activities = [{'activity_type': 'unusual_location', 'details': {'new_country': 'Russia', 'previous_country': 'US'}}, {'activity_type': 'rapid_requests', 'details': {'requests_per_minute': 1000, 'normal_rate': 10}}, {'activity_type': 'device_change', 'details': {'fingerprint_mismatch': True, 'confidence': 0.95}}]
        for suspicious_activity in suspicious_activities:
            suspicion_result = await self.unified_auth.process_suspicious_activity(session_id=suspicious_session['session_id'], activity_data=suspicious_activity)
            self.assertTrue(suspicion_result.get('detected', False), f"Suspicious activity not detected: {suspicious_activity['activity_type']}")
        session_status = await self.unified_auth.get_session_status(session_id=suspicious_session['session_id'])
        self.assertFalse(session_status.get('active', True), 'Suspicious session was not automatically terminated')
        self.assertIn('security_violation', session_status.get('termination_reason', ''), 'Wrong termination reason for suspicious session')
        remaining_sessions = created_sessions[1:]
        for session in remaining_sessions:
            renewal_result = await self.unified_auth.renew_session(session_id=session['session_id'], access_token=session['access_token'], device_fingerprint=session['device_fingerprint'])
            self.assertTrue(renewal_result.get('success', False), f"Session renewal failed for {session['session_id']}")
            self.assertIsNotNone(renewal_result.get('new_access_token'), 'No new access token after renewal')
            termination_result = await self.unified_auth.terminate_session(session_id=session['session_id'], reason='user_logout', cleanup_associated_data=True)
            self.assertTrue(termination_result.get('success', False), f"Session termination failed for {session['session_id']}")
        user_sessions = await self.unified_auth.get_user_sessions(user_id=enterprise_user_id, include_terminated=False)
        active_sessions = [s for s in user_sessions if s.get('active', False)]
        self.assertEqual(len(active_sessions), 0, 'Sessions not properly cleaned up after termination')

    @pytest.mark.e2e_gcp_staging
    async def test_oauth_provider_integration_comprehensive(self):
        """
        Test comprehensive OAuth provider integration with error handling.
        
        Business Value: Customer acquisition - supports all major OAuth providers.
        Validates: Provider-specific flows, error handling, token management.
        """
        oauth_test_results = {}
        for provider_name, provider_config in self.oauth_configs.items():
            if not provider_config.get('client_id'):
                continue
            provider_start_time = time.time()
            provider_test_result = {'provider': provider_name, 'tests_passed': 0, 'tests_failed': 0, 'error_scenarios': []}
            try:
                auth_url_result = await self.unified_auth.generate_oauth_auth_url(provider=provider_name, scopes=['openid', 'email', 'profile'], state=str(uuid.uuid4()), redirect_uri=provider_config['redirect_uri'])
                if auth_url_result.get('success', False) and auth_url_result.get('auth_url'):
                    provider_test_result['tests_passed'] += 1
                    auth_url = auth_url_result['auth_url']
                    self.assertIn(provider_config['client_id'], auth_url, f'Client ID missing from {provider_name} auth URL')
                    self.assertIn('response_type=code', auth_url, f'Response type missing from {provider_name} auth URL')
                else:
                    provider_test_result['tests_failed'] += 1
                    provider_test_result['error_scenarios'].append('auth_url_generation')
            except Exception as e:
                provider_test_result['tests_failed'] += 1
                provider_test_result['error_scenarios'].append(f'auth_url_exception: {str(e)}')
            try:
                mock_auth_code = f'mock_code_{provider_name}_{int(time.time())}'
                token_exchange_result = await self.unified_auth.exchange_oauth_code(provider=provider_name, authorization_code=mock_auth_code, redirect_uri=provider_config['redirect_uri'], test_mode=True)
                if token_exchange_result.get('success', False):
                    provider_test_result['tests_passed'] += 1
                    if 'access_token' in token_exchange_result:
                        self.assertIsNotNone(token_exchange_result['access_token'])
                    if 'user_info' in token_exchange_result:
                        user_info = token_exchange_result['user_info']
                        self.assertIn('email', user_info)
                else:
                    provider_test_result['tests_failed'] += 1
                    provider_test_result['error_scenarios'].append('token_exchange')
            except Exception as e:
                provider_test_result['tests_failed'] += 1
                provider_test_result['error_scenarios'].append(f'token_exchange_exception: {str(e)}')
            try:
                mock_access_token = f'mock_token_{provider_name}_{int(time.time())}'
                profile_result = await self.unified_auth.get_oauth_user_profile(provider=provider_name, access_token=mock_access_token, test_mode=True)
                if profile_result.get('success', False):
                    provider_test_result['tests_passed'] += 1
                    profile_data = profile_result.get('profile', {})
                    required_fields = ['id', 'email', 'name']
                    for field in required_fields:
                        if field not in profile_data:
                            provider_test_result['error_scenarios'].append(f'missing_profile_field_{field}')
                else:
                    provider_test_result['tests_failed'] += 1
                    provider_test_result['error_scenarios'].append('profile_retrieval')
            except Exception as e:
                provider_test_result['tests_failed'] += 1
                provider_test_result['error_scenarios'].append(f'profile_exception: {str(e)}')
            error_scenarios = [{'scenario': 'invalid_client', 'error_code': 'invalid_client'}, {'scenario': 'invalid_grant', 'error_code': 'invalid_grant'}, {'scenario': 'expired_token', 'error_code': 'token_expired'}, {'scenario': 'insufficient_scope', 'error_code': 'insufficient_scope'}]
            for error_scenario in error_scenarios:
                try:
                    error_handling_result = await self.unified_auth.test_oauth_error_handling(provider=provider_name, error_scenario=error_scenario['scenario'], expected_error_code=error_scenario['error_code'])
                    if error_handling_result.get('handled_correctly', False):
                        provider_test_result['tests_passed'] += 1
                    else:
                        provider_test_result['tests_failed'] += 1
                        provider_test_result['error_scenarios'].append(f"error_handling_{error_scenario['scenario']}")
                except Exception as e:
                    provider_test_result['tests_failed'] += 1
                    provider_test_result['error_scenarios'].append(f"error_handling_exception_{error_scenario['scenario']}: {str(e)}")
            provider_test_time = time.time() - provider_start_time
            provider_test_result['test_duration'] = provider_test_time
            oauth_test_results[provider_name] = provider_test_result
        total_tests = sum((result['tests_passed'] + result['tests_failed'] for result in oauth_test_results.values()))
        total_passed = sum((result['tests_passed'] for result in oauth_test_results.values()))
        overall_success_rate = total_passed / total_tests if total_tests > 0 else 0
        self.assertGreater(overall_success_rate, 0.8, f'OAuth integration success rate too low: {overall_success_rate}')
        for provider_name, result in oauth_test_results.items():
            provider_success_rate = result['tests_passed'] / (result['tests_passed'] + result['tests_failed'])
            self.assertGreater(provider_success_rate, 0.5, f'Provider {provider_name} success rate too low: {provider_success_rate}')

    @pytest.mark.e2e_gcp_staging
    async def test_jwt_token_security_comprehensive(self):
        """
        Test JWT token security, validation, and lifecycle management.
        
        Business Value: Platform security - prevents token-based attacks.
        Validates: JWT signing, validation, expiration, refresh token security.
        """
        test_user_id = self.id_manager.generate_user_id()
        test_email = 'jwt.security.test@netrasystems.ai'
        security_levels = [SecurityLevel.BASIC, SecurityLevel.STANDARD, SecurityLevel.ENTERPRISE]
        jwt_test_results = []
        for security_level in security_levels:
            jwt_generation_start = time.time()
            jwt_result = await self.unified_auth.generate_jwt_token(user_id=test_user_id, email=test_email, security_level=security_level, additional_claims={'user_type': 'test_user', 'permissions': ['read', 'write'], 'security_level': security_level.value}, expiry_minutes=60)
            jwt_generation_time = time.time() - jwt_generation_start
            self.assertTrue(jwt_result.get('success', False), f'JWT generation failed for {security_level.value}')
            self.assertIsNotNone(jwt_result.get('access_token'), f'No access token for {security_level.value}')
            self.assertIsNotNone(jwt_result.get('refresh_token'), f'No refresh token for {security_level.value}')
            access_token = jwt_result['access_token']
            try:
                token_header = jwt.get_unverified_header(access_token)
                token_payload = jwt.decode(access_token, options={'verify_signature': False})
                self.assertEqual(token_header.get('alg'), self.jwt_algorithm, 'Incorrect JWT algorithm')
                self.assertEqual(token_header.get('typ'), 'JWT', 'Incorrect JWT type')
                required_claims = ['sub', 'email', 'iat', 'exp', 'user_type']
                for claim in required_claims:
                    self.assertIn(claim, token_payload, f'Missing claim {claim} in JWT')
                self.assertEqual(token_payload['sub'], test_user_id, 'Incorrect user ID in JWT')
                self.assertEqual(token_payload['email'], test_email, 'Incorrect email in JWT')
                exp_timestamp = token_payload['exp']
                current_timestamp = time.time()
                self.assertGreater(exp_timestamp, current_timestamp, 'JWT already expired')
                self.assertLess(exp_timestamp - current_timestamp, 3700, 'JWT expiration too long')
            except jwt.DecodeError as e:
                self.fail(f'JWT structure validation failed for {security_level.value}: {e}')
            verification_result = await self.unified_auth.verify_jwt_token(token=access_token, required_claims=['sub', 'email'], check_expiration=True)
            self.assertTrue(verification_result.get('valid', False), f'JWT verification failed for {security_level.value}')
            self.assertEqual(verification_result.get('user_id'), test_user_id, 'Incorrect user ID from JWT verification')
            wrong_secret_result = await self.unified_auth.verify_jwt_token(token=access_token, secret_key='wrong_secret_key_12345', required_claims=['sub', 'email'])
            self.assertFalse(wrong_secret_result.get('valid', True), f'JWT verification should have failed with wrong secret for {security_level.value}')
            refresh_token = jwt_result['refresh_token']
            await asyncio.sleep(1)
            refresh_result = await self.unified_auth.refresh_jwt_token(refresh_token=refresh_token, user_id=test_user_id)
            self.assertTrue(refresh_result.get('success', False), f'JWT refresh failed for {security_level.value}')
            self.assertIsNotNone(refresh_result.get('new_access_token'), f'No new access token from refresh for {security_level.value}')
            new_access_token = refresh_result['new_access_token']
            self.assertNotEqual(access_token, new_access_token, f'Refresh token should generate new access token for {security_level.value}')
            jwt_test_results.append({'security_level': security_level.value, 'generation_time': jwt_generation_time, 'generation_success': True, 'verification_success': verification_result.get('valid', False), 'refresh_success': refresh_result.get('success', False), 'access_token': access_token, 'refresh_token': refresh_token})
        short_lived_jwt = await self.unified_auth.generate_jwt_token(user_id=test_user_id, email=test_email, security_level=SecurityLevel.STANDARD, expiry_minutes=0.1)
        self.assertTrue(short_lived_jwt.get('success', False), 'Short-lived JWT generation failed')
        short_token = short_lived_jwt['access_token']
        immediate_verification = await self.unified_auth.verify_jwt_token(token=short_token, check_expiration=True)
        self.assertTrue(immediate_verification.get('valid', False), 'Short-lived JWT should be immediately valid')
        await asyncio.sleep(10)
        expired_verification = await self.unified_auth.verify_jwt_token(token=short_token, check_expiration=True)
        self.assertFalse(expired_verification.get('valid', True), 'Expired JWT should not be valid')
        self.assertIn('expired', expired_verification.get('error', '').lower(), 'Wrong error message for expired JWT')
        active_token = jwt_test_results[0]['access_token']
        revocation_result = await self.unified_auth.revoke_jwt_token(token=active_token, user_id=test_user_id, reason='security_test')
        self.assertTrue(revocation_result.get('success', False), 'JWT revocation failed')
        revoked_verification = await self.unified_auth.verify_jwt_token(token=active_token, check_revocation=True)
        self.assertFalse(revoked_verification.get('valid', True), 'Revoked JWT should not be valid')
        avg_generation_time = sum((r['generation_time'] for r in jwt_test_results)) / len(jwt_test_results)
        self.assertLess(avg_generation_time, 0.1, f'JWT generation too slow: {avg_generation_time}s')

    @pytest.mark.e2e_gcp_staging
    async def test_rate_limiting_and_brute_force_protection(self):
        """
        Test rate limiting and brute force attack protection.
        
        Business Value: Security - prevents credential stuffing and DoS attacks.
        Validates: Login rate limits, IP-based blocking, progressive delays.
        """
        rate_limit_scenarios = [{'scenario': 'normal_usage', 'requests_per_minute': 10, 'expected_success_rate': 1.0, 'ip_address': '192.168.1.100'}, {'scenario': 'high_usage', 'requests_per_minute': 30, 'expected_success_rate': 0.8, 'ip_address': '192.168.1.101'}, {'scenario': 'brute_force_attack', 'requests_per_minute': 100, 'expected_success_rate': 0.1, 'ip_address': '10.0.0.50'}]
        rate_limit_results = []
        for scenario in rate_limit_scenarios:
            scenario_start_time = time.time()
            scenario_results = {'scenario': scenario['scenario'], 'requests_attempted': scenario['requests_per_minute'], 'requests_successful': 0, 'requests_rate_limited': 0, 'requests_blocked': 0, 'average_response_time': 0, 'progressive_delay_detected': False}
            response_times = []
            for attempt in range(scenario['requests_per_minute']):
                attempt_start = time.time()
                test_email = f'rate.limit.test.{attempt}@netrasystems.ai'
                wrong_password = f'wrong_password_{attempt}'
                login_result = await self.unified_auth.authenticate_user(email=test_email, password=wrong_password, ip_address=scenario['ip_address'], user_agent='Rate Limit Test Bot', bypass_rate_limit=False)
                attempt_time = time.time() - attempt_start
                response_times.append(attempt_time)
                if login_result.get('success', False):
                    scenario_results['requests_successful'] += 1
                elif 'rate_limit' in login_result.get('error_code', ''):
                    scenario_results['requests_rate_limited'] += 1
                elif 'blocked' in login_result.get('error_code', ''):
                    scenario_results['requests_blocked'] += 1
                if attempt > 5 and attempt_time > response_times[0] * 2:
                    scenario_results['progressive_delay_detected'] = True
                if scenario['scenario'] != 'brute_force_attack':
                    await asyncio.sleep(0.1)
            scenario_results['average_response_time'] = sum(response_times) / len(response_times)
            scenario_results['actual_success_rate'] = scenario_results['requests_successful'] / scenario_results['requests_attempted']
            if scenario['scenario'] == 'normal_usage':
                self.assertGreater(scenario_results['actual_success_rate'], 0.7, 'Normal usage too heavily rate limited')
            elif scenario['scenario'] == 'high_usage':
                self.assertGreater(scenario_results['requests_rate_limited'], 0, 'High usage not being rate limited')
            elif scenario['scenario'] == 'brute_force_attack':
                self.assertGreater(scenario_results['requests_blocked'] + scenario_results['requests_rate_limited'], scenario_results['requests_attempted'] * 0.8, 'Brute force attack not sufficiently blocked')
                self.assertTrue(scenario_results['progressive_delay_detected'], 'Progressive delay not detected for brute force')
            rate_limit_results.append(scenario_results)
        attack_ip = '192.168.100.200'
        for attack_round in range(3):
            attack_tasks = []
            for i in range(20):
                attack_email = f'attack.test.{attack_round}.{i}@netrasystems.ai'
                attack_task = self.unified_auth.authenticate_user(email=attack_email, password='definitely_wrong_password', ip_address=attack_ip, user_agent='Attack Bot', bypass_rate_limit=False)
                attack_tasks.append(attack_task)
            attack_results = await asyncio.gather(*attack_tasks, return_exceptions=True)
            if attack_round >= 1:
                blocked_count = sum((1 for result in attack_results if not isinstance(result, Exception) and 'blocked' in result.get('error_code', '')))
                self.assertGreater(blocked_count, 15, f'Insufficient IP blocking after attack round {attack_round}')
            await asyncio.sleep(1)
        whitelist_ip = '192.168.1.250'
        whitelist_result = await self.unified_auth.add_ip_to_whitelist(ip_address=whitelist_ip, reason='rate_limit_test', expiry_hours=1)
        self.assertTrue(whitelist_result.get('success', False), 'IP whitelist addition failed')
        whitelist_test_tasks = []
        for i in range(50):
            whitelist_email = f'whitelist.test.{i}@netrasystems.ai'
            whitelist_task = self.unified_auth.authenticate_user(email=whitelist_email, password='wrong_password', ip_address=whitelist_ip, user_agent='Whitelist Test', bypass_rate_limit=False)
            whitelist_test_tasks.append(whitelist_task)
        whitelist_results = await asyncio.gather(*whitelist_test_tasks, return_exceptions=True)
        non_rate_limited = sum((1 for result in whitelist_results if not isinstance(result, Exception) and 'rate_limit' not in result.get('error_code', '')))
        whitelist_bypass_rate = non_rate_limited / len(whitelist_results)
        self.assertGreater(whitelist_bypass_rate, 0.9, f'Whitelist not effectively bypassing rate limits: {whitelist_bypass_rate}')

    @pytest.mark.e2e_gcp_staging
    async def test_audit_logging_compliance_comprehensive(self):
        """
        Test comprehensive audit logging for security compliance.
        
        Business Value: $15K+ MRR per Enterprise - regulatory compliance required.
        Validates: Audit trail completeness, log integrity, compliance reporting.
        """
        audit_user_id = self.id_manager.generate_user_id()
        audit_email = 'audit.compliance@enterprise.netrasystems.ai'
        audit_config = await self.unified_auth.configure_audit_logging(log_level='comprehensive', retention_days=2555, encryption_enabled=True, integrity_checking=True, real_time_alerts=True, compliance_standards=['sox', 'gdpr', 'hipaa', 'iso27001'])
        self.assertTrue(audit_config.get('success', False), 'Audit logging configuration failed')
        audit_activities = [{'activity': 'user_registration', 'data': {'email': audit_email, 'security_level': 'enterprise'}}, {'activity': 'login_attempt', 'data': {'email': audit_email, 'success': True, 'mfa_used': True}}, {'activity': 'login_failure', 'data': {'email': audit_email, 'reason': 'wrong_password'}}, {'activity': 'password_change', 'data': {'user_id': audit_user_id, 'forced': False}}, {'activity': 'mfa_setup', 'data': {'user_id': audit_user_id, 'method': 'totp'}}, {'activity': 'permission_granted', 'data': {'user_id': audit_user_id, 'permission': 'admin_access'}}, {'activity': 'permission_denied', 'data': {'user_id': audit_user_id, 'resource': 'sensitive_data'}}, {'activity': 'role_assignment', 'data': {'user_id': audit_user_id, 'role': 'enterprise_admin'}}, {'activity': 'session_created', 'data': {'user_id': audit_user_id, 'device': 'laptop'}}, {'activity': 'session_expired', 'data': {'user_id': audit_user_id, 'reason': 'timeout'}}, {'activity': 'concurrent_session_limit', 'data': {'user_id': audit_user_id, 'limit': 5}}, {'activity': 'suspicious_login', 'data': {'user_id': audit_user_id, 'reason': 'unusual_location'}}, {'activity': 'account_locked', 'data': {'user_id': audit_user_id, 'reason': 'brute_force'}}, {'activity': 'security_alert', 'data': {'user_id': audit_user_id, 'alert_type': 'credential_stuffing'}}, {'activity': 'data_access', 'data': {'user_id': audit_user_id, 'resource': 'customer_data', 'action': 'read'}}, {'activity': 'data_modification', 'data': {'user_id': audit_user_id, 'resource': 'user_profile', 'action': 'update'}}, {'activity': 'data_deletion', 'data': {'user_id': audit_user_id, 'resource': 'audit_logs', 'action': 'delete'}}, {'activity': 'admin_action', 'data': {'admin_id': audit_user_id, 'action': 'user_deletion', 'target': 'test_user'}}, {'activity': 'config_change', 'data': {'admin_id': audit_user_id, 'setting': 'password_policy', 'old_value': 'standard', 'new_value': 'strict'}}, {'activity': 'backup_created', 'data': {'admin_id': audit_user_id, 'backup_type': 'full', 'size_mb': 1024}}]
        generated_events = []
        for activity in audit_activities:
            event_result = await self.unified_auth.log_audit_event(activity_type=activity['activity'], user_id=audit_user_id, event_data=activity['data'], ip_address='192.168.1.100', user_agent='Audit Test Client', timestamp=time.time(), compliance_level='enterprise')
            self.assertTrue(event_result.get('logged', False), f"Audit event logging failed: {activity['activity']}")
            generated_events.append({'event_id': event_result.get('event_id'), 'activity_type': activity['activity'], 'timestamp': event_result.get('timestamp'), 'integrity_hash': event_result.get('integrity_hash')})
        await asyncio.sleep(2)
        audit_query_tests = [{'name': 'user_authentication_events', 'query': {'user_id': audit_user_id, 'activity_types': ['login_attempt', 'login_failure', 'mfa_setup'], 'time_range_hours': 1}, 'expected_min_count': 3}, {'name': 'security_events', 'query': {'user_id': audit_user_id, 'activity_types': ['suspicious_login', 'account_locked', 'security_alert'], 'time_range_hours': 1}, 'expected_min_count': 3}, {'name': 'data_access_events', 'query': {'user_id': audit_user_id, 'activity_types': ['data_access', 'data_modification', 'data_deletion'], 'time_range_hours': 1}, 'expected_min_count': 3}, {'name': 'administrative_events', 'query': {'user_id': audit_user_id, 'activity_types': ['admin_action', 'config_change', 'backup_created'], 'time_range_hours': 1}, 'expected_min_count': 3}]
        query_results = []
        for test in audit_query_tests:
            query_result = await self.unified_auth.query_audit_logs(query_params=test['query'], include_metadata=True, verify_integrity=True)
            self.assertTrue(query_result.get('success', False), f"Audit log query failed: {test['name']}")
            events = query_result.get('events', [])
            self.assertGreaterEqual(len(events), test['expected_min_count'], f"Insufficient audit events for {test['name']}: {len(events)}")
            for event in events:
                integrity_valid = query_result.get('integrity_checks', {}).get(event['event_id'], False)
                self.assertTrue(integrity_valid, f"Integrity check failed for event {event['event_id']}")
            query_results.append({'test_name': test['name'], 'events_found': len(events), 'integrity_verified': True})
        compliance_reports = []
        for standard in ['sox', 'gdpr', 'hipaa', 'iso27001']:
            report_generation_start = time.time()
            compliance_report = await self.unified_auth.generate_compliance_report(compliance_standard=standard, user_id=audit_user_id, time_range_days=1, include_recommendations=True, include_risk_assessment=True)
            report_generation_time = time.time() - report_generation_start
            self.assertTrue(compliance_report.get('success', False), f'Compliance report generation failed for {standard}')
            report_data = compliance_report.get('report', {})
            required_sections = ['executive_summary', 'audit_events', 'compliance_status', 'recommendations']
            for section in required_sections:
                self.assertIn(section, report_data, f'Missing section {section} in {standard} compliance report')
            compliance_metrics = report_data.get('compliance_status', {})
            self.assertIn('compliance_score', compliance_metrics, f'Missing compliance score in {standard} report')
            self.assertIn('total_events_audited', compliance_metrics, f'Missing event count in {standard} report')
            self.assertLess(report_generation_time, 30.0, f'{standard} compliance report generation too slow: {report_generation_time}s')
            compliance_reports.append({'standard': standard, 'generation_time': report_generation_time, 'events_audited': compliance_metrics.get('total_events_audited', 0), 'compliance_score': compliance_metrics.get('compliance_score', 0)})
        integrity_check_result = await self.unified_auth.verify_audit_log_integrity(user_id=audit_user_id, time_range_hours=1, deep_verification=True)
        self.assertTrue(integrity_check_result.get('integrity_valid', False), 'Audit log integrity verification failed')
        self.assertEqual(integrity_check_result.get('tampered_events', 0), 0, 'Evidence of audit log tampering detected')
        export_result = await self.unified_auth.export_audit_logs(user_id=audit_user_id, time_range_hours=1, format='json', include_integrity_proofs=True, encryption_enabled=True)
        self.assertTrue(export_result.get('success', False), 'Audit log export failed')
        self.assertIsNotNone(export_result.get('export_file_path'), 'No export file path provided')
        self.assertGreater(export_result.get('events_exported', 0), 15, 'Insufficient events in audit export')
        overall_compliance_score = sum((report['compliance_score'] for report in compliance_reports)) / len(compliance_reports)
        self.assertGreater(overall_compliance_score, 85.0, f'Overall compliance score too low: {overall_compliance_score}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')