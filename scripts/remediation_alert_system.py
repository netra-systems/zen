#!/usr/bin/env python3
"""
Remediation Alert System

Provides automated monitoring, alerting, and escalation for P0 issue remediation
to prevent the "Analysis Trap" organizational anti-pattern by ensuring systematic
execution of remediation plans.

Features:
- Real-time monitoring of issue deadlines and progress
- Multi-channel alerting (logs, email, external systems)
- Automatic escalation based on configurable thresholds  
- Business impact tracking and reporting
- Integration with existing monitoring infrastructure
"""

import asyncio
import json
import logging
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import subprocess
import sys

# Import our remediation infrastructure
from scripts.critical_remediation_tracker import CriticalRemediationTracker, IssueStatus, IssuePriority

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertSeverity:
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning" 
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertChannel:
    """Alert delivery channel"""
    LOG = "log"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"


class RemediationAlert:
    """Data class for remediation alerts"""
    
    def __init__(
        self,
        alert_id: str,
        alert_type: str,
        severity: str,
        issue_id: str,
        title: str,
        message: str,
        business_impact: Optional[str] = None,
        owner: Optional[str] = None,
        escalation_level: int = 0,
        channels: List[str] = None,
        created_at: datetime = None
    ):
        self.alert_id = alert_id
        self.alert_type = alert_type
        self.severity = severity
        self.issue_id = issue_id
        self.title = title
        self.message = message
        self.business_impact = business_impact
        self.owner = owner
        self.escalation_level = escalation_level
        self.channels = channels or [AlertChannel.LOG]
        self.created_at = created_at or datetime.now()
        self.delivered_at = {}  # Track delivery per channel
        self.acknowledged = False
        self.acknowledged_by = None
        self.acknowledged_at = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "issue_id": self.issue_id,
            "title": self.title,
            "message": self.message,
            "business_impact": self.business_impact,
            "owner": self.owner,
            "escalation_level": self.escalation_level,
            "channels": self.channels,
            "created_at": self.created_at.isoformat(),
            "delivered_at": {k: v.isoformat() if isinstance(v, datetime) else v for k, v in self.delivered_at.items()},
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RemediationAlert':
        """Create from dictionary"""
        alert = cls(
            alert_id=data["alert_id"],
            alert_type=data["alert_type"],
            severity=data["severity"],
            issue_id=data["issue_id"],
            title=data["title"],
            message=data["message"],
            business_impact=data.get("business_impact"),
            owner=data.get("owner"),
            escalation_level=data.get("escalation_level", 0),
            channels=data.get("channels", [AlertChannel.LOG]),
            created_at=datetime.fromisoformat(data["created_at"])
        )
        
        # Restore delivered_at timestamps
        alert.delivered_at = {
            k: datetime.fromisoformat(v) if isinstance(v, str) else v
            for k, v in data.get("delivered_at", {}).items()
        }
        
        alert.acknowledged = data.get("acknowledged", False)
        alert.acknowledged_by = data.get("acknowledged_by")
        alert.acknowledged_at = datetime.fromisoformat(data["acknowledged_at"]) if data.get("acknowledged_at") else None
        
        return alert


