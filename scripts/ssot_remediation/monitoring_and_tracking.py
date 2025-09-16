#!/usr/bin/env python3
"""
SSOT Remediation Monitoring and Compliance Tracking

Real-time monitoring and tracking system for SSOT remediation progress.
Ensures continuous compliance visibility and regression prevention.

Business Value: Platform/Internal - $500K+ ARR Protection
Priority: CRITICAL - Prevents compliance regression during remediation
"""

import os
import sys
import json
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import subprocess

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.isolated_environment import IsolatedEnvironment
from shared.windows_encoding import setup_windows_encoding

# Setup Windows encoding
setup_windows_encoding()


@dataclass
class ComplianceSnapshot:
    """Point-in-time compliance measurement."""
    timestamp: datetime
    overall_score: float
    production_score: float
    test_score: float
    total_violations: int
    critical_violations: int
    high_violations: int
    medium_violations: int
    low_violations: int
    phase: str
    commit_hash: str
    golden_path_status: bool


@dataclass
class RemediationProgress:
    """Progress tracking for remediation phases."""
    phase_name: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str  # "in_progress", "completed", "failed", "rolled_back"
    changes_made: List[str]
    compliance_improvement: float
    tests_affected: List[str]
    commits: List[str]


@dataclass
class QualityMetric:
    """Quality and performance metrics during remediation."""
    metric_name: str
    timestamp: datetime
    value: float
    unit: str
    phase: str
    threshold_status: str  # "ok", "warning", "critical"


