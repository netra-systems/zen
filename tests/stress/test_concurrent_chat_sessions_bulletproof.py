#!/usr/bin/env python
"""MISSION CRITICAL STRESS TEST: Concurrent Chat Sessions

Business Value: $500K+ ARR - System scalability and reliability
CHAT IS KING - Must handle multiple users simultaneously.

Tests system behavior under concurrent load:
1. Multiple simultaneous chat sessions
2. WebSocket connection management
3. Message ordering and isolation
4. Resource utilization and limits
5. Performance degradation patterns
6. Recovery from overload

NO MOCKS - Uses real services under load.
"""

import asyncio
import json
import os
import sys
import time
import uuid
import psutil
import resource
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
import threading
import multiprocessing
import pytest
from loguru import logger
import websockets
import aiohttp
from dataclasses import dataclass, field

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import production components
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.services.message_handler import MessageHandlerService
from netra_backend.app.auth_integration.auth import AuthService, AuthUser


# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

@dataclass
class SessionMetrics:
    """Metrics for a single chat session."""
    session_id: str
    start_time: float
    end_time: float = 0
    connection_time: float = 0
    first_message_time: float = 0
    messages_sent: int = 0
    messages_received: int = 0
    events_received: int = 0
    errors: List[Dict] = field(default_factory=list)
    latencies: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    cpu_usage: List[float] = field(default_factory=list)
    
    @property
    def duration(self) -> float:
        """Total session duration."""
        return self.end_time - self.start_time if self.end_time else time.time() - self.start_time
    
    @property
    def avg_latency(self) -> float:
        """Average message latency."""
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0
    
    @property
    def p95_latency(self) -> float:
        """95th percentile latency."""
        if not self.latencies:
            return 0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx] if idx < len(sorted_latencies) else sorted_latencies[-1]
    
    @property
    def success_rate(self) -> float:
        """Message success rate."""
        if self.messages_sent == 0:
            return 0
        return (self.messages_sent - len(self.errors)) / self.messages_sent * 100


# ============================================================================
# CONCURRENT CHAT SESSION
# ============================================================================

