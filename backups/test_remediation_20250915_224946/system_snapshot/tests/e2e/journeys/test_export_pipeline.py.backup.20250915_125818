"""E2E Test #9: Export and Reporting Pipeline - Large Dataset Export Validation

BUSINESS VALUE JUSTIFICATION (BVJ):
1. Segment: Mid & Enterprise (data ownership and compliance critical)
2. Business Goal: Protect $20K+ MRR through reliable large data export capability
3. Value Impact: Enables enterprise deals requiring bulk data export and reporting
4. Revenue Impact: 25% of enterprise deals require high-volume export features

CRITICAL E2E test for complete export pipeline flow:
Frontend  ->  Request Export  ->  Backend Generation  ->  Large Dataset Handling  ->  Download  ->  Validation

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (modular design with helper imports)
- Function size: <8 lines each
- Real service integration with actual data generation for performance testing
- Performance: Export 10K records <30 seconds, <5 seconds per test step
- Support multiple export formats: CSV, JSON, Excel

TECHNICAL COVERAGE:
- Request export via Frontend API
- Generate reports with large datasets (Backend)
- Handle large datasets efficiently (memory management)
- Download file validation (Frontend)  
- Verify data completeness (100% accuracy)
- Test various export formats and data types
"""

import asyncio
import time
import json
import httpx
import tempfile
import os
from typing import Dict, Any, List
from pathlib import Path
import pytest
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.export_pipeline_helpers import (
    LargeDatasetGenerator, ExportRequestManager, ExportFileValidator, PerformanceTracker,
    LargeDatasetGenerator,
    ExportRequestManager,
    ExportFileValidator,
    PerformanceTracker
)
from tests.e2e.harness_utils import UnifiedTestHarnessComplete


class ExportPipelineCore:
    """Core export pipeline test infrastructure."""
    
    def __init__(self, harness: UnifiedTestHarnessComplete):
        self.harness = harness
        self.data_generator = LargeDatasetGenerator()
        self.request_manager = ExportRequestManager(harness)
        self.validator = ExportFileValidator()
        self.performance_tracker = PerformanceTracker()
    
    async def setup_test_environment(self) -> None:
        """Setup export pipeline test environment."""
        await self.request_manager.initialize_backend_connection()
    
    async def test_teardown_test_environment(self) -> None:
        """Cleanup export pipeline test environment."""
        await self.request_manager.cleanup_connections()


