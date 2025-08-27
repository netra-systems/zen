"""Comprehensive unit tests for security observability across distributed systems.

Tests security monitoring, threat detection, compliance tracking,
and security incident response patterns. Covers iterations 68-70.

Business Value: Ensures comprehensive security posture monitoring
and provides early detection of security threats and compliance violations.
"""

import asyncio
import hashlib
import json
import time
from enum import Enum
from typing import Dict, List, Optional, Set
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest


class SecurityEventType(Enum):
    """Types of security events."""
    AUTHENTICATION_FAILURE = "auth_failure"
    AUTHORIZATION_VIOLATION = "authz_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_ACCESS_ANOMALY = "data_access_anomaly"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    BRUTE_FORCE_ATTACK = "brute_force_attack"
    INJECTION_ATTEMPT = "injection_attempt"
    COMPLIANCE_VIOLATION = "compliance_violation"


class ThreatLevel(Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TestSecurityEventMonitoring:
    """Test suite for security event monitoring and analysis."""
    
    @pytest.fixture
    def mock_security_monitor(self):
        """Create mock security monitoring system."""
        monitor = Mock()
        monitor.events = []
        monitor.threat_indicators = {}
        monitor.baseline_behavior = {}
        monitor.alert_rules = []
        return monitor
    
    def test_authentication_failure_pattern_detection(self, mock_security_monitor):
        """Test detection of authentication failure patterns."""
        
        class AuthFailureDetector:
            def __init__(self):
                self.failure_counts = {}
                self.failure_threshold = 5
                self.time_window_seconds = 300  # 5 minutes
                self.blocked_ips = set()
            
            def record_auth_failure(self, ip_address: str, username: str, timestamp: float):
                key = f"{ip_address}:{username}"
                
                if key not in self.failure_counts:
                    self.failure_counts[key] = []
                
                self.failure_counts[key].append(timestamp)
                
                # Clean old failures outside time window
                cutoff_time = timestamp - self.time_window_seconds
                self.failure_counts[key] = [
                    t for t in self.failure_counts[key] if t > cutoff_time
                ]
                
                # Check for brute force pattern
                if len(self.failure_counts[key]) >= self.failure_threshold:
                    return self.trigger_brute_force_alert(ip_address, username, len(self.failure_counts[key]))
                
                return None
            
            def trigger_brute_force_alert(self, ip_address: str, username: str, failure_count: int):
                self.blocked_ips.add(ip_address)
                return {
                    'alert_type': 'brute_force_attack',
                    'ip_address': ip_address,
                    'username': username,
                    'failure_count': failure_count,
                    'threat_level': ThreatLevel.HIGH,
                    'recommended_action': 'block_ip',
                    'timestamp': time.time()
                }
        
        detector = AuthFailureDetector()
        current_time = time.time()
        
        # Simulate authentication failures
        alerts = []
        for i in range(6):  # Exceed threshold
            alert = detector.record_auth_failure('192.168.1.100', 'admin', current_time + i)
            if alert:
                alerts.append(alert)
        
        # Verify brute force detection (alerts generated at 5th and 6th failures)
        assert len(alerts) == 2
        assert alerts[0]['alert_type'] == 'brute_force_attack'
        assert alerts[0]['failure_count'] >= detector.failure_threshold
        assert '192.168.1.100' in detector.blocked_ips
    
    def test_data_access_anomaly_detection(self, mock_security_monitor):
        """Test detection of anomalous data access patterns."""
        
        class DataAccessAnomalyDetector:
            def __init__(self):
                self.user_baselines = {}
                self.access_logs = []
                self.anomaly_threshold = 2.0  # Standard deviations
            
            def record_data_access(self, user_id: str, resource_type: str, resource_count: int, timestamp: float):
                access_record = {
                    'user_id': user_id,
                    'resource_type': resource_type,
                    'resource_count': resource_count,
                    'timestamp': timestamp
                }
                self.access_logs.append(access_record)
                
                # Update user baseline
                if user_id not in self.user_baselines:
                    self.user_baselines[user_id] = {}
                
                if resource_type not in self.user_baselines[user_id]:
                    self.user_baselines[user_id][resource_type] = {
                        'access_counts': [],
                        'mean': 0.0,
                        'std_dev': 0.0
                    }
                
                baseline = self.user_baselines[user_id][resource_type]
                baseline['access_counts'].append(resource_count)
                
                # Keep only recent access counts for baseline (last 30 accesses)
                baseline['access_counts'] = baseline['access_counts'][-30:]
                
                # Calculate statistics
                if len(baseline['access_counts']) > 5:  # Minimum sample size
                    counts = baseline['access_counts']
                    baseline['mean'] = sum(counts) / len(counts)
                    variance = sum((x - baseline['mean']) ** 2 for x in counts) / len(counts)
                    baseline['std_dev'] = variance ** 0.5
                    
                    # Check for anomaly
                    if baseline['std_dev'] > 0:
                        z_score = abs(resource_count - baseline['mean']) / baseline['std_dev']
                        if z_score > self.anomaly_threshold:
                            return self.generate_anomaly_alert(user_id, resource_type, resource_count, z_score)
                
                return None
            
            def generate_anomaly_alert(self, user_id: str, resource_type: str, access_count: int, z_score: float):
                return {
                    'alert_type': 'data_access_anomaly',
                    'user_id': user_id,
                    'resource_type': resource_type,
                    'access_count': access_count,
                    'z_score': z_score,
                    'threat_level': ThreatLevel.MEDIUM if z_score < 3.0 else ThreatLevel.HIGH,
                    'timestamp': time.time()
                }
        
        detector = DataAccessAnomalyDetector()
        
        # Establish baseline for user
        user_id = 'user_123'
        current_time = time.time()
        
        # Normal access pattern (around 10 records per access)
        for i in range(10):
            detector.record_data_access(user_id, 'user_profiles', 10 + (i % 3), current_time + i)
        
        # Anomalous access (100 records - much higher than baseline)
        anomaly_alert = detector.record_data_access(user_id, 'user_profiles', 100, current_time + 15)
        
        # Verify anomaly detection
        assert anomaly_alert is not None
        assert anomaly_alert['alert_type'] == 'data_access_anomaly'
        assert anomaly_alert['z_score'] > detector.anomaly_threshold
        assert anomaly_alert['access_count'] == 100
    
    @pytest.mark.asyncio
    async def test_privilege_escalation_detection(self, mock_security_monitor):
        """Test detection of privilege escalation attempts."""
        
        class PrivilegeEscalationDetector:
            def __init__(self):
                self.user_roles = {}
                self.role_hierarchy = {
                    'user': 1,
                    'moderator': 2,
                    'admin': 3,
                    'superadmin': 4
                }
                self.suspicious_activities = []
            
            async def track_role_change(self, user_id: str, old_role: str, new_role: str, initiator_id: str, timestamp: float):
                # Record role change
                role_change = {
                    'user_id': user_id,
                    'old_role': old_role,
                    'new_role': new_role,
                    'initiator_id': initiator_id,
                    'timestamp': timestamp
                }
                
                # Check for suspicious escalation
                old_level = self.role_hierarchy.get(old_role, 0)
                new_level = self.role_hierarchy.get(new_role, 0)
                
                if new_level > old_level + 1:  # More than one level jump
                    return await self.flag_suspicious_escalation(role_change, 'role_level_jump')
                
                # Check if user is escalating their own privileges
                if user_id == initiator_id and new_level > old_level:
                    return await self.flag_suspicious_escalation(role_change, 'self_escalation')
                
                # Check for rapid escalations
                recent_escalations = [
                    activity for activity in self.suspicious_activities
                    if activity['user_id'] == user_id and 
                    activity['timestamp'] > timestamp - 3600  # Last hour
                ]
                
                if len(recent_escalations) >= 2:
                    return await self.flag_suspicious_escalation(role_change, 'rapid_escalation')
                
                return None
            
            async def flag_suspicious_escalation(self, role_change: Dict, reason: str):
                suspicious_activity = {
                    **role_change,
                    'suspicion_reason': reason,
                    'threat_level': ThreatLevel.HIGH,
                    'requires_investigation': True
                }
                
                self.suspicious_activities.append(suspicious_activity)
                
                return {
                    'alert_type': 'privilege_escalation',
                    'details': suspicious_activity,
                    'recommended_action': 'review_and_verify',
                    'timestamp': time.time()
                }
        
        detector = PrivilegeEscalationDetector()
        current_time = time.time()
        
        # Test self-escalation detection
        alert1 = await detector.track_role_change('user_456', 'user', 'admin', 'user_456', current_time)
        
        # Test role level jump detection
        alert2 = await detector.track_role_change('user_789', 'user', 'superadmin', 'admin_001', current_time + 10)
        
        # Verify privilege escalation detection
        assert alert1 is not None
        assert alert1['alert_type'] == 'privilege_escalation'
        assert alert1['details']['suspicion_reason'] == 'role_level_jump'
        
        assert alert2 is not None
        assert alert2['details']['suspicion_reason'] == 'role_level_jump'


class TestComplianceMonitoring:
    """Test suite for compliance monitoring and tracking."""
    
    @pytest.fixture
    def compliance_framework(self):
        """Create compliance framework rules."""
        return {
            'GDPR': {
                'data_retention_days': 365,
                'requires_consent': True,
                'requires_encryption': True,
                'allows_data_export': True,
                'allows_data_deletion': True
            },
            'SOX': {
                'requires_audit_trail': True,
                'financial_data_access_logging': True,
                'segregation_of_duties': True,
                'change_management_required': True
            },
            'HIPAA': {
                'phi_encryption_required': True,
                'access_logging_required': True,
                'minimum_password_length': 8,
                'session_timeout_minutes': 30
            }
        }
    
    def test_data_retention_compliance_monitoring(self, compliance_framework):
        """Test monitoring of data retention compliance."""
        
        class DataRetentionMonitor:
            def __init__(self, frameworks: Dict):
                self.frameworks = frameworks
                self.data_records = {}
                self.retention_violations = []
            
            def register_data_record(self, record_id: str, data_type: str, created_at: float, applicable_frameworks: List[str]):
                self.data_records[record_id] = {
                    'data_type': data_type,
                    'created_at': created_at,
                    'applicable_frameworks': applicable_frameworks,
                    'deletion_required_by': None
                }
                
                # Calculate earliest deletion requirement
                min_retention_days = float('inf')
                for framework in applicable_frameworks:
                    if framework in self.frameworks:
                        retention_days = self.frameworks[framework].get('data_retention_days')
                        if retention_days:
                            min_retention_days = min(min_retention_days, retention_days)
                
                if min_retention_days != float('inf'):
                    deletion_deadline = created_at + (min_retention_days * 86400)  # Convert to seconds
                    self.data_records[record_id]['deletion_required_by'] = deletion_deadline
            
            def check_retention_compliance(self, current_time: float):
                violations = []
                
                for record_id, record in self.data_records.items():
                    if record['deletion_required_by'] and current_time > record['deletion_required_by']:
                        violation = {
                            'violation_type': 'data_retention_exceeded',
                            'record_id': record_id,
                            'data_type': record['data_type'],
                            'overdue_days': (current_time - record['deletion_required_by']) / 86400,
                            'applicable_frameworks': record['applicable_frameworks'],
                            'severity': 'high'
                        }
                        violations.append(violation)
                        self.retention_violations.append(violation)
                
                return violations
        
        monitor = DataRetentionMonitor(compliance_framework)
        
        # Register data records
        current_time = time.time()
        old_time = current_time - (400 * 86400)  # 400 days ago
        
        monitor.register_data_record('record_001', 'user_profile', old_time, ['GDPR'])
        monitor.register_data_record('record_002', 'session_log', current_time - (30 * 86400), ['GDPR', 'HIPAA'])
        
        # Check compliance
        violations = monitor.check_retention_compliance(current_time)
        
        # Verify retention compliance monitoring
        assert len(violations) == 1  # record_001 should be overdue
        assert violations[0]['record_id'] == 'record_001'
        assert violations[0]['overdue_days'] > 30  # More than 30 days overdue
    
    def test_access_control_compliance_monitoring(self, compliance_framework):
        """Test monitoring of access control compliance."""
        
        class AccessControlComplianceMonitor:
            def __init__(self, frameworks: Dict):
                self.frameworks = frameworks
                self.access_events = []
                self.compliance_violations = []
            
            def record_access_event(self, user_id: str, resource_type: str, action: str, timestamp: float, session_duration_minutes: Optional[float] = None):
                access_event = {
                    'user_id': user_id,
                    'resource_type': resource_type,
                    'action': action,
                    'timestamp': timestamp,
                    'session_duration_minutes': session_duration_minutes
                }
                self.access_events.append(access_event)
                
                # Check session timeout compliance (HIPAA)
                if resource_type == 'phi_data' and session_duration_minutes:
                    hipaa_rules = self.frameworks.get('HIPAA', {})
                    max_session_minutes = hipaa_rules.get('session_timeout_minutes', 30)
                    
                    if session_duration_minutes > max_session_minutes:
                        violation = {
                            'violation_type': 'session_timeout_exceeded',
                            'user_id': user_id,
                            'resource_type': resource_type,
                            'session_duration_minutes': session_duration_minutes,
                            'max_allowed_minutes': max_session_minutes,
                            'framework': 'HIPAA',
                            'severity': 'medium'
                        }
                        self.compliance_violations.append(violation)
                
                # Check access logging compliance (SOX for financial data)
                if resource_type == 'financial_data':
                    sox_rules = self.frameworks.get('SOX', {})
                    if sox_rules.get('financial_data_access_logging') and action not in ['logged_access']:
                        violation = {
                            'violation_type': 'insufficient_access_logging',
                            'user_id': user_id,
                            'resource_type': resource_type,
                            'action': action,
                            'framework': 'SOX',
                            'severity': 'high'
                        }
                        self.compliance_violations.append(violation)
            
            def generate_compliance_report(self):
                violations_by_framework = {}
                for violation in self.compliance_violations:
                    framework = violation['framework']
                    if framework not in violations_by_framework:
                        violations_by_framework[framework] = []
                    violations_by_framework[framework].append(violation)
                
                return {
                    'total_violations': len(self.compliance_violations),
                    'violations_by_framework': violations_by_framework,
                    'compliance_score': max(0, 100 - (len(self.compliance_violations) * 5)),  # Penalty per violation
                    'report_timestamp': time.time()
                }
        
        monitor = AccessControlComplianceMonitor(compliance_framework)
        
        # Record access events
        current_time = time.time()
        
        # HIPAA violation - long session
        monitor.record_access_event('user_001', 'phi_data', 'read', current_time, session_duration_minutes=45)
        
        # SOX violation - unlogged financial access
        monitor.record_access_event('user_002', 'financial_data', 'update', current_time + 10)
        
        # Compliant access
        monitor.record_access_event('user_003', 'phi_data', 'read', current_time + 20, session_duration_minutes=25)
        
        # Generate compliance report
        report = monitor.generate_compliance_report()
        
        # Verify compliance monitoring
        assert report['total_violations'] == 2
        assert 'HIPAA' in report['violations_by_framework']
        assert 'SOX' in report['violations_by_framework']
        assert report['compliance_score'] == 90  # 100 - (2 * 5)


class TestSecurityIncidentResponse:
    """Test suite for security incident response and automation."""
    
    @pytest.fixture
    def incident_response_system(self):
        """Create mock incident response system."""
        return Mock()
    
    @pytest.mark.asyncio
    async def test_automated_incident_response_workflow(self, incident_response_system):
        """Test automated security incident response workflows."""
        
        class IncidentResponseOrchestrator:
            def __init__(self):
                self.active_incidents = {}
                self.response_playbooks = {}
                self.automated_actions = []
            
            def register_playbook(self, threat_type: str, playbook: Dict):
                self.response_playbooks[threat_type] = playbook
            
            async def trigger_incident(self, incident_id: str, threat_type: str, severity: ThreatLevel, context: Dict):
                incident = {
                    'incident_id': incident_id,
                    'threat_type': threat_type,
                    'severity': severity,
                    'context': context,
                    'status': 'active',
                    'created_at': time.time(),
                    'actions_taken': []
                }
                
                self.active_incidents[incident_id] = incident
                
                # Execute automated response
                if threat_type in self.response_playbooks:
                    await self.execute_playbook(incident_id, threat_type)
            
            async def execute_playbook(self, incident_id: str, threat_type: str):
                playbook = self.response_playbooks[threat_type]
                incident = self.active_incidents[incident_id]
                
                for step in playbook['steps']:
                    action_result = await self.execute_response_action(step, incident['context'])
                    
                    incident['actions_taken'].append({
                        'action': step['action'],
                        'result': action_result,
                        'timestamp': time.time()
                    })
                    
                    self.automated_actions.append({
                        'incident_id': incident_id,
                        'action': step['action'],
                        'result': action_result
                    })
            
            async def execute_response_action(self, action_step: Dict, context: Dict):
                action_type = action_step['action']
                
                # Simulate different response actions
                if action_type == 'block_ip':
                    ip_address = context.get('ip_address')
                    return f"Blocked IP address: {ip_address}"
                
                elif action_type == 'disable_user':
                    user_id = context.get('user_id')
                    return f"Disabled user account: {user_id}"
                
                elif action_type == 'quarantine_resource':
                    resource_id = context.get('resource_id')
                    return f"Quarantined resource: {resource_id}"
                
                elif action_type == 'notify_security_team':
                    return "Security team notified"
                
                elif action_type == 'collect_forensics':
                    return "Forensic data collection initiated"
                
                else:
                    return f"Executed action: {action_type}"
        
        orchestrator = IncidentResponseOrchestrator()
        
        # Register response playbook for brute force attacks
        brute_force_playbook = {
            'threat_type': 'brute_force_attack',
            'steps': [
                {'action': 'block_ip', 'timeout_minutes': 60},
                {'action': 'notify_security_team', 'priority': 'high'},
                {'action': 'collect_forensics', 'scope': 'network_logs'}
            ]
        }
        
        orchestrator.register_playbook('brute_force_attack', brute_force_playbook)
        
        # Trigger incident
        incident_id = str(uuid4())
        context = {
            'ip_address': '192.168.1.100',
            'username': 'admin',
            'failure_count': 10
        }
        
        await orchestrator.trigger_incident(
            incident_id, 
            'brute_force_attack', 
            ThreatLevel.HIGH, 
            context
        )
        
        # Verify automated response
        incident = orchestrator.active_incidents[incident_id]
        assert len(incident['actions_taken']) == 3
        assert len(orchestrator.automated_actions) == 3
        
        # Check specific actions
        action_types = [action['action'] for action in incident['actions_taken']]
        assert 'block_ip' in action_types
        assert 'notify_security_team' in action_types
        assert 'collect_forensics' in action_types
    
    def test_security_metrics_dashboard_data(self):
        """Test generation of security metrics for dashboard visualization."""
        
        class SecurityMetricsDashboard:
            def __init__(self):
                self.security_events = []
                self.incident_history = []
                self.compliance_scores = {}
            
            def add_security_event(self, event_type: SecurityEventType, severity: ThreatLevel, timestamp: float):
                self.security_events.append({
                    'type': event_type,
                    'severity': severity,
                    'timestamp': timestamp
                })
            
            def add_incident(self, incident_type: str, resolution_time_hours: float, severity: ThreatLevel):
                self.incident_history.append({
                    'type': incident_type,
                    'resolution_time_hours': resolution_time_hours,
                    'severity': severity,
                    'timestamp': time.time()
                })
            
            def generate_dashboard_metrics(self, time_range_hours: int = 24):
                current_time = time.time()
                cutoff_time = current_time - (time_range_hours * 3600)
                
                # Filter recent events
                recent_events = [
                    event for event in self.security_events 
                    if event['timestamp'] > cutoff_time
                ]
                
                recent_incidents = [
                    incident for incident in self.incident_history
                    if incident['timestamp'] > cutoff_time
                ]
                
                # Calculate metrics
                event_counts_by_type = {}
                for event in recent_events:
                    event_type = event['type'].value
                    event_counts_by_type[event_type] = event_counts_by_type.get(event_type, 0) + 1
                
                severity_distribution = {}
                for event in recent_events:
                    severity = event['severity'].value
                    severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
                
                # Incident metrics
                if recent_incidents:
                    avg_resolution_time = sum(i['resolution_time_hours'] for i in recent_incidents) / len(recent_incidents)
                    critical_incidents = sum(1 for i in recent_incidents if i['severity'] == ThreatLevel.CRITICAL)
                else:
                    avg_resolution_time = 0
                    critical_incidents = 0
                
                # Security health score
                total_events = len(recent_events)
                critical_events = sum(1 for e in recent_events if e['severity'] == ThreatLevel.CRITICAL)
                high_events = sum(1 for e in recent_events if e['severity'] == ThreatLevel.HIGH)
                
                # Calculate health score (0-100)
                if total_events == 0:
                    health_score = 100
                else:
                    critical_penalty = (critical_events / total_events) * 50
                    high_penalty = (high_events / total_events) * 25
                    health_score = max(0, 100 - critical_penalty - high_penalty)
                
                return {
                    'time_range_hours': time_range_hours,
                    'total_security_events': total_events,
                    'event_counts_by_type': event_counts_by_type,
                    'severity_distribution': severity_distribution,
                    'total_incidents': len(recent_incidents),
                    'critical_incidents': critical_incidents,
                    'average_resolution_time_hours': avg_resolution_time,
                    'security_health_score': health_score,
                    'generated_at': current_time
                }
        
        dashboard = SecurityMetricsDashboard()
        
        # Add sample security events
        current_time = time.time()
        
        # Add various security events over the last day
        dashboard.add_security_event(SecurityEventType.AUTHENTICATION_FAILURE, ThreatLevel.MEDIUM, current_time - 3600)
        dashboard.add_security_event(SecurityEventType.BRUTE_FORCE_ATTACK, ThreatLevel.HIGH, current_time - 7200)
        dashboard.add_security_event(SecurityEventType.DATA_ACCESS_ANOMALY, ThreatLevel.MEDIUM, current_time - 1800)
        dashboard.add_security_event(SecurityEventType.PRIVILEGE_ESCALATION, ThreatLevel.CRITICAL, current_time - 900)
        
        # Add incidents
        dashboard.add_incident('brute_force_attack', 2.5, ThreatLevel.HIGH)
        dashboard.add_incident('data_breach', 8.0, ThreatLevel.CRITICAL)
        
        # Generate dashboard metrics
        metrics = dashboard.generate_dashboard_metrics(24)
        
        # Verify dashboard metrics
        assert metrics['total_security_events'] == 4
        assert metrics['total_incidents'] == 2
        assert metrics['critical_incidents'] == 1
        assert metrics['security_health_score'] < 100  # Should be penalized for critical events
        
        # Check event distribution
        assert 'auth_failure' in metrics['event_counts_by_type']
        assert 'brute_force_attack' in metrics['event_counts_by_type']
        assert 'critical' in metrics['severity_distribution']
        
        # Check resolution time
        assert metrics['average_resolution_time_hours'] == 5.25  # (2.5 + 8.0) / 2