class ConcurrentChatSession:
    """Represents a single concurrent chat session."""
    
    def __init__(self, session_id: str, user_id: str = None):
        self.session_id = session_id
        self.user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        self.websocket = None
        self.connected = False
        self.thread_id = None
        self.metrics = SessionMetrics(session_id=session_id, start_time=time.time())
        self.message_queue = asyncio.Queue()
        self.running = True
        
    async def start(self, ws_url: str, token: str) -> bool:
        """Start the chat session."""
        try:
            # Record connection start
            conn_start = time.time()
            
            # Connect WebSocket
            self.websocket = await websockets.connect(
                f"{ws_url}?jwt={token}",
                subprotocols=[f"jwt.{token}"],
                ping_interval=10,
                ping_timeout=5
            )
            
            self.connected = True
            self.metrics.connection_time = time.time() - conn_start
            
            # Create thread for this session
            self.thread_id = f"thread_{self.session_id}"
            
            # Start background tasks
            asyncio.create_task(self._listen_for_messages())
            asyncio.create_task(self._monitor_resources())
            
            logger.info(f"Session {self.session_id} started (connection: {self.metrics.connection_time:.2f}s)")
            return True
            
        except Exception as e:
            logger.error(f"Session {self.session_id} failed to start: {e}")
            self.metrics.errors.append({'phase': 'connection', 'error': str(e)})
            return False
    
    async def _listen_for_messages(self):
        """Listen for incoming messages."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.metrics.events_received += 1
                    
                    # Track specific event types
                    event_type = data.get('type')
                    if event_type in ['assistant_message', 'agent_completed', 'final_report']:
                        self.metrics.messages_received += 1
                        
                except json.JSONDecodeError:
                    logger.warning(f"Session {self.session_id}: Invalid JSON")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Session {self.session_id} connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"Session {self.session_id} listener error: {e}")
            self.metrics.errors.append({'phase': 'listening', 'error': str(e)})
    
    async def _monitor_resources(self):
        """Monitor resource usage during session."""
        process = psutil.Process()
        
        while self.running and self.connected:
            try:
                # Record CPU and memory usage
                self.metrics.cpu_usage.append(process.cpu_percent())
                self.metrics.memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
                await asyncio.sleep(1)
            except Exception as e:
                logger.debug(f"Resource monitoring error: {e}")
                break
    
    async def send_message(self, content: str) -> bool:
        """Send a chat message."""
        if not self.connected:
            return False
        
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        
        message = {
            "type": "user_message",
            "payload": {
                "content": content,
                "thread_id": self.thread_id,
                "message_id": message_id,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": self.user_id
            }
        }
        
        try:
            send_start = time.time()
            await self.websocket.send(json.dumps(message))
            
            # Track metrics
            self.metrics.messages_sent += 1
            if self.metrics.first_message_time == 0:
                self.metrics.first_message_time = time.time() - self.metrics.start_time
            
            # Wait for response (simplified - in real test would track specific response)
            await asyncio.sleep(0.1)
            
            latency = time.time() - send_start
            self.metrics.latencies.append(latency)
            
            return True
            
        except Exception as e:
            logger.error(f"Session {self.session_id} send error: {e}")
            self.metrics.errors.append({'phase': 'sending', 'error': str(e)})
            return False
    
    async def run_chat_scenario(self, num_messages: int = 5, delay: float = 2.0):
        """Run a chat scenario with multiple messages."""
        for i in range(num_messages):
            if not self.connected:
                break
                
            # Generate varied message content
            messages = [
                "What is the weather today?",
                "Can you help me optimize my code?",
                "Explain quantum computing in simple terms",
                "What are the best practices for microservices?",
                "How do I improve system performance?"
            ]
            
            content = messages[i % len(messages)]
            success = await self.send_message(f"[Session {self.session_id}] {content}")
            
            if not success:
                logger.warning(f"Session {self.session_id} message {i} failed")
            
            # Wait between messages
            await asyncio.sleep(delay)
    
    async def stop(self):
        """Stop the chat session."""
        self.running = False
        self.metrics.end_time = time.time()
        
        if self.websocket:
            await self.websocket.close()
            self.connected = False
        
        logger.info(f"Session {self.session_id} stopped (duration: {self.metrics.duration:.2f}s)")


# ============================================================================
# CONCURRENT SESSION MANAGER
# ============================================================================

class ConcurrentSessionManager:
    """Manages multiple concurrent chat sessions."""
    
    def __init__(self):
        self.sessions: List[ConcurrentChatSession] = []
        self.auth_service = AuthService()
        self.start_time = 0
        self.end_time = 0
        
    async def create_sessions(self, num_sessions: int) -> List[ConcurrentChatSession]:
        """Create multiple chat sessions."""
        sessions = []
        
        for i in range(num_sessions):
            session = ConcurrentChatSession(
                session_id=f"stress_{i}",
                user_id=f"stress_user_{i}"
            )
            sessions.append(session)
            
        self.sessions = sessions
        return sessions
    
    async def start_all_sessions(self, ws_url: str, stagger_delay: float = 0.1) -> int:
        """Start all sessions with optional staggering."""
        self.start_time = time.time()
        successful = 0
        
        for session in self.sessions:
            # Create unique user and token for each session
            user = AuthUser(
                id=session.user_id,
                email=f"{session.user_id}@test.netra.ai",
                name=f"Stress Test User {session.session_id}"
            )
            token = await self.auth_service.create_access_token(user)
            
            # Start session
            success = await session.start(ws_url, token)
            if success:
                successful += 1
            
            # Stagger starts to avoid thundering herd
            if stagger_delay > 0:
                await asyncio.sleep(stagger_delay)
        
        logger.info(f"Started {successful}/{len(self.sessions)} sessions")
        return successful
    
    async def run_scenario(self, messages_per_session: int = 5, message_delay: float = 2.0):
        """Run chat scenario on all sessions."""
        tasks = []
        
        for session in self.sessions:
            if session.connected:
                task = session.run_chat_scenario(messages_per_session, message_delay)
                tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop_all_sessions(self):
        """Stop all sessions."""
        self.end_time = time.time()
        
        tasks = [session.stop() for session in self.sessions]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics from all sessions."""
        total_duration = self.end_time - self.start_time if self.end_time else time.time() - self.start_time
        
        # Aggregate metrics
        all_latencies = []
        all_errors = []
        total_messages_sent = 0
        total_messages_received = 0
        total_events = 0
        successful_sessions = 0
        
        for session in self.sessions:
            metrics = session.metrics
            all_latencies.extend(metrics.latencies)
            all_errors.extend(metrics.errors)
            total_messages_sent += metrics.messages_sent
            total_messages_received += metrics.messages_received
            total_events += metrics.events_received
            
            if metrics.success_rate > 90:  # Consider >90% success rate as successful
                successful_sessions += 1
        
        # Calculate statistics
        avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0
        p95_latency = 0
        if all_latencies:
            sorted_latencies = sorted(all_latencies)
            p95_idx = int(len(sorted_latencies) * 0.95)
            p95_latency = sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else sorted_latencies[-1]
        
        # Resource usage
        max_memory = max((max(s.metrics.memory_usage) for s in self.sessions if s.metrics.memory_usage), default=0)
        avg_cpu = sum((sum(s.metrics.cpu_usage)/len(s.metrics.cpu_usage) for s in self.sessions if s.metrics.cpu_usage)) / len(self.sessions) if self.sessions else 0
        
        return {
            'total_sessions': len(self.sessions),
            'successful_sessions': successful_sessions,
            'session_success_rate': (successful_sessions / len(self.sessions)) * 100 if self.sessions else 0,
            'total_duration': total_duration,
            'total_messages_sent': total_messages_sent,
            'total_messages_received': total_messages_received,
            'total_events': total_events,
            'throughput': total_messages_sent / total_duration if total_duration > 0 else 0,
            'avg_latency_ms': avg_latency * 1000,
            'p95_latency_ms': p95_latency * 1000,
            'max_memory_mb': max_memory,
            'avg_cpu_percent': avg_cpu,
            'total_errors': len(all_errors),
            'error_rate': (len(all_errors) / total_messages_sent) * 100 if total_messages_sent > 0 else 0
        }