class SSotComplianceTracker:
    """Comprehensive compliance tracking and monitoring system."""

    def __init__(self):
        """Initialize compliance tracker with persistent storage."""
        self.project_root = PROJECT_ROOT
        self.env = IsolatedEnvironment()

        # Setup tracking database
        self.tracking_dir = self.project_root / "reports" / "ssot_remediation" / "tracking"
        self.tracking_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.tracking_dir / "compliance_tracking.db"
        self._initialize_database()

    def _initialize_database(self):
        """Initialize SQLite database for compliance tracking."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Compliance snapshots table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS compliance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    overall_score REAL NOT NULL,
                    production_score REAL NOT NULL,
                    test_score REAL NOT NULL,
                    total_violations INTEGER NOT NULL,
                    critical_violations INTEGER NOT NULL,
                    high_violations INTEGER NOT NULL,
                    medium_violations INTEGER NOT NULL,
                    low_violations INTEGER NOT NULL,
                    phase TEXT NOT NULL,
                    commit_hash TEXT NOT NULL,
                    golden_path_status BOOLEAN NOT NULL
                )
            ''')

            # Remediation progress table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS remediation_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phase_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL,
                    changes_made TEXT NOT NULL,
                    compliance_improvement REAL NOT NULL,
                    tests_affected TEXT NOT NULL,
                    commits TEXT NOT NULL
                )
            ''')

            # Quality metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quality_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    threshold_status TEXT NOT NULL
                )
            ''')

            conn.commit()

    def capture_compliance_snapshot(self, phase: str = "unknown") -> ComplianceSnapshot:
        """Capture current compliance state."""
        print("📊 Capturing compliance snapshot...")

        # Get current commit hash
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            commit_hash = result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            commit_hash = "unknown"

        # Run compliance check
        try:
            result = subprocess.run(
                ["python", "scripts/check_architecture_compliance.py"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                compliance_data = self._parse_compliance_output(result.stdout)
            else:
                # Default values if compliance check fails
                compliance_data = {
                    "overall_score": 0.0,
                    "production_score": 0.0,
                    "test_score": 0.0,
                    "total_violations": 999,
                    "critical_violations": 999,
                    "high_violations": 0,
                    "medium_violations": 0,
                    "low_violations": 0
                }
        except Exception as e:
            print(f"Warning: Compliance check failed: {e}")
            compliance_data = {
                "overall_score": 0.0,
                "production_score": 0.0,
                "test_score": 0.0,
                "total_violations": 999,
                "critical_violations": 999,
                "high_violations": 0,
                "medium_violations": 0,
                "low_violations": 0
            }

        # Check Golden Path status
        golden_path_status = self._check_golden_path_status()

        snapshot = ComplianceSnapshot(
            timestamp=datetime.now(),
            overall_score=compliance_data["overall_score"],
            production_score=compliance_data["production_score"],
            test_score=compliance_data["test_score"],
            total_violations=compliance_data["total_violations"],
            critical_violations=compliance_data["critical_violations"],
            high_violations=compliance_data["high_violations"],
            medium_violations=compliance_data["medium_violations"],
            low_violations=compliance_data["low_violations"],
            phase=phase,
            commit_hash=commit_hash,
            golden_path_status=golden_path_status
        )

        # Store in database
        self._store_compliance_snapshot(snapshot)

        print(f"✅ Snapshot captured: {snapshot.overall_score:.1f}% compliance, "
              f"{snapshot.total_violations} violations, "
              f"Golden Path: {'OK' if golden_path_status else 'FAIL'}")

        return snapshot

    def start_phase_tracking(self, phase_name: str) -> str:
        """Start tracking a remediation phase."""
        print(f"🚀 Starting phase tracking: {phase_name}")

        # Capture baseline snapshot
        baseline_snapshot = self.capture_compliance_snapshot(phase_name)

        progress = RemediationProgress(
            phase_name=phase_name,
            start_time=datetime.now(),
            end_time=None,
            status="in_progress",
            changes_made=[],
            compliance_improvement=0.0,
            tests_affected=[],
            commits=[]
        )

        # Store in database
        phase_id = self._store_remediation_progress(progress)

        print(f"✅ Phase tracking started: {phase_name} (ID: {phase_id})")
        print(f"   Baseline compliance: {baseline_snapshot.overall_score:.1f}%")

        return str(phase_id)

    def update_phase_progress(self, phase_name: str, change_description: str,
                            test_files: List[str] = None, commit_hash: str = None):
        """Update progress for an ongoing phase."""
        print(f"📝 Updating phase progress: {phase_name} - {change_description}")

        # Capture current snapshot
        current_snapshot = self.capture_compliance_snapshot(phase_name)

        # Get baseline for comparison
        baseline_snapshot = self._get_latest_snapshot_for_phase(phase_name, "baseline")
        compliance_improvement = current_snapshot.overall_score - baseline_snapshot.overall_score if baseline_snapshot else 0.0

        # Update database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get current progress
            cursor.execute('''
                SELECT changes_made, tests_affected, commits
                FROM remediation_progress
                WHERE phase_name = ? AND status = 'in_progress'
                ORDER BY start_time DESC LIMIT 1
            ''', (phase_name,))

            result = cursor.fetchone()
            if result:
                current_changes = json.loads(result[0])
                current_tests = json.loads(result[1])
                current_commits = json.loads(result[2])

                # Add new information
                current_changes.append(change_description)
                if test_files:
                    current_tests.extend(test_files)
                if commit_hash:
                    current_commits.append(commit_hash)

                # Update record
                cursor.execute('''
                    UPDATE remediation_progress
                    SET changes_made = ?, tests_affected = ?, commits = ?, compliance_improvement = ?
                    WHERE phase_name = ? AND status = 'in_progress'
                ''', (
                    json.dumps(current_changes),
                    json.dumps(current_tests),
                    json.dumps(current_commits),
                    compliance_improvement,
                    phase_name
                ))

                conn.commit()

        print(f"✅ Progress updated: +{compliance_improvement:.2f}% compliance improvement")

    def complete_phase_tracking(self, phase_name: str, success: bool = True):
        """Complete tracking for a remediation phase."""
        status = "completed" if success else "failed"
        print(f"🏁 Completing phase tracking: {phase_name} - {status.upper()}")

        # Capture final snapshot
        final_snapshot = self.capture_compliance_snapshot(phase_name)

        # Update database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE remediation_progress
                SET end_time = ?, status = ?
                WHERE phase_name = ? AND status = 'in_progress'
            ''', (datetime.now().isoformat(), status, phase_name))

            conn.commit()

        print(f"✅ Phase completed: {final_snapshot.overall_score:.1f}% final compliance")

    def record_quality_metric(self, metric_name: str, value: float, unit: str,
                            phase: str, threshold_warning: float = None,
                            threshold_critical: float = None):
        """Record a quality metric with threshold checking."""

        # Determine threshold status
        threshold_status = "ok"
        if threshold_critical is not None and value >= threshold_critical:
            threshold_status = "critical"
        elif threshold_warning is not None and value >= threshold_warning:
            threshold_status = "warning"

        metric = QualityMetric(
            metric_name=metric_name,
            timestamp=datetime.now(),
            value=value,
            unit=unit,
            phase=phase,
            threshold_status=threshold_status
        )

        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO quality_metrics
                (metric_name, timestamp, value, unit, phase, threshold_status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                metric.metric_name,
                metric.timestamp.isoformat(),
                metric.value,
                metric.unit,
                metric.phase,
                metric.threshold_status
            ))

            conn.commit()

        status_icon = {"ok": "✅", "warning": "⚠️", "critical": "🚨"}[threshold_status]
        print(f"{status_icon} Quality metric recorded: {metric_name} = {value} {unit}")

    def generate_compliance_trend_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate compliance trend report for recent period."""
        print(f"📊 Generating compliance trend report (last {hours} hours)...")

        cutoff_time = datetime.now() - timedelta(hours=hours)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get compliance snapshots
            cursor.execute('''
                SELECT * FROM compliance_snapshots
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            ''', (cutoff_time.isoformat(),))

            snapshots = cursor.fetchall()

            # Get remediation progress
            cursor.execute('''
                SELECT * FROM remediation_progress
                WHERE start_time > ?
                ORDER BY start_time ASC
            ''', (cutoff_time.isoformat(),))

            progress_records = cursor.fetchall()

            # Get quality metrics
            cursor.execute('''
                SELECT * FROM quality_metrics
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            ''', (cutoff_time.isoformat(),))

            quality_records = cursor.fetchall()

        # Calculate trends
        if len(snapshots) >= 2:
            first_score = snapshots[0][2]  # overall_score
            last_score = snapshots[-1][2]
            trend = last_score - first_score
        else:
            trend = 0.0

        # Count violations trend
        if len(snapshots) >= 2:
            first_violations = snapshots[0][5]  # total_violations
            last_violations = snapshots[-1][5]
            violations_trend = last_violations - first_violations
        else:
            violations_trend = 0

        report = {
            "report_timestamp": datetime.now().isoformat(),
            "period_hours": hours,
            "compliance_trend": {
                "score_change": trend,
                "violations_change": violations_trend,
                "snapshots_count": len(snapshots)
            },
            "current_status": {
                "overall_score": snapshots[-1][2] if snapshots else 0.0,
                "total_violations": snapshots[-1][5] if snapshots else 999,
                "golden_path_status": bool(snapshots[-1][12]) if snapshots else False
            },
            "remediation_activity": {
                "phases_active": len([r for r in progress_records if r[4] == "in_progress"]),
                "phases_completed": len([r for r in progress_records if r[4] == "completed"]),
                "phases_failed": len([r for r in progress_records if r[4] == "failed"])
            },
            "quality_alerts": {
                "critical_metrics": len([m for m in quality_records if m[6] == "critical"]),
                "warning_metrics": len([m for m in quality_records if m[6] == "warning"])
            }
        }

        # Save report
        report_file = self.tracking_dir / f"compliance_trend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        print(f"✅ Trend report generated: {report_file}")
        print(f"   Compliance trend: {trend:+.2f}%")
        print(f"   Violations trend: {violations_trend:+d}")

        return report

    def check_regression_alerts(self) -> List[Dict[str, Any]]:
        """Check for compliance regression alerts."""
        alerts = []

        # Get recent snapshots
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT overall_score, total_violations, golden_path_status, timestamp
                FROM compliance_snapshots
                ORDER BY timestamp DESC LIMIT 5
            ''')

            recent_snapshots = cursor.fetchall()

        if len(recent_snapshots) >= 2:
            current = recent_snapshots[0]
            previous = recent_snapshots[1]

            # Check for compliance score decrease
            if current[0] < previous[0] - 1.0:  # >1% decrease
                alerts.append({
                    "type": "compliance_regression",
                    "severity": "high",
                    "message": f"Compliance score decreased from {previous[0]:.1f}% to {current[0]:.1f}%",
                    "timestamp": current[3]
                })

            # Check for violation increase
            if current[1] > previous[1] + 5:  # >5 additional violations
                alerts.append({
                    "type": "violations_increase",
                    "severity": "medium",
                    "message": f"Violations increased from {previous[1]} to {current[1]}",
                    "timestamp": current[3]
                })

            # Check for Golden Path failure
            if not current[2] and previous[2]:  # Golden Path went from OK to FAIL
                alerts.append({
                    "type": "golden_path_failure",
                    "severity": "critical",
                    "message": "Golden Path functionality has failed",
                    "timestamp": current[3]
                })

        return alerts

    def _parse_compliance_output(self, output: str) -> Dict[str, Any]:
        """Parse compliance check output to extract metrics."""
        import re

        # Default values
        data = {
            "overall_score": 0.0,
            "production_score": 100.0,  # Assume production is clean unless stated otherwise
            "test_score": 0.0,
            "total_violations": 999,
            "critical_violations": 0,
            "high_violations": 0,
            "medium_violations": 0,
            "low_violations": 0
        }

        # Extract compliance score
        score_match = re.search(r'Compliance Score:\s*(\d+\.?\d*)%', output)
        if score_match:
            data["overall_score"] = float(score_match.group(1))

        # Extract total violations
        violations_match = re.search(r'Total Violations:\s*(\d+)', output)
        if violations_match:
            data["total_violations"] = int(violations_match.group(1))

        # Extract production score
        production_match = re.search(r'Real System:\s*(\d+\.?\d*)%\s*compliant', output)
        if production_match:
            data["production_score"] = float(production_match.group(1))

        # Extract test score
        test_match = re.search(r'Test Files:\s*(\d+\.?\d*)%\s*compliant', output)
        if test_match:
            data["test_score"] = float(test_match.group(1))

        return data

    def _check_golden_path_status(self) -> bool:
        """Check if Golden Path is operational."""
        try:
            result = subprocess.run(
                ["python", "tests/mission_critical/test_websocket_agent_events_suite.py"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            return result.returncode == 0
        except Exception:
            return False

    def _store_compliance_snapshot(self, snapshot: ComplianceSnapshot):
        """Store compliance snapshot in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO compliance_snapshots
                (timestamp, overall_score, production_score, test_score, total_violations,
                 critical_violations, high_violations, medium_violations, low_violations,
                 phase, commit_hash, golden_path_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot.timestamp.isoformat(),
                snapshot.overall_score,
                snapshot.production_score,
                snapshot.test_score,
                snapshot.total_violations,
                snapshot.critical_violations,
                snapshot.high_violations,
                snapshot.medium_violations,
                snapshot.low_violations,
                snapshot.phase,
                snapshot.commit_hash,
                snapshot.golden_path_status
            ))

            conn.commit()

    def _store_remediation_progress(self, progress: RemediationProgress) -> int:
        """Store remediation progress in database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO remediation_progress
                (phase_name, start_time, end_time, status, changes_made,
                 compliance_improvement, tests_affected, commits)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                progress.phase_name,
                progress.start_time.isoformat(),
                progress.end_time.isoformat() if progress.end_time else None,
                progress.status,
                json.dumps(progress.changes_made),
                progress.compliance_improvement,
                json.dumps(progress.tests_affected),
                json.dumps(progress.commits)
            ))

            conn.commit()
            return cursor.lastrowid

    def _get_latest_snapshot_for_phase(self, phase: str, snapshot_type: str = "latest") -> Optional[ComplianceSnapshot]:
        """Get latest snapshot for a specific phase."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if snapshot_type == "baseline":
                # Get first snapshot for phase (baseline)
                cursor.execute('''
                    SELECT * FROM compliance_snapshots
                    WHERE phase = ?
                    ORDER BY timestamp ASC LIMIT 1
                ''', (phase,))
            else:
                # Get latest snapshot for phase
                cursor.execute('''
                    SELECT * FROM compliance_snapshots
                    WHERE phase = ?
                    ORDER BY timestamp DESC LIMIT 1
                ''', (phase,))

            result = cursor.fetchone()

            if result:
                return ComplianceSnapshot(
                    timestamp=datetime.fromisoformat(result[1]),
                    overall_score=result[2],
                    production_score=result[3],
                    test_score=result[4],
                    total_violations=result[5],
                    critical_violations=result[6],
                    high_violations=result[7],
                    medium_violations=result[8],
                    low_violations=result[9],
                    phase=result[10],
                    commit_hash=result[11],
                    golden_path_status=bool(result[12])
                )

            return None


def main():
    """Main entry point for monitoring and tracking."""
    if len(sys.argv) < 2:
        print("Usage: python monitoring_and_tracking.py <command> [args...]")
        print("Commands:")
        print("  snapshot [phase]           - Capture compliance snapshot")
        print("  start-phase <phase_name>   - Start phase tracking")
        print("  update-phase <phase_name> <description> [test_files] [commit_hash]")
        print("  complete-phase <phase_name> [success|failed]")
        print("  trend-report [hours]       - Generate trend report")
        print("  check-alerts              - Check for regression alerts")
        sys.exit(1)

    command = sys.argv[1]
    tracker = SSotComplianceTracker()

    if command == "snapshot":
        phase = sys.argv[2] if len(sys.argv) > 2 else "manual"
        tracker.capture_compliance_snapshot(phase)

    elif command == "start-phase":
        if len(sys.argv) < 3:
            print("Error: phase_name required")
            sys.exit(1)
        phase_name = sys.argv[2]
        tracker.start_phase_tracking(phase_name)

    elif command == "update-phase":
        if len(sys.argv) < 4:
            print("Error: phase_name and description required")
            sys.exit(1)
        phase_name = sys.argv[2]
        description = sys.argv[3]
        test_files = sys.argv[4].split(",") if len(sys.argv) > 4 else None
        commit_hash = sys.argv[5] if len(sys.argv) > 5 else None
        tracker.update_phase_progress(phase_name, description, test_files, commit_hash)

    elif command == "complete-phase":
        if len(sys.argv) < 3:
            print("Error: phase_name required")
            sys.exit(1)
        phase_name = sys.argv[2]
        success = sys.argv[3] != "failed" if len(sys.argv) > 3 else True
        tracker.complete_phase_tracking(phase_name, success)

    elif command == "trend-report":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        tracker.generate_compliance_trend_report(hours)

    elif command == "check-alerts":
        alerts = tracker.check_regression_alerts()
        if alerts:
            print("🚨 REGRESSION ALERTS DETECTED:")
            for alert in alerts:
                severity_icon = {"critical": "🚨", "high": "⚠️", "medium": "⚠️"}[alert["severity"]]
                print(f"  {severity_icon} {alert['type']}: {alert['message']}")
        else:
            print("✅ No regression alerts detected")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()