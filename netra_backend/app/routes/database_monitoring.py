"""Database Monitoring and Health Endpoints

This module provides comprehensive monitoring endpoints for database session management,
connection pool health, and session leak detection.

Business Value Justification (BVJ):
- Segment: Platform Operations (all tiers)
- Business Goal: Proactive monitoring to prevent system outages
- Value Impact: Early detection of connection issues prevents downtime
- Strategic Impact: Operational visibility enables proactive maintenance
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone

from netra_backend.app.database.request_scoped_session_factory import (
    get_session_factory, 
    get_factory_health,
    RequestScopedSessionFactory
)
from netra_backend.app.database import DatabaseManager
from netra_backend.app.dependencies import RequestScopedDbDep
from netra_backend.app.logging_config import central_logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = central_logger.get_logger(__name__)

router = APIRouter(prefix="/api/v1/monitoring/database", tags=["database-monitoring"])


@router.get("/health")
async def database_health_check() -> Dict[str, Any]:
    """Comprehensive database health check.
    
    Returns:
        Health status of database components including session factory,
        connection pool, and database connectivity
    """
    try:
        # Get session factory health
        factory_health = await get_factory_health()
        
        # Get database manager health  
        db_health = await DatabaseManager.health_check_all()
        
        # Test basic connectivity
        connectivity_test = False
        try:
            from netra_backend.app.database.request_scoped_session_factory import get_isolated_session
            async with get_isolated_session("health_check", "health_test") as session:
                result = await session.execute(text("SELECT 1 as test"))
                connectivity_test = result.scalar() == 1
        except Exception as e:
            logger.error(f"Database connectivity test failed: {e}")
        
        # Determine overall health
        factory_healthy = factory_health.get('status') == 'healthy'
        db_healthy = db_health.get('postgres', {}).get('status') == 'healthy'
        
        overall_status = 'healthy' if (factory_healthy and db_healthy and connectivity_test) else 'unhealthy'
        
        return {
            'overall_status': overall_status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'components': {
                'session_factory': factory_health,
                'database_manager': db_health,
                'connectivity_test': connectivity_test
            }
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'overall_status': 'error',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': str(e)
        }


@router.get("/connection-pool/metrics")
async def get_connection_pool_metrics() -> Dict[str, Any]:
    """Get detailed connection pool metrics.
    
    Returns:
        Detailed metrics about connection pool usage, session lifecycle,
        and potential issues
    """
    try:
        factory = await get_session_factory()
        pool_metrics = factory.get_pool_metrics()
        session_metrics = factory.get_session_metrics()
        
        # Get engine pool status
        engine = DatabaseManager.create_application_engine()
        engine_pool_status = DatabaseManager.get_pool_status(engine)
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'factory_metrics': {
                'active_sessions': pool_metrics.active_sessions,
                'total_sessions_created': pool_metrics.total_sessions_created,
                'sessions_closed': pool_metrics.sessions_closed,
                'leaked_sessions': pool_metrics.leaked_sessions,
                'pool_exhaustion_events': pool_metrics.pool_exhaustion_events,
                'circuit_breaker_trips': pool_metrics.circuit_breaker_trips,
                'peak_concurrent_sessions': pool_metrics.peak_concurrent_sessions,
                'avg_session_lifetime_ms': pool_metrics.avg_session_lifetime_ms,
                'last_pool_exhaustion': pool_metrics.last_pool_exhaustion.isoformat() if pool_metrics.last_pool_exhaustion else None,
                'last_leak_detection': pool_metrics.last_leak_detection.isoformat() if pool_metrics.last_leak_detection else None
            },
            'engine_pool_status': engine_pool_status,
            'active_session_count': len(session_metrics),
            'session_details': session_metrics
        }
        
    except Exception as e:
        logger.error(f"Failed to get connection pool metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/test/concurrent-load")
async def test_concurrent_load(
    concurrent_sessions: int = Query(default=50, ge=1, le=200, description="Number of concurrent sessions"),
    queries_per_session: int = Query(default=3, ge=1, le=10, description="Queries per session")
) -> Dict[str, Any]:
    """Test concurrent session load to validate isolation and pool limits.
    
    Args:
        concurrent_sessions: Number of concurrent sessions to create
        queries_per_session: Number of queries each session should execute
        
    Returns:
        Load test results with session metrics and pool status
    """
    import asyncio
    
    try:
        start_time = datetime.now(timezone.utc)
        
        async def run_session_workload(session_index: int):
            """Run workload for a single session."""
            user_id = f"load_test_user_{session_index}"
            request_id = f"load_test_{session_index}_{int(start_time.timestamp())}"
            
            try:
                from netra_backend.app.database.request_scoped_session_factory import get_isolated_session
                
                async with get_isolated_session(user_id, request_id) as session:
                    results = []
                    for query_index in range(queries_per_session):
                        query_start = datetime.now(timezone.utc)
                        result = await session.execute(
                            text("SELECT :session_index as session_id, :query_index as query_id, NOW() as timestamp"),
                            {'session_index': session_index, 'query_index': query_index}
                        )
                        query_end = datetime.now(timezone.utc)
                        
                        row = result.fetchone()
                        results.append({
                            'query_id': query_index,
                            'duration_ms': (query_end - query_start).total_seconds() * 1000,
                            'result': row._asdict() if row else None
                        })
                    
                    return {
                        'session_index': session_index,
                        'user_id': user_id,
                        'status': 'success',
                        'queries_executed': len(results),
                        'query_results': results
                    }
                    
            except Exception as e:
                return {
                    'session_index': session_index,
                    'user_id': user_id,
                    'status': 'failed',
                    'error': str(e)
                }
        
        # Execute concurrent sessions
        logger.info(f"Starting concurrent load test: {concurrent_sessions} sessions, {queries_per_session} queries each")
        
        tasks = [run_session_workload(i) for i in range(concurrent_sessions)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.now(timezone.utc)
        total_duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Analyze results
        successful_sessions = [r for r in results if isinstance(r, dict) and r.get('status') == 'success']
        failed_sessions = [r for r in results if isinstance(r, dict) and r.get('status') == 'failed']
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        # Get final metrics
        factory = await get_session_factory()
        pool_metrics = factory.get_pool_metrics()
        
        return {
            'timestamp': end_time.isoformat(),
            'load_test_config': {
                'concurrent_sessions': concurrent_sessions,
                'queries_per_session': queries_per_session,
                'total_expected_queries': concurrent_sessions * queries_per_session
            },
            'results': {
                'total_duration_ms': total_duration_ms,
                'successful_sessions': len(successful_sessions),
                'failed_sessions': len(failed_sessions),
                'exceptions': len(exceptions),
                'success_rate_percent': (len(successful_sessions) / concurrent_sessions) * 100,
                'total_queries_executed': sum(s.get('queries_executed', 0) for s in successful_sessions)
            },
            'pool_metrics': {
                'peak_concurrent_sessions': pool_metrics.peak_concurrent_sessions,
                'active_sessions_after_test': pool_metrics.active_sessions,
                'total_sessions_created': pool_metrics.total_sessions_created,
                'leaked_sessions': pool_metrics.leaked_sessions,
                'pool_exhaustion_events': pool_metrics.pool_exhaustion_events
            },
            'failures': failed_sessions[:3],  # Show first 3 failures for debugging
            'exceptions': [str(e) for e in exceptions[:3]]
        }
        
    except Exception as e:
        logger.error(f"Concurrent load test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Load test failed: {str(e)}")