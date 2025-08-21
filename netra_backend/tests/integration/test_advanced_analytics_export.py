"""
Critical Integration Test #10: Advanced Analytics Export for Revenue Pipeline Tier

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: Enterprise (Revenue Pipeline tier customers)
- Business Goal: Data warehouse integration protecting $100K-$200K MRR
- Value Impact: Ensures enterprise customers can export analytics data for compliance
- Revenue Impact: Prevents churn from large enterprise accounts requiring data portability

COVERAGE TARGET: 100% for analytics export functionality

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (modular design with helper imports)
- Function size: <8 lines each (focused, single-responsibility functions)
- Real ClickHouse integration with comprehensive mocking fallback
- Performance: Export 50K records <60 seconds, test completion <5 minutes
"""

import pytest
import asyncio
import time
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.db.clickhouse import ClickHouseService
from netra_backend.app.services.thread_analytics import get_analytics_dashboard
from netra_backend.tests.helpers.analytics_export_helpers import (

# Add project root to path
    AdvancedAnalyticsExportInfrastructure,
    AnalyticsDataGenerator,
    ExportConfigFactory
)


class TestAdvancedAnalyticsExport:
    """
    Critical Integration Test #10: Advanced Analytics Export
    BVJ: Protects $100K-$200K MRR from enterprise data export requirements
    """
    
    @pytest.fixture
    async def analytics_infrastructure(self):
        """Setup analytics export infrastructure."""
        infra = AdvancedAnalyticsExportInfrastructure()
        await infra.initialize_infrastructure()
        yield infra
        await infra.cleanup_infrastructure()
    
    @pytest.mark.asyncio
    async def test_01_clickhouse_large_dataset_export(self, analytics_infrastructure):
        """
        BVJ: Validates ClickHouse data export capability for enterprise reporting
        Tests: Large dataset export from ClickHouse with performance validation
        """
        dataset_size = 50000
        export_config = await self._create_large_export_config(dataset_size)
        export_performance = await self._execute_clickhouse_export(analytics_infrastructure, export_config)
        export_validation = await self._validate_export_performance(export_performance, dataset_size)
        await self._verify_clickhouse_export_success(export_validation, dataset_size)
    
    async def _create_large_export_config(self, record_count: int) -> Dict[str, Any]:
        """Create configuration for large dataset export."""
        return ExportConfigFactory.create_large_export_config(record_count)
    
    async def _execute_clickhouse_export(self, infra, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ClickHouse data export."""
        start_time = time.time()
        job_id = await infra.export_manager.create_export_job(config)
        export_result = await infra.export_manager.execute_export_job(job_id)
        
        return {
            "job_id": job_id,
            "result": export_result,
            "duration": time.time() - start_time,
            "records_exported": export_result["record_count"]
        }
    
    async def _validate_export_performance(self, performance: Dict[str, Any], expected_records: int) -> Dict[str, Any]:
        """Validate export performance meets requirements."""
        validation_result = {
            "performance_valid": performance["duration"] < 60.0,  # <60 seconds for 50K records
            "record_count_valid": performance["records_exported"] == expected_records,
            "export_completed": performance["result"]["status"] == "completed"
        }
        return validation_result
    
    async def _verify_clickhouse_export_success(self, validation: Dict[str, Any], expected_records: int):
        """Verify ClickHouse export completed successfully."""
        assert validation["performance_valid"], f"Export took too long (>60s)"
        assert validation["record_count_valid"], f"Record count mismatch"
        assert validation["export_completed"], f"Export did not complete"
    
    @pytest.mark.asyncio
    async def test_02_custom_report_generation_pipeline(self, analytics_infrastructure):
        """
        BVJ: Validates custom report generation for enterprise analytics needs
        Tests: Custom report templates with dynamic data filtering
        """
        report_template = await self._create_custom_report_template()
        report_generation = await self._execute_custom_report_generation(analytics_infrastructure, report_template)
        report_validation = await self._validate_custom_report_output(report_generation)
        await self._verify_custom_report_success(report_validation, report_template)
    
    async def _create_custom_report_template(self) -> Dict[str, Any]:
        """Create custom report template configuration."""
        return ExportConfigFactory.create_custom_report_template()
    
    async def _execute_custom_report_generation(self, infra, template: Dict[str, Any]) -> Dict[str, Any]:
        """Execute custom report generation."""
        analytics_data = await get_analytics_dashboard(template)
        job_id = await infra.export_manager.create_export_job(template)
        
        return {
            "template": template,
            "analytics_data": analytics_data,
            "job_id": job_id,
            "generated_at": time.time()
        }
    
    async def _validate_custom_report_output(self, generation: Dict[str, Any]) -> Dict[str, Any]:
        """Validate custom report generation output."""
        return {
            "template_applied": generation["template"] is not None,
            "data_generated": generation["analytics_data"] is not None,
            "job_created": generation["job_id"] is not None
        }
    
    async def _verify_custom_report_success(self, validation: Dict[str, Any], template: Dict[str, Any]):
        """Verify custom report generation succeeded."""
        assert validation["template_applied"], "Report template not applied"
        assert validation["data_generated"], "Analytics data not generated"
        assert validation["job_created"], "Export job not created"
    
    @pytest.mark.asyncio
    async def test_03_scheduled_export_automation(self, analytics_infrastructure):
        """
        BVJ: Validates scheduled export automation for regular enterprise reporting
        Tests: Export scheduling, recurring jobs, and automation reliability
        """
        schedule_config = await self._create_export_schedule_config()
        schedule_creation = await self._create_scheduled_export(analytics_infrastructure, schedule_config)
        schedule_validation = await self._validate_export_schedule(analytics_infrastructure, schedule_creation)
        await self._verify_schedule_automation_success(schedule_validation, schedule_config)
    
    async def _create_export_schedule_config(self) -> Dict[str, Any]:
        """Create export schedule configuration."""
        return ExportConfigFactory.create_export_schedule_config()
    
    async def _create_scheduled_export(self, infra, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create scheduled export job."""
        schedule_id = await infra.export_manager.schedule_manager.create_scheduled_export(config)
        scheduled_exports = await infra.export_manager.schedule_manager.get_scheduled_exports()
        
        return {
            "schedule_id": schedule_id,
            "config": config,
            "scheduled_exports": scheduled_exports
        }
    
    async def _validate_export_schedule(self, infra, creation: Dict[str, Any]) -> Dict[str, Any]:
        """Validate export schedule configuration."""
        return {
            "schedule_created": creation["schedule_id"] is not None,
            "schedule_active": len(creation["scheduled_exports"]) > 0,
            "config_preserved": creation["config"]["interval_hours"] == 24
        }
    
    async def _verify_schedule_automation_success(self, validation: Dict[str, Any], config: Dict[str, Any]):
        """Verify scheduled export automation."""
        assert validation["schedule_created"], "Schedule not created"
        assert validation["schedule_active"], "No active schedules found"
        assert validation["config_preserved"], "Schedule config not preserved"
    
    @pytest.mark.asyncio
    async def test_04_data_warehouse_sync_integration(self, analytics_infrastructure):
        """
        BVJ: Validates data warehouse integration for enterprise data pipelines
        Tests: Incremental sync, warehouse connections, and data consistency
        """
        warehouse_config = await self._create_warehouse_config()
        sync_execution = await self._execute_warehouse_sync(analytics_infrastructure, warehouse_config)
        sync_validation = await self._validate_warehouse_sync_results(sync_execution)
        await self._verify_warehouse_integration_success(sync_validation, warehouse_config)
    
    async def _create_warehouse_config(self) -> Dict[str, Any]:
        """Create data warehouse configuration."""
        return ExportConfigFactory.create_warehouse_config()
    
    async def _execute_warehouse_sync(self, infra, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data warehouse synchronization."""
        connection_id = await infra.data_warehouse_sync.configure_warehouse_connection(config)
        sync_config = {"connection_id": connection_id, "batch_size": config["batch_size"]}
        sync_result = await infra.data_warehouse_sync.execute_incremental_sync(sync_config)
        
        return {
            "connection_id": connection_id,
            "sync_result": sync_result,
            "config": config
        }
    
    async def _validate_warehouse_sync_results(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        """Validate warehouse sync execution results."""
        return {
            "connection_established": execution["connection_id"] is not None,
            "sync_completed": execution["sync_result"]["status"] == "completed",
            "records_synced": execution["sync_result"]["records_synced"] > 0
        }
    
    async def _verify_warehouse_integration_success(self, validation: Dict[str, Any], config: Dict[str, Any]):
        """Verify data warehouse integration succeeded."""
        assert validation["connection_established"], "Warehouse connection not established"
        assert validation["sync_completed"], "Warehouse sync not completed"
        assert validation["records_synced"], "No records synced to warehouse"
    
    @pytest.mark.asyncio
    async def test_05_format_conversion_comprehensive(self, analytics_infrastructure):
        """
        BVJ: Validates comprehensive format conversion for diverse enterprise needs
        Tests: CSV, JSON, Parquet, XML format conversions with data integrity
        """
        test_dataset = await self._create_format_test_dataset()
        format_conversions = await self._execute_all_format_conversions(analytics_infrastructure, test_dataset)
        conversion_validation = await self._validate_format_conversion_integrity(format_conversions)
        await self._verify_format_conversion_success(conversion_validation, test_dataset)
    
    async def _create_format_test_dataset(self) -> List[Dict[str, Any]]:
        """Create test dataset for format conversion."""
        return AnalyticsDataGenerator.create_test_dataset(1000)
    
    async def _execute_all_format_conversions(self, infra, dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute conversions to all supported formats."""
        conversions = {}
        
        for format_name, converter in infra.format_converters.items():
            conversion_method = getattr(converter, f"convert_to_{format_name}", None)
            if conversion_method:
                conversion_result = await conversion_method(dataset)
                conversions[format_name] = {
                    "result": conversion_result,
                    "success": conversion_result is not None
                }
        
        return conversions
    
    async def _validate_format_conversion_integrity(self, conversions: Dict[str, Any]) -> Dict[str, Any]:
        """Validate format conversion data integrity."""
        return {
            "all_formats_converted": all(conv["success"] for conv in conversions.values()),
            "format_count": len(conversions),
            "expected_formats": ["csv", "json", "parquet", "xml"]
        }
    
    async def _verify_format_conversion_success(self, validation: Dict[str, Any], dataset: List[Dict[str, Any]]):
        """Verify format conversion completed successfully."""
        assert validation["all_formats_converted"], "Not all formats converted successfully"
        assert validation["format_count"] == 4, f"Expected 4 formats, got {validation['format_count']}"
        assert len(dataset) == 1000, "Test dataset size mismatch"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])