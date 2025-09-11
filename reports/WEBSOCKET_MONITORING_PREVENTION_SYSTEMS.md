# WebSocket Monitoring and Prevention Systems

## Overview

Comprehensive monitoring and prevention systems that provide real-time visibility into WebSocket resource usage, predict potential issues before they occur, and automatically take corrective actions to maintain system stability.

## Business Value Justification (BVJ)
- **Segment**: ALL (Infrastructure supporting Free → Enterprise)
- **Business Goal**: Zero-downtime WebSocket service with proactive issue prevention
- **Value Impact**: Prevents chat service interruptions that block user engagement
- **Strategic Impact**: Enables enterprise-grade reliability and SLA compliance

## Monitoring Architecture

### Real-Time Metrics Dashboard
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   WebSocket     │───▶│   Metrics        │───▶│   Dashboard     │
│   Operations    │    │   Collector      │    │   & Alerts      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Resource      │    │   Time Series    │    │   Automated     │
│   Tracking      │    │   Database       │    │   Response      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Component 1: Real-Time Resource Monitor

### Implementation
```python
class WebSocketResourceMonitor:
    """Comprehensive real-time monitoring for WebSocket resources"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.prediction_engine = ResourcePredictionEngine()
        self.auto_responder = AutomatedResponseSystem()
        
        # Monitoring intervals
        self.monitoring_intervals = {
            'real_time': 5,      # 5 seconds
            'frequent': 30,      # 30 seconds  
            'regular': 300,      # 5 minutes
            'background': 1800   # 30 minutes
        }
        
        # Start monitoring tasks
        asyncio.create_task(self._start_monitoring_tasks())
    
    async def _start_monitoring_tasks(self):
        """Start all monitoring background tasks"""
        tasks = [
            asyncio.create_task(self._real_time_monitoring()),
            asyncio.create_task(self._frequent_health_checks()),
            asyncio.create_task(self._regular_resource_analysis()),
            asyncio.create_task(self._background_trend_analysis())
        ]
        
        # Wait for all tasks to complete (never in normal operation)
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _real_time_monitoring(self):
        """Real-time monitoring every 5 seconds"""
        while True:
            try:
                await asyncio.sleep(self.monitoring_intervals['real_time'])
                
                # Get current system state
                system_snapshot = await self._capture_system_snapshot()
                
                # Store metrics
                await self.metrics_collector.record_system_snapshot(system_snapshot)
                
                # Check for immediate alerts
                await self._check_immediate_alerts(system_snapshot)
                
                # Update predictive models
                await self.prediction_engine.update_with_snapshot(system_snapshot)
                
            except Exception as e:
                logger.error(f"Real-time monitoring error: {e}")
                await asyncio.sleep(30)  # Back off on errors

    async def _capture_system_snapshot(self) -> SystemSnapshot:
        """Capture comprehensive system state snapshot"""
        factory = WebSocketManagerFactory()
        
        # Get per-user manager counts
        user_manager_counts = await factory.get_all_user_manager_counts()
        
        # Calculate system-wide metrics
        total_managers = sum(user_manager_counts.values())
        max_managers_reached = sum(1 for count in user_manager_counts.values() if count >= 20)
        avg_managers_per_user = total_managers / max(1, len(user_manager_counts))
        
        # Get connection health metrics
        connection_health = await self._assess_connection_health()
        
        # Get resource utilization
        resource_utilization = await self._get_resource_utilization()
        
        return SystemSnapshot(
            timestamp=datetime.utcnow(),
            total_managers=total_managers,
            total_users=len(user_manager_counts),
            max_managers_reached=max_managers_reached,
            avg_managers_per_user=avg_managers_per_user,
            user_manager_counts=user_manager_counts,
            connection_health=connection_health,
            resource_utilization=resource_utilization
        )

    async def _assess_connection_health(self) -> ConnectionHealthMetrics:
        """Assess overall connection health"""
        factory = WebSocketManagerFactory()
        
        # Test connection responsiveness
        active_connections = await factory.get_active_connection_count()
        healthy_connections = await factory.get_healthy_connection_count()
        
        # Calculate health ratios
        health_ratio = healthy_connections / max(1, active_connections)
        
        # Get connection error rates
        error_rates = await self._get_connection_error_rates()
        
        return ConnectionHealthMetrics(
            active_connections=active_connections,
            healthy_connections=healthy_connections,
            health_ratio=health_ratio,
            error_rates=error_rates,
            avg_response_time=await self._measure_avg_response_time()
        )

    async def _check_immediate_alerts(self, snapshot: SystemSnapshot):
        """Check for conditions requiring immediate alerts"""
        
        # Critical: Users hitting manager limits
        if snapshot.max_managers_reached > 0:
            await self.alert_manager.trigger_alert(
                severity='CRITICAL',
                message=f"{snapshot.max_managers_reached} users hit 20-manager limit",
                snapshot=snapshot,
                suggested_action="Immediate emergency cleanup required"
            )
        
        # Warning: High system-wide manager count
        if snapshot.total_managers > 200:  # Example threshold
            await self.alert_manager.trigger_alert(
                severity='WARNING',
                message=f"High system-wide manager count: {snapshot.total_managers}",
                snapshot=snapshot,
                suggested_action="Consider proactive cleanup"
            )
        
        # Warning: Poor connection health
        if snapshot.connection_health.health_ratio < 0.8:
            await self.alert_manager.trigger_alert(
                severity='WARNING',
                message=f"Poor connection health: {snapshot.connection_health.health_ratio:.1%}",
                snapshot=snapshot,
                suggested_action="Investigate connection issues"
            )

@dataclass
class SystemSnapshot:
    timestamp: datetime
    total_managers: int
    total_users: int
    max_managers_reached: int
    avg_managers_per_user: float
    user_manager_counts: Dict[str, int]
    connection_health: 'ConnectionHealthMetrics'
    resource_utilization: 'ResourceUtilizationMetrics'

@dataclass  
class ConnectionHealthMetrics:
    active_connections: int
    healthy_connections: int
    health_ratio: float
    error_rates: Dict[str, float]
    avg_response_time: float

@dataclass
class ResourceUtilizationMetrics:
    memory_usage_mb: float
    cpu_usage_percent: float
    network_connections: int
    disk_usage_mb: float
```

