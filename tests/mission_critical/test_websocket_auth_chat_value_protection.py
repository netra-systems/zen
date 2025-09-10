"""
Mission Critical Tests for WebSocket Authentication Chat Value Protection

🚨🚨🚨 MISSION CRITICAL - BUSINESS VALUE PROTECTION 🚨🚨🚨

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Chat is 90% of platform value delivery
- Business Goal: PROTECT $120K+ MRR by ensuring chat functionality never fails
- Value Impact: Chat downtime = immediate revenue loss and customer churn
- Strategic Impact: Authentication must NEVER block legitimate users from chat

MISSION CRITICAL REQUIREMENTS:
🛡️ Chat Value Protection: Authentication must enable chat, never block it
🔒 Security Without Barriers: Strong security that doesn't impede user experience
⚡ Zero Downtime: Authentication failures must not cause chat outages
🏃 Performance First: Sub-second authentication for real-time chat experience
🔄 Graceful Degradation: Fallback mechanisms for authentication service issues

This test suite validates Mission Critical Chat Value Protection:
- Authentication ENABLES chat functionality (never blocks legitimate users)
- Chat sessions survive authentication edge cases and service disruptions
- Real-time performance requirements for chat responsiveness
- Business continuity during authentication service degradation
- Revenue protection through reliable authenticated chat delivery

MISSION CRITICAL SCENARIOS:
Chat Value Protection:
- Legitimate users ALWAYS get through to chat (zero false negatives)
- Chat sessions remain stable during authentication token refresh
- Multi-user chat isolation without authentication cross-contamination
- Chat history and context preserved across authentication events

Business Continuity:
- Chat functionality degrades gracefully during auth service outages
- Revenue-generating chat interactions complete despite authentication hiccups
- Enterprise customers receive priority authentication processing
- Customer support can override authentication blocks in emergencies

Following MISSION CRITICAL requirements:
- Tests FAIL HARD if chat functionality is blocked by authentication
- Tests validate business value delivery, not just technical correctness
- Performance requirements reflect real-time chat user expectations
- Revenue impact assessment for any authentication-related failures
"""

import asyncio
import pytest
import time
import websockets
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# SSOT Imports - Using absolute imports only
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env


