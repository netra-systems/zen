"""Event Processing Service

Main event processor for analytics service with batch processing, 
error handling, and report generation capabilities.
"""

import asyncio
import logging
import hashlib
import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import os
from contextlib import asynccontextmanager

from analytics_service.analytics_core.models.events import (
    FrontendEvent,
    EventType,
    EventCategory,
    ChatInteractionEvent,
    ThreadLifecycleEvent,
    FeatureUsageEvent,
    PromptAnalytics,
    EventBatch,
    ProcessingResult
)
from analytics_service.analytics_core.database.clickhouse import ClickHouseManager
from analytics_service.analytics_core.database.redis import RedisManager

logger = logging.getLogger(__name__)


@dataclass
class ProcessorConfig:
    """Event processor configuration"""
    batch_size: int = 100
    flush_interval_seconds: int = 5
    max_retries: int = 3
    retry_delay_seconds: int = 1
    max_events_per_user_per_minute: int = 1000
    enable_privacy_filtering: bool = True
    enable_analytics: bool = True


class EventProcessor:
    """Main event processing service for analytics"""
    
    def __init__(self, 
                 clickhouse_manager: Optional[ClickHouseManager] = None,
                 redis_manager: Optional[RedisManager] = None,
                 config: Optional[ProcessorConfig] = None):
        """Initialize event processor"""
        self.config = config or ProcessorConfig()
        self.clickhouse = clickhouse_manager
        self.redis = redis_manager
        
        # Processing state
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._batch_buffer: List[FrontendEvent] = []
        self._processing_tasks: List[asyncio.Task] = []
        self._running = False
        self._last_flush_time = datetime.utcnow()
        
        # Metrics
        self._processed_count = 0
        self._failed_count = 0
        self._batch_count = 0
        
        # Background tasks
        self._flush_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize the event processor"""
        try:
            # Initialize database connections
            if self.clickhouse:
                await self.clickhouse.initialize_schema()
            
            if self.redis:
                await self.redis.initialize()
            
            logger.info("Event processor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize event processor: {e}")
            return False
    
    async def start(self):
        """Start the event processor"""
        if self._running:
            logger.warning("Event processor already running")
            return
        
        self._running = True
        logger.info("Starting event processor")
        
        # Start background tasks
        self._flush_task = asyncio.create_task(self._periodic_flush())
        self._metrics_task = asyncio.create_task(self._update_metrics())
        self._cleanup_task = asyncio.create_task(self._cleanup_task_runner())
        
        # Start processing workers
        for i in range(3):  # 3 worker tasks
            task = asyncio.create_task(self._process_events_worker(f"worker-{i}"))
            self._processing_tasks.append(task)
    
    async def stop(self):
        """Stop the event processor"""
        if not self._running:
            return
            
        logger.info("Stopping event processor")
        self._running = False
        
        # Cancel background tasks
        if self._flush_task:
            self._flush_task.cancel()
        if self._metrics_task:
            self._metrics_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Cancel processing tasks
        for task in self._processing_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._processing_tasks, return_exceptions=True)
        
        # Flush remaining events
        await self._flush_events()
        
        # Close connections
        if self.clickhouse:
            self.clickhouse.close()
        if self.redis:
            await self.redis.close()
        
        logger.info("Event processor stopped")
    
    @asynccontextmanager
    async def processor_context(self):
        """Context manager for event processor lifecycle"""
        await self.initialize()
        await self.start()
        try:
            yield self
        finally:
            await self.stop()
    
    # Event Processing Methods
    
    async def process_event(self, event: FrontendEvent) -> bool:
        """Process a single event"""
        try:
            # Validate event
            if not self._validate_event(event):
                logger.warning(f"Invalid event rejected: {event.event_id}")
                return False
            
            # Check rate limiting
            if self.redis and not await self.redis.check_rate_limit(
                event.user_id, self.config.max_events_per_user_per_minute
            ):
                logger.warning(f"Rate limit exceeded for user {event.user_id}")
                return False
            
            # Apply privacy filtering
            if self.config.enable_privacy_filtering:
                event = self._apply_privacy_filters(event)
            
            # Add to processing queue
            await self._processing_queue.put(event)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process event {event.event_id}: {e}")
            return False
    
    async def process_batch(self, batch: EventBatch) -> ProcessingResult:
        """Process a batch of events"""
        start_time = datetime.utcnow()
        processed_count = 0
        failed_count = 0
        errors = []
        
        try:
            for event in batch.events:
                success = await self.process_event(event)
                if success:
                    processed_count += 1
                else:
                    failed_count += 1
                    errors.append(f"Failed to process event {event.event_id}")
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ProcessingResult(
                processed_count=processed_count,
                failed_count=failed_count,
                errors=errors,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Failed to process batch: {e}")
            return ProcessingResult(
                processed_count=processed_count,
                failed_count=len(batch.events) - processed_count,
                errors=[str(e)],
                processing_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
    
    # Background Workers
    
    async def _process_events_worker(self, worker_name: str):
        """Background worker for processing events"""
        logger.info(f"Started processing worker: {worker_name}")
        
        while self._running:
            try:
                # Get event from queue with timeout
                event = await asyncio.wait_for(
                    self._processing_queue.get(),
                    timeout=1.0
                )
                
                # Add to batch buffer
                self._batch_buffer.append(event)
                
                # Check if batch is ready
                if (len(self._batch_buffer) >= self.config.batch_size or 
                    self._should_flush_batch()):
                    await self._flush_events()
                
            except asyncio.TimeoutError:
                # No events to process, check if we should flush
                if self._batch_buffer and self._should_flush_batch():
                    await self._flush_events()
                    
            except Exception as e:
                logger.error(f"Error in processing worker {worker_name}: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"Stopped processing worker: {worker_name}")
    
    async def _periodic_flush(self):
        """Periodic flush of events"""
        while self._running:
            try:
                await asyncio.sleep(self.config.flush_interval_seconds)
                
                if self._batch_buffer:
                    await self._flush_events()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
    
    async def _update_metrics(self):
        """Update real-time metrics"""
        while self._running:
            try:
                await asyncio.sleep(30)  # Update every 30 seconds
                
                if self.clickhouse and self.redis:
                    metrics = await self.get_realtime_metrics()
                    if metrics:
                        await self.redis.set_realtime_metrics(metrics)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
    
    async def _cleanup_task_runner(self):
        """Periodic cleanup tasks"""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                if self.redis:
                    await self.redis.cleanup_expired_keys()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    # Event Processing Logic
    
    def _validate_event(self, event: FrontendEvent) -> bool:
        """Validate event data"""
        try:
            # Required fields check
            if not event.user_id or not event.session_id:
                return False
            
            if not event.event_type or not event.event_category:
                return False
            
            # Event type specific validation
            if event.event_type == EventType.CHAT_INTERACTION:
                props = event.properties
                if not props.get('thread_id') or not props.get('message_id'):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Event validation error: {e}")
            return False
    
    def _apply_privacy_filters(self, event: FrontendEvent) -> FrontendEvent:
        """Apply privacy filters to event data"""
        try:
            # Hash IP address if present
            if event.ip_address:
                event.ip_address = hashlib.sha256(event.ip_address.encode()).hexdigest()
            
            # Sanitize prompt text in chat interactions
            if event.event_type == EventType.CHAT_INTERACTION:
                props = event.properties.copy()
                if 'prompt_text' in props and props['prompt_text']:
                    props['prompt_text'] = self._sanitize_text(props['prompt_text'])
                event.properties = props
            
            # Remove sensitive user agent details
            if event.user_agent:
                event.user_agent = self._sanitize_user_agent(event.user_agent)
            
            return event
            
        except Exception as e:
            logger.error(f"Privacy filter error: {e}")
            return event
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text for privacy compliance"""
        if not text:
            return text
            
        import re
        
        # Remove email patterns
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Remove phone patterns
        text = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE]', text)
        text = re.sub(r'\b\(\d{3}\)\s*\d{3}-\d{4}\b', '[PHONE]', text)
        
        # Remove credit card patterns
        text = re.sub(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[CARD]', text)
        
        # Remove SSN patterns
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
        
        # Truncate if too long
        if len(text) > 1000:
            text = text[:1000] + '...[TRUNCATED]'
            
        return text
    
    def _sanitize_user_agent(self, user_agent: str) -> str:
        """Sanitize user agent string"""
        if not user_agent:
            return user_agent
            
        # Keep only browser family and major version
        import re
        
        # Extract browser info
        browser_patterns = [
            r'(Chrome)/(\d+)',
            r'(Firefox)/(\d+)',
            r'(Safari)/(\d+)',
            r'(Edge)/(\d+)',
            r'(Opera)/(\d+)'
        ]
        
        for pattern in browser_patterns:
            match = re.search(pattern, user_agent)
            if match:
                return f"{match.group(1)}/{match.group(2)}"
        
        return "Unknown"
    
    def _should_flush_batch(self) -> bool:
        """Check if batch should be flushed"""
        time_since_last_flush = datetime.utcnow() - self._last_flush_time
        return time_since_last_flush.total_seconds() >= self.config.flush_interval_seconds
    
    async def _flush_events(self):
        """Flush events to storage"""
        if not self._batch_buffer:
            return
        
        batch = self._batch_buffer.copy()
        self._batch_buffer.clear()
        self._last_flush_time = datetime.utcnow()
        
        success = await self._store_events_with_retry(batch)
        
        if success:
            self._processed_count += len(batch)
            self._batch_count += 1
            
            # Update hot prompts cache
            if self.redis:
                await self._update_hot_prompts(batch)
                
            logger.info(f"Flushed {len(batch)} events to storage")
        else:
            self._failed_count += len(batch)
            logger.error(f"Failed to flush {len(batch)} events")
    
    async def _store_events_with_retry(self, events: List[FrontendEvent]) -> bool:
        """Store events with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                if self.clickhouse:
                    count = await self.clickhouse.insert_events(events)
                    if count > 0:
                        return True
                
                # If ClickHouse fails, buffer to Redis
                if self.redis:
                    for event in events:
                        await self.redis.buffer_event(event.dict())
                    return True
                
                return False
                
            except Exception as e:
                logger.error(f"Storage attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds * (2 ** attempt))
        
        return False
    
    async def _update_hot_prompts(self, events: List[FrontendEvent]):
        """Update hot prompts cache with chat interactions"""
        if not self.redis:
            return
            
        try:
            for event in events:
                if event.event_type == EventType.CHAT_INTERACTION:
                    props = event.properties
                    if props.get('prompt_text'):
                        prompt_hash = hashlib.md5(
                            props['prompt_text'].encode()
                        ).hexdigest()
                        
                        prompt_data = {
                            'user_id': event.user_id,
                            'timestamp': event.timestamp.isoformat(),
                            'prompt_length': props.get('prompt_length', 0),
                            'model_used': props.get('model_used'),
                            'tokens_consumed': props.get('tokens_consumed', 0)
                        }
                        
                        await self.redis.add_hot_prompt(prompt_hash, prompt_data)
                        
        except Exception as e:
            logger.error(f"Failed to update hot prompts: {e}")
    
    # Report Generation Methods
    
    async def generate_user_activity_report(self, 
                                          user_id: Optional[str] = None,
                                          start_date: Optional[date] = None,
                                          end_date: Optional[date] = None,
                                          granularity: str = "day") -> List[Dict[str, Any]]:
        """Generate user activity report"""
        if not self.clickhouse:
            logger.error("ClickHouse not available for report generation")
            return []
        
        try:
            # Check cache first
            if self.redis:
                cache_key = f"user_activity:{user_id}:{start_date}:{end_date}:{granularity}"
                cached_report = await self.redis.get_cached_report(cache_key)
                if cached_report:
                    return cached_report
            
            # Generate report from ClickHouse
            report = await self.clickhouse.get_user_activity_report(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                granularity=granularity
            )
            
            # Cache the report
            if self.redis and report:
                cache_key = f"user_activity:{user_id}:{start_date}:{end_date}:{granularity}"
                await self.redis.cache_report(cache_key, report, ttl=300)  # 5 minute cache
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate user activity report: {e}")
            return []
    
    async def generate_prompt_analytics(self,
                                      category: Optional[str] = None,
                                      min_frequency: int = 5,
                                      time_range: str = "24h") -> List[Dict[str, Any]]:
        """Generate prompt analytics report"""
        if not self.clickhouse:
            logger.error("ClickHouse not available for report generation")
            return []
        
        try:
            # Check cache first
            if self.redis:
                cache_key = f"prompt_analytics:{category}:{min_frequency}:{time_range}"
                cached_report = await self.redis.get_cached_report(cache_key)
                if cached_report:
                    return cached_report
            
            # Generate report from ClickHouse
            report = await self.clickhouse.get_prompt_analytics_report(
                category=category,
                min_frequency=min_frequency,
                time_range=time_range
            )
            
            # Cache the report
            if self.redis and report:
                cache_key = f"prompt_analytics:{category}:{min_frequency}:{time_range}"
                await self.redis.cache_report(cache_key, report, ttl=600)  # 10 minute cache
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate prompt analytics: {e}")
            return []
    
    async def get_realtime_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics"""
        try:
            # Try Redis cache first
            if self.redis:
                cached_metrics = await self.redis.get_realtime_metrics()
                if cached_metrics:
                    return cached_metrics
            
            # Fallback to ClickHouse
            if self.clickhouse:
                metrics = await self.clickhouse.get_realtime_metrics()
                
                # Add processor metrics
                metrics.update({
                    'processor_events_processed': self._processed_count,
                    'processor_events_failed': self._failed_count,
                    'processor_batches_processed': self._batch_count,
                    'processor_queue_size': self._processing_queue.qsize(),
                    'processor_buffer_size': len(self._batch_buffer)
                })
                
                return metrics
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get realtime metrics: {e}")
            return {}
    
    # Health and Status
    
    async def health_check(self) -> Dict[str, Any]:
        """Get health status of event processor"""
        status = {
            'running': self._running,
            'queue_size': self._processing_queue.qsize(),
            'buffer_size': len(self._batch_buffer),
            'processed_count': self._processed_count,
            'failed_count': self._failed_count,
            'batch_count': self._batch_count,
            'clickhouse_healthy': False,
            'redis_healthy': False
        }
        
        if self.clickhouse:
            status['clickhouse_healthy'] = await self.clickhouse.health_check()
        
        if self.redis:
            status['redis_healthy'] = await self.redis.health_check()
        
        return status
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        return {
            'events_processed': self._processed_count,
            'events_failed': self._failed_count,
            'batches_processed': self._batch_count,
            'current_queue_size': self._processing_queue.qsize(),
            'current_buffer_size': len(self._batch_buffer),
            'running': self._running,
            'worker_count': len(self._processing_tasks)
        }