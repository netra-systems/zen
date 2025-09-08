#!/usr/bin/env python3
"""
Remediation Business Value Dashboard

Provides comprehensive business value tracking and reporting for the Critical
Remediation System, focusing on quantifiable business outcomes and ROI from
systematic P0 issue remediation.

Features:
- MRR protection and revenue impact tracking
- System uptime and availability metrics
- Cost-benefit analysis of remediation efforts
- Executive-level business reporting
- ROI calculation for remediation process
- Predictive analytics for business risk
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import subprocess
import statistics

# Import remediation infrastructure
from scripts.critical_remediation_tracker import CriticalRemediationTracker, IssueStatus, IssuePriority

logger = logging.getLogger(__name__)


class BusinessMetricsCalculator:
    """Calculates business value metrics for remediation tracking"""
    
    def __init__(self, base_mrr: float = 50000.0, target_uptime: float = 99.9):
        """
        Initialize with business parameters
        
        Args:
            base_mrr: Monthly Recurring Revenue baseline ($)
            target_uptime: Target system uptime percentage
        """
        self.base_mrr = base_mrr
        self.target_uptime = target_uptime
        self.hourly_revenue = base_mrr / (30 * 24)  # Approximate hourly revenue
        
        # Business impact multipliers based on issue priority
        self.priority_impact_multipliers = {
            IssuePriority.P0: 0.15,  # P0 issues can affect up to 15% of MRR
            IssuePriority.P1: 0.08,  # P1 issues can affect up to 8% of MRR  
            IssuePriority.P2: 0.03,  # P2 issues can affect up to 3% of MRR
            IssuePriority.P3: 0.01   # P3 issues can affect up to 1% of MRR
        }
        
        # Cost estimates for remediation activities
        self.remediation_costs = {
            "engineer_hourly_rate": 150.0,  # Loaded cost per engineer hour
            "p0_average_hours": 8,           # Average hours to fix P0
            "p1_average_hours": 16,          # Average hours to fix P1
            "system_downtime_cost_per_hour": self.hourly_revenue * 0.8,  # 80% revenue impact during downtime
            "customer_churn_cost_per_incident": 2500.0  # Average cost of customer churn from incidents
        }

    def calculate_mrr_at_risk(self, issue_priority: IssuePriority, duration_hours: float = 24.0) -> float:
        """Calculate MRR at risk for a given issue priority and duration"""
        base_risk = self.base_mrr * self.priority_impact_multipliers[issue_priority]
        
        # Scale risk based on duration - longer unresolved issues have higher impact
        duration_multiplier = min(1.0 + (duration_hours / 168), 2.0)  # Cap at 2x for week+ issues
        
        return base_risk * duration_multiplier

    def calculate_revenue_impact(self, downtime_hours: float) -> Dict[str, float]:
        """Calculate revenue impact of system downtime"""
        direct_revenue_loss = downtime_hours * self.remediation_costs["system_downtime_cost_per_hour"]
        
        # Estimate customer churn impact based on downtime severity
        churn_incidents = max(0, (downtime_hours - 1) / 4)  # 1+ incidents for every 4 hours of downtime
        churn_impact = churn_incidents * self.remediation_costs["customer_churn_cost_per_incident"]
        
        # Estimate recovery time impact (reduced performance after restoration)
        recovery_impact = direct_revenue_loss * 0.1  # 10% additional impact during recovery
        
        return {
            "direct_revenue_loss": direct_revenue_loss,
            "customer_churn_impact": churn_impact,
            "recovery_impact": recovery_impact,
            "total_impact": direct_revenue_loss + churn_impact + recovery_impact
        }

    def calculate_remediation_cost(self, issue_priority: IssuePriority, actual_hours: Optional[float] = None) -> float:
        """Calculate cost of remediation efforts"""
        if actual_hours:
            engineer_hours = actual_hours
        else:
            # Use average based on priority
            if issue_priority == IssuePriority.P0:
                engineer_hours = self.remediation_costs["p0_average_hours"]
            elif issue_priority == IssuePriority.P1:
                engineer_hours = self.remediation_costs["p1_average_hours"]
            else:
                engineer_hours = 4.0  # Default for lower priority
        
        return engineer_hours * self.remediation_costs["engineer_hourly_rate"]

    def calculate_roi(self, value_protected: float, remediation_cost: float) -> Dict[str, float]:
        """Calculate Return on Investment for remediation"""
        if remediation_cost <= 0:
            return {"roi_ratio": float('inf'), "roi_percentage": float('inf'), "net_benefit": value_protected}
        
        roi_ratio = value_protected / remediation_cost
        roi_percentage = ((value_protected - remediation_cost) / remediation_cost) * 100
        net_benefit = value_protected - remediation_cost
        
        return {
            "roi_ratio": roi_ratio,
            "roi_percentage": roi_percentage, 
            "net_benefit": net_benefit
        }

    def calculate_prevention_value(self, similar_incidents_prevented: int, avg_incident_cost: float) -> float:
        """Calculate value of prevention measures"""
        return similar_incidents_prevented * avg_incident_cost


class BusinessValueDashboard:
    """Main dashboard for business value reporting"""
    
    def __init__(self, data_dir: str = "reports/remediation"):
        self.tracker = CriticalRemediationTracker(data_dir)
        self.metrics_calculator = BusinessMetricsCalculator()
        self.data_dir = Path(data_dir)
        self.dashboard_dir = self.data_dir / "dashboard"
        self.dashboard_dir.mkdir(parents=True, exist_ok=True)
        
        self.business_config_file = self.dashboard_dir / "business_config.json"
        self.metrics_history_file = self.dashboard_dir / "metrics_history.json"
        
        self._load_business_config()

    def _load_business_config(self):
        """Load business configuration parameters"""
        default_config = {
            "base_mrr": 50000.0,
            "target_uptime_percentage": 99.9,
            "customer_base_size": 150,
            "average_customer_value": 333.33,  # base_mrr / customer_base_size
            "churn_rate_threshold": 5.0,  # Percentage monthly churn that triggers alerts
            "uptime_sla_threshold": 99.0,  # SLA threshold
            "business_hours": {
                "start_hour": 8,
                "end_hour": 18,
                "timezone": "UTC",
                "business_days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
            },
            "cost_centers": {
                "engineering_team_size": 5,
                "average_engineer_salary": 120000.0,
                "infrastructure_monthly_cost": 5000.0,
                "support_overhead_monthly": 8000.0
            }
        }
        
        if self.business_config_file.exists():
            with open(self.business_config_file, 'r') as f:
                loaded_config = json.load(f)
                self.business_config = {**default_config, **loaded_config}
        else:
            self.business_config = default_config
            self._save_business_config()
        
        # Update metrics calculator with loaded config
        self.metrics_calculator = BusinessMetricsCalculator(
            base_mrr=self.business_config["base_mrr"],
            target_uptime=self.business_config["target_uptime_percentage"]
        )

    def _save_business_config(self):
        """Save business configuration"""
        with open(self.business_config_file, 'w') as f:
            json.dump(self.business_config, f, indent=2)

    def calculate_comprehensive_business_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive business metrics for all tracked issues"""
        metrics = {
            "calculation_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_mrr_at_risk": 0.0,
                "total_mrr_protected": 0.0,
                "total_remediation_cost": 0.0,
                "overall_roi": 0.0,
                "issues_by_priority": {},
                "issues_by_status": {}
            },
            "priority_breakdown": {},
            "roi_analysis": {},
            "prevention_value": {},
            "temporal_analysis": {},
            "business_impact_forecast": {}
        }
        
        try:
            active_issues = []
            completed_issues = []
            
            # Categorize issues
            for issue in self.tracker.issues.values():
                if issue.status in [IssueStatus.IDENTIFIED, IssueStatus.PLANNED, IssueStatus.IN_PROGRESS]:
                    active_issues.append(issue)
                elif issue.status in [IssueStatus.COMPLETED, IssueStatus.VALIDATED]:
                    completed_issues.append(issue)
                
                # Count by priority and status
                priority_key = issue.priority.value
                status_key = issue.status.value
                
                metrics["summary"]["issues_by_priority"][priority_key] = metrics["summary"]["issues_by_priority"].get(priority_key, 0) + 1
                metrics["summary"]["issues_by_status"][status_key] = metrics["summary"]["issues_by_status"].get(status_key, 0) + 1
            
            # Calculate MRR at risk from active issues
            for issue in active_issues:
                duration_hours = (datetime.now() - issue.created_at).total_seconds() / 3600
                mrr_at_risk = self.metrics_calculator.calculate_mrr_at_risk(issue.priority, duration_hours)
                metrics["summary"]["total_mrr_at_risk"] += mrr_at_risk
                
                # Store individual issue risk
                if issue.priority.value not in metrics["priority_breakdown"]:
                    metrics["priority_breakdown"][issue.priority.value] = {
                        "count": 0,
                        "total_mrr_at_risk": 0.0,
                        "avg_age_hours": 0.0,
                        "issues": []
                    }
                
                metrics["priority_breakdown"][issue.priority.value]["count"] += 1
                metrics["priority_breakdown"][issue.priority.value]["total_mrr_at_risk"] += mrr_at_risk
                metrics["priority_breakdown"][issue.priority.value]["issues"].append({
                    "issue_id": issue.issue_id,
                    "title": issue.title[:50],
                    "mrr_at_risk": mrr_at_risk,
                    "age_hours": duration_hours,
                    "owner": issue.owner
                })
            
            # Calculate average age by priority
            for priority_data in metrics["priority_breakdown"].values():
                if priority_data["issues"]:
                    priority_data["avg_age_hours"] = statistics.mean([i["age_hours"] for i in priority_data["issues"]])
            
            # Calculate MRR protected and ROI from completed issues
            total_remediation_cost = 0.0
            
            for issue in completed_issues:
                resolution_time_hours = (issue.updated_at - issue.created_at).total_seconds() / 3600
                
                # Calculate value protected
                mrr_protected = self.metrics_calculator.calculate_mrr_at_risk(issue.priority, resolution_time_hours)
                metrics["summary"]["total_mrr_protected"] += mrr_protected
                
                # Calculate remediation cost
                remediation_cost = self.metrics_calculator.calculate_remediation_cost(issue.priority, resolution_time_hours)
                total_remediation_cost += remediation_cost
            
            metrics["summary"]["total_remediation_cost"] = total_remediation_cost
            
            # Calculate overall ROI
            if total_remediation_cost > 0:
                overall_roi = self.metrics_calculator.calculate_roi(
                    metrics["summary"]["total_mrr_protected"],
                    total_remediation_cost
                )
                metrics["summary"]["overall_roi"] = overall_roi["roi_percentage"]
                metrics["roi_analysis"] = overall_roi
            
            # Add temporal analysis
            metrics["temporal_analysis"] = self._calculate_temporal_trends()
            
            # Add business impact forecast
            metrics["business_impact_forecast"] = self._calculate_business_forecast(active_issues)
            
            # Calculate prevention value
            metrics["prevention_value"] = self._calculate_prevention_metrics(completed_issues)
            
        except Exception as e:
            logger.error(f"Error calculating business metrics: {str(e)}")
            metrics["error"] = str(e)
        
        return metrics

    def _calculate_temporal_trends(self) -> Dict[str, Any]:
        """Calculate temporal trends in remediation performance"""
        trends = {
            "last_30_days": {"issues_created": 0, "issues_resolved": 0, "avg_resolution_time_hours": 0.0},
            "last_7_days": {"issues_created": 0, "issues_resolved": 0, "avg_resolution_time_hours": 0.0},
            "resolution_time_trend": "stable",  # improving, degrading, stable
            "volume_trend": "stable"  # increasing, decreasing, stable
        }
        
        now = datetime.now()
        
        # Analyze last 30 days
        last_30_days = now - timedelta(days=30)
        last_7_days = now - timedelta(days=7)
        
        recent_resolved_30d = []
        recent_resolved_7d = []
        
        for issue in self.tracker.issues.values():
            # Count issues created in timeframes
            if issue.created_at >= last_30_days:
                trends["last_30_days"]["issues_created"] += 1
            if issue.created_at >= last_7_days:
                trends["last_7_days"]["issues_created"] += 1
            
            # Count issues resolved in timeframes
            if issue.status in [IssueStatus.COMPLETED, IssueStatus.VALIDATED]:
                resolution_time_hours = (issue.updated_at - issue.created_at).total_seconds() / 3600
                
                if issue.updated_at >= last_30_days:
                    trends["last_30_days"]["issues_resolved"] += 1
                    recent_resolved_30d.append(resolution_time_hours)
                    
                if issue.updated_at >= last_7_days:
                    trends["last_7_days"]["issues_resolved"] += 1
                    recent_resolved_7d.append(resolution_time_hours)
        
        # Calculate average resolution times
        if recent_resolved_30d:
            trends["last_30_days"]["avg_resolution_time_hours"] = statistics.mean(recent_resolved_30d)
        if recent_resolved_7d:
            trends["last_7_days"]["avg_resolution_time_hours"] = statistics.mean(recent_resolved_7d)
        
        # Determine trends
        if len(recent_resolved_7d) >= 3 and len(recent_resolved_30d) >= 10:
            avg_7d = trends["last_7_days"]["avg_resolution_time_hours"]
            avg_30d = trends["last_30_days"]["avg_resolution_time_hours"]
            
            if avg_7d < avg_30d * 0.9:
                trends["resolution_time_trend"] = "improving"
            elif avg_7d > avg_30d * 1.1:
                trends["resolution_time_trend"] = "degrading"
        
        # Volume trend
        create_7d = trends["last_7_days"]["issues_created"]
        create_30d = trends["last_30_days"]["issues_created"]
        avg_daily_30d = create_30d / 30
        avg_daily_7d = create_7d / 7
        
        if avg_daily_7d > avg_daily_30d * 1.2:
            trends["volume_trend"] = "increasing"
        elif avg_daily_7d < avg_daily_30d * 0.8:
            trends["volume_trend"] = "decreasing"
        
        return trends

    def _calculate_business_forecast(self, active_issues: List) -> Dict[str, Any]:
        """Calculate business impact forecast based on active issues"""
        forecast = {
            "next_24_hours": {"mrr_at_risk": 0.0, "expected_resolutions": 0},
            "next_7_days": {"mrr_at_risk": 0.0, "expected_resolutions": 0},
            "next_30_days": {"mrr_at_risk": 0.0, "expected_resolutions": 0},
            "risk_level": "low",  # low, medium, high, critical
            "recommended_actions": []
        }
        
        now = datetime.now()
        total_risk_score = 0.0
        
        for issue in active_issues:
            age_hours = (now - issue.created_at).total_seconds() / 3600
            current_risk = self.metrics_calculator.calculate_mrr_at_risk(issue.priority, age_hours)
            
            # Calculate risk growth over time
            risk_24h = self.metrics_calculator.calculate_mrr_at_risk(issue.priority, age_hours + 24)
            risk_7d = self.metrics_calculator.calculate_mrr_at_risk(issue.priority, age_hours + 168)
            risk_30d = self.metrics_calculator.calculate_mrr_at_risk(issue.priority, age_hours + 720)
            
            forecast["next_24_hours"]["mrr_at_risk"] += risk_24h
            forecast["next_7_days"]["mrr_at_risk"] += risk_7d
            forecast["next_30_days"]["mrr_at_risk"] += risk_30d
            
            # Estimate resolution probability based on age and priority
            if issue.priority == IssuePriority.P0:
                if age_hours < 24:
                    forecast["next_24_hours"]["expected_resolutions"] += 0.8
                elif age_hours < 168:
                    forecast["next_7_days"]["expected_resolutions"] += 0.9
                else:
                    forecast["next_30_days"]["expected_resolutions"] += 0.95
            elif issue.priority == IssuePriority.P1:
                if age_hours < 72:
                    forecast["next_7_days"]["expected_resolutions"] += 0.7
                else:
                    forecast["next_30_days"]["expected_resolutions"] += 0.85
            
            # Calculate risk score for overall risk level
            priority_weight = {IssuePriority.P0: 4, IssuePriority.P1: 2, IssuePriority.P2: 1, IssuePriority.P3: 0.5}
            age_weight = min(age_hours / 24, 5)  # Cap at 5x weight for very old issues
            total_risk_score += priority_weight.get(issue.priority, 1) * age_weight
        
        # Determine overall risk level
        if total_risk_score >= 20:
            forecast["risk_level"] = "critical"
            forecast["recommended_actions"].extend([
                "Immediate executive escalation required",
                "Consider emergency resource allocation",
                "Activate incident response team"
            ])
        elif total_risk_score >= 10:
            forecast["risk_level"] = "high"
            forecast["recommended_actions"].extend([
                "Management attention required",
                "Consider additional resource allocation",
                "Daily status reviews recommended"
            ])
        elif total_risk_score >= 5:
            forecast["risk_level"] = "medium"
            forecast["recommended_actions"].extend([
                "Monitor closely",
                "Ensure adequate resource allocation"
            ])
        
        # Add specific recommendations based on forecast
        if forecast["next_24_hours"]["mrr_at_risk"] > self.business_config["base_mrr"] * 0.1:
            forecast["recommended_actions"].append("High MRR at risk in next 24 hours - prioritize P0 resolution")
        
        return forecast

    def _calculate_prevention_metrics(self, completed_issues: List) -> Dict[str, Any]:
        """Calculate value of prevention measures implemented"""
        prevention = {
            "total_prevention_value": 0.0,
            "avg_prevention_measures_per_issue": 0.0,
            "prevention_effectiveness_score": 0.0,
            "recurrence_rate": 0.0,
            "top_prevention_categories": {}
        }
        
        if not completed_issues:
            return prevention
        
        total_prevention_measures = 0
        prevention_categories = {}
        
        for issue in completed_issues:
            if issue.recurrence_prevention:
                total_prevention_measures += len(issue.recurrence_prevention)
                
                # Categorize prevention measures
                for measure in issue.recurrence_prevention:
                    # Simple categorization based on keywords
                    if any(keyword in measure.lower() for keyword in ['test', 'testing']):
                        category = "Testing Improvements"
                    elif any(keyword in measure.lower() for keyword in ['monitor', 'alert', 'observability']):
                        category = "Monitoring & Alerting"
                    elif any(keyword in measure.lower() for keyword in ['documentation', 'guide', 'process']):
                        category = "Process & Documentation"
                    elif any(keyword in measure.lower() for keyword in ['automation', 'lint', 'check']):
                        category = "Automation"
                    else:
                        category = "Other"
                    
                    prevention_categories[category] = prevention_categories.get(category, 0) + 1
        
        prevention["avg_prevention_measures_per_issue"] = total_prevention_measures / len(completed_issues)
        
        # Calculate prevention value (simplified)
        # Assume each prevention measure prevents 1 similar incident per year
        avg_incident_cost = 5000.0  # Average cost of a similar incident
        prevention["total_prevention_value"] = total_prevention_measures * avg_incident_cost
        
        # Calculate prevention effectiveness score
        issues_with_prevention = sum(1 for issue in completed_issues if issue.recurrence_prevention)
        prevention["prevention_effectiveness_score"] = (issues_with_prevention / len(completed_issues)) * 100
        
        # Sort prevention categories
        prevention["top_prevention_categories"] = dict(sorted(
            prevention_categories.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5])
        
        return prevention

    def generate_executive_report(self) -> str:
        """Generate executive-level business report"""
        metrics = self.calculate_comprehensive_business_metrics()
        
        report = f"""
# Executive Remediation Business Report
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📊 Business Impact Summary

### Financial Metrics
- **MRR Currently at Risk:** ${metrics['summary']['total_mrr_at_risk']:,.0f}
- **MRR Protected (MTD):** ${metrics['summary']['total_mrr_protected']:,.0f} 
- **Remediation Investment:** ${metrics['summary']['total_remediation_cost']:,.0f}
- **Return on Investment:** {metrics['summary']['overall_roi']:.1f}%

### Operational Metrics  
- **Active Issues:** {sum(metrics['summary']['issues_by_status'].get(status, 0) for status in ['identified', 'planned', 'in_progress'])}
- **Completed This Period:** {metrics['summary']['issues_by_status'].get('completed', 0) + metrics['summary']['issues_by_status'].get('validated', 0)}
- **Average Resolution Time:** {metrics['temporal_analysis']['last_30_days']['avg_resolution_time_hours']:.1f} hours

## 🎯 Risk Assessment

### Current Risk Level: **{metrics['business_impact_forecast']['risk_level'].upper()}**

#### Critical Issues (P0)
"""
        
        p0_issues = metrics['priority_breakdown'].get('p0', {})
        if p0_issues.get('count', 0) > 0:
            report += f"- **{p0_issues['count']} active P0 issues**\n"
            report += f"- **${p0_issues['total_mrr_at_risk']:,.0f} MRR at risk**\n"
            report += f"- **Average age: {p0_issues['avg_age_hours']:.1f} hours**\n"
            
            for issue in p0_issues.get('issues', [])[:3]:  # Top 3 P0 issues
                report += f"  - {issue['issue_id']}: {issue['title']} (${issue['mrr_at_risk']:,.0f} at risk)\n"
        else:
            report += "- ✅ No active P0 issues\n"
        
        report += f"""
## 📈 Performance Trends

### Resolution Performance
- **7-day trend:** {metrics['temporal_analysis']['resolution_time_trend']}
- **Volume trend:** {metrics['temporal_analysis']['volume_trend']}
- **Issues resolved (7d):** {metrics['temporal_analysis']['last_7_days']['issues_resolved']}
- **Issues created (7d):** {metrics['temporal_analysis']['last_7_days']['issues_created']}

## 🔮 Forecast & Recommendations

### Next 24 Hours
- **Additional MRR at risk:** ${metrics['business_impact_forecast']['next_24_hours']['mrr_at_risk'] - metrics['summary']['total_mrr_at_risk']:,.0f}
- **Expected resolutions:** {metrics['business_impact_forecast']['next_24_hours']['expected_resolutions']:.0f}

### Immediate Actions Required
"""
        
        for action in metrics['business_impact_forecast']['recommended_actions'][:5]:
            report += f"- {action}\n"
        
        report += f"""
## 💡 Prevention & Process Improvements

### Prevention Value This Period
- **Total prevention value:** ${metrics['prevention_value']['total_prevention_value']:,.0f}
- **Prevention effectiveness:** {metrics['prevention_value']['prevention_effectiveness_score']:.1f}%
- **Avg prevention measures per issue:** {metrics['prevention_value']['avg_prevention_measures_per_issue']:.1f}

### Top Prevention Categories
"""
        
        for category, count in list(metrics['prevention_value']['top_prevention_categories'].items())[:3]:
            report += f"- **{category}:** {count} measures\n"
        
        # Add ROI analysis if available
        if 'roi_analysis' in metrics and metrics['roi_analysis']:
            roi = metrics['roi_analysis']
            report += f"""
## 💰 Return on Investment Analysis

- **ROI Ratio:** {roi['roi_ratio']:.1f}:1 (${roi['roi_ratio']:.1f} value for every $1 spent)
- **ROI Percentage:** {roi['roi_percentage']:.1f}%
- **Net Benefit:** ${roi['net_benefit']:,.0f}

*ROI Interpretation:*
"""
            if roi['roi_percentage'] > 500:
                report += "- 🟢 **Excellent ROI** - Remediation process highly effective\n"
            elif roi['roi_percentage'] > 200:
                report += "- 🟡 **Good ROI** - Remediation process effective\n"
            elif roi['roi_percentage'] > 0:
                report += "- 🟠 **Positive ROI** - Remediation process beneficial\n"
            else:
                report += "- 🔴 **Negative ROI** - Process improvement needed\n"
        
        report += f"""
---

## 📋 Key Performance Indicators

| Metric | Current | Target | Status |
|--------|---------|---------|---------|
| MRR at Risk | ${metrics['summary']['total_mrr_at_risk']:,.0f} | <${self.business_config['base_mrr'] * 0.05:,.0f} | {"🔴" if metrics['summary']['total_mrr_at_risk'] > self.business_config['base_mrr'] * 0.05 else "🟢"} |
| P0 Resolution Time | {p0_issues.get('avg_age_hours', 0):.1f}h | <24h | {"🔴" if p0_issues.get('avg_age_hours', 0) > 24 else "🟢"} |
| Active P0 Issues | {p0_issues.get('count', 0)} | 0 | {"🔴" if p0_issues.get('count', 0) > 0 else "🟢"} |
| Prevention Score | {metrics['prevention_value']['prevention_effectiveness_score']:.1f}% | >90% | {"🔴" if metrics['prevention_value']['prevention_effectiveness_score'] < 90 else "🟢"} |

---

*This report is generated by the Netra Critical Remediation Business Dashboard*  
*For detailed technical metrics, see the operational dashboard*
"""
        
        return report

    def generate_operational_dashboard_html(self) -> str:
        """Generate HTML dashboard for operational monitoring"""
        metrics = self.calculate_comprehensive_business_metrics()
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Remediation Business Dashboard</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .dashboard {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; font-size: 2.5rem; }}
        .header .subtitle {{ opacity: 0.9; margin-top: 10px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric-card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .metric-card h3 {{ margin: 0 0 10px 0; color: #333; font-size: 1.1rem; }}
        .metric-value {{ font-size: 2.5rem; font-weight: bold; margin: 10px 0; }}
        .metric-value.positive {{ color: #10B981; }}
        .metric-value.negative {{ color: #EF4444; }}
        .metric-value.warning {{ color: #F59E0B; }}
        .metric-value.neutral {{ color: #6B7280; }}
        .metric-subtitle {{ color: #6B7280; font-size: 0.9rem; }}
        .priority-section {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .priority-section h2 {{ margin: 0 0 20px 0; color: #333; }}
        .issue-list {{ list-style: none; padding: 0; }}
        .issue-item {{ padding: 15px; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: between; align-items: center; }}
        .issue-priority {{ padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }}
        .p0 {{ background-color: #FEE2E2; color: #991B1B; }}
        .p1 {{ background-color: #FEF3C7; color: #92400E; }}
        .p2 {{ background-color: #DBEAFE; color: #1E40AF; }}
        .forecast {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; }}
        .forecast h2 {{ margin: 0 0 15px 0; }}
        .trend {{ display: inline-block; margin-left: 10px; }}
        .trend.improving {{ color: #10B981; }}
        .trend.degrading {{ color: #EF4444; }}
        .trend.stable {{ color: #6B7280; }}
        .actions {{ background: #FEF9E7; border: 1px solid #F3E8FF; border-radius: 10px; padding: 20px; }}
        .actions h3 {{ margin: 0 0 15px 0; color: #7C2D12; }}
        .actions ul {{ margin: 0; padding-left: 20px; }}
        .actions li {{ margin-bottom: 5px; color: #92400E; }}
        .timestamp {{ text-align: right; color: #6B7280; font-size: 0.9rem; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🎯 Remediation Business Dashboard</h1>
            <div class="subtitle">Real-time business value tracking and system health monitoring</div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>💰 MRR at Risk</h3>
                <div class="metric-value {'negative' if metrics['summary']['total_mrr_at_risk'] > 5000 else 'warning' if metrics['summary']['total_mrr_at_risk'] > 1000 else 'positive'}">${metrics['summary']['total_mrr_at_risk']:,.0f}</div>
                <div class="metric-subtitle">Monthly recurring revenue at risk from active issues</div>
            </div>
            
            <div class="metric-card">
                <h3>🛡️ MRR Protected</h3>
                <div class="metric-value positive">${metrics['summary']['total_mrr_protected']:,.0f}</div>
                <div class="metric-subtitle">Revenue protected through successful remediation</div>
            </div>
            
            <div class="metric-card">
                <h3>📊 ROI</h3>
                <div class="metric-value {'positive' if metrics['summary']['overall_roi'] > 200 else 'warning' if metrics['summary']['overall_roi'] > 0 else 'negative'}">{metrics['summary']['overall_roi']:.0f}%</div>
                <div class="metric-subtitle">Return on investment for remediation efforts</div>
            </div>
            
            <div class="metric-card">
                <h3>⏱️ Avg Resolution Time</h3>
                <div class="metric-value neutral">{metrics['temporal_analysis']['last_30_days']['avg_resolution_time_hours']:.1f}h</div>
                <div class="metric-subtitle">Average time to resolve issues (30-day average)</div>
            </div>
        </div>
        
        <div class="forecast">
            <h2>🔮 Business Impact Forecast</h2>
            <p><strong>Risk Level:</strong> {metrics['business_impact_forecast']['risk_level'].upper()}</p>
            <p><strong>Next 24h MRR Impact:</strong> ${metrics['business_impact_forecast']['next_24_hours']['mrr_at_risk']:,.0f}</p>
            <p><strong>Expected Resolutions:</strong> {metrics['business_impact_forecast']['next_24_hours']['expected_resolutions']:.0f}</p>
        </div>
"""
        
        # Add priority sections
        for priority in ['p0', 'p1']:
            if priority in metrics['priority_breakdown']:
                priority_data = metrics['priority_breakdown'][priority]
                priority_display = priority.upper()
                
                html += f"""
        <div class="priority-section">
            <h2>{priority_display} Issues ({priority_data['count']} active)</h2>
            <div class="metric-value {'negative' if priority == 'p0' else 'warning'}">${priority_data['total_mrr_at_risk']:,.0f} at risk</div>
            <ul class="issue-list">
"""
                
                for issue in priority_data['issues'][:5]:  # Show top 5
                    html += f"""
                <li class="issue-item">
                    <span>
                        <span class="issue-priority {priority}">{priority_display}</span>
                        <strong>{issue['issue_id']}</strong>: {issue['title']}
                        (Owner: {issue['owner'] or 'Unassigned'})
                    </span>
                    <span>${issue['mrr_at_risk']:,.0f}</span>
                </li>
"""
                
                html += "            </ul>\n        </div>\n"
        
        # Add recommended actions
        if metrics['business_impact_forecast']['recommended_actions']:
            html += f"""
        <div class="actions">
            <h3>🎯 Recommended Actions</h3>
            <ul>
"""
            for action in metrics['business_impact_forecast']['recommended_actions'][:5]:
                html += f"                <li>{action}</li>\n"
            
            html += "            </ul>\n        </div>\n"
        
        html += f"""
        <div class="timestamp">
            Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""
        
        return html

    def save_dashboard_html(self, filename: str = "business_dashboard.html") -> str:
        """Save HTML dashboard to file"""
        html_content = self.generate_operational_dashboard_html()
        dashboard_file = self.dashboard_dir / filename
        
        with open(dashboard_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"Dashboard saved to {dashboard_file}")
        return str(dashboard_file)

    def save_metrics_to_history(self):
        """Save current metrics to historical tracking"""
        metrics = self.calculate_comprehensive_business_metrics()
        
        # Load existing history
        if self.metrics_history_file.exists():
            with open(self.metrics_history_file, 'r') as f:
                history = json.load(f)
        else:
            history = []
        
        # Add current metrics to history
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "summary": metrics["summary"],
            "forecast": metrics["business_impact_forecast"],
            "temporal_analysis": metrics["temporal_analysis"]
        }
        
        history.append(history_entry)
        
        # Keep only last 90 days of history (assuming daily snapshots)
        history = history[-90:]
        
        # Save updated history
        with open(self.metrics_history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        logger.info(f"Metrics saved to history: {len(history)} entries")


def main():
    """Main entry point for the dashboard"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Remediation Business Dashboard')
    parser.add_argument('command', choices=['report', 'dashboard', 'metrics', 'history'], 
                       help='Command to execute')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--save', action='store_true', help='Save output to file')
    
    args = parser.parse_args()
    
    dashboard = BusinessValueDashboard()
    
    if args.command == 'report':
        report = dashboard.generate_executive_report()
        print(report)
        
        if args.save:
            report_file = dashboard.dashboard_dir / f"executive_report_{datetime.now().strftime('%Y%m%d')}.md"
            with open(report_file, 'w') as f:
                f.write(report)
            print(f"\nReport saved to: {report_file}")
    
    elif args.command == 'dashboard':
        if args.save:
            dashboard_file = dashboard.save_dashboard_html()
            print(f"Dashboard saved to: {dashboard_file}")
        else:
            html = dashboard.generate_operational_dashboard_html()
            print(html)
    
    elif args.command == 'metrics':
        metrics = dashboard.calculate_comprehensive_business_metrics()
        if args.json:
            print(json.dumps(metrics, indent=2))
        else:
            print("=== Business Metrics Summary ===")
            print(f"MRR at Risk: ${metrics['summary']['total_mrr_at_risk']:,.0f}")
            print(f"MRR Protected: ${metrics['summary']['total_mrr_protected']:,.0f}")
            print(f"Overall ROI: {metrics['summary']['overall_roi']:.1f}%")
            print(f"Risk Level: {metrics['business_impact_forecast']['risk_level'].upper()}")
    
    elif args.command == 'history':
        dashboard.save_metrics_to_history()
        print("Metrics saved to historical tracking")
    
    return 0


if __name__ == '__main__':
    exit(main())