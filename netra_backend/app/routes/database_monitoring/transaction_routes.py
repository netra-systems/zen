"""
Database Transaction Management Routes
"""
from typing import Any, Dict

from fastapi import HTTPException

from netra_backend.app.db.transaction_manager import transaction_manager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def handle_transaction_stats_error(e: Exception) -> None:
    """Handle transaction stats retrieval error."""
    logger.error(f"Error getting transaction stats: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to get transaction stats: {str(e)}"
    )


async def get_transaction_stats_handler() -> Dict[str, Any]:
    """Get transaction statistics."""
    try:
        return transaction_manager.get_transaction_stats()
    except Exception as e:
        handle_transaction_stats_error(e)


def serialize_single_metric(metrics) -> Dict[str, Any]:
    """Serialize single transaction metric."""
    base_fields = _build_base_metric_fields(metrics)
    extra_fields = _build_extra_metric_fields(metrics)
    return {**base_fields, **extra_fields}


def _build_base_metric_fields(metrics) -> Dict[str, Any]:
    """Build base transaction metric fields."""
    return {
        "transaction_id": metrics.transaction_id, "start_time": metrics.start_time,
        "duration": metrics.duration, "retry_count": metrics.retry_count
    }


def _build_extra_metric_fields(metrics) -> Dict[str, Any]:
    """Build extra transaction metric fields."""
    return {
        "error_count": metrics.error_count, "success": metrics.success,
        "isolation_level": metrics.isolation_level
    }


def serialize_transaction_metrics(active_transactions: Dict) -> Dict[str, Any]:
    """Convert TransactionMetrics to dict for JSON serialization."""
    return {
        tx_id: serialize_single_metric(metrics)
        for tx_id, metrics in active_transactions.items()
    }


def build_active_transactions_response(serialized: Dict[str, Any]) -> Dict[str, Any]:
    """Build active transactions response."""
    return {
        "active_transactions": serialized,
        "count": len(serialized)
    }


def handle_active_transactions_error(e: Exception) -> None:
    """Handle active transactions retrieval error."""
    logger.error(f"Error getting active transactions: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to get active transactions: {str(e)}"
    )


async def get_active_transactions_handler() -> Dict[str, Any]:
    """Get currently active transactions."""
    try:
        active_transactions = transaction_manager.get_active_transactions()
        serialized = serialize_transaction_metrics(active_transactions)
        return build_active_transactions_response(serialized)
    except Exception as e:
        handle_active_transactions_error(e)