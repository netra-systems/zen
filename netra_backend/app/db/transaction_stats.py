"""Transaction statistics and monitoring module.

Handles transaction metrics, performance tracking, and statistics calculation.
Focused module adhering to 25-line function limit and modular architecture.
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TransactionMetrics:
    """Metrics for transaction performance."""
    transaction_id: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    retry_count: int = 0
    error_count: int = 0
    success: bool = False
    isolation_level: Optional[str] = None
    
    def complete(self, success: bool = True) -> None:
        """Mark transaction as complete."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success


def _get_empty_transaction_stats() -> Dict[str, Any]:
    """Get empty transaction stats when no active transactions."""
    return {
        "active_transactions": 0, "avg_duration": 0.0,
        "max_duration": 0.0, "total_retries": 0
    }


def _calculate_single_transaction_duration(metrics: TransactionMetrics, current_time: float) -> float:
    """Calculate duration for a single transaction."""
    return current_time - metrics.start_time


def _collect_durations_and_retries(active_transactions: Dict[str, TransactionMetrics], current_time: float) -> tuple:
    """Collect all durations and retries from active transactions."""
    durations = [_calculate_single_transaction_duration(metrics, current_time) 
                for metrics in active_transactions.values()]
    total_retries = sum(metrics.retry_count for metrics in active_transactions.values())
    return durations, total_retries


def _calculate_transaction_durations_and_retries(active_transactions: Dict[str, TransactionMetrics], current_time: float) -> tuple:
    """Calculate durations and retries for active transactions."""
    return _collect_durations_and_retries(active_transactions, current_time)


def _build_transaction_stats(active_count: int, durations: list, total_retries: int) -> Dict[str, Any]:
    """Build transaction statistics dictionary."""
    return {
        "active_transactions": active_count,
        "avg_duration": sum(durations) / len(durations) if durations else 0.0,
        "max_duration": max(durations) if durations else 0.0,
        "total_retries": total_retries
    }


def _get_durations_and_retries_with_time(active_transactions: Dict[str, TransactionMetrics]) -> tuple:
    """Get current time and calculate durations and retries."""
    current_time = time.time()
    durations, total_retries = _calculate_transaction_durations_and_retries(active_transactions, current_time)
    return durations, total_retries


def get_transaction_stats(active_transactions: Dict[str, TransactionMetrics]) -> Dict[str, Any]:
    """Get transaction statistics."""
    active_count = len(active_transactions)
    if not active_transactions:
        return _get_empty_transaction_stats()
    durations, total_retries = _get_durations_and_retries_with_time(active_transactions)
    return _build_transaction_stats(active_count, durations, total_retries)


def generate_transaction_id() -> str:
    """Generate unique transaction ID."""
    return f"txn_{int(time.time())}_{hash(time.time()) % 10000}"