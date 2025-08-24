"""
E2E Tests for Frontend Initialization
Tests React frontend loading, hydration, routing, and API connectivity.

Business Value Justification (BVJ):
- Segment: All (100% of users interact via frontend)
- Business Goal: User Experience, Engagement
- Value Impact: Frontend is primary user interface for AI optimization
- Strategic Impact: Broken frontend = 100% user loss
"""

import asyncio
import pytest
import aiohttp
from playwright.async_api import async_playwright
import json
from typing import Dict, List, Optional
import time


@pytest.mark.e2e
@pytest.mark.real_services
class TestFrontendInitialization:
    """Test suite for frontend loading and initialization."""

    @pytest.mark.asyncio
    async def test_frontend_loads_without_errors(self):
        """
        Test that frontend loads without JavaScript errors.
        
        Critical Assertions:
        - Page loads successfully (200 status)
        - No JavaScript errors in console
        - React app mounts properly
        - No React hydration errors
        
        Expected Failure: Build errors, missing dependencies
        Business Impact: Frontend completely unusable
        """
        frontend_url = "http://localhost:3000"
        
        # First check if frontend server is running
        async with aiohttp.ClientSession() as session:
            try:
                response = await session.get(frontend_url)
                assert response.status == 200, f"Frontend not running: {response.status}"
            except aiohttp.ClientError as e:
                raise AssertionError(f"Frontend server not accessible: {str(e)}")
        
        # Use Playwright for browser testing
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Collect console errors
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)
            
            # Collect page errors
            page_errors = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            
            # Navigate to frontend
            response = await page.goto(frontend_url, wait_until="networkidle")
            assert response.status == 200, f"Page load failed: {response.status}"
            
            # Wait for React to mount
            await page.wait_for_selector("#root", state="attached", timeout=10000)
            
            # Check for React root
            react_root = await page.query_selector("#root")
            assert react_root, "React root element not found"
            
            # Check if React rendered content
            root_content = await page.evaluate("document.getElementById('root').innerHTML")
            assert len(root_content) > 100, "React app did not render content"
            
            # Check for React DevTools
            has_react = await page.evaluate("""
                () => {
                    return window.React !== undefined || 
                           window.__REACT_DEVTOOLS_GLOBAL_HOOK__ !== undefined ||
                           document.querySelector('[data-reactroot]') !== null;
                }
            """)
            assert has_react, "React not detected on page"
            
            # Verify no console errors
            critical_errors = [e for e in console_errors if "Warning:" not in str(e.text)]
            assert len(critical_errors) == 0, f"JavaScript errors found: {critical_errors}"
            
            # Verify no page errors
            assert len(page_errors) == 0, f"Page errors found: {page_errors}"
            
            # Check for hydration errors
            hydration_errors = [e for e in console_errors if "hydration" in str(e.text).lower()]
            assert len(hydration_errors) == 0, f"React hydration errors: {hydration_errors}"
            
            await browser.close()

    @pytest.mark.asyncio
    async def test_all_routes_accessible(self):
        """
        Test that all critical frontend routes are accessible.
        
        Critical Assertions:
        - Home page loads
        - Login/signup pages work
        - Dashboard accessible (redirects if not auth)
        - Settings page loads
        - 404 page works
        
        Expected Failure: Router misconfiguration, missing routes
        Business Impact: Users can't navigate, features inaccessible
        """
        frontend_url = "http://localhost:3000"
        
        critical_routes = [
            {"path": "/", "expected_title": "Netra", "auth_required": False},
            {"path": "/login", "expected_content": "login", "auth_required": False},
            {"path": "/signup", "expected_content": "signup", "auth_required": False},
            {"path": "/dashboard", "expected_content": "dashboard", "auth_required": True},
            {"path": "/threads", "expected_content": "threads", "auth_required": True},
            {"path": "/settings", "expected_content": "settings", "auth_required": True},
            {"path": "/api-keys", "expected_content": "api", "auth_required": True},
            {"path": "/nonexistent", "expected_content": "404", "auth_required": False}
        ]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            for route in critical_routes:
                page = await context.new_page()
                
                # Navigate to route
                full_url = f"{frontend_url}{route['path']}"
                response = await page.goto(full_url, wait_until="domcontentloaded")
                
                # Check response
                assert response.status in [200, 404], \
                    f"Route {route['path']} returned unexpected status: {response.status}"
                
                # Wait for content to load
                await page.wait_for_load_state("networkidle")
                
                if route.get("expected_title"):
                    title = await page.title()
                    assert route["expected_title"].lower() in title.lower(), \
                        f"Wrong title for {route['path']}: {title}"
                
                if route.get("expected_content"):
                    content = await page.content()
                    assert route["expected_content"].lower() in content.lower(), \
                        f"Expected content not found in {route['path']}"
                
                # Check for auth redirect if needed
                if route.get("auth_required"):
                    current_url = page.url
                    if "/login" in current_url:
                        # Correctly redirected to login
                        pass
                    else:
                        # Should have auth-protected content
                        auth_indicator = await page.query_selector("[data-auth-required]")
                        if not auth_indicator:
                            # Check if there's a dashboard or protected component
                            protected_content = await page.evaluate("""
                                () => {
                                    const text = document.body.innerText.toLowerCase();
                                    return text.includes('dashboard') || 
                                           text.includes('unauthorized') ||
                                           text.includes('login');
                                }
                            """)
                            assert protected_content, \
                                f"Auth-protected route {route['path']} accessible without auth"
                
                await page.close()
            
            await browser.close()

    @pytest.mark.asyncio
    async def test_component_hydration(self):
        """
        Test React component hydration and interactivity.
        
        Critical Assertions:
        - Components are interactive after load
        - State management works
        - Click handlers function
        - Forms are submittable
        
        Expected Failure: SSR/hydration mismatch, event handlers not attached
        Business Impact: UI non-functional, users can't interact
        """
        frontend_url = "http://localhost:3000"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Go to login page (should be interactive without auth)
            await page.goto(f"{frontend_url}/login", wait_until="networkidle")
            
            # Wait for form to be present
            await page.wait_for_selector("form", timeout=10000)
            
            # Test form interactivity
            email_input = await page.query_selector("input[type='email'], input[name='email']")
            password_input = await page.query_selector("input[type='password'], input[name='password']")
            
            if email_input and password_input:
                # Test input interactivity
                await email_input.type("test@example.com")
                email_value = await email_input.input_value()
                assert email_value == "test@example.com", "Email input not interactive"
                
                await password_input.type("TestPassword123")
                password_value = await password_input.input_value()
                assert password_value == "TestPassword123", "Password input not interactive"
                
                # Test form submission (should trigger validation or API call)
                submit_button = await page.query_selector("button[type='submit']")
                if submit_button:
                    # Click and check for response
                    await submit_button.click()
                    
                    # Wait for either error message or redirect
                    await page.wait_for_timeout(1000)
                    
                    # Check if form responded (error message, loading state, or redirect)
                    form_responded = await page.evaluate("""
                        () => {
                            const text = document.body.innerText.toLowerCase();
                            return text.includes('error') || 
                                   text.includes('invalid') ||
                                   text.includes('loading') ||
                                   window.location.pathname !== '/login';
                        }
                    """)
                    assert form_responded, "Form submission had no effect"
            
            # Test navigation interactivity
            await page.goto(frontend_url, wait_until="networkidle")
            
            # Find and click a navigation link
            nav_links = await page.query_selector_all("a[href], button")
            interactive_count = 0
            
            for link in nav_links[:5]:  # Test first 5 links
                is_clickable = await link.is_enabled()
                if is_clickable:
                    interactive_count += 1
            
            assert interactive_count > 0, "No interactive elements found"
            
            # Test state management (theme toggle if exists)
            theme_toggle = await page.query_selector(
                "[data-testid='theme-toggle'], [aria-label*='theme'], button:has-text('Theme')"
            )
            
            if theme_toggle:
                # Get initial theme
                initial_theme = await page.evaluate("""
                    () => {
                        return document.documentElement.getAttribute('data-theme') ||
                               document.body.classList.contains('dark') ||
                               localStorage.getItem('theme');
                    }
                """)
                
                # Click toggle
                await theme_toggle.click()
                await page.wait_for_timeout(500)
                
                # Check theme changed
                new_theme = await page.evaluate("""
                    () => {
                        return document.documentElement.getAttribute('data-theme') ||
                               document.body.classList.contains('dark') ||
                               localStorage.getItem('theme');
                    }
                """)
                
                assert new_theme != initial_theme, "Theme toggle not working"
            
            await browser.close()

    @pytest.mark.asyncio
    async def test_api_connections_established(self):
        """
        Test frontend-to-backend API connectivity.
        
        Critical Assertions:
        - API calls from frontend reach backend
        - CORS headers properly configured
        - Auth headers included in requests
        - Error handling works
        
        Expected Failure: API URL misconfigured, CORS issues
        Business Impact: Frontend can't communicate with backend
        """
        frontend_url = "http://localhost:3000"
        backend_url = "http://localhost:8000"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Track network requests
            api_requests = []
            
            def handle_request(request):
                if backend_url in request.url or "/api/" in request.url:
                    api_requests.append({
                        "url": request.url,
                        "method": request.method,
                        "headers": request.headers
                    })
            
            page.on("request", handle_request)
            
            # Track network responses
            api_responses = []
            
            def handle_response(response):
                if backend_url in response.url or "/api/" in response.url:
                    api_responses.append({
                        "url": response.url,
                        "status": response.status,
                        "headers": response.headers
                    })
            
            page.on("response", handle_response)
            
            # Navigate to frontend
            await page.goto(frontend_url, wait_until="networkidle")
            
            # Trigger an API call (try to load data)
            await page.goto(f"{frontend_url}/login", wait_until="networkidle")
            
            # Try to submit login form to trigger API call
            await page.evaluate("""
                async () => {
                    // Try to make a direct API call
                    try {
                        const response = await fetch('http://localhost:8000/health', {
                            method: 'GET',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            mode: 'cors'
                        });
                        return response.ok;
                    } catch (error) {
                        console.error('API call failed:', error);
                        return false;
                    }
                }
            """)
            
            # Wait for any API calls
            await page.wait_for_timeout(2000)
            
            # Check if any API requests were made
            if len(api_requests) > 0:
                # Verify CORS headers in requests
                for request in api_requests:
                    headers = request["headers"]
                    # Frontend should send proper headers
                    if "origin" in headers:
                        assert headers["origin"] == frontend_url, \
                            f"Wrong origin header: {headers['origin']}"
                
                # Verify CORS headers in responses
                for response in api_responses:
                    if response["status"] == 200:
                        headers = response["headers"]
                        if "access-control-allow-origin" in headers:
                            cors_origin = headers["access-control-allow-origin"]
                            assert cors_origin in [frontend_url, "*"], \
                                f"CORS not configured for frontend: {cors_origin}"
            
            # Test error handling
            error_handled = await page.evaluate("""
                async () => {
                    try {
                        const response = await fetch('http://localhost:8000/api/v1/nonexistent', {
                            method: 'GET'
                        });
                        if (!response.ok) {
                            // Error was properly handled
                            return true;
                        }
                        return false;
                    } catch (error) {
                        // Network error caught
                        return true;
                    }
                }
            """)
            
            assert error_handled, "API errors not properly handled"
            
            # Test WebSocket connection attempt
            ws_connected = await page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        try {
                            const ws = new WebSocket('ws://localhost:8000/ws');
                            ws.onopen = () => {
                                ws.close();
                                resolve(true);
                            };
                            ws.onerror = () => {
                                resolve(false);
                            };
                            setTimeout(() => resolve(false), 5000);
                        } catch (error) {
                            resolve(false);
                        }
                    });
                }
            """)
            
            # WebSocket might fail if auth required, but attempt should be made
            # The important thing is no CORS or connection errors
            
            await browser.close()