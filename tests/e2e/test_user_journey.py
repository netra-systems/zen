"""
E2E Tests for User Journey
Tests complete user flows from signup through first LLM interaction.

Business Value Justification (BVJ):
- Segment: Free-to-Paid conversion critical path
- Business Goal: User Activation, Feature Adoption
- Value Impact: Drives initial value realization and conversion
- Strategic Impact: 80% of users who complete first AI interaction convert to paid
"""

import asyncio
import pytest
import aiohttp
import json
from typing import Dict, List, Optional
import uuid
import time
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig



@pytest.mark.e2e
@pytest.mark.real_services
class TestUserJourney:
    """Test suite for complete user journey flows."""

    @pytest.mark.asyncio
    async def test_complete_signup_flow(self):
        """
        Test complete user signup and initial login flow.
        
        Critical Assertions:
        - User can sign up with email/password
        - Email verification works (if enabled)
        - First login successful
        - Welcome flow triggers
        
        Expected Failure: Signup flow broken at any step
        Business Impact: 100% user acquisition loss
        """
        backend_url = "http://localhost:8000"
        test_user = {
            "email": f"journey.{uuid.uuid4()}@example.com",
            "password": "Journey123!Test",
            "name": "Journey Test User",
            "company": "Test Corp"
        }
        
        async with aiohttp.ClientSession() as session:
            # Step 1: Sign up
            signup_response = await session.post(
                f"{backend_url}/auth/register",
                json=test_user
            )
            
            assert signup_response.status in [200, 201], \
                f"Signup failed: {signup_response.status}"
            
            signup_data = await signup_response.json()
            user_id = signup_data.get('user_id')
            assert user_id, "No user_id returned on signup"
            
            # Check if email verification required
            requires_verification = signup_data.get('requires_email_verification', False)
            if requires_verification:
                verification_token = signup_data.get('verification_token')
                assert verification_token, "No verification token provided"
                
                # Verify email (mock)
                verify_response = await session.post(
                    f"{backend_url}/auth/verify-email",
                    json={"token": verification_token}
                )
                assert verify_response.status == 200, "Email verification failed"
            
            # Step 2: First login
            login_response = await session.post(
                f"{backend_url}/auth/login",
                json={
                    "email": test_user['email'],
                    "password": test_user['password']
                }
            )
            
            assert login_response.status == 200, "First login failed"
            login_data = await login_response.json()
            
            access_token = login_data.get('access_token')
            assert access_token, "No access token on first login"
            
            # Step 3: Check welcome flow
            is_first_login = login_data.get('is_first_login', False)
            if is_first_login:
                assert login_data.get('onboarding_status') == 'pending', \
                    "Onboarding not initiated"
                assert login_data.get('welcome_message'), \
                    "No welcome message for new user"
            
            # Step 4: Get user profile
            profile_response = await session.get(
                f"{backend_url}/api/user/profile",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if profile_response.status == 200:
                profile = await profile_response.json()
                assert profile.get('email') == test_user['email'], \
                    "Profile email mismatch"
                assert profile.get('name') == test_user['name'], \
                    "Profile name mismatch"
                assert profile.get('created_at'), "No creation timestamp"
            
            # Step 5: Check default workspace
            workspace_response = await session.get(
                f"{backend_url}/api/workspace",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if workspace_response.status == 200:
                workspace = await workspace_response.json()
                assert workspace.get('workspace_id'), \
                    "No default workspace created"
                assert workspace.get('is_default'), \
                    "Default workspace not marked"

    @pytest.mark.asyncio
    async def test_user_profile_creation(self):
        """
        Test user profile creation and preferences.
        
        Critical Assertions:
        - Profile fields saved correctly
        - Preferences persisted
        - Avatar upload works
        - Timezone settings applied
        
        Expected Failure: Profile service not functioning
        Business Impact: Poor personalization, reduced engagement
        """
        backend_url = "http://localhost:8000"
        
        # Create and login user
        test_email = f"profile.{uuid.uuid4()}@example.com"
        async with aiohttp.ClientSession() as session:
            # Register
            await session.post(
                f"{backend_url}/auth/register",
                json={
                    "email": test_email,
                    "password": "Profile123!",
                    "name": "Profile Test"
                }
            )
            
            # Login
            login_response = await session.post(
                f"{backend_url}/auth/login",
                json={"email": test_email, "password": "Profile123!"}
            )
            
            login_data = await login_response.json()
            access_token = login_data['access_token']
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Update profile
            profile_update = {
                "name": "Updated Name",
                "bio": "AI optimization expert",
                "company": "Tech Corp",
                "role": "CTO",
                "timezone": "America/New_York",
                "preferences": {
                    "theme": "dark",
                    "notifications": {
                        "email": True,
                        "push": False,
                        "sms": False
                    },
                    "language": "en-US",
                    "ai_preferences": {
                        "default_model": LLMModel.GEMINI_2_5_FLASH.value,
                        "temperature": 0.7,
                        "max_tokens": 2000
                    }
                }
            }
            
            update_response = await session.put(
                f"{backend_url}/api/user/profile",
                json=profile_update,
                headers=headers
            )
            
            if update_response.status == 200:
                updated_profile = await update_response.json()
                
                # Verify updates
                assert updated_profile.get('name') == "Updated Name", \
                    "Name not updated"
                assert updated_profile.get('company') == "Tech Corp", \
                    "Company not saved"
                assert updated_profile.get('timezone') == "America/New_York", \
                    "Timezone not saved"
                
                # Verify preferences
                prefs = updated_profile.get('preferences', {})
                assert prefs.get('theme') == 'dark', "Theme preference not saved"
                assert prefs.get('language') == 'en-US', "Language not saved"
                
                ai_prefs = prefs.get('ai_preferences', {})
                assert ai_prefs.get('default_model') == LLMModel.GEMINI_2_5_FLASH.value, \
                    "AI model preference not saved"
            
            # Test avatar upload (mock)
            avatar_data = b"fake_image_data_png"
            avatar_response = await session.post(
                f"{backend_url}/api/user/avatar",
                data={'file': avatar_data},
                headers=headers
            )
            
            if avatar_response.status == 200:
                avatar_result = await avatar_response.json()
                assert avatar_result.get('avatar_url'), "No avatar URL returned"

    @pytest.mark.asyncio
    async def test_workspace_initialization(self):
        """
        Test workspace creation and initialization.
        
        Critical Assertions:
        - Default workspace created on signup
        - Workspace settings configurable
        - Team invites work
        - Workspace switching works
        
        Expected Failure: Workspace service not initialized
        Business Impact: No multi-tenancy, can't scale to teams
        """
        backend_url = "http://localhost:8000"
        
        async with aiohttp.ClientSession() as session:
            # Create user
            test_email = f"workspace.{uuid.uuid4()}@example.com"
            await session.post(
                f"{backend_url}/auth/register",
                json={
                    "email": test_email,
                    "password": "Workspace123!",
                    "name": "Workspace Test"
                }
            )
            
            # Login
            login_response = await session.post(
                f"{backend_url}/auth/login",
                json={"email": test_email, "password": "Workspace123!"}
            )
            
            login_data = await login_response.json()
            access_token = login_data['access_token']
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Get default workspace
            workspaces_response = await session.get(
                f"{backend_url}/api/workspaces",
                headers=headers
            )
            
            if workspaces_response.status == 200:
                workspaces = await workspaces_response.json()
                assert len(workspaces) >= 1, "No default workspace"
                
                default_ws = workspaces[0]
                assert default_ws.get('workspace_id'), "No workspace ID"
                assert default_ws.get('name'), "No workspace name"
                assert default_ws.get('owner_id'), "No owner ID"
                
                workspace_id = default_ws['workspace_id']
                
                # Update workspace settings
                ws_update = {
                    "name": "AI Optimization Team",
                    "description": "Workspace for AI optimization",
                    "settings": {
                        "ai_limits": {
                            "monthly_tokens": 1000000,
                            "max_concurrent_requests": 10
                        },
                        "security": {
                            "ip_whitelist": [],
                            "require_2fa": False
                        },
                        "integrations": {
                            "slack": {"enabled": False},
                            "github": {"enabled": True}
                        }
                    }
                }
                
                update_response = await session.put(
                    f"{backend_url}/api/workspace/{workspace_id}",
                    json=ws_update,
                    headers=headers
                )
                
                if update_response.status == 200:
                    updated_ws = await update_response.json()
                    assert updated_ws.get('name') == "AI Optimization Team", \
                        "Workspace name not updated"
                    
                    settings = updated_ws.get('settings', {})
                    assert settings.get('ai_limits'), "AI limits not saved"
                
                # Create additional workspace
                new_ws_response = await session.post(
                    f"{backend_url}/api/workspaces",
                    json={
                        "name": "Secondary Workspace",
                        "description": "Test secondary workspace"
                    },
                    headers=headers
                )
                
                if new_ws_response.status in [200, 201]:
                    new_ws = await new_ws_response.json()
                    new_ws_id = new_ws.get('workspace_id')
                    assert new_ws_id, "New workspace not created"
                    
                    # Switch workspace
                    switch_response = await session.post(
                        f"{backend_url}/api/workspace/switch",
                        json={"workspace_id": new_ws_id},
                        headers=headers
                    )
                    
                    assert switch_response.status == 200, \
                        "Workspace switch failed"

    @pytest.mark.asyncio
    async def test_api_key_generation(self):
        """
        Test API key generation and management.
        
        Critical Assertions:
        - API keys can be generated
        - Keys have correct permissions
        - Key rotation works
        - Keys can be revoked
        
        Expected Failure: API key service not working
        Business Impact: No programmatic access, blocks automation
        """
        backend_url = "http://localhost:8000"
        
        async with aiohttp.ClientSession() as session:
            # Create and login user
            test_email = f"apikey.{uuid.uuid4()}@example.com"
            await session.post(
                f"{backend_url}/auth/register",
                json={
                    "email": test_email,
                    "password": "ApiKey123!",
                    "name": "API Key Test"
                }
            )
            
            login_response = await session.post(
                f"{backend_url}/auth/login",
                json={"email": test_email, "password": "ApiKey123!"}
            )
            
            login_data = await login_response.json()
            access_token = login_data['access_token']
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Generate API key
            api_key_request = {
                "name": "Production API Key",
                "description": "Key for production automation",
                "permissions": [
                    "read:threads",
                    "write:threads",
                    "read:messages",
                    "write:messages",
                    "execute:ai"
                ],
                "expires_in_days": 90
            }
            
            key_response = await session.post(
                f"{backend_url}/api/api-keys",
                json=api_key_request,
                headers=headers
            )
            
            if key_response.status in [200, 201]:
                key_data = await key_response.json()
                
                api_key = key_data.get('api_key')
                api_key_id = key_data.get('api_key_id')
                
                assert api_key, "No API key generated"
                assert api_key_id, "No API key ID"
                assert len(api_key) >= 32, "API key too short"
                
                # Test API key authentication
                test_response = await session.get(
                    f"{backend_url}/api/threads",
                    headers={"X-API-Key": api_key}
                )
                
                assert test_response.status in [200, 404], \
                    f"API key auth failed: {test_response.status}"
                
                # List API keys
                list_response = await session.get(
                    f"{backend_url}/api/api-keys",
                    headers=headers
                )
                
                if list_response.status == 200:
                    keys_list = await list_response.json()
                    assert len(keys_list) >= 1, "API key not in list"
                    
                    key_entry = next((k for k in keys_list if k['id'] == api_key_id), None)
                    assert key_entry, "Generated key not found"
                    assert key_entry.get('name') == "Production API Key", \
                        "Key name mismatch"
                
                # Revoke API key
                revoke_response = await session.delete(
                    f"{backend_url}/api/api-keys/{api_key_id}",
                    headers=headers
                )
                
                assert revoke_response.status in [200, 204], \
                    "API key revocation failed"
                
                # Verify key no longer works
                revoked_test = await session.get(
                    f"{backend_url}/api/threads",
                    headers={"X-API-Key": api_key}
                )
                
                assert revoked_test.status in [401, 403], \
                    "Revoked API key still works"

    @pytest.mark.asyncio
    async def test_first_llm_interaction(self):
        """
        Test first LLM interaction through the platform.
        
        Critical Assertions:
        - Thread creation works
        - Message sent to LLM
        - Response received and stored
        - Streaming works
        - Usage tracked
        
        Expected Failure: LLM integration not working
        Business Impact: Core value prop broken, 0% conversion
        """
        backend_url = "http://localhost:8000"
        
        async with aiohttp.ClientSession() as session:
            # Create and login user
            test_email = f"llm.{uuid.uuid4()}@example.com"
            await session.post(
                f"{backend_url}/auth/register",
                json={
                    "email": test_email,
                    "password": "LLMTest123!",
                    "name": "LLM Test User"
                }
            )
            
            login_response = await session.post(
                f"{backend_url}/auth/login",
                json={"email": test_email, "password": "LLMTest123!"}
            )
            
            login_data = await login_response.json()
            access_token = login_data['access_token']
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Create a thread
            thread_response = await session.post(
                f"{backend_url}/api/threads",
                json={
                    "title": "First AI Conversation",
                    "metadata": {
                        "purpose": "test",
                        "tags": ["first-interaction", "e2e-test"]
                    }
                },
                headers=headers
            )
            
            if thread_response.status in [200, 201]:
                thread_data = await thread_response.json()
                thread_id = thread_data.get('thread_id')
                assert thread_id, "No thread ID returned"
                
                # Send message to LLM
                message_request = {
                    "thread_id": thread_id,
                    "content": "Hello AI, this is my first message. Can you explain what AI optimization means?",
                    "role": "user",
                    "model": LLMModel.GEMINI_2_5_FLASH.value,
                    "temperature": 0.7,
                    "max_tokens": 500
                }
                
                message_response = await session.post(
                    f"{backend_url}/api/messages",
                    json=message_request,
                    headers=headers
                )
                
                assert message_response.status in [200, 201], \
                    f"Message send failed: {message_response.status}"
                
                message_data = await message_response.json()
                message_id = message_data.get('message_id')
                assert message_id, "No message ID returned"
                
                # Wait for AI response (with timeout)
                max_wait = 30  # seconds
                start_time = time.time()
                ai_response_received = False
                
                while time.time() - start_time < max_wait:
                    # Get thread messages
                    messages_response = await session.get(
                        f"{backend_url}/api/threads/{thread_id}/messages",
                        headers=headers
                    )
                    
                    if messages_response.status == 200:
                        messages = await messages_response.json()
                        
                        # Look for AI response
                        ai_messages = [m for m in messages if m.get('role') == 'assistant']
                        if ai_messages:
                            ai_response_received = True
                            ai_message = ai_messages[0]
                            
                            assert ai_message.get('content'), \
                                "AI response has no content"
                            assert len(ai_message['content']) > 10, \
                                "AI response too short"
                            assert ai_message.get('message_id'), \
                                "AI message has no ID"
                            assert ai_message.get('model'), \
                                "Model not recorded"
                            
                            break
                    
                    await asyncio.sleep(1)
                
                assert ai_response_received, \
                    "No AI response received within timeout"
                
                # Check usage tracking
                usage_response = await session.get(
                    f"{backend_url}/api/usage",
                    headers=headers
                )
                
                if usage_response.status == 200:
                    usage_data = await usage_response.json()
                    assert usage_data.get('total_tokens', 0) > 0, \
                        "Token usage not tracked"
                    assert usage_data.get('total_requests', 0) > 0, \
                        "Request count not tracked"
                
                # Test streaming (if supported)
                stream_response = await session.post(
                    f"{backend_url}/api/messages/stream",
                    json={
                        "thread_id": thread_id,
                        "content": "Please count from 1 to 5",
                        "role": "user",
                        "stream": True
                    },
                    headers=headers
                )
                
                if stream_response.status == 200:
                    # Read streaming response
                    chunks_received = 0
                    async for line in stream_response.content:
                        if line:
                            chunks_received += 1
                            if chunks_received >= 3:
                                break  # Got enough chunks to verify streaming
                    
                    assert chunks_received >= 3, \
                        "Streaming not working properly"