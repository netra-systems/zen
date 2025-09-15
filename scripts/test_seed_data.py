from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python3
"""
Test Data Seeder for Real Services
Seeds test databases with realistic fixture data for comprehensive testing.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

import asyncpg
import redis.asyncio as redis
from clickhouse_connect import get_client as get_clickhouse_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDataSeeder:
    """Seeds test data into real databases."""
    
    def __init__(self):
        self.postgres_url = self._build_postgres_url()
        self.redis_url = self._build_redis_url()
        self.clickhouse_config = self._build_clickhouse_config()
        
    def _build_postgres_url(self) -> str:
        """Build PostgreSQL connection URL from environment."""
        host = get_env().get("POSTGRES_HOST", "localhost")
        port = get_env().get("POSTGRES_PORT", "5432")
        user = get_env().get("POSTGRES_USER", "test_user")
        password = get_env().get("POSTGRES_PASSWORD", "test_pass")
        db = get_env().get("POSTGRES_DB", "netra_test")
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    def _build_redis_url(self) -> str:
        """Build Redis connection URL from environment."""
        host = get_env().get("REDIS_HOST", "localhost")
        port = get_env().get("REDIS_PORT", "6379")
        return f"redis://{host}:{port}/0"
    
    def _build_clickhouse_config(self) -> Dict:
        """Build ClickHouse connection config from environment."""
        return {
            "host": get_env().get("CLICKHOUSE_HOST", "localhost"),
            "port": int(get_env().get("CLICKHOUSE_PORT", "8123")),
            "user": get_env().get("CLICKHOUSE_USER", "test_user"),
            "password": get_env().get("CLICKHOUSE_PASSWORD", "test_pass"),
            "database": get_env().get("CLICKHOUSE_DB", "netra_test_analytics")
        }
    
    async def wait_for_services(self) -> None:
        """Wait for all services to be ready."""
        logger.info("Waiting for services to be ready...")
        
        # Wait for PostgreSQL
        max_retries = 30
        for attempt in range(max_retries):
            try:
                conn = await asyncpg.connect(self.postgres_url, timeout=5.0)
                await conn.fetchval("SELECT 1")
                await conn.close()
                logger.info("PostgreSQL is ready")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"PostgreSQL not ready after {max_retries} attempts: {e}")
                    sys.exit(1)
                logger.info(f"Waiting for PostgreSQL (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(2.0)
        
        # Wait for Redis
        for attempt in range(max_retries):
            try:
                client = redis.Redis.from_url(self.redis_url)
                await client.ping()
                await client.aclose()
                logger.info("Redis is ready")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Redis not ready after {max_retries} attempts: {e}")
                    sys.exit(1)
                logger.info(f"Waiting for Redis (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(2.0)
        
        # Wait for ClickHouse
        for attempt in range(max_retries):
            try:
                client = ClickHouseClient(**self.clickhouse_config, connect_timeout=5)
                client.execute("SELECT 1")
                client.disconnect()
                logger.info("ClickHouse is ready")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"ClickHouse not ready after {max_retries} attempts: {e}")
                    sys.exit(1)
                logger.info(f"Waiting for ClickHouse (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(2.0)
    
    async def seed_postgres_data(self) -> None:
        """Seed PostgreSQL with test fixture data."""
        logger.info("Seeding PostgreSQL test data...")
        
        conn = await asyncpg.connect(self.postgres_url)
        try:
            # Create test users
            test_users = [
                {
                    'email': 'admin@netra.local',
                    'name': 'Admin User',
                    'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdCmUiGD.9K.9qS',
                    'is_active': True,
                    'is_superuser': True
                },
                {
                    'email': 'user@netra.local', 
                    'name': 'Regular User',
                    'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdCmUiGD.9K.9qS',
                    'is_active': True,
                    'is_superuser': False
                },
                {
                    'email': 'inactive@netra.local',
                    'name': 'Inactive User', 
                    'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdCmUiGD.9K.9qS',
                    'is_active': False,
                    'is_superuser': False
                }
            ]
            
            user_ids = []
            for user in test_users:
                user_id = await conn.fetchval("""
                    INSERT INTO auth.users (email, name, password_hash, is_active, is_superuser)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (email) DO UPDATE SET
                        name = EXCLUDED.name,
                        password_hash = EXCLUDED.password_hash,
                        is_active = EXCLUDED.is_active,
                        is_superuser = EXCLUDED.is_superuser
                    RETURNING id
                """, user['email'], user['name'], user['password_hash'], 
                    user['is_active'], user['is_superuser'])
                user_ids.append(user_id)
                
            logger.info(f"Created {len(user_ids)} test users")
            
            # Create test organizations
            test_orgs = [
                {'name': 'Acme Corp', 'slug': 'acme-corp', 'plan': 'enterprise'},
                {'name': 'Beta Inc', 'slug': 'beta-inc', 'plan': 'pro'},
                {'name': 'Gamma LLC', 'slug': 'gamma-llc', 'plan': 'free'}
            ]
            
            org_ids = []
            for org in test_orgs:
                org_id = await conn.fetchval("""
                    INSERT INTO backend.organizations (name, slug, plan)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (slug) DO UPDATE SET
                        name = EXCLUDED.name,
                        plan = EXCLUDED.plan
                    RETURNING id
                """, org['name'], org['slug'], org['plan'])
                org_ids.append(org_id)
                
            logger.info(f"Created {len(org_ids)} test organizations")
            
            # Link users to organizations
            memberships = [
                (user_ids[0], org_ids[0], 'admin'),  # Admin user -> Acme Corp
                (user_ids[1], org_ids[0], 'member'), # Regular user -> Acme Corp
                (user_ids[1], org_ids[1], 'admin'),  # Regular user -> Beta Inc (admin)
                (user_ids[2], org_ids[2], 'member')  # Inactive user -> Gamma LLC
            ]
            
            for user_id, org_id, role in memberships:
                await conn.execute("""
                    INSERT INTO backend.organization_memberships (user_id, organization_id, role)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, organization_id) DO UPDATE SET
                        role = EXCLUDED.role
                """, user_id, org_id, role)
                
            logger.info(f"Created {len(memberships)} organization memberships")
            
            # Create test agents
            test_agents = [
                {
                    'organization_id': org_ids[0],
                    'name': 'Customer Support Agent',
                    'description': 'Helps with customer support inquiries',
                    'system_prompt': 'You are a helpful customer support assistant.',
                    'model_config': {'model': 'gpt-4', 'temperature': 0.3},
                    'created_by': user_ids[0]
                },
                {
                    'organization_id': org_ids[0], 
                    'name': 'Code Review Agent',
                    'description': 'Reviews code and provides feedback',
                    'system_prompt': 'You are an expert code reviewer.',
                    'model_config': {'model': 'gpt-4', 'temperature': 0.1},
                    'created_by': user_ids[1]
                },
                {
                    'organization_id': org_ids[1],
                    'name': 'Sales Assistant',
                    'description': 'Helps with sales and lead qualification',
                    'system_prompt': 'You are a sales assistant.',
                    'model_config': {'model': 'gpt-3.5-turbo', 'temperature': 0.7},
                    'created_by': user_ids[1]
                }
            ]
            
            agent_ids = []
            for agent in test_agents:
                agent_id = await conn.fetchval("""
                    INSERT INTO backend.agents (organization_id, name, description, system_prompt, model_config, created_by)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                """, agent['organization_id'], agent['name'], agent['description'],
                    agent['system_prompt'], agent['model_config'], agent['created_by'])
                agent_ids.append(agent_id)
                
            logger.info(f"Created {len(agent_ids)} test agents")
            
            logger.info("PostgreSQL test data seeding completed")
            
        finally:
            await conn.close()
    
    async def seed_redis_data(self) -> None:
        """Seed Redis with test fixture data.""" 
        logger.info("Seeding Redis test data...")
        
        client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        try:
            # Test session data
            test_sessions = {
                'session:test-session-1': json.dumps({
                    'user_id': 'test-user-1',
                    'email': 'admin@netra.local',
                    'expires_at': '2025-12-31T23:59:59Z'
                }),
                'session:test-session-2': json.dumps({
                    'user_id': 'test-user-2', 
                    'email': 'user@netra.local',
                    'expires_at': '2025-12-31T23:59:59Z'
                })
            }
            
            # Test rate limiting data
            test_rate_limits = {
                'rate_limit:api:test-user-1': '10',
                'rate_limit:api:test-user-2': '5',
                'rate_limit:websocket:test-session-1': '100'
            }
            
            # Test cache data
            test_cache = {
                'cache:user_profile:test-user-1': json.dumps({
                    'name': 'Admin User',
                    'email': 'admin@netra.local',
                    'cached_at': '2025-01-01T00:00:00Z'
                }),
                'cache:organization:acme-corp': json.dumps({
                    'id': 'test-org-1',
                    'name': 'Acme Corp',
                    'plan': 'enterprise',
                    'cached_at': '2025-01-01T00:00:00Z'
                })
            }
            
            # Set all test data
            all_data = {**test_sessions, **test_rate_limits, **test_cache}
            
            for key, value in all_data.items():
                await client.set(key, value, ex=3600)  # 1 hour expiry
                
            logger.info(f"Seeded {len(all_data)} Redis key-value pairs")
            
            # Set some keys with specific TTLs
            await client.set('temp:test-key-1', 'temporary data', ex=300)  # 5 min
            await client.set('temp:test-key-2', 'another temp', ex=60)    # 1 min
            
            logger.info("Redis test data seeding completed")
            
        finally:
            await client.aclose()
    
    async def seed_clickhouse_data(self) -> None:
        """Seed ClickHouse with test analytics data."""
        logger.info("Seeding ClickHouse test data...")
        
        client = ClickHouseClient(**self.clickhouse_config)
        try:
            # Generate sample user events
            user_events = []
            for i in range(100):
                user_events.append({
                    'user_id': f'550e8400-e29b-41d4-a716-44665544000{i % 3 + 1}',
                    'event_type': ['login', 'page_view', 'agent_create', 'message_send'][i % 4],
                    'session_id': f'session_{i % 10}',
                    'properties': {'source': 'test', 'batch': 'seed_data'}
                })
            
            # Insert user events
            if user_events:
                client.execute(
                    "INSERT INTO user_events (user_id, event_type, session_id, properties) VALUES",
                    [(e['user_id'], e['event_type'], e['session_id'], e['properties']) for e in user_events]
                )
                logger.info(f"Inserted {len(user_events)} user events")
            
            # Generate sample conversation events
            conversation_events = []
            for i in range(50):
                conversation_events.append((
                    f'660e8400-e29b-41d4-a716-44665544000{i % 5 + 1}',  # conversation_id
                    f'770e8400-e29b-41d4-a716-44665544000{i % 3 + 1}',  # agent_id
                    f'550e8400-e29b-41d4-a716-44665544000{i % 3 + 1}',  # user_id
                    f'880e8400-e29b-41d4-a716-44665544000{i % 2 + 1}',  # organization_id
                    ['conversation_start', 'message_sent', 'tool_used'][i % 3],  # event_type
                    i + 1,  # message_count
                    (i + 1) * 150,  # tokens_used
                    (i + 1) * 100,  # execution_time_ms
                    'gpt-4',  # model_used
                    ['web_search', 'code_execution'][i % 2:i % 2 + 1]  # tool_calls
                ))
            
            if conversation_events:
                client.execute("""
                    INSERT INTO conversation_events 
                    (conversation_id, agent_id, user_id, organization_id, event_type, 
                     message_count, tokens_used, execution_time_ms, model_used, tool_calls) VALUES
                """, conversation_events)
                logger.info(f"Inserted {len(conversation_events)} conversation events")
            
            # Generate tool execution data
            tool_executions = []
            for i in range(30):
                tool_executions.append((
                    f'660e8400-e29b-41d4-a716-44665544000{i % 5 + 1}',  # conversation_id
                    f'770e8400-e29b-41d4-a716-44665544000{i % 3 + 1}',  # agent_id
                    ['web_search', 'code_execution', 'file_read', 'api_call'][i % 4],  # tool_name
                    ['success', 'error', 'timeout'][i % 3],  # execution_status
                    (i + 1) * 100 + 50,  # execution_time_ms
                    1024 + i * 100,  # parameters_size
                    2048 + i * 200,  # result_size
                    'Test error' if i % 3 == 1 else None,  # error_message
                    i % 3  # retry_count
                ))
                
            if tool_executions:
                client.execute("""
                    INSERT INTO tool_executions
                    (conversation_id, agent_id, tool_name, execution_status, execution_time_ms,
                     parameters_size, result_size, error_message, retry_count) VALUES  
                """, tool_executions)
                logger.info(f"Inserted {len(tool_executions)} tool executions")
                
            logger.info("ClickHouse test data seeding completed")
            
        finally:
            client.disconnect()
    
    async def run(self) -> None:
        """Run the complete seeding process."""
        logger.info("Starting test data seeding process...")
        
        try:
            await self.wait_for_services()
            
            # Seed databases in parallel where possible
            await asyncio.gather(
                self.seed_postgres_data(),
                self.seed_redis_data(),
                self.seed_clickhouse_data()
            )
            
            logger.info("Test data seeding completed successfully!")
            
        except Exception as e:
            logger.error(f"Test data seeding failed: {e}")
            raise


async def main():
    """Main entry point."""
    seeder = TestDataSeeder()
    await seeder.run()


if __name__ == "__main__":
    asyncio.run(main())
