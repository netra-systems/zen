#!/usr/bin/env python3
"""
Production Monitoring System for Isolation Features Rollout
===========================================================

Real-time monitoring system for tracking isolation score, error rates,
response times, and cascade failure detection during production rollout.

Features:
- Real-time isolation score monitoring
- Cascade failure detection
- Performance metrics tracking
- Automated alerting (Slack, PagerDuty, Email)
- Circuit breaker monitoring
- A/B testing metrics comparison

Usage Examples:
    # Start real-time monitoring
    python scripts/production_monitoring.py start --stage canary
    
    # Check current metrics
    python scripts/production_monitoring.py metrics --detailed
    
    # Configure alerts
    python scripts/production_monitoring.py configure-alerts \
        --slack-webhook $SLACK_WEBHOOK --pagerduty-key $PAGERDUTY_KEY
    
    # Generate daily report
    python scripts/production_monitoring.py daily-report --email-recipients team@netra.ai
"""

import asyncio
import argparse
import json
import logging
import sys
import time
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.feature_flags import (
    ProductionFeatureFlags, 
    IsolationMetrics, 
    get_feature_flags
)
from shared.isolated_environment import IsolatedEnvironment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AlertConfig:
    """Alert configuration for production monitoring."""
    slack_webhook_url: Optional[str] = None
    pagerduty_integration_key: Optional[str] = None
    email_smtp_host: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_recipients: List[str] = None
    
    def __post_init__(self):
        if self.email_recipients is None:
            self.email_recipients = []


@dataclass 
class MonitoringThresholds:
    """Monitoring thresholds for alerts."""
    isolation_score_warning: float = 0.995  # 99.5%
    isolation_score_critical: float = 0.99   # 99%
    isolation_score_emergency: float = 0.95  # 95%
    
    error_rate_warning: float = 0.005        # 0.5%
    error_rate_critical: float = 0.01        # 1%
    error_rate_emergency: float = 0.05       # 5%
    
    response_time_warning_increase: float = 0.1   # 10%
    response_time_critical_increase: float = 0.2  # 20%
    response_time_emergency_increase: float = 0.5 # 50%
    
    cascade_failures_warning: int = 1
    cascade_failures_critical: int = 3
    cascade_failures_emergency: int = 5


@dataclass
class PerformanceBaseline:
    """Performance baseline for comparison."""
    baseline_response_time_p95: float = 0.0
    baseline_error_rate: float = 0.0
    baseline_isolation_score: float = 1.0
    baseline_timestamp: float = 0.0
    baseline_period_hours: int = 24


