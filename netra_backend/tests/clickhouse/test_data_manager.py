import pytest
import asyncio

"""
ClickHouse Test Data Manager
Handles test data insertion and management for ClickHouse
"""""

import sys
from pathlib import Path
from datetime import datetime
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import json
from dataclasses import asdict
from typing import Any, Dict, List

from netra_backend.tests.clickhouse.data_generator import RealisticDataGenerator

from netra_backend.tests.clickhouse.data_models import LLMEvent, LogEntry, WorkloadMetric

class ClickHouseTestData:
    """Manage test data for ClickHouse tests"""

    def __init__(self):
        self.generator = RealisticDataGenerator(seed=42)

        async def insert_test_data(self, client, table_type: str, count: int):
            """Insert test data into ClickHouse"""
            if table_type == "llm_events":
                data = self.generator.generate_llm_events(count)
                await self._insert_llm_events(client, data)
            elif table_type == "workload_events":
                data = self.generator.generate_workload_metrics(count)
                await self._insert_workload_metrics(client, data)
            elif table_type == "logs":
                data = self.generator.generate_log_entries(count)
                await self._insert_logs(client, data)
            elif table_type == "corpus":
                data = self.generator.generate_corpus_data(count)
                await self._insert_corpus(client, data)

                def _format_llm_event_records(self, events: List[LLMEvent]) -> List[Dict[str, Any]]:
                    """Format LLM events for ClickHouse insertion"""
                    records = [asdict(event) for event in events]
                    for record in records:
                        record['timestamp'] = record['timestamp'].isoformat()
                        record['metadata'] = json.dumps(record['metadata'])
                        return records

                    async def _insert_llm_events(self, client, events: List[LLMEvent]):
                        """Insert LLM events into ClickHouse"""
                        records = self._format_llm_event_records(events)
                        await client.insert_data("llm_events", records)

                        def _format_workload_metrics(self, metrics: List[WorkloadMetric]) -> List[Dict[str, Any]]:
                            """Format workload metrics for ClickHouse insertion"""
                            records = []
                            for metric in metrics:
                                record = {
                                'timestamp': metric.timestamp.isoformat(),
                                'user_id': metric.user_id,
                                'workload_id': metric.workload_id,
                                'metrics.name': metric.metrics['name'],
                                'metrics.value': metric.metrics['value'],
                                'metrics.unit': metric.metrics['unit'],
                                'metadata': json.dumps(metric.metadata)
                                }
                                records.append(record)
                                return records

                            async def _insert_workload_metrics(self, client, metrics: List[WorkloadMetric]):
                                """Insert workload metrics into ClickHouse"""
                                records = self._format_workload_metrics(metrics)
                                await client.insert_data("workload_events", records)

                                def _format_log_entries(self, logs: List[LogEntry]) -> List[Dict[str, Any]]:
                                    """Format log entries for ClickHouse insertion"""
                                    records = []
                                    for log in logs:
                                        record = {
                                        'timestamp': log.timestamp.isoformat(),
                                        'level': log.level,
                                        'component': log.component,
                                        'message': log.message,
                                        'metadata': json.dumps(log.metadata)
                                        }
                                        records.append(record)
                                        return records

                                    async def _insert_logs(self, client, logs: List[LogEntry]):
                                        """Insert log entries into ClickHouse"""
                                        records = self._format_log_entries(logs)
                                        await client.insert_data("netra_app_internal_logs", records)

                                        def _format_corpus_data(self, corpus: List[Dict]) -> List[Dict]:
                                            """Format corpus data for ClickHouse insertion"""
                                            for record in corpus:
                                                record['metadata'] = json.dumps(record['metadata'])
                                                record['created_at'] = record['created_at'].isoformat()
                                                return corpus

                                            async def _insert_corpus(self, client, corpus: List[Dict]):
                                                """Insert corpus data into ClickHouse"""
                                                records = self._format_corpus_data(corpus)
                                                await client.insert_data("corpus_table", records)

                                                def get_sample_queries(self) -> Dict[str, str]:
                                                    """Get sample queries for testing"""
                                                    return {
                                                "llm_cost_by_model": """
                                                SELECT model, sum(cost_cents) as total_cost
                                                FROM llm_events
                                                WHERE timestamp >= now() - INTERVAL 1 DAY
                                                GROUP BY model
                                                ORDER BY total_cost DESC
                                                """,""
                                                "workload_anomalies": """
                                                WITH baseline AS (
                                                SELECT avg(arrayElement(metrics.value, 
                                                arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as avg_latency
                                                FROM workload_events
                                                WHERE timestamp >= now() - INTERVAL 1 HOUR
                                                )
                                                SELECT * FROM workload_events
                                                WHERE arrayElement(metrics.value, 
                                                arrayFirstIndex(x -> x = 'latency_ms', metrics.name)) > 
                                                (SELECT avg_latency * 2 FROM baseline)
                                                """,""
                                                "error_patterns": """
                                                SELECT 
                                                component,
                                                count() as error_count,
                                                groupArray(message)[1:5] as sample_errors
                                                FROM netra_app_internal_logs
                                                WHERE level = 'ERROR'
                                                GROUP BY component
                                                ORDER BY error_count DESC
                                                """""
                                                }