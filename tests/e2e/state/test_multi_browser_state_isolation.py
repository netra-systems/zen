"""
E2E Test: Multi-Browser State Isolation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Cross-device security is fundamental
- Business Goal: Ensure complete state isolation between different browser sessions
- Value Impact: Users can safely use the platform from multiple devices without cross-contamination
- Strategic Impact: Core security and multi-device functionality that prevents data leaks

This E2E test validates:
- Different browsers/devices don't share state or session data
- Cross-device authentication isolation with independent JWT tokens
- Independent WebSocket connections per browser session
- No cross-contamination of agent execution contexts between devices
- Proper session isolation for enterprise multi-device scenarios

CRITICAL: Tests fundamental security isolation between browser sessions
"""

import pytest
import asyncio
import uuid
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient

# Core system imports with absolute paths
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class BrowserSimulator:
    """Simulates different browser sessions with isolated authentication."""
    
    def __init__(self, browser_id: str, user_email: str, environment: str = "test"):
        self.browser_id = browser_id
        self.user_email = user_email
        self.environment = environment
        self.auth_helper = None
        self.websocket_auth_helper = None
        self.user_context = None
        self.websocket_connection = None
        self.session_data = {}
    
    async def initialize_browser_session(self):
        """Initialize isolated browser session with independent authentication."""
        # Create independent auth helpers for this browser
        self.auth_helper = E2EAuthHelper(environment=self.environment)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment=self.environment)
        
        # Create user context with browser-specific identifier
        self.user_context = await create_authenticated_user_context(
            user_email=self.user_email,
            environment=self.environment,
            permissions=["read", "write", "agent_execute", "websocket_connect"],
            websocket_enabled=True
        )
        
        # Store session metadata
        self.session_data = {
            'browser_id': self.browser_id,
            'user_id': str(self.user_context.user_id),
            'thread_id': str(self.user_context.thread_id),
            'initialization_time': time.time(),
            'jwt_token': self.user_context.agent_context.get('jwt_token')
        }
        
        return self.session_data
    
    async def connect_websocket(self, timeout: float = 15.0):
        """Connect WebSocket for this browser session."""
        if not self.websocket_auth_helper:
            raise RuntimeError("Browser session not initialized")
        
        self.websocket_connection = await self.websocket_auth_helper.connect_authenticated_websocket(
            timeout=timeout
        )
        return self.websocket_connection
    
    async def execute_agent_in_browser_context(
        self,
        agent_registry: AgentRegistry,
        agent_name: str = "triage_agent",
        user_message: str = "Browser-specific agent request"
    ):
        """Execute agent within this browser's isolated context."""
        if not self.user_context:
            raise RuntimeError("Browser session not initialized")
        
        id_generator = UnifiedIdGenerator()
        run_id = id_generator.generate_run_id(
            user_id=str(self.user_context.user_id),
            operation=f"browser_{self.browser_id}_execution"
        )
        
        execution_context = AgentExecutionContext(
            agent_name=agent_name,
            run_id=str(run_id),
            correlation_id=str(self.user_context.request_id),
            retry_count=0,
            user_context=self.user_context
        )
        
        agent_state = DeepAgentState(
            user_id=str(self.user_context.user_id),
            thread_id=str(self.user_context.thread_id),
            agent_context={
                **self.user_context.agent_context,
                'user_message': user_message,
                'browser_id': self.browser_id,
                'browser_session': True,
                'browser_isolation_test': True
            }
        )
        
        # Set up execution infrastructure
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        execution_core = AgentExecutionCore(agent_registry, websocket_bridge)
        
        # Execute agent
        result = await execution_core.execute_agent(
            context=execution_context,
            state=agent_state,
            timeout=30.0,
            enable_websocket_events=True
        )
        
        return result, str(run_id)
    
    async def collect_websocket_events(self, timeout: float = 25.0) -> List[Dict[str, Any]]:
        """Collect WebSocket events for this browser session."""
        if not self.websocket_connection:
            raise RuntimeError("WebSocket not connected")
        
        events = []
        
        try:
            while True:
                event_raw = await asyncio.wait_for(self.websocket_connection.recv(), timeout=timeout)
                event = json.loads(event_raw)
                events.append(event)
                
                if event.get('type') == 'agent_completed':
                    break
        except asyncio.TimeoutError:
            pass
        
        return events
    
    async def cleanup_browser_session(self):
        """Clean up browser session resources."""
        if self.websocket_connection:
            try:
                await self.websocket_connection.close()
            except:
                pass
        
        self.session_data.clear()


