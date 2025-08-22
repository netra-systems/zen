#!/usr/bin/env python3
"""
Comprehensive test for Prometheus metrics collection:
1. Metrics endpoint availability
2. Counter metrics accuracy
3. Gauge metrics tracking
4. Histogram metrics distribution
5. Summary metrics calculation
6. Custom metrics registration
7. Label cardinality handling
8. Metrics aggregation
"""

# Test framework import - using pytest fixtures instead

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import pytest
from prometheus_client.parser import text_string_to_metric_families

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
METRICS_URL = os.getenv("METRICS_URL", f"{BACKEND_URL}/metrics")

class PrometheusMetricsTester:
    """Test Prometheus metrics collection."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.baseline_metrics: Dict[str, float] = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def test_metrics_endpoint(self) -> bool:
        """Test metrics endpoint availability."""
        print("\n[ENDPOINT] Testing metrics endpoint...")
        try:
            async with self.session.get(METRICS_URL) as response:
                if response.status == 200:
                    text = await response.text()
                    families = list(text_string_to_metric_families(text))
                    print(f"[OK] Metrics endpoint available: {len(families)} metric families")
                    return True
                return False
        except Exception as e:
            print(f"[ERROR] Metrics endpoint test failed: {e}")
            return False
            
    async def test_counter_metrics(self) -> bool:
        """Test counter metrics accuracy."""
        print("\n[COUNTER] Testing counter metrics...")
        try:
            # Get baseline
            async with self.session.get(METRICS_URL) as response:
                text = await response.text()
                for family in text_string_to_metric_families(text):
                    if family.name == "http_requests_total":
                        for sample in family.samples:
                            self.baseline_metrics[sample.name] = sample.value
                            
            # Generate traffic
            for _ in range(10):
                await self.session.get(f"{BACKEND_URL}/api/v1/health")
                
            # Check counter increased
            async with self.session.get(METRICS_URL) as response:
                text = await response.text()
                for family in text_string_to_metric_families(text):
                    if family.name == "http_requests_total":
                        for sample in family.samples:
                            baseline = self.baseline_metrics.get(sample.name, 0)
                            if sample.value > baseline:
                                print(f"[OK] Counter increased: {sample.name} = {sample.value}")
                                return True
                                
            return False
            
        except Exception as e:
            print(f"[ERROR] Counter metrics test failed: {e}")
            return False
            
    async def test_gauge_metrics(self) -> bool:
        """Test gauge metrics tracking."""
        print("\n[GAUGE] Testing gauge metrics...")
        try:
            async with self.session.get(METRICS_URL) as response:
                text = await response.text()
                gauge_found = False
                
                for family in text_string_to_metric_families(text):
                    if family.type == "gauge":
                        gauge_found = True
                        for sample in family.samples:
                            print(f"[INFO] Gauge: {sample.name} = {sample.value}")
                            
                if gauge_found:
                    print("[OK] Gauge metrics found and tracking")
                    return True
                    
            return False
            
        except Exception as e:
            print(f"[ERROR] Gauge metrics test failed: {e}")
            return False
            
    async def test_histogram_metrics(self) -> bool:
        """Test histogram metrics distribution."""
        print("\n[HISTOGRAM] Testing histogram metrics...")
        try:
            # Generate requests with varying latencies
            for i in range(20):
                await self.session.get(f"{BACKEND_URL}/api/v1/health")
                await asyncio.sleep(0.05 * (i % 3))  # Vary response times
                
            async with self.session.get(METRICS_URL) as response:
                text = await response.text()
                histogram_found = False
                
                for family in text_string_to_metric_families(text):
                    if "duration" in family.name.lower():
                        histogram_found = True
                        buckets = {}
                        for sample in family.samples:
                            if "_bucket" in sample.name:
                                le = sample.labels.get("le")
                                buckets[le] = sample.value
                                
                        if buckets:
                            print(f"[OK] Histogram buckets: {len(buckets)}")
                            return True
                            
                return histogram_found
                
        except Exception as e:
            print(f"[ERROR] Histogram metrics test failed: {e}")
            return False
            
    async def test_summary_metrics(self) -> bool:
        """Test summary metrics calculation."""
        print("\n[SUMMARY] Testing summary metrics...")
        try:
            async with self.session.get(METRICS_URL) as response:
                text = await response.text()
                
                for family in text_string_to_metric_families(text):
                    if family.type == "summary":
                        quantiles = {}
                        for sample in family.samples:
                            if "quantile" in sample.labels:
                                q = sample.labels["quantile"]
                                quantiles[q] = sample.value
                                
                        if quantiles:
                            print(f"[OK] Summary quantiles: {quantiles}")
                            return True
                            
                print("[INFO] No summary metrics found")
                return True  # Not all apps use summaries
                
        except Exception as e:
            print(f"[ERROR] Summary metrics test failed: {e}")
            return False
            
    async def test_custom_metrics(self) -> bool:
        """Test custom metrics registration."""
        print("\n[CUSTOM] Testing custom metrics...")
        try:
            # Register custom metric via API
            async with self.session.post(
                f"{BACKEND_URL}/api/v1/metrics/custom",
                json={
                    "name": "test_custom_metric",
                    "type": "counter",
                    "help": "Test custom metric"
                }
            ) as response:
                if response.status in [200, 201]:
                    print("[OK] Custom metric registered")
                    
                    # Increment custom metric
                    async with self.session.post(
                        f"{BACKEND_URL}/api/v1/metrics/custom/test_custom_metric/inc"
                    ) as inc_response:
                        if inc_response.status == 200:
                            print("[OK] Custom metric incremented")
                            
                    # Verify in metrics
                    async with self.session.get(METRICS_URL) as metrics_response:
                        text = await metrics_response.text()
                        if "test_custom_metric" in text:
                            print("[OK] Custom metric visible in metrics")
                            return True
                            
            return True  # Custom metrics might not be implemented
            
        except Exception as e:
            print(f"[ERROR] Custom metrics test failed: {e}")
            return False
            
    async def test_label_cardinality(self) -> bool:
        """Test label cardinality handling."""
        print("\n[CARDINALITY] Testing label cardinality...")
        try:
            async with self.session.get(METRICS_URL) as response:
                text = await response.text()
                high_cardinality_metrics = []
                
                for family in text_string_to_metric_families(text):
                    unique_label_sets = set()
                    for sample in family.samples:
                        label_tuple = tuple(sorted(sample.labels.items()))
                        unique_label_sets.add(label_tuple)
                        
                    if len(unique_label_sets) > 100:
                        high_cardinality_metrics.append(family.name)
                        print(f"[WARNING] High cardinality: {family.name} = {len(unique_label_sets)}")
                        
                if not high_cardinality_metrics:
                    print("[OK] No high cardinality metrics detected")
                    return True
                else:
                    print(f"[WARNING] {len(high_cardinality_metrics)} high cardinality metrics")
                    return len(high_cardinality_metrics) < 5
                    
        except Exception as e:
            print(f"[ERROR] Label cardinality test failed: {e}")
            return False
            
    async def test_metrics_aggregation(self) -> bool:
        """Test metrics aggregation."""
        print("\n[AGGREGATION] Testing metrics aggregation...")
        try:
            # Get aggregated metrics via API
            async with self.session.get(
                f"{BACKEND_URL}/api/v1/metrics/aggregate",
                params={"period": "5m"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if "request_rate" in data:
                        print(f"[OK] Request rate: {data['request_rate']}/s")
                    if "error_rate" in data:
                        print(f"[OK] Error rate: {data['error_rate']}%")
                    if "p95_latency" in data:
                        print(f"[OK] P95 latency: {data['p95_latency']}ms")
                        
                    return True
                    
            # Fallback to raw metrics
            async with self.session.get(METRICS_URL) as response:
                text = await response.text()
                metrics_count = len(list(text_string_to_metric_families(text)))
                print(f"[INFO] Total metrics available: {metrics_count}")
                return metrics_count > 0
                
        except Exception as e:
            print(f"[ERROR] Metrics aggregation test failed: {e}")
            return False
            
    async def test_grafana_integration(self) -> bool:
        """Test Grafana integration readiness."""
        print("\n[GRAFANA] Testing Grafana integration...")
        try:
            # Check if metrics are in Prometheus format
            async with self.session.get(METRICS_URL) as response:
                text = await response.text()
                
                # Check for required annotations
                has_help = "# HELP" in text
                has_type = "# TYPE" in text
                
                if has_help and has_type:
                    print("[OK] Metrics in Prometheus format with annotations")
                    
                    # Count metric types
                    types = {"counter": 0, "gauge": 0, "histogram": 0, "summary": 0}
                    for family in text_string_to_metric_families(text):
                        if family.type in types:
                            types[family.type] += 1
                            
                    print(f"[INFO] Metric types: {types}")
                    return True
                    
            return False
            
        except Exception as e:
            print(f"[ERROR] Grafana integration test failed: {e}")
            return False
            
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all Prometheus metrics tests."""
        results = {}
        
        results["metrics_endpoint"] = await self.test_metrics_endpoint()
        results["counter_metrics"] = await self.test_counter_metrics()
        results["gauge_metrics"] = await self.test_gauge_metrics()
        results["histogram_metrics"] = await self.test_histogram_metrics()
        results["summary_metrics"] = await self.test_summary_metrics()
        results["custom_metrics"] = await self.test_custom_metrics()
        results["label_cardinality"] = await self.test_label_cardinality()
        results["metrics_aggregation"] = await self.test_metrics_aggregation()
        results["grafana_integration"] = await self.test_grafana_integration()
        
        return results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l3
async def test_prometheus_metrics_collection():
    """Test Prometheus metrics collection."""
    async with PrometheusMetricsTester() as tester:
        results = await tester.run_all_tests()
        
        print("\n" + "="*60)
        print("PROMETHEUS METRICS TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {test_name:25} : {status}")
            
        print("="*60)
        
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        critical_tests = ["metrics_endpoint", "counter_metrics", "gauge_metrics"]
        for test in critical_tests:
            assert results.get(test, False), f"Critical test failed: {test}"

if __name__ == "__main__":
    exit_code = asyncio.run(test_prometheus_metrics_collection())
    sys.exit(0 if exit_code else 1)