## Component 2: Predictive Analysis Engine

### Implementation
```python
class ResourcePredictionEngine:
    """Predict resource usage patterns and potential issues"""
    
    def __init__(self):
        self.historical_data: List[SystemSnapshot] = []
        self.prediction_models = {
            'manager_growth': ManagerGrowthPredictor(),
            'user_behavior': UserBehaviorPredictor(),
            'system_load': SystemLoadPredictor()
        }
        self.max_historical_snapshots = 10000  # ~14 hours at 5-second intervals
    
    async def update_with_snapshot(self, snapshot: SystemSnapshot):
        """Update prediction models with new data"""
        self.historical_data.append(snapshot)
        
        # Maintain sliding window of historical data
        if len(self.historical_data) > self.max_historical_snapshots:
            self.historical_data.pop(0)
        
        # Update all prediction models
        for model_name, model in self.prediction_models.items():
            try:
                await model.update(snapshot, self.historical_data)
            except Exception as e:
                logger.error(f"Error updating {model_name} model: {e}")
    
    async def predict_resource_crisis(self, time_horizon_minutes: int = 30) -> ResourceCrisisPrediction:
        """Predict likelihood of resource crisis in the next time period"""
        
        predictions = {}
        for model_name, model in self.prediction_models.items():
            predictions[model_name] = await model.predict(time_horizon_minutes)
        
        # Aggregate predictions
        crisis_probability = self._calculate_crisis_probability(predictions)
        
        # Identify most likely crisis scenarios
        crisis_scenarios = self._identify_crisis_scenarios(predictions)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(crisis_scenarios)
        
        return ResourceCrisisPrediction(
            time_horizon_minutes=time_horizon_minutes,
            crisis_probability=crisis_probability,
            crisis_scenarios=crisis_scenarios,
            recommendations=recommendations,
            confidence=self._calculate_confidence(predictions)
        )

    def _calculate_crisis_probability(self, predictions: Dict[str, Any]) -> float:
        """Calculate overall crisis probability from individual model predictions"""
        probabilities = []
        
        # Manager growth model
        if 'manager_growth' in predictions:
            growth_pred = predictions['manager_growth']
            if growth_pred.get('projected_managers', 0) > 300:  # System threshold
                probabilities.append(0.8)
            elif growth_pred.get('projected_managers', 0) > 200:
                probabilities.append(0.4)
            else:
                probabilities.append(0.1)
        
        # User behavior model
        if 'user_behavior' in predictions:
            behavior_pred = predictions['user_behavior']
            if behavior_pred.get('peak_concurrent_users', 0) > 50:
                probabilities.append(0.6)
            else:
                probabilities.append(0.2)
        
        # System load model
        if 'system_load' in predictions:
            load_pred = predictions['system_load']
            if load_pred.get('cpu_utilization', 0) > 80:
                probabilities.append(0.7)
            else:
                probabilities.append(0.3)
        
        # Use weighted average
        if not probabilities:
            return 0.0
        
        return sum(probabilities) / len(probabilities)

class ManagerGrowthPredictor:
    """Predict manager count growth trends"""
    
    async def update(self, snapshot: SystemSnapshot, historical_data: List[SystemSnapshot]):
        """Update model with new data point"""
        self.current_snapshot = snapshot
        self.recent_history = historical_data[-100:]  # Last 100 snapshots (8+ minutes)
    
    async def predict(self, time_horizon_minutes: int) -> Dict[str, Any]:
        """Predict manager growth for time horizon"""
        if len(self.recent_history) < 10:
            return {'projected_managers': self.current_snapshot.total_managers, 'confidence': 0.1}
        
        # Calculate growth rate (managers per minute)
        time_span_minutes = len(self.recent_history) * 5 / 60  # 5-second intervals
        manager_growth = (self.current_snapshot.total_managers - 
                         self.recent_history[0].total_managers)
        growth_rate = manager_growth / max(1, time_span_minutes)
        
        # Project forward
        projected_managers = self.current_snapshot.total_managers + (growth_rate * time_horizon_minutes)
        
        # Calculate confidence based on trend consistency
        confidence = self._calculate_trend_confidence()
        
        return {
            'projected_managers': max(0, int(projected_managers)),
            'growth_rate_per_minute': growth_rate,
            'confidence': confidence,
            'trend': 'increasing' if growth_rate > 0.1 else 'decreasing' if growth_rate < -0.1 else 'stable'
        }
    
    def _calculate_trend_confidence(self) -> float:
        """Calculate confidence in the growth trend"""
        if len(self.recent_history) < 5:
            return 0.1
        
        # Look at recent growth rates
        growth_rates = []
        for i in range(1, min(10, len(self.recent_history))):
            prev_count = self.recent_history[-i-1].total_managers
            curr_count = self.recent_history[-i].total_managers
            growth_rates.append(curr_count - prev_count)
        
        if not growth_rates:
            return 0.1
        
        # Calculate consistency (lower variance = higher confidence)
        import statistics
        try:
            variance = statistics.variance(growth_rates)
            # Convert variance to confidence (0-1)
            confidence = max(0.1, min(1.0, 1.0 / (1.0 + variance)))
            return confidence
        except statistics.StatisticsError:
            return 0.1

@dataclass
class ResourceCrisisPrediction:
    time_horizon_minutes: int
    crisis_probability: float
    crisis_scenarios: List[Dict[str, Any]]
    recommendations: List[str]
    confidence: float
```

