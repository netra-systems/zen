#!/usr/bin/env python3
"""
Integration Test: Multiple Service Failure Cascade Prevention

MISSION CRITICAL: This test prevents multiple service failures from cascading into
multiple fallback handlers that mask critical system failures.

PURPOSE: Ensure that when multiple services fail simultaneously (supervisor, thread_service, startup),
the system fails cleanly with clear errors rather than creating a cascade of fallback handlers
that provide degraded mock functionality.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Prevent cascading service failures from masking critical system issues
- Value Impact: Ensure clear failure modes rather than degraded mock functionality
- Strategic Impact: Protect system observability and prevent silent degradation

CRITICAL: This test must FAIL if cascading fallback handlers are created during multiple service failures.
"""

import asyncio
import json
import logging
import os
import sys
import time
import threading
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from unittest.mock import patch, MagicMock
import re

# CRITICAL: Add project root to Python path for imports  
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import SSOT components
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper
from shared.isolated_environment import get_env

# Import system components for service failure simulation
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.smd import StartupOrchestrator

# Import BusinessValueValidator
from tests.mission_critical.test_fallback_handler_degradation_prevention import (
    BusinessValueValidator, MockServiceController
)


class MultipleServiceFailureSimulator:
    """
    Simulator for multiple simultaneous service failures.
    
    This class creates realistic conditions where multiple critical services
    fail simultaneously, testing the system's failure handling behavior.
    """
    
    def __init__(self):
        """Initialize multiple service failure simulator."""
        self.original_services: Dict[str, Any] = {}
        self.failed_services: Set[str] = set()
        self._lock = threading.Lock()
        
    def simulate_supervisor_failure(self) -> None:
        """Simulate agent supervisor failure."""
        with self._lock:
            if 'supervisor' not in self.failed_services:
                self.original_services['supervisor'] = getattr(AgentRegistry, '_instance', None)
                AgentRegistry._instance = None
                self.failed_services.add('supervisor')
                logger.error("🚨 SERVICE FAILURE: Agent supervisor failed")
    
    def simulate_thread_service_failure(self) -> None:
        """Simulate thread service failure."""
        with self._lock:
            if 'thread_service' not in self.failed_services:
                self.original_services['thread_service'] = getattr(ThreadService, '_instance', None)
                ThreadService._instance = None
                self.failed_services.add('thread_service')
                logger.error("🚨 SERVICE FAILURE: Thread service failed")
    
    def simulate_startup_failure(self) -> None:
        """Simulate startup completion failure."""
        with self._lock:
            if 'startup' not in self.failed_services:
                self.original_services['startup'] = getattr(StartupOrchestrator, '_startup_complete', True)
                StartupOrchestrator._startup_complete = False
                self.failed_services.add('startup')
                logger.error("🚨 SERVICE FAILURE: Startup incomplete")
    
    def simulate_all_service_failures(self) -> None:
        """Simulate all critical service failures simultaneously."""
        logger.error("🚨 CATASTROPHIC FAILURE: Simulating all critical service failures")
        self.simulate_supervisor_failure()
        self.simulate_thread_service_failure()
        self.simulate_startup_failure()
        logger.error(f"🚨 SERVICES FAILED: {', '.join(self.failed_services)}")
    
    def restore_service(self, service_name: str) -> None:
        """Restore a specific failed service."""
        with self._lock:
            if service_name in self.failed_services:
                if service_name == 'supervisor':
                    AgentRegistry._instance = self.original_services.get('supervisor')
                elif service_name == 'thread_service':
                    ThreadService._instance = self.original_services.get('thread_service')
                elif service_name == 'startup':
                    StartupOrchestrator._startup_complete = self.original_services.get('startup', True)
                
                self.failed_services.discard(service_name)
                logger.info(f"✅ SERVICE RESTORED: {service_name}")
    
    def restore_all_services(self) -> None:
        """Restore all failed services."""
        with self._lock:
            for service in list(self.failed_services):
                self.restore_service(service)
            logger.info("✅ ALL SERVICES RESTORED")
    
    def get_failed_services(self) -> Set[str]:
        """Get list of currently failed services."""
        return self.failed_services.copy()
    
    def cleanup(self) -> None:
        """Clean up all service failure simulations."""
        self.restore_all_services()


