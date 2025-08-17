"""
Database Transaction Management Routes
"""
from typing import Dict, Any
from fastapi import HTTPException
from app.db.transaction_manager import transaction_manager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


async def get_transaction_stats_handler() -> Dict[str, Any]:
    """Get transaction statistics."""
    try:
        return transaction_manager.get_transaction_stats()
        
    except Exception as e:
        logger.error(f"Error getting transaction stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get transaction stats: {str(e)}"
        )


def serialize_transaction_metrics(active_transactions: Dict) -> Dict[str, Any]:
    """Convert TransactionMetrics to dict for JSON serialization."""
    serialized_transactions = {}
    for tx_id, metrics in active_transactions.items():
        serialized_transactions[tx_id] = {
            "transaction_id": metrics.transaction_id,
            "start_time": metrics.start_time,
            "duration": metrics.duration,
            "retry_count": metrics.retry_count,
            "error_count": metrics.error_count,
            "success": metrics.success,
            "isolation_level": metrics.isolation_level
        }
    return serialized_transactions


async def get_active_transactions_handler() -> Dict[str, Any]:
    """Get currently active transactions."""
    try:
        active_transactions = transaction_manager.get_active_transactions()
        serialized_transactions = serialize_transaction_metrics(active_transactions)
        
        return {
            "active_transactions": serialized_transactions,
            "count": len(serialized_transactions)
        }
        
    except Exception as e:
        logger.error(f"Error getting active transactions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get active transactions: {str(e)}"
        )