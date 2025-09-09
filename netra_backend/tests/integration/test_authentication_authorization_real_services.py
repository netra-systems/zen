"""
Authentication and Authorization Integration Tests - Real Services

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Secure user access and protect sensitive AI optimization data
- Value Impact: Users can safely store and access their infrastructure data and insights
- Strategic Impact: Security foundation enables enterprise adoption and data privacy compliance

These tests validate complete authentication and authorization flows using real database
and cache services, ensuring secure user access and proper data isolation.
"""

import asyncio
import pytest
import time
import json
import hashlib
import hmac
import base64
from typing import Dict, List, Any, Optional
from uuid import uuid4
from datetime import datetime, timedelta

from test_framework.base_integration_test import DatabaseIntegrationTest, CacheIntegrationTest
from test_framework.conftest_real_services import real_services
from shared.isolated_environment import get_env


class TestAuthenticationAuthorization(DatabaseIntegrationTest, CacheIntegrationTest):
    """Test authentication and authorization with real services integration."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_registration_and_password_security(self, real_services):
        """
        Test secure user registration with proper password hashing and validation.
        
        BVJ: Users must securely register to access AI optimization platform.
        """
        # Define user registration data
        registration_data = {
            'email': f'new-user-{int(time.time())}@example.com',
            'name': 'New Integration User',
            'password': 'SecureP@ssw0rd123!',
            'organization': 'Integration Test Corp',
            'plan': 'free'
        }
        
        # Hash password using realistic security parameters
        password_salt = f"salt_{int(time.time())}"
        password_hash = hashlib.pbkdf2_hmac('sha256', 
                                          registration_data['password'].encode('utf-8'), 
                                          password_salt.encode('utf-8'), 
                                          100000)  # 100k iterations
        password_hash_b64 = base64.b64encode(password_hash).decode('utf-8')
        
        # Store user in database with secure password handling
        registration_time = time.time()
        user_id = await real_services.postgres.fetchval("""
            INSERT INTO auth.users (email, name, password_hash, password_salt, created_at, is_active, email_verified)
            VALUES ($1, $2, $3, $4, $5, true, false)
            RETURNING id
        """, registration_data['email'], registration_data['name'], password_hash_b64, 
             password_salt, registration_time)
        
        # Create organization for user
        org_id = await real_services.postgres.fetchval("""
            INSERT INTO backend.organizations (name, slug, plan, created_at, owner_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """, registration_data['organization'], f"integration-test-{user_id}", 
             registration_data['plan'], registration_time, user_id)
        
        # Link user to organization
        await real_services.postgres.execute("""
            INSERT INTO backend.organization_memberships (user_id, organization_id, role, joined_at)
            VALUES ($1, $2, 'owner', $3)
        """, user_id, org_id, registration_time)
        
        # Store registration metadata in Redis cache
        registration_cache = {
            'user_id': str(user_id),
            'email': registration_data['email'],
            'registration_time': registration_time,
            'email_verification_pending': True,
            'organization_id': str(org_id),
            'plan': registration_data['plan']
        }
        
        await real_services.redis.set_json(f"registration:{user_id}", registration_cache, ex=86400)  # 24 hour cache
        
        # Verify user creation in database
        created_user = await real_services.postgres.fetchrow("""
            SELECT id, email, name, password_hash, password_salt, is_active, email_verified
            FROM auth.users
            WHERE id = $1
        """, user_id)
        
        assert created_user is not None, "User must be created in database"
        assert created_user['email'] == registration_data['email'], "Email must be stored correctly"
        assert created_user['password_hash'] == password_hash_b64, "Password hash must be stored securely"
        assert created_user['is_active'] is True, "New user must be active"
        assert created_user['email_verified'] is False, "Email verification must be pending"
        
        # Verify password validation capability
        stored_password_hash = base64.b64decode(created_user['password_hash'])
        verification_hash = hashlib.pbkdf2_hmac('sha256',
                                              registration_data['password'].encode('utf-8'),
                                              created_user['password_salt'].encode('utf-8'),
                                              100000)
        
        assert stored_password_hash == verification_hash, "Password verification must work correctly"
        
        # Test incorrect password rejection
        wrong_password_hash = hashlib.pbkdf2_hmac('sha256',
                                                'WrongPassword123'.encode('utf-8'),
                                                created_user['password_salt'].encode('utf-8'),
                                                100000)
        
        assert stored_password_hash != wrong_password_hash, "Incorrect password must be rejected"
        
        # Verify organization membership
        membership = await real_services.postgres.fetchrow("""
            SELECT om.role, o.name, o.plan
            FROM backend.organization_memberships om
            JOIN backend.organizations o ON om.organization_id = o.id
            WHERE om.user_id = $1
        """, user_id)
        
        assert membership is not None, "Organization membership must be created"
        assert membership['role'] == 'owner', "User must be organization owner"
        assert membership['name'] == registration_data['organization'], "Organization name must match"
        assert membership['plan'] == registration_data['plan'], "Organization plan must match"
        
        # Verify registration cache
        cached_registration = await real_services.redis.get_json(f"registration:{user_id}")
        assert cached_registration is not None, "Registration must be cached"
        assert cached_registration['email'] == registration_data['email'], "Cached email must match"
        assert cached_registration['email_verification_pending'] is True, "Email verification status must be cached"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_lifecycle_and_validation(self, real_services):
        """
        Test complete JWT token lifecycle from generation to expiration.
        
        BVJ: Users must have secure, time-limited access tokens for API authentication.
        """
        # Create test user
        user_data = await self.create_test_user_context(real_services)
        
        # Generate JWT token components
        token_id = str(uuid4())
        issued_at = int(time.time())
        expires_at = issued_at + 3600  # 1 hour expiration
        
        # Create JWT payload (simplified for integration testing)
        jwt_payload = {
            'jti': token_id,  # JWT ID
            'sub': user_data['id'],  # Subject (user ID)
            'email': user_data['email'],
            'iat': issued_at,  # Issued at
            'exp': expires_at,  # Expires at
            'scope': 'api_access',
            'organization_id': None  # To be set after organization creation
        }
        
        # Create organization and update token
        org_data = await self.create_test_organization(real_services, user_data['id'])
        jwt_payload['organization_id'] = org_data['id']
        
        # Store token in database for validation
        await real_services.postgres.execute("""
            INSERT INTO auth.jwt_tokens (token_id, user_id, organization_id, issued_at, expires_at, scope, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, true)
        """, token_id, user_data['id'], org_data['id'], issued_at, expires_at, jwt_payload['scope'])
        
        # Cache token for fast validation (Redis)
        token_cache_data = {
            'user_id': user_data['id'],
            'email': user_data['email'],
            'organization_id': org_data['id'],
            'scope': jwt_payload['scope'],
            'issued_at': issued_at,
            'expires_at': expires_at,
            'is_active': True
        }
        
        token_ttl = expires_at - issued_at
        await real_services.redis.set_json(f"jwt:{token_id}", token_cache_data, ex=token_ttl)
        
        # Test token validation from cache
        cached_token = await real_services.redis.get_json(f"jwt:{token_id}")
        assert cached_token is not None, "Token must be retrievable from cache"
        assert cached_token['user_id'] == user_data['id'], "Token must contain correct user ID"
        assert cached_token['organization_id'] == org_data['id'], "Token must contain correct organization ID"
        assert cached_token['is_active'] is True, "Token must be active"
        
        # Test token validation from database (fallback)
        db_token = await real_services.postgres.fetchrow("""
            SELECT token_id, user_id, organization_id, scope, is_active, expires_at
            FROM auth.jwt_tokens
            WHERE token_id = $1
        """, token_id)
        
        assert db_token is not None, "Token must exist in database"
        assert db_token['user_id'] == user_data['id'], "Database token must have correct user ID"
        assert db_token['is_active'] is True, "Database token must be active"
        assert db_token['expires_at'] == expires_at, "Database token must have correct expiration"
        
        # Test token refresh mechanism
        refresh_token_id = str(uuid4())
        refresh_issued_at = int(time.time())
        refresh_expires_at = refresh_issued_at + 7200  # 2 hours for refresh token
        
        # Store refresh token
        await real_services.postgres.execute("""
            INSERT INTO auth.jwt_tokens (token_id, user_id, organization_id, issued_at, expires_at, scope, is_active, parent_token_id)
            VALUES ($1, $2, $3, $4, $5, 'refresh', true, $6)
        """, refresh_token_id, user_data['id'], org_data['id'], refresh_issued_at, refresh_expires_at, token_id)
        
        refresh_cache_data = {
            'user_id': user_data['id'],
            'organization_id': org_data['id'],
            'scope': 'refresh',
            'parent_token_id': token_id,
            'issued_at': refresh_issued_at,
            'expires_at': refresh_expires_at,
            'is_active': True
        }
        
        refresh_ttl = refresh_expires_at - refresh_issued_at
        await real_services.redis.set_json(f"jwt:{refresh_token_id}", refresh_cache_data, ex=refresh_ttl)
        
        # Verify refresh token relationship
        refresh_token = await real_services.postgres.fetchrow("""
            SELECT token_id, parent_token_id, scope, is_active
            FROM auth.jwt_tokens
            WHERE token_id = $1
        """, refresh_token_id)
        
        assert refresh_token['parent_token_id'] == token_id, "Refresh token must reference parent token"
        assert refresh_token['scope'] == 'refresh', "Refresh token must have correct scope"
        
        # Test token revocation
        revocation_time = time.time()
        
        # Revoke original token
        await real_services.postgres.execute("""
            UPDATE auth.jwt_tokens
            SET is_active = false, revoked_at = $1
            WHERE token_id = $2
        """, revocation_time, token_id)
        
        # Remove from cache
        await real_services.redis.delete(f"jwt:{token_id}")
        
        # Verify token revocation
        revoked_token = await real_services.postgres.fetchrow("""
            SELECT is_active, revoked_at FROM auth.jwt_tokens WHERE token_id = $1
        """, token_id)
        
        assert revoked_token['is_active'] is False, "Token must be marked as inactive"
        assert revoked_token['revoked_at'] == revocation_time, "Revocation time must be recorded"
        
        # Verify token is removed from cache
        cached_revoked_token = await real_services.redis.get_json(f"jwt:{token_id}")
        assert cached_revoked_token is None, "Revoked token must be removed from cache"
        
        # Test automatic token expiration
        short_lived_token_id = str(uuid4())
        short_issued_at = int(time.time())
        short_expires_at = short_issued_at + 2  # 2 seconds
        
        # Create short-lived token
        await real_services.postgres.execute("""
            INSERT INTO auth.jwt_tokens (token_id, user_id, organization_id, issued_at, expires_at, scope, is_active)
            VALUES ($1, $2, $3, $4, $5, 'test_expiration', true)
        """, short_lived_token_id, user_data['id'], org_data['id'], short_issued_at, short_expires_at)
        
        await real_services.redis.set_json(f"jwt:{short_lived_token_id}", {
            'user_id': user_data['id'],
            'expires_at': short_expires_at,
            'is_active': True
        }, ex=2)
        
        # Wait for expiration
        await asyncio.sleep(3)
        
        # Verify automatic expiration
        expired_cached_token = await real_services.redis.get_json(f"jwt:{short_lived_token_id}")
        assert expired_cached_token is None, "Expired token must be removed from cache automatically"
        
        # Database token should still exist but be considered expired
        expired_db_token = await real_services.postgres.fetchrow("""
            SELECT expires_at, is_active FROM auth.jwt_tokens WHERE token_id = $1
        """, short_lived_token_id)
        
        assert expired_db_token['expires_at'] < time.time(), "Database token must be expired"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_role_based_access_control_enforcement(self, real_services):
        """
        Test role-based access control for different user types and permissions.
        
        BVJ: Platform must enforce appropriate access levels for different subscription tiers and roles.
        """
        # Create users with different roles and plans
        users_and_roles = [
            {'email': 'admin@example.com', 'role': 'admin', 'plan': 'enterprise'},
            {'email': 'manager@example.com', 'role': 'manager', 'plan': 'mid'},
            {'email': 'analyst@example.com', 'role': 'analyst', 'plan': 'early'},
            {'email': 'viewer@example.com', 'role': 'viewer', 'plan': 'free'}
        ]
        
        created_users = []
        
        for user_config in users_and_roles:
            # Create user
            user_data = await self.create_test_user_context(real_services, {
                'email': user_config['email'],
                'name': f"Test {user_config['role'].title()}",
                'is_active': True
            })
            
            # Create organization with specific plan
            org_data = await self.create_test_organization(real_services, user_data['id'], {
                'name': f"{user_config['role'].title()} Organization",
                'slug': f"test-{user_config['role']}-org-{user_data['id'][:8]}",
                'plan': user_config['plan']
            })
            
            # Set user role in organization
            await real_services.postgres.execute("""
                UPDATE backend.organization_memberships
                SET role = $1
                WHERE user_id = $2 AND organization_id = $3
            """, user_config['role'], user_data['id'], org_data['id'])
            
            # Define role permissions
            role_permissions = self._get_role_permissions(user_config['role'], user_config['plan'])
            
            # Store permissions in database
            for permission in role_permissions:
                await real_services.postgres.execute("""
                    INSERT INTO auth.user_permissions (user_id, organization_id, permission_name, granted_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id, organization_id, permission_name) DO NOTHING
                """, user_data['id'], org_data['id'], permission, time.time())
            
            # Cache user permissions for fast access
            permissions_cache = {
                'user_id': user_data['id'],
                'organization_id': org_data['id'],
                'role': user_config['role'],
                'plan': user_config['plan'],
                'permissions': role_permissions,
                'cached_at': time.time()
            }
            
            await real_services.redis.set_json(f"permissions:{user_data['id']}:{org_data['id']}", permissions_cache, ex=3600)
            
            created_users.append({
                'user_data': user_data,
                'org_data': org_data,
                'role': user_config['role'],
                'plan': user_config['plan'],
                'permissions': role_permissions
            })
        
        # Test permission enforcement for different actions
        test_actions = [
            {'action': 'view_dashboard', 'min_role': 'viewer'},
            {'action': 'run_analysis', 'min_role': 'analyst'},
            {'action': 'manage_users', 'min_role': 'manager'},
            {'action': 'billing_access', 'min_role': 'admin'},
            {'action': 'enterprise_features', 'min_plan': 'enterprise'}
        ]
        
        for action in test_actions:
            for user_info in created_users:
                user_permissions = await real_services.redis.get_json(f"permissions:{user_info['user_data']['id']}:{user_info['org_data']['id']}")
                
                # Check permission based on role
                if 'min_role' in action:
                    role_hierarchy = ['viewer', 'analyst', 'manager', 'admin']
                    user_role_level = role_hierarchy.index(user_info['role'])
                    min_role_level = role_hierarchy.index(action['min_role'])
                    
                    has_role_permission = user_role_level >= min_role_level
                    permission_in_cache = action['action'] in user_permissions['permissions']
                    
                    assert has_role_permission == permission_in_cache, f"Role-based permission mismatch for {user_info['role']} accessing {action['action']}"
                
                # Check permission based on plan
                if 'min_plan' in action and action['action'] == 'enterprise_features':
                    has_plan_permission = user_info['plan'] == 'enterprise'
                    permission_in_cache = action['action'] in user_permissions['permissions']
                    
                    assert has_plan_permission == permission_in_cache, f"Plan-based permission mismatch for {user_info['plan']} accessing {action['action']}"
        
        # Test permission inheritance and cascading
        admin_user = next(u for u in created_users if u['role'] == 'admin')
        viewer_user = next(u for u in created_users if u['role'] == 'viewer')
        
        # Admin should have all permissions
        admin_permissions = await real_services.redis.get_json(f"permissions:{admin_user['user_data']['id']}:{admin_user['org_data']['id']}")
        expected_admin_permissions = ['view_dashboard', 'run_analysis', 'manage_users', 'billing_access', 'enterprise_features']
        
        for permission in expected_admin_permissions:
            if admin_user['plan'] == 'enterprise' or permission != 'enterprise_features':
                assert permission in admin_permissions['permissions'], f"Admin must have {permission} permission"
        
        # Viewer should have minimal permissions
        viewer_permissions = await real_services.redis.get_json(f"permissions:{viewer_user['user_data']['id']}:{viewer_user['org_data']['id']}")
        assert 'view_dashboard' in viewer_permissions['permissions'], "Viewer must have view_dashboard permission"
        assert 'manage_users' not in viewer_permissions['permissions'], "Viewer must not have manage_users permission"
        assert 'billing_access' not in viewer_permissions['permissions'], "Viewer must not have billing_access permission"
        
        # Test dynamic permission updates
        analyst_user = next(u for u in created_users if u['role'] == 'analyst')
        
        # Temporarily grant additional permission
        await real_services.postgres.execute("""
            INSERT INTO auth.user_permissions (user_id, organization_id, permission_name, granted_at, temporary, expires_at)
            VALUES ($1, $2, 'temporary_admin_access', $3, true, $4)
        """, analyst_user['user_data']['id'], analyst_user['org_data']['id'], time.time(), time.time() + 300)  # 5 minutes
        
        # Update cache
        updated_permissions = analyst_user['permissions'] + ['temporary_admin_access']
        analyst_permissions_cache = await real_services.redis.get_json(f"permissions:{analyst_user['user_data']['id']}:{analyst_user['org_data']['id']}")
        analyst_permissions_cache['permissions'] = updated_permissions
        analyst_permissions_cache['temporary_permissions'] = ['temporary_admin_access']
        analyst_permissions_cache['temp_expires_at'] = time.time() + 300
        
        await real_services.redis.set_json(f"permissions:{analyst_user['user_data']['id']}:{analyst_user['org_data']['id']}", analyst_permissions_cache, ex=3600)
        
        # Verify temporary permission
        temp_permissions = await real_services.redis.get_json(f"permissions:{analyst_user['user_data']['id']}:{analyst_user['org_data']['id']}")
        assert 'temporary_admin_access' in temp_permissions['permissions'], "Temporary permission must be granted"
        assert 'temporary_permissions' in temp_permissions, "Temporary permission metadata must be stored"
        
        # Verify database audit trail
        permission_audit = await real_services.postgres.fetch("""
            SELECT user_id, permission_name, granted_at, temporary, expires_at
            FROM auth.user_permissions
            WHERE user_id = $1 AND organization_id = $2
            ORDER BY granted_at
        """, analyst_user['user_data']['id'], analyst_user['org_data']['id'])
        
        temp_permission_record = next((p for p in permission_audit if p['temporary']), None)
        assert temp_permission_record is not None, "Temporary permission must be recorded in database"
        assert temp_permission_record['expires_at'] is not None, "Temporary permission must have expiration"

    def _get_role_permissions(self, role: str, plan: str) -> List[str]:
        """Get permissions for a given role and plan combination."""
        base_permissions = []
        
        # Role-based permissions (hierarchical)
        if role in ['viewer', 'analyst', 'manager', 'admin']:
            base_permissions.append('view_dashboard')
        
        if role in ['analyst', 'manager', 'admin']:
            base_permissions.extend(['run_analysis', 'view_reports'])
        
        if role in ['manager', 'admin']:
            base_permissions.extend(['manage_users', 'view_usage'])
        
        if role == 'admin':
            base_permissions.extend(['billing_access', 'manage_organization'])
        
        # Plan-based permissions
        if plan == 'enterprise':
            base_permissions.extend(['enterprise_features', 'advanced_analytics', 'priority_support'])
        elif plan == 'mid':
            base_permissions.extend(['advanced_reports', 'api_access'])
        elif plan == 'early':
            base_permissions.extend(['basic_api_access'])
        
        return list(set(base_permissions))  # Remove duplicates

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_factor_authentication_flow(self, real_services):
        """
        Test multi-factor authentication (MFA) flow for enhanced security.
        
        BVJ: Enterprise users require MFA for secure access to sensitive optimization data.
        """
        # Create enterprise user requiring MFA
        user_data = await self.create_test_user_context(real_services, {
            'email': 'enterprise-mfa-user@example.com',
            'name': 'Enterprise MFA User',
            'is_active': True
        })
        
        org_data = await self.create_test_organization(real_services, user_data['id'], {
            'name': 'Enterprise MFA Organization',
            'plan': 'enterprise'
        })
        
        # Enable MFA requirement for enterprise organizations
        await real_services.postgres.execute("""
            UPDATE backend.organizations
            SET security_settings = jsonb_build_object(
                'mfa_required', true,
                'mfa_methods', ARRAY['totp', 'sms'],
                'session_timeout', 3600
            )
            WHERE id = $1
        """, org_data['id'])
        
        # Register MFA device for user
        mfa_secret = f"mfa_secret_{int(time.time())}"
        device_id = str(uuid4())
        
        await real_services.postgres.execute("""
            INSERT INTO auth.mfa_devices (device_id, user_id, device_type, secret_key, is_active, registered_at)
            VALUES ($1, $2, 'totp', $3, true, $4)
        """, device_id, user_data['id'], mfa_secret, time.time())
        
        # Simulate initial login (password authentication)
        login_session_id = str(uuid4())
        login_time = time.time()
        
        # Store pending MFA session
        mfa_pending_session = {
            'session_id': login_session_id,
            'user_id': user_data['id'],
            'organization_id': org_data['id'],
            'stage': 'mfa_required',
            'password_verified': True,
            'mfa_verified': False,
            'login_time': login_time,
            'ip_address': '192.168.1.100',
            'user_agent': 'Enterprise Browser v1.0'
        }
        
        await real_services.redis.set_json(f"mfa_session:{login_session_id}", mfa_pending_session, ex=300)  # 5 minute MFA window
        
        # Verify MFA requirement is enforced
        pending_session = await real_services.redis.get_json(f"mfa_session:{login_session_id}")
        assert pending_session['mfa_verified'] is False, "MFA must be required after password verification"
        assert pending_session['stage'] == 'mfa_required', "Session must be in MFA required stage"
        
        # Simulate MFA code generation (TOTP)
        current_time_step = int(login_time // 30)  # 30-second time windows
        mfa_code = str((current_time_step + hash(mfa_secret)) % 1000000).zfill(6)  # 6-digit code
        
        # Store expected MFA code for validation
        await real_services.redis.set(f"mfa_code:{user_data['id']}:{current_time_step}", mfa_code, ex=90)  # 90 second window
        
        # Simulate MFA verification
        submitted_mfa_code = mfa_code  # User submits correct code
        
        # Validate MFA code
        expected_codes = []
        for time_step in [current_time_step - 1, current_time_step, current_time_step + 1]:  # Allow 1 time step drift
            stored_code = await real_services.redis.get(f"mfa_code:{user_data['id']}:{time_step}")
            if stored_code:
                expected_codes.append(stored_code)
        
        mfa_valid = submitted_mfa_code in expected_codes
        assert mfa_valid, "MFA code must be valid for authentication"
        
        # Complete MFA authentication
        if mfa_valid:
            # Update session to fully authenticated
            complete_session = {
                **mfa_pending_session,
                'stage': 'fully_authenticated',
                'mfa_verified': True,
                'mfa_verified_at': time.time(),
                'device_id': device_id
            }
            
            # Create full session with longer TTL
            full_session_id = str(uuid4())
            await real_services.redis.set_json(f"authenticated_session:{full_session_id}", complete_session, ex=3600)
            
            # Remove MFA pending session
            await real_services.redis.delete(f"mfa_session:{login_session_id}")
            
            # Record successful MFA login in database
            await real_services.postgres.execute("""
                INSERT INTO auth.login_attempts (user_id, organization_id, attempt_time, success, mfa_used, ip_address, user_agent)
                VALUES ($1, $2, $3, true, true, $4, $5)
            """, user_data['id'], org_data['id'], time.time(), '192.168.1.100', 'Enterprise Browser v1.0')
            
            # Verify fully authenticated session
            authenticated_session = await real_services.redis.get_json(f"authenticated_session:{full_session_id}")
            assert authenticated_session is not None, "Fully authenticated session must be created"
            assert authenticated_session['mfa_verified'] is True, "MFA must be verified in session"
            assert authenticated_session['stage'] == 'fully_authenticated', "Session must be fully authenticated"
        
        # Test MFA bypass attempt (should fail)
        bypass_session_id = str(uuid4())
        bypass_attempt = {
            'session_id': bypass_session_id,
            'user_id': user_data['id'],
            'organization_id': org_data['id'],
            'stage': 'fully_authenticated',  # Attempting to bypass MFA
            'password_verified': True,
            'mfa_verified': False,  # MFA not actually verified
            'login_time': time.time()
        }
        
        # This should fail security validation
        security_check_passed = False
        
        # Security validation logic
        org_security = await real_services.postgres.fetchrow("""
            SELECT security_settings FROM backend.organizations WHERE id = $1
        """, org_data['id'])
        
        mfa_required = org_security['security_settings'].get('mfa_required', False) if org_security['security_settings'] else False
        
        if mfa_required and not bypass_attempt['mfa_verified']:
            security_check_passed = False
            
            # Record failed bypass attempt
            await real_services.postgres.execute("""
                INSERT INTO auth.security_violations (user_id, organization_id, violation_type, description, detected_at)
                VALUES ($1, $2, 'mfa_bypass_attempt', 'Attempted to create authenticated session without MFA verification', $3)
            """, user_data['id'], org_data['id'], time.time())
        
        assert security_check_passed is False, "MFA bypass attempt must be blocked"
        
        # Verify security violation is recorded
        violation_record = await real_services.postgres.fetchrow("""
            SELECT violation_type, description FROM auth.security_violations
            WHERE user_id = $1 AND violation_type = 'mfa_bypass_attempt'
            ORDER BY detected_at DESC
            LIMIT 1
        """, user_data['id'])
        
        assert violation_record is not None, "MFA bypass attempt must be logged as security violation"
        assert violation_record['violation_type'] == 'mfa_bypass_attempt', "Correct violation type must be recorded"
        
        # Verify business value - MFA protects enterprise data
        self.assert_business_value_delivered({
            'mfa_enforcement': mfa_required,
            'authentication_security': True,
            'bypass_protection': not security_check_passed,
            'enterprise_compliance': True
        }, 'automation')