class CascadeFailureDetector:
    """
    Detector for cascading fallback handler patterns.
    
    This class specifically looks for patterns that indicate multiple
    fallback handlers are being created in response to service failures.
    """
    
    CASCADE_PATTERNS = {
        'multiple_fallbacks': r'(fallback.*handler.*fallback|emergency.*emergency)',
        'cascade_indicators': r'(cascade|cascading|multiple.*fallback)',
        'degraded_mode': r'(degraded.*mode|emergency.*mode|limited.*mode)',
        'service_chain_failure': r'(supervisor.*fallback.*thread|thread.*fallback.*supervisor)',
        'mock_chain': r'(mock.*mock|template.*template|fallback.*fallback)',
    }
    
    def __init__(self):
        """Initialize cascade failure detector."""
        self.detected_cascades: List[str] = []
        self.cascade_count = 0
        
    def detect_cascade_patterns(self, content: str) -> List[str]:
        """
        Detect cascading fallback patterns in content.
        
        Args:
            content: Content to analyze for cascade patterns
            
        Returns:
            List of detected cascade patterns
        """
        detected = []
        content_lower = content.lower()
        
        for pattern_name, pattern in self.CASCADE_PATTERNS.items():
            if re.search(pattern, content_lower, re.IGNORECASE):
                detected.append(f"CASCADE: {pattern_name}")
                self.detected_cascades.append(pattern_name)
        
        if detected:
            self.cascade_count += 1
        
        return detected
    
    def is_cascade_detected(self) -> bool:
        """Check if any cascade patterns have been detected."""
        return len(self.detected_cascades) > 0 or self.cascade_count > 1


