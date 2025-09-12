from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Example usage of the Grafana Analytics Service

This script demonstrates how to use the GrafanaService for:
- Setting up datasources
- Provisioning dashboards
- Creating alert rules
- Managing Grafana configuration

Run this script to automatically provision all analytics dashboards.
"""

import logging
import asyncio
import os
from typing import Dict, Any

from grafana_service import create_grafana_service, GrafanaServiceError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def setup_analytics_environment() -> Dict[str, Any]:
    """
    Set up the complete analytics environment with Grafana integration.
    
    Returns:
        Dictionary with setup results and status
    """
    logger.info("Starting analytics environment setup...")
    
    # Create Grafana service instance
    grafana_service = create_grafana_service()
    
    results = {
        "health_check": None,
        "datasources": [],
        "dashboards": [],
        "alerts": [],
        "errors": []
    }
    
    try:
        # 1. Health check
        logger.info("Performing Grafana health check...")
        health_result = grafana_service.health_check()
        results["health_check"] = health_result
        
        if health_result["status"] != "healthy":
            logger.error(f"Grafana health check failed: {health_result}")
            results["errors"].append("Grafana health check failed")
            return results
        
        logger.info(f"Grafana is healthy (version: {health_result.get('grafana_version', 'unknown')})")
        
        # 2. Setup datasources
        logger.info("Setting up ClickHouse datasource...")
        try:
            clickhouse_ds = grafana_service.setup_clickhouse_datasource()
            results["datasources"].append(clickhouse_ds)
            logger.info(f"ClickHouse datasource configured: {clickhouse_ds.get('name')}")
        except Exception as e:
            error_msg = f"Failed to setup ClickHouse datasource: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        logger.info("Setting up Redis datasource...")
        try:
            redis_ds = grafana_service.setup_redis_datasource()
            results["datasources"].append(redis_ds)
            logger.info(f"Redis datasource configured: {redis_ds.get('name')}")
        except Exception as e:
            error_msg = f"Failed to setup Redis datasource: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # 3. Provision dashboards
        dashboard_names = ["executive_overview", "prompt_analytics", "user_behavior"]
        
        for dashboard_name in dashboard_names:
            logger.info(f"Provisioning {dashboard_name} dashboard...")
            try:
                dashboard_result = grafana_service.provision_dashboard(dashboard_name)
                results["dashboards"].append(dashboard_result)
                logger.info(f"Dashboard provisioned: {dashboard_name} (UID: {dashboard_result.get('uid')})")
            except Exception as e:
                error_msg = f"Failed to provision {dashboard_name}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        # 4. Setup alerts
        logger.info("Setting up default alert rules...")
        try:
            alert_results = grafana_service.setup_default_alerts()
            results["alerts"] = alert_results
            logger.info(f"Created {len(alert_results)} alert rules")
        except Exception as e:
            error_msg = f"Failed to setup alerts: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        
        # 5. Test datasource connections
        logger.info("Testing datasource connections...")
        try:
            datasources = grafana_service.list_datasources()
            for ds in datasources:
                if ds.get('name') in ['ClickHouse Analytics', 'Redis Real-time']:
                    test_result = grafana_service.test_datasource_connection(ds['id'])
                    if test_result['status'] == 'success':
                        logger.info(f"Datasource {ds['name']} connection: OK")
                    else:
                        logger.warning(f"Datasource {ds['name']} connection: {test_result['message']}")
        except Exception as e:
            logger.warning(f"Datasource connection tests failed: {e}")
        
        logger.info("Analytics environment setup completed successfully!")
        
    except GrafanaServiceError as e:
        error_msg = f"Grafana service error: {e}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during setup: {e}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
    
    return results


def validate_environment_variables():
    """
    Validate that required environment variables are set.
    """
    required_vars = [
        'GRAFANA_API_URL',
        'CLICKHOUSE_ANALYTICS_URL', 
        'REDIS_ANALYTICS_URL'
    ]
    
    optional_vars = [
        'GRAFANA_USER',
        'GRAFANA_PASSWORD'
    ]
    
    logger.info("Validating environment variables...")
    
    for var in required_vars:
        if not get_env().get(var):
            logger.warning(f"Required environment variable {var} not set, using default")
    
    for var in optional_vars:
        if not get_env().get(var):
            logger.info(f"Optional environment variable {var} not set, using default")
    
    # Log current configuration (without sensitive info)
    logger.info(f"Grafana URL: {get_env().get('GRAFANA_API_URL', 'http://localhost:3000')}")
    logger.info(f"ClickHouse URL: {get_env().get('CLICKHOUSE_ANALYTICS_URL', 'clickhouse://localhost:8123/analytics')}")
    logger.info(f"Redis URL: {get_env().get('REDIS_ANALYTICS_URL', 'redis://localhost:6379/2')}")


async def main():
    """
    Main function to run the analytics setup.
    """
    print("=" * 60)
    print("Netra Analytics - Grafana Integration Setup")
    print("=" * 60)
    
    validate_environment_variables()
    
    setup_results = await setup_analytics_environment()
    
    print("\n" + "=" * 60)
    print("SETUP SUMMARY")
    print("=" * 60)
    
    # Print health check status
    health = setup_results.get("health_check", {})
    print(f"Grafana Health: {health.get('status', 'unknown').upper()}")
    if health.get('grafana_version'):
        print(f"Grafana Version: {health['grafana_version']}")
    
    # Print datasource results
    print(f"Datasources Created: {len(setup_results['datasources'])}")
    for ds in setup_results["datasources"]:
        print(f"  - {ds.get('name', 'Unknown')}: {ds.get('uid', 'N/A')}")
    
    # Print dashboard results
    print(f"Dashboards Provisioned: {len(setup_results['dashboards'])}")
    for dashboard in setup_results["dashboards"]:
        print(f"  - {dashboard.get('title', 'Unknown')}: {dashboard.get('uid', 'N/A')}")
    
    # Print alert results
    print(f"Alert Rules Created: {len(setup_results['alerts'])}")
    for alert in setup_results["alerts"]:
        print(f"  - {alert.get('title', 'Unknown')}")
    
    # Print errors if any
    if setup_results["errors"]:
        print(f"\nErrors ({len(setup_results['errors'])}):")
        for error in setup_results["errors"]:
            print(f"  - {error}")
    else:
        print("\n PASS:  All setup completed successfully!")
    
    print("\n" + "=" * 60)
    print("You can now access your dashboards in Grafana:")
    grafana_url = get_env().get('GRAFANA_API_URL', 'http://localhost:3000')
    print(f"  - Executive Overview: {grafana_url}/d/executive_overview_001")
    print(f"  - Prompt Analytics: {grafana_url}/d/prompt_analytics_001")
    print(f"  - User Behavior: {grafana_url}/d/user_behavior_001")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