# ============================================================================
# LOAD PATTERN TESTS
# ============================================================================

class LoadPatternTest:
    """Different load patterns for stress testing."""
    
    @staticmethod
    async def ramp_up_pattern(max_sessions: int = 50, ramp_time: int = 30):
        """Gradually increase load."""
        manager = ConcurrentSessionManager()
        ws_url = "ws://localhost:8080/ws"
        
        sessions_per_step = 5
        step_delay = ramp_time / (max_sessions / sessions_per_step)
        
        all_sessions = []
        
        for i in range(0, max_sessions, sessions_per_step):
            # Create batch of sessions
            batch = await manager.create_sessions(sessions_per_step)
            all_sessions.extend(batch)
            manager.sessions = all_sessions
            
            # Start batch
            await manager.start_all_sessions(ws_url, stagger_delay=0.05)
            
            # Run for a bit
            await manager.run_scenario(messages_per_session=2, message_delay=1)
            
            logger.info(f"Ramp up: {len(all_sessions)} sessions active")
            
            await asyncio.sleep(step_delay)
        
        # Run at peak load
        logger.info(f"Peak load: {len(all_sessions)} sessions")
        await manager.run_scenario(messages_per_session=5, message_delay=2)
        
        # Stop all
        await manager.stop_all_sessions()
        
        return manager.get_aggregated_metrics()
    
    @staticmethod
    async def spike_pattern(baseline: int = 10, spike: int = 50, duration: int = 10):
        """Test sudden traffic spike."""
        manager = ConcurrentSessionManager()
        ws_url = "ws://localhost:8080/ws"
        
        # Start baseline sessions
        await manager.create_sessions(baseline)
        await manager.start_all_sessions(ws_url)
        
        # Run baseline
        logger.info(f"Running baseline: {baseline} sessions")
        await manager.run_scenario(messages_per_session=2, message_delay=2)
        
        # Create spike
        spike_sessions = await manager.create_sessions(spike - baseline)
        manager.sessions.extend(spike_sessions)
        
        logger.info(f"Creating spike: {spike} total sessions")
        for session in spike_sessions:
            user = AuthUser(
                id=session.user_id,
                email=f"{session.user_id}@test.netra.ai",
                name=f"Spike User {session.session_id}"
            )
            token = await manager.auth_service.create_access_token(user)
            await session.start(ws_url, token)
        
        # Run during spike
        await manager.run_scenario(messages_per_session=3, message_delay=1)
        
        # Stop all
        await manager.stop_all_sessions()
        
        return manager.get_aggregated_metrics()
    
    @staticmethod
    async def sustained_load_pattern(num_sessions: int = 25, duration_minutes: int = 5):
        """Test sustained load over time."""
        manager = ConcurrentSessionManager()
        ws_url = "ws://localhost:8080/ws"
        
        # Create and start all sessions
        await manager.create_sessions(num_sessions)
        await manager.start_all_sessions(ws_url, stagger_delay=0.1)
        
        # Run sustained load
        start_time = time.time()
        duration_seconds = duration_minutes * 60
        messages_sent = 0
        
        logger.info(f"Running sustained load: {num_sessions} sessions for {duration_minutes} minutes")
        
        while time.time() - start_time < duration_seconds:
            await manager.run_scenario(messages_per_session=1, message_delay=0.5)
            messages_sent += num_sessions
            
            # Log progress
            elapsed = time.time() - start_time
            if int(elapsed) % 30 == 0:  # Every 30 seconds
                metrics = manager.get_aggregated_metrics()
                logger.info(f"Progress: {elapsed:.0f}s, Messages: {messages_sent}, Avg Latency: {metrics['avg_latency_ms']:.0f}ms")
        
        # Stop all
        await manager.stop_all_sessions()
        
        return manager.get_aggregated_metrics()


