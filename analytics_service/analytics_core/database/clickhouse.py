"""ClickHouse Database Manager

Handles ClickHouse connections and analytics table management.
"""

import logging
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime, date
import json

try:
    from clickhouse_driver import Client
    from clickhouse_driver.errors import Error as ClickHouseError
except ImportError:
    # Fallback for when ClickHouse is not available
    Client = None
    ClickHouseError = Exception

from analytics_service.analytics_core.models.events import (
    FrontendEvent, 
    PromptAnalytics, 
    UserAnalyticsSummary
)

logger = logging.getLogger(__name__)


class ClickHouseManager:
    """ClickHouse database manager for analytics data"""
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 9000,
                 database: str = "analytics",
                 user: str = "default",
                 password: str = "",
                 secure: bool = False):
        """Initialize ClickHouse manager"""
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.secure = secure
        self._client = None
        
        # Connection settings
        self.settings = {
            'max_execution_time': 60,
            'max_memory_usage': 10**10,  # 10GB
            'use_numpy': True
        }
    
    @property
    def client(self) -> Optional[Client]:
        """Get ClickHouse client connection"""
        if Client is None:
            logger.error("ClickHouse client not available - please install clickhouse-driver")
            return None
            
        if self._client is None:
            try:
                self._client = Client(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    secure=self.secure,
                    settings=self.settings
                )
                logger.info(f"Connected to ClickHouse at {self.host}:{self.port}")
            except Exception as e:
                logger.error(f"Failed to connect to ClickHouse: {e}")
                return None
        
        return self._client
    
    async def initialize_schema(self) -> bool:
        """Initialize analytics database schema"""
        if not self.client:
            return False
            
        try:
            # Create database
            await self._execute_async(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            
            # Create frontend_events table
            await self._create_frontend_events_table()
            
            # Create prompt_analytics table
            await self._create_prompt_analytics_table()
            
            # Create user_analytics_summary materialized view
            await self._create_user_analytics_summary_view()
            
            logger.info("ClickHouse schema initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse schema: {e}")
            return False
    
    async def _execute_async(self, query: str, params=None):
        """Execute query asynchronously"""
        def _execute():
            return self.client.execute(query, params)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _execute)
    
    async def _create_frontend_events_table(self):
        """Create frontend_events table"""
        query = """
        CREATE TABLE IF NOT EXISTS frontend_events (
          event_id String,
          timestamp DateTime64(3) DEFAULT now(),
          user_id String,
          session_id String,
          event_type String,
          event_category String,
          event_action String,
          event_label String,
          event_value Float64,
          
          -- Event-specific properties as JSON
          properties String,
          
          -- User context
          user_agent String,
          ip_address String,
          country_code String,
          
          -- Page context  
          page_path String,
          page_title String,
          referrer String,
          
          -- Technical metadata
          gtm_container_id String,
          environment String,
          app_version String,
          
          -- Computed fields
          date Date DEFAULT toDate(timestamp),
          hour UInt8 DEFAULT toHour(timestamp)
        )
        ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (user_id, timestamp, event_id)
        TTL timestamp + INTERVAL 90 DAY
        SETTINGS index_granularity = 8192
        """
        await self._execute_async(query)
        
    async def _create_prompt_analytics_table(self):
        """Create prompt_analytics table"""
        query = """
        CREATE TABLE IF NOT EXISTS prompt_analytics (
          prompt_id String,
          timestamp DateTime64(3) DEFAULT now(),
          user_id String,
          thread_id String,
          
          -- Prompt details
          prompt_hash String,
          prompt_category String,
          prompt_intent String,
          prompt_complexity_score Float32,
          
          -- Response metrics
          response_quality_score Float32,
          response_relevance_score Float32,
          follow_up_generated UInt8,
          
          -- Usage patterns
          is_repeat_question UInt8,
          similar_prompts Array(String),
          
          -- Cost tracking
          estimated_cost_cents Float32,
          actual_cost_cents Float32
        )
        ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (user_id, timestamp, prompt_id)
        TTL timestamp + INTERVAL 180 DAY
        """
        await self._execute_async(query)
    
    async def _create_user_analytics_summary_view(self):
        """Create user_analytics_summary materialized view"""
        query = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS user_analytics_summary
        ENGINE = SummingMergeTree()
        PARTITION BY toYYYYMM(date)
        ORDER BY (user_id, date)
        AS SELECT
          user_id,
          toDate(timestamp) as date,
          count() as total_events,
          countIf(event_type = 'chat_interaction') as chat_interactions,
          countIf(event_type = 'thread_lifecycle' AND event_action = 'created') as threads_created,
          countIf(event_type = 'feature_usage') as feature_interactions,
          sumIf(event_value, event_type = 'chat_interaction') as total_tokens_consumed,
          avgIf(event_value, event_type = 'performance_metric') as avg_response_time
        FROM frontend_events
        GROUP BY user_id, date
        """
        await self._execute_async(query)
    
    async def insert_events(self, events: List[FrontendEvent]) -> int:
        """Insert frontend events into ClickHouse"""
        if not self.client or not events:
            return 0
            
        try:
            # Convert events to tuples for bulk insert
            data = []
            for event in events:
                data.append((
                    str(event.event_id),
                    event.timestamp,
                    event.user_id,
                    event.session_id,
                    event.event_type.value,
                    event.event_category.value,
                    event.event_action,
                    event.event_label or '',
                    event.event_value or 0.0,
                    json.dumps(event.properties),
                    event.user_agent or '',
                    event.ip_address or '',
                    event.country_code or '',
                    event.page_path or '',
                    event.page_title or '',
                    event.referrer or '',
                    event.gtm_container_id or '',
                    event.environment or '',
                    event.app_version or ''
                ))
            
            query = """
            INSERT INTO frontend_events (
                event_id, timestamp, user_id, session_id, event_type, event_category,
                event_action, event_label, event_value, properties, user_agent,
                ip_address, country_code, page_path, page_title, referrer,
                gtm_container_id, environment, app_version
            ) VALUES
            """
            
            await self._execute_async(query, data)
            logger.info(f"Inserted {len(events)} events into ClickHouse")
            return len(events)
            
        except Exception as e:
            logger.error(f"Failed to insert events into ClickHouse: {e}")
            return 0
    
    async def insert_prompt_analytics(self, analytics: List[PromptAnalytics]) -> int:
        """Insert prompt analytics into ClickHouse"""
        if not self.client or not analytics:
            return 0
            
        try:
            data = []
            for analytic in analytics:
                data.append((
                    str(analytic.prompt_id),
                    analytic.timestamp,
                    analytic.user_id,
                    analytic.thread_id,
                    analytic.prompt_hash,
                    analytic.prompt_category or '',
                    analytic.prompt_intent or '',
                    analytic.prompt_complexity_score or 0.0,
                    analytic.response_quality_score or 0.0,
                    analytic.response_relevance_score or 0.0,
                    1 if analytic.follow_up_generated else 0,
                    1 if analytic.is_repeat_question else 0,
                    analytic.similar_prompts,
                    analytic.estimated_cost_cents or 0.0,
                    analytic.actual_cost_cents or 0.0
                ))
            
            query = """
            INSERT INTO prompt_analytics (
                prompt_id, timestamp, user_id, thread_id, prompt_hash,
                prompt_category, prompt_intent, prompt_complexity_score,
                response_quality_score, response_relevance_score,
                follow_up_generated, is_repeat_question, similar_prompts,
                estimated_cost_cents, actual_cost_cents
            ) VALUES
            """
            
            await self._execute_async(query, data)
            logger.info(f"Inserted {len(analytics)} prompt analytics into ClickHouse")
            return len(analytics)
            
        except Exception as e:
            logger.error(f"Failed to insert prompt analytics into ClickHouse: {e}")
            return 0
    
    async def get_user_activity_report(self, 
                                     user_id: Optional[str] = None,
                                     start_date: Optional[date] = None,
                                     end_date: Optional[date] = None,
                                     granularity: str = "day") -> List[Dict[str, Any]]:
        """Get user activity report"""
        if not self.client:
            return []
            
        try:
            # Build query
            conditions = []
            if user_id:
                conditions.append(f"user_id = '{user_id}'")
            if start_date:
                conditions.append(f"date >= '{start_date}'")
            if end_date:
                conditions.append(f"date <= '{end_date}'")
                
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            # Determine grouping based on granularity
            if granularity == "hour":
                group_by = "user_id, toStartOfHour(timestamp)"
                time_field = "toStartOfHour(timestamp) as time_period"
            elif granularity == "week":
                group_by = "user_id, toStartOfWeek(timestamp)"
                time_field = "toStartOfWeek(timestamp) as time_period"
            elif granularity == "month":
                group_by = "user_id, toStartOfMonth(timestamp)"
                time_field = "toStartOfMonth(timestamp) as time_period"
            else:  # day
                group_by = "user_id, date"
                time_field = "date as time_period"
            
            query = f"""
            SELECT 
                user_id,
                {time_field},
                sum(total_events) as total_events,
                sum(chat_interactions) as chat_interactions,
                sum(threads_created) as threads_created,
                sum(feature_interactions) as feature_interactions,
                sum(total_tokens_consumed) as total_tokens_consumed,
                avg(avg_response_time) as avg_response_time
            FROM user_analytics_summary
            {where_clause}
            GROUP BY {group_by}
            ORDER BY time_period DESC
            LIMIT 1000
            """
            
            result = await self._execute_async(query)
            
            # Convert result to list of dicts
            columns = [
                'user_id', 'time_period', 'total_events', 'chat_interactions',
                'threads_created', 'feature_interactions', 'total_tokens_consumed',
                'avg_response_time'
            ]
            
            return [dict(zip(columns, row)) for row in result]
            
        except Exception as e:
            logger.error(f"Failed to get user activity report: {e}")
            return []
    
    async def get_prompt_analytics_report(self,
                                        category: Optional[str] = None,
                                        min_frequency: int = 5,
                                        time_range: str = "24h") -> List[Dict[str, Any]]:
        """Get prompt analytics report"""
        if not self.client:
            return []
            
        try:
            # Convert time range to hours
            time_hours = {
                "1h": 1,
                "24h": 24,
                "7d": 168,
                "30d": 720
            }.get(time_range, 24)
            
            conditions = [f"timestamp >= now() - INTERVAL {time_hours} HOUR"]
            if category:
                conditions.append(f"prompt_category = '{category}'")
                
            where_clause = "WHERE " + " AND ".join(conditions)
            
            query = f"""
            SELECT 
                prompt_hash,
                prompt_category,
                prompt_intent,
                count() as frequency,
                avg(prompt_complexity_score) as avg_complexity,
                avg(response_quality_score) as avg_quality,
                countIf(follow_up_generated = 1) / count() as follow_up_rate,
                avg(estimated_cost_cents) as avg_cost_cents
            FROM prompt_analytics
            {where_clause}
            GROUP BY prompt_hash, prompt_category, prompt_intent
            HAVING frequency >= {min_frequency}
            ORDER BY frequency DESC
            LIMIT 100
            """
            
            result = await self._execute_async(query)
            
            columns = [
                'prompt_hash', 'prompt_category', 'prompt_intent', 'frequency',
                'avg_complexity', 'avg_quality', 'follow_up_rate', 'avg_cost_cents'
            ]
            
            return [dict(zip(columns, row)) for row in result]
            
        except Exception as e:
            logger.error(f"Failed to get prompt analytics report: {e}")
            return []
    
    async def get_realtime_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics"""
        if not self.client:
            return {}
            
        try:
            # Get metrics from last 5 minutes
            query = """
            SELECT
                countDistinct(user_id) as active_users,
                countIf(event_type = 'chat_interaction') as active_chats,
                avgIf(event_value, event_type = 'performance_metric' AND event_action = 'api_response') as avg_response_time,
                countIf(event_type = 'error_tracking') / count() * 100 as error_rate_percent
            FROM frontend_events
            WHERE timestamp >= now() - INTERVAL 5 MINUTE
            """
            
            result = await self._execute_async(query)
            
            if result:
                return {
                    'active_users': result[0][0],
                    'active_chats': result[0][1],
                    'avg_response_time_ms': result[0][2] or 0,
                    'error_rate_percent': result[0][3] or 0,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get realtime metrics: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check ClickHouse connection health"""
        if not self.client:
            return False
            
        try:
            await self._execute_async("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {e}")
            return False
    
    def close(self):
        """Close ClickHouse connection"""
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None