class TestMultiBrowserStateIsolation(BaseE2ETest):
    """E2E tests for complete state isolation between browser sessions."""
    
    @pytest.fixture
    def unified_id_generator(self):
        """ID generator for test consistency."""
        return UnifiedIdGenerator()
    
    @pytest.fixture
    async def real_agent_registry(self):
        """Real agent registry for browser isolation testing."""
        registry = AgentRegistry()
        await registry.initialize_registry()
        return registry
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    @pytest.mark.state_isolation
    @pytest.mark.security
    async def test_two_browser_complete_state_isolation(
        self,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test complete state isolation between two different browser sessions.
        
        CRITICAL: This test validates core security - browsers must not share any state.
        """
        
        # Create two separate browser simulators
        browser_1 = BrowserSimulator(
            browser_id="chrome_desktop",
            user_email="browser1_isolation_test@e2e.test"
        )
        
        browser_2 = BrowserSimulator(
            browser_id="firefox_mobile",
            user_email="browser2_isolation_test@e2e.test" 
        )
        
        try:
            # Initialize both browser sessions
            session_1_data = await browser_1.initialize_browser_session()
            session_2_data = await browser_2.initialize_browser_session()
            
            self.logger.info(f"Browser 1 session: {session_1_data['user_id']}")
            self.logger.info(f"Browser 2 session: {session_2_data['user_id']}")
            
            # Connect WebSockets for both browsers
            ws_1 = await browser_1.connect_websocket()
            ws_2 = await browser_2.connect_websocket()
            
            # Execute agents concurrently in both browsers
            async def execute_browser_1():
                """Execute agent in browser 1 and collect events."""
                events_task = asyncio.create_task(browser_1.collect_websocket_events())
                
                result, run_id = await browser_1.execute_agent_in_browser_context(
                    agent_registry=real_agent_registry,
                    user_message="Browser 1 isolation test request"
                )
                
                events = await events_task
                return result, run_id, events
            
            async def execute_browser_2():
                """Execute agent in browser 2 and collect events."""
                events_task = asyncio.create_task(browser_2.collect_websocket_events())
                
                result, run_id = await browser_2.execute_agent_in_browser_context(
                    agent_registry=real_agent_registry,
                    user_message="Browser 2 isolation test request"
                )
                
                events = await events_task
                return result, run_id, events
            
            # Execute both browsers concurrently
            (result_1, run_id_1, events_1), (result_2, run_id_2, events_2) = await asyncio.gather(
                execute_browser_1(),
                execute_browser_2()
            )
            
            # CRITICAL VALIDATION: Both executions succeeded
            assert result_1.success is True, f"Browser 1 execution failed: {result_1.error}"
            assert result_2.success is True, f"Browser 2 execution failed: {result_2.error}"
            
            # CRITICAL VALIDATION: Both browsers received events
            assert len(events_1) > 0, "Browser 1 received no WebSocket events"
            assert len(events_2) > 0, "Browser 2 received no WebSocket events"
            
            # CRITICAL VALIDATION: Complete isolation - no shared identifiers
            
            # 1. User IDs must be different
            assert session_1_data['user_id'] != session_2_data['user_id'], \
                f"ISOLATION VIOLATION: Browsers share user_id: {session_1_data['user_id']}"
            
            # 2. Thread IDs must be different
            assert session_1_data['thread_id'] != session_2_data['thread_id'], \
                f"ISOLATION VIOLATION: Browsers share thread_id: {session_1_data['thread_id']}"
            
            # 3. Run IDs must be different
            assert run_id_1 != run_id_2, \
                f"ISOLATION VIOLATION: Browsers share run_id: {run_id_1}"
            
            # 4. JWT tokens must be different
            assert session_1_data['jwt_token'] != session_2_data['jwt_token'], \
                "ISOLATION VIOLATION: Browsers share JWT token"
            
            # CRITICAL VALIDATION: Event isolation
            browser_1_run_ids = {event.get('run_id') for event in events_1}
            browser_2_run_ids = {event.get('run_id') for event in events_2}
            
            # Browser 1 should only see its own run_id
            assert run_id_1 in browser_1_run_ids, \
                "Browser 1 missing its own run_id in events"
            assert run_id_2 not in browser_1_run_ids, \
                f"ISOLATION VIOLATION: Browser 1 saw Browser 2 run_id ({run_id_2})"
            
            # Browser 2 should only see its own run_id
            assert run_id_2 in browser_2_run_ids, \
                "Browser 2 missing its own run_id in events"
            assert run_id_1 not in browser_2_run_ids, \
                f"ISOLATION VIOLATION: Browser 2 saw Browser 1 run_id ({run_id_1})"
            
            # CRITICAL VALIDATION: No cross-contamination of any session data
            browser_1_user_ids = {event.get('user_id') for event in events_1 if event.get('user_id')}
            browser_2_user_ids = {event.get('user_id') for event in events_2 if event.get('user_id')}
            
            # User IDs in events should be isolated
            assert browser_1_user_ids.isdisjoint(browser_2_user_ids), \
                f"ISOLATION VIOLATION: Browsers share user_ids in events: " \
                f"Browser1={browser_1_user_ids}, Browser2={browser_2_user_ids}"
            
            self.logger.info(" PASS:  CRITICAL SUCCESS: Complete browser state isolation validated")
            self.logger.info(f"  - Browser 1: User {session_1_data['user_id'][:8]}..., Run {run_id_1[:8]}...")
            self.logger.info(f"  - Browser 2: User {session_2_data['user_id'][:8]}..., Run {run_id_2[:8]}...")
            
        finally:
            # Clean up browser sessions
            await browser_1.cleanup_browser_session()
            await browser_2.cleanup_browser_session()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.state_isolation
    @pytest.mark.security
    async def test_same_user_different_browsers_isolation(
        self,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test isolation when same user accesses from different browsers.
        
        Even the same user should have isolated sessions across different browsers.
        """
        
        same_user_email = "same_user_multi_browser@e2e.test"
        
        # Create two browser sessions for the same user
        browser_desktop = BrowserSimulator(
            browser_id="desktop_chrome",
            user_email=same_user_email
        )
        
        browser_mobile = BrowserSimulator(
            browser_id="mobile_safari", 
            user_email=same_user_email
        )
        
        try:
            # Initialize sessions (same user, different browsers)
            desktop_session = await browser_desktop.initialize_browser_session()
            mobile_session = await browser_mobile.initialize_browser_session()
            
            self.logger.info(f"Desktop session for {same_user_email}: {desktop_session['user_id']}")
            self.logger.info(f"Mobile session for {same_user_email}: {mobile_session['user_id']}")
            
            # Connect WebSockets
            await browser_desktop.connect_websocket()
            await browser_mobile.connect_websocket()
            
            # Execute agents with slight delay to avoid race conditions
            desktop_task = asyncio.create_task(
                browser_desktop.execute_agent_in_browser_context(
                    real_agent_registry,
                    user_message="Desktop browser request"
                )
            )
            
            await asyncio.sleep(0.1)  # Small delay
            
            mobile_task = asyncio.create_task(
                browser_mobile.execute_agent_in_browser_context(
                    real_agent_registry, 
                    user_message="Mobile browser request"
                )
            )
            
            # Collect results
            (desktop_result, desktop_run_id), (mobile_result, mobile_run_id) = await asyncio.gather(
                desktop_task,
                mobile_task
            )
            
            # VALIDATION: Both executions succeeded
            assert desktop_result.success is True, f"Desktop execution failed: {desktop_result.error}"
            assert mobile_result.success is True, f"Mobile execution failed: {mobile_result.error}"
            
            # CRITICAL VALIDATION: Even same user has isolated browser sessions
            
            # Different user IDs (new session per browser)
            assert desktop_session['user_id'] != mobile_session['user_id'], \
                "Same user should have different user_ids across browser sessions"
            
            # Different thread IDs (new thread per browser)
            assert desktop_session['thread_id'] != mobile_session['thread_id'], \
                "Same user should have different thread_ids across browser sessions"
            
            # Different JWT tokens (independent authentication)
            assert desktop_session['jwt_token'] != mobile_session['jwt_token'], \
                "Same user should have different JWT tokens across browser sessions"
            
            # Different run IDs
            assert desktop_run_id != mobile_run_id, \
                "Same user should have different run_ids across browser sessions"
            
            self.logger.info(" PASS:  SUCCESS: Same user browser isolation validated")
            self.logger.info(f"  - Desktop: {desktop_session['user_id'][:8]}..., Thread: {desktop_session['thread_id'][:8]}...")
            self.logger.info(f"  - Mobile: {mobile_session['user_id'][:8]}..., Thread: {mobile_session['thread_id'][:8]}...")
            
        finally:
            await browser_desktop.cleanup_browser_session()
            await browser_mobile.cleanup_browser_session()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.state_isolation
    @pytest.mark.performance
    async def test_multiple_browser_sessions_performance(
        self,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test performance and isolation with multiple concurrent browser sessions.
        
        Validates system can handle multiple isolated browser sessions without degradation.
        """
        
        num_browsers = 4
        browsers = []
        
        # Create multiple browser simulators
        for i in range(num_browsers):
            browser = BrowserSimulator(
                browser_id=f"performance_browser_{i}",
                user_email=f"perf_user_{i}@e2e.test"
            )
            browsers.append(browser)
        
        start_time = time.time()
        
        try:
            # Initialize all browser sessions
            initialization_tasks = [browser.initialize_browser_session() for browser in browsers]
            session_data_list = await asyncio.gather(*initialization_tasks)
            
            # Connect WebSockets for all browsers
            websocket_tasks = [browser.connect_websocket() for browser in browsers]
            await asyncio.gather(*websocket_tasks)
            
            # Execute agents in all browsers concurrently
            execution_tasks = []
            for i, browser in enumerate(browsers):
                task = browser.execute_agent_in_browser_context(
                    real_agent_registry,
                    user_message=f"Performance test browser {i}"
                )
                execution_tasks.append(task)
            
            results = await asyncio.gather(*execution_tasks)
            
            total_time = time.time() - start_time
            
            # VALIDATION: All executions succeeded
            for i, (result, run_id) in enumerate(results):
                assert result.success is True, f"Browser {i} execution failed: {result.error}"
            
            # VALIDATION: Complete isolation across all browsers
            all_user_ids = {session['user_id'] for session in session_data_list}
            all_thread_ids = {session['thread_id'] for session in session_data_list}
            all_run_ids = {run_id for _, run_id in results}
            
            # All identifiers should be unique
            assert len(all_user_ids) == num_browsers, \
                f"User IDs not unique: {len(all_user_ids)} unique out of {num_browsers}"
            assert len(all_thread_ids) == num_browsers, \
                f"Thread IDs not unique: {len(all_thread_ids)} unique out of {num_browsers}"
            assert len(all_run_ids) == num_browsers, \
                f"Run IDs not unique: {len(all_run_ids)} unique out of {num_browsers}"
            
            # VALIDATION: Performance within acceptable bounds
            assert total_time < 45.0, \
                f"Multiple browser performance too slow: {total_time:.2f}s"
            
            average_time = total_time / num_browsers
            assert average_time < 15.0, \
                f"Average per-browser time too high: {average_time:.2f}s"
            
            self.logger.info(f" PASS:  PERFORMANCE SUCCESS: {num_browsers} browser isolation validated")
            self.logger.info(f"  - Total time: {total_time:.2f}s")
            self.logger.info(f"  - Average per browser: {average_time:.2f}s")
            self.logger.info(f"  - Unique user IDs: {len(all_user_ids)}")
            self.logger.info(f"  - Unique thread IDs: {len(all_thread_ids)}")
            self.logger.info(f"  - Unique run IDs: {len(all_run_ids)}")
            
        finally:
            # Clean up all browser sessions
            cleanup_tasks = [browser.cleanup_browser_session() for browser in browsers]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)