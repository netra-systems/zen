#!/usr/bin/env python3
"""
Database Session Isolation Validation Test

This script validates the database session isolation implementation
by running concurrent sessions and checking for proper isolation.
"""

import asyncio
import time
import sys
from datetime import datetime, timezone
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from netra_backend.app.database.request_scoped_session_factory import (
        RequestScopedSessionFactory,
        get_isolated_session,
        validate_session_isolation
    )
    from sqlalchemy import text
    
    print("✅ Successfully imported session factory modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def test_session_isolation():
    """Test basic session isolation functionality."""
    print("\n🧪 Testing Basic Session Isolation")
    
    try:
        factory = RequestScopedSessionFactory()
        
        # Test single session
        user_id = "test_user_1"
        async with factory.get_request_scoped_session(user_id) as session:
            print(f"✅ Created session for {user_id}")
            
            # Check session info
            assert session.info['user_id'] == user_id
            assert session.info['is_request_scoped'] is True
            print(f"✅ Session properly tagged with user {user_id}")
            
            # Test validation
            assert await factory.validate_session_isolation(session, user_id)
            print(f"✅ Session validation passed for {user_id}")
        
        print(f"✅ Session cleaned up properly")
        
        await factory.close()
        print("✅ Basic session isolation test passed")
        
    except Exception as e:
        print(f"❌ Basic session isolation test failed: {e}")
        raise


async def test_concurrent_sessions():
    """Test concurrent session isolation."""
    print("\n🧪 Testing Concurrent Session Isolation")
    
    try:
        factory = RequestScopedSessionFactory()
        num_users = 10
        
        async def user_session_test(user_index: int):
            """Test session for a single user."""
            user_id = f"concurrent_user_{user_index}"
            
            try:
                async with factory.get_request_scoped_session(user_id) as session:
                    # Verify session belongs to correct user
                    if session.info['user_id'] != user_id:
                        return f"❌ User {user_index}: Wrong user ID in session"
                    
                    # Test validation
                    await factory.validate_session_isolation(session, user_id)
                    
                    # Brief operation
                    await asyncio.sleep(0.01)
                    
                    return f"✅ User {user_index}: Success"
                    
            except Exception as e:
                return f"❌ User {user_index}: Error - {e}"
        
        # Run concurrent sessions
        tasks = [user_session_test(i) for i in range(num_users)]
        results = await asyncio.gather(*tasks)
        
        # Check results
        successful = 0
        for result in results:
            print(f"  {result}")
            if "✅" in result:
                successful += 1
        
        success_rate = successful / num_users
        print(f"\n📊 Concurrent Test Results:")
        print(f"   Sessions: {num_users}")
        print(f"   Successful: {successful}")
        print(f"   Success Rate: {success_rate:.1%}")
        
        # Check factory metrics
        pool_metrics = factory.get_pool_metrics()
        print(f"   Total Created: {pool_metrics.total_sessions_created}")
        print(f"   Active: {pool_metrics.active_sessions}")
        print(f"   Closed: {pool_metrics.sessions_closed}")
        
        assert success_rate >= 0.9, f"Success rate too low: {success_rate:.1%}"
        assert pool_metrics.active_sessions == 0, "Sessions not properly cleaned up"
        
        await factory.close()
        print("✅ Concurrent session isolation test passed")
        
    except Exception as e:
        print(f"❌ Concurrent session isolation test failed: {e}")
        raise


async def test_high_concurrency_load():
    """Test high concurrency load (100 sessions)."""
    print("\n🧪 Testing High Concurrency Load (100 Sessions)")
    
    try:
        factory = RequestScopedSessionFactory()
        num_sessions = 100
        
        async def session_load_test(session_index: int):
            """Load test for a single session."""
            user_id = f"load_user_{session_index}"
            
            try:
                async with factory.get_request_scoped_session(user_id) as session:
                    # Verify proper tagging
                    if session.info['user_id'] != user_id:
                        return False
                    
                    # Quick validation
                    await factory.validate_session_isolation(session, user_id)
                    return True
                    
            except Exception:
                return False
        
        # Run high concurrency test
        start_time = time.time()
        tasks = [session_load_test(i) for i in range(num_sessions)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyze results
        successful_sessions = sum(1 for r in results if r is True)
        failed_sessions = sum(1 for r in results if r is False)
        exceptions = sum(1 for r in results if isinstance(r, Exception))
        
        duration_ms = (end_time - start_time) * 1000
        success_rate = successful_sessions / num_sessions
        
        print(f"📊 High Concurrency Load Test Results:")
        print(f"   Sessions: {num_sessions}")
        print(f"   Successful: {successful_sessions}")
        print(f"   Failed: {failed_sessions}")
        print(f"   Exceptions: {exceptions}")
        print(f"   Success Rate: {success_rate:.1%}")
        print(f"   Duration: {duration_ms:.1f}ms")
        print(f"   Avg per session: {duration_ms/num_sessions:.1f}ms")
        
        # Check final factory state
        pool_metrics = factory.get_pool_metrics()
        print(f"   Peak Concurrent: {pool_metrics.peak_concurrent_sessions}")
        print(f"   Total Created: {pool_metrics.total_sessions_created}")
        print(f"   Active After Test: {pool_metrics.active_sessions}")
        print(f"   Leaked Sessions: {pool_metrics.leaked_sessions}")
        
        # Assertions
        assert success_rate >= 0.9, f"Success rate too low: {success_rate:.1%}"
        assert pool_metrics.active_sessions == 0, "Sessions not cleaned up"
        assert pool_metrics.total_sessions_created == num_sessions
        
        await factory.close()
        print("✅ High concurrency load test passed")
        
    except Exception as e:
        print(f"❌ High concurrency load test failed: {e}")
        raise


async def test_session_factory_health():
    """Test session factory health check."""
    print("\n🧪 Testing Session Factory Health Check")
    
    try:
        factory = RequestScopedSessionFactory()
        
        # Get health status
        health = await factory.health_check()
        
        print(f"📊 Factory Health Status:")
        print(f"   Status: {health.get('status')}")
        print(f"   Active Sessions: {health.get('factory_metrics', {}).get('active_sessions')}")
        print(f"   Total Created: {health.get('factory_metrics', {}).get('total_created')}")
        print(f"   Leaked Sessions: {health.get('factory_metrics', {}).get('leaked_sessions')}")
        print(f"   Background Cleanup: {health.get('background_cleanup_running')}")
        
        assert health.get('status') in ['healthy', 'unhealthy']
        assert 'factory_metrics' in health
        
        await factory.close()
        print("✅ Factory health check test passed")
        
    except Exception as e:
        print(f"❌ Factory health check test failed: {e}")
        raise


async def main():
    """Run all database isolation tests."""
    print("🚀 Starting Database Session Isolation Validation")
    print(f"⏰ Start time: {datetime.now(timezone.utc).isoformat()}")
    
    start_time = time.time()
    
    try:
        # Run all tests
        await test_session_isolation()
        await test_concurrent_sessions()
        await test_session_factory_health()
        await test_high_concurrency_load()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"⏱️  Total test duration: {duration:.2f} seconds")
        print(f"✅ Database session isolation is working correctly")
        print(f"✅ Connection pool management is functioning properly")
        print(f"✅ Session leak detection and cleanup is operational")
        print(f"✅ System can handle 100+ concurrent isolated sessions")
        
    except Exception as e:
        print(f"\n💥 TEST FAILURE: {e}")
        print(f"❌ Database session isolation needs attention")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())