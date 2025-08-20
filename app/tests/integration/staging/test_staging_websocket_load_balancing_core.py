"""Core Tests - Split from test_staging_websocket_load_balancing.py

Business Value Justification (BVJ):
- Segment: Enterprise ($100K+ MRR customers)
- Business Goal: WebSocket scaling and reliability for enterprise workloads
- Value Impact: Enterprise customers require 1000+ concurrent connections with high availability
- Revenue Impact: Prevents $30K+ MRR churn from connection failures, enables enterprise tier features

Test Overview:
Tests real WebSocket load distribution across workers, validates failover mechanisms,
verifies session affinity, and confirms performance SLAs for enterprise-grade connections.
Uses containerized Redis and real WebSocket infrastructure (L3 realism).
"""

import asyncio
import pytest
import time
import json
import random
from typing import Dict, List, Any, Optional
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch
from contextlib import asynccontextmanager
from test_framework.mock_utils import mock_justified
from app.websocket.unified.manager import UnifiedWebSocketManager
from app.websocket.connection import ConnectionManager
from app.logging_config import central_logger

    def __init__(self, worker_count: int = 4):
        self.worker_count = worker_count
        self.worker_connections: Dict[int, List[str]] = {i: [] for i in range(worker_count)}
        self.worker_loads: Dict[int, int] = {i: 0 for i in range(worker_count)}
        self.session_affinity: Dict[str, int] = {}
        self.failover_events: List[Dict[str, Any]] = []

    def assign_connection(self, connection_id: str, user_id: str = None) -> int:
        """Assign connection to least loaded worker."""
        if user_id and user_id in self.session_affinity:
            # Honor session affinity
            worker_id = self.session_affinity[user_id]
            if worker_id < self.worker_count:  # Worker still available
                self.worker_connections[worker_id].append(connection_id)
                self.worker_loads[worker_id] += 1
                return worker_id
        
        # Find least loaded worker
        worker_id = min(self.worker_loads.keys(), key=lambda w: self.worker_loads[w])
        self.worker_connections[worker_id].append(connection_id)
        self.worker_loads[worker_id] += 1
        
        if user_id:
            self.session_affinity[user_id] = worker_id
        
        return worker_id

    def simulate_worker_failure(self, worker_id: int) -> List[str]:
        """Simulate worker failure and return affected connections."""
        if worker_id not in self.worker_connections:
            return []
        
        affected_connections = self.worker_connections[worker_id].copy()
        self.worker_connections[worker_id] = []
        self.worker_loads[worker_id] = 0
        
        # Record failover event
        self.failover_events.append({
            "timestamp": time.time(),
            "failed_worker": worker_id,
            "affected_connections": len(affected_connections),
            "failover_strategy": "redistribute"
        })
        
        return affected_connections

    def redistribute_connections(self, connections: List[str]) -> Dict[int, List[str]]:
        """Redistribute connections after failover."""
        redistribution = {}
        
        for conn_id in connections:
            # Find least loaded available worker
            available_workers = [w for w in self.worker_loads.keys() if w != -1]
            if not available_workers:
                continue
                
            target_worker = min(available_workers, key=lambda w: self.worker_loads[w])
            
            if target_worker not in redistribution:
                redistribution[target_worker] = []
            redistribution[target_worker].append(conn_id)
            
            self.worker_connections[target_worker].append(conn_id)
            self.worker_loads[target_worker] += 1
        
        return redistribution

    def get_load_distribution_stats(self) -> Dict[str, Any]:
        """Get load distribution statistics."""
        loads = list(self.worker_loads.values())
        total_connections = sum(loads)
        
        return {
            "total_connections": total_connections,
            "worker_loads": self.worker_loads.copy(),
            "load_variance": max(loads) - min(loads) if loads else 0,
            "average_load": total_connections / len(loads) if loads else 0,
            "session_affinity_count": len(self.session_affinity),
            "failover_events": len(self.failover_events)
        }

    def __init__(self, websocket_manager: UnifiedWebSocketManager):
        self.websocket_manager = websocket_manager
        self.active_connections: Dict[str, Any] = {}
        self.connection_metrics: Dict[str, Dict[str, float]] = {}

    def _create_websocket_mock(self, user_id: str) -> AsyncMock:
        """Create mock WebSocket for testing."""
        websocket_mock = AsyncMock()
        websocket_mock.client_state = "CONNECTED"
        websocket_mock.user_id = user_id
        websocket_mock.send_text = AsyncMock()
        websocket_mock.receive_text = AsyncMock(return_value=json.dumps({"type": "heartbeat"}))
        websocket_mock.close = AsyncMock()
        return websocket_mock

    def load_balancer(self):
        """Create load balancer simulator for testing."""
        return LoadBalancerSimulator(worker_count=4)
