#!/usr/bin/env python3
"""
Real-time Staging Health Dashboard

Provides real-time monitoring display with alert thresholds, notifications,
historical trend analysis, failure prediction, and automated remediation suggestions.
"""

import asyncio
import json
import logging
import os
import sys
import time
from collections import deque
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional, Tuple

import httpx
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.text import Text
from rich.align import Align

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from shared.isolated_environment import get_env

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthDashboard:
    """Real-time staging health dashboard with alerting and trend analysis."""
    
    def __init__(self, backend_url: str = "http://localhost:8000", refresh_interval: int = 5):
        self.backend_url = backend_url
        self.refresh_interval = refresh_interval
        self.console = Console()
        
        # Alert configuration
        self.alert_thresholds = {
            "overall_health_threshold": 0.8,
            "component_failure_threshold": 2,
            "response_time_threshold_ms": 1000,
            "resource_usage_threshold": 80.0,
            "consecutive_failure_threshold": 3
        }
        
        # Historical data storage
        self.health_history = deque(maxlen=100)
        self.performance_history = deque(maxlen=50)
        self.alert_history = deque(maxlen=20)
        
        # Dashboard state
        self.last_update = None
        self.active_alerts = []
        self.consecutive_failures = 0
        self.dashboard_running = True
        
        # HTTP client
        self.client = None
        
    async def start_dashboard(self) -> None:
        """Start the real-time health dashboard."""
        self.console.print("[bold blue]🚀 Starting Staging Health Dashboard[/bold blue]")
        self.console.print(f"Backend URL: {self.backend_url}")
        self.console.print(f"Refresh Interval: {self.refresh_interval}s")
        self.console.print()
        
        # Initialize HTTP client
        self.client = httpx.AsyncClient(timeout=10.0)
        
        try:
            # Create dashboard layout
            layout = self._create_dashboard_layout()
            
            # Start real-time monitoring
            with Live(layout, refresh_per_second=1, console=self.console) as live:
                while self.dashboard_running:
                    try:
                        # Update dashboard data
                        await self._update_dashboard_data()
                        
                        # Refresh layout with new data
                        updated_layout = self._create_dashboard_layout()
                        live.update(updated_layout)
                        
                        # Wait for next refresh
                        await asyncio.sleep(self.refresh_interval)
                        
                    except KeyboardInterrupt:
                        self.console.print("\\n[yellow]Dashboard stopped by user[/yellow]")
                        self.dashboard_running = False
                        break
                    except Exception as e:
                        logger.error(f"Dashboard update failed: {e}")
                        await asyncio.sleep(1)  # Brief pause before retry
                        
        finally:
            if self.client:
                await self.client.aclose()
    
    def _create_dashboard_layout(self) -> Layout:
        """Create the main dashboard layout."""
        layout = Layout(name="root")
        
        # Create main sections
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        # Split main area
        layout["main"].split_row(
            Layout(name="left_panel", ratio=1),
            Layout(name="right_panel", ratio=1)
        )
        
        # Split left panel
        layout["left_panel"].split_column(
            Layout(name="overview", ratio=1),
            Layout(name="components", ratio=2)
        )
        
        # Split right panel
        layout["right_panel"].split_column(
            Layout(name="performance", ratio=1),
            Layout(name="alerts", ratio=1),
            Layout(name="trends", ratio=1)
        )
        
        # Populate sections
        layout["header"].update(self._create_header_panel())
        layout["overview"].update(self._create_overview_panel())
        layout["components"].update(self._create_components_panel())
        layout["performance"].update(self._create_performance_panel())
        layout["alerts"].update(self._create_alerts_panel())
        layout["trends"].update(self._create_trends_panel())
        layout["footer"].update(self._create_footer_panel())
        
        return layout
    
    def _create_header_panel(self) -> Panel:
        """Create header panel with title and status."""
        title_text = Text("🏥 Staging Environment Health Dashboard", style="bold white")
        
        if self.last_update:
            timestamp = datetime.fromtimestamp(self.last_update).strftime("%Y-%m-%d %H:%M:%S")
            subtitle = f"Last Updated: {timestamp}"
        else:
            subtitle = "Initializing..."
        
        header_content = Align.center(f"{title_text}\\n{subtitle}")
        
        return Panel(
            header_content,
            title="Netra Apex Staging Monitor",
            border_style="blue",
            padding=(0, 1)
        )
    
    def _create_overview_panel(self) -> Panel:
        """Create system overview panel."""
        if not self.health_history:
            content = "⏳ Loading system overview..."
            return Panel(content, title="System Overview", border_style="yellow")
        
        latest_health = self.health_history[-1] if self.health_history else {}
        
        # Overall status
        overall_status = latest_health.get("status", "unknown")
        status_color = self._get_status_color(overall_status)
        
        # Component summary
        checks = latest_health.get("checks", {})
        total_components = len(checks)
        healthy_components = sum(
            1 for result in checks.values()
            if isinstance(result, dict) and result.get("success", True)
        )
        
        # Health percentage
        health_percentage = (healthy_components / total_components) * 100 if total_components > 0 else 0
        
        # Business impact
        business_impact = self._get_business_impact_summary(latest_health)
        
        overview_table = Table(show_header=False, box=None)
        overview_table.add_column("Metric", style="bold")
        overview_table.add_column("Value")
        
        overview_table.add_row("Overall Status", f"[{status_color}]{overall_status.upper()}[/{status_color}]")
        overview_table.add_row("Health Score", f"{health_percentage:.1f}%")
        overview_table.add_row("Components", f"{healthy_components}/{total_components}")
        overview_table.add_row("Business Impact", f"[{self._get_impact_color(business_impact)}]{business_impact.upper()}[/{self._get_impact_color(business_impact)}]")
        overview_table.add_row("Active Alerts", f"[red]{len(self.active_alerts)}[/red]")
        
        return Panel(overview_table, title="System Overview", border_style=status_color)
    
    def _create_components_panel(self) -> Panel:
        """Create components health panel."""
        if not self.health_history:
            content = "⏳ Loading component status..."
            return Panel(content, title="Component Health", border_style="yellow")
        
        latest_health = self.health_history[-1] if self.health_history else {}
        checks = latest_health.get("checks", {})
        
        components_table = Table(show_header=True)
        components_table.add_column("Component", style="bold")
        components_table.add_column("Status", justify="center")
        components_table.add_column("Health Score", justify="center")
        components_table.add_column("Response Time", justify="center")
        
        # Sort components by health score (worst first)
        sorted_components = sorted(
            checks.items(),
            key=lambda x: x[1].get("health_score", 1.0) if isinstance(x[1], dict) else 1.0
        )
        
        for name, result in sorted_components[:10]:  # Show top 10 components
            if isinstance(result, dict):
                success = result.get("success", True)
                health_score = result.get("health_score", 1.0)
                response_time = result.get("response_time_ms", 0)
                
                # Format component name (remove prefixes for display)
                display_name = name.replace("staging_", "").replace("database_", "").replace("service_", "")
                
                # Status indicator
                status_icon = "✅" if success else "❌"
                status_color = "green" if success else "red"
                
                # Health score with color coding
                score_color = "green" if health_score >= 0.8 else "yellow" if health_score >= 0.6 else "red"
                
                components_table.add_row(
                    display_name[:20],  # Truncate long names
                    f"[{status_color}]{status_icon}[/{status_color}]",
                    f"[{score_color}]{health_score:.2f}[/{score_color}]",
                    f"{response_time:.1f}ms"
                )
        
        return Panel(components_table, title="Component Health", border_style="cyan")
    
    def _create_performance_panel(self) -> Panel:
        """Create performance metrics panel."""
        if not self.performance_history:
            content = "⏳ Loading performance metrics..."
            return Panel(content, title="Performance Metrics", border_style="yellow")
        
        latest_perf = self.performance_history[-1] if self.performance_history else {}
        
        performance_table = Table(show_header=False, box=None)
        performance_table.add_column("Metric", style="bold")
        performance_table.add_column("Current")
        performance_table.add_column("Trend")
        
        # API Response Time
        api_time = latest_perf.get("api_response_time_ms", 0)
        api_trend = self._calculate_trend("api_response_time_ms")
        api_color = "green" if api_time < 500 else "yellow" if api_time < 1000 else "red"
        
        performance_table.add_row(
            "API Response",
            f"[{api_color}]{api_time:.1f}ms[/{api_color}]",
            self._get_trend_indicator(api_trend)
        )
        
        # WebSocket Latency
        ws_latency = latest_perf.get("websocket_latency_ms", 0)
        ws_trend = self._calculate_trend("websocket_latency_ms")
        ws_color = "green" if ws_latency < 100 else "yellow" if ws_latency < 200 else "red"
        
        performance_table.add_row(
            "WebSocket Latency",
            f"[{ws_color}]{ws_latency:.1f}ms[/{ws_color}]",
            self._get_trend_indicator(ws_trend)
        )
        
        # Database Query Time
        db_time = latest_perf.get("database_query_time_ms", 0)
        db_trend = self._calculate_trend("database_query_time_ms")
        db_color = "green" if db_time < 50 else "yellow" if db_time < 100 else "red"
        
        performance_table.add_row(
            "Database Query",
            f"[{db_color}]{db_time:.1f}ms[/{db_color}]",
            self._get_trend_indicator(db_trend)
        )
        
        # Resource Usage
        cpu_usage = latest_perf.get("cpu_usage_percent", 0)
        memory_usage = latest_perf.get("memory_usage_percent", 0)
        
        cpu_color = "green" if cpu_usage < 70 else "yellow" if cpu_usage < 85 else "red"
        memory_color = "green" if memory_usage < 80 else "yellow" if memory_usage < 90 else "red"
        
        performance_table.add_row(
            "CPU Usage",
            f"[{cpu_color}]{cpu_usage:.1f}%[/{cpu_color}]",
            "📊"
        )
        
        performance_table.add_row(
            "Memory Usage",
            f"[{memory_color}]{memory_usage:.1f}%[/{memory_color}]",
            "📊"
        )
        
        return Panel(performance_table, title="Performance Metrics", border_style="magenta")
    
    def _create_alerts_panel(self) -> Panel:
        """Create alerts and notifications panel."""
        if not self.active_alerts:
            content = "[green]✅ No active alerts[/green]"
            return Panel(content, title="Active Alerts", border_style="green")
        
        alerts_table = Table(show_header=True)
        alerts_table.add_column("Severity", justify="center")
        alerts_table.add_column("Component")
        alerts_table.add_column("Message")
        alerts_table.add_column("Time")
        
        for alert in self.active_alerts[:5]:  # Show latest 5 alerts
            severity = alert.get("severity", "info")
            severity_color = self._get_alert_severity_color(severity)
            severity_icon = self._get_alert_severity_icon(severity)
            
            component = alert.get("component", "system")
            message = alert.get("message", "")[:40] + "..." if len(alert.get("message", "")) > 40 else alert.get("message", "")
            alert_time = datetime.fromtimestamp(alert.get("timestamp", time.time())).strftime("%H:%M:%S")
            
            alerts_table.add_row(
                f"[{severity_color}]{severity_icon}[/{severity_color}]",
                component,
                message,
                alert_time
            )
        
        panel_color = "red" if any(alert.get("severity") == "critical" for alert in self.active_alerts) else "yellow"
        
        return Panel(alerts_table, title=f"Active Alerts ({len(self.active_alerts)})", border_style=panel_color)
    
    def _create_trends_panel(self) -> Panel:
        """Create trends and predictions panel."""
        if len(self.health_history) < 5:
            content = "⏳ Collecting trend data..."
            return Panel(content, title="Trends & Predictions", border_style="yellow")
        
        trends_table = Table(show_header=False, box=None)
        trends_table.add_column("Metric", style="bold")
        trends_table.add_column("Trend")
        trends_table.add_column("Prediction")
        
        # Overall health trend
        health_trend = self._calculate_health_trend()
        health_prediction = self._predict_health_issues()
        
        trends_table.add_row(
            "Overall Health",
            self._get_trend_indicator(health_trend),
            health_prediction
        )
        
        # Component failure trend
        failure_trend = self._calculate_failure_trend()
        failure_prediction = self._predict_component_failures()
        
        trends_table.add_row(
            "Component Failures",
            self._get_trend_indicator(failure_trend),
            failure_prediction
        )
        
        # Performance trend
        perf_trend = self._calculate_performance_trend()
        perf_prediction = self._predict_performance_issues()
        
        trends_table.add_row(
            "Performance",
            self._get_trend_indicator(perf_trend),
            perf_prediction
        )
        
        # Stability score
        stability_score = self._calculate_stability_score()
        stability_color = "green" if stability_score > 0.8 else "yellow" if stability_score > 0.6 else "red"
        
        trends_table.add_row(
            "Stability Score",
            f"[{stability_color}]{stability_score:.2f}[/{stability_color}]",
            "📈" if stability_score > 0.8 else "⚠️"
        )
        
        return Panel(trends_table, title="Trends & Predictions", border_style="cyan")
    
    def _create_footer_panel(self) -> Panel:
        """Create footer panel with controls and status."""
        footer_text = (
            "[bold white]Controls:[/bold white] "
            "[cyan]Ctrl+C[/cyan] to exit | "
            f"[green]Refresh: {self.refresh_interval}s[/green] | "
            f"[yellow]History: {len(self.health_history)} entries[/yellow]"
        )
        
        return Panel(
            Align.center(footer_text),
            border_style="dim"
        )
    
    async def _update_dashboard_data(self) -> None:
        """Update dashboard with latest health data."""
        try:
            # Fetch comprehensive health status
            health_response = await self.client.get(f"{self.backend_url}/staging/health")
            health_response.raise_for_status()
            health_data = health_response.json()
            
            # Store in history
            health_data["fetch_timestamp"] = time.time()
            self.health_history.append(health_data)
            
            # Fetch performance metrics
            metrics_response = await self.client.get(f"{self.backend_url}/staging/health/metrics")
            metrics_response.raise_for_status()
            metrics_data = metrics_response.json()
            
            # Extract performance metrics
            performance_metrics = self._extract_performance_metrics(metrics_data)
            if performance_metrics:
                self.performance_history.append(performance_metrics)
            
            # Check for alerts
            self._check_alert_conditions(health_data)
            
            # Update last update timestamp
            self.last_update = time.time()
            
            # Reset consecutive failures on success
            self.consecutive_failures = 0
            
        except Exception as e:
            logger.error(f"Failed to update dashboard data: {e}")
            self.consecutive_failures += 1
            
            # Add connectivity alert if too many consecutive failures
            if self.consecutive_failures >= self.alert_thresholds["consecutive_failure_threshold"]:
                self._add_alert({
                    "severity": "critical",
                    "component": "dashboard",
                    "message": f"Lost connection to backend ({self.consecutive_failures} failures)",
                    "timestamp": time.time()
                })
    
    def _extract_performance_metrics(self, metrics_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract performance metrics from metrics response."""
        try:
            real_time_metrics = metrics_data.get("real_time_metrics", {})
            performance_data = metrics_data.get("performance", {})
            
            return {
                "api_response_time_ms": performance_data.get("api_response_time_ms", 0),
                "websocket_latency_ms": performance_data.get("websocket_latency_ms", 0),
                "database_query_time_ms": performance_data.get("database_query_time_ms", 0),
                "cpu_usage_percent": real_time_metrics.get("cpu_percent", 0),
                "memory_usage_percent": real_time_metrics.get("memory_percent", 0),
                "timestamp": time.time()
            }
        except Exception:
            return None
    
    def _check_alert_conditions(self, health_data: Dict[str, Any]) -> None:
        """Check for alert conditions in health data."""
        # Clear old alerts (older than 5 minutes)
        current_time = time.time()
        self.active_alerts = [
            alert for alert in self.active_alerts 
            if current_time - alert.get("timestamp", 0) < 300
        ]
        
        # Check overall health threshold
        overall_health_score = self._calculate_overall_health_score(health_data)
        if overall_health_score < self.alert_thresholds["overall_health_threshold"]:
            self._add_alert({
                "severity": "warning",
                "component": "system",
                "message": f"Overall health score {overall_health_score:.2f} below threshold",
                "timestamp": current_time
            })
        
        # Check component failures
        checks = health_data.get("checks", {})
        failed_components = [
            name for name, result in checks.items()
            if isinstance(result, dict) and not result.get("success", True)
        ]
        
        if len(failed_components) >= self.alert_thresholds["component_failure_threshold"]:
            self._add_alert({
                "severity": "critical",
                "component": "system",
                "message": f"{len(failed_components)} components failed: {', '.join(failed_components[:3])}",
                "timestamp": current_time
            })
        
        # Check business impact
        staging_analysis = health_data.get("staging_analysis", {})
        business_impact = staging_analysis.get("business_impact", {})
        
        if business_impact.get("impact_level") == "critical":
            self._add_alert({
                "severity": "critical",
                "component": "business",
                "message": "Critical business functionality impacted",
                "timestamp": current_time
            })
    
    def _add_alert(self, alert: Dict[str, Any]) -> None:
        """Add a new alert to the active alerts list."""
        # Avoid duplicate alerts
        existing_alert = next(
            (a for a in self.active_alerts 
             if a.get("component") == alert.get("component") and 
             a.get("message") == alert.get("message")), 
            None
        )
        
        if not existing_alert:
            self.active_alerts.append(alert)
            self.alert_history.append(alert)
            
            # Log critical alerts
            if alert.get("severity") == "critical":
                logger.error(f"CRITICAL ALERT: {alert.get('message')}")
    
    def _calculate_overall_health_score(self, health_data: Dict[str, Any]) -> float:
        """Calculate overall health score from health data."""
        checks = health_data.get("checks", {})
        if not checks:
            return 1.0
        
        total_score = 0
        count = 0
        
        for result in checks.values():
            if isinstance(result, dict):
                score = result.get("health_score", 1.0)
                total_score += score
                count += 1
        
        return total_score / count if count > 0 else 1.0
    
    def _calculate_trend(self, metric_name: str) -> str:
        """Calculate trend for a specific metric."""
        if len(self.performance_history) < 3:
            return "stable"
        
        recent_values = [
            entry.get(metric_name, 0) 
            for entry in list(self.performance_history)[-5:]
            if metric_name in entry
        ]
        
        if len(recent_values) < 3:
            return "stable"
        
        # Simple trend calculation
        first_half = sum(recent_values[:len(recent_values)//2]) / (len(recent_values)//2)
        second_half = sum(recent_values[len(recent_values)//2:]) / (len(recent_values) - len(recent_values)//2)
        
        diff_percentage = ((second_half - first_half) / first_half) * 100 if first_half > 0 else 0
        
        if abs(diff_percentage) < 5:
            return "stable"
        elif diff_percentage > 0:
            return "increasing"
        else:
            return "decreasing"
    
    def _calculate_health_trend(self) -> str:
        """Calculate overall health trend."""
        if len(self.health_history) < 5:
            return "stable"
        
        recent_scores = [
            self._calculate_overall_health_score(entry)
            for entry in list(self.health_history)[-10:]
        ]
        
        if len(recent_scores) < 5:
            return "stable"
        
        first_avg = sum(recent_scores[:5]) / 5
        second_avg = sum(recent_scores[-5:]) / 5
        
        diff = second_avg - first_avg
        
        if abs(diff) < 0.05:
            return "stable"
        elif diff > 0:
            return "improving"
        else:
            return "degrading"
    
    def _calculate_failure_trend(self) -> str:
        """Calculate component failure trend."""
        if len(self.health_history) < 5:
            return "stable"
        
        failure_counts = []
        for entry in list(self.health_history)[-10:]:
            checks = entry.get("checks", {})
            failures = sum(
                1 for result in checks.values()
                if isinstance(result, dict) and not result.get("success", True)
            )
            failure_counts.append(failures)
        
        if len(failure_counts) < 5:
            return "stable"
        
        first_avg = sum(failure_counts[:5]) / 5
        second_avg = sum(failure_counts[-5:]) / 5
        
        diff = second_avg - first_avg
        
        if abs(diff) < 0.5:
            return "stable"
        elif diff > 0:
            return "increasing"
        else:
            return "decreasing"
    
    def _calculate_performance_trend(self) -> str:
        """Calculate overall performance trend."""
        api_trend = self._calculate_trend("api_response_time_ms")
        ws_trend = self._calculate_trend("websocket_latency_ms")
        db_trend = self._calculate_trend("database_query_time_ms")
        
        trends = [api_trend, ws_trend, db_trend]
        
        if trends.count("increasing") > trends.count("decreasing"):
            return "degrading"  # Increasing response times = degrading performance
        elif trends.count("decreasing") > trends.count("increasing"):
            return "improving"  # Decreasing response times = improving performance
        else:
            return "stable"
    
    def _calculate_stability_score(self) -> float:
        """Calculate system stability score."""
        if len(self.health_history) < 10:
            return 0.5
        
        recent_scores = [
            self._calculate_overall_health_score(entry)
            for entry in list(self.health_history)[-20:]
        ]
        
        # Calculate variance (lower variance = higher stability)
        mean_score = sum(recent_scores) / len(recent_scores)
        variance = sum((score - mean_score) ** 2 for score in recent_scores) / len(recent_scores)
        
        # Convert variance to stability score (0-1)
        stability = max(0, min(1, 1 - (variance * 10)))
        
        return stability
    
    def _predict_health_issues(self) -> str:
        """Predict potential health issues."""
        health_trend = self._calculate_health_trend()
        
        if health_trend == "degrading":
            return "[red]⚠️ Potential issues[/red]"
        elif health_trend == "stable":
            return "[green]✅ Stable[/green]"
        else:
            return "[cyan]📈 Improving[/cyan]"
    
    def _predict_component_failures(self) -> str:
        """Predict component failures."""
        failure_trend = self._calculate_failure_trend()
        
        if failure_trend == "increasing":
            return "[red]⚠️ More failures expected[/red]"
        elif failure_trend == "stable":
            return "[yellow]➖ Stable[/yellow]"
        else:
            return "[green]✅ Improving[/green]"
    
    def _predict_performance_issues(self) -> str:
        """Predict performance issues."""
        perf_trend = self._calculate_performance_trend()
        
        if perf_trend == "degrading":
            return "[red]⚠️ Performance declining[/red]"
        elif perf_trend == "stable":
            return "[green]✅ Stable performance[/green]"
        else:
            return "[cyan]📈 Performance improving[/cyan]"
    
    def _get_business_impact_summary(self, health_data: Dict[str, Any]) -> str:
        """Get business impact summary."""
        staging_analysis = health_data.get("staging_analysis", {})
        business_impact = staging_analysis.get("business_impact", {})
        return business_impact.get("impact_level", "none")
    
    def _get_status_color(self, status: str) -> str:
        """Get color for health status."""
        status_colors = {
            "healthy": "green",
            "degraded": "yellow",
            "unhealthy": "red",
            "unknown": "dim"
        }
        return status_colors.get(status.lower(), "dim")
    
    def _get_impact_color(self, impact: str) -> str:
        """Get color for business impact level."""
        impact_colors = {
            "none": "green",
            "low": "green",
            "moderate": "yellow",
            "critical": "red"
        }
        return impact_colors.get(impact.lower(), "dim")
    
    def _get_alert_severity_color(self, severity: str) -> str:
        """Get color for alert severity."""
        severity_colors = {
            "info": "blue",
            "warning": "yellow",
            "critical": "red"
        }
        return severity_colors.get(severity.lower(), "dim")
    
    def _get_alert_severity_icon(self, severity: str) -> str:
        """Get icon for alert severity."""
        severity_icons = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨"
        }
        return severity_icons.get(severity.lower(), "•")
    
    def _get_trend_indicator(self, trend: str) -> str:
        """Get visual indicator for trend."""
        trend_indicators = {
            "improving": "[green]📈[/green]",
            "stable": "[yellow]➖[/yellow]",
            "degrading": "[red]📉[/red]",
            "increasing": "[red]📈[/red]",  # For metrics where increase is bad
            "decreasing": "[green]📉[/green]"  # For metrics where decrease is good
        }
        return trend_indicators.get(trend.lower(), "[dim]?[/dim]")


async def main():
    """Main function to run the health dashboard."""
    # Get configuration from environment
    env = get_env()
    backend_url = env.get("BACKEND_URL", "http://localhost:8000")
    refresh_interval = int(env.get("DASHBOARD_REFRESH_INTERVAL", "5"))
    
    # Create and start dashboard
    dashboard = HealthDashboard(backend_url=backend_url, refresh_interval=refresh_interval)
    
    try:
        await dashboard.start_dashboard()
    except KeyboardInterrupt:
        print("\\nDashboard stopped by user")
    except Exception as e:
        print(f"\\nDashboard error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())