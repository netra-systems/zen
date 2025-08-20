"""Utilities Tests - Split from test_database_coordination_l4.py

Business Value Justification (BVJ):
- Segment: Enterprise/Platform (data consistency foundation)
- Business Goal: Ensure cross-service transaction integrity and database consistency
- Value Impact: Protects $12K MRR through data consistency and recovery capabilities
- Strategic Impact: Critical for maintaining data integrity across microservices and preventing data corruption

Critical Path: 
Transaction initiation -> Cross-service coordination -> Partial failure injection -> Rollback verification -> Consistency validation

Coverage: PostgreSQL + ClickHouse coordination, distributed transactions, failure recovery, staging environment validation
"""

import pytest
import asyncio
import psycopg2
import clickhouse_connect
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from app.services.database.postgres_service import PostgresService
from app.services.database.clickhouse_service import ClickHouseService
from app.services.database.transaction_coordinator import TransactionCoordinator
from app.services.redis.session_manager import RedisSessionManager
from tests.unified.e2e.staging_test_helpers import StagingTestSuite, get_staging_suite

    def __init__(self):
        self.staging_suite: Optional[StagingTestSuite] = None
        self.postgres_service: Optional[PostgresService] = None
        self.clickhouse_service: Optional[ClickHouseService] = None
        self.transaction_coordinator: Optional[TransactionCoordinator] = None
        self.redis_session: Optional[RedisSessionManager] = None
        self.active_transactions: Dict[str, Dict] = {}
        self.test_metrics = TransactionMetrics(
            total_transactions=0,
            successful_transactions=0,
            failed_transactions=0,
            rollback_transactions=0,
            consistency_checks_passed=0,
            average_transaction_time=0.0,
            cross_service_operations=0
        )

    def _resolve_data_references(self, data: Dict[str, Any], previous_results: List[Dict]) -> Dict[str, Any]:
        """Resolve cross-operation data references."""
        resolved_data = data.copy()
        
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("$"):
                reference = value[1:]  # Remove $ prefix
                
                # Look for reference in previous results
                for result in previous_results:
                    if not result.get("success", False):
                        continue
                        
                    if reference == "previous_user_id" and "user_id" in result.get("data", {}):
                        resolved_data[key] = result["data"]["user_id"]
                        break
                    elif reference == "previous_execution_id" and "execution_id" in result.get("data", {}):
                        resolved_data[key] = result["data"]["execution_id"]
                        break
                    elif reference in result.get("data", {}):
                        resolved_data[key] = result["data"][reference]
                        break
                    elif reference == "user_id" and result.get("result_id"):
                        resolved_data[key] = result["result_id"]
                        break
        
        return resolved_data

    def _update_average_transaction_time(self, new_time: float) -> None:
        """Update running average of transaction times."""
        total_transactions = self.test_metrics.successful_transactions + self.test_metrics.failed_transactions
        if total_transactions == 1:
            self.test_metrics.average_transaction_time = new_time
        else:
            current_avg = self.test_metrics.average_transaction_time
            self.test_metrics.average_transaction_time = (
                (current_avg * (total_transactions - 1) + new_time) / total_transactions
            )