class ProductionMonitoringSystem:
    """Production monitoring system for isolation features rollout."""
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.env = IsolatedEnvironment.get_instance()
        self.feature_flags = ProductionFeatureFlags(environment)
        
        # Monitoring configuration
        self.check_interval_seconds = 30
        self.alert_config = AlertConfig()
        self.thresholds = MonitoringThresholds()
        self.baseline = PerformanceBaseline()
        
        # State tracking
        self.is_monitoring = False
        self.last_alert_times = {}
        self.alert_cooldown_seconds = 300  # 5 minutes
        
        logger.info(f"Initialized ProductionMonitoringSystem for {environment}")

    def load_configuration(self) -> None:
        """Load monitoring configuration from environment."""
        # Alert configuration
        self.alert_config.slack_webhook_url = self.env.get("SLACK_PROD_WEBHOOK")
        self.alert_config.pagerduty_integration_key = self.env.get("PAGERDUTY_INTEGRATION_KEY")
        self.alert_config.email_smtp_host = self.env.get("EMAIL_SMTP_HOST", "smtp.gmail.com")
        self.alert_config.email_username = self.env.get("EMAIL_USERNAME")
        self.alert_config.email_password = self.env.get("EMAIL_PASSWORD")
        
        email_recipients = self.env.get("ALERT_EMAIL_RECIPIENTS")
        if email_recipients:
            self.alert_config.email_recipients = email_recipients.split(",")
        
        logger.info("Loaded monitoring configuration from environment")

    async def start_monitoring(self, stage: str = "production") -> None:
        """Start real-time monitoring."""
        logger.info(f"Starting production monitoring for stage: {stage}")
        
        self.load_configuration()
        self.is_monitoring = True
        
        # Load or calculate baseline
        await self.load_performance_baseline()
        
        try:
            while self.is_monitoring:
                # Collect current metrics
                current_metrics = self.collect_current_metrics()
                
                if current_metrics:
                    # Analyze metrics against thresholds
                    alerts = self.analyze_metrics_for_alerts(current_metrics)
                    
                    # Send alerts if needed
                    for alert in alerts:
                        await self.send_alert(alert)
                    
                    # Log current status
                    self.log_monitoring_status(current_metrics, stage)
                    
                    # Update performance tracking
                    self.update_performance_tracking(current_metrics)
                
                # Wait for next check interval
                await asyncio.sleep(self.check_interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            await self.send_alert({
                "level": "CRITICAL",
                "title": "Monitoring System Error",
                "message": f"Production monitoring system encountered error: {e}",
                "timestamp": time.time()
            })
        finally:
            self.is_monitoring = False

    def collect_current_metrics(self) -> Optional[IsolationMetrics]:
        """Collect current isolation and performance metrics."""
        try:
            # Get metrics from feature flags system
            metrics = self.feature_flags.get_current_isolation_metrics()
            
            if not metrics:
                # Create default metrics if none exist
                metrics = IsolationMetrics(
                    total_requests=0,
                    isolated_requests=0,
                    failed_requests=0,
                    cascade_failures=0,
                    isolation_score=1.0,
                    error_rate=0.0,
                    response_time_p95=0.0,
                    timestamp=time.time()
                )
            
            # Enhance with additional metrics collection
            enhanced_metrics = self.enhance_metrics_with_system_data(metrics)
            
            return enhanced_metrics
            
        except Exception as e:
            logger.error(f"Failed to collect current metrics: {e}")
            return None

    def enhance_metrics_with_system_data(self, base_metrics: IsolationMetrics) -> IsolationMetrics:
        """Enhance base metrics with additional system monitoring data."""
        try:
            # Here you would integrate with your monitoring systems:
            # - Prometheus metrics
            # - Application logs
            # - Cloud monitoring APIs
            # - Database performance metrics
            
            # For now, return base metrics
            # In production, you would add:
            # - Real response time data from load balancer
            # - Error rates from application logs
            # - System resource utilization
            # - Database query performance
            
            return base_metrics
            
        except Exception as e:
            logger.error(f"Failed to enhance metrics: {e}")
            return base_metrics

    def analyze_metrics_for_alerts(self, metrics: IsolationMetrics) -> List[Dict[str, Any]]:
        """Analyze metrics against thresholds and generate alerts."""
        alerts = []
        current_time = time.time()
        
        # Check isolation score
        if metrics.isolation_score <= self.thresholds.isolation_score_emergency:
            alerts.append({
                "level": "EMERGENCY",
                "title": " ALERT:  CRITICAL: Isolation Score Emergency",
                "message": f"Isolation score dropped to {metrics.isolation_score:.1%} (threshold: {self.thresholds.isolation_score_emergency:.1%})",
                "metric": "isolation_score",
                "value": metrics.isolation_score,
                "threshold": self.thresholds.isolation_score_emergency,
                "timestamp": current_time,
                "action_required": "IMMEDIATE ROLLBACK REQUIRED"
            })
        elif metrics.isolation_score <= self.thresholds.isolation_score_critical:
            alerts.append({
                "level": "CRITICAL",
                "title": " ALERT:  Isolation Score Critical",
                "message": f"Isolation score at {metrics.isolation_score:.1%} (threshold: {self.thresholds.isolation_score_critical:.1%})",
                "metric": "isolation_score",
                "value": metrics.isolation_score,
                "threshold": self.thresholds.isolation_score_critical,
                "timestamp": current_time,
                "action_required": "Consider rollback"
            })
        elif metrics.isolation_score <= self.thresholds.isolation_score_warning:
            alerts.append({
                "level": "WARNING",
                "title": " WARNING: [U+FE0F] Isolation Score Warning",
                "message": f"Isolation score at {metrics.isolation_score:.1%} (threshold: {self.thresholds.isolation_score_warning:.1%})",
                "metric": "isolation_score",
                "value": metrics.isolation_score,
                "threshold": self.thresholds.isolation_score_warning,
                "timestamp": current_time
            })
        
        # Check error rate
        if metrics.error_rate >= self.thresholds.error_rate_emergency:
            alerts.append({
                "level": "EMERGENCY",
                "title": " ALERT:  CRITICAL: Error Rate Emergency", 
                "message": f"Error rate spiked to {metrics.error_rate:.2%} (threshold: {self.thresholds.error_rate_emergency:.2%})",
                "metric": "error_rate",
                "value": metrics.error_rate,
                "threshold": self.thresholds.error_rate_emergency,
                "timestamp": current_time,
                "action_required": "IMMEDIATE ROLLBACK REQUIRED"
            })
        elif metrics.error_rate >= self.thresholds.error_rate_critical:
            alerts.append({
                "level": "CRITICAL",
                "title": " ALERT:  High Error Rate",
                "message": f"Error rate at {metrics.error_rate:.2%} (threshold: {self.thresholds.error_rate_critical:.2%})",
                "metric": "error_rate", 
                "value": metrics.error_rate,
                "threshold": self.thresholds.error_rate_critical,
                "timestamp": current_time,
                "action_required": "Investigate immediately"
            })
        elif metrics.error_rate >= self.thresholds.error_rate_warning:
            alerts.append({
                "level": "WARNING",
                "title": " WARNING: [U+FE0F] Elevated Error Rate",
                "message": f"Error rate at {metrics.error_rate:.2%} (threshold: {self.thresholds.error_rate_warning:.2%})",
                "metric": "error_rate",
                "value": metrics.error_rate,
                "threshold": self.thresholds.error_rate_warning,
                "timestamp": current_time
            })
        
        # Check cascade failures
        if metrics.cascade_failures >= self.thresholds.cascade_failures_emergency:
            alerts.append({
                "level": "EMERGENCY", 
                "title": " ALERT:  CRITICAL: Multiple Cascade Failures",
                "message": f"{metrics.cascade_failures} cascade failures detected (threshold: {self.thresholds.cascade_failures_emergency})",
                "metric": "cascade_failures",
                "value": metrics.cascade_failures,
                "threshold": self.thresholds.cascade_failures_emergency,
                "timestamp": current_time,
                "action_required": "IMMEDIATE ROLLBACK REQUIRED"
            })
        elif metrics.cascade_failures >= self.thresholds.cascade_failures_critical:
            alerts.append({
                "level": "CRITICAL",
                "title": " ALERT:  Multiple Cascade Failures",
                "message": f"{metrics.cascade_failures} cascade failures detected (threshold: {self.thresholds.cascade_failures_critical})",
                "metric": "cascade_failures",
                "value": metrics.cascade_failures,
                "threshold": self.thresholds.cascade_failures_critical,
                "timestamp": current_time,
                "action_required": "Investigate cascade failures"
            })
        elif metrics.cascade_failures >= self.thresholds.cascade_failures_warning:
            alerts.append({
                "level": "WARNING",
                "title": " WARNING: [U+FE0F] Cascade Failure Detected",
                "message": f"{metrics.cascade_failures} cascade failure(s) detected",
                "metric": "cascade_failures",
                "value": metrics.cascade_failures,
                "timestamp": current_time
            })
        
        # Check response time degradation (if baseline available)
        if self.baseline.baseline_response_time_p95 > 0:
            response_time_increase = (metrics.response_time_p95 - self.baseline.baseline_response_time_p95) / self.baseline.baseline_response_time_p95
            
            if response_time_increase >= self.thresholds.response_time_emergency_increase:
                alerts.append({
                    "level": "EMERGENCY",
                    "title": " ALERT:  CRITICAL: Response Time Degradation",
                    "message": f"Response time increased by {response_time_increase:.1%} (threshold: {self.thresholds.response_time_emergency_increase:.1%})",
                    "metric": "response_time_degradation",
                    "value": response_time_increase,
                    "threshold": self.thresholds.response_time_emergency_increase,
                    "timestamp": current_time,
                    "action_required": "IMMEDIATE ROLLBACK REQUIRED"
                })
            elif response_time_increase >= self.thresholds.response_time_critical_increase:
                alerts.append({
                    "level": "CRITICAL",
                    "title": " ALERT:  Response Time Degradation",
                    "message": f"Response time increased by {response_time_increase:.1%} (threshold: {self.thresholds.response_time_critical_increase:.1%})",
                    "metric": "response_time_degradation",
                    "value": response_time_increase,
                    "threshold": self.thresholds.response_time_critical_increase,
                    "timestamp": current_time
                })
            elif response_time_increase >= self.thresholds.response_time_warning_increase:
                alerts.append({
                    "level": "WARNING",
                    "title": " WARNING: [U+FE0F] Response Time Increase",
                    "message": f"Response time increased by {response_time_increase:.1%} from baseline",
                    "metric": "response_time_degradation", 
                    "value": response_time_increase,
                    "timestamp": current_time
                })
        
        # Filter alerts by cooldown period
        filtered_alerts = []
        for alert in alerts:
            alert_key = f"{alert['metric']}_{alert['level']}"
            last_alert_time = self.last_alert_times.get(alert_key, 0)
            
            if current_time - last_alert_time >= self.alert_cooldown_seconds:
                filtered_alerts.append(alert)
                self.last_alert_times[alert_key] = current_time
            else:
                logger.debug(f"Alert {alert_key} in cooldown period")
        
        return filtered_alerts

    async def send_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert through configured channels."""
        logger.warning(f"ALERT {alert['level']}: {alert['title']} - {alert['message']}")
        
        try:
            # Send to Slack
            if self.alert_config.slack_webhook_url:
                await self.send_slack_alert(alert)
            
            # Send to PagerDuty for critical/emergency alerts
            if alert['level'] in ['CRITICAL', 'EMERGENCY'] and self.alert_config.pagerduty_integration_key:
                await self.send_pagerduty_alert(alert)
            
            # Send email for all alerts
            if self.alert_config.email_recipients:
                await self.send_email_alert(alert)
                
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    async def send_slack_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert to Slack."""
        try:
            color = {
                "WARNING": "warning",
                "CRITICAL": "danger", 
                "EMERGENCY": "danger"
            }.get(alert['level'], "good")
            
            slack_message = {
                "text": f"Production Monitoring Alert - {self.environment.upper()}",
                "attachments": [{
                    "color": color,
                    "title": alert['title'],
                    "text": alert['message'],
                    "fields": [
                        {
                            "title": "Environment",
                            "value": self.environment,
                            "short": True
                        },
                        {
                            "title": "Timestamp", 
                            "value": datetime.fromtimestamp(alert['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                            "short": True
                        }
                    ]
                }]
            }
            
            if 'action_required' in alert:
                slack_message['attachments'][0]['fields'].append({
                    "title": "Action Required",
                    "value": alert['action_required'],
                    "short": False
                })
            
            response = requests.post(
                self.alert_config.slack_webhook_url,
                json=slack_message,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Slack alert sent successfully")
            else:
                logger.error(f"Failed to send Slack alert: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")

    async def send_pagerduty_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert to PagerDuty."""
        try:
            pagerduty_event = {
                "routing_key": self.alert_config.pagerduty_integration_key,
                "event_action": "trigger",
                "dedup_key": f"{alert['metric']}_{alert['level']}_{self.environment}",
                "payload": {
                    "summary": f"{alert['title']} - {self.environment}",
                    "source": f"netra-monitoring-{self.environment}",
                    "severity": "critical" if alert['level'] == "EMERGENCY" else "error",
                    "custom_details": {
                        "environment": self.environment,
                        "metric": alert.get('metric'),
                        "value": alert.get('value'),
                        "threshold": alert.get('threshold'),
                        "message": alert['message'],
                        "action_required": alert.get('action_required', 'Monitor situation')
                    }
                }
            }
            
            response = requests.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=pagerduty_event,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 202:
                logger.info("PagerDuty alert sent successfully")
            else:
                logger.error(f"Failed to send PagerDuty alert: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending PagerDuty alert: {e}")

    async def send_email_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert via email."""
        try:
            if not all([self.alert_config.email_username, self.alert_config.email_password]):
                logger.debug("Email credentials not configured, skipping email alert")
                return
            
            msg = MIMEMultipart()
            msg['From'] = self.alert_config.email_username
            msg['To'] = ", ".join(self.alert_config.email_recipients)
            msg['Subject'] = f"[{alert['level']}] Netra Production Alert - {self.environment.upper()}"
            
            body = f"""
Production Monitoring Alert

Environment: {self.environment}
Level: {alert['level']}
Title: {alert['title']}
Message: {alert['message']}
Timestamp: {datetime.fromtimestamp(alert['timestamp']).strftime('%Y-%m-%d %H:%M:%S UTC')}

"""
            
            if 'metric' in alert:
                body += f"Metric: {alert['metric']}\n"
                body += f"Value: {alert['value']}\n"
                body += f"Threshold: {alert.get('threshold', 'N/A')}\n"
            
            if 'action_required' in alert:
                body += f"\nAction Required: {alert['action_required']}\n"
            
            body += f"\n---\nNetra Production Monitoring System"
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.alert_config.email_smtp_host, self.alert_config.email_smtp_port)
            server.starttls()
            server.login(self.alert_config.email_username, self.alert_config.email_password)
            server.sendmail(self.alert_config.email_username, self.alert_config.email_recipients, msg.as_string())
            server.quit()
            
            logger.info("Email alert sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")

    def log_monitoring_status(self, metrics: IsolationMetrics, stage: str) -> None:
        """Log current monitoring status."""
        logger.info(f"MONITORING [{stage}] - "
                   f"Score: {metrics.isolation_score:.1%}, "
                   f"Errors: {metrics.error_rate:.2%}, "
                   f"Cascades: {metrics.cascade_failures}, "
                   f"Requests: {metrics.total_requests}")

    def update_performance_tracking(self, metrics: IsolationMetrics) -> None:
        """Update performance tracking data."""
        try:
            # Store metrics for trending analysis
            tracking_key = f"performance_tracking:{self.environment}"
            timestamp = int(metrics.timestamp)
            
            # Store in Redis with TTL (keep 7 days of data)
            tracking_data = {
                "isolation_score": metrics.isolation_score,
                "error_rate": metrics.error_rate,
                "response_time_p95": metrics.response_time_p95,
                "cascade_failures": metrics.cascade_failures,
                "total_requests": metrics.total_requests,
                "timestamp": timestamp
            }
            
            self.feature_flags.redis.zadd(
                tracking_key,
                {json.dumps(tracking_data): timestamp}
            )
            
            # Keep only last 7 days
            cutoff = timestamp - (7 * 24 * 60 * 60)
            self.feature_flags.redis.zremrangebyscore(tracking_key, 0, cutoff)
            
        except Exception as e:
            logger.error(f"Failed to update performance tracking: {e}")

    async def load_performance_baseline(self) -> None:
        """Load or calculate performance baseline."""
        try:
            # Try to load existing baseline
            baseline_key = f"performance_baseline:{self.environment}"
            baseline_data = self.feature_flags.redis.hgetall(baseline_key)
            
            if baseline_data:
                self.baseline = PerformanceBaseline(
                    baseline_response_time_p95=float(baseline_data.get("response_time_p95", "0")),
                    baseline_error_rate=float(baseline_data.get("error_rate", "0")),
                    baseline_isolation_score=float(baseline_data.get("isolation_score", "1.0")),
                    baseline_timestamp=float(baseline_data.get("timestamp", "0")),
                    baseline_period_hours=int(baseline_data.get("period_hours", "24"))
                )
                
                logger.info(f"Loaded performance baseline from {datetime.fromtimestamp(self.baseline.baseline_timestamp)}")
            else:
                # Calculate baseline from recent data
                await self.calculate_performance_baseline()
                
        except Exception as e:
            logger.error(f"Failed to load performance baseline: {e}")

    async def calculate_performance_baseline(self) -> None:
        """Calculate performance baseline from recent historical data."""
        try:
            # Get last 24 hours of data
            tracking_key = f"performance_tracking:{self.environment}"
            end_time = int(time.time())
            start_time = end_time - (24 * 60 * 60)
            
            historical_data = self.feature_flags.redis.zrangebyscore(
                tracking_key, start_time, end_time
            )
            
            if len(historical_data) < 10:  # Need at least 10 data points
                logger.warning("Insufficient historical data for baseline calculation")
                return
            
            # Parse data and calculate averages
            response_times = []
            error_rates = []
            isolation_scores = []
            
            for data_json in historical_data:
                try:
                    data = json.loads(data_json)
                    response_times.append(data['response_time_p95'])
                    error_rates.append(data['error_rate'])
                    isolation_scores.append(data['isolation_score'])
                except:
                    continue
            
            if response_times:
                self.baseline = PerformanceBaseline(
                    baseline_response_time_p95=statistics.median(response_times),
                    baseline_error_rate=statistics.median(error_rates),
                    baseline_isolation_score=statistics.median(isolation_scores),
                    baseline_timestamp=time.time(),
                    baseline_period_hours=24
                )
                
                # Save baseline
                baseline_key = f"performance_baseline:{self.environment}"
                self.feature_flags.redis.hset(baseline_key, mapping={
                    "response_time_p95": self.baseline.baseline_response_time_p95,
                    "error_rate": self.baseline.baseline_error_rate,
                    "isolation_score": self.baseline.baseline_isolation_score,
                    "timestamp": self.baseline.baseline_timestamp,
                    "period_hours": self.baseline.baseline_period_hours
                })
                
                logger.info(f"Calculated new performance baseline: "
                           f"RT={self.baseline.baseline_response_time_p95:.3f}s, "
                           f"ER={self.baseline.baseline_error_rate:.3%}, "
                           f"IS={self.baseline.baseline_isolation_score:.3%}")
            
        except Exception as e:
            logger.error(f"Failed to calculate performance baseline: {e}")

    def get_current_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        metrics = self.collect_current_metrics()
        
        if not metrics:
            return {"error": "Unable to collect current metrics"}
        
        status = {
            "environment": self.environment,
            "timestamp": metrics.timestamp,
            "monitoring_active": self.is_monitoring,
            "metrics": {
                "isolation_score": metrics.isolation_score,
                "error_rate": metrics.error_rate,
                "response_time_p95": metrics.response_time_p95,
                "total_requests": metrics.total_requests,
                "failed_requests": metrics.failed_requests,
                "cascade_failures": metrics.cascade_failures,
                "last_cascade_failure": metrics.last_cascade_failure
            },
            "baseline": {
                "response_time_p95": self.baseline.baseline_response_time_p95,
                "error_rate": self.baseline.baseline_error_rate,
                "isolation_score": self.baseline.baseline_isolation_score,
                "timestamp": self.baseline.baseline_timestamp
            },
            "alert_status": {
                "last_alert_times": self.last_alert_times,
                "configured_channels": {
                    "slack": bool(self.alert_config.slack_webhook_url),
                    "pagerduty": bool(self.alert_config.pagerduty_integration_key),
                    "email": bool(self.alert_config.email_recipients)
                }
            }
        }
        
        return status

    async def generate_daily_report(self, email_recipients: List[str] = None) -> str:
        """Generate daily monitoring report."""
        try:
            end_time = int(time.time())
            start_time = end_time - (24 * 60 * 60)
            
            # Get historical data for the last 24 hours
            tracking_key = f"performance_tracking:{self.environment}"
            daily_data = self.feature_flags.redis.zrangebyscore(
                tracking_key, start_time, end_time
            )
            
            if not daily_data:
                return "No data available for daily report"
            
            # Parse and analyze data
            isolation_scores = []
            error_rates = []
            response_times = []
            cascade_failures_count = 0
            total_requests = 0
            
            for data_json in daily_data:
                try:
                    data = json.loads(data_json)
                    isolation_scores.append(data['isolation_score'])
                    error_rates.append(data['error_rate'])
                    response_times.append(data['response_time_p95'])
                    cascade_failures_count += data.get('cascade_failures', 0)
                    total_requests = max(total_requests, data.get('total_requests', 0))
                except:
                    continue
            
            # Generate report
            report = f"""
Netra Production Monitoring - Daily Report
Environment: {self.environment.upper()}
Date: {datetime.now().strftime('%Y-%m-%d')}

=== EXECUTIVE SUMMARY ===
Overall Status: {' PASS:  HEALTHY' if min(isolation_scores) >= 0.99 else ' WARNING: [U+FE0F] NEEDS ATTENTION'}
Data Points: {len(daily_data)}
Monitoring Period: 24 hours

=== ISOLATION METRICS ===
Isolation Score:
  - Minimum: {min(isolation_scores):.1%}
  - Average: {statistics.mean(isolation_scores):.1%}
  - Maximum: {max(isolation_scores):.1%}
  - Current: {isolation_scores[-1] if isolation_scores else 0:.1%}

=== ERROR METRICS ===
Error Rate:
  - Minimum: {min(error_rates):.3%}
  - Average: {statistics.mean(error_rates):.3%}
  - Maximum: {max(error_rates):.3%}
  - Current: {error_rates[-1] if error_rates else 0:.3%}

=== PERFORMANCE METRICS ===
Response Time P95:
  - Minimum: {min(response_times):.3f}s
  - Average: {statistics.mean(response_times):.3f}s
  - Maximum: {max(response_times):.3f}s
  - Current: {response_times[-1] if response_times else 0:.3f}s

=== STABILITY METRICS ===
Total Requests Processed: {total_requests:,}
Cascade Failures (24h): {cascade_failures_count}
System Uptime: {' PASS:  100%' if cascade_failures_count == 0 else f' WARNING: [U+FE0F] {cascade_failures_count} incidents'}

=== RECOMMENDATIONS ===
"""
            
            # Add recommendations based on metrics
            if min(isolation_scores) < 0.99:
                report += "-  ALERT:  Isolation score below 99% - investigate request isolation\n"
            
            if max(error_rates) > 0.01:
                report += "-  WARNING: [U+FE0F] Error rate exceeded 1% - review error logs\n"
            
            if cascade_failures_count > 0:
                report += f"-  ALERT:  {cascade_failures_count} cascade failures detected - review isolation implementation\n"
            
            if not any([min(isolation_scores) < 0.99, max(error_rates) > 0.01, cascade_failures_count > 0]):
                report += "-  PASS:  All metrics within acceptable ranges\n"
                report += "-  PASS:  System operating normally\n"
            
            report += f"""
=== NEXT ACTIONS ===
- Continue monitoring isolation metrics
- Review any error spikes or performance degradation
- Maintain rollout stage based on current metrics

---
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
Netra Production Monitoring System
"""
            
            # Send email if recipients provided
            if email_recipients or self.alert_config.email_recipients:
                recipients = email_recipients or self.alert_config.email_recipients
                await self.send_daily_report_email(report, recipients)
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}")
            return f"Error generating daily report: {e}"

    async def send_daily_report_email(self, report: str, recipients: List[str]) -> None:
        """Send daily report via email."""
        try:
            if not all([self.alert_config.email_username, self.alert_config.email_password]):
                logger.warning("Email credentials not configured for daily report")
                return
            
            msg = MIMEMultipart()
            msg['From'] = self.alert_config.email_username
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = f"Netra Production Daily Report - {self.environment.upper()} - {datetime.now().strftime('%Y-%m-%d')}"
            
            msg.attach(MIMEText(report, 'plain'))
            
            server = smtplib.SMTP(self.alert_config.email_smtp_host, self.alert_config.email_smtp_port)
            server.starttls()
            server.login(self.alert_config.email_username, self.alert_config.email_password)
            server.sendmail(self.alert_config.email_username, recipients, msg.as_string())
            server.quit()
            
            logger.info(f"Daily report sent to {len(recipients)} recipients")
            
        except Exception as e:
            logger.error(f"Failed to send daily report email: {e}")


def main():
    """Main entry point for production monitoring."""
    parser = argparse.ArgumentParser(
        description="Production Monitoring System for Isolation Features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start real-time monitoring
  python scripts/production_monitoring.py start --stage canary
  
  # Check current metrics
  python scripts/production_monitoring.py metrics --detailed
  
  # Generate daily report
  python scripts/production_monitoring.py daily-report --email-recipients team@netra.ai
        """
    )
    
    parser.add_argument(
        "command",
        choices=["start", "metrics", "daily-report", "configure-alerts"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--environment",
        default="production",
        help="Environment to monitor"
    )
    
    parser.add_argument(
        "--stage",
        choices=["internal", "canary", "staged", "full"],
        default="production",
        help="Rollout stage being monitored"
    )
    
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed metrics"
    )
    
    parser.add_argument(
        "--email-recipients",
        nargs="+",
        help="Email recipients for reports"
    )
    
    parser.add_argument(
        "--slack-webhook",
        help="Slack webhook URL for alerts"
    )
    
    parser.add_argument(
        "--pagerduty-key",
        help="PagerDuty integration key"
    )
    
    args = parser.parse_args()
    
    # Initialize monitoring system
    monitor = ProductionMonitoringSystem(args.environment)
    
    try:
        if args.command == "start":
            asyncio.run(monitor.start_monitoring(args.stage))
            
        elif args.command == "metrics":
            status = monitor.get_current_status()
            
            print("\n" + "="*60)
            print(f"PRODUCTION MONITORING STATUS - {args.environment.upper()}")
            print("="*60)
            
            if "error" in status:
                print(f" FAIL:  Error: {status['error']}")
                sys.exit(1)
            
            metrics = status["metrics"]
            print(f"\nCurrent Metrics:")
            print(f"  Isolation Score: {metrics['isolation_score']:.1%}")
            print(f"  Error Rate: {metrics['error_rate']:.3%}")
            print(f"  Response Time P95: {metrics['response_time_p95']:.3f}s")
            print(f"  Total Requests: {metrics['total_requests']:,}")
            print(f"  Cascade Failures: {metrics['cascade_failures']}")
            
            if args.detailed:
                baseline = status["baseline"]
                print(f"\nBaseline Comparison:")
                print(f"  Response Time: {baseline['response_time_p95']:.3f}s")
                print(f"  Error Rate: {baseline['error_rate']:.3%}")
                print(f"  Isolation Score: {baseline['isolation_score']:.1%}")
                
                alert_status = status["alert_status"]
                print(f"\nAlert Configuration:")
                print(f"  Slack: {' PASS: ' if alert_status['configured_channels']['slack'] else ' FAIL: '}")
                print(f"  PagerDuty: {' PASS: ' if alert_status['configured_channels']['pagerduty'] else ' FAIL: '}")
                print(f"  Email: {' PASS: ' if alert_status['configured_channels']['email'] else ' FAIL: '}")
            
            print("\n" + "="*60)
            
        elif args.command == "daily-report":
            report = asyncio.run(monitor.generate_daily_report(args.email_recipients))
            print(report)
            
        elif args.command == "configure-alerts":
            if args.slack_webhook:
                monitor.alert_config.slack_webhook_url = args.slack_webhook
            if args.pagerduty_key:
                monitor.alert_config.pagerduty_integration_key = args.pagerduty_key
                
            print(" PASS:  Alert configuration updated")
            
    except KeyboardInterrupt:
        print("\n WARNING: [U+FE0F] Monitoring interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f" FAIL:  Error: {e}")
        logger.exception("Unexpected error in monitoring")
        sys.exit(1)


if __name__ == "__main__":
    main()