"""Core Tests - Split from test_database_transaction_coordination.py

BVJ: Enterprise ACID Compliance
- Segment: Enterprise (80% of MRR from financial/healthcare customers)  
- Business Goal: Data Integrity & Compliance ($50K-$100K MRR protection)
- Value Impact: Prevents corruption in customer AI optimization data
- Strategic Impact: Enterprise compliance requirement for SOX/HIPAA customers
"""

import pytest
import asyncio
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from dataclasses import dataclass
import tempfile
import time
from app.db.base import Base
from app.db.models_postgres import User, Thread, Message, Supply, ResearchSession
from app.core.database_types import DatabaseType
from app.tests.services.database_transaction_test_helpers import (

    def __init__(self):
        self.active_transactions: Dict[str, Dict[str, AsyncMock]] = {}
        self.transaction_log: Dict[str, Dict[str, Any]] = {}
        self.deadlock_detector = DeadlockDetector()
        self.metrics = TransactionCoordinationMetrics()

    def _log_transaction_state(self, transaction_id: str, state: str, error: str = None):
        """Log transaction state changes"""
        self.transaction_log[transaction_id] = {
            "state": state,
            "timestamp": datetime.now(UTC),
            "error": error
        }

    def __init__(self):
        self.lock_graph: Dict[str, List[str]] = {}
        self.transaction_locks: Dict[str, List[str]] = {}

    def __init__(self):
        self.consistency_checks: List[Dict[str, Any]] = []
