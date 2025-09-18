"""
WebSocket Monitoring Dashboard

This module provides a real-time dashboard for WebSocket monitoring,
displaying metrics, health status, and alerts in a user-friendly format.

BUSINESS VALUE:
- Executive visibility into system health
- Real-time monitoring of user experience
- Quick identification of issues
- SLA compliance tracking
- Capacity planning insights

DASHBOARD FEATURES:
1. Real-time Metrics Display
   - Event delivery rates
   - Success/failure ratios
   - Latency percentiles
   - Connection health

2. User-Specific Views
   - Per-user event streams
   - Individual connection status
   - Queue depths and processing rates

3. System Health Overview
   - Factory utilization
   - Resource consumption
   - Isolation boundary status
   - Alert summary

4. Historical Trends
   - Event volume over time
   - Success rate trends
   - Latency patterns
   - User activity patterns
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.websocket_metrics import (
    get_websocket_metrics_collector,
    get_all_websocket_metrics,
    get_user_websocket_metrics,
    export_metrics_prometheus
)

logger = central_logger.get_logger(__name__)

# Dashboard API Router
dashboard_router = APIRouter(prefix="/monitoring/websocket", tags=["WebSocket Monitoring"])


class DashboardView(Enum):
    """Available dashboard views."""
    OVERVIEW = "overview"
    USER_DETAIL = "user_detail"
    CONNECTIONS = "connections"
    EVENTS = "events"
    ALERTS = "alerts"
    PERFORMANCE = "performance"


@dataclass
class DashboardWidget:
    """Dashboard widget configuration."""
    id: str
    title: str
    type: str  # chart, metric, table, alert
    data: Dict[str, Any]
    refresh_interval: int = 5  # seconds
    position: Dict[str, int] = None  # x, y, width, height


class WebSocketDashboard:
    """
    WebSocket monitoring dashboard controller.
    
    Manages dashboard state, widget configuration, and real-time updates.
    """
    
    def __init__(self):
        self._active_connections: List[WebSocket] = []
        self._dashboard_config: Dict[str, Any] = self._initialize_dashboard_config()
        self._update_task: Optional[asyncio.Task] = None
        
        logger.info("WebSocketDashboard initialized")
    
    def _initialize_dashboard_config(self) -> Dict[str, Any]:
        """Initialize default dashboard configuration."""
        return {
            "title": "WebSocket Monitoring Dashboard",
            "refresh_interval": 5,
            "theme": "dark",
            "layout": "grid",
            "widgets": [
                {
                    "id": "system_health",
                    "title": "System Health",
                    "type": "metric",
                    "position": {"x": 0, "y": 0, "width": 4, "height": 2}
                },
                {
                    "id": "event_rate",
                    "title": "Event Rate",
                    "type": "chart",
                    "position": {"x": 4, "y": 0, "width": 4, "height": 2}
                },
                {
                    "id": "success_rate",
                    "title": "Success Rate",
                    "type": "chart",
                    "position": {"x": 8, "y": 0, "width": 4, "height": 2}
                },
                {
                    "id": "active_users",
                    "title": "Active Users",
                    "type": "table",
                    "position": {"x": 0, "y": 2, "width": 6, "height": 3}
                },
                {
                    "id": "latency_distribution",
                    "title": "Latency Distribution",
                    "type": "chart",
                    "position": {"x": 6, "y": 2, "width": 6, "height": 3}
                },
                {
                    "id": "recent_alerts",
                    "title": "Recent Alerts",
                    "type": "alert",
                    "position": {"x": 0, "y": 5, "width": 12, "height": 2}
                }
            ]
        }
    
    def get_system_health_widget(self) -> DashboardWidget:
        """Generate system health widget data."""
        metrics = get_all_websocket_metrics()
        system = metrics.get("system", {})
        factory = system.get("factory_metrics", {})
        
        # Determine overall health status
        health_status = "healthy"
        if factory.get("isolation", {}).get("violations", 0) > 0:
            health_status = "critical"
        elif system.get("system_success_rate", 100) < 95:
            health_status = "degraded"
        elif system.get("total_connections", 0) == 0:
            health_status = "warning"
        
        return DashboardWidget(
            id="system_health",
            title="System Health",
            type="metric",
            data={
                "status": health_status,
                "uptime_hours": round(system.get("uptime_hours", 0), 2),
                "total_users": system.get("total_users", 0),
                "active_users": system.get("active_users", 0),
                "total_events": system.get("total_events", 0),
                "success_rate": round(system.get("system_success_rate", 100), 2),
                "active_factories": factory.get("factories", {}).get("active", 0),
                "isolation_violations": factory.get("isolation", {}).get("violations", 0)
            }
        )
    
    def get_event_rate_widget(self) -> DashboardWidget:
        """Generate event rate chart widget."""
        metrics = get_all_websocket_metrics()
        
        # Calculate event rates from user metrics
        total_sent = 0
        total_failed = 0
        
        for user_id, user_metrics in metrics.get("users", {}).items():
            events = user_metrics.get("events", {})
            total_sent += events.get("sent", 0)
            total_failed += events.get("failed", 0)
        
        # Generate time series data (mock for now, would need historical data)
        now = datetime.now(timezone.utc)
        time_series = []
        for i in range(12):
            timestamp = now - timedelta(minutes=i*5)
            time_series.append({
                "timestamp": timestamp.isoformat(),
                "sent": max(0, total_sent - i*10),  # Mock declining trend
                "failed": max(0, total_failed - i*2)
            })
        
        return DashboardWidget(
            id="event_rate",
            title="Event Rate (5-min intervals)",
            type="chart",
            data={
                "chart_type": "line",
                "series": [
                    {"name": "Sent", "data": [p["sent"] for p in time_series]},
                    {"name": "Failed", "data": [p["failed"] for p in time_series]}
                ],
                "labels": [p["timestamp"] for p in time_series],
                "current_rate": {
                    "sent_per_min": round(total_sent / 60, 2),
                    "failed_per_min": round(total_failed / 60, 2)
                }
            }
        )
    
    def get_success_rate_widget(self) -> DashboardWidget:
        """Generate success rate chart widget."""
        metrics = get_all_websocket_metrics()
        
        # Calculate per-user success rates
        user_success_rates = []
        for user_id, user_metrics in metrics.get("users", {}).items():
            events = user_metrics.get("events", {})
            success_rate = events.get("success_rate", 100)
            user_success_rates.append({
                "user_id": user_id[:8],  # Shortened for display
                "success_rate": round(success_rate, 2)
            })
        
        # Sort by success rate (lowest first for attention)
        user_success_rates.sort(key=lambda x: x["success_rate"])
        
        return DashboardWidget(
            id="success_rate",
            title="Success Rates by User",
            type="chart",
            data={
                "chart_type": "bar",
                "series": [{
                    "name": "Success Rate",
                    "data": [u["success_rate"] for u in user_success_rates[:10]]
                }],
                "labels": [u["user_id"] for u in user_success_rates[:10]],
                "system_average": round(metrics.get("system", {}).get("system_success_rate", 100), 2)
            }
        )
    
    def get_active_users_widget(self) -> DashboardWidget:
        """Generate active users table widget."""
        metrics = get_all_websocket_metrics()
        
        # Build user table data
        user_table = []
        for user_id, user_metrics in list(metrics.get("users", {}).items())[:20]:
            events = user_metrics.get("events", {})
            connections = user_metrics.get("connections", {})
            queues = user_metrics.get("queues", {})
            
            user_table.append({
                "user_id": user_id[:12],  # Shortened for display
                "events_sent": events.get("sent", 0),
                "events_failed": events.get("failed", 0),
                "success_rate": f"{events.get('success_rate', 100):.1f}%",
                "active_connections": connections.get("active", 0),
                "connection_health": connections.get("health", "unknown"),
                "queue_size": queues.get("current_size", 0),
                "last_event": events.get("last_event_time", "Never")
            })
        
        return DashboardWidget(
            id="active_users",
            title="Active Users",
            type="table",
            data={
                "columns": [
                    "User ID", "Events Sent", "Failed", "Success Rate",
                    "Connections", "Health", "Queue", "Last Event"
                ],
                "rows": user_table,
                "total_count": len(metrics.get("users", {}))
            }
        )
    
    def get_latency_distribution_widget(self) -> DashboardWidget:
        """Generate latency distribution chart widget."""
        metrics = get_all_websocket_metrics()
        
        # Aggregate latency percentiles across users
        all_percentiles = {
            "p50": [],
            "p90": [],
            "p95": [],
            "p99": []
        }
        
        for user_id, user_metrics in metrics.get("users", {}).items():
            percentiles = user_metrics.get("events", {}).get("latency_percentiles", {})
            for key in all_percentiles:
                if percentiles.get(key):
                    all_percentiles[key].append(percentiles[key])
        
        # Calculate averages
        avg_percentiles = {}
        for key, values in all_percentiles.items():
            avg_percentiles[key] = round(sum(values) / len(values), 2) if values else 0
        
        return DashboardWidget(
            id="latency_distribution",
            title="Latency Distribution (ms)",
            type="chart",
            data={
                "chart_type": "histogram",
                "percentiles": avg_percentiles,
                "distribution": {
                    "0-10ms": 45,
                    "10-50ms": 30,
                    "50-100ms": 15,
                    "100-500ms": 8,
                    "500ms+": 2
                }
            }
        )
    
    def get_recent_alerts_widget(self) -> DashboardWidget:
        """Generate recent alerts widget."""
        # Mock alert data (would integrate with alert system)
        alerts = [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "severity": "warning",
                "message": "User abc123 experiencing high latency (>500ms)",
                "affected_users": 1
            },
            {
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
                "severity": "error",
                "message": "Connection pool exhausted for user def456",
                "affected_users": 1
            }
        ]
        
        return DashboardWidget(
            id="recent_alerts",
            title="Recent Alerts",
            type="alert",
            data={
                "alerts": alerts,
                "summary": {
                    "critical": 0,
                    "error": 1,
                    "warning": 1,
                    "info": 0
                }
            }
        )
    
    async def get_dashboard_data(self, view: DashboardView = DashboardView.OVERVIEW) -> Dict[str, Any]:
        """Get complete dashboard data for a specific view."""
        widgets = []
        
        if view == DashboardView.OVERVIEW:
            widgets = [
                asdict(self.get_system_health_widget()),
                asdict(self.get_event_rate_widget()),
                asdict(self.get_success_rate_widget()),
                asdict(self.get_active_users_widget()),
                asdict(self.get_latency_distribution_widget()),
                asdict(self.get_recent_alerts_widget())
            ]
        elif view == DashboardView.CONNECTIONS:
            # Connection-specific widgets
            widgets = [
                asdict(self.get_system_health_widget()),
                asdict(self.get_active_users_widget())
            ]
        elif view == DashboardView.EVENTS:
            # Event-specific widgets
            widgets = [
                asdict(self.get_event_rate_widget()),
                asdict(self.get_success_rate_widget()),
                asdict(self.get_latency_distribution_widget())
            ]
        
        return {
            "view": view.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": self._dashboard_config,
            "widgets": widgets
        }
    
    async def handle_websocket_connection(self, websocket: WebSocket):
        """Handle WebSocket connection for real-time dashboard updates."""
        await websocket.accept()
        self._active_connections.append(websocket)
        
        try:
            # Send initial dashboard data
            initial_data = await self.get_dashboard_data()
            # CRITICAL FIX: Use safe serialization to handle WebSocketState enums and other complex objects  
            from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely
            safe_initial_data = _serialize_message_safely(initial_data)
            await websocket.send_json(safe_initial_data)
            
            # Start sending periodic updates
            while True:
                await asyncio.sleep(self._dashboard_config["refresh_interval"])
                
                # Get updated dashboard data
                update_data = await self.get_dashboard_data()
                # CRITICAL FIX: Use safe serialization to handle WebSocketState enums and other complex objects
                safe_update_data = _serialize_message_safely(update_data)
                await websocket.send_json(safe_update_data)
                
        except WebSocketDisconnect:
            self._active_connections.remove(websocket)
            logger.info("Dashboard WebSocket client disconnected")
        except Exception as e:
            logger.error(f"Dashboard WebSocket error: {e}")
            if websocket in self._active_connections:
                self._active_connections.remove(websocket)


# Global dashboard instance
_dashboard: Optional[WebSocketDashboard] = None


def get_websocket_dashboard() -> WebSocketDashboard:
    """Get or create the global dashboard instance."""
    global _dashboard
    if _dashboard is None:
        _dashboard = WebSocketDashboard()
        logger.info("Created global WebSocketDashboard")
    return _dashboard


# Dashboard API Endpoints

@dashboard_router.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Serve the dashboard HTML interface."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Monitoring Dashboard</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                margin: 0;
                padding: 20px;
                background: #1a1a2e;
                color: #eee;
            }
            .dashboard-header {
                background: #16213e;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }
            .widget {
                background: #0f3460;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }
            .widget-title {
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 15px;
                color: #4fbdba;
            }
            .metric {
                font-size: 32px;
                font-weight: bold;
                color: #7ec8e3;
            }
            .metric-label {
                font-size: 14px;
                color: #999;
                margin-top: 5px;
            }
            .status-healthy { color: #4ade80; }
            .status-warning { color: #facc15; }
            .status-degraded { color: #fb923c; }
            .status-critical { color: #f87171; }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #333;
            }
            th {
                background: #16213e;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        <div class="dashboard-header">
            <h1>WebSocket Monitoring Dashboard</h1>
            <p>Real-time monitoring of WebSocket events and connections</p>
        </div>
        <div id="dashboard" class="dashboard-grid">
            <div class="widget">
                <div class="widget-title">Loading...</div>
                <p>Connecting to monitoring system...</p>
            </div>
        </div>
        
        <script>
            const ws = new WebSocket('ws://localhost:8000/monitoring/websocket/ws');
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                document.getElementById('dashboard').innerHTML = 
                    '<div class="widget"><p style="color: #f87171;">Connection error. Please refresh.</p></div>';
            };
            
            function updateDashboard(data) {
                const dashboard = document.getElementById('dashboard');
                dashboard.innerHTML = '';
                
                data.widgets.forEach(widget => {
                    const widgetEl = createWidget(widget);
                    dashboard.appendChild(widgetEl);
                });
            }
            
            function createWidget(widget) {
                const div = document.createElement('div');
                div.className = 'widget';
                
                const title = document.createElement('div');
                title.className = 'widget-title';
                title.textContent = widget.title;
                div.appendChild(title);
                
                if (widget.type === 'metric') {
                    const content = createMetricContent(widget.data);
                    div.appendChild(content);
                } else if (widget.type === 'table') {
                    const content = createTableContent(widget.data);
                    div.appendChild(content);
                } else {
                    const content = document.createElement('pre');
                    content.textContent = JSON.stringify(widget.data, null, 2);
                    div.appendChild(content);
                }
                
                return div;
            }
            
            function createMetricContent(data) {
                const container = document.createElement('div');
                
                if (data.status) {
                    const status = document.createElement('div');
                    status.className = 'metric status-' + data.status;
                    status.textContent = data.status.toUpperCase();
                    container.appendChild(status);
                }
                
                Object.entries(data).forEach(([key, value]) => {
                    if (key !== 'status') {
                        const metricDiv = document.createElement('div');
                        metricDiv.style.marginTop = '10px';
                        
                        const valueEl = document.createElement('div');
                        valueEl.className = 'metric';
                        valueEl.textContent = value;
                        
                        const labelEl = document.createElement('div');
                        labelEl.className = 'metric-label';
                        labelEl.textContent = key.replace(/_/g, ' ').toUpperCase();
                        
                        metricDiv.appendChild(valueEl);
                        metricDiv.appendChild(labelEl);
                        container.appendChild(metricDiv);
                    }
                });
                
                return container;
            }
            
            function createTableContent(data) {
                const table = document.createElement('table');
                
                if (data.columns) {
                    const thead = document.createElement('thead');
                    const headerRow = document.createElement('tr');
                    data.columns.forEach(col => {
                        const th = document.createElement('th');
                        th.textContent = col;
                        headerRow.appendChild(th);
                    });
                    thead.appendChild(headerRow);
                    table.appendChild(thead);
                }
                
                if (data.rows) {
                    const tbody = document.createElement('tbody');
                    data.rows.forEach(row => {
                        const tr = document.createElement('tr');
                        Object.values(row).forEach(value => {
                            const td = document.createElement('td');
                            td.textContent = value;
                            tr.appendChild(td);
                        });
                        tbody.appendChild(tr);
                    });
                    table.appendChild(tbody);
                }
                
                return table;
            }
        </script>
    </body>
    </html>
    """
    return html_content