class RemediationAlertSystem:
    """Main alert system for remediation tracking"""

    def __init__(self, data_dir: str = "reports/remediation"):
        self.tracker = CriticalRemediationTracker(data_dir)
        self.data_dir = Path(data_dir)
        self.alerts_dir = self.data_dir / "alerts"
        self.alerts_dir.mkdir(parents=True, exist_ok=True)
        
        self.active_alerts_file = self.alerts_dir / "active_alerts.json"
        self.alert_history_file = self.alerts_dir / "alert_history.json"
        self.alert_config_file = self.alerts_dir / "alert_config.json"
        
        self._load_config()
        self._load_active_alerts()
        
        # Alert handlers for different channels
        self.alert_handlers = {
            AlertChannel.LOG: self._handle_log_alert,
            AlertChannel.EMAIL: self._handle_email_alert,
            AlertChannel.SLACK: self._handle_slack_alert,
            AlertChannel.WEBHOOK: self._handle_webhook_alert
        }
        
        # Monitoring state
        self.monitoring_active = False
        self.last_check_time = datetime.now()

    def _load_config(self):
        """Load alert system configuration"""
        default_config = {
            "monitoring_interval_seconds": 300,  # 5 minutes
            "escalation_thresholds": {
                "level_1_hours": 4,   # Standard escalation after 4 hours overdue
                "level_2_hours": 8,   # Management escalation after 8 hours overdue
                "level_3_hours": 24   # Executive escalation after 24 hours overdue
            },
            "business_impact_thresholds": {
                "mrr_warning_threshold": 1000,    # $1K MRR at risk
                "mrr_critical_threshold": 5000,   # $5K MRR at risk
                "uptime_warning_threshold": 99.0, # Below 99% uptime
                "uptime_critical_threshold": 95.0  # Below 95% uptime
            },
            "notification_channels": {
                "default_channels": [AlertChannel.LOG],
                "p0_channels": [AlertChannel.LOG, AlertChannel.EMAIL],
                "escalation_channels": [AlertChannel.LOG, AlertChannel.EMAIL, AlertChannel.SLACK]
            },
            "email_settings": {
                "enabled": False,
                "smtp_server": "localhost",
                "smtp_port": 587,
                "sender_email": "alerts@netra.ai",
                "recipient_list": []
            },
            "slack_settings": {
                "enabled": False,
                "webhook_url": "",
                "channel": "#alerts"
            }
        }
        
        if self.alert_config_file.exists():
            with open(self.alert_config_file, 'r') as f:
                loaded_config = json.load(f)
                # Merge with defaults
                self.config = {**default_config, **loaded_config}
        else:
            self.config = default_config
            self._save_config()

    def _save_config(self):
        """Save alert configuration"""
        with open(self.alert_config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _load_active_alerts(self):
        """Load active alerts from storage"""
        if self.active_alerts_file.exists():
            with open(self.active_alerts_file, 'r') as f:
                data = json.load(f)
                self.active_alerts = {
                    alert_id: RemediationAlert.from_dict(alert_data)
                    for alert_id, alert_data in data.items()
                }
        else:
            self.active_alerts = {}

    def _save_active_alerts(self):
        """Save active alerts to storage"""
        data = {
            alert_id: alert.to_dict()
            for alert_id, alert in self.active_alerts.items()
        }
        with open(self.active_alerts_file, 'w') as f:
            json.dump(data, f, indent=2)

    def start_monitoring(self):
        """Start the alert monitoring loop"""
        logger.info("Starting remediation alert monitoring")
        self.monitoring_active = True
        
        try:
            while self.monitoring_active:
                self._monitoring_cycle()
                time.sleep(self.config["monitoring_interval_seconds"])
        except KeyboardInterrupt:
            logger.info("Monitoring interrupted by user")
        except Exception as e:
            logger.error(f"Monitoring error: {str(e)}")
        finally:
            self.monitoring_active = False
            logger.info("Alert monitoring stopped")

    def stop_monitoring(self):
        """Stop the alert monitoring loop"""
        self.monitoring_active = False

    def _monitoring_cycle(self):
        """Single monitoring cycle - check issues and generate alerts"""
        try:
            logger.debug("Starting monitoring cycle")
            current_time = datetime.now()
            
            # Reload issues from tracker
            self.tracker._load_issues()
            
            # Check for overdue issues
            self._check_overdue_issues(current_time)
            
            # Check for upcoming deadlines
            self._check_upcoming_deadlines(current_time)
            
            # Check business impact thresholds
            self._check_business_impact_thresholds(current_time)
            
            # Process escalations
            self._process_escalations(current_time)
            
            # Clean up resolved alerts
            self._cleanup_resolved_alerts(current_time)
            
            self.last_check_time = current_time
            logger.debug("Monitoring cycle completed")
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {str(e)}")

    def _check_overdue_issues(self, current_time: datetime):
        """Check for overdue issues and generate alerts"""
        overdue_issues = self.tracker.get_overdue_issues()
        
        for issue in overdue_issues:
            alert_id = f"overdue_{issue.issue_id}"
            
            # Skip if we already have an active alert for this issue
            if alert_id in self.active_alerts:
                continue
                
            days_overdue = -issue.days_until_deadline() if issue.days_until_deadline() else 0
            hours_overdue = days_overdue * 24
            
            # Determine severity based on priority and how overdue
            severity = self._determine_overdue_severity(issue.priority, hours_overdue)
            
            # Determine escalation level
            escalation_level = self._determine_escalation_level(hours_overdue)
            
            # Create alert
            alert = RemediationAlert(
                alert_id=alert_id,
                alert_type="overdue",
                severity=severity,
                issue_id=issue.issue_id,
                title=f"P{issue.priority.value.upper()} Issue Overdue: {issue.title[:50]}...",
                message=f"Issue {issue.issue_id} is {days_overdue:.1f} days overdue. "
                       f"Owner: {issue.owner or 'Unassigned'}. "
                       f"Business Impact: {issue.business_impact or 'Not specified'}",
                business_impact=issue.business_impact,
                owner=issue.owner,
                escalation_level=escalation_level,
                channels=self._get_channels_for_severity_and_escalation(severity, escalation_level)
            )
            
            self._fire_alert(alert)

    def _check_upcoming_deadlines(self, current_time: datetime):
        """Check for upcoming deadlines and generate alerts"""
        upcoming_issues = self.tracker.get_upcoming_deadlines(days_ahead=2)  # 2 days ahead
        
        for issue in upcoming_issues:
            alert_id = f"upcoming_{issue.issue_id}"
            
            # Skip if we already have an active alert for this issue
            if alert_id in self.active_alerts:
                continue
                
            days_until = issue.days_until_deadline()
            
            alert = RemediationAlert(
                alert_id=alert_id,
                alert_type="upcoming_deadline",
                severity=AlertSeverity.WARNING,
                issue_id=issue.issue_id,
                title=f"Upcoming Deadline: {issue.title[:50]}...",
                message=f"Issue {issue.issue_id} is due in {days_until} day(s). "
                       f"Owner: {issue.owner or 'Unassigned'}. "
                       f"Priority: {issue.priority.value.upper()}",
                business_impact=issue.business_impact,
                owner=issue.owner,
                escalation_level=0,
                channels=self.config["notification_channels"]["default_channels"]
            )
            
            self._fire_alert(alert)

    def _check_business_impact_thresholds(self, current_time: datetime):
        """Check if business impact thresholds are exceeded"""
        # Calculate total MRR at risk from active P0/P1 issues
        total_mrr_at_risk = 0
        critical_issues = []
        
        for issue in self.tracker.issues.values():
            if issue.status in [IssueStatus.IDENTIFIED, IssueStatus.PLANNED, IssueStatus.IN_PROGRESS]:
                if issue.priority in [IssuePriority.P0, IssuePriority.P1]:
                    if issue.business_value_protected:
                        total_mrr_at_risk += issue.business_value_protected
                        critical_issues.append(issue)
        
        # Check MRR threshold
        mrr_critical = self.config["business_impact_thresholds"]["mrr_critical_threshold"]
        mrr_warning = self.config["business_impact_thresholds"]["mrr_warning_threshold"]
        
        if total_mrr_at_risk >= mrr_critical:
            alert_id = "business_impact_critical"
            
            if alert_id not in self.active_alerts:
                alert = RemediationAlert(
                    alert_id=alert_id,
                    alert_type="business_impact",
                    severity=AlertSeverity.CRITICAL,
                    issue_id="MULTIPLE",
                    title=f"Critical Business Impact: ${total_mrr_at_risk:,.0f} MRR at Risk",
                    message=f"Total MRR at risk from {len(critical_issues)} active P0/P1 issues "
                           f"exceeds critical threshold of ${mrr_critical:,.0f}. "
                           f"Immediate executive attention required.",
                    business_impact=f"${total_mrr_at_risk:,.0f} MRR at risk",
                    escalation_level=3,  # Executive level
                    channels=self.config["notification_channels"]["escalation_channels"]
                )
                self._fire_alert(alert)
                
        elif total_mrr_at_risk >= mrr_warning:
            alert_id = "business_impact_warning"
            
            if alert_id not in self.active_alerts:
                alert = RemediationAlert(
                    alert_id=alert_id,
                    alert_type="business_impact",
                    severity=AlertSeverity.WARNING,
                    issue_id="MULTIPLE",
                    title=f"Business Impact Warning: ${total_mrr_at_risk:,.0f} MRR at Risk",
                    message=f"Total MRR at risk from {len(critical_issues)} active P0/P1 issues "
                           f"exceeds warning threshold of ${mrr_warning:,.0f}. "
                           f"Consider resource prioritization.",
                    business_impact=f"${total_mrr_at_risk:,.0f} MRR at risk",
                    escalation_level=1,
                    channels=self.config["notification_channels"]["p0_channels"]
                )
                self._fire_alert(alert)

    def _process_escalations(self, current_time: datetime):
        """Process alert escalations based on time and acknowledgment"""
        escalation_config = self.config["escalation_thresholds"]
        
        for alert in list(self.active_alerts.values()):
            if alert.acknowledged:
                continue
                
            alert_age_hours = (current_time - alert.created_at).total_seconds() / 3600
            
            # Determine if escalation is needed
            new_escalation_level = 0
            if alert_age_hours >= escalation_config["level_3_hours"]:
                new_escalation_level = 3  # Executive
            elif alert_age_hours >= escalation_config["level_2_hours"]:
                new_escalation_level = 2  # Management
            elif alert_age_hours >= escalation_config["level_1_hours"]:
                new_escalation_level = 1  # Team Lead
            
            # Escalate if needed
            if new_escalation_level > alert.escalation_level:
                self._escalate_alert(alert, new_escalation_level)

    def _escalate_alert(self, alert: RemediationAlert, new_level: int):
        """Escalate an alert to a higher level"""
        old_level = alert.escalation_level
        alert.escalation_level = new_level
        
        # Create escalation alert
        escalation_names = {1: "Team Lead", 2: "Management", 3: "Executive"}
        
        escalation_alert = RemediationAlert(
            alert_id=f"escalation_{alert.alert_id}_{new_level}",
            alert_type="escalation",
            severity=AlertSeverity.CRITICAL if new_level >= 2 else AlertSeverity.WARNING,
            issue_id=alert.issue_id,
            title=f"ESCALATED to {escalation_names.get(new_level, 'Unknown')}: {alert.title}",
            message=f"Alert {alert.alert_id} has been escalated to level {new_level} "
                   f"after {(datetime.now() - alert.created_at).total_seconds() / 3600:.1f} hours "
                   f"without acknowledgment. Original message: {alert.message}",
            business_impact=alert.business_impact,
            owner=alert.owner,
            escalation_level=new_level,
            channels=self.config["notification_channels"]["escalation_channels"]
        )
        
        self._fire_alert(escalation_alert)
        
        logger.warning(f"Alert {alert.alert_id} escalated from level {old_level} to {new_level}")

    def _cleanup_resolved_alerts(self, current_time: datetime):
        """Clean up alerts for resolved issues"""
        alerts_to_remove = []
        
        for alert_id, alert in self.active_alerts.items():
            if alert.issue_id in self.tracker.issues:
                issue = self.tracker.issues[alert.issue_id]
                
                # Remove alerts for completed or validated issues
                if issue.status in [IssueStatus.COMPLETED, IssueStatus.VALIDATED]:
                    alerts_to_remove.append(alert_id)
                    
                    # Log resolution
                    logger.info(f"Resolving alert {alert_id} - issue {issue.issue_id} status: {issue.status.value}")
            else:
                # Issue no longer exists, clean up alert
                alerts_to_remove.append(alert_id)
        
        # Remove resolved alerts
        for alert_id in alerts_to_remove:
            self._archive_alert(self.active_alerts[alert_id])
            del self.active_alerts[alert_id]
        
        if alerts_to_remove:
            self._save_active_alerts()
            logger.info(f"Cleaned up {len(alerts_to_remove)} resolved alerts")

    def _determine_overdue_severity(self, priority: IssuePriority, hours_overdue: float) -> str:
        """Determine alert severity based on issue priority and how overdue it is"""
        if priority == IssuePriority.P0:
            if hours_overdue >= 8:
                return AlertSeverity.EMERGENCY
            elif hours_overdue >= 4:
                return AlertSeverity.CRITICAL
            else:
                return AlertSeverity.WARNING
        elif priority == IssuePriority.P1:
            if hours_overdue >= 24:
                return AlertSeverity.CRITICAL
            elif hours_overdue >= 8:
                return AlertSeverity.WARNING
            else:
                return AlertSeverity.INFO
        else:
            return AlertSeverity.INFO

    def _determine_escalation_level(self, hours_overdue: float) -> int:
        """Determine escalation level based on how overdue an issue is"""
        thresholds = self.config["escalation_thresholds"]
        
        if hours_overdue >= thresholds["level_3_hours"]:
            return 3  # Executive
        elif hours_overdue >= thresholds["level_2_hours"]:
            return 2  # Management
        elif hours_overdue >= thresholds["level_1_hours"]:
            return 1  # Team Lead
        else:
            return 0  # Standard

    def _get_channels_for_severity_and_escalation(self, severity: str, escalation_level: int) -> List[str]:
        """Get appropriate notification channels based on severity and escalation level"""
        if escalation_level >= 2:
            return self.config["notification_channels"]["escalation_channels"]
        elif severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]:
            return self.config["notification_channels"]["p0_channels"] 
        else:
            return self.config["notification_channels"]["default_channels"]

    def _fire_alert(self, alert: RemediationAlert):
        """Fire an alert through configured channels"""
        logger.info(f"Firing alert: {alert.alert_id} [{alert.severity}] {alert.title}")
        
        # Add to active alerts
        self.active_alerts[alert.alert_id] = alert
        
        # Deliver through each channel
        for channel in alert.channels:
            try:
                if channel in self.alert_handlers:
                    self.alert_handlers[channel](alert)
                    alert.delivered_at[channel] = datetime.now()
                else:
                    logger.warning(f"Unknown alert channel: {channel}")
            except Exception as e:
                logger.error(f"Failed to deliver alert {alert.alert_id} via {channel}: {str(e)}")
        
        # Save state
        self._save_active_alerts()
        
        # Archive alert for history
        self._archive_alert(alert)

    def _handle_log_alert(self, alert: RemediationAlert):
        """Handle log-based alerts"""
        severity_icons = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️", 
            AlertSeverity.CRITICAL: "🔴",
            AlertSeverity.EMERGENCY: "🚨"
        }
        
        icon = severity_icons.get(alert.severity, "📢")
        log_message = f"{icon} REMEDIATION ALERT [{alert.severity.upper()}] {alert.title}"
        
        if alert.severity == AlertSeverity.EMERGENCY:
            logger.critical(log_message)
            logger.critical(f"  Issue: {alert.issue_id}")
            logger.critical(f"  Owner: {alert.owner or 'UNASSIGNED'}")
            logger.critical(f"  Message: {alert.message}")
            if alert.business_impact:
                logger.critical(f"  Business Impact: {alert.business_impact}")
        elif alert.severity == AlertSeverity.CRITICAL:
            logger.error(log_message)
            logger.error(f"  Issue: {alert.issue_id} | Owner: {alert.owner or 'UNASSIGNED'}")
            logger.error(f"  Message: {alert.message}")
        elif alert.severity == AlertSeverity.WARNING:
            logger.warning(log_message)
            logger.warning(f"  Issue: {alert.issue_id} | Owner: {alert.owner or 'UNASSIGNED'}")
        else:
            logger.info(log_message)

    def _handle_email_alert(self, alert: RemediationAlert):
        """Handle email alerts"""
        if not self.config["email_settings"]["enabled"]:
            logger.debug(f"Email alerts disabled, skipping alert {alert.alert_id}")
            return
        
        try:
            # Create email content
            subject = f"[{alert.severity.upper()}] Remediation Alert: {alert.title}"
            
            body = f"""
Remediation Alert Details:

Alert ID: {alert.alert_id}
Severity: {alert.severity.upper()}
Issue ID: {alert.issue_id}
Owner: {alert.owner or 'UNASSIGNED'}

Message: {alert.message}

Business Impact: {alert.business_impact or 'Not specified'}

Created: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Escalation Level: {alert.escalation_level}

---
Netra Remediation Alert System
"""
            
            # Send email
            smtp_config = self.config["email_settings"]
            msg = MimeText(body)
            msg['Subject'] = subject
            msg['From'] = smtp_config["sender_email"]
            msg['To'] = ", ".join(smtp_config["recipient_list"])
            
            # This is a simplified implementation
            # In production, you'd use proper SMTP with authentication
            logger.info(f"Email alert would be sent: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")

    def _handle_slack_alert(self, alert: RemediationAlert):
        """Handle Slack alerts via webhook"""
        if not self.config["slack_settings"]["enabled"]:
            logger.debug(f"Slack alerts disabled, skipping alert {alert.alert_id}")
            return
            
        try:
            # This is a simplified implementation
            # In production, you'd use the Slack API or webhooks
            logger.info(f"Slack alert would be sent to {self.config['slack_settings']['channel']}: {alert.title}")
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {str(e)}")

    def _handle_webhook_alert(self, alert: RemediationAlert):
        """Handle webhook alerts to external systems"""
        try:
            # This would integrate with external monitoring/alerting systems
            logger.info(f"Webhook alert would be sent: {alert.title}")
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {str(e)}")

    def _archive_alert(self, alert: RemediationAlert):
        """Archive alert to history"""
        try:
            # Load existing history
            if self.alert_history_file.exists():
                with open(self.alert_history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []
            
            # Add alert to history
            alert_dict = alert.to_dict()
            alert_dict["archived_at"] = datetime.now().isoformat()
            history.append(alert_dict)
            
            # Keep only last 1000 alerts
            history = history[-1000:]
            
            # Save history
            with open(self.alert_history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to archive alert {alert.alert_id}: {str(e)}")

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an active alert"""
        if alert_id not in self.active_alerts:
            logger.warning(f"Alert {alert_id} not found in active alerts")
            return False
        
        alert = self.active_alerts[alert_id]
        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now()
        
        self._save_active_alerts()
        
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return True

    def get_active_alerts_summary(self) -> Dict[str, Any]:
        """Get summary of active alerts"""
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_active_alerts": len(self.active_alerts),
            "alerts_by_severity": {},
            "alerts_by_escalation_level": {},
            "unacknowledged_alerts": 0,
            "business_impact_alerts": 0,
            "oldest_alert_age_hours": 0,
            "alerts": []
        }
        
        if not self.active_alerts:
            return summary
        
        # Process active alerts
        oldest_alert_time = datetime.now()
        
        for alert in self.active_alerts.values():
            # Count by severity
            summary["alerts_by_severity"][alert.severity] = summary["alerts_by_severity"].get(alert.severity, 0) + 1
            
            # Count by escalation level
            level_key = f"level_{alert.escalation_level}"
            summary["alerts_by_escalation_level"][level_key] = summary["alerts_by_escalation_level"].get(level_key, 0) + 1
            
            # Count unacknowledged
            if not alert.acknowledged:
                summary["unacknowledged_alerts"] += 1
            
            # Count business impact alerts
            if alert.business_impact:
                summary["business_impact_alerts"] += 1
            
            # Track oldest alert
            if alert.created_at < oldest_alert_time:
                oldest_alert_time = alert.created_at
            
            # Add alert summary
            summary["alerts"].append({
                "alert_id": alert.alert_id,
                "severity": alert.severity,
                "issue_id": alert.issue_id,
                "title": alert.title,
                "owner": alert.owner,
                "escalation_level": alert.escalation_level,
                "acknowledged": alert.acknowledged,
                "age_hours": (datetime.now() - alert.created_at).total_seconds() / 3600
            })
        
        # Calculate oldest alert age
        if oldest_alert_time < datetime.now():
            summary["oldest_alert_age_hours"] = (datetime.now() - oldest_alert_time).total_seconds() / 3600
        
        return summary

    def generate_daily_report(self) -> str:
        """Generate daily alert report"""
        summary = self.get_active_alerts_summary()
        status_report = self.tracker.generate_status_report()
        
        report = f"""
# Daily Remediation Alert Report - {datetime.now().strftime('%Y-%m-%d')}

## Alert Summary
- **Total Active Alerts:** {summary['total_active_alerts']}
- **Unacknowledged Alerts:** {summary['unacknowledged_alerts']}
- **Business Impact Alerts:** {summary['business_impact_alerts']}
- **Oldest Alert Age:** {summary['oldest_alert_age_hours']:.1f} hours

## Alerts by Severity
"""
        
        for severity, count in summary['alerts_by_severity'].items():
            report += f"- **{severity.upper()}:** {count}\n"
        
        report += f"""
## Issue Status Summary
- **Total Issues Tracked:** {status_report['summary']['total_issues']}
- **Overdue Issues:** {status_report['summary']['overdue_issues']}
- **Completion Rate:** {status_report['summary']['completion_rate']:.1f}%

## Business Metrics
- **Total Value Protected:** ${status_report['business_metrics']['total_value_protected']:,.0f}
- **Avg Resolution Time:** {status_report['business_metrics']['avg_resolution_time']:.1f} hours
- **Prevention Score:** {status_report['business_metrics']['recurrence_prevention_score']:.1f}%

## Active Critical Alerts
"""
        
        critical_alerts = [a for a in summary['alerts'] if a['severity'] in ['critical', 'emergency']]
        if critical_alerts:
            for alert in critical_alerts:
                report += f"- **{alert['alert_id']}** [{alert['severity'].upper()}] {alert['title']} (Owner: {alert['owner'] or 'Unassigned'})\n"
        else:
            report += "- No critical alerts active\n"
        
        report += f"""
---
*Report generated by Netra Remediation Alert System*
*Last monitoring check: {self.last_check_time.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return report


def main():
    """Main entry point for the alert system"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Remediation Alert System')
    parser.add_argument('command', choices=['monitor', 'status', 'acknowledge', 'report'], 
                       help='Command to execute')
    parser.add_argument('--alert-id', help='Alert ID for acknowledge command')
    parser.add_argument('--acknowledged-by', help='Person acknowledging the alert')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    alert_system = RemediationAlertSystem()
    
    if args.command == 'monitor':
        try:
            alert_system.start_monitoring()
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
    
    elif args.command == 'status':
        summary = alert_system.get_active_alerts_summary()
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print("=== Active Alerts Summary ===")
            print(f"Total Active: {summary['total_active_alerts']}")
            print(f"Unacknowledged: {summary['unacknowledged_alerts']}")
            print(f"Business Impact: {summary['business_impact_alerts']}")
            
            if summary['alerts']:
                print("\n--- Critical Alerts ---")
                for alert in summary['alerts']:
                    if alert['severity'] in ['critical', 'emergency']:
                        print(f"  {alert['alert_id']}: {alert['title']} (Owner: {alert['owner'] or 'Unassigned'})")
    
    elif args.command == 'acknowledge':
        if not args.alert_id or not args.acknowledged_by:
            print("Error: --alert-id and --acknowledged-by are required for acknowledge command")
            return 1
        
        success = alert_system.acknowledge_alert(args.alert_id, args.acknowledged_by)
        if success:
            print(f"Alert {args.alert_id} acknowledged by {args.acknowledged_by}")
        else:
            print(f"Failed to acknowledge alert {args.alert_id}")
            return 1
    
    elif args.command == 'report':
        report = alert_system.generate_daily_report()
        print(report)
    
    return 0


if __name__ == '__main__':
    exit(main())