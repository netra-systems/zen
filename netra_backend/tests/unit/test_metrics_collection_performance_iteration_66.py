"""
Test Metrics Collection Performance - Iteration 66

Business Value Justification:
- Segment: Enterprise/Mid
- Business Goal: Observability & Performance Monitoring
- Value Impact: Enables data-driven optimization decisions
- Strategic Impact: Provides insights for scaling and cost optimization
"""

import pytest
import asyncio
from unittest.mock import MagicMock
import time
import statistics
import json


class TestMetricsCollectionPerformance:
    """Test metrics collection system performance and efficiency"""
    
    @pytest.mark.asyncio
    async def test_high_frequency_metrics_collection(self):
        """Test collection of high-frequency metrics without performance impact"""
        metrics_buffer = []
        collection_overhead = []
        
        async def collect_system_metrics():
            """Simulate collecting system metrics"""
            collection_start = time.time()
            
            # Simulate various metric collection operations
            metrics = {
                "timestamp": time.time(),
                "cpu_usage": 45.2 + (time.time() % 10),
                "memory_usage": 78.5 + (time.time() % 5),
                "request_count": len(metrics_buffer),
                "response_time": 25.5 + (time.time() % 15),
                "error_rate": 0.02
            }
            
            metrics_buffer.append(metrics)
            collection_time = (time.time() - collection_start) * 1000  # ms
            collection_overhead.append(collection_time)
            
            return metrics
        
        # Test high-frequency collection
        start_time = time.time()
        collection_tasks = []
        
        for i in range(100):  # 100 metric collections
            task = asyncio.create_task(collect_system_metrics())
            collection_tasks.append(task)
            await asyncio.sleep(0.001)  # 1ms intervals = 1000 Hz
        
        results = await asyncio.gather(*collection_tasks)
        total_time = time.time() - start_time
        
        # Analyze collection performance
        avg_collection_overhead = statistics.mean(collection_overhead)
        max_collection_overhead = max(collection_overhead)
        collection_rate = len(results) / total_time
        
        performance_metrics = {
            "total_collections": len(results),
            "total_time": total_time,
            "avg_overhead_ms": avg_collection_overhead,
            "max_overhead_ms": max_collection_overhead,
            "collection_rate_hz": collection_rate,
            "overhead_percentage": (sum(collection_overhead) / 1000) / total_time * 100
        }
        
        # Verify performance characteristics
        assert performance_metrics["avg_overhead_ms"] < 1.0  # < 1ms average overhead
        assert performance_metrics["max_overhead_ms"] < 5.0  # < 5ms max overhead
        assert performance_metrics["collection_rate_hz"] > 500  # > 500 Hz collection rate
        assert performance_metrics["overhead_percentage"] < 10  # < 10% overhead
        
        return performance_metrics
    
    def test_metrics_aggregation_efficiency(self):
        """Test efficient aggregation of collected metrics"""
        raw_metrics = []
        
        # Generate sample metrics data
        base_time = time.time()
        for i in range(1000):  # 1000 data points
            metric = {
                "timestamp": base_time + i * 0.1,  # 100ms intervals
                "cpu_usage": 40 + (i % 30) + (i * 0.01),
                "memory_usage": 70 + (i % 20) + (i * 0.005),
                "request_count": i * 2 + (i % 10),
                "error_count": i // 100,  # Occasional errors
                "response_time": 50 + (i % 40) + (i * 0.02)
            }
            raw_metrics.append(metric)
        
        def aggregate_metrics(metrics, window_size=60):  # 60-second windows
            """Aggregate metrics into time windows"""
            aggregation_start = time.time()
            
            if not metrics:
                return []
            
            # Group metrics by time windows
            start_time = metrics[0]["timestamp"]
            windows = {}
            
            for metric in metrics:
                window_key = int((metric["timestamp"] - start_time) // window_size)
                if window_key not in windows:
                    windows[window_key] = []
                windows[window_key].append(metric)
            
            # Aggregate each window
            aggregated = []
            for window_key, window_metrics in windows.items():
                if not window_metrics:
                    continue
                
                window_start = start_time + (window_key * window_size)
                
                agg_metric = {
                    "window_start": window_start,
                    "window_size": window_size,
                    "sample_count": len(window_metrics),
                    "cpu_usage": {
                        "avg": statistics.mean([m["cpu_usage"] for m in window_metrics]),
                        "min": min([m["cpu_usage"] for m in window_metrics]),
                        "max": max([m["cpu_usage"] for m in window_metrics]),
                        "p95": statistics.quantiles([m["cpu_usage"] for m in window_metrics], n=20)[18]
                    },
                    "memory_usage": {
                        "avg": statistics.mean([m["memory_usage"] for m in window_metrics]),
                        "max": max([m["memory_usage"] for m in window_metrics])
                    },
                    "request_rate": sum([m["request_count"] for m in window_metrics]) / window_size,
                    "error_rate": sum([m["error_count"] for m in window_metrics]) / max(1, sum([m["request_count"] for m in window_metrics])),
                    "response_time": {
                        "avg": statistics.mean([m["response_time"] for m in window_metrics]),
                        "p95": statistics.quantiles([m["response_time"] for m in window_metrics], n=20)[18]
                    }
                }
                aggregated.append(agg_metric)
            
            aggregation_time = (time.time() - aggregation_start) * 1000
            
            return {
                "aggregated_metrics": aggregated,
                "aggregation_time_ms": aggregation_time,
                "compression_ratio": len(metrics) / len(aggregated) if aggregated else 0,
                "windows_created": len(aggregated)
            }
        
        # Test aggregation with different window sizes
        window_sizes = [10, 30, 60, 120]  # seconds
        aggregation_results = []
        
        for window_size in window_sizes:
            result = aggregate_metrics(raw_metrics, window_size)
            result["window_size"] = window_size
            aggregation_results.append(result)
        
        # Verify aggregation efficiency
        for result in aggregation_results:
            assert result["compression_ratio"] > 5  # Should compress by > 5x
            assert result["aggregation_time_ms"] < 100  # Should complete in < 100ms
            assert result["windows_created"] > 0  # Should create windows
        
        # Larger window sizes should have higher compression ratios
        small_window = next(r for r in aggregation_results if r["window_size"] == 10)
        large_window = next(r for r in aggregation_results if r["window_size"] == 120)
        
        assert large_window["compression_ratio"] > small_window["compression_ratio"]
        assert large_window["windows_created"] < small_window["windows_created"]
        
        return aggregation_results
    
    @pytest.mark.asyncio
    async def test_metrics_storage_optimization(self):
        """Test optimized storage patterns for metrics data"""
        storage_backends = {
            "memory": {"data": [], "size_bytes": 0},
            "compressed": {"data": [], "size_bytes": 0},
            "sampled": {"data": [], "size_bytes": 0}
        }
        
        async def store_metrics_memory(metrics):
            """Store metrics in memory without optimization"""
            storage_start = time.time()
            
            for metric in metrics:
                # Store full precision data
                storage_backends["memory"]["data"].append(metric)
                # Estimate storage size (rough JSON serialization)
                storage_backends["memory"]["size_bytes"] += len(json.dumps(metric))
            
            storage_time = (time.time() - storage_start) * 1000
            return {"storage_time_ms": storage_time, "backend": "memory"}
        
        async def store_metrics_compressed(metrics):
            """Store metrics with compression optimization"""
            storage_start = time.time()
            
            # Simulate compression by reducing precision and removing redundant data
            for metric in metrics:
                compressed_metric = {
                    "ts": int(metric["timestamp"]),  # Reduce timestamp precision
                    "cpu": round(metric["cpu_usage"], 1),  # 1 decimal place
                    "mem": round(metric["memory_usage"], 1),
                    "req": metric["request_count"],
                    "rt": round(metric["response_time"], 1)
                }
                storage_backends["compressed"]["data"].append(compressed_metric)
                storage_backends["compressed"]["size_bytes"] += len(json.dumps(compressed_metric))
            
            storage_time = (time.time() - storage_start) * 1000
            return {"storage_time_ms": storage_time, "backend": "compressed"}
        
        async def store_metrics_sampled(metrics):
            """Store metrics with sampling optimization"""
            storage_start = time.time()
            
            # Sample every Nth metric to reduce volume
            sample_rate = 5  # Keep every 5th metric
            
            for i, metric in enumerate(metrics):
                if i % sample_rate == 0:  # Sample
                    storage_backends["sampled"]["data"].append(metric)
                    storage_backends["sampled"]["size_bytes"] += len(json.dumps(metric))
            
            storage_time = (time.time() - storage_start) * 1000
            return {"storage_time_ms": storage_time, "backend": "sampled"}
        
        # Generate test metrics
        test_metrics = []
        base_time = time.time()
        
        for i in range(500):
            metric = {
                "timestamp": base_time + i * 0.1,
                "cpu_usage": 45.2345 + (i % 30) * 1.234,
                "memory_usage": 78.5678 + (i % 20) * 0.567,
                "request_count": i * 2 + (i % 10),
                "response_time": 25.789 + (i % 40) * 2.345,
                "host": f"server_{i % 5}",
                "service": "api_service"
            }
            test_metrics.append(metric)
        
        # Test different storage approaches
        storage_tasks = [
            store_metrics_memory(test_metrics),
            store_metrics_compressed(test_metrics),
            store_metrics_sampled(test_metrics)
        ]
        
        storage_results = await asyncio.gather(*storage_tasks)
        
        # Analyze storage efficiency
        memory_size = storage_backends["memory"]["size_bytes"]
        compressed_size = storage_backends["compressed"]["size_bytes"]
        sampled_size = storage_backends["sampled"]["size_bytes"]
        
        storage_analysis = {
            "memory_backend": {
                "size_bytes": memory_size,
                "metric_count": len(storage_backends["memory"]["data"]),
                "storage_time": next(r["storage_time_ms"] for r in storage_results if r["backend"] == "memory")
            },
            "compressed_backend": {
                "size_bytes": compressed_size,
                "metric_count": len(storage_backends["compressed"]["data"]),
                "compression_ratio": memory_size / compressed_size if compressed_size > 0 else 0,
                "storage_time": next(r["storage_time_ms"] for r in storage_results if r["backend"] == "compressed")
            },
            "sampled_backend": {
                "size_bytes": sampled_size,
                "metric_count": len(storage_backends["sampled"]["data"]),
                "sampling_ratio": len(test_metrics) / len(storage_backends["sampled"]["data"]) if storage_backends["sampled"]["data"] else 0,
                "storage_time": next(r["storage_time_ms"] for r in storage_results if r["backend"] == "sampled")
            }
        }
        
        # Verify optimization effectiveness
        assert storage_analysis["compressed_backend"]["compression_ratio"] > 1.2  # > 20% size reduction
        assert storage_analysis["sampled_backend"]["sampling_ratio"] > 3  # > 3x data reduction
        
        # Storage time should be reasonable for all backends
        for backend_key in ["memory_backend", "compressed_backend", "sampled_backend"]:
            assert storage_analysis[backend_key]["storage_time"] < 50  # < 50ms
        
        # Compressed should be smaller than memory
        assert storage_analysis["compressed_backend"]["size_bytes"] < storage_analysis["memory_backend"]["size_bytes"]
        
        # Sampled should have fewer metrics
        assert storage_analysis["sampled_backend"]["metric_count"] < storage_analysis["memory_backend"]["metric_count"]
        
        return storage_analysis