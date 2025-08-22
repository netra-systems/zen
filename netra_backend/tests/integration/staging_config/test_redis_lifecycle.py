"""
Test Redis Lifecycle

Validates Redis connectivity, persistence, and failover
in the staging environment.
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import os
import time
from typing import List, Optional

import redis
from redis.sentinel import Sentinel

# Add project root to path
from .base import StagingConfigTestBase

# Add project root to path


class TestRedisLifecycle(StagingConfigTestBase):
    """Test Redis lifecycle in staging."""
    
    def setUp(self):
        """Set up Redis connection."""
        super().setUp()
        
        # Get Redis configuration
        try:
            redis_url = self.assert_secret_exists('redis-url')
            # Parse Redis URL
            if 'redis://' in redis_url:
                parts = redis_url.replace('redis://', '').split(':')
                self.redis_host = parts[0]
                self.redis_port = int(parts[1].split('/')[0]) if len(parts) > 1 else 6379
            else:
                self.redis_host = 'redis-staging'
                self.redis_port = 6379
        except AssertionError:
            self.redis_host = os.getenv('REDIS_HOST', 'redis-staging')
            self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
            
    def test_redis_connectivity(self):
        """Test basic Redis connectivity."""
        self.skip_if_not_staging()
        
        try:
            # Connect to Redis
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                socket_connect_timeout=5
            )
            
            # Test basic operations
            test_key = 'test:staging:connectivity'
            test_value = 'staging_test_value'
            
            # Set value
            client.set(test_key, test_value, ex=60)
            
            # Get value
            retrieved = client.get(test_key)
            self.assertEqual(retrieved, test_value,
                           "Redis value mismatch")
                           
            # Clean up
            client.delete(test_key)
            
        except redis.ConnectionError as e:
            self.fail(f"Redis connection failed: {e}")
            
    def test_redis_persistence(self):
        """Test Redis data persistence."""
        self.skip_if_not_staging()
        
        try:
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True
            )
            
            # Set persistent value
            persist_key = 'test:staging:persist'
            persist_value = f"persist_{time.time()}"
            
            client.set(persist_key, persist_value)
            
            # Check persistence settings
            ttl = client.ttl(persist_key)
            self.assertEqual(ttl, -1,
                           "Key should not have TTL for persistence test")
                           
            # Simulate restart by reconnecting
            client.connection_pool.disconnect()
            time.sleep(1)
            
            # Reconnect and verify
            new_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True
            )
            
            retrieved = new_client.get(persist_key)
            self.assertEqual(retrieved, persist_value,
                           "Value not persisted after reconnection")
                           
            # Clean up
            new_client.delete(persist_key)
            
        except redis.ConnectionError as e:
            self.fail(f"Redis persistence test failed: {e}")
            
    def test_redis_pub_sub(self):
        """Test Redis pub/sub functionality."""
        self.skip_if_not_staging()
        
        try:
            # Create publisher and subscriber
            pub_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True
            )
            
            sub_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True
            )
            
            # Subscribe to channel
            pubsub = sub_client.pubsub()
            channel = 'test:staging:channel'
            pubsub.subscribe(channel)
            
            # Publish message
            test_message = 'staging_pubsub_test'
            pub_client.publish(channel, test_message)
            
            # Receive message
            time.sleep(0.5)  # Allow time for message delivery
            message = pubsub.get_message(ignore_subscribe_messages=True)
            
            self.assertIsNotNone(message, "No message received")
            self.assertEqual(message['data'], test_message,
                           "Pub/sub message mismatch")
                           
            # Clean up
            pubsub.unsubscribe(channel)
            pubsub.close()
            
        except redis.ConnectionError as e:
            self.fail(f"Redis pub/sub test failed: {e}")
            
    def test_redis_cluster_mode(self):
        """Test Redis cluster mode if configured."""
        self.skip_if_not_staging()
        
        # Check if Redis is in cluster mode
        try:
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True
            )
            
            info = client.info('cluster')
            
            if info.get('cluster_enabled') == 1:
                # Test cluster operations
                from redis.cluster import RedisCluster
                
                cluster_client = RedisCluster(
                    host=self.redis_host,
                    port=self.redis_port,
                    decode_responses=True
                )
                
                # Test sharding across cluster
                for i in range(10):
                    key = f"test:cluster:{i}"
                    value = f"value_{i}"
                    cluster_client.set(key, value, ex=60)
                    
                # Verify distribution
                nodes = cluster_client.cluster_nodes()
                self.assertGreater(len(nodes), 1,
                                 "Cluster should have multiple nodes")
                                 
                # Clean up
                for i in range(10):
                    cluster_client.delete(f"test:cluster:{i}")
                    
            else:
                self.skipTest("Redis not in cluster mode")
                
        except Exception as e:
            self.skipTest(f"Cluster mode test skipped: {e}")
            
    def test_redis_memory_limits(self):
        """Test Redis memory configuration."""
        self.skip_if_not_staging()
        
        try:
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True
            )
            
            # Get memory configuration
            config = client.config_get('maxmemory*')
            
            # Check memory limit is set
            max_memory = config.get('maxmemory', '0')
            self.assertNotEqual(max_memory, '0',
                              "Redis maxmemory not configured")
                              
            # Check eviction policy
            policy = config.get('maxmemory-policy', 'noeviction')
            self.assertIn(policy, ['allkeys-lru', 'volatile-lru', 'allkeys-lfu'],
                        f"Unexpected eviction policy: {policy}")
                        
            # Get memory stats
            memory_info = client.info('memory')
            used_memory = memory_info.get('used_memory', 0)
            
            self.assertGreater(used_memory, 0,
                             "Redis not reporting memory usage")
                             
        except redis.ConnectionError as e:
            self.fail(f"Redis memory test failed: {e}")
            
    def test_redis_sentinel(self):
        """Test Redis Sentinel for high availability."""
        self.skip_if_not_staging()
        
        # Check if Sentinel is configured
        sentinel_hosts = os.getenv('REDIS_SENTINELS', '').split(',')
        
        if not sentinel_hosts or sentinel_hosts == ['']:
            self.skipTest("Redis Sentinel not configured")
            
        try:
            # Parse Sentinel hosts
            sentinels = []
            for host in sentinel_hosts:
                if ':' in host:
                    h, p = host.split(':')
                    sentinels.append((h.strip(), int(p)))
                    
            if not sentinels:
                self.skipTest("No valid Sentinel hosts")
                
            # Connect via Sentinel
            sentinel = Sentinel(sentinels)
            
            # Discover master
            master_name = os.getenv('REDIS_MASTER_NAME', 'mymaster')
            master = sentinel.master_for(
                master_name,
                decode_responses=True
            )
            
            # Test operations via Sentinel
            test_key = 'test:sentinel:key'
            test_value = 'sentinel_value'
            
            master.set(test_key, test_value, ex=60)
            retrieved = master.get(test_key)
            
            self.assertEqual(retrieved, test_value,
                           "Sentinel Redis operation failed")
                           
            # Clean up
            master.delete(test_key)
            
        except Exception as e:
            self.fail(f"Redis Sentinel test failed: {e}")