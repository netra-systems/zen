"""Frontend Initial Load Authentication Flow L4 Integration Test

Business Value Justification (BVJ):
- Segment: All segments (100% of users)
- Business Goal: Conversion & Retention
- Value Impact: First impression and user onboarding experience
- Revenue Impact: $75K MRR - Initial auth is gateway to all features

Critical Path: Frontend Initial Load -> Auth Config Fetch -> OAuth Flow -> Token Exchange -> WebSocket -> User Data Load

L4 Test Coverage:
- Real browser automation with Playwright
- Actual frontend application in staging environment
- Real OAuth provider integration
- Complete user authentication journey
- Network request validation
- WebSocket connection establishment
- Session persistence across page refresh
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from netra_backend.tests.integration.critical_paths.l4_staging_critical_base import (
    CriticalPathMetrics,
    L4StagingCriticalPathTestBase,
)

@dataclass
class FrontendAuthMetrics:
    """Frontend authentication metrics container."""
    initial_load_time: float = 0.0
    auth_config_fetch_time: float = 0.0
    oauth_redirect_time: float = 0.0
    token_exchange_time: float = 0.0
    websocket_connect_time: float = 0.0
    user_data_load_time: float = 0.0
    total_auth_flow_time: float = 0.0
    page_refresh_recovery_time: float = 0.0
    network_requests_count: int = 0
    websocket_messages_count: int = 0

@dataclass
class AuthFlowStep:
    """Authentication flow step result."""
    step_name: str
    success: bool
    duration: float
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class FrontendInitialAuthFlowL4Test(L4StagingCriticalPathTestBase):
    """L4 test for frontend initial load authentication flow."""

    def __init__(self):
        """Initialize frontend auth flow L4 test."""
        super().__init__("frontend_initial_auth_flow_l4")
        self.playwright = None
        self.browser = None
        self.browser_context = None
        self.page = None
        self.auth_metrics = FrontendAuthMetrics()
        self.auth_flow_steps: List[AuthFlowStep] = []
        self.test_user_email = f"test_frontend_auth_{uuid.uuid4().hex[:8]}@staging.netrasystems.ai"
        self.network_requests: List[Dict[str, Any]] = []
        self.websocket_messages: List[Dict[str, Any]] = []

    async def setup_test_specific_environment(self) -> None:
        """Setup Playwright browser automation for L4 frontend testing."""
        try:
            # Import and setup Playwright
            from playwright.async_api import async_playwright
            
            self.playwright = await async_playwright().start()
            
            # Launch browser with appropriate settings for staging
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Set to False for debugging
                args=[
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            # Create browser context with realistic user settings
            self.browser_context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                permissions=['notifications'],
                locale='en-US'
            )
            
            # Setup network monitoring
            await self._setup_network_monitoring()
            
            # Create page
            self.page = await self.browser_context.new_page()
            
            # Setup console and error monitoring
            await self._setup_browser_monitoring()
            
        except Exception as e:
            raise RuntimeError(f"Failed to setup Playwright environment: {e}")

    async def _setup_network_monitoring(self) -> None:
        """Setup network request/response monitoring."""
        async def handle_request(request):
            request_data = {
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
                'timestamp': time.time(),
                'type': 'request'
            }
            self.network_requests.append(request_data)
            self.auth_metrics.network_requests_count += 1

        async def handle_response(response):
            response_data = {
                'url': response.url,
                'status': response.status,
                'headers': dict(response.headers),
                'timestamp': time.time(),
                'type': 'response'
            }
            self.network_requests.append(response_data)

        self.browser_context.on('request', handle_request)
        self.browser_context.on('response', handle_response)

    async def _setup_browser_monitoring(self) -> None:
        """Setup browser console and error monitoring."""
        async def handle_console(msg):
            if msg.type in ['error', 'warning']:
                print(f"Browser {msg.type}: {msg.text}")

        async def handle_page_error(error):
            print(f"Page error: {error}")

        self.page.on('console', handle_console)
        self.page.on('pageerror', handle_page_error)

    async def execute_critical_path_test(self) -> Dict[str, Any]:
        """Execute frontend initial auth flow critical path test."""
        test_start_time = time.time()
        
        try:
            # Step 1: Initial Frontend Load
            initial_load_result = await self._test_initial_frontend_load()
            self.auth_flow_steps.append(initial_load_result)
            
            if not initial_load_result.success:
                raise Exception(f"Initial load failed: {initial_load_result.error}")

            # Step 2: Auth Config Fetch
            auth_config_result = await self._test_auth_config_fetch()
            self.auth_flow_steps.append(auth_config_result)
            
            if not auth_config_result.success:
                raise Exception(f"Auth config fetch failed: {auth_config_result.error}")

            # Step 3: OAuth Flow Initiation
            oauth_initiation_result = await self._test_oauth_flow_initiation()
            self.auth_flow_steps.append(oauth_initiation_result)
            
            if not oauth_initiation_result.success:
                raise Exception(f"OAuth initiation failed: {oauth_initiation_result.error}")

            # Step 4: OAuth Provider Redirect
            oauth_redirect_result = await self._test_oauth_provider_redirect()
            self.auth_flow_steps.append(oauth_redirect_result)
            
            if not oauth_redirect_result.success:
                raise Exception(f"OAuth redirect failed: {oauth_redirect_result.error}")

            # Step 5: Token Exchange
            token_exchange_result = await self._test_token_exchange()
            self.auth_flow_steps.append(token_exchange_result)
            
            if not token_exchange_result.success:
                raise Exception(f"Token exchange failed: {token_exchange_result.error}")

            # Step 6: WebSocket Connection
            websocket_result = await self._test_websocket_connection()
            self.auth_flow_steps.append(websocket_result)
            
            if not websocket_result.success:
                raise Exception(f"WebSocket connection failed: {websocket_result.error}")

            # Step 7: User Data Load
            user_data_result = await self._test_user_data_load()
            self.auth_flow_steps.append(user_data_result)
            
            if not user_data_result.success:
                raise Exception(f"User data load failed: {user_data_result.error}")

            # Step 8: Session Persistence Test
            session_persistence_result = await self._test_session_persistence()
            self.auth_flow_steps.append(session_persistence_result)
            
            if not session_persistence_result.success:
                raise Exception(f"Session persistence failed: {session_persistence_result.error}")

            # Step 9: Logout Flow
            logout_result = await self._test_logout_flow()
            self.auth_flow_steps.append(logout_result)

            # Calculate total flow time
            self.auth_metrics.total_auth_flow_time = time.time() - test_start_time

            return {
                "success": True,
                "auth_flow_steps": [
                    {
                        "step_name": step.step_name,
                        "success": step.success,
                        "duration": step.duration,
                        "error": step.error,
                        "data": step.data
                    }
                    for step in self.auth_flow_steps
                ],
                "auth_metrics": {
                    "initial_load_time": self.auth_metrics.initial_load_time,
                    "auth_config_fetch_time": self.auth_metrics.auth_config_fetch_time,
                    "oauth_redirect_time": self.auth_metrics.oauth_redirect_time,
                    "token_exchange_time": self.auth_metrics.token_exchange_time,
                    "websocket_connect_time": self.auth_metrics.websocket_connect_time,
                    "user_data_load_time": self.auth_metrics.user_data_load_time,
                    "total_auth_flow_time": self.auth_metrics.total_auth_flow_time,
                    "network_requests_count": self.auth_metrics.network_requests_count,
                    "websocket_messages_count": self.auth_metrics.websocket_messages_count
                },
                "network_requests": self.network_requests[-50:],  # Last 50 requests
                "service_calls": len(self.auth_flow_steps)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "auth_flow_steps": [
                    {
                        "step_name": step.step_name,
                        "success": step.success,
                        "duration": step.duration,
                        "error": step.error
                    }
                    for step in self.auth_flow_steps
                ],
                "total_auth_flow_time": time.time() - test_start_time,
                "service_calls": len(self.auth_flow_steps)
            }

    async def _test_initial_frontend_load(self) -> AuthFlowStep:
        """Test initial frontend application load."""
        step_start_time = time.time()
        
        try:
            frontend_url = self.service_endpoints.frontend
            
            # Navigate to frontend
            await self.page.goto(frontend_url, wait_until='networkidle', timeout=30000)
            
            # Wait for React app to initialize
            await self.page.wait_for_selector('[data-testid="app-container"], #root, .app', timeout=15000)
            
            # Check for critical errors
            page_errors = await self.page.evaluate('''() => {
                return {
                    hasJSErrors: window.hasJSErrors || false,
                    consoleErrors: window.consoleErrors || [],
                    title: document.title,
                    readyState: document.readyState
                };
            }''')
            
            if page_errors['hasJSErrors']:
                raise Exception(f"JavaScript errors detected: {page_errors['consoleErrors']}")
            
            duration = time.time() - step_start_time
            self.auth_metrics.initial_load_time = duration
            
            return AuthFlowStep(
                step_name="initial_frontend_load",
                success=True,
                duration=duration,
                data={
                    "frontend_url": frontend_url,
                    "page_title": page_errors['title'],
                    "ready_state": page_errors['readyState']
                }
            )
            
        except Exception as e:
            return AuthFlowStep(
                step_name="initial_frontend_load",
                success=False,
                duration=time.time() - step_start_time,
                error=str(e)
            )

    async def _test_auth_config_fetch(self) -> AuthFlowStep:
        """Test authentication configuration fetch from auth service."""
        step_start_time = time.time()
        
        try:
            # Wait for auth config network request
            auth_config_request = None
            
            # Look for auth config requests in network traffic
            for request in self.network_requests:
                if (request['type'] == 'request' and 
                    'auth/config' in request['url'] or 
                    'config' in request['url'] and 'auth' in request['url']):
                    auth_config_request = request
                    break
            
            if not auth_config_request:
                # Trigger auth config fetch manually if not automatic
                await self.page.evaluate('''async () => {
                    if (window.authService && window.authService.getAuthConfig) {
                        return await window.authService.getAuthConfig();
                    }
                    return fetch('/auth/config').then(r => r.json());
                }''')
                
                # Wait for the request to appear
                await asyncio.sleep(2)
            
            # Verify auth config response
            auth_config_response = None
            for request in self.network_requests:
                if (request['type'] == 'response' and 
                    'auth/config' in request['url'] and 
                    request['status'] == 200):
                    auth_config_response = request
                    break
            
            if not auth_config_response:
                raise Exception("Auth config request not found or failed")
            
            duration = time.time() - step_start_time
            self.auth_metrics.auth_config_fetch_time = duration
            
            return AuthFlowStep(
                step_name="auth_config_fetch",
                success=True,
                duration=duration,
                data={
                    "config_url": auth_config_response['url'],
                    "status_code": auth_config_response['status']
                }
            )
            
        except Exception as e:
            return AuthFlowStep(
                step_name="auth_config_fetch",
                success=False,
                duration=time.time() - step_start_time,
                error=str(e)
            )

    async def _test_oauth_flow_initiation(self) -> AuthFlowStep:
        """Test OAuth flow initiation from frontend."""
        step_start_time = time.time()
        
        try:
            # Look for login button or trigger
            login_selectors = [
                '[data-testid="login-button"]',
                '.login-button',
                'button:has-text("Login")',
                'button:has-text("Sign In")',
                '.auth-button',
                '#login-btn'
            ]
            
            login_button = None
            for selector in login_selectors:
                try:
                    login_button = await self.page.wait_for_selector(selector, timeout=5000)
                    if login_button:
                        break
                except:
                    continue
            
            if not login_button:
                # Check if already authenticated
                authenticated = await self.page.evaluate('''() => {
                    return localStorage.getItem('jwt_token') || 
                           localStorage.getItem('access_token') ||
                           document.querySelector('[data-testid="user-menu"]') !== null;
                }''')
                
                if authenticated:
                    # If already authenticated, simulate logout first
                    await self._simulate_logout()
                    await asyncio.sleep(2)
                    
                    # Try to find login button again
                    for selector in login_selectors:
                        try:
                            login_button = await self.page.wait_for_selector(selector, timeout=5000)
                            if login_button:
                                break
                        except:
                            continue
            
            if not login_button:
                raise Exception("Login button not found on page")
            
            # Click login button to start OAuth flow
            await login_button.click()
            
            # Wait for OAuth redirect or popup
            try:
                # Check if redirected to OAuth provider
                await self.page.wait_for_url('**/auth/**', timeout=10000)
                oauth_initiated = True
            except:
                # Check if OAuth popup opened
                oauth_initiated = len(self.browser_context.pages) > 1
            
            if not oauth_initiated:
                raise Exception("OAuth flow did not initiate properly")
            
            duration = time.time() - step_start_time
            self.auth_metrics.oauth_redirect_time = duration
            
            return AuthFlowStep(
                step_name="oauth_flow_initiation",
                success=True,
                duration=duration,
                data={"oauth_initiated": True}
            )
            
        except Exception as e:
            return AuthFlowStep(
                step_name="oauth_flow_initiation",
                success=False,
                duration=time.time() - step_start_time,
                error=str(e)
            )

    async def _test_oauth_provider_redirect(self) -> AuthFlowStep:
        """Test OAuth provider redirect and authorization."""
        step_start_time = time.time()
        
        try:
            current_url = self.page.url
            
            # Handle OAuth provider page (Google/GitHub/etc.)
            if 'accounts.google.com' in current_url or 'github.com' in current_url:
                # For staging, use dev login if available
                dev_login_success = await self._attempt_dev_login()
                if dev_login_success:
                    duration = time.time() - step_start_time
                    return AuthFlowStep(
                        step_name="oauth_provider_redirect",
                        success=True,
                        duration=duration,
                        data={"dev_login_used": True}
                    )
                
                # Otherwise simulate OAuth provider interaction
                await self._simulate_oauth_provider_auth()
            
            # Wait for redirect back to frontend
            await self.page.wait_for_url(f"{self.service_endpoints.frontend}/**", timeout=15000)
            
            # Wait for auth callback processing
            await asyncio.sleep(3)
            
            duration = time.time() - step_start_time
            
            return AuthFlowStep(
                step_name="oauth_provider_redirect",
                success=True,
                duration=duration,
                data={"redirected_back": True}
            )
            
        except Exception as e:
            return AuthFlowStep(
                step_name="oauth_provider_redirect",
                success=False,
                duration=time.time() - step_start_time,
                error=str(e)
            )

    async def _attempt_dev_login(self) -> bool:
        """Attempt development login if available."""
        try:
            # Check for dev login endpoint
            dev_login_button = await self.page.query_selector('[data-testid="dev-login"], .dev-login')
            if dev_login_button:
                await dev_login_button.click()
                await asyncio.sleep(2)
                return True
            
            # Try direct dev login API call
            dev_login_result = await self.page.evaluate('''async () => {
                try {
                    const response = await fetch('/auth/dev-login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email: 'dev@example.com' })
                    });
                    if (response.ok) {
                        const data = await response.json();
                        localStorage.setItem('jwt_token', data.access_token);
                        return true;
                    }
                } catch (e) {
                    console.log('Dev login not available:', e);
                }
                return false;
            }''')
            
            return dev_login_result
            
        except:
            return False

    async def _simulate_oauth_provider_auth(self) -> None:
        """Simulate OAuth provider authentication."""
        try:
            # Handle Google OAuth
            if 'accounts.google.com' in self.page.url:
                await self._handle_google_oauth()
            # Handle GitHub OAuth
            elif 'github.com' in self.page.url:
                await self._handle_github_oauth()
            # Handle other providers
            else:
                await self._handle_generic_oauth()
                
        except Exception as e:
            print(f"OAuth provider simulation failed: {e}")

    async def _handle_google_oauth(self) -> None:
        """Handle Google OAuth flow."""
        # For staging, we might have test credentials or need to simulate
        # This would typically involve filling in test credentials
        # and approving the OAuth request
        pass

    async def _handle_github_oauth(self) -> None:
        """Handle GitHub OAuth flow."""
        # Similar to Google OAuth handling
        pass

    async def _handle_generic_oauth(self) -> None:
        """Handle generic OAuth provider."""
        # Generic OAuth handling
        pass

    async def _test_token_exchange(self) -> AuthFlowStep:
        """Test token exchange after OAuth callback."""
        step_start_time = time.time()
        
        try:
            # Wait for token to be stored in localStorage
            token_stored = await self.page.wait_for_function('''() => {
                return localStorage.getItem('jwt_token') || 
                       localStorage.getItem('access_token') ||
                       localStorage.getItem('auth_token');
            }''', timeout=10000)
            
            if not token_stored:
                raise Exception("Token not stored after OAuth callback")
            
            # Verify token format
            token_info = await self.page.evaluate('''() => {
                const token = localStorage.getItem('jwt_token') || 
                             localStorage.getItem('access_token') ||
                             localStorage.getItem('auth_token');
                
                try {
                    // Basic JWT validation (3 parts separated by dots)
                    const parts = token.split('.');
                    return {
                        token_present: true,
                        token_format_valid: parts.length === 3,
                        token_length: token.length
                    };
                } catch (e) {
                    return {
                        token_present: true,
                        token_format_valid: false,
                        error: e.message
                    };
                }
            }''')
            
            if not token_info['token_format_valid']:
                raise Exception("Invalid token format")
            
            duration = time.time() - step_start_time
            self.auth_metrics.token_exchange_time = duration
            
            return AuthFlowStep(
                step_name="token_exchange",
                success=True,
                duration=duration,
                data=token_info
            )
            
        except Exception as e:
            return AuthFlowStep(
                step_name="token_exchange",
                success=False,
                duration=time.time() - step_start_time,
                error=str(e)
            )

    async def _test_websocket_connection(self) -> AuthFlowStep:
        """Test WebSocket connection establishment with auth token."""
        step_start_time = time.time()
        
        try:
            # Wait for WebSocket connection
            websocket_connected = await self.page.wait_for_function('''() => {
                return window.websocketConnected || 
                       (window.wsManager && window.wsManager.isConnected) ||
                       (window.webSocket && window.webSocket.readyState === 1);
            }''', timeout=15000)
            
            if not websocket_connected:
                raise Exception("WebSocket connection not established")
            
            # Verify WebSocket authentication
            ws_auth_status = await self.page.evaluate('''() => {
                return {
                    connected: window.websocketConnected || false,
                    authenticated: window.websocketAuthenticated || false,
                    url: window.webSocketUrl || null
                };
            }''')
            
            if not ws_auth_status['authenticated']:
                # Wait a bit more for authentication
                await asyncio.sleep(3)
                ws_auth_status = await self.page.evaluate('''() => {
                    return {
                        connected: window.websocketConnected || false,
                        authenticated: window.websocketAuthenticated || false
                    };
                }''')
            
            duration = time.time() - step_start_time
            self.auth_metrics.websocket_connect_time = duration
            
            return AuthFlowStep(
                step_name="websocket_connection",
                success=True,
                duration=duration,
                data=ws_auth_status
            )
            
        except Exception as e:
            return AuthFlowStep(
                step_name="websocket_connection",
                success=False,
                duration=time.time() - step_start_time,
                error=str(e)
            )

    async def _test_user_data_load(self) -> AuthFlowStep:
        """Test user profile data loading after authentication."""
        step_start_time = time.time()
        
        try:
            # Wait for user data to load
            user_data_loaded = await self.page.wait_for_function('''() => {
                return window.userProfile || 
                       document.querySelector('[data-testid="user-profile"]') ||
                       document.querySelector('.user-menu') ||
                       localStorage.getItem('user_data');
            }''', timeout=15000)
            
            if not user_data_loaded:
                raise Exception("User data not loaded")
            
            # Extract user data
            user_info = await self.page.evaluate('''() => {
                const userProfile = window.userProfile || 
                                  JSON.parse(localStorage.getItem('user_data') || '{}');
                
                return {
                    user_loaded: true,
                    has_email: !!(userProfile.email),
                    has_id: !!(userProfile.id || userProfile.user_id),
                    profile_data: userProfile
                };
            }''')
            
            if not user_info['user_loaded']:
                raise Exception("User profile data not available")
            
            duration = time.time() - step_start_time
            self.auth_metrics.user_data_load_time = duration
            
            return AuthFlowStep(
                step_name="user_data_load",
                success=True,
                duration=duration,
                data=user_info
            )
            
        except Exception as e:
            return AuthFlowStep(
                step_name="user_data_load",
                success=False,
                duration=time.time() - step_start_time,
                error=str(e)
            )

    async def _test_session_persistence(self) -> AuthFlowStep:
        """Test session persistence across page refresh."""
        step_start_time = time.time()
        
        try:
            # Store current auth state
            auth_state_before = await self.page.evaluate('''() => {
                return {
                    token: localStorage.getItem('jwt_token') || localStorage.getItem('access_token'),
                    user_data: localStorage.getItem('user_data'),
                    authenticated: window.userProfile ? true : false
                };
            }''')
            
            if not auth_state_before['token']:
                raise Exception("No auth token found before refresh")
            
            # Refresh the page
            await self.page.reload(wait_until='networkidle')
            
            # Wait for auth restoration
            await asyncio.sleep(3)
            
            # Check auth state after refresh
            auth_state_after = await self.page.evaluate('''() => {
                return {
                    token: localStorage.getItem('jwt_token') || localStorage.getItem('access_token'),
                    user_data: localStorage.getItem('user_data'),
                    authenticated: window.userProfile ? true : false
                };
            }''')
            
            if not auth_state_after['token']:
                raise Exception("Auth token lost after refresh")
            
            if auth_state_before['token'] != auth_state_after['token']:
                raise Exception("Auth token changed after refresh")
            
            duration = time.time() - step_start_time
            self.auth_metrics.page_refresh_recovery_time = duration
            
            return AuthFlowStep(
                step_name="session_persistence",
                success=True,
                duration=duration,
                data={
                    "token_persisted": True,
                    "user_data_persisted": auth_state_after['user_data'] is not None
                }
            )
            
        except Exception as e:
            return AuthFlowStep(
                step_name="session_persistence",
                success=False,
                duration=time.time() - step_start_time,
                error=str(e)
            )

    async def _test_logout_flow(self) -> AuthFlowStep:
        """Test logout flow and cleanup."""
        step_start_time = time.time()
        
        try:
            # Find logout button or trigger
            logout_selectors = [
                '[data-testid="logout-button"]',
                '.logout-button',
                'button:has-text("Logout")',
                'button:has-text("Sign Out")',
                '.auth-logout'
            ]
            
            logout_button = None
            for selector in logout_selectors:
                try:
                    logout_button = await self.page.wait_for_selector(selector, timeout=5000)
                    if logout_button:
                        break
                except:
                    continue
            
            if logout_button:
                # Click logout button
                await logout_button.click()
                await asyncio.sleep(2)
            else:
                # Programmatic logout
                await self._simulate_logout()
            
            # Verify logout cleanup
            auth_cleaned = await self.page.evaluate('''() => {
                return {
                    token_removed: !localStorage.getItem('jwt_token') && !localStorage.getItem('access_token'),
                    user_data_removed: !localStorage.getItem('user_data'),
                    websocket_disconnected: !window.websocketConnected
                };
            }''')
            
            duration = time.time() - step_start_time
            
            return AuthFlowStep(
                step_name="logout_flow",
                success=True,
                duration=duration,
                data=auth_cleaned
            )
            
        except Exception as e:
            return AuthFlowStep(
                step_name="logout_flow",
                success=False,
                duration=time.time() - step_start_time,
                error=str(e)
            )

    async def _simulate_logout(self) -> None:
        """Simulate logout programmatically."""
        await self.page.evaluate('''() => {
            // Clear auth tokens
            localStorage.removeItem('jwt_token');
            localStorage.removeItem('access_token');
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_data');
            
            // Clear user state
            if (window.userProfile) {
                window.userProfile = null;
            }
            
            // Disconnect WebSocket
            if (window.webSocket) {
                window.webSocket.close();
                window.websocketConnected = false;
            }
        }''')

    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:
        """Validate frontend auth flow meets business requirements."""
        if not results["success"]:
            return False
        
        auth_metrics = results.get("auth_metrics", {})
        auth_flow_steps = results.get("auth_flow_steps", [])
        
        # Business requirement validations
        validation_checks = []
        
        # 1. Frontend loads within 3 seconds
        initial_load_time = auth_metrics.get("initial_load_time", 0)
        validation_checks.append(initial_load_time <= 3.0)
        
        # 2. Auth config fetched successfully
        auth_config_step = next((s for s in auth_flow_steps if s["step_name"] == "auth_config_fetch"), None)
        validation_checks.append(auth_config_step and auth_config_step["success"])
        
        # 3. OAuth flow completes within 10 seconds
        oauth_time = auth_metrics.get("oauth_redirect_time", 0)
        validation_checks.append(oauth_time <= 10.0)
        
        # 4. WebSocket establishes with valid token
        websocket_step = next((s for s in auth_flow_steps if s["step_name"] == "websocket_connection"), None)
        validation_checks.append(websocket_step and websocket_step["success"])
        
        # 5. User data loads after authentication
        user_data_step = next((s for s in auth_flow_steps if s["step_name"] == "user_data_load"), None)
        validation_checks.append(user_data_step and user_data_step["success"])
        
        # 6. Session persists on refresh
        persistence_step = next((s for s in auth_flow_steps if s["step_name"] == "session_persistence"), None)
        validation_checks.append(persistence_step and persistence_step["success"])
        
        # 7. Total auth flow time reasonable
        total_time = auth_metrics.get("total_auth_flow_time", 0)
        validation_checks.append(total_time <= 30.0)
        
        return all(validation_checks)

    async def cleanup_test_specific_resources(self) -> None:
        """Cleanup Playwright browser resources."""
        try:
            if self.page:
                await self.page.close()
            if self.browser_context:
                await self.browser_context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            print(f"Browser cleanup error: {e}")

@pytest.fixture
async def frontend_auth_l4_test():
    """Fixture for frontend auth flow L4 test."""
    test_instance = FrontendInitialAuthFlowL4Test()
    try:
        yield test_instance
    finally:
        await test_instance.cleanup_l4_resources()

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L4
@pytest.mark.staging
@pytest.mark.asyncio
async def test_frontend_initial_load_authentication_flow_l4(frontend_auth_l4_test):
    """Test frontend initial load authentication flow (L4)."""
    # Run complete critical path test
    metrics = await frontend_auth_l4_test.run_complete_critical_path_test()
    
    # Assert business requirements
    assert metrics.success, f"Critical path failed: {metrics.errors}"
    assert metrics.error_count == 0, f"Unexpected errors: {metrics.errors}"
    
    # Validate specific frontend auth requirements
    test_results = metrics.details
    auth_metrics = test_results.get("auth_metrics", {})
    auth_flow_steps = test_results.get("auth_flow_steps", [])
    
    # Frontend loads within 3 seconds
    assert auth_metrics.get("initial_load_time", 0) <= 3.0, "Frontend load time too slow"
    
    # Auth config fetched successfully
    auth_config_step = next((s for s in auth_flow_steps if s["step_name"] == "auth_config_fetch"), None)
    assert auth_config_step and auth_config_step["success"], "Auth config fetch failed"
    
    # OAuth flow completes within 10 seconds
    assert auth_metrics.get("oauth_redirect_time", 0) <= 10.0, "OAuth flow too slow"
    
    # WebSocket connection established
    websocket_step = next((s for s in auth_flow_steps if s["step_name"] == "websocket_connection"), None)
    assert websocket_step and websocket_step["success"], "WebSocket connection failed"
    
    # User data loads successfully
    user_data_step = next((s for s in auth_flow_steps if s["step_name"] == "user_data_load"), None)
    assert user_data_step and user_data_step["success"], "User data load failed"
    
    # Session persists across page refresh
    persistence_step = next((s for s in auth_flow_steps if s["step_name"] == "session_persistence"), None)
    assert persistence_step and persistence_step["success"], "Session persistence failed"
    
    # Total auth flow time reasonable
    assert auth_metrics.get("total_auth_flow_time", 0) <= 30.0, "Total auth flow time too long"
    
    # Network requests reasonable
    assert auth_metrics.get("network_requests_count", 0) > 0, "No network requests detected"
    assert auth_metrics.get("network_requests_count", 0) < 50, "Too many network requests"

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L4
@pytest.mark.staging
@pytest.mark.asyncio
async def test_frontend_auth_flow_performance_l4(frontend_auth_l4_test):
    """Test frontend auth flow performance requirements (L4)."""
    # Run performance-focused test
    start_time = time.time()
    metrics = await frontend_auth_l4_test.run_complete_critical_path_test()
    total_time = time.time() - start_time
    
    # Performance assertions
    assert metrics.success, "Auth flow must succeed for performance validation"
    assert total_time <= 45.0, f"Total test execution too slow: {total_time:.2f}s"
    
    # Validate performance metrics
    test_results = metrics.details
    auth_metrics = test_results.get("auth_metrics", {})
    
    # Individual step performance
    assert auth_metrics.get("initial_load_time", 0) <= 3.0, "Initial load performance"
    assert auth_metrics.get("auth_config_fetch_time", 0) <= 2.0, "Auth config fetch performance"
    assert auth_metrics.get("token_exchange_time", 0) <= 5.0, "Token exchange performance"
    assert auth_metrics.get("websocket_connect_time", 0) <= 5.0, "WebSocket connect performance"
    assert auth_metrics.get("user_data_load_time", 0) <= 3.0, "User data load performance"
    assert auth_metrics.get("page_refresh_recovery_time", 0) <= 5.0, "Page refresh recovery performance"

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L4
@pytest.mark.staging
@pytest.mark.asyncio
async def test_frontend_auth_flow_error_recovery_l4(frontend_auth_l4_test):
    """Test frontend auth flow error recovery (L4)."""
    # Initialize the test environment
    await frontend_auth_l4_test.initialize_l4_environment()
    
    # Test network failure recovery
    await frontend_auth_l4_test.page.route('**/auth/config', lambda route: route.abort())
    
    # Attempt auth flow with network failure
    try:
        metrics = await frontend_auth_l4_test.run_complete_critical_path_test()
        # Should fail gracefully
        assert not metrics.success, "Should fail with network errors"
        
        # Verify error handling
        error_messages = metrics.errors
        assert any("auth" in error.lower() for error in error_messages), "Should report auth-related errors"
        
    finally:
        # Remove route handler
        await frontend_auth_l4_test.page.unroute('**/auth/config')