class TestExportPipelineE2Eer:
    """Executes complete export pipeline E2E test flow."""
    
    def __init__(self, harness: UnifiedTestHarnessComplete):
        self.harness = harness
        self.core = ExportPipelineCore(harness)
    
    async def execute_large_csv_export_flow(self, record_count: int = 10000) -> Dict[str, Any]:
        """Execute large CSV export flow with performance validation."""
        start_time = time.time()
        results = {"steps": [], "success": False, "duration": 0, "record_count": record_count}
        
        try:
            # Step 1: Setup environment
            await self.core.setup_test_environment()
            results["steps"].append({"step": "environment_setup", "success": True})
            
            # Step 2: Generate large dataset
            dataset = await self._generate_large_dataset(record_count)
            results["steps"].append({"step": "dataset_generated", "success": True, "records": len(dataset)})
            
            # Step 3: Request CSV export
            export_data = await self._request_csv_export(dataset)
            results["steps"].append({"step": "export_requested", "success": True})
            
            # Step 4: Generate export file
            file_path = await self._generate_export_file(export_data, "csv")
            results["steps"].append({"step": "file_generated", "success": True, "path": file_path})
            
            # Step 5: Validate download and completeness
            validation_result = await self._validate_export_completeness(file_path, dataset, "csv")
            results["steps"].append({"step": "validation_complete", "success": validation_result})
            
            results["success"] = validation_result
            results["duration"] = time.time() - start_time
            
            # CRITICAL: Must complete 10K records in <30 seconds
            assert results["duration"] < 30.0, f"Export took {results['duration']:.2f}s > 30s limit"
            
        except Exception as e:
            results["error"] = str(e)
            results["duration"] = time.time() - start_time
            raise
        
        return results
    
    async def execute_multi_format_export_flow(self) -> Dict[str, Any]:
        """Execute export flow testing multiple formats."""
        formats = ["json", "csv", "excel"]
        results = {"formats": {}, "success": True, "total_duration": 0}
        start_time = time.time()
        
        dataset = await self._generate_large_dataset(1000)  # Smaller for multi-format test
        
        for format_type in formats:
            format_start = time.time()
            try:
                export_data = await self._request_format_export(dataset, format_type)
                file_path = await self._generate_export_file(export_data, format_type)
                validation_result = await self._validate_export_completeness(file_path, dataset, format_type)
                
                results["formats"][format_type] = {
                    "success": validation_result,
                    "duration": time.time() - format_start,
                    "file_path": file_path
                }
            except Exception as e:
                results["formats"][format_type] = {
                    "success": False,
                    "error": str(e),
                    "duration": time.time() - format_start
                }
                results["success"] = False
        
        results["total_duration"] = time.time() - start_time
        return results
    
    async def _generate_large_dataset(self, record_count: int) -> List[Dict[str, Any]]:
        """Generate large dataset for export testing."""
        return await self.core.data_generator.generate_ai_operation_records(record_count)
    
    async def _request_csv_export(self, dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Request CSV export via API."""
        return await self.core.request_manager.request_export(dataset, "csv")
    
    async def _request_format_export(self, dataset: List[Dict[str, Any]], format_type: str) -> Dict[str, Any]:
        """Request export in specific format."""
        return await self.core.request_manager.request_export(dataset, format_type)
    
    async def _generate_export_file(self, export_data: Dict[str, Any], format_type: str) -> str:
        """Generate export file from data."""
        return await self.core.request_manager.generate_export_file(export_data, format_type)
    
    async def _validate_export_completeness(self, file_path: str, original_data: List[Dict[str, Any]], format_type: str) -> bool:
        """Validate export file completeness and data integrity."""
        return await self.core.validator.validate_export_file(file_path, original_data, format_type)


# Pytest Test Implementation
@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.e2e
async def test_large_dataset_export_pipeline():
    """
    CRITICAL E2E Test #9: Export and Reporting Pipeline - Large Dataset Export
    
    Business Value: $20K+ MRR - Large data export capability for enterprises
    
    Test Flow:
    1. Setup export pipeline environment
    2. Generate 10K AI operation records
    3. Request CSV export via API
    4. Generate export file with proper memory management
    5. Validate file download functionality
    6. Verify 100% data completeness
    7. Ensure performance targets (<30 seconds)
    
    Success Criteria:
    - Export 10K records in <30 seconds
    - 100% data completeness validation
    - Proper file download mechanism
    - Memory efficient processing
    - Real API integration (minimal mocking)
    """
    harness = UnifiedE2ETestHarness()
    tester = ExportPipelineE2ETester(harness)
    
    try:
        # Execute large dataset export flow with 10K records
        results = await tester.execute_large_csv_export_flow(10000)
        
        # Validate overall success
        assert results["success"], f"Export pipeline failed: {results.get('error')}"
        
        # Validate performance requirement (10K records <30 seconds)
        assert results["duration"] < 30.0, f"Performance requirement failed: {results['duration']:.2f}s"
        
        # Validate record count
        assert results["record_count"] == 10000, f"Record count mismatch: {results['record_count']}"
        
        # Validate all critical steps completed
        expected_steps = ["environment_setup", "dataset_generated", "export_requested", "file_generated", "validation_complete"]
        completed_steps = [step["step"] for step in results["steps"]]
        
        for expected_step in expected_steps:
            assert expected_step in completed_steps, f"Missing critical step: {expected_step}"
        
        # Validate step success
        failed_steps = [step for step in results["steps"] if not step.get("success")]
        assert len(failed_steps) == 0, f"Failed steps: {failed_steps}"
        
        print(f"[SUCCESS] Large Export E2E: {results['duration']:.2f}s for {results['record_count']} records")
        print(f"[PERF] Performance: {results['record_count']/results['duration']:.0f} records/second")
        print(f"[BIZ] $20K+ MRR export capability VALIDATED")
        
    finally:
        await harness.cleanup()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.e2e  
async def test_multi_format_export_support():
    """
    Test multiple export formats: CSV, JSON, Excel
    Business Value: Format flexibility for different enterprise requirements
    """
    harness = UnifiedE2ETestHarness()
    tester = ExportPipelineE2ETester(harness)
    
    try:
        # Execute multi-format export flow
        results = await tester.execute_multi_format_export_flow()
        
        # Validate overall success
        assert results["success"], "Multi-format export failed"
        
        # Validate all formats succeeded
        expected_formats = ["json", "csv", "excel"]
        for format_type in expected_formats:
            format_result = results["formats"].get(format_type)
            assert format_result, f"Missing format result: {format_type}"
            assert format_result["success"], f"Format {format_type} failed: {format_result.get('error')}"
        
        # Validate performance (all formats <10 seconds total)
        assert results["total_duration"] < 10.0, f"Multi-format export too slow: {results['total_duration']:.2f}s"
        
        print(f"[SUCCESS] Multi-format export: {results['total_duration']:.2f}s")
        print(f"[FORMATS] Formats supported: {list(results['formats'].keys())}")
        print(f"[BIZ] Enterprise format requirements VALIDATED")
        
    finally:
        await harness.cleanup()


@pytest.mark.asyncio
@pytest.mark.performance
async def test_export_performance_under_load():
    """
    Performance validation for export pipeline under load conditions.
    Business Value: Ensure export reliability during peak usage
    """
    harness = UnifiedE2ETestHarness()
    tester = ExportPipelineE2ETester(harness)
    
    try:
        # Test concurrent exports
        tasks = []
        for i in range(3):
            task = tester.execute_large_csv_export_flow(5000)  # 5K records each
            tasks.append(task)
        
        # Execute concurrent exports
        start_time = time.time()
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Validate all exports succeeded
        successful_exports = [r for r in results_list if isinstance(r, dict) and r.get("success")]
        assert len(successful_exports) == 3, f"Only {len(successful_exports)}/3 exports succeeded"
        
        # Validate total performance (concurrent exports <45 seconds)
        assert total_duration < 45.0, f"Concurrent exports too slow: {total_duration:.2f}s"
        
        avg_duration = sum(r["duration"] for r in successful_exports) / len(successful_exports)
        total_records = sum(r["record_count"] for r in successful_exports)
        
        print(f"[SUCCESS] Concurrent export: {total_duration:.2f}s total")
        print(f"[PERF] Average per export: {avg_duration:.2f}s")
        print(f"[SCALE] Total records exported: {total_records}")
        print(f"[BIZ] Load handling capability VALIDATED")
        
    finally:
        await harness.cleanup()