@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.fallback_prevention
@pytest.mark.cascade_failure_testing
class TestMultipleServiceFailureCascade:
    """
    Integration tests for multiple service failure cascade prevention.
    
    These tests ensure that multiple simultaneous service failures result
    in clean failure modes rather than cascading fallback handlers.
    """
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for cascade failure testing."""
        # Initialize environment and auth
        self.env = get_env()
        environment = self.env.get("TEST_ENV", "test")
        self.auth_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Initialize validators and simulators
        self.validator = BusinessValueValidator()
        self.cascade_detector = CascadeFailureDetector()
        self.service_simulator = MultipleServiceFailureSimulator()
        
        yield
        
        # Cleanup: Ensure all services are restored
        self.service_simulator.cleanup()
    
    async def test_all_services_failed_should_fail_cleanly_not_cascade(self):
        """
        TEST: All critical services failed should result in clean failure, not cascading fallbacks.
        
        This test simulates the worst-case scenario where all critical services
        (supervisor, thread_service, startup) fail simultaneously and validates
        that the system fails cleanly rather than creating cascading fallback handlers.
        
        EXPECTED BEHAVIOR:
        - System fails with clear error messages about service unavailability
        - NO cascading fallback handlers created
        - NO mock responses delivered to users
        - Clean failure preferred over degraded functionality
        
        FAILURE CONDITIONS:
        - Multiple fallback handlers created
        - Cascading mock responses delivered
        - System appears to work but provides no real value
        """
        logger.info("🧪 INTEGRATION TEST: All services failed - clean failure not cascade")
        
        # Step 1: Simulate all critical service failures
        self.service_simulator.simulate_all_service_failures()
        failed_services = self.service_simulator.get_failed_services()
        logger.error(f"🚨 SIMULATED FAILURES: {', '.join(failed_services)}")
        
        # Step 2: Attempt WebSocket connection with all services failed
        try:
            logger.info("🔌 Attempting WebSocket connection with all services failed")
            websocket = await self.auth_helper.connect_authenticated_websocket(timeout=10.0)
            
            # If connection succeeds, test what happens when we send a request
            try:
                catastrophic_request = {
                    "type": "user_message",
                    "content": "Perform comprehensive business analysis with optimization recommendations",
                    "thread_id": f"catastrophic-{int(time.time())}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(catastrophic_request))
                logger.info("📤 Sent request with all services failed")
                
                # Collect any responses
                events = []
                timeout = 15.0
                end_time = time.time() + timeout
                
                while time.time() < end_time and len(events) < 10:  # More events due to potential cascades
                    try:
                        message_str = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        event = json.loads(message_str)
                        events.append(event)
                        
                        # CRITICAL: Check for cascade patterns immediately
                        event_content = json.dumps(event)
                        
                        # Check for fallback patterns
                        has_fallback, fallback_patterns = self.validator.validate_response_for_fallback_patterns(event_content)
                        
                        # Check for cascade patterns
                        cascade_patterns = self.cascade_detector.detect_cascade_patterns(event_content)
                        
                        if has_fallback:
                            logger.error(f"🚨 FALLBACK DETECTED in event {len(events)}: {fallback_patterns}")
                        
                        if cascade_patterns:
                            logger.error(f"🚨 CASCADE DETECTED in event {len(events)}: {cascade_patterns}")
                        
                        # Immediate failure on cascade detection
                        if cascade_patterns or (has_fallback and len(events) > 1):
                            raise AssertionError(
                                f"🚨 CATASTROPHIC FAILURE: CASCADING FALLBACKS DETECTED\n"
                                f"Event {len(events)}: {event.get('type', 'unknown')}\n"
                                f"Fallback patterns: {fallback_patterns}\n"
                                f"Cascade patterns: {cascade_patterns}\n"
                                f"Event content: {event_content[:200]}...\n"
                                f"BUSINESS IMPACT: Multiple mock services masking critical system failure\n"
                                f"Failed services: {', '.join(failed_services)}"
                            )
                        
                    except asyncio.TimeoutError:
                        break
                    except Exception as e:
                        logger.error(f"Event reception error: {e}")
                        break
                
                # If we got events, analyze them for cascade patterns
                if events:
                    # Count fallback events
                    fallback_event_count = 0
                    all_fallback_patterns = []
                    
                    for event in events:
                        event_content = json.dumps(event)
                        has_fallback, patterns = self.validator.validate_response_for_fallback_patterns(event_content)
                        
                        if has_fallback:
                            fallback_event_count += 1
                            all_fallback_patterns.extend(patterns)
                    
                    # CRITICAL: Multiple fallback events indicate cascade
                    if fallback_event_count > 1:
                        raise AssertionError(
                            f"🚨 CASCADE FAILURE: MULTIPLE FALLBACK EVENTS\n"
                            f"Fallback events: {fallback_event_count}/{len(events)}\n"
                            f"All patterns: {all_fallback_patterns}\n"
                            f"BUSINESS IMPACT: Cascading mock responses masking system failure\n"
                            f"Expected: Clean failure with {', '.join(failed_services)} services down"
                        )
                    
                    # Single fallback might be acceptable, but validate it's not providing mock business value
                    if fallback_event_count == 1:
                        # Find the fallback event
                        fallback_events = []
                        for event in events:
                            event_content = json.dumps(event)
                            has_fallback, _ = self.validator.validate_response_for_fallback_patterns(event_content)
                            if has_fallback:
                                fallback_events.append(event)
                        
                        if fallback_events:
                            fallback_content = json.dumps(fallback_events[0])
                            
                            # Check if fallback is providing mock business value
                            has_mock_value, _ = self.validator.validate_response_for_business_value(fallback_content)
                            
                            if has_mock_value:
                                raise AssertionError(
                                    f"🚨 MOCK BUSINESS VALUE: Fallback providing fake insights\n"
                                    f"Fallback content: {fallback_content[:200]}...\n"
                                    f"BUSINESS IMPACT: Users receiving mock value instead of error\n"
                                    f"Should show clear error with services: {', '.join(failed_services)} failed"
                                )
                            
                            logger.warning(f"Single fallback detected but not providing mock business value")
                    
                    logger.info(f"Received {len(events)} events with {fallback_event_count} fallback events")
                
                await websocket.close()
                
                # If we get here without cascade, that's acceptable
                logger.success("✅ NO CASCADE DETECTED: System handled multiple service failures appropriately")
            
            except AssertionError as e:
                if "CASCADE" in str(e) or "FALLBACK" in str(e):
                    raise e
                else:
                    # Unexpected error during request processing
                    logger.success(f"✅ EXPECTED BEHAVIOR: Request failed appropriately: {e}")
        
        except Exception as e:
            error_msg = str(e)
            
            # Check if error indicates cascade or fallback creation
            if any(word in error_msg.lower() for word in ['cascade', 'fallback', 'mock', 'degraded']):
                raise AssertionError(f"🚨 CASCADE/FALLBACK in connection error: {error_msg}")
            
            # Connection failure with all services down is expected
            logger.success(f"✅ EXPECTED BEHAVIOR: Connection failed cleanly with all services down: {error_msg}")
    
    async def test_gradual_service_failure_cascade_prevention(self):
        """
        TEST: Gradual service failures should not create cascading fallbacks.
        
        This test simulates services failing one by one and validates that
        the system doesn't create additional fallback handlers as more services fail.
        
        EXPECTED BEHAVIOR:
        - First service failure handled appropriately (wait or clean error)
        - Additional service failures don't trigger more fallbacks
        - System maintains clean failure state
        """
        logger.info("🧪 INTEGRATION TEST: Gradual service failure cascade prevention")
        
        # Start with working connection
        websocket = await self.auth_helper.connect_authenticated_websocket(timeout=10.0)
        
        services_to_fail = ['supervisor', 'thread_service', 'startup']
        
        for i, service in enumerate(services_to_fail):
            logger.info(f"🚨 Failing service {i+1}/{len(services_to_fail)}: {service}")
            
            # Fail the service
            if service == 'supervisor':
                self.service_simulator.simulate_supervisor_failure()
            elif service == 'thread_service':
                self.service_simulator.simulate_thread_service_failure()
            elif service == 'startup':
                self.service_simulator.simulate_startup_failure()
            
            # Send request after each service failure
            request = {
                "type": "user_message",
                "content": f"Test request after {service} failure - step {i+1}",
                "thread_id": f"gradual-{service}-{int(time.time())}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                await websocket.send(json.dumps(request))
                
                # Check for immediate cascade patterns
                try:
                    message_str = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(message_str)
                    
                    event_content = json.dumps(event)
                    cascade_patterns = self.cascade_detector.detect_cascade_patterns(event_content)
                    
                    if cascade_patterns:
                        raise AssertionError(
                            f"🚨 GRADUAL CASCADE: Service {service} failure triggered cascade\n"
                            f"Patterns: {cascade_patterns}\n"
                            f"Failed services so far: {', '.join(self.service_simulator.get_failed_services())}"
                        )
                    
                    logger.info(f"✅ No cascade after {service} failure")
                    
                except asyncio.TimeoutError:
                    logger.info(f"✅ Appropriate timeout after {service} failure")
            
            except Exception as e:
                error_msg = str(e)
                if 'cascade' in error_msg.lower():
                    raise AssertionError(f"Cascade in send after {service} failure: {error_msg}")
                logger.info(f"✅ Appropriate failure after {service} failure: {error_msg}")
            
            # Brief pause between failures
            await asyncio.sleep(0.5)
        
        await websocket.close()
        logger.success("✅ GRADUAL FAILURE TEST PASSED: No cascading fallbacks detected")
    
    async def test_service_recovery_after_multiple_failures(self):
        """
        TEST: Service recovery after multiple failures should restore normal operation.
        
        This test validates that after multiple service failures are resolved,
        the system returns to normal operation without any residual fallback behavior.
        """
        logger.info("🧪 INTEGRATION TEST: Service recovery after multiple failures")
        
        # Simulate all failures
        self.service_simulator.simulate_all_service_failures()
        await asyncio.sleep(1.0)
        
        # Restore all services
        self.service_simulator.restore_all_services()
        await asyncio.sleep(1.0)
        
        # Test normal operation
        websocket = await self.auth_helper.connect_authenticated_websocket(timeout=10.0)
        
        request = {
            "type": "user_message",
            "content": "Test normal operation after multiple service recovery",
            "thread_id": f"recovery-{int(time.time())}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await websocket.send(json.dumps(request))
        
        # Validate normal operation
        events = []
        end_time = time.time() + 15.0
        
        while time.time() < end_time and len(events) < 5:
            try:
                message_str = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                event = json.loads(message_str)
                events.append(event)
            except asyncio.TimeoutError:
                continue
        
        # Validate no fallback or cascade patterns
        assert len(events) >= 5, f"Post-recovery operation failed: {len(events)}/5 events"
        
        for event in events:
            event_content = json.dumps(event)
            
            has_fallback, fallback_patterns = self.validator.validate_response_for_fallback_patterns(event_content)
            assert not has_fallback, f"Residual fallback after recovery: {fallback_patterns}"
            
            cascade_patterns = self.cascade_detector.detect_cascade_patterns(event_content)
            assert not cascade_patterns, f"Residual cascade patterns after recovery: {cascade_patterns}"
        
        await websocket.close()
        logger.success("✅ RECOVERY TEST PASSED: Normal operation restored after multiple failures")


if __name__ == "__main__":
    """
    Run the multiple service failure cascade prevention tests.
    
    Usage:
        python tests/integration/test_multiple_service_failure_cascade.py
        pytest tests/integration/test_multiple_service_failure_cascade.py -v
    """
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--pytest":
        pytest.main([__file__, "-v", "--tb=short"])
    else:
        print("🧪 INTEGRATION: Multiple Service Failure Cascade Prevention Tests")
        print("📋 These tests prevent multiple service failures from creating cascading fallbacks")
        print("🚀 Starting test execution...")
        
        exit_code = pytest.main([
            __file__,
            "-v",
            "-x",
            "--tb=short",
            "-m", "integration and cascade_failure_testing",
            "--durations=10"
        ])
        
        if exit_code == 0:
            print("✅ ALL TESTS PASSED: Multiple service failures handled correctly")
        else:
            print("🚨 TEST FAILURES: Cascade failure issues detected")
            
        sys.exit(exit_code)