## Component 3: Automated Response System

### Implementation  
```python
class AutomatedResponseSystem:
    """Automatically respond to predicted and detected issues"""
    
    def __init__(self):
        self.response_strategies = {
            'high_manager_count': HighManagerCountResponse(),
            'connection_health_degradation': ConnectionHealthResponse(),
            'predicted_resource_crisis': PredictiveCrisisResponse(),
            'user_quota_exceeded': UserQuotaResponse()
        }
        self.response_history: List[ResponseEvent] = []
        
    async def handle_alert(self, alert: Alert) -> ResponseResult:
        """Handle an alert with appropriate automated response"""
        logger.info(f"Automated response triggered for alert: {alert.severity} - {alert.message}")
        
        # Determine response strategy
        strategy_name = self._determine_strategy(alert)
        
        if strategy_name not in self.response_strategies:
            logger.warning(f"No automated response strategy for: {strategy_name}")
            return ResponseResult(success=False, message="No strategy available")
        
        strategy = self.response_strategies[strategy_name]
        
        try:
            # Execute response strategy
            result = await strategy.execute(alert)
            
            # Record response event
            response_event = ResponseEvent(
                timestamp=datetime.utcnow(),
                alert=alert,
                strategy_name=strategy_name,
                result=result
            )
            self.response_history.append(response_event)
            
            logger.info(f"Automated response completed: {strategy_name} - {result.message}")
            return result
            
        except Exception as e:
            logger.error(f"Automated response failed: {strategy_name} - {e}")
            return ResponseResult(success=False, message=f"Strategy execution failed: {e}")

    def _determine_strategy(self, alert: Alert) -> str:
        """Determine which response strategy to use"""
        if "manager limit" in alert.message.lower():
            return 'high_manager_count'
        elif "connection health" in alert.message.lower():
            return 'connection_health_degradation'
        elif "crisis probability" in alert.message.lower():
            return 'predicted_resource_crisis'
        elif "quota" in alert.message.lower():
            return 'user_quota_exceeded'
        
        return 'default'

class HighManagerCountResponse:
    """Response strategy for high manager count scenarios"""
    
    async def execute(self, alert: Alert) -> ResponseResult:
        """Execute high manager count response"""
        factory = WebSocketManagerFactory()
        
        # Step 1: Identify users with highest manager counts
        user_counts = alert.snapshot.user_manager_counts
        high_usage_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        cleaned_managers = 0
        
        # Step 2: Perform targeted cleanup for high-usage users
        for user_id, count in high_usage_users:
            if count >= 15:  # Focus on users with 15+ managers
                try:
                    user_cleaned = await factory._emergency_cleanup_with_timeout(user_id)
                    cleaned_managers += user_cleaned
                    logger.info(f"Emergency cleanup for {user_id}: {user_cleaned} managers cleaned")
                except Exception as e:
                    logger.error(f"Emergency cleanup failed for {user_id}: {e}")
        
        # Step 3: System-wide cleanup if still high
        if alert.snapshot.total_managers - cleaned_managers > 200:
            try:
                additional_cleaned = await factory._system_wide_cleanup()
                cleaned_managers += additional_cleaned
            except Exception as e:
                logger.error(f"System-wide cleanup failed: {e}")
        
        return ResponseResult(
            success=cleaned_managers > 0,
            message=f"Cleaned {cleaned_managers} managers across {len(high_usage_users)} users",
            actions_taken=[f"Emergency cleanup for users: {[user for user, _ in high_usage_users]}"],
            metrics={'managers_cleaned': cleaned_managers}
        )

class PredictiveCrisisResponse:
    """Response strategy for predicted resource crises"""
    
    async def execute(self, alert: Alert) -> ResponseResult:
        """Execute predictive crisis prevention"""
        prediction = alert.context.get('prediction')
        if not prediction:
            return ResponseResult(success=False, message="No prediction data available")
        
        actions_taken = []
        
        # Proactive cleanup based on prediction
        if prediction.crisis_probability > 0.7:
            factory = WebSocketManagerFactory()
            
            # Reduce cleanup thresholds temporarily
            original_threshold = factory.CLEANUP_TRIGGER_THRESHOLD
            factory.CLEANUP_TRIGGER_THRESHOLD = 0.4  # More aggressive cleanup
            
            try:
                # Trigger proactive cleanup for all users
                cleanup_count = await self._proactive_system_cleanup(factory)
                actions_taken.append(f"Proactive cleanup: {cleanup_count} managers")
                
                # Reduce background cleanup interval temporarily
                factory.BACKGROUND_CLEANUP_INTERVAL = 15  # 15 seconds instead of normal
                actions_taken.append("Increased cleanup frequency")
                
            finally:
                # Restore original threshold after 10 minutes
                asyncio.create_task(self._restore_threshold(factory, original_threshold, 600))
        
        return ResponseResult(
            success=len(actions_taken) > 0,
            message=f"Proactive crisis prevention: {len(actions_taken)} actions taken",
            actions_taken=actions_taken
        )
    
    async def _proactive_system_cleanup(self, factory: WebSocketManagerFactory) -> int:
        """Perform proactive cleanup across the system"""
        total_cleaned = 0
        
        # Get all users with managers
        all_users = await factory._get_active_users()
        
        for user_id in all_users:
            try:
                # Clean idle and disconnected managers proactively
                user_cleaned = 0
                user_cleaned += await factory._cleanup_disconnected_managers(user_id)
                user_cleaned += await factory._cleanup_idle_managers(user_id, max_idle_time=120)  # 2 minutes
                
                total_cleaned += user_cleaned
                if user_cleaned > 0:
                    logger.debug(f"Proactive cleanup for {user_id}: {user_cleaned} managers")
                    
            except Exception as e:
                logger.warning(f"Proactive cleanup failed for {user_id}: {e}")
        
        return total_cleaned

@dataclass
class ResponseResult:
    success: bool
    message: str
    actions_taken: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ResponseEvent:
    timestamp: datetime
    alert: 'Alert'
    strategy_name: str
    result: ResponseResult
```

