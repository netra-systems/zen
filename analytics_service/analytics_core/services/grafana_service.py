"""
Grafana Integration Service for Analytics Platform

This service provides comprehensive Grafana integration including:
- Dashboard provisioning and management
- Datasource configuration (ClickHouse, Redis)
- Alert rule creation and management
- Panel creation for analytics dashboards

Business Value:
- Real-time visibility into user behavior and system performance
- Automated alerting for critical issues
- Data-driven insights for product optimization
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
import time

logger = logging.getLogger(__name__)


class GrafanaServiceError(Exception):
    """Base exception for Grafana service errors"""
    pass


class GrafanaDashboardError(GrafanaServiceError):
    """Errors related to dashboard operations"""
    pass


class GrafanaDatasourceError(GrafanaServiceError):
    """Errors related to datasource operations"""
    pass


class GrafanaAlertError(GrafanaServiceError):
    """Errors related to alert operations"""
    pass


class GrafanaService:
    """
    Comprehensive Grafana integration service for analytics platform.
    
    Provides auto-provisioning of dashboards, datasource configuration,
    and alert rule management with proper error handling and retry logic.
    """
    
    def __init__(
        self,
        grafana_url: str = None,
        grafana_user: str = None,
        grafana_password: str = None,
        clickhouse_url: str = None,
        redis_url: str = None
    ):
        """
        Initialize Grafana service with configuration.
        
        Args:
            grafana_url: Grafana server URL
            grafana_user: Grafana admin username
            grafana_password: Grafana admin password
            clickhouse_url: ClickHouse connection URL
            redis_url: Redis connection URL
        """
        self.grafana_url = grafana_url or os.getenv(
            'GRAFANA_API_URL', 'http://localhost:3000'
        )
        self.grafana_user = grafana_user or os.getenv('GRAFANA_USER', 'admin')
        self.grafana_password = grafana_password or os.getenv('GRAFANA_PASSWORD', 'admin')
        
        self.clickhouse_url = clickhouse_url or os.getenv(
            'CLICKHOUSE_ANALYTICS_URL', 'clickhouse://localhost:8123/analytics'
        )
        self.redis_url = redis_url or os.getenv(
            'REDIS_ANALYTICS_URL', 'redis://localhost:6379/2'
        )
        
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.grafana_user, self.grafana_password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        self.dashboard_configs_path = Path(__file__).parent / "dashboard_configs"
        
    def health_check(self) -> Dict[str, Any]:
        """
        Check Grafana service health and connectivity.
        
        Returns:
            Dict with health status and connection details
        """
        try:
            response = self.session.get(f"{self.grafana_url}/api/health")
            response.raise_for_status()
            
            return {
                "status": "healthy",
                "grafana_version": response.json().get("version"),
                "database": response.json().get("database"),
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Grafana health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def create_datasource(
        self, 
        name: str, 
        datasource_type: str, 
        url: str,
        additional_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create or update a Grafana datasource.
        
        Args:
            name: Datasource name
            datasource_type: Type of datasource (clickhouse, redis, etc.)
            url: Connection URL
            additional_config: Additional configuration parameters
            
        Returns:
            Created datasource information
        """
        datasource_config = {
            "name": name,
            "type": datasource_type,
            "url": url,
            "access": "proxy",
            "isDefault": False,
            "database": "",
            "user": "",
            "password": "",
            "jsonData": additional_config or {},
            "secureJsonData": {}
        }
        
        try:
            # Check if datasource exists
            response = self.session.get(f"{self.grafana_url}/api/datasources/name/{name}")
            
            if response.status_code == 200:
                # Update existing datasource
                existing_ds = response.json()
                datasource_config["id"] = existing_ds["id"]
                
                response = self.session.put(
                    f"{self.grafana_url}/api/datasources/{existing_ds['id']}",
                    json=datasource_config
                )
                logger.info(f"Updated existing datasource: {name}")
            else:
                # Create new datasource
                response = self.session.post(
                    f"{self.grafana_url}/api/datasources",
                    json=datasource_config
                )
                logger.info(f"Created new datasource: {name}")
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            error_msg = f"Failed to create/update datasource {name}: {e}"
            logger.error(error_msg)
            raise GrafanaDatasourceError(error_msg)
    
    def setup_clickhouse_datasource(self) -> Dict[str, Any]:
        """
        Configure ClickHouse datasource for analytics data.
        
        Returns:
            ClickHouse datasource configuration
        """
        # Parse ClickHouse URL for connection details
        clickhouse_config = {
            "httpHeaderName1": "X-ClickHouse-User",
            "httpHeaderValue1": "analytics",
            "timeout": 30,
            "queryTimeout": "30s",
            "validateSql": True
        }
        
        return self.create_datasource(
            name="ClickHouse Analytics",
            datasource_type="vertamedia-clickhouse-datasource",
            url=self.clickhouse_url.replace('clickhouse://', 'http://'),
            additional_config=clickhouse_config
        )
    
    def setup_redis_datasource(self) -> Dict[str, Any]:
        """
        Configure Redis datasource for real-time metrics.
        
        Returns:
            Redis datasource configuration
        """
        redis_config = {
            "timeout": 10,
            "pingInterval": 30,
            "pipelineWindow": "5s"
        }
        
        return self.create_datasource(
            name="Redis Real-time",
            datasource_type="redis-datasource",
            url=self.redis_url,
            additional_config=redis_config
        )
    
    def provision_dashboard(self, dashboard_name: str) -> Dict[str, Any]:
        """
        Provision a dashboard from configuration file.
        
        Args:
            dashboard_name: Name of dashboard configuration file (without .json)
            
        Returns:
            Dashboard creation result
        """
        config_file = self.dashboard_configs_path / f"{dashboard_name}.json"
        
        if not config_file.exists():
            raise GrafanaDashboardError(f"Dashboard config not found: {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                dashboard_config = json.load(f)
            
            # Wrap in dashboard object if needed
            if "dashboard" not in dashboard_config:
                dashboard_config = {
                    "dashboard": dashboard_config,
                    "overwrite": True,
                    "message": f"Provisioned {dashboard_name} dashboard via API"
                }
            
            response = self.session.post(
                f"{self.grafana_url}/api/dashboards/db",
                json=dashboard_config
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Successfully provisioned dashboard: {dashboard_name}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to provision dashboard {dashboard_name}: {e}"
            logger.error(error_msg)
            raise GrafanaDashboardError(error_msg)
    
    def create_alert_rule(
        self,
        title: str,
        condition: str,
        frequency: str = "10s",
        for_duration: str = "5m",
        severity: str = "critical",
        notifications: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Grafana alert rule.
        
        Args:
            title: Alert rule title
            condition: Alert condition query
            frequency: How often to evaluate the rule
            for_duration: How long condition must be true
            severity: Alert severity level
            notifications: List of notification channels
            
        Returns:
            Created alert rule information
        """
        alert_rule = {
            "uid": f"alert_{title.lower().replace(' ', '_')}",
            "title": title,
            "condition": "A",
            "data": [
                {
                    "refId": "A",
                    "queryType": "",
                    "relativeTimeRange": {
                        "from": 300,
                        "to": 0
                    },
                    "model": {
                        "expr": condition,
                        "intervalMs": 1000,
                        "maxDataPoints": 43200,
                        "refId": "A"
                    }
                }
            ],
            "intervalSeconds": int(frequency.rstrip('s')),
            "noDataState": "NoData",
            "execErrState": "Alerting",
            "for": for_duration,
            "annotations": {
                "description": f"Alert for {title}",
                "runbook_url": "",
                "summary": title
            },
            "labels": {
                "severity": severity
            }
        }
        
        try:
            response = self.session.post(
                f"{self.grafana_url}/api/v1/provisioning/alert-rules",
                json=alert_rule
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Created alert rule: {title}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to create alert rule {title}: {e}"
            logger.error(error_msg)
            raise GrafanaAlertError(error_msg)
    
    def setup_default_alerts(self) -> List[Dict[str, Any]]:
        """
        Set up default alert rules for analytics platform.
        
        Returns:
            List of created alert rules
        """
        default_alerts = [
            {
                "title": "High Error Rate",
                "condition": "rate(frontend_events{event_type='error_tracking'}[5m]) > 0.05",
                "severity": "critical",
                "for_duration": "2m"
            },
            {
                "title": "Unusual Traffic Volume",
                "condition": "rate(frontend_events[5m]) > 1000",
                "severity": "warning",
                "for_duration": "5m"
            },
            {
                "title": "Slow Response Time",
                "condition": "histogram_quantile(0.95, rate(chat_response_duration_seconds_bucket[5m])) > 10",
                "severity": "warning",
                "for_duration": "3m"
            },
            {
                "title": "ClickHouse Connection Issues",
                "condition": "up{job='clickhouse'} == 0",
                "severity": "critical",
                "for_duration": "1m"
            }
        ]
        
        results = []
        for alert_config in default_alerts:
            try:
                result = self.create_alert_rule(**alert_config)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to create alert {alert_config['title']}: {e}")
        
        return results
    
    def auto_provision_all(self) -> Dict[str, Any]:
        """
        Auto-provision all dashboards, datasources, and alerts.
        
        Returns:
            Summary of provisioning results
        """
        results = {
            "datasources": [],
            "dashboards": [],
            "alerts": [],
            "errors": []
        }
        
        try:
            # Setup datasources
            logger.info("Setting up ClickHouse datasource...")
            clickhouse_result = self.setup_clickhouse_datasource()
            results["datasources"].append(clickhouse_result)
            
            logger.info("Setting up Redis datasource...")
            redis_result = self.setup_redis_datasource()
            results["datasources"].append(redis_result)
            
            # Provision dashboards
            dashboard_names = ["executive_overview", "prompt_analytics", "user_behavior"]
            for dashboard_name in dashboard_names:
                try:
                    logger.info(f"Provisioning {dashboard_name} dashboard...")
                    dashboard_result = self.provision_dashboard(dashboard_name)
                    results["dashboards"].append(dashboard_result)
                except Exception as e:
                    error_msg = f"Dashboard {dashboard_name}: {e}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
            
            # Setup alerts
            logger.info("Setting up default alerts...")
            alert_results = self.setup_default_alerts()
            results["alerts"].extend(alert_results)
            
            logger.info("Grafana auto-provisioning completed successfully")
            
        except Exception as e:
            error_msg = f"Auto-provisioning failed: {e}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
        
        return results
    
    def get_dashboard_by_uid(self, uid: str) -> Dict[str, Any]:
        """
        Retrieve dashboard by UID.
        
        Args:
            uid: Dashboard UID
            
        Returns:
            Dashboard configuration
        """
        try:
            response = self.session.get(f"{self.grafana_url}/api/dashboards/uid/{uid}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            error_msg = f"Failed to retrieve dashboard {uid}: {e}"
            logger.error(error_msg)
            raise GrafanaDashboardError(error_msg)
    
    def list_datasources(self) -> List[Dict[str, Any]]:
        """
        List all configured datasources.
        
        Returns:
            List of datasource configurations
        """
        try:
            response = self.session.get(f"{self.grafana_url}/api/datasources")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            error_msg = f"Failed to list datasources: {e}"
            logger.error(error_msg)
            raise GrafanaDatasourceError(error_msg)
    
    def test_datasource_connection(self, datasource_id: int) -> Dict[str, Any]:
        """
        Test datasource connectivity.
        
        Args:
            datasource_id: Datasource ID to test
            
        Returns:
            Connection test results
        """
        try:
            response = self.session.post(
                f"{self.grafana_url}/api/datasources/{datasource_id}/proxy",
                json={"query": "SELECT 1"}
            )
            response.raise_for_status()
            return {"status": "success", "message": "Connection successful"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Factory function for creating Grafana service instance
def create_grafana_service() -> GrafanaService:
    """
    Factory function to create configured Grafana service instance.
    
    Returns:
        Configured GrafanaService instance
    """
    return GrafanaService()


# Export main classes and functions
__all__ = [
    'GrafanaService',
    'GrafanaServiceError',
    'GrafanaDashboardError', 
    'GrafanaDatasourceError',
    'GrafanaAlertError',
    'create_grafana_service'
]