#!/usr/bin/env python3
"""Performance Profiler for Request Isolation Architecture

This script profiles the performance of the isolation architecture to identify
bottlenecks and measure latencies across different components.

Business Value Justification:
- Segment: Platform Performance & Scalability
- Business Goal: Ensure chat responsiveness for user satisfaction
- Value Impact: <20ms total request overhead enables real-time chat
- Strategic Impact: 100+ concurrent users without degradation

Performance Targets:
- Agent instance creation: <10ms
- WebSocket message dispatch: <5ms  
- Database session acquisition: <2ms
- Total request overhead: <20ms

Usage:
    python scripts/performance_profiler.py --all
    python scripts/performance_profiler.py --factory
    python scripts/performance_profiler.py --websocket
    python scripts/performance_profiler.py --database
"""

import asyncio
import cProfile
import pstats
import time
import sys
import os
import argparse
from io import StringIO
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone
import statistics
import json
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import IsolatedEnvironment

# Configure logging
logger = central_logger.get_logger(__name__)
env = IsolatedEnvironment("backend")


class PerformanceProfiler:
    """Comprehensive performance profiler for isolation architecture."""
    
    def __init__(self):
        """Initialize profiler with metrics collection."""
        self.metrics: Dict[str, List[float]] = {
            'factory_create_context': [],
            'factory_create_agent': [],
            'factory_cleanup': [],
            'websocket_handler_init': [],
            'websocket_send_event': [],
            'websocket_authenticate': [],
            'database_session_create': [],
            'database_session_close': [],
            'database_query_simple': [],
            'total_request_time': []
        }
        
        self.test_iterations = 100
        self.concurrent_users = 10
        self.results: Dict[str, Any] = {}
    
    async def profile_factory_performance(self) -> Dict[str, Any]:
        """Profile AgentInstanceFactory performance."""
        logger.info("Profiling AgentInstanceFactory performance...")
        
        from netra_backend.app.agents.supervisor.agent_instance_factory import (
            AgentInstanceFactory,
            UserExecutionContext
        )
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.websocket_core.manager import WebSocketManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        
        # Initialize factory
        factory = AgentInstanceFactory()
        websocket_manager = WebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        agent_registry = AgentRegistry()
        await agent_registry.initialize()
        
        factory.configure(
            agent_registry=agent_registry,
            websocket_bridge=websocket_bridge,
            websocket_manager=websocket_manager
        )
        
        # Warm up
        for _ in range(5):
            context = await factory.create_user_execution_context(
                user_id="warmup_user",
                thread_id="warmup_thread",
                run_id=f"warmup_{uuid.uuid4().hex[:8]}"
            )
            await factory.cleanup_user_context(context)
        
        # Profile context creation
        context_times = []
        for i in range(self.test_iterations):
            user_id = f"user_{i % 10}"  # Simulate 10 different users
            
            start_time = time.perf_counter()
            context = await factory.create_user_execution_context(
                user_id=user_id,
                thread_id=f"thread_{i}",
                run_id=f"run_{uuid.uuid4().hex[:8]}"
            )
            creation_time = (time.perf_counter() - start_time) * 1000
            context_times.append(creation_time)
            
            # Profile agent creation
            agent_start = time.perf_counter()
            try:
                agent = await factory.create_agent_instance(
                    agent_name="triage",
                    user_context=context
                )
                agent_time = (time.perf_counter() - agent_start) * 1000
                self.metrics['factory_create_agent'].append(agent_time)
            except Exception as e:
                logger.warning(f"Agent creation failed: {e}")
                self.metrics['factory_create_agent'].append(0)
            
            # Profile cleanup
            cleanup_start = time.perf_counter()
            await factory.cleanup_user_context(context)
            cleanup_time = (time.perf_counter() - cleanup_start) * 1000
            self.metrics['factory_cleanup'].append(cleanup_time)
        
        self.metrics['factory_create_context'] = context_times
        
        # Calculate statistics
        stats = {
            'context_creation': {
                'mean_ms': statistics.mean(context_times),
                'median_ms': statistics.median(context_times),
                'p95_ms': statistics.quantiles(context_times, n=20)[18] if len(context_times) > 20 else max(context_times),
                'min_ms': min(context_times),
                'max_ms': max(context_times),
                'target_ms': 10,
                'pass': statistics.mean(context_times) < 10
            }
        }
        
        if self.metrics['factory_create_agent']:
            agent_times = [t for t in self.metrics['factory_create_agent'] if t > 0]
            if agent_times:
                stats['agent_creation'] = {
                    'mean_ms': statistics.mean(agent_times),
                    'median_ms': statistics.median(agent_times),
                    'p95_ms': statistics.quantiles(agent_times, n=20)[18] if len(agent_times) > 20 else max(agent_times),
                    'min_ms': min(agent_times),
                    'max_ms': max(agent_times),
                    'target_ms': 10,
                    'pass': statistics.mean(agent_times) < 10
                }
        
        if self.metrics['factory_cleanup']:
            stats['context_cleanup'] = {
                'mean_ms': statistics.mean(self.metrics['factory_cleanup']),
                'median_ms': statistics.median(self.metrics['factory_cleanup']),
                'p95_ms': statistics.quantiles(self.metrics['factory_cleanup'], n=20)[18] if len(self.metrics['factory_cleanup']) > 20 else max(self.metrics['factory_cleanup']),
                'min_ms': min(self.metrics['factory_cleanup']),
                'max_ms': max(self.metrics['factory_cleanup']),
                'target_ms': 5,
                'pass': statistics.mean(self.metrics['factory_cleanup']) < 5
            }
        
        # Get factory metrics
        factory_metrics = factory.get_factory_metrics()
        stats['factory_metrics'] = factory_metrics
        
        return stats
    
    async def profile_websocket_performance(self) -> Dict[str, Any]:
        """Profile WebSocket connection handler performance."""
        logger.info("Profiling WebSocket connection handler performance...")
        
        from netra_backend.app.websocket.connection_handler import ConnectionHandler
        from fastapi import WebSocket
        from unittest.mock import Mock, AsyncMock
        
        # Create mock WebSocket
        mock_ws = Mock(spec=WebSocket)
        mock_ws.send_json = AsyncMock()
        mock_ws.client_state = "connected"
        
        handler_times = []
        auth_times = []
        send_times = []
        
        for i in range(self.test_iterations):
            user_id = f"user_{i % 10}"
            
            # Profile handler initialization
            start_time = time.perf_counter()
            handler = ConnectionHandler(mock_ws, user_id)
            init_time = (time.perf_counter() - start_time) * 1000
            handler_times.append(init_time)
            
            # Profile authentication
            auth_start = time.perf_counter()
            await handler.authenticate(thread_id=f"thread_{i}")
            auth_time = (time.perf_counter() - auth_start) * 1000
            auth_times.append(auth_time)
            
            # Profile event sending (simulate 10 events)
            for j in range(10):
                event = {
                    'type': 'agent_started',
                    'agent_name': 'test_agent',
                    'user_id': user_id,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                send_start = time.perf_counter()
                await handler.send_event(event)
                send_time = (time.perf_counter() - send_start) * 1000
                send_times.append(send_time)
            
            # Cleanup
            await handler.cleanup()
        
        self.metrics['websocket_handler_init'] = handler_times
        self.metrics['websocket_authenticate'] = auth_times
        self.metrics['websocket_send_event'] = send_times
        
        # Calculate statistics
        stats = {
            'handler_init': {
                'mean_ms': statistics.mean(handler_times),
                'median_ms': statistics.median(handler_times),
                'p95_ms': statistics.quantiles(handler_times, n=20)[18] if len(handler_times) > 20 else max(handler_times),
                'min_ms': min(handler_times),
                'max_ms': max(handler_times),
                'target_ms': 1,
                'pass': statistics.mean(handler_times) < 1
            },
            'authentication': {
                'mean_ms': statistics.mean(auth_times),
                'median_ms': statistics.median(auth_times),
                'p95_ms': statistics.quantiles(auth_times, n=20)[18] if len(auth_times) > 20 else max(auth_times),
                'min_ms': min(auth_times),
                'max_ms': max(auth_times),
                'target_ms': 2,
                'pass': statistics.mean(auth_times) < 2
            },
            'event_dispatch': {
                'mean_ms': statistics.mean(send_times),
                'median_ms': statistics.median(send_times),
                'p95_ms': statistics.quantiles(send_times, n=20)[18] if len(send_times) > 20 else max(send_times),
                'min_ms': min(send_times),
                'max_ms': max(send_times),
                'target_ms': 5,
                'pass': statistics.mean(send_times) < 5
            }
        }
        
        # Get handler statistics
        handler_stats = ConnectionHandler.get_global_stats()
        stats['handler_stats'] = handler_stats
        
        return stats
    
    async def profile_database_performance(self) -> Dict[str, Any]:
        """Profile database session performance."""
        logger.info("Profiling database session performance...")
        
        from netra_backend.app.database.request_scoped_session_factory import (
            get_isolated_session,
            get_session_factory
        )
        from sqlalchemy import text
        
        session_times = []
        query_times = []
        close_times = []
        
        for i in range(self.test_iterations):
            user_id = f"user_{i % 10}"
            request_id = f"req_{uuid.uuid4().hex[:8]}"
            
            # Profile session creation and query
            start_time = time.perf_counter()
            
            async with get_isolated_session(user_id, request_id) as session:
                creation_time = (time.perf_counter() - start_time) * 1000
                session_times.append(creation_time)
                
                # Profile simple query
                query_start = time.perf_counter()
                result = await session.execute(text("SELECT 1"))
                _ = result.scalar()
                query_time = (time.perf_counter() - query_start) * 1000
                query_times.append(query_time)
            
            # Session close time (implicit in context manager)
            close_time = (time.perf_counter() - start_time - creation_time/1000 - query_time/1000) * 1000
            close_times.append(max(0, close_time))
        
        self.metrics['database_session_create'] = session_times
        self.metrics['database_query_simple'] = query_times
        self.metrics['database_session_close'] = close_times
        
        # Calculate statistics
        stats = {
            'session_acquisition': {
                'mean_ms': statistics.mean(session_times),
                'median_ms': statistics.median(session_times),
                'p95_ms': statistics.quantiles(session_times, n=20)[18] if len(session_times) > 20 else max(session_times),
                'min_ms': min(session_times),
                'max_ms': max(session_times),
                'target_ms': 2,
                'pass': statistics.mean(session_times) < 2
            },
            'simple_query': {
                'mean_ms': statistics.mean(query_times),
                'median_ms': statistics.median(query_times),
                'p95_ms': statistics.quantiles(query_times, n=20)[18] if len(query_times) > 20 else max(query_times),
                'min_ms': min(query_times),
                'max_ms': max(query_times),
                'target_ms': 1,
                'pass': statistics.mean(query_times) < 1
            },
            'session_cleanup': {
                'mean_ms': statistics.mean(close_times) if close_times else 0,
                'median_ms': statistics.median(close_times) if close_times else 0,
                'p95_ms': statistics.quantiles(close_times, n=20)[18] if len(close_times) > 20 else max(close_times) if close_times else 0,
                'min_ms': min(close_times) if close_times else 0,
                'max_ms': max(close_times) if close_times else 0,
                'target_ms': 1,
                'pass': statistics.mean(close_times) < 1 if close_times else True
            }
        }
        
        # Get factory metrics
        factory = await get_session_factory()
        pool_metrics = factory.get_pool_metrics()
        stats['pool_metrics'] = {
            'active_sessions': pool_metrics.active_sessions,
            'total_created': pool_metrics.total_sessions_created,
            'sessions_closed': pool_metrics.sessions_closed,
            'leaked_sessions': pool_metrics.leaked_sessions,
            'avg_lifetime_ms': pool_metrics.avg_session_lifetime_ms,
            'peak_concurrent': pool_metrics.peak_concurrent_sessions
        }
        
        return stats
    
    async def profile_end_to_end_request(self) -> Dict[str, Any]:
        """Profile complete end-to-end request with isolation."""
        logger.info("Profiling end-to-end request performance...")
        
        from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.websocket_core.manager import WebSocketManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.database.request_scoped_session_factory import get_isolated_session
        
        # Initialize components
        factory = AgentInstanceFactory()
        websocket_manager = WebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        agent_registry = AgentRegistry()
        await agent_registry.initialize()
        
        factory.configure(
            agent_registry=agent_registry,
            websocket_bridge=websocket_bridge,
            websocket_manager=websocket_manager
        )
        
        request_times = []
        
        for i in range(self.test_iterations):
            user_id = f"user_{i % 10}"
            request_id = f"req_{uuid.uuid4().hex[:8]}"
            thread_id = f"thread_{i}"
            run_id = f"run_{uuid.uuid4().hex[:8]}"
            
            start_time = time.perf_counter()
            
            try:
                # 1. Get database session
                async with get_isolated_session(user_id, request_id, thread_id) as session:
                    # 2. Create user execution context
                    context = await factory.create_user_execution_context(
                        user_id=user_id,
                        thread_id=thread_id,
                        run_id=run_id,
                        db_session=session
                    )
                    
                    # 3. Create agent instance
                    try:
                        agent = await factory.create_agent_instance(
                            agent_name="triage",
                            user_context=context
                        )
                    except Exception as e:
                        logger.debug(f"Agent creation failed (expected): {e}")
                    
                    # 4. Simulate some work
                    await asyncio.sleep(0.001)  # 1ms simulated work
                    
                    # 5. Cleanup
                    await factory.cleanup_user_context(context)
                
                total_time = (time.perf_counter() - start_time) * 1000
                request_times.append(total_time)
                
            except Exception as e:
                logger.error(f"End-to-end request failed: {e}")
                request_times.append(0)
        
        self.metrics['total_request_time'] = [t for t in request_times if t > 0]
        
        # Calculate statistics
        valid_times = [t for t in request_times if t > 0]
        if valid_times:
            stats = {
                'total_request': {
                    'mean_ms': statistics.mean(valid_times),
                    'median_ms': statistics.median(valid_times),
                    'p95_ms': statistics.quantiles(valid_times, n=20)[18] if len(valid_times) > 20 else max(valid_times),
                    'min_ms': min(valid_times),
                    'max_ms': max(valid_times),
                    'target_ms': 20,
                    'pass': statistics.mean(valid_times) < 20,
                    'success_rate': len(valid_times) / len(request_times)
                }
            }
        else:
            stats = {'error': 'No successful requests'}
        
        return stats
    
    async def profile_concurrent_load(self) -> Dict[str, Any]:
        """Profile performance under concurrent load."""
        logger.info(f"Profiling concurrent load with {self.concurrent_users} users...")
        
        from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.websocket_core.manager import WebSocketManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        
        # Initialize components
        factory = AgentInstanceFactory()
        websocket_manager = WebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        agent_registry = AgentRegistry()
        await agent_registry.initialize()
        
        factory.configure(
            agent_registry=agent_registry,
            websocket_bridge=websocket_bridge,
            websocket_manager=websocket_manager
        )
        
        async def simulate_user_request(user_id: str, request_count: int) -> List[float]:
            """Simulate requests from a single user."""
            times = []
            
            for i in range(request_count):
                request_id = f"req_{uuid.uuid4().hex[:8]}"
                thread_id = f"thread_{user_id}_{i}"
                run_id = f"run_{uuid.uuid4().hex[:8]}"
                
                start_time = time.perf_counter()
                
                try:
                    context = await factory.create_user_execution_context(
                        user_id=user_id,
                        thread_id=thread_id,
                        run_id=run_id
                    )
                    
                    # Simulate some work
                    await asyncio.sleep(0.01)  # 10ms simulated work
                    
                    await factory.cleanup_user_context(context)
                    
                    total_time = (time.perf_counter() - start_time) * 1000
                    times.append(total_time)
                    
                except Exception as e:
                    logger.debug(f"User request failed: {e}")
                    times.append(0)
            
            return times
        
        # Run concurrent users
        start_time = time.perf_counter()
        
        tasks = [
            simulate_user_request(f"user_{i}", 10)
            for i in range(self.concurrent_users)
        ]
        
        results = await asyncio.gather(*tasks)
        
        total_duration = (time.perf_counter() - start_time) * 1000
        
        # Flatten results
        all_times = []
        for user_times in results:
            all_times.extend([t for t in user_times if t > 0])
        
        if all_times:
            stats = {
                'concurrent_load': {
                    'concurrent_users': self.concurrent_users,
                    'requests_per_user': 10,
                    'total_requests': len(all_times),
                    'total_duration_ms': total_duration,
                    'throughput_rps': len(all_times) / (total_duration / 1000),
                    'mean_latency_ms': statistics.mean(all_times),
                    'median_latency_ms': statistics.median(all_times),
                    'p95_latency_ms': statistics.quantiles(all_times, n=20)[18] if len(all_times) > 20 else max(all_times),
                    'min_latency_ms': min(all_times),
                    'max_latency_ms': max(all_times),
                    'target_ms': 50,
                    'pass': statistics.mean(all_times) < 50
                }
            }
        else:
            stats = {'error': 'No successful concurrent requests'}
        
        return stats
    
    def print_results(self, results: Dict[str, Any]):
        """Print formatted performance results."""
        print("\n" + "=" * 80)
        print("PERFORMANCE PROFILING RESULTS")
        print("=" * 80)
        
        for category, stats in results.items():
            print(f"\n{category.upper().replace('_', ' ')}:")
            print("-" * 40)
            
            if isinstance(stats, dict):
                if 'error' in stats:
                    print(f"  ERROR: {stats['error']}")
                else:
                    for metric, values in stats.items():
                        if isinstance(values, dict) and 'mean_ms' in values:
                            status = "PASS" if values.get('pass', False) else "FAIL"
                            target = values.get('target_ms', 'N/A')
                            mean = values.get('mean_ms', 0)
                            p95 = values.get('p95_ms', 0)
                            
                            print(f"  {metric}:")
                            print(f"    Mean: {mean:.2f}ms (Target: {target}ms) [{status}]")
                            print(f"    P95:  {p95:.2f}ms")
                            print(f"    Min:  {values.get('min_ms', 0):.2f}ms")
                            print(f"    Max:  {values.get('max_ms', 0):.2f}ms")
                        elif metric in ['throughput_rps', 'success_rate']:
                            print(f"  {metric}: {values:.2f}")
                        elif not isinstance(values, dict):
                            print(f"  {metric}: {values}")
        
        # Overall summary
        print("\n" + "=" * 80)
        print("OVERALL PERFORMANCE SUMMARY")
        print("=" * 80)
        
        all_pass = True
        for category, stats in results.items():
            if isinstance(stats, dict):
                for metric, values in stats.items():
                    if isinstance(values, dict) and 'pass' in values:
                        if not values['pass']:
                            all_pass = False
                            target = values.get('target_ms', 'N/A')
                            mean = values.get('mean_ms', 0)
                            print(f"  FAIL: {category}.{metric} - {mean:.2f}ms > {target}ms target")
        
        if all_pass:
            print("  ALL PERFORMANCE TARGETS MET!")
        else:
            print("\n  Some performance targets not met. See failures above.")
        
        print("\n" + "=" * 80)
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save results to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_profile_{timestamp}.json"
        
        filepath = os.path.join("reports", filename)
        os.makedirs("reports", exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {filepath}")
        return filepath


async def main():
    """Main entry point for performance profiler."""
    parser = argparse.ArgumentParser(description='Profile isolation architecture performance')
    parser.add_argument('--all', action='store_true', help='Run all profiles')
    parser.add_argument('--factory', action='store_true', help='Profile AgentInstanceFactory')
    parser.add_argument('--websocket', action='store_true', help='Profile WebSocket handlers')
    parser.add_argument('--database', action='store_true', help='Profile database sessions')
    parser.add_argument('--e2e', action='store_true', help='Profile end-to-end requests')
    parser.add_argument('--concurrent', action='store_true', help='Profile concurrent load')
    parser.add_argument('--iterations', type=int, default=100, help='Number of test iterations')
    parser.add_argument('--users', type=int, default=10, help='Number of concurrent users')
    parser.add_argument('--save', action='store_true', help='Save results to file')
    
    args = parser.parse_args()
    
    # Default to all if no specific profile selected
    if not any([args.factory, args.websocket, args.database, args.e2e, args.concurrent]):
        args.all = True
    
    profiler = PerformanceProfiler()
    profiler.test_iterations = args.iterations
    profiler.concurrent_users = args.users
    
    results = {}
    
    try:
        if args.all or args.factory:
            results['factory'] = await profiler.profile_factory_performance()
        
        if args.all or args.websocket:
            results['websocket'] = await profiler.profile_websocket_performance()
        
        if args.all or args.database:
            results['database'] = await profiler.profile_database_performance()
        
        if args.all or args.e2e:
            results['end_to_end'] = await profiler.profile_end_to_end_request()
        
        if args.all or args.concurrent:
            results['concurrent'] = await profiler.profile_concurrent_load()
        
        # Print results
        profiler.print_results(results)
        
        # Save results if requested
        if args.save:
            filepath = profiler.save_results(results)
            print(f"\nResults saved to: {filepath}")
        
    except Exception as e:
        logger.error(f"Profiling failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())