## Component 4: Alert Management System

### Implementation
```python
class AlertManager:
    """Manage alerts with deduplication, escalation, and notification"""
    
    def __init__(self):
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_channels = [
            LogNotificationChannel(),
            EmailNotificationChannel(),  # For production
            SlackNotificationChannel(),  # For production
        ]
        self.escalation_rules = EscalationRules()
    
    async def trigger_alert(self, severity: str, message: str, 
                          snapshot: SystemSnapshot = None,
                          suggested_action: str = None,
                          context: Dict[str, Any] = None) -> Alert:
        """Trigger a new alert with deduplication"""
        
        alert_key = self._generate_alert_key(severity, message)
        
        # Check for existing similar alert (deduplication)
        if alert_key in self.active_alerts:
            existing_alert = self.active_alerts[alert_key]
            existing_alert.occurrence_count += 1
            existing_alert.last_seen = datetime.utcnow()
            logger.debug(f"Deduplicated alert: {message} (count: {existing_alert.occurrence_count})")
            return existing_alert
        
        # Create new alert
        alert = Alert(
            id=str(uuid.uuid4()),
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            snapshot=snapshot,
            suggested_action=suggested_action,
            context=context or {},
            status=AlertStatus.ACTIVE
        )
        
        # Store alert
        self.active_alerts[alert_key] = alert
        self.alert_history.append(alert)
        
        # Send notifications
        await self._send_notifications(alert)
        
        # Check escalation rules
        await self._check_escalation(alert)
        
        logger.info(f"New {severity} alert: {message}")
        return alert
    
    def _generate_alert_key(self, severity: str, message: str) -> str:
        """Generate key for alert deduplication"""
        # Use first few words of message for grouping similar alerts
        message_key = ' '.join(message.split()[:5])
        return f"{severity}:{message_key}"
    
    async def _send_notifications(self, alert: Alert):
        """Send notifications through all configured channels"""
        for channel in self.notification_channels:
            try:
                await channel.send_notification(alert)
            except Exception as e:
                logger.error(f"Failed to send notification via {channel.__class__.__name__}: {e}")
    
    async def resolve_alert(self, alert_id: str, resolution_message: str = None):
        """Resolve an active alert"""
        alert = self._find_alert_by_id(alert_id)
        if alert:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            alert.resolution_message = resolution_message
            
            # Remove from active alerts
            alert_key = self._generate_alert_key(alert.severity, alert.message)
            if alert_key in self.active_alerts:
                del self.active_alerts[alert_key]
            
            logger.info(f"Alert resolved: {alert.message}")

@dataclass
class Alert:
    id: str
    severity: str  # 'INFO', 'WARNING', 'CRITICAL'
    message: str
    timestamp: datetime
    snapshot: Optional[SystemSnapshot] = None
    suggested_action: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = 'ACTIVE'
    occurrence_count: int = 1
    last_seen: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution_message: Optional[str] = None

class LogNotificationChannel:
    """Send notifications to structured logs"""
    
    async def send_notification(self, alert: Alert):
        """Send alert to logs"""
        log_level = {
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'CRITICAL': logging.ERROR
        }.get(alert.severity, logging.INFO)
        
        structured_log = {
            'alert_id': alert.id,
            'severity': alert.severity,
            'message': alert.message,
            'suggested_action': alert.suggested_action,
            'occurrence_count': alert.occurrence_count,
            'snapshot': {
                'total_managers': alert.snapshot.total_managers if alert.snapshot else None,
                'total_users': alert.snapshot.total_users if alert.snapshot else None
            }
        }
        
        logger.log(log_level, f"WEBSOCKET_ALERT: {json.dumps(structured_log)}")
```