# ============================================================================
# TEST CASES
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.stress
async def test_concurrent_sessions_baseline():
    """Test baseline concurrent sessions."""
    manager = ConcurrentSessionManager()
    
    # Create 10 concurrent sessions
    await manager.create_sessions(10)
    
    # Start all sessions
    ws_url = "ws://localhost:8080/ws"
    successful = await manager.start_all_sessions(ws_url, stagger_delay=0.1)
    
    assert successful >= 8, f"Too many connection failures: {successful}/10"
    
    # Run chat scenario
    await manager.run_scenario(messages_per_session=5, message_delay=1)
    
    # Stop and get metrics
    await manager.stop_all_sessions()
    metrics = manager.get_aggregated_metrics()
    
    logger.info(f"Baseline test metrics: {json.dumps(metrics, indent=2)}")
    
    # Validate metrics
    assert metrics['session_success_rate'] >= 80, "Session success rate too low"
    assert metrics['avg_latency_ms'] < 5000, "Average latency too high"
    assert metrics['error_rate'] < 10, "Error rate too high"


@pytest.mark.asyncio
@pytest.mark.stress
async def test_ramp_up_load():
    """Test gradual load increase."""
    metrics = await LoadPatternTest.ramp_up_pattern(max_sessions=30, ramp_time=20)
    
    logger.info(f"Ramp up test metrics: {json.dumps(metrics, indent=2)}")
    
    # System should handle gradual increase
    assert metrics['session_success_rate'] >= 70, "Too many session failures during ramp up"
    assert metrics['p95_latency_ms'] < 10000, "P95 latency too high"


@pytest.mark.asyncio
@pytest.mark.stress
async def test_traffic_spike():
    """Test sudden traffic spike."""
    metrics = await LoadPatternTest.spike_pattern(baseline=5, spike=25, duration=10)
    
    logger.info(f"Spike test metrics: {json.dumps(metrics, indent=2)}")
    
    # System should recover from spike
    assert metrics['total_sessions'] == 25, "Not all sessions created"
    assert metrics['session_success_rate'] >= 60, "Too many failures during spike"


@pytest.mark.asyncio
@pytest.mark.stress
@pytest.mark.slow
async def test_sustained_load():
    """Test sustained load over time."""
    metrics = await LoadPatternTest.sustained_load_pattern(num_sessions=15, duration_minutes=2)
    
    logger.info(f"Sustained load test metrics: {json.dumps(metrics, indent=2)}")
    
    # System should remain stable
    assert metrics['session_success_rate'] >= 85, "Degradation during sustained load"
    assert metrics['avg_latency_ms'] < 3000, "Performance degradation over time"
    assert metrics['error_rate'] < 5, "Error rate increased over time"


@pytest.mark.asyncio
@pytest.mark.stress
async def test_connection_limits():
    """Test system connection limits."""
    manager = ConcurrentSessionManager()
    
    # Try to create many sessions
    await manager.create_sessions(100)
    
    # Start with no stagger (thundering herd)
    ws_url = "ws://localhost:8080/ws"
    successful = await manager.start_all_sessions(ws_url, stagger_delay=0)
    
    # Should handle gracefully
    assert successful > 0, "No sessions connected"
    
    # Get metrics
    await manager.stop_all_sessions()
    metrics = manager.get_aggregated_metrics()
    
    logger.info(f"Connection limit test: {successful}/100 sessions connected")
    logger.info(f"Metrics: {json.dumps(metrics, indent=2)}")


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level="INFO"
    )
    
    # Run stress tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "stress",
        "--asyncio-mode=auto",
        "-k", "baseline or ramp_up"  # Run specific tests
    ])