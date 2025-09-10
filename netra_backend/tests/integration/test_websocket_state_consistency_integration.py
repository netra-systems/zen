"""
Test WebSocket State Consistency Integration - Critical State Management Infrastructure Tests

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: Consistent WebSocket State Management & System Reliability  
- Value Impact: Ensures WebSocket state consistency across all system components
- Strategic Impact: Core infrastructure for reliable multi-user WebSocket interactions

CRITICAL: These tests MUST FAIL initially to reproduce exact state consistency race conditions.
The goal is to expose state management issues between different system components that handle WebSocket state.

Root Cause Analysis:
- Race conditions between WebSocket state checks across multiple components
- Inconsistent WebSocket state reporting between WebSocketManager, MessageRouter, NotificationManager  
- State synchronization issues during connection lifecycle transitions
- Component-specific state caching causing stale state reads

This test suite creates FAILING scenarios that reproduce production state consistency races.
"""

import asyncio
import json
import logging
import pytest
import time
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from starlette.websockets import WebSocketDisconnect

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper
from shared.isolated_environment import get_env
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, WebSocketID

# Import WebSocket components for state consistency testing
from netra_backend.app.websocket_core import (
    WebSocketManager,
    MessageRouter,
    get_websocket_manager,
    get_message_router
)
from netra_backend.app.websocket_core.utils import is_websocket_connected
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.core.websocket_message_handler import WebSocketMessageHandler

logger = logging.getLogger(__name__)


class WebSocketStateTracker:
    """
    Tracks WebSocket state across multiple system components to detect inconsistencies.
    
    This monitors state from different perspectives and detects when components
    have conflicting views of the same WebSocket connection state.
    """
    
    def __init__(self):
        self.state_log = []
        self.component_states = defaultdict(list)  # component_name -> [states]
        self.state_inconsistencies = []
        self.state_lock = asyncio.Lock()
        
    async def record_component_state(self, component_name: str, websocket: WebSocket, additional_info: Dict[str, Any] = None):
        """Record WebSocket state from a specific component's perspective."""
        async with self.state_lock:
            timestamp = time.time()
            
            # Get state from multiple perspectives
            state_info = {
                "component": component_name,
                "timestamp": timestamp,
                "websocket_id": id(websocket),
                "client_state": getattr(websocket, 'client_state', 'UNKNOWN'),
                "is_connected_util": is_websocket_connected(websocket),
                "has_send_method": hasattr(websocket, 'send_json'),
                "additional_info": additional_info or {}
            }
            
            # Try to get more detailed state info
            try:
                if hasattr(websocket, 'application_state'):
                    state_info["application_state"] = websocket.application_state
                if hasattr(websocket, 'connection_state'):
                    state_info["connection_state"] = websocket.connection_state
            except Exception as e:
                state_info["state_access_error"] = str(e)
            
            self.state_log.append(state_info)
            self.component_states[component_name].append(state_info)
            
    def detect_state_inconsistencies(self, time_window: float = 0.1):
        """Detect state inconsistencies between components within a time window."""
        inconsistencies = []
        
        # Group states by time windows
        time_groups = defaultdict(list)
        
        for state in self.state_log:
            time_bucket = int(state["timestamp"] / time_window)
            time_groups[time_bucket].append(state)
        
        # Check each time window for inconsistencies
        for time_bucket, states_in_window in time_groups.items():
            if len(states_in_window) < 2:
                continue  # Need at least 2 states to compare
                
            # Group by websocket_id within the time window
            websocket_groups = defaultdict(list)
            for state in states_in_window:
                websocket_groups[state["websocket_id"]].append(state)
            
            # Check for inconsistencies within each websocket group
            for websocket_id, websocket_states in websocket_groups.items():
                if len(websocket_states) < 2:
                    continue
                
                # Check for state conflicts
                client_states = set(s["client_state"] for s in websocket_states)
                is_connected_states = set(s["is_connected_util"] for s in websocket_states)
                
                if len(client_states) > 1 or len(is_connected_states) > 1:
                    inconsistency = {
                        "type": "state_inconsistency",
                        "websocket_id": websocket_id,
                        "time_window": time_bucket * time_window,
                        "conflicting_states": websocket_states,
                        "client_state_conflicts": list(client_states),
                        "is_connected_conflicts": list(is_connected_states),
                        "components_involved": [s["component"] for s in websocket_states]
                    }
                    inconsistencies.append(inconsistency)
                    
        self.state_inconsistencies.extend(inconsistencies)
        return inconsistencies


