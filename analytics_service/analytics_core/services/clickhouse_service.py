"""
ClickHouse Service Layer for Analytics Service

Provides high-level methods for event insertion, querying, reporting,
materialized view management, data retention, and aggregation queries.
Complete isolation from other services.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import json
import hashlib
from uuid import UUID, uuid4

from analytics_core.database.clickhouse_manager import ClickHouseManager, ClickHouseQueryError


logger = logging.getLogger(__name__)


class ClickHouseService:
    """
    High-level ClickHouse service for analytics operations including
    event insertion, querying, reporting, and data management.
    """
    
    def __init__(self, clickhouse_manager: ClickHouseManager):
        """
        Initialize ClickHouse service.
        
        Args:
            clickhouse_manager: ClickHouse connection manager instance
        """
        self.ch_manager = clickhouse_manager
        self._table_schemas = self._get_table_schemas()
        self._materialized_views = self._get_materialized_view_schemas()
    
    async def initialize_tables(self) -> None:
        """Initialize all required tables and materialized views."""
        try:
            # Create main tables
            for table_name, schema in self._table_schemas.items():
                logger.info(f"Creating table: {table_name}")
                await self.ch_manager.create_table_if_not_exists(schema)
            
            # Create materialized views
            for view_name, schema in self._materialized_views.items():
                logger.info(f"Creating materialized view: {view_name}")
                await self.ch_manager.execute_command(schema)
            
            logger.info("All ClickHouse tables and views initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse tables: {e}")
            raise
    
    # Event Insertion Methods
    
    async def insert_frontend_event(
        self,
        user_id: str,
        session_id: str,
        event_type: str,
        event_category: str,
        event_action: str,
        event_label: Optional[str] = None,
        event_value: Optional[float] = None,
        properties: Optional[Dict[str, Any]] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        country_code: Optional[str] = None,
        page_path: Optional[str] = None,
        page_title: Optional[str] = None,
        referrer: Optional[str] = None,
        gtm_container_id: Optional[str] = None,
        environment: str = "production",
        app_version: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Insert a frontend event into the events table.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            event_type: Type of event
            event_category: Event category
            event_action: Event action
            event_label: Optional event label
            event_value: Optional numeric value
            properties: Additional event properties as dict
            user_agent: User agent string
            ip_address: IP address (will be hashed for privacy)
            country_code: Country code
            page_path: Current page path
            page_title: Current page title
            referrer: Referrer URL
            gtm_container_id: GTM container ID
            environment: Environment (dev/staging/production)
            app_version: Application version
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            Event ID (UUID)
        """
        event_id = str(uuid4())
        current_timestamp = timestamp or datetime.utcnow()
        
        # Hash IP address for privacy if provided
        hashed_ip = None
        if ip_address:
            hashed_ip = hashlib.sha256(f"{ip_address}:{current_timestamp.date()}".encode()).hexdigest()[:16]
        
        event_data = {
            'event_id': event_id,
            'timestamp': current_timestamp,
            'user_id': user_id,
            'session_id': session_id,
            'event_type': event_type,
            'event_category': event_category,
            'event_action': event_action,
            'event_label': event_label or '',
            'event_value': event_value or 0.0,
            'properties': json.dumps(properties) if properties else '{}',
            'user_agent': user_agent or '',
            'ip_address': hashed_ip or '',
            'country_code': country_code or '',
            'page_path': page_path or '',
            'page_title': page_title or '',
            'referrer': referrer or '',
            'gtm_container_id': gtm_container_id or '',
            'environment': environment,
            'app_version': app_version or ''
        }
        
        await self.ch_manager.insert_data('frontend_events', [event_data])
        
        logger.debug(f"Inserted frontend event: {event_id} for user {user_id}")
        return event_id
    
    async def insert_chat_interaction(
        self,
        user_id: str,
        session_id: str,
        thread_id: str,
        message_id: str,
        message_type: str,
        prompt_text: Optional[str] = None,
        prompt_length: Optional[int] = None,
        response_length: Optional[int] = None,
        response_time_ms: Optional[float] = None,
        model_used: Optional[str] = None,
        tokens_consumed: Optional[int] = None,
        is_follow_up: bool = False,
        **kwargs
    ) -> str:
        """
        Insert a chat interaction event.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            thread_id: Chat thread identifier
            message_id: Message identifier
            message_type: Type of message (user_prompt|ai_response|system_message)
            prompt_text: User's prompt text (sanitized)
            prompt_length: Character count of prompt
            response_length: Character count of AI response
            response_time_ms: Time to receive response
            model_used: AI model identifier
            tokens_consumed: Token count for request
            is_follow_up: Whether this is a follow-up question
            **kwargs: Additional properties
            
        Returns:
            Event ID
        """
        properties = {
            'thread_id': thread_id,
            'message_id': message_id,
            'message_type': message_type,
            'prompt_length': prompt_length,
            'response_length': response_length,
            'response_time_ms': response_time_ms,
            'model_used': model_used,
            'tokens_consumed': tokens_consumed,
            'is_follow_up': is_follow_up,
            **kwargs
        }
        
        # Remove None values
        properties = {k: v for k, v in properties.items() if v is not None}
        
        return await self.insert_frontend_event(
            user_id=user_id,
            session_id=session_id,
            event_type='chat_interaction',
            event_category='User Interaction Events',
            event_action=message_type,
            event_label=thread_id,
            event_value=float(tokens_consumed) if tokens_consumed else None,
            properties=properties,
            **{k: v for k, v in kwargs.items() if k in [
                'page_path', 'page_title', 'user_agent', 'environment', 'app_version'
            ]}
        )
    
    async def insert_prompt_analytics(
        self,
        user_id: str,
        thread_id: str,
        prompt_hash: str,
        prompt_category: Optional[str] = None,
        prompt_intent: Optional[str] = None,
        prompt_complexity_score: Optional[float] = None,
        response_quality_score: Optional[float] = None,
        response_relevance_score: Optional[float] = None,
        follow_up_generated: bool = False,
        is_repeat_question: bool = False,
        similar_prompts: Optional[List[str]] = None,
        estimated_cost_cents: Optional[float] = None,
        actual_cost_cents: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Insert prompt analytics data.
        
        Args:
            user_id: User identifier
            thread_id: Thread identifier
            prompt_hash: Hash for deduplication
            prompt_category: ML-classified category
            prompt_intent: Detected user intent
            prompt_complexity_score: Complexity score
            response_quality_score: Quality score
            response_relevance_score: Relevance score
            follow_up_generated: Whether follow-up was generated
            is_repeat_question: Whether this is a repeat question
            similar_prompts: List of similar prompt IDs
            estimated_cost_cents: Estimated cost in cents
            actual_cost_cents: Actual cost in cents
            timestamp: Event timestamp
            
        Returns:
            Prompt ID (UUID)
        """
        prompt_id = str(uuid4())
        current_timestamp = timestamp or datetime.utcnow()
        
        prompt_data = {
            'prompt_id': prompt_id,
            'timestamp': current_timestamp,
            'user_id': user_id,
            'thread_id': thread_id,
            'prompt_hash': prompt_hash,
            'prompt_category': prompt_category or '',
            'prompt_intent': prompt_intent or '',
            'prompt_complexity_score': prompt_complexity_score,
            'response_quality_score': response_quality_score,
            'response_relevance_score': response_relevance_score,
            'follow_up_generated': follow_up_generated,
            'is_repeat_question': is_repeat_question,
            'similar_prompts': similar_prompts or [],
            'estimated_cost_cents': estimated_cost_cents,
            'actual_cost_cents': actual_cost_cents
        }
        
        await self.ch_manager.insert_data('prompt_analytics', [prompt_data])
        
        logger.debug(f"Inserted prompt analytics: {prompt_id} for user {user_id}")
        return prompt_id
    
    async def batch_insert_events(
        self,
        events: List[Dict[str, Any]],
        table: str = 'frontend_events'
    ) -> int:
        """
        Insert multiple events in a batch for better performance.
        
        Args:
            events: List of event dictionaries
            table: Target table name
            
        Returns:
            Number of events inserted
        """
        if not events:
            return 0
        
        # Add generated fields for events missing them
        for event in events:
            if 'event_id' not in event:
                event['event_id'] = str(uuid4())
            if 'timestamp' not in event:
                event['timestamp'] = datetime.utcnow()
            if 'properties' in event and isinstance(event['properties'], dict):
                event['properties'] = json.dumps(event['properties'])
        
        count = await self.ch_manager.insert_data(table, events)
        
        logger.info(f"Batch inserted {count} events into {table}")
        return count
    
    # Query Methods for Reports
    
    async def get_user_activity_summary(
        self,
        user_id: Optional[str] = None,
        start_date: datetime = None,
        end_date: datetime = None,
        granularity: str = 'day'
    ) -> List[Dict[str, Any]]:
        """
        Get user activity summary.
        
        Args:
            user_id: Optional user ID filter
            start_date: Start date for the report
            end_date: End date for the report
            granularity: Time granularity (hour|day|week|month)
            
        Returns:
            List of user activity records
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Build granularity clause
        granularity_map = {
            'hour': 'toStartOfHour(timestamp)',
            'day': 'toStartOfDay(timestamp)',
            'week': 'toStartOfWeek(timestamp)',
            'month': 'toStartOfMonth(timestamp)'
        }
        time_bucket = granularity_map.get(granularity, 'toStartOfDay(timestamp)')
        
        # Build WHERE clause
        where_conditions = [
            "timestamp >= %(start_date)s",
            "timestamp <= %(end_date)s"
        ]
        
        parameters = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        if user_id:
            where_conditions.append("user_id = %(user_id)s")
            parameters['user_id'] = user_id
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        query = f"""
        SELECT 
            user_id,
            {time_bucket} as time_bucket,
            count() as total_events,
            countIf(event_type = 'chat_interaction') as chat_interactions,
            countIf(event_type = 'thread_lifecycle' AND event_action = 'created') as threads_created,
            countIf(event_type = 'feature_usage') as feature_interactions,
            countIf(event_type = 'performance_metric') as performance_events,
            uniqExact(session_id) as unique_sessions,
            sum(event_value) as total_event_value,
            avg(event_value) as avg_event_value
        FROM frontend_events 
        {where_clause}
        GROUP BY user_id, time_bucket
        ORDER BY user_id, time_bucket
        """
        
        results = await self.ch_manager.execute_query(query, parameters)
        
        return [
            {
                'user_id': row[0],
                'time_bucket': row[1],
                'total_events': row[2],
                'chat_interactions': row[3],
                'threads_created': row[4],
                'feature_interactions': row[5],
                'performance_events': row[6],
                'unique_sessions': row[7],
                'total_event_value': row[8],
                'avg_event_value': row[9]
            }
            for row in results
        ]
    
    async def get_prompt_analytics_report(
        self,
        category: Optional[str] = None,
        min_frequency: int = 5,
        time_range: str = '24h',
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate prompt analytics report.
        
        Args:
            category: Optional prompt category filter
            min_frequency: Minimum frequency for inclusion
            time_range: Time range (1h|24h|7d|30d)
            user_id: Optional user ID filter
            
        Returns:
            Prompt analytics report
        """
        # Parse time range
        time_ranges = {
            '1h': timedelta(hours=1),
            '24h': timedelta(hours=24),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30)
        }
        
        delta = time_ranges.get(time_range, timedelta(days=1))
        start_time = datetime.utcnow() - delta
        
        # Build WHERE clause
        where_conditions = ["timestamp >= %(start_time)s"]
        parameters = {'start_time': start_time, 'min_frequency': min_frequency}
        
        if category:
            where_conditions.append("prompt_category = %(category)s")
            parameters['category'] = category
        
        if user_id:
            where_conditions.append("user_id = %(user_id)s")
            parameters['user_id'] = user_id
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Get top prompts by frequency
        prompt_frequency_query = f"""
        SELECT 
            prompt_hash,
            prompt_category,
            prompt_intent,
            count() as frequency,
            avg(prompt_complexity_score) as avg_complexity,
            avg(response_quality_score) as avg_quality,
            avg(response_relevance_score) as avg_relevance,
            countIf(follow_up_generated) as follow_ups_generated,
            countIf(is_repeat_question) as repeat_questions,
            avg(actual_cost_cents) as avg_cost_cents
        FROM prompt_analytics 
        {where_clause}
        GROUP BY prompt_hash, prompt_category, prompt_intent
        HAVING count() >= %(min_frequency)s
        ORDER BY frequency DESC
        LIMIT 50
        """
        
        prompt_results = await self.ch_manager.execute_query(prompt_frequency_query, parameters)
        
        # Get category distribution
        category_query = f"""
        SELECT 
            prompt_category,
            count() as count,
            avg(prompt_complexity_score) as avg_complexity
        FROM prompt_analytics 
        {where_clause}
        GROUP BY prompt_category
        ORDER BY count DESC
        """
        
        category_results = await self.ch_manager.execute_query(category_query, parameters)
        
        # Get intent distribution
        intent_query = f"""
        SELECT 
            prompt_intent,
            count() as count,
            avg(response_quality_score) as avg_quality
        FROM prompt_analytics 
        {where_clause}
        GROUP BY prompt_intent
        ORDER BY count DESC
        """
        
        intent_results = await self.ch_manager.execute_query(intent_query, parameters)
        
        return {
            'time_range': time_range,
            'total_prompts': sum(row[3] for row in prompt_results),
            'top_prompts': [
                {
                    'prompt_hash': row[0],
                    'category': row[1],
                    'intent': row[2],
                    'frequency': row[3],
                    'avg_complexity': row[4],
                    'avg_quality': row[5],
                    'avg_relevance': row[6],
                    'follow_ups_generated': row[7],
                    'repeat_questions': row[8],
                    'avg_cost_cents': row[9]
                }
                for row in prompt_results
            ],
            'category_distribution': [
                {
                    'category': row[0],
                    'count': row[1],
                    'avg_complexity': row[2]
                }
                for row in category_results
            ],
            'intent_distribution': [
                {
                    'intent': row[0],
                    'count': row[1],
                    'avg_quality': row[2]
                }
                for row in intent_results
            ]
        }
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """
        Get real-time metrics for dashboards.
        
        Returns:
            Dictionary with real-time metrics
        """
        # Get metrics for last 5 minutes
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)
        
        metrics_query = """
        SELECT 
            uniqExact(user_id) as active_users,
            uniqExact(session_id) as active_sessions,
            countIf(event_type = 'chat_interaction') as chat_interactions,
            countIf(event_type = 'thread_lifecycle' AND event_action = 'created') as new_threads,
            countIf(event_type = 'error_tracking') as errors,
            avgIf(
                JSONExtractFloat(properties, 'response_time_ms'), 
                event_type = 'chat_interaction' AND JSONExtractFloat(properties, 'response_time_ms') > 0
            ) as avg_response_time_ms
        FROM frontend_events 
        WHERE timestamp >= %(five_min_ago)s
        """
        
        result = await self.ch_manager.execute_query(
            metrics_query,
            {'five_min_ago': five_min_ago}
        )
        
        if result:
            row = result[0]
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'active_users': row[0],
                'active_sessions': row[1],
                'chat_interactions': row[2],
                'new_threads': row[3],
                'errors': row[4],
                'avg_response_time_ms': row[5] or 0,
                'error_rate': (row[4] / max(row[2], 1)) * 100  # Error rate as percentage
            }
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'active_users': 0,
            'active_sessions': 0,
            'chat_interactions': 0,
            'new_threads': 0,
            'errors': 0,
            'avg_response_time_ms': 0,
            'error_rate': 0
        }
    
    # Materialized View Management
    
    async def refresh_materialized_views(self) -> None:
        """Manually refresh materialized views (if needed)."""
        # ClickHouse materialized views are automatically updated,
        # but we can check their status or force optimization
        
        tables_to_optimize = ['user_analytics_summary']
        
        for table in tables_to_optimize:
            try:
                await self.ch_manager.execute_command(f"OPTIMIZE TABLE {table} FINAL")
                logger.info(f"Optimized materialized view: {table}")
            except Exception as e:
                logger.warning(f"Failed to optimize {table}: {e}")
    
    async def get_materialized_view_status(self) -> Dict[str, Any]:
        """
        Get status of materialized views.
        
        Returns:
            Dictionary with view status information
        """
        status = {}
        
        for view_name in self._materialized_views.keys():
            try:
                # Get row count and latest timestamp
                count_query = f"SELECT count(), max(date) FROM {view_name}"
                result = await self.ch_manager.execute_query(count_query)
                
                if result:
                    row_count, latest_date = result[0]
                    status[view_name] = {
                        'row_count': row_count,
                        'latest_date': latest_date,
                        'status': 'healthy'
                    }
                else:
                    status[view_name] = {
                        'row_count': 0,
                        'latest_date': None,
                        'status': 'empty'
                    }
                    
            except Exception as e:
                status[view_name] = {
                    'error': str(e),
                    'status': 'error'
                }
        
        return status
    
    # Data Retention and Cleanup
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """
        Clean up expired data based on TTL policies.
        Note: ClickHouse handles TTL automatically, but we can force cleanup.
        
        Returns:
            Dictionary with cleanup results
        """
        cleanup_results = {}
        
        # Force TTL cleanup on tables with TTL
        ttl_tables = ['frontend_events', 'prompt_analytics']
        
        for table in ttl_tables:
            try:
                # Force TTL deletion
                await self.ch_manager.execute_command(f"OPTIMIZE TABLE {table} FINAL")
                
                # Get count after cleanup
                count_result = await self.ch_manager.execute_query(f"SELECT count() FROM {table}")
                remaining_count = count_result[0][0] if count_result else 0
                
                cleanup_results[table] = remaining_count
                logger.info(f"TTL cleanup completed for {table}, {remaining_count} rows remaining")
                
            except Exception as e:
                logger.error(f"TTL cleanup failed for {table}: {e}")
                cleanup_results[table] = -1
        
        return cleanup_results
    
    async def get_storage_usage(self) -> Dict[str, Any]:
        """
        Get storage usage information.
        
        Returns:
            Dictionary with storage usage data
        """
        usage_query = """
        SELECT 
            table,
            sum(bytes_on_disk) as bytes_on_disk,
            sum(rows) as total_rows,
            max(modification_time) as last_modified
        FROM system.parts 
        WHERE database = %(database)s
        GROUP BY table
        ORDER BY bytes_on_disk DESC
        """
        
        results = await self.ch_manager.execute_query(
            usage_query,
            {'database': self.ch_manager.database}
        )
        
        return {
            'tables': [
                {
                    'table': row[0],
                    'bytes_on_disk': row[1],
                    'total_rows': row[2],
                    'last_modified': row[3],
                    'size_mb': round(row[1] / (1024 * 1024), 2)
                }
                for row in results
            ],
            'total_size_bytes': sum(row[1] for row in results),
            'total_rows': sum(row[2] for row in results)
        }
    
    # Aggregation Queries
    
    async def get_user_journey_funnel(
        self,
        funnel_steps: List[str],
        start_date: datetime,
        end_date: datetime,
        user_segment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate conversion funnel for user journey.
        
        Args:
            funnel_steps: List of event types/actions defining the funnel
            start_date: Start date for analysis
            end_date: End date for analysis
            user_segment: Optional user segment filter
            
        Returns:
            Funnel analysis results
        """
        # Build funnel query using ClickHouse's funnel analysis functions
        step_conditions = []
        for i, step in enumerate(funnel_steps):
            if '=' in step:
                # Handle conditions like 'event_type=chat_interaction'
                step_conditions.append(f"step_{i+1} = 1")
            else:
                step_conditions.append(f"event_type = '{step}'")
        
        # This is a simplified version - real funnel analysis would be more complex
        funnel_query = f"""
        SELECT 
            arraySum(arraySlice(levels, 1, 1)) as step_1_users,
            arraySum(arraySlice(levels, 1, 2)) as step_2_users,
            arraySum(arraySlice(levels, 1, 3)) as step_3_users
        FROM (
            SELECT 
                user_id,
                windowFunnel(86400)(
                    timestamp,
                    {', '.join(step_conditions[:3])}  -- Limit to first 3 steps for example
                ) as levels
            FROM (
                SELECT 
                    user_id,
                    timestamp,
                    {', '.join([f"event_type = '{step}' as step_{i+1}" for i, step in enumerate(funnel_steps[:3])])}
                FROM frontend_events 
                WHERE timestamp BETWEEN %(start_date)s AND %(end_date)s
            )
            GROUP BY user_id
        )
        """
        
        # This is a placeholder - implement proper funnel analysis based on your needs
        return {
            'funnel_steps': funnel_steps,
            'conversion_rates': [],
            'total_users_entered': 0,
            'dropoff_analysis': []
        }
    
    # Private Methods
    
    def _get_table_schemas(self) -> Dict[str, str]:
        """Get table creation schemas."""
        return {
            'frontend_events': """
            CREATE TABLE IF NOT EXISTS frontend_events (
              event_id UUID DEFAULT generateUUIDv4(),
              timestamp DateTime64(3) DEFAULT now(),
              user_id String,
              session_id String,
              event_type String,
              event_category String,
              event_action String,
              event_label String,
              event_value Float64,
              
              -- Event-specific properties as JSON
              properties String, -- JSON string with event-specific data
              
              -- User context
              user_agent String,
              ip_address String, -- Hashed for privacy
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
            """,
            
            'prompt_analytics': """
            CREATE TABLE IF NOT EXISTS prompt_analytics (
              prompt_id UUID DEFAULT generateUUIDv4(),
              timestamp DateTime64(3) DEFAULT now(),
              user_id String,
              thread_id String,
              
              -- Prompt details
              prompt_hash String, -- Hash for deduplication
              prompt_category String, -- ML-classified category
              prompt_intent String, -- Detected user intent
              prompt_complexity_score Float32,
              
              -- Response metrics
              response_quality_score Float32,
              response_relevance_score Float32,
              follow_up_generated Boolean,
              
              -- Usage patterns
              is_repeat_question Boolean,
              similar_prompts Array(String), -- IDs of similar prompts
              
              -- Cost tracking
              estimated_cost_cents Float32,
              actual_cost_cents Float32
            )
            ENGINE = MergeTree()
            PARTITION BY toYYYYMM(timestamp)
            ORDER BY (user_id, timestamp, prompt_id)
            TTL timestamp + INTERVAL 180 DAY
            """
        }
    
    def _get_materialized_view_schemas(self) -> Dict[str, str]:
        """Get materialized view creation schemas."""
        return {
            'user_analytics_summary': """
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
        }