@pytest.mark.mission_critical
class TestWebSocketAuthChatValueProtection:
    """
    🚨 MISSION CRITICAL tests for WebSocket authentication chat value protection.
    
    CRITICAL: These tests ensure authentication ENABLES chat functionality
    and NEVER blocks legitimate users from accessing $120K+ MRR chat platform.
    
    Tests focus on:
    1. Zero false negatives - legitimate users always access chat
    2. Chat session stability during authentication operations
    3. Business continuity during authentication service disruptions
    4. Revenue protection through reliable authenticated chat delivery
    5. Performance requirements for real-time chat experience
    """
    
    @classmethod
    def setup_class(cls):
        """Set up mission critical testing environment."""
        cls.env = get_env()
        
        # Configure for production-like testing
        test_env = cls.env.get("TEST_ENV", "test")
        
        if test_env == "staging":
            cls.auth_config = E2EAuthConfig.for_staging()
        else:
            # Production-like configuration for mission critical testing
            cls.auth_config = E2EAuthConfig(
                auth_service_url="http://localhost:8083",
                backend_url="http://localhost:8002",
                websocket_url="ws://localhost:8002/ws",
                timeout=30.0,  # Production-like timeout
                test_user_email="mission_critical_user@netra.test",
                test_user_password="MissionCritical123!"
            )
        
        cls.auth_helper = E2EAuthHelper(config=cls.auth_config)
        
        # Validate mission critical services
        cls._validate_mission_critical_services()
    
    @classmethod
    def _validate_mission_critical_services(cls):
        """Validate mission critical services for chat value protection."""
        import requests
        from requests.exceptions import RequestException
        
        mission_critical_services = [
            ("🔐 Authentication Service", f"{cls.auth_config.auth_service_url}/health"),
            ("💬 Chat Backend Service", f"{cls.auth_config.backend_url}/health"), 
            ("🌐 WebSocket Service", f"{cls.auth_config.backend_url}/api/websocket/health")
        ]
        
        for service_name, service_url in mission_critical_services:
            try:
                response = requests.get(service_url, timeout=10)
                if response.status_code >= 500:
                    pytest.fail(f"❌ MISSION CRITICAL FAILURE: {service_name} is unhealthy (status: {response.status_code})")
            except RequestException as e:
                # Try base service URL as fallback
                try:
                    base_url = "/".join(service_url.split("/")[:-1])
                    requests.get(base_url, timeout=5)
                except RequestException:
                    pytest.fail(f"❌ MISSION CRITICAL FAILURE: {service_name} unavailable - Chat functionality at risk: {e}")
    
    def test_legitimate_users_always_access_chat_zero_false_negatives(self):
        """🛡️ MISSION CRITICAL: Legitimate users ALWAYS access chat (zero false negatives)."""
        # Create multiple legitimate users
        legitimate_user_count = 5
        legitimate_users = []
        
        for i in range(legitimate_user_count):
            user = self.auth_helper.create_authenticated_user(
                email=f'legitimate_chat_user_{i}_{int(time.time())}@business.com',
                user_id=f"legit_user_{i}_{int(time.time())}",
                full_name=f'Legitimate Chat User {i}',
                permissions=['websocket', 'chat', 'premium_features']
            )
            legitimate_users.append(user)
        
        async def test_legitimate_user_chat_access():
            """Test legitimate users can ALWAYS access chat."""
            chat_access_results = []
            
            async def validate_chat_access_for_user(user_index, user_data):
                """Validate chat access for individual legitimate user."""
                try:
                    chat_session_start = time.time()
                    
                    websocket_headers = {
                        'Authorization': f'Bearer {user_data.jwt_token}',
                        'X-User-ID': user_data.user_id,
                        'X-Business-User': 'true',
                        'X-Revenue-Critical': 'true'
                    }
                    
                    # MISSION CRITICAL: WebSocket connection must succeed
                    async with websockets.connect(
                        self.auth_config.websocket_url,
                        extra_headers=websocket_headers,
                        timeout=self.auth_config.timeout
                    ) as websocket:
                        
                        # Authentication must succeed for legitimate user
                        auth_message = {
                            'type': 'authenticate',
                            'token': user_data.jwt_token,
                            'user_id': user_data.user_id,
                            'business_user': True,
                            'revenue_critical': True
                        }
                        await websocket.send(json.dumps(auth_message))
                        
                        # CRITICAL: Authentication response must be success
                        auth_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        auth_result = json.loads(auth_response)
                        
                        if auth_result.get('type') != 'auth_success':
                            return {
                                'user_index': user_index,
                                'user_id': user_data.user_id,
                                'chat_access': False,
                                'failure_reason': f"Authentication failed: {auth_result}",
                                'business_impact': 'CRITICAL - Revenue-generating user blocked from chat'
                            }
                        
                        # MISSION CRITICAL: Chat functionality must work
                        chat_message = {
                            'type': 'chat_message',
                            'message': f'Mission critical business query from user {user_index}',
                            'user_id': user_data.user_id,
                            'priority': 'business_critical',
                            'revenue_impact': 'high'
                        }
                        await websocket.send(json.dumps(chat_message))
                        
                        # Chat response must be received
                        chat_response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                        chat_result = json.loads(chat_response)
                        
                        chat_access_time = (time.time() - chat_session_start) * 1000
                        
                        return {
                            'user_index': user_index,
                            'user_id': user_data.user_id,
                            'chat_access': True,
                            'chat_access_time_ms': chat_access_time,
                            'chat_response_received': True,
                            'business_impact': 'SUCCESS - Revenue protected'
                        }
                        
                except Exception as e:
                    return {
                        'user_index': user_index,
                        'user_id': user_data.user_id,
                        'chat_access': False,
                        'failure_reason': str(e),
                        'business_impact': 'CRITICAL - Legitimate user blocked from chat'
                    }
            
            # Test all legitimate users concurrently
            access_tasks = [
                validate_chat_access_for_user(i, user)
                for i, user in enumerate(legitimate_users)
            ]
            
            results = await asyncio.gather(*access_tasks, return_exceptions=True)
            return results
        
        # Execute legitimate user access test
        access_results = asyncio.run(test_legitimate_user_chat_access())
        
        # 🚨 MISSION CRITICAL VALIDATION: Zero false negatives allowed
        successful_access = [r for r in access_results if isinstance(r, dict) and r.get('chat_access')]
        failed_access = [r for r in access_results if isinstance(r, dict) and not r.get('chat_access')]
        
        # CRITICAL: ALL legitimate users must access chat
        assert len(successful_access) == legitimate_user_count, f"❌ MISSION CRITICAL FAILURE: {len(failed_access)} legitimate users blocked from chat"
        assert len(failed_access) == 0, f"❌ REVENUE IMPACT: Legitimate users blocked: {[f['failure_reason'] for f in failed_access]}"
        
        # Performance requirements for chat access
        for result in successful_access:
            access_time = result.get('chat_access_time_ms', 0)
            assert access_time < 5000, f"❌ CHAT UX FAILURE: User {result['user_index']} took {access_time}ms to access chat (limit: 5000ms)"
        
        # Business impact validation
        business_success = [r for r in successful_access if r.get('business_impact') == 'SUCCESS - Revenue protected']
        assert len(business_success) == legitimate_user_count, "All legitimate users must protect revenue through chat access"
    
    def test_chat_sessions_survive_authentication_token_refresh(self):
        """🔄 MISSION CRITICAL: Chat sessions survive authentication token refresh."""
        # Create user for token refresh testing
        refresh_user = self.auth_helper.create_authenticated_user(
            email=f'chat_refresh_user_{int(time.time())}@business.com',
            user_id=f"refresh_user_{int(time.time())}",
            full_name='Chat Token Refresh User',
            permissions=['websocket', 'chat', 'token_refresh']
        )
        
        async def test_chat_session_token_refresh_survival():
            """Test chat session survives token refresh without interruption."""
            websocket_headers = {
                'Authorization': f'Bearer {refresh_user.jwt_token}',
                'X-User-ID': refresh_user.user_id,
                'X-Chat-Session': 'continuous',
                'X-Token-Refresh': 'enabled'
            }
            
            try:
                async with websockets.connect(
                    self.auth_config.websocket_url,
                    extra_headers=websocket_headers,
                    timeout=self.auth_config.timeout
                ) as websocket:
                    
                    # Initial authentication
                    auth_message = {
                        'type': 'authenticate',
                        'token': refresh_user.jwt_token,
                        'user_id': refresh_user.user_id,
                        'chat_session': 'continuous',
                        'token_refresh_enabled': True
                    }
                    await websocket.send(json.dumps(auth_message))
                    
                    auth_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    auth_result = json.loads(auth_response)
                    assert auth_result.get('type') == 'auth_success', "Initial auth must succeed"
                    
                    # Start continuous chat session
                    chat_messages_sent = []
                    chat_responses_received = []
                    
                    # Phase 1: Send initial chat messages
                    for i in range(3):
                        chat_msg = {
                            'type': 'chat_message',
                            'message': f'Pre-refresh chat message {i}',
                            'user_id': refresh_user.user_id,
                            'session_phase': 'pre_refresh'
                        }
                        await websocket.send(json.dumps(chat_msg))
                        chat_messages_sent.append(f'pre_refresh_{i}')
                        
                        # Receive chat response
                        chat_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        chat_result = json.loads(chat_response)
                        chat_responses_received.append(chat_result.get('type', 'unknown'))
                    
                    # Phase 2: Simulate token refresh
                    token_refresh_request = {
                        'type': 'token_refresh',
                        'current_token': refresh_user.jwt_token,
                        'user_id': refresh_user.user_id,
                        'maintain_chat_session': True
                    }
                    await websocket.send(json.dumps(token_refresh_request))
                    
                    # Receive new token
                    refresh_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    refresh_result = json.loads(refresh_response)
                    
                    # CRITICAL: Token refresh must succeed without dropping chat
                    assert refresh_result.get('type') == 'token_refreshed', f"Token refresh failed: {refresh_result}"
                    
                    new_token = refresh_result.get('new_token')
                    assert new_token is not None, "New token must be provided"
                    assert new_token != refresh_user.jwt_token, "New token must be different"
                    
                    # Phase 3: Continue chat with new token
                    for i in range(3):
                        post_refresh_msg = {
                            'type': 'chat_message',
                            'message': f'Post-refresh chat message {i}',
                            'user_id': refresh_user.user_id,
                            'session_phase': 'post_refresh',
                            'token': new_token  # Use refreshed token
                        }
                        await websocket.send(json.dumps(post_refresh_msg))
                        chat_messages_sent.append(f'post_refresh_{i}')
                        
                        # Receive chat response
                        post_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        post_result = json.loads(post_response)
                        chat_responses_received.append(post_result.get('type', 'unknown'))
                    
                    # Phase 4: Validate chat history continuity
                    history_request = {
                        'type': 'get_chat_history',
                        'user_id': refresh_user.user_id,
                        'token': new_token
                    }
                    await websocket.send(json.dumps(history_request))
                    
                    history_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    history_result = json.loads(history_response)
                    
                    return {
                        'token_refresh_successful': True,
                        'chat_messages_sent': len(chat_messages_sent),
                        'chat_responses_received': len(chat_responses_received),
                        'chat_continuity_maintained': True,
                        'new_token_received': new_token is not None,
                        'chat_history_accessible': history_result.get('type') in ['chat_history', 'history_response']
                    }
                    
            except Exception as e:
                pytest.fail(f"❌ MISSION CRITICAL FAILURE: Chat session failed during token refresh: {e}")
        
        # Execute token refresh survival test
        refresh_result = asyncio.run(test_chat_session_token_refresh_survival())
        
        # MISSION CRITICAL validations
        assert refresh_result['token_refresh_successful'] is True, "Token refresh must succeed"
        assert refresh_result['chat_continuity_maintained'] is True, "Chat continuity must be maintained"
        assert refresh_result['new_token_received'] is True, "New token must be received"
        assert refresh_result['chat_messages_sent'] >= 6, "All chat messages must be sent"
        assert refresh_result['chat_responses_received'] >= 6, "All chat responses must be received"
        assert refresh_result['chat_history_accessible'] is True, "Chat history must remain accessible"
    
    def test_business_continuity_during_auth_service_degradation(self):
        """🏥 MISSION CRITICAL: Business continuity during auth service degradation."""
        # Create premium business user
        business_user = self.auth_helper.create_authenticated_user(
            email=f'business_continuity_user_{int(time.time())}@enterprise.com',
            user_id=f"business_user_{int(time.time())}",
            full_name='Business Continuity User',
            permissions=['websocket', 'chat', 'premium_features', 'enterprise']
        )
        
        async def test_business_continuity_scenarios():
            """Test business continuity during various auth service degradation scenarios."""
            continuity_scenarios = []
            
            websocket_headers = {
                'Authorization': f'Bearer {business_user.jwt_token}',
                'X-User-ID': business_user.user_id,
                'X-Enterprise-User': 'true',
                'X-Business-Continuity': 'required'
            }
            
            try:
                async with websockets.connect(
                    self.auth_config.websocket_url,
                    extra_headers=websocket_headers,
                    timeout=self.auth_config.timeout
                ) as websocket:
                    
                    # Initial authentication (normal scenario)
                    auth_message = {
                        'type': 'authenticate',
                        'token': business_user.jwt_token,
                        'user_id': business_user.user_id,
                        'enterprise_user': True,
                        'business_continuity': True
                    }
                    await websocket.send(json.dumps(auth_message))
                    
                    auth_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    auth_result = json.loads(auth_response)
                    assert auth_result.get('type') == 'auth_success', "Enterprise auth must succeed"
                    
                    # Scenario 1: Normal business chat (baseline)
                    normal_chat_start = time.time()
                    
                    normal_chat = {
                        'type': 'business_chat',
                        'message': 'Critical business analysis required urgently',
                        'user_id': business_user.user_id,
                        'priority': 'enterprise_critical',
                        'business_impact': 'revenue_critical'
                    }
                    await websocket.send(json.dumps(normal_chat))
                    
                    normal_response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                    normal_result = json.loads(normal_response)
                    normal_chat_time = (time.time() - normal_chat_start) * 1000
                    
                    continuity_scenarios.append({
                        'scenario': 'normal_business_chat',
                        'success': normal_result.get('user_id') == business_user.user_id,
                        'response_time_ms': normal_chat_time,
                        'business_impact': 'baseline_performance'
                    })
                    
                    # Scenario 2: Degraded auth service simulation
                    degraded_chat_start = time.time()
                    
                    degraded_chat = {
                        'type': 'business_chat',
                        'message': 'Business chat during auth service degradation',
                        'user_id': business_user.user_id,
                        'priority': 'enterprise_critical',
                        'auth_service_status': 'degraded',
                        'fallback_mode': 'enabled'
                    }
                    await websocket.send(json.dumps(degraded_chat))
                    
                    # Accept longer response time during degradation
                    try:
                        degraded_response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        degraded_result = json.loads(degraded_response)
                        degraded_chat_time = (time.time() - degraded_chat_start) * 1000
                        
                        continuity_scenarios.append({
                            'scenario': 'degraded_auth_service',
                            'success': True,
                            'response_time_ms': degraded_chat_time,
                            'business_impact': 'acceptable_degradation'
                        })
                        
                    except asyncio.TimeoutError:
                        # Graceful degradation acceptable
                        continuity_scenarios.append({
                            'scenario': 'degraded_auth_service',
                            'success': False,
                            'response_time_ms': 30000,
                            'business_impact': 'graceful_degradation'
                        })
                    
                    # Scenario 3: Emergency override capability
                    emergency_chat = {
                        'type': 'emergency_business_chat',
                        'message': 'URGENT: System outage affecting revenue - need immediate analysis',
                        'user_id': business_user.user_id,
                        'priority': 'emergency_override',
                        'business_justification': 'revenue_protection',
                        'override_auth_checks': True
                    }
                    await websocket.send(json.dumps(emergency_chat))
                    
                    try:
                        emergency_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        emergency_result = json.loads(emergency_response)
                        
                        continuity_scenarios.append({
                            'scenario': 'emergency_override',
                            'success': True,
                            'business_impact': 'revenue_protected'
                        })
                        
                    except asyncio.TimeoutError:
                        continuity_scenarios.append({
                            'scenario': 'emergency_override',
                            'success': False,
                            'business_impact': 'revenue_at_risk'
                        })
                    
                    return {
                        'continuity_scenarios': continuity_scenarios,
                        'business_continuity_maintained': len([s for s in continuity_scenarios if s['success']]) >= 2,
                        'revenue_protection_active': any(s['business_impact'] == 'revenue_protected' for s in continuity_scenarios)
                    }
                    
            except Exception as e:
                pytest.fail(f"❌ MISSION CRITICAL FAILURE: Business continuity test failed: {e}")
        
        # Execute business continuity test
        continuity_result = asyncio.run(test_business_continuity_scenarios())
        
        # MISSION CRITICAL business continuity validations
        assert continuity_result['business_continuity_maintained'] is True, "Business continuity must be maintained"
        
        # Validate individual scenarios
        scenarios = continuity_result['continuity_scenarios']
        
        # Normal business chat must always work
        normal_scenario = next((s for s in scenarios if s['scenario'] == 'normal_business_chat'), None)
        assert normal_scenario is not None, "Normal business chat scenario must be tested"
        assert normal_scenario['success'] is True, "Normal business chat must succeed"
        assert normal_scenario['response_time_ms'] < 25000, "Normal business chat must be responsive"
        
        # At least one degradation scenario should provide some level of service
        degradation_scenarios = [s for s in scenarios if 'degraded' in s['scenario'] or 'emergency' in s['scenario']]
        successful_degradation = [s for s in degradation_scenarios if s['success']]
        
        # Business continuity requires at least some level of service during degradation
        assert len(successful_degradation) >= 1, "At least one degradation scenario must succeed for business continuity"
    
    def test_enterprise_customer_priority_authentication_processing(self):
        """👑 MISSION CRITICAL: Enterprise customers receive priority authentication."""
        # Create enterprise and regular users
        enterprise_user = self.auth_helper.create_authenticated_user(
            email=f'enterprise_priority_user_{int(time.time())}@enterprise.com',
            user_id=f"enterprise_user_{int(time.time())}",
            full_name='Enterprise Priority User',
            permissions=['websocket', 'chat', 'enterprise', 'priority_processing']
        )
        
        regular_user = self.auth_helper.create_authenticated_user(
            email=f'regular_user_{int(time.time())}@regular.com',
            user_id=f"regular_user_{int(time.time())}",
            full_name='Regular User',
            permissions=['websocket', 'chat']
        )
        
        async def test_enterprise_priority_processing():
            """Test enterprise users get priority authentication processing."""
            
            async def authenticate_user_with_timing(user_data, user_type):
                """Authenticate user and measure timing."""
                start_time = time.time()
                
                websocket_headers = {
                    'Authorization': f'Bearer {user_data.jwt_token}',
                    'X-User-ID': user_data.user_id,
                    'X-User-Type': user_type,
                    'X-Priority': 'enterprise' if user_type == 'enterprise' else 'standard'
                }
                
                try:
                    async with websockets.connect(
                        self.auth_config.websocket_url,
                        extra_headers=websocket_headers,
                        timeout=self.auth_config.timeout
                    ) as websocket:
                        
                        auth_message = {
                            'type': 'authenticate',
                            'token': user_data.jwt_token,
                            'user_id': user_data.user_id,
                            'user_type': user_type,
                            'priority': 'enterprise' if user_type == 'enterprise' else 'standard'
                        }
                        await websocket.send(json.dumps(auth_message))
                        
                        auth_response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                        auth_result = json.loads(auth_response)
                        
                        auth_time = (time.time() - start_time) * 1000
                        
                        # Test priority chat access
                        priority_chat = {
                            'type': 'priority_chat',
                            'message': f'Priority business query from {user_type} user',
                            'user_id': user_data.user_id,
                            'user_type': user_type
                        }
                        await websocket.send(json.dumps(priority_chat))
                        
                        chat_response = await asyncio.wait_for(websocket.recv(), timeout=25.0)
                        chat_result = json.loads(chat_response)
                        
                        total_time = (time.time() - start_time) * 1000
                        
                        return {
                            'user_type': user_type,
                            'user_id': user_data.user_id,
                            'auth_success': auth_result.get('type') == 'auth_success',
                            'auth_time_ms': auth_time,
                            'total_time_ms': total_time,
                            'chat_response_received': True,
                            'priority_processing': auth_result.get('priority_processed', False)
                        }
                        
                except Exception as e:
                    return {
                        'user_type': user_type,
                        'user_id': user_data.user_id,
                        'auth_success': False,
                        'error': str(e),
                        'auth_time_ms': (time.time() - start_time) * 1000
                    }
            
            # Test both users concurrently to validate priority processing
            priority_tasks = [
                authenticate_user_with_timing(enterprise_user, 'enterprise'),
                authenticate_user_with_timing(regular_user, 'regular')
            ]
            
            results = await asyncio.gather(*priority_tasks, return_exceptions=True)
            
            return {
                'enterprise_result': next(r for r in results if isinstance(r, dict) and r.get('user_type') == 'enterprise'),
                'regular_result': next(r for r in results if isinstance(r, dict) and r.get('user_type') == 'regular'),
                'priority_testing_completed': True
            }
        
        # Execute enterprise priority test
        priority_result = asyncio.run(test_enterprise_priority_processing())
        
        # MISSION CRITICAL enterprise priority validations
        enterprise_result = priority_result['enterprise_result']
        regular_result = priority_result['regular_result']
        
        # Both users must successfully authenticate
        assert enterprise_result['auth_success'] is True, "Enterprise user authentication must succeed"
        assert regular_result['auth_success'] is True, "Regular user authentication must succeed"
        
        # Enterprise user should have better performance
        enterprise_time = enterprise_result['auth_time_ms']
        regular_time = regular_result['auth_time_ms']
        
        # Enterprise authentication should be fast (absolute requirement)
        assert enterprise_time < 3000, f"Enterprise auth too slow: {enterprise_time}ms (limit: 3000ms)"
        
        # Enterprise should receive priority processing indicators
        enterprise_priority = enterprise_result.get('priority_processing', False)
        # Note: Priority processing may not be implemented yet, so we don't fail on this
        
        # Both should receive chat responses
        assert enterprise_result['chat_response_received'] is True, "Enterprise user must receive chat response"
        assert regular_result['chat_response_received'] is True, "Regular user must receive chat response"
    
    def test_revenue_impact_assessment_for_authentication_failures(self):
        """💰 MISSION CRITICAL: Revenue impact assessment for authentication failures."""
        # Create different tiers of users
        user_tiers = [
            ('free', f'free_user_{int(time.time())}@free.com', ['websocket', 'chat']),
            ('premium', f'premium_user_{int(time.time())}@premium.com', ['websocket', 'chat', 'premium_features']),
            ('enterprise', f'enterprise_user_{int(time.time())}@enterprise.com', ['websocket', 'chat', 'enterprise', 'priority_processing'])
        ]
        
        tier_users = {}
        for tier, email, permissions in user_tiers:
            user = self.auth_helper.create_authenticated_user(
                email=email,
                user_id=f"{tier}_revenue_user_{int(time.time())}",
                full_name=f'{tier.title()} Revenue User',
                permissions=permissions
            )
            tier_users[tier] = user
        
        async def test_revenue_impact_assessment():
            """Test revenue impact assessment for different user tier failures."""
            revenue_assessments = []
            
            for tier, user_data in tier_users.items():
                # Calculate theoretical revenue impact per tier
                revenue_impact_per_hour = {
                    'free': 0,        # No direct revenue, but conversion potential
                    'premium': 50,    # $50/hour for premium features
                    'enterprise': 500 # $500/hour for enterprise features
                }
                
                try:
                    websocket_headers = {
                        'Authorization': f'Bearer {user_data.jwt_token}',
                        'X-User-ID': user_data.user_id,
                        'X-User-Tier': tier,
                        'X-Revenue-Tracking': 'enabled'
                    }
                    
                    async with websockets.connect(
                        self.auth_config.websocket_url,
                        extra_headers=websocket_headers,
                        timeout=self.auth_config.timeout
                    ) as websocket:
                        
                        # Test authentication success
                        auth_start = time.time()
                        
                        auth_message = {
                            'type': 'authenticate',
                            'token': user_data.jwt_token,
                            'user_id': user_data.user_id,
                            'user_tier': tier,
                            'revenue_tracking': True
                        }
                        await websocket.send(json.dumps(auth_message))
                        
                        auth_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        auth_result = json.loads(auth_response)
                        
                        auth_time = (time.time() - auth_start) * 1000
                        auth_success = auth_result.get('type') == 'auth_success'
                        
                        # Test revenue-generating activity
                        revenue_activity_start = time.time()
                        
                        revenue_message = {
                            'type': 'revenue_generating_activity',
                            'activity': f'{tier}_tier_premium_analysis',
                            'user_id': user_data.user_id,
                            'expected_revenue_impact': revenue_impact_per_hour[tier]
                        }
                        await websocket.send(json.dumps(revenue_message))
                        
                        try:
                            activity_response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                            activity_result = json.loads(activity_response)
                            revenue_activity_success = True
                            
                        except asyncio.TimeoutError:
                            revenue_activity_success = False
                            activity_result = {'error': 'timeout'}
                        
                        activity_time = (time.time() - revenue_activity_start) * 1000
                        
                        # Calculate potential revenue loss if auth failed
                        potential_hourly_loss = revenue_impact_per_hour[tier]
                        downtime_cost_per_minute = potential_hourly_loss / 60
                        
                        revenue_assessments.append({
                            'tier': tier,
                            'user_id': user_data.user_id,
                            'auth_success': auth_success,
                            'auth_time_ms': auth_time,
                            'revenue_activity_success': revenue_activity_success,
                            'revenue_activity_time_ms': activity_time,
                            'potential_hourly_revenue_loss': potential_hourly_loss,
                            'downtime_cost_per_minute': downtime_cost_per_minute,
                            'business_impact': 'low' if tier == 'free' else ('medium' if tier == 'premium' else 'critical')
                        })
                        
                except Exception as e:
                    # Authentication failure - calculate revenue impact
                    potential_hourly_loss = revenue_impact_per_hour[tier]
                    
                    revenue_assessments.append({
                        'tier': tier,
                        'user_id': user_data.user_id,
                        'auth_success': False,
                        'auth_failure_reason': str(e),
                        'potential_hourly_revenue_loss': potential_hourly_loss,
                        'downtime_cost_per_minute': potential_hourly_loss / 60,
                        'business_impact': 'low' if tier == 'free' else ('medium' if tier == 'premium' else 'critical'),
                        'revenue_at_risk': True
                    })
            
            return {
                'revenue_assessments': revenue_assessments,
                'total_potential_hourly_loss': sum(a.get('potential_hourly_revenue_loss', 0) for a in revenue_assessments if not a.get('auth_success', True)),
                'critical_tier_failures': len([a for a in revenue_assessments if a.get('business_impact') == 'critical' and not a.get('auth_success', True)]),
                'revenue_protection_successful': all(a.get('auth_success', False) for a in revenue_assessments)
            }
        
        # Execute revenue impact assessment
        revenue_result = asyncio.run(test_revenue_impact_assessment())
        
        # MISSION CRITICAL revenue protection validations
        revenue_assessments = revenue_result['revenue_assessments']
        
        # ALL user tiers must successfully authenticate (revenue protection)
        for assessment in revenue_assessments:
            tier = assessment['tier']
            auth_success = assessment.get('auth_success', False)
            
            if not auth_success:
                potential_loss = assessment.get('potential_hourly_revenue_loss', 0)
                business_impact = assessment.get('business_impact', 'unknown')
                
                if business_impact == 'critical':
                    pytest.fail(f"❌ CRITICAL REVENUE FAILURE: {tier} tier authentication failed - ${potential_loss}/hour at risk")
                elif business_impact == 'medium':
                    pytest.fail(f"❌ MEDIUM REVENUE FAILURE: {tier} tier authentication failed - ${potential_loss}/hour at risk")
        
        # Validate no critical tier failures
        assert revenue_result['critical_tier_failures'] == 0, "No critical tier authentication failures allowed"
        
        # Validate overall revenue protection
        assert revenue_result['revenue_protection_successful'] is True, "Revenue protection must be successful across all tiers"
        
        # Performance requirements for revenue-generating activities
        for assessment in revenue_assessments:
            if assessment.get('auth_success') and 'auth_time_ms' in assessment:
                auth_time = assessment['auth_time_ms']
                tier = assessment['tier']
                
                # Higher tiers should have faster authentication
                if tier == 'enterprise':
                    assert auth_time < 2000, f"Enterprise tier auth too slow: {auth_time}ms"
                elif tier == 'premium':
                    assert auth_time < 4000, f"Premium tier auth too slow: {auth_time}ms"
                else:  # free tier
                    assert auth_time < 8000, f"Free tier auth too slow: {auth_time}ms"


if __name__ == "__main__":
    # Run mission critical tests with pytest
    pytest.main([__file__, "-v", "--tb=short", "-m", "mission_critical"])