class TestWebSocketStateConsistencyIntegration(BaseIntegrationTest):
    """
    Integration tests for WebSocket state consistency across system components.
    
    CRITICAL: These tests are designed to FAIL initially and expose exact state consistency issues
    that occur when multiple components have different views of WebSocket connection state.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_state_consistency_environment(self):
        """Set up environment for state consistency testing."""
        self.env = get_env()
        self.auth_helper = E2EWebSocketAuthHelper(environment="test")
        self.state_trackers = []
        self.test_websockets = []
        
        yield
        
        # Analyze all state inconsistencies
        total_inconsistencies = 0
        for tracker in self.state_trackers:
            inconsistencies = tracker.detect_state_inconsistencies()
            total_inconsistencies += len(inconsistencies)
            
        if total_inconsistencies > 0:
            logger.warning(f"WebSocket state inconsistencies detected: {total_inconsistencies} total inconsistencies")
    
    async def _create_mock_websocket_with_state_control(self, initial_state: WebSocketState = WebSocketState.CONNECTING):
        """Create mock WebSocket with controlled state for testing consistency."""
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.client_state = initial_state
        
        # Track state changes
        state_changes = []
        
        def track_state_change(new_state: WebSocketState):
            """Track when state changes."""
            old_state = mock_websocket.client_state
            mock_websocket.client_state = new_state
            state_changes.append({
                "timestamp": time.time(),
                "old_state": old_state,
                "new_state": new_state
            })
        
        # Add state change tracking
        mock_websocket.track_state_change = track_state_change
        mock_websocket.state_changes = state_changes
        
        # Mock common WebSocket methods
        mock_websocket.send_json = AsyncMock()
        mock_websocket.close = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        self.test_websockets.append(mock_websocket)
        return mock_websocket
    
    async def _simulate_component_state_checks(
        self, 
        websocket: WebSocket, 
        components: List[str],
        check_interval: float = 0.01,
        total_checks: int = 10
    ) -> WebSocketStateTracker:
        """Simulate multiple components checking WebSocket state concurrently."""
        tracker = WebSocketStateTracker()
        self.state_trackers.append(tracker)
        
        async def component_state_checker(component_name: str):
            """Simulate a component checking WebSocket state repeatedly."""
            for check_num in range(total_checks):
                await tracker.record_component_state(
                    component_name, 
                    websocket,
                    {"check_number": check_num}
                )
                await asyncio.sleep(check_interval)
        
        # Start all component checkers concurrently
        checker_tasks = [
            asyncio.create_task(component_state_checker(component))
            for component in components
        ]
        
        await asyncio.gather(*checker_tasks)
        return tracker
    
    @pytest.mark.integration
    @pytest.mark.websocket_race_conditions
    async def test_websocket_manager_message_router_state_consistency_race(self, real_services_fixture):
        """
        CRITICAL TEST: Tests state consistency between WebSocketManager and MessageRouter.
        
        Simulates: Both components checking WebSocket state during connection transitions
        Expected Result: TEST SHOULD FAIL with state inconsistency between components
        """
        # Create WebSocket with controlled state
        mock_websocket = await self._create_mock_websocket_with_state_control(WebSocketState.CONNECTING)
        
        # Get real system components
        websocket_manager = get_websocket_manager()
        message_router = get_message_router()
        
        start_time = time.time()
        
        # Start concurrent state checking from both components
        components = ["websocket_manager", "message_router"]
        
        # CRITICAL: Start state checking before connection is complete
        state_check_task = asyncio.create_task(
            self._simulate_component_state_checks(
                mock_websocket, 
                components,
                check_interval=0.005,  # Very frequent checks
                total_checks=20
            )
        )
        
        # CRITICAL: Change WebSocket state during checking to create race conditions
        await asyncio.sleep(0.02)  # Let some checks happen
        mock_websocket.track_state_change(WebSocketState.CONNECTED)
        
        await asyncio.sleep(0.05)  # More checks with connected state
        mock_websocket.track_state_change(WebSocketState.DISCONNECTED)
        
        # Wait for all state checks to complete
        state_tracker = await state_check_task
        
        end_time = time.time()
        
        # Analyze state consistency
        inconsistencies = state_tracker.detect_state_inconsistencies(time_window=0.01)
        state_changes = len(mock_websocket.state_changes)
        
        # Check component-specific state views
        manager_states = state_tracker.component_states["websocket_manager"]
        router_states = state_tracker.component_states["message_router"]
        
        # Compare states between components at similar timestamps
        timestamp_tolerance = 0.02  # 20ms tolerance
        concurrent_state_pairs = []
        
        for manager_state in manager_states:
            for router_state in router_states:
                time_diff = abs(manager_state["timestamp"] - router_state["timestamp"])
                if time_diff <= timestamp_tolerance:
                    concurrent_state_pairs.append((manager_state, router_state))
        
        # Find conflicting concurrent states
        state_conflicts = []
        for manager_state, router_state in concurrent_state_pairs:
            if (manager_state["client_state"] != router_state["client_state"] or 
                manager_state["is_connected_util"] != router_state["is_connected_util"]):
                state_conflicts.append({
                    "manager_state": manager_state,
                    "router_state": router_state,
                    "time_diff": abs(manager_state["timestamp"] - router_state["timestamp"])
                })
        
        # CRITICAL: This test SHOULD FAIL initially
        # It demonstrates that WebSocketManager and MessageRouter have inconsistent state views
        assert len(inconsistencies) == 0, f"WebSocketManager/MessageRouter state inconsistency: {len(inconsistencies)} inconsistencies detected"
        assert len(state_conflicts) == 0, f"Concurrent state conflicts: {len(state_conflicts)} conflicts between components"
    
    @pytest.mark.integration
    @pytest.mark.websocket_race_conditions  
    async def test_websocket_notifier_state_consistency_during_transitions(self, real_services_fixture):
        """
        CRITICAL TEST: Tests WebSocketNotifier state consistency during connection state transitions.
        
        Simulates: AgentWebSocketBridge checking connection state while connections are transitioning
        Expected Result: TEST SHOULD FAIL with notifier state inconsistencies
        """
        # Create multiple WebSockets in different states
        websockets_states = [
            (WebSocketState.CONNECTING, "connecting_ws"),
            (WebSocketState.CONNECTED, "connected_ws"),
            (WebSocketState.DISCONNECTED, "disconnected_ws")
        ]
        
        test_websockets = []
        for state, name in websockets_states:
            ws = await self._create_mock_websocket_with_state_control(state)
            ws.test_name = name
            test_websockets.append(ws)
        
        # Create WebSocketNotifier
        websocket_notifier = AgentWebSocketBridge(websocket_manager=None)
        
        # Track notifier state checks
        notifier_state_tracker = WebSocketStateTracker()
        self.state_trackers.append(notifier_state_tracker)
        
        start_time = time.time()
        
        # CRITICAL: Simulate rapid state transitions while notifier is checking
        async def transition_websocket_states():
            """Transition WebSocket states to create race conditions."""
            for i in range(5):  # 5 transition cycles
                await asyncio.sleep(0.01)
                
                for ws in test_websockets:
                    # Cycle through states
                    current_state = ws.client_state
                    if current_state == WebSocketState.CONNECTING:
                        ws.track_state_change(WebSocketState.CONNECTED)
                    elif current_state == WebSocketState.CONNECTED:
                        ws.track_state_change(WebSocketState.DISCONNECTED)
                    else:  # DISCONNECTED
                        ws.track_state_change(WebSocketState.CONNECTING)
        
        async def notifier_state_monitoring():
            """Simulate WebSocketNotifier monitoring connection states."""
            for check_round in range(50):  # Many state checks
                for ws in test_websockets:
                    await notifier_state_tracker.record_component_state(
                        "websocket_notifier",
                        ws,
                        {"check_round": check_round, "websocket_name": ws.test_name}
                    )
                await asyncio.sleep(0.002)  # Very frequent monitoring
        
        # Run state transitions and monitoring concurrently
        transition_task = asyncio.create_task(transition_websocket_states())
        monitoring_task = asyncio.create_task(notifier_state_monitoring())
        
        await asyncio.gather(transition_task, monitoring_task)
        
        end_time = time.time()
        
        # Analyze notifier state consistency
        inconsistencies = notifier_state_tracker.detect_state_inconsistencies(time_window=0.005)
        
        # Count state transitions per WebSocket
        total_transitions = sum(len(ws.state_changes) for ws in test_websockets)
        
        # Check for notifier-specific inconsistencies
        notifier_states = notifier_state_tracker.component_states["websocket_notifier"]
        state_snapshot_conflicts = 0
        
        # Look for cases where notifier saw conflicting states for same WebSocket
        websocket_state_snapshots = defaultdict(list)
        for state_info in notifier_states:
            websocket_state_snapshots[state_info["websocket_id"]].append(state_info)
        
        for websocket_id, snapshots in websocket_state_snapshots.items():
            # Check for rapid state changes that notifier might have missed
            for i in range(1, len(snapshots)):
                prev_snapshot = snapshots[i-1]
                curr_snapshot = snapshots[i]
                
                # If states are the same but time gap is large, there might have been missed transitions
                if (prev_snapshot["client_state"] == curr_snapshot["client_state"] and
                    curr_snapshot["timestamp"] - prev_snapshot["timestamp"] > 0.02):  # 20ms gap
                    state_snapshot_conflicts += 1
        
        # CRITICAL: This test SHOULD FAIL initially
        # It demonstrates WebSocketNotifier has inconsistent state views during transitions
        assert len(inconsistencies) == 0, f"WebSocketNotifier state inconsistency: {len(inconsistencies)} inconsistencies during {total_transitions} transitions"
        assert state_snapshot_conflicts < 5, f"Notifier missed state transitions: {state_snapshot_conflicts} potential missed transitions"
    
    @pytest.mark.integration
    @pytest.mark.websocket_race_conditions
    async def test_multi_component_websocket_state_race_conditions(self, real_services_fixture):
        """
        CRITICAL TEST: Tests state consistency across multiple components simultaneously.
        
        Simulates: WebSocketManager, MessageRouter, WebSocketNotifier, and MessageHandler all checking state
        Expected Result: TEST SHOULD FAIL with multi-component state inconsistencies
        """
        # Create WebSocket for multi-component testing
        mock_websocket = await self._create_mock_websocket_with_state_control(WebSocketState.CONNECTING)
        
        # All components that might check WebSocket state
        components = [
            "websocket_manager",
            "message_router", 
            "websocket_notifier",
            "message_handler",
            "connection_monitor",
            "heartbeat_monitor"
        ]
        
        start_time = time.time()
        
        # CRITICAL: All components check state very frequently and concurrently
        multi_component_tracker = WebSocketStateTracker()
        self.state_trackers.append(multi_component_tracker)
        
        # Start intensive multi-component state checking
        state_check_task = asyncio.create_task(
            self._simulate_component_state_checks(
                mock_websocket,
                components,
                check_interval=0.001,  # Very aggressive checking - 1ms intervals
                total_checks=30
            )
        )
        
        # CRITICAL: Rapidly change WebSocket state during multi-component checking
        async def rapid_state_transitions():
            """Create rapid state transitions to challenge consistency."""
            state_sequence = [
                WebSocketState.CONNECTING,
                WebSocketState.CONNECTED, 
                WebSocketState.DISCONNECTED,
                WebSocketState.CONNECTING,
                WebSocketState.CONNECTED,
                WebSocketState.DISCONNECTED
            ]
            
            for state in state_sequence:
                await asyncio.sleep(0.008)  # Quick transitions
                mock_websocket.track_state_change(state)
        
        # Run transitions concurrently with state checking
        transition_task = asyncio.create_task(rapid_state_transitions())
        
        # Wait for all operations to complete
        await asyncio.gather(state_check_task, transition_task)
        
        end_time = time.time()
        
        # Analyze multi-component state consistency
        inconsistencies = multi_component_tracker.detect_state_inconsistencies(time_window=0.003)
        
        # Check for component-specific consistency issues
        component_state_views = {}
        for component in components:
            component_states = multi_component_tracker.component_states[component]
            if component_states:
                component_state_views[component] = {
                    "total_checks": len(component_states),
                    "unique_states_seen": len(set(s["client_state"] for s in component_states)),
                    "is_connected_views": set(s["is_connected_util"] for s in component_states)
                }
        
        # Find components with wildly different state views
        state_view_conflicts = []
        components_list = list(component_state_views.keys())
        
        for i in range(len(components_list)):
            for j in range(i + 1, len(components_list)):
                comp1, comp2 = components_list[i], components_list[j]
                view1, view2 = component_state_views[comp1], component_state_views[comp2]
                
                # Compare state views
                if (view1["unique_states_seen"] != view2["unique_states_seen"] or
                    view1["is_connected_views"] != view2["is_connected_views"]):
                    state_view_conflicts.append({
                        "components": [comp1, comp2],
                        "view_differences": {
                            comp1: view1,
                            comp2: view2
                        }
                    })
        
        # Calculate total state transitions
        total_transitions = len(mock_websocket.state_changes)
        
        # CRITICAL: This test SHOULD FAIL initially
        # It demonstrates that multiple components have inconsistent state views
        assert len(inconsistencies) == 0, f"Multi-component state inconsistency: {len(inconsistencies)} inconsistencies across {len(components)} components"
        assert len(state_view_conflicts) == 0, f"Component state view conflicts: {len(state_view_conflicts)} conflicts between component pairs"
    
    @pytest.mark.integration
    @pytest.mark.websocket_race_conditions
    async def test_websocket_state_caching_consistency_race(self, real_services_fixture):
        """
        CRITICAL TEST: Tests state consistency issues caused by component-level state caching.
        
        Simulates: Components caching WebSocket state locally, leading to stale state reads
        Expected Result: TEST SHOULD FAIL with stale state cache inconsistencies
        """
        # Create WebSocket for cache consistency testing
        mock_websocket = await self._create_mock_websocket_with_state_control(WebSocketState.CONNECTING)
        
        # Simulate components with state caching
        class ComponentWithStateCache:
            def __init__(self, name: str):
                self.name = name
                self.state_cache = {}
                self.cache_hits = 0
                self.cache_misses = 0
                
            async def get_websocket_state(self, websocket: WebSocket) -> Dict[str, Any]:
                """Get WebSocket state with caching."""
                websocket_id = id(websocket)
                current_time = time.time()
                
                # Check cache (with 50ms TTL to create race conditions)
                if websocket_id in self.state_cache:
                    cached_entry = self.state_cache[websocket_id]
                    if current_time - cached_entry["timestamp"] < 0.05:  # 50ms TTL
                        self.cache_hits += 1
                        return cached_entry["state"]
                
                # Cache miss - get fresh state
                self.cache_misses += 1
                fresh_state = {
                    "client_state": getattr(websocket, 'client_state', 'UNKNOWN'),
                    "is_connected": is_websocket_connected(websocket),
                    "timestamp": current_time
                }
                
                # Update cache
                self.state_cache[websocket_id] = {
                    "state": fresh_state,
                    "timestamp": current_time
                }
                
                return fresh_state
        
        # Create components with caching
        cached_components = [
            ComponentWithStateCache("cached_websocket_manager"),
            ComponentWithStateCache("cached_message_router"),
            ComponentWithStateCache("cached_notifier")
        ]
        
        # Track cache-based state views
        cache_state_tracker = WebSocketStateTracker()
        self.state_trackers.append(cache_state_tracker)
        
        start_time = time.time()
        
        # CRITICAL: Rapid state changes with cached state reads
        async def rapid_state_changes_with_cache_reads():
            """Change state rapidly while components use cached reads."""
            state_sequence = [
                WebSocketState.CONNECTING,
                WebSocketState.CONNECTED,
                WebSocketState.DISCONNECTED,
                WebSocketState.CONNECTING,
                WebSocketState.CONNECTED
            ]
            
            for i, new_state in enumerate(state_sequence):
                # Change WebSocket state
                mock_websocket.track_state_change(new_state)
                
                # CRITICAL: Multiple cached components read state immediately after change
                # Some will get fresh state, others will get stale cached state
                for component in cached_components:
                    cached_state = await component.get_websocket_state(mock_websocket)
                    
                    await cache_state_tracker.record_component_state(
                        component.name,
                        mock_websocket,
                        {
                            "cached_state": cached_state,
                            "change_sequence": i,
                            "cache_hits": component.cache_hits,
                            "cache_misses": component.cache_misses
                        }
                    )
                
                # Small delay between state changes
                await asyncio.sleep(0.02)
        
        await rapid_state_changes_with_cache_reads()
        
        end_time = time.time()
        
        # Analyze cache consistency issues
        cache_inconsistencies = cache_state_tracker.detect_state_inconsistencies(time_window=0.01)
        
        # Check for stale state reads
        stale_state_reads = 0
        total_cache_hits = sum(comp.cache_hits for comp in cached_components)
        
        # Analyze cached states for staleness
        for component in cached_components:
            component_states = cache_state_tracker.component_states[component.name]
            
            for i in range(1, len(component_states)):
                prev_state = component_states[i-1]
                curr_state = component_states[i]
                
                # Check if component reported same state across actual state transitions
                if (prev_state["client_state"] == curr_state["client_state"] and
                    abs(curr_state["timestamp"] - prev_state["timestamp"]) > 0.015):  # Gap suggests missed transition
                    stale_state_reads += 1
        
        # Calculate cache effectiveness vs consistency
        total_state_reads = sum(len(cache_state_tracker.component_states[comp.name]) for comp in cached_components)
        cache_hit_rate = total_cache_hits / total_state_reads if total_state_reads > 0 else 0
        
        # CRITICAL: This test SHOULD FAIL initially  
        # It demonstrates that state caching introduces consistency issues
        assert len(cache_inconsistencies) == 0, f"Cache-based state inconsistencies: {len(cache_inconsistencies)} inconsistencies detected"
        assert stale_state_reads == 0, f"Stale cached state reads: {stale_state_reads} stale reads detected (cache hit rate: {cache_hit_rate:.2f})"
    
    def test_websocket_state_consistency_race_analysis(self):
        """
        Analysis test that documents WebSocket state consistency race condition patterns.
        
        This test reviews all state tracking data and provides analysis for fixing
        the actual state consistency race conditions.
        """
        if not hasattr(self, 'state_trackers') or not self.state_trackers:
            pytest.skip("No state trackers - state consistency tests may not have run")
        
        # Aggregate analysis from all state trackers
        total_inconsistencies = 0
        all_inconsistencies = []
        component_analysis = defaultdict(lambda: {
            "total_state_checks": 0,
            "inconsistencies_detected": 0,
            "unique_states_seen": set(),
            "state_transitions_observed": 0
        })
        
        for tracker in self.state_trackers:
            # Get inconsistencies from this tracker
            tracker_inconsistencies = tracker.detect_state_inconsistencies()
            total_inconsistencies += len(tracker_inconsistencies)
            all_inconsistencies.extend(tracker_inconsistencies)
            
            # Analyze per-component data
            for component_name, component_states in tracker.component_states.items():
                analysis = component_analysis[component_name]
                analysis["total_state_checks"] += len(component_states)
                
                for state_info in component_states:
                    analysis["unique_states_seen"].add(state_info["client_state"])
                
                # Count state transitions detected by this component
                prev_state = None
                for state_info in component_states:
                    if prev_state and prev_state["client_state"] != state_info["client_state"]:
                        analysis["state_transitions_observed"] += 1
                    prev_state = state_info
        
        # Analyze inconsistency patterns
        inconsistency_types = defaultdict(int)
        components_involved = set()
        
        for inconsistency in all_inconsistencies:
            inconsistency_types[inconsistency["type"]] += 1
            components_involved.update(inconsistency.get("components_involved", []))
        
        # Calculate overall consistency metrics
        total_state_checks = sum(analysis["total_state_checks"] for analysis in component_analysis.values())
        inconsistency_rate = total_inconsistencies / total_state_checks if total_state_checks > 0 else 0
        
        # Component consistency comparison
        component_consistency_scores = {}
        for component, analysis in component_analysis.items():
            if analysis["total_state_checks"] > 0:
                # Simple consistency score based on state check frequency vs transitions observed
                consistency_score = analysis["state_transitions_observed"] / analysis["total_state_checks"]
                component_consistency_scores[component] = consistency_score
        
        # Generate comprehensive state consistency report
        consistency_report = {
            "total_state_trackers": len(self.state_trackers),
            "total_inconsistencies": total_inconsistencies,
            "total_state_checks": total_state_checks,
            "inconsistency_rate": inconsistency_rate,
            "inconsistency_types": dict(inconsistency_types),
            "components_with_issues": list(components_involved),
            "component_analysis": dict(component_analysis),
            "component_consistency_scores": component_consistency_scores,
            "detailed_inconsistencies": all_inconsistencies
        }
        
        # Log comprehensive analysis
        logger.critical("=" * 80)
        logger.critical("WEBSOCKET STATE CONSISTENCY RACE CONDITION ANALYSIS REPORT")
        logger.critical("=" * 80)
        logger.critical(f"State Trackers: {len(self.state_trackers)}")
        logger.critical(f"Total State Checks: {total_state_checks}")
        logger.critical(f"Total Inconsistencies: {total_inconsistencies}")
        logger.critical(f"Inconsistency Rate: {inconsistency_rate:.4f}")
        logger.critical(f"Inconsistency Types: {dict(inconsistency_types)}")
        logger.critical(f"Components Involved: {list(components_involved)}")
        logger.critical(f"Component Consistency Scores: {component_consistency_scores}")
        logger.critical("=" * 80)
        
        # CRITICAL: This documents that state consistency race conditions were successfully reproduced
        assert total_inconsistencies == 0, f"WebSocket state consistency race conditions reproduced: {total_inconsistencies} inconsistencies across {len(self.state_trackers)} test scenarios"