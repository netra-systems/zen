#!/usr/bin/env python3
"""
MISSION CRITICAL E2E TEST: Complete User Prompt to Report Generation Flow

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prove core value proposition works end-to-end
- Value Impact: Users receive actionable AI insights that solve real problems
- Strategic Impact: Core validation of $3M+ ARR business model

This test validates the COMPLETE business value chain:
User sends prompt  ->  Agent processes  ->  Tool execution  ->  Final report with actionable insights

REQUIREMENTS FROM CLAUDE.md:
- NO MOCKS AT ALL - Uses REAL services only (WebSocket, Database, LLM)
- Tests the 5 REQUIRED WebSocket events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Real authentication with JWT tokens via E2EAuthHelper
- Complete flow validation with business value assessment
- Report content quality validation
- Performance timing validation under 2 minutes

KEY ARCHITECTURAL COMPLIANCE:
- Uses SSOT E2EAuthHelper for authentication
- Uses IsolatedEnvironment per unified_environment_management.xml
- Real WebSocket connections with actual backend
- Validates WebSocket agent integration per websocket_agent_integration_critical.xml
- Tests business value delivery, not just technical functionality

ANY FAILURE HERE INDICATES CORE VALUE PROPOSITION IS BROKEN.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import SSOT authentication and environment isolation
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, E2EAuthConfig
from test_framework.environment_isolation import isolated_test_env
from tests.clients.websocket_client import WebSocketTestClient
from tests.clients.backend_client import BackendTestClient
from tests.clients.auth_client import AuthTestClient
from shared.isolated_environment import get_env

# Create a simple fixture for testing
@pytest.fixture
async def isolated_test_environment():
    """Simple isolated test environment for E2E testing."""
    from test_framework.environment_isolation import setup_real_services_environment
    setup_real_services_environment()
    yield {}  # Return empty dict as placeholder


# ============================================================================
# BUSINESS VALUE REPORT VALIDATOR
# ============================================================================

class BusinessValueReportValidator:
    """Validates that reports contain actual business value, not just technical outputs."""
    
    # Keywords indicating actionable business insights
    BUSINESS_VALUE_KEYWORDS = {
        'recommendations', 'optimize', 'reduce', 'improve', 'save', 'savings',
        'cost', 'efficiency', 'performance', 'strategy', 'opportunity',
        'action', 'implement', 'upgrade', 'migrate', 'configure',
        'best practices', 'guidelines', 'steps', 'plan', 'solution'
    }
    
    # Keywords indicating quantitative insights
    QUANTITATIVE_KEYWORDS = {
        '$', '%', 'percent', 'dollars', 'cost', 'hours', 'minutes',
        'reduction', 'increase', 'improvement', 'roi', 'return on investment'
    }
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.business_score = 0.0
        self.has_actionable_insights = False
        self.has_quantitative_data = False
        
    def validate_report(self, report_content: str) -> Tuple[bool, float, List[str]]:
        """
        Validate that a report contains real business value.
        
        Args:
            report_content: The final report text from the agent
            
        Returns:
            Tuple of (is_valid, business_score, errors)
        """
        if not report_content or len(report_content.strip()) < 100:
            self.errors.append("Report too short - insufficient content for business value")
            return False, 0.0, self.errors
            
        content_lower = report_content.lower()
        
        # Check for business value keywords
        business_keywords_found = sum(1 for keyword in self.BUSINESS_VALUE_KEYWORDS 
                                    if keyword in content_lower)
        business_keyword_density = business_keywords_found / len(self.BUSINESS_VALUE_KEYWORDS)
        
        # Check for quantitative insights
        quantitative_keywords_found = sum(1 for keyword in self.QUANTITATIVE_KEYWORDS 
                                        if keyword in content_lower)
        has_quantitative = quantitative_keywords_found > 0
        
        # Check for actionable recommendations structure
        has_recommendations_section = any(marker in content_lower for marker in [
            'recommend', 'suggest', 'action', 'next steps', 'implementation'
        ])
        
        # Check for specific, concrete advice (not generic platitudes)
        has_specific_advice = any(marker in content_lower for marker in [
            'specific', 'configure', 'set to', 'change to', 'upgrade to',
            'migrate from', 'implement', 'deploy', 'enable', 'disable'
        ])
        
        # Calculate business value score (0-100)
        score = 0
        
        # Base score for having business keywords (0-30 points)
        score += min(30, business_keyword_density * 30)
        
        # Bonus for actionable recommendations (0-25 points)
        if has_recommendations_section:
            score += 15
            if has_specific_advice:
                score += 10
                
        # Bonus for quantitative insights (0-20 points)  
        if has_quantitative:
            score += 20
            
        # Bonus for comprehensive content (0-25 points)
        if len(report_content) > 500:
            score += 10
        if len(report_content) > 1000:
            score += 10
        if report_content.count('\n') > 10:  # Multi-section report
            score += 5
            
        self.business_score = score
        self.has_actionable_insights = has_recommendations_section and has_specific_advice
        self.has_quantitative_data = has_quantitative
        
        # Validation criteria
        is_valid = (
            score >= 50 and  # Minimum business value score
            has_recommendations_section and  # Must have recommendations
            len(report_content) >= 200  # Minimum substantial content
        )
        
        if not is_valid:
            if score < 50:
                self.errors.append(f"Insufficient business value score: {score:.1f}/100")
            if not has_recommendations_section:
                self.errors.append("Report lacks actionable recommendations")
            if len(report_content) < 200:
                self.errors.append(f"Report too brief: {len(report_content)} chars (min 200)")
                
        return is_valid, score, self.errors


# ============================================================================
# COMPLETE FLOW WEBSOCKET EVENT VALIDATOR
# ============================================================================

class CompleteFlowEventValidator:
    """Validates complete WebSocket event flow for business value delivery."""
    
    # REQUIRED events for complete business value flow
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    # Business value indicating event types
    BUSINESS_VALUE_EVENTS = {
        "report_generated", "final_report", "analysis_complete",
        "recommendations_ready", "insights_generated"
    }
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_timeline: List[Tuple[float, str, Dict]] = []
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.start_time = time.time()
        self.business_content_events: List[Dict] = []
        
    def record_event(self, event: Dict[str, Any]) -> None:
        """Record an event from real WebSocket connection."""
        timestamp = time.time() - self.start_time
        event_type = event.get("type", "unknown")
        
        self.events.append(event.copy())
        self.event_timeline.append((timestamp, event_type, event.copy()))
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        
        # Track business content events
        if self._has_business_content(event):
            self.business_content_events.append(event.copy())
        
        logger.info(f"[COMPLETE FLOW EVENT] {event_type} at {timestamp:.2f}s")
        
    def _has_business_content(self, event: Dict[str, Any]) -> bool:
        """Check if event contains business-relevant content."""
        content_fields = ['result', 'response', 'message', 'content', 'output', 'data']
        
        for field in content_fields:
            content = event.get(field, '')
            if isinstance(content, str) and len(content) > 50:
                return True
            elif isinstance(content, dict) and content:
                return True
                
        return False
        
    def validate_complete_flow(self) -> Tuple[bool, List[str]]:
        """Validate the complete business value delivery flow."""
        failures = []
        
        # 1. CRITICAL: All required events must be present
        missing_events = self.REQUIRED_EVENTS - set(self.event_counts.keys())
        if missing_events:
            failures.append(f"CRITICAL: Missing required WebSocket events: {missing_events}")
        
        # 2. CRITICAL: Events must be in proper order
        if not self._validate_event_order():
            failures.append("CRITICAL: WebSocket events out of order")
        
        # 3. CRITICAL: Tool events must be paired properly
        if not self._validate_tool_event_pairing():
            failures.append("CRITICAL: Unpaired tool execution events")
        
        # 4. CRITICAL: Must have substantial business content
        if not self._validate_business_content():
            failures.append("CRITICAL: Insufficient business content in events")
        
        # 5. CRITICAL: Timing must be reasonable for user experience
        if not self._validate_performance_timing():
            failures.append("CRITICAL: Flow execution time exceeds user tolerance")
        
        # 6. CRITICAL: Final completion must contain actionable content
        if not self._validate_completion_content():
            failures.append("CRITICAL: Final completion lacks substantial content")
        
        return len(failures) == 0, failures
    
    def _validate_event_order(self) -> bool:
        """Ensure events follow the correct business flow order."""
        if not self.event_timeline:
            self.errors.append("No events received - complete flow failure")
            return False
            
        # First event MUST be agent_started
        first_event = self.event_timeline[0][1]
        if first_event != "agent_started":
            self.errors.append(f"Flow must start with 'agent_started', got '{first_event}'")
            return False
        
        # Last event should be agent_completed or business value event
        last_event = self.event_timeline[-1][1]
        valid_endings = {"agent_completed", "final_report", "report_generated", "analysis_complete"}
        if last_event not in valid_endings:
            self.errors.append(f"Flow should end with completion event, got '{last_event}'")
            return False
            
        return True
    
    def _validate_tool_event_pairing(self) -> bool:
        """Ensure every tool_executing has matching tool_completed."""
        executing_count = self.event_counts.get("tool_executing", 0)
        completed_count = self.event_counts.get("tool_completed", 0)
        
        if executing_count != completed_count:
            self.errors.append(f"Tool event mismatch: {executing_count} executing vs {completed_count} completed")
            return False
            
        # Should have at least one tool execution for meaningful work
        if executing_count == 0:
            self.errors.append("No tool executions detected - insufficient agent work")
            return False
            
        return True
    
    def _validate_business_content(self) -> bool:
        """Validate sufficient business-relevant content in events."""
        if len(self.business_content_events) == 0:
            self.errors.append("No events contain substantial business content")
            return False
            
        # At least 3 events should have business content (thinking, tool results, completion)
        if len(self.business_content_events) < 3:
            self.errors.append(f"Insufficient business content events: {len(self.business_content_events)} (min 3)")
            return False
            
        return True
    
    def _validate_performance_timing(self) -> bool:
        """Validate performance is within user tolerance."""
        if not self.event_timeline:
            return True
            
        total_time = self.event_timeline[-1][0]
        
        # Complete flow should finish within 120 seconds (2 minutes)
        if total_time > 120.0:
            self.errors.append(f"Flow too slow: {total_time:.1f}s (max 120s)")
            return False
            
        # Should have meaningful activity (events spread over time)
        if total_time < 5.0:
            self.errors.append(f"Flow too fast: {total_time:.1f}s - likely skipping real work")
            return False
            
        return True
    
    def _validate_completion_content(self) -> bool:
        """Validate completion events have substantial content."""
        completion_events = [e for e in self.events 
                           if e.get("type") in {"agent_completed", "final_report", "report_generated"}]
        
        if not completion_events:
            self.errors.append("No completion events with content found")
            return False
            
        for event in completion_events:
            # Check for substantial content
            content_fields = ['result', 'response', 'final_response', 'report', 'analysis']
            has_content = False
            
            for field in content_fields:
                content = event.get(field, '')
                if isinstance(content, str) and len(content) > 100:
                    has_content = True
                    break
                elif isinstance(content, dict) and content:
                    has_content = True
                    break
                    
            if not has_content:
                self.errors.append(f"Completion event lacks substantial content: {event.get('type')}")
                return False
                
        return True


# ============================================================================
# COMPLETE FLOW TEST INFRASTRUCTURE
# ============================================================================

class CompleteUserPromptToReportTester:
    """Tests complete user prompt to report generation flow with REAL services."""
    
    def __init__(self):
        self.auth_helper = None
        self.ws_client = None
        self.backend_client = None
        self.auth_client = None
        self.test_user_token = None
        self.test_env = None
        
    async def setup_real_services(self, isolated_env) -> None:
        """Setup real service connections with proper authentication."""
        self.test_env = isolated_env
        
        # Initialize SSOT authentication helper
        self.auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Get service endpoints - use standard test ports since isolated_env is a resource dict
        from shared.isolated_environment import get_env
        env = get_env()
        
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000") 
        auth_host = env.get("AUTH_SERVICE_HOST", "localhost")
        auth_port = env.get("AUTH_SERVICE_PORT", "8081")
        
        backend_url = f"http://{backend_host}:{backend_port}"
        auth_url = f"http://{auth_host}:{auth_port}"
        ws_url = f"ws://{backend_host}:{backend_port}/ws"
        
        logger.info(f"Setting up real services - Backend: {backend_url}, Auth: {auth_url}, WS: {ws_url}")
        
        # Initialize clients
        self.backend_client = BackendTestClient(backend_url)
        self.auth_client = AuthTestClient(auth_url)
        
        # Create test user and authenticate via SSOT helper
        try:
            self.test_user_token, user_data = await self.auth_helper.authenticate_user()
            logger.info(f"Authenticated test user: {user_data.get('email', 'unknown')}")
        except Exception as e:
            # Fallback to direct auth client if SSOT helper fails
            logger.warning(f"SSOT auth failed ({e}), using fallback auth")
            test_user_data = await self.auth_client.create_test_user()
            self.test_user_token = test_user_data["token"]
        
        # Setup WebSocket client with authentication
        self.ws_client = WebSocketTestClient(ws_url)
        connected = await self.ws_client.connect(token=self.test_user_token, timeout=15.0)
        
        if not connected:
            raise RuntimeError("Failed to establish authenticated WebSocket connection")
            
        logger.info(" PASS:  Real services setup complete with authentication")
        
    async def test_complete_prompt_to_report_flow(
        self, 
        user_prompt: str, 
        timeout: float = 120.0
    ) -> Tuple[bool, CompleteFlowEventValidator, Optional[str]]:
        """
        Test complete user prompt to report generation flow.
        
        Args:
            user_prompt: The user's prompt/question
            timeout: Maximum time to wait for completion
            
        Returns:
            Tuple of (success, validator, final_report_content)
        """
        if not self.ws_client:
            raise RuntimeError("WebSocket client not initialized")
            
        validator = CompleteFlowEventValidator()
        final_report_content = None
        
        logger.info(f"[U+1F680] Starting complete flow test with prompt: '{user_prompt[:50]}...'")
        
        # Start event collection task
        event_task = asyncio.create_task(
            self._collect_complete_flow_events(validator, timeout)
        )
        
        # Send user prompt through WebSocket
        await self.ws_client.send_chat(text=user_prompt)
        logger.info("[U+1F4E4] User prompt sent via WebSocket")
        
        # Wait for complete flow to finish
        try:
            await event_task
        except asyncio.TimeoutError:
            logger.error(f"[U+23F0] Complete flow timed out after {timeout}s")
            
        # Extract final report content
        final_report_content = self._extract_final_report(validator.events)
        
        # Validate the complete flow
        is_valid, failures = validator.validate_complete_flow()
        
        if is_valid and final_report_content:
            logger.info(" PASS:  Complete prompt-to-report flow PASSED")
        else:
            logger.error(f" FAIL:  Complete flow FAILED: {failures}")
            
        return is_valid, validator, final_report_content
        
    async def _collect_complete_flow_events(
        self, 
        validator: CompleteFlowEventValidator, 
        timeout: float
    ) -> None:
        """Collect all WebSocket events until flow completion or timeout."""
        start_time = time.time()
        flow_completed = False
        
        completion_events = {"agent_completed", "final_report", "report_generated", "analysis_complete"}
        
        while not flow_completed and (time.time() - start_time) < timeout:
            try:
                message = await self.ws_client.receive(timeout=2.0)
                
                if message:
                    validator.record_event(message)
                    
                    # Check for flow completion
                    event_type = message.get("type", "")
                    if event_type in completion_events:
                        # Wait a bit more for any trailing events
                        await asyncio.sleep(1.0)
                        flow_completed = True
                        logger.info(f"[U+1F3C1] Flow completed with event: {event_type}")
                        
            except asyncio.TimeoutError:
                # Continue collecting - brief timeouts are expected
                continue
            except Exception as e:
                logger.error(f"Error collecting events: {e}")
                break
                
        if not flow_completed:
            logger.warning(f" WARNING: [U+FE0F] Flow did not complete within {timeout}s")
            
    def _extract_final_report(self, events: List[Dict[str, Any]]) -> Optional[str]:
        """Extract the final report content from events."""
        # Look for the final completion event with substantial content
        completion_events = [e for e in reversed(events) 
                           if e.get("type") in {"agent_completed", "final_report", "report_generated"}]
        
        for event in completion_events:
            # Try different content fields
            for field in ['result', 'response', 'final_response', 'report', 'analysis', 'message']:
                content = event.get(field)
                if isinstance(content, str) and len(content) > 100:
                    return content
                elif isinstance(content, dict):
                    # Try to extract text from structured content
                    if 'content' in content:
                        return str(content['content'])
                    elif 'text' in content:
                        return str(content['text'])
                    elif 'report' in content:
                        return str(content['report'])
                        
        # Fallback: concatenate all substantial content from completion events
        all_content = []
        for event in completion_events:
            for field in ['result', 'response', 'final_response', 'report', 'analysis']:
                content = event.get(field)
                if isinstance(content, str) and len(content) > 50:
                    all_content.append(content)
                    
        return '\n\n'.join(all_content) if all_content else None
        
    async def cleanup(self) -> None:
        """Cleanup test resources."""
        if self.ws_client:
            await self.ws_client.disconnect()
        if self.backend_client:
            await self.backend_client.close()
        if self.auth_client:
            await self.auth_client.close()
            
        logger.info("[U+1F9F9] Cleanup completed")


# ============================================================================
# MISSION CRITICAL TEST CASES  
# ============================================================================

class TestCompleteUserPromptToReportFlow:
    """MISSION CRITICAL: Tests complete user prompt to actionable report flow."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_basic_optimization_query_to_report(self, isolated_test_environment):
        """
        MISSION CRITICAL: Basic Optimization Query to Complete Report
        
        Tests the core business value proposition:
        User asks "How can I optimize my cloud costs?"  ->  
        Agent processes  ->  Tools execute  ->  
        Final report with actionable cost optimization recommendations
        
        This is the #1 most important test - validates core $3M+ ARR value prop.
        """
        tester = CompleteUserPromptToReportTester()
        
        try:
            # Setup real services with authentication  
            await tester.setup_real_services(isolated_test_environment)
            
            # Test the most common user query type
            optimization_query = (
                "I'm spending $10,000/month on AWS. How can I optimize my cloud costs "
                "and reduce my infrastructure spending? Please provide specific recommendations."
            )
            
            # Execute complete flow test
            start_time = time.time()
            is_valid, validator, final_report = await tester.test_complete_prompt_to_report_flow(
                user_prompt=optimization_query,
                timeout=120.0  # 2 minutes max for user tolerance
            )
            execution_time = time.time() - start_time
            
            # CRITICAL ASSERTIONS - Core Business Value
            assert is_valid, f"CRITICAL: Complete flow failed: {validator.errors}"
            assert final_report, "CRITICAL: No final report generated"
            
            # Validate WebSocket events were sent
            missing_events = validator.REQUIRED_EVENTS - set(validator.event_counts.keys())
            assert len(missing_events) == 0, f"Missing critical events: {missing_events}"
            
            # Validate business value in the report
            bv_validator = BusinessValueReportValidator()
            has_value, business_score, value_errors = bv_validator.validate_report(final_report)
            
            assert has_value, f"CRITICAL: Report lacks business value: {value_errors}"
            assert business_score >= 50, f"Business value score too low: {business_score}/100"
            
            # Validate report contains specific optimization recommendations
            report_lower = final_report.lower()
            optimization_terms = ['reduce', 'optimize', 'save', 'cost', 'recommend', 'strategy']
            found_terms = [term for term in optimization_terms if term in report_lower]
            assert len(found_terms) >= 3, f"Report lacks optimization focus, found: {found_terms}"
            
            # Validate performance
            assert execution_time <= 120.0, f"Flow too slow: {execution_time:.1f}s (max 120s)"
            
            # Validate tool usage (should execute analysis tools)
            tool_count = validator.event_counts.get("tool_executing", 0)
            assert tool_count >= 1, f"No tools executed for analysis (got {tool_count})"
            
            logger.info(f" PASS:  CRITICAL TEST PASSED: Optimization query  ->  report in {execution_time:.1f}s")
            logger.info(f" CHART:  Business Value Score: {business_score:.1f}/100")
            logger.info(f"[U+1F4DD] Report Length: {len(final_report)} chars")
            logger.info(f"[U+1F527] Tools Used: {tool_count}")
            
        except Exception as e:
            logger.error(f" FAIL:  CRITICAL TEST FAILED: {e}")
            raise
        finally:
            await tester.cleanup()
            
    @pytest.mark.asyncio
    @pytest.mark.e2e 
    @pytest.mark.real_services
    async def test_infrastructure_analysis_to_report(self, isolated_test_environment):
        """
        CRITICAL: Infrastructure Analysis Query to Comprehensive Report
        
        Tests complex analysis capability:
        User asks for infrastructure analysis  ->  Agent processes multiple dimensions  -> 
        Tools gather data  ->  Final report with architectural recommendations
        """
        tester = CompleteUserPromptToReportTester()
        
        try:
            await tester.setup_real_services(isolated_test_environment)
            
            analysis_query = (
                "Analyze my cloud infrastructure setup. I'm running 20 EC2 instances, "
                "using RDS for database, and S3 for storage. What are the best practices "
                "I should implement and what improvements can I make?"
            )
            
            start_time = time.time()
            is_valid, validator, final_report = await tester.test_complete_prompt_to_report_flow(
                user_prompt=analysis_query,
                timeout=180.0  # Longer timeout for complex analysis
            )
            execution_time = time.time() - start_time
            
            # CRITICAL: Flow must complete successfully
            assert is_valid, f"Infrastructure analysis flow failed: {validator.errors}"
            assert final_report, "No analysis report generated"
            
            # Validate comprehensive analysis content
            bv_validator = BusinessValueReportValidator()
            has_value, business_score, value_errors = bv_validator.validate_report(final_report)
            
            assert has_value, f"Analysis report lacks business value: {value_errors}"
            assert business_score >= 40, f"Analysis score too low: {business_score}/100"
            
            # Should mention specific AWS services (EC2, RDS, S3)
            report_lower = final_report.lower()
            aws_services = ['ec2', 'rds', 's3', 'database', 'storage', 'instances']
            mentioned_services = [svc for svc in aws_services if svc in report_lower]
            assert len(mentioned_services) >= 2, f"Should reference AWS services, found: {mentioned_services}"
            
            # Should have architectural recommendations
            arch_terms = ['architecture', 'configure', 'implement', 'best practice', 'security']
            arch_mentions = [term for term in arch_terms if term in report_lower]
            assert len(arch_mentions) >= 2, f"Should have architectural guidance, found: {arch_mentions}"
            
            # Complex analysis should use multiple tools
            tool_count = validator.event_counts.get("tool_executing", 0)
            assert tool_count >= 2, f"Complex analysis needs multiple tools (got {tool_count})"
            
            logger.info(f" PASS:  Infrastructure analysis test PASSED: {execution_time:.1f}s")
            logger.info(f" CHART:  Business Score: {business_score:.1f}/100")
            logger.info(f"[U+1F3D7][U+FE0F] AWS Services Mentioned: {mentioned_services}")
            
        finally:
            await tester.cleanup()
            
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_performance_timing_validation(self, isolated_test_environment):
        """
        CRITICAL: Performance and Timing Validation
        
        Tests that the complete flow meets performance requirements:
        - Simple queries complete within 60 seconds
        - All 5 WebSocket events are sent in proper sequence
        - Events arrive with reasonable timing gaps
        """
        tester = CompleteUserPromptToReportTester()
        
        try:
            await tester.setup_real_services(isolated_test_environment)
            
            # Simple query that should execute quickly
            simple_query = "What are 5 quick wins for reducing AWS costs?"
            
            start_time = time.time()
            is_valid, validator, final_report = await tester.test_complete_prompt_to_report_flow(
                user_prompt=simple_query,
                timeout=90.0  # Strict timeout for simple query
            )
            execution_time = time.time() - start_time
            
            # Performance assertions
            assert is_valid, f"Performance test flow failed: {validator.errors}"
            assert execution_time <= 90.0, f"Simple query too slow: {execution_time:.1f}s (max 90s)"
            
            # Timing validation - events should be spread reasonably
            timeline = validator.event_timeline
            assert len(timeline) >= 5, f"Insufficient events for timing analysis: {len(timeline)}"
            
            # First event should come quickly (within 5 seconds)
            first_event_time = timeline[0][0]
            assert first_event_time <= 5.0, f"First event delayed: {first_event_time:.1f}s"
            
            # Events should not have excessive gaps (max 30s between events)
            max_gap = 0.0
            for i in range(1, len(timeline)):
                gap = timeline[i][0] - timeline[i-1][0]
                max_gap = max(max_gap, gap)
                
            assert max_gap <= 30.0, f"Excessive gap between events: {max_gap:.1f}s"
            
            # Final validation - all required events present
            assert all(event in validator.event_counts for event in validator.REQUIRED_EVENTS), \
                f"Missing events: {validator.REQUIRED_EVENTS - set(validator.event_counts.keys())}"
                
            logger.info(f" PASS:  Performance test PASSED: {execution_time:.1f}s")
            logger.info(f" LIGHTNING:  Max event gap: {max_gap:.1f}s")
            logger.info(f"[U+1F4C8] Event sequence length: {len(timeline)}")
            
        finally:
            await tester.cleanup()
            
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services 
    async def test_websocket_event_sequence_validation(self, isolated_test_environment):
        """
        CRITICAL: WebSocket Event Sequence Validation
        
        Validates that all 5 required WebSocket events are sent in the correct sequence
        and contain appropriate content for business value delivery.
        """
        tester = CompleteUserPromptToReportTester()
        
        try:
            await tester.setup_real_services(isolated_test_environment)
            
            query = "Create a cloud security checklist for my AWS environment"
            
            is_valid, validator, final_report = await tester.test_complete_prompt_to_report_flow(
                user_prompt=query,
                timeout=120.0
            )
            
            # Event sequence validation
            assert is_valid, f"Event sequence test failed: {validator.errors}"
            
            # Validate all 5 required events are present
            for required_event in validator.REQUIRED_EVENTS:
                count = validator.event_counts.get(required_event, 0)
                assert count >= 1, f"Required event '{required_event}' not sent (count: {count})"
                
            # Validate event order
            event_sequence = [event[1] for event in validator.event_timeline]
            
            # Must start with agent_started
            assert event_sequence[0] == "agent_started", f"Wrong start event: {event_sequence[0]}"
            
            # Must end with completion event
            completion_events = {"agent_completed", "final_report", "analysis_complete"}
            assert event_sequence[-1] in completion_events, f"Wrong end event: {event_sequence[-1]}"
            
            # Agent_thinking should come before tool execution
            thinking_index = next((i for i, e in enumerate(event_sequence) if e == "agent_thinking"), -1)
            tool_index = next((i for i, e in enumerate(event_sequence) if e == "tool_executing"), -1)
            
            if tool_index >= 0:  # If tools were used
                assert thinking_index >= 0 and thinking_index < tool_index, \
                    "agent_thinking should come before tool_executing"
                    
            # Tool events should be paired
            tool_executing = validator.event_counts.get("tool_executing", 0)
            tool_completed = validator.event_counts.get("tool_completed", 0)
            assert tool_executing == tool_completed, \
                f"Unpaired tool events: {tool_executing} executing, {tool_completed} completed"
                
            # Business content validation
            assert len(validator.business_content_events) >= 3, \
                f"Insufficient business content events: {len(validator.business_content_events)}"
                
            logger.info(f" PASS:  WebSocket event sequence validation PASSED")
            logger.info(f" CYCLE:  Event sequence: {'  ->  '.join(event_sequence[:10])}...")  # First 10 events
            logger.info(f" CHART:  Total events: {len(event_sequence)}")
            
        finally:
            await tester.cleanup()


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    """
    Run the complete user prompt to report flow tests.
    
    These tests validate the core business value delivery using REAL services only.
    
    Usage:
        python test_complete_user_prompt_to_report_flow.py
        pytest test_complete_user_prompt_to_report_flow.py -v -s
    """
    
    logger.info("[U+1F680] Starting MISSION CRITICAL complete user prompt to report tests")
    logger.info(" WARNING: [U+FE0F]  USING REAL SERVICES ONLY - NO MOCKS")
    logger.info("[U+1F4BC] Testing complete business value delivery chain")
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v", "-s",
        "--tb=short",
        "--timeout=300",  # 5 minute timeout for complete flows
        "-x"  # Stop on first failure for critical tests
    ])
    
    if exit_code == 0:
        logger.info(" PASS:  ALL COMPLETE FLOW TESTS PASSED - Business value delivery verified")
    else:
        logger.error(" FAIL:  COMPLETE FLOW TESTS FAILED - Business value delivery broken")
    
    sys.exit(exit_code)