## Component 5: Health Check and Status Dashboard

### Implementation
```python
class WebSocketHealthChecker:
    """Comprehensive health checking for WebSocket system"""
    
    def __init__(self):
        self.health_checks = {
            'manager_factory': self._check_manager_factory,
            'resource_usage': self._check_resource_usage,
            'connection_health': self._check_connection_health,
            'cleanup_effectiveness': self._check_cleanup_effectiveness,
            'system_performance': self._check_system_performance
        }
    
    async def get_overall_health(self) -> SystemHealth:
        """Get overall system health status"""
        health_results = {}
        
        for check_name, check_func in self.health_checks.items():
            try:
                result = await check_func()
                health_results[check_name] = result
            except Exception as e:
                health_results[check_name] = HealthResult(
                    status='UNHEALTHY',
                    message=f"Health check failed: {e}",
                    metrics={}
                )
        
        # Calculate overall health
        overall_status = self._calculate_overall_status(health_results)
        
        return SystemHealth(
            overall_status=overall_status,
            timestamp=datetime.utcnow(),
            health_results=health_results,
            summary=self._generate_health_summary(health_results)
        )
    
    async def _check_manager_factory(self) -> HealthResult:
        """Check WebSocket manager factory health"""
        factory = WebSocketManagerFactory()
        
        try:
            # Test basic functionality
            test_user_id = "health-check-user"
            test_context = UserExecutionContext.from_websocket_request(test_user_id)
            
            # Try creating and cleaning up a test manager
            manager = await factory.create_manager(test_context)
            cleanup_success = await factory.cleanup_manager_by_context(test_context)
            
            metrics = {
                'factory_responsive': True,
                'test_manager_created': manager is not None,
                'test_cleanup_successful': cleanup_success
            }
            
            if manager and cleanup_success:
                return HealthResult('HEALTHY', 'Manager factory working correctly', metrics)
            else:
                return HealthResult('DEGRADED', 'Manager factory partially working', metrics)
                
        except Exception as e:
            return HealthResult('UNHEALTHY', f'Manager factory error: {e}', {'error': str(e)})
    
    async def _check_resource_usage(self) -> HealthResult:
        """Check current resource usage levels"""
        factory = WebSocketManagerFactory()
        
        user_counts = await factory.get_all_user_manager_counts()
        total_managers = sum(user_counts.values())
        users_at_limit = sum(1 for count in user_counts.values() if count >= 20)
        
        metrics = {
            'total_managers': total_managers,
            'total_users': len(user_counts),
            'users_at_limit': users_at_limit,
            'avg_managers_per_user': total_managers / max(1, len(user_counts))
        }
        
        if users_at_limit > 0:
            return HealthResult('UNHEALTHY', f'{users_at_limit} users at manager limit', metrics)
        elif total_managers > 300:
            return HealthResult('DEGRADED', f'High total manager count: {total_managers}', metrics)
        else:
            return HealthResult('HEALTHY', 'Resource usage within normal limits', metrics)

@dataclass
class HealthResult:
    status: str  # 'HEALTHY', 'DEGRADED', 'UNHEALTHY'
    message: str
    metrics: Dict[str, Any]

@dataclass  
class SystemHealth:
    overall_status: str
    timestamp: datetime
    health_results: Dict[str, HealthResult]
    summary: str
```