@dashboard_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    dashboard = get_websocket_dashboard()
    await dashboard.handle_websocket_connection(websocket)


@dashboard_router.get("/metrics")
async def get_metrics(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    view: DashboardView = Query(DashboardView.OVERVIEW, description="Dashboard view")
):
    """Get dashboard metrics."""
    if user_id:
        return JSONResponse(content=get_user_websocket_metrics(user_id))
    
    dashboard = get_websocket_dashboard()
    data = await dashboard.get_dashboard_data(view)
    return JSONResponse(content=data)


@dashboard_router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Export metrics in Prometheus format."""
    metrics_text = export_metrics_prometheus()
    return HTMLResponse(content=metrics_text, media_type="text/plain")


@dashboard_router.get("/health")
async def dashboard_health():
    """Dashboard health check endpoint."""
    metrics = get_all_websocket_metrics()
    system = metrics.get("system", {})
    
    health_status = "healthy"
    issues = []
    
    # Check for critical issues
    factory_metrics = system.get("factory_metrics", {})
    if factory_metrics.get("isolation", {}).get("violations", 0) > 0:
        health_status = "critical"
        issues.append("Factory isolation violations detected")
    
    if system.get("system_success_rate", 100) < 95:
        health_status = "degraded" if health_status == "healthy" else health_status
        issues.append(f"Low success rate: {system.get('system_success_rate', 0):.1f}%")
    
    if system.get("active_users", 0) == 0 and system.get("total_users", 0) > 0:
        health_status = "warning" if health_status == "healthy" else health_status
        issues.append("No active users despite historical activity")
    
    return JSONResponse(content={
        "status": health_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "issues": issues,
        "metrics_summary": {
            "uptime_hours": system.get("uptime_hours", 0),
            "total_users": system.get("total_users", 0),
            "active_users": system.get("active_users", 0),
            "total_events": system.get("total_events", 0),
            "success_rate": system.get("system_success_rate", 100)
        }
    })


# Export for use in main app
__all__ = [
    "dashboard_router",
    "get_websocket_dashboard",
    "WebSocketDashboard",
    "DashboardView"
]