## Component 6: Configuration and Deployment

### Production Configuration
```python
# Production monitoring configuration
MONITORING_CONFIG = {
    'real_time_interval': 5,       # 5 seconds
    'alert_thresholds': {
        'manager_count_warning': 200,
        'manager_count_critical': 300,
        'users_at_limit_warning': 1,
        'users_at_limit_critical': 3,
        'connection_health_warning': 0.8,
        'connection_health_critical': 0.6
    },
    'prediction_horizon_minutes': 30,
    'crisis_probability_threshold': 0.7,
    'automated_response_enabled': True,
    'notification_channels': ['log', 'email', 'slack']
}

# Staging configuration (more aggressive monitoring)  
STAGING_MONITORING_CONFIG = {
    'real_time_interval': 3,       # 3 seconds
    'alert_thresholds': {
        'manager_count_warning': 50,
        'manager_count_critical': 100,
        'users_at_limit_warning': 1,
        'users_at_limit_critical': 2
    },
    'automated_response_enabled': True,
    'notification_channels': ['log']
}
```

## Expected Benefits

### Proactive Issue Prevention
- **95% reduction** in resource limit incidents
- **Early warning** 15-30 minutes before crises
- **Automated resolution** of 80% of common issues

### Operational Visibility
- **Real-time dashboards** showing system health
- **Predictive analytics** for capacity planning
- **Alert fatigue reduction** through intelligent deduplication

### Business Impact
- **Zero-downtime** WebSocket service
- **Enterprise SLA compliance** (99.9% uptime)
- **Reduced operational costs** through automation

This comprehensive monitoring and prevention system provides the observability and automation needed to maintain stable WebSocket resource management at enterprise scale, preventing the resource leak issues from impacting users and enabling proactive capacity management.

---

**Implementation Priority**: HIGH  
**Implementation Timeline**: 1-2 weeks  
**Dependencies**: Requires metrics infrastructure  
**Business Impact**: Critical for enterprise reliability