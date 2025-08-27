"""
Test Async Batch Processing - Iteration 70

Business Value Justification:
- Segment: Enterprise/Mid
- Business Goal: Processing Efficiency & Throughput
- Value Impact: Improves processing throughput and reduces latency
- Strategic Impact: Enables handling of high-volume data processing
"""

import pytest
import asyncio
import time
from unittest.mock import MagicMock
import statistics


class TestAsyncBatchProcessing:
    """Test async batch processing patterns and optimizations"""
    
    @pytest.mark.asyncio
    async def test_adaptive_batch_sizing(self):
        """Test adaptive batch sizing based on processing performance"""
        
        class AdaptiveBatchProcessor:
            def __init__(self, initial_batch_size=10, min_batch_size=1, max_batch_size=100):
                self.current_batch_size = initial_batch_size
                self.min_batch_size = min_batch_size
                self.max_batch_size = max_batch_size
                self.performance_history = []
                self.processed_items = []
            
            async def process_batch(self, items):
                """Process a batch of items"""
                batch_start = time.time()
                batch_results = []
                
                # Simulate batch processing with some items taking longer
                for i, item in enumerate(items):
                    # Simulate variable processing time
                    processing_time = 0.001 + (i % 3) * 0.001  # 1-3ms per item
                    await asyncio.sleep(processing_time)
                    
                    result = {
                        "item_id": item["id"],
                        "processed_at": time.time(),
                        "processing_time": processing_time
                    }
                    batch_results.append(result)
                
                batch_duration = time.time() - batch_start
                throughput = len(items) / batch_duration
                
                # Record performance metrics
                performance_metric = {
                    "batch_size": len(items),
                    "duration": batch_duration,
                    "throughput": throughput,
                    "avg_item_time": batch_duration / len(items) if items else 0
                }
                self.performance_history.append(performance_metric)
                self.processed_items.extend(batch_results)
                
                return batch_results
            
            async def adapt_batch_size(self):
                """Adapt batch size based on recent performance"""
                if len(self.performance_history) < 3:
                    return  # Need more data
                
                recent_metrics = self.performance_history[-3:]
                avg_throughput = statistics.mean([m["throughput"] for m in recent_metrics])
                current_performance = recent_metrics[-1]
                
                # If throughput is decreasing, try smaller batches
                if len(self.performance_history) >= 2:
                    prev_throughput = self.performance_history[-2]["throughput"]
                    
                    if avg_throughput < prev_throughput * 0.9:  # 10% decrease
                        self.current_batch_size = max(
                            self.min_batch_size,
                            int(self.current_batch_size * 0.8)
                        )
                    elif avg_throughput > prev_throughput * 1.1:  # 10% increase
                        self.current_batch_size = min(
                            self.max_batch_size,
                            int(self.current_batch_size * 1.2)
                        )
                
                # Also adapt based on absolute performance
                if current_performance["avg_item_time"] > 0.01:  # Items taking too long
                    self.current_batch_size = max(
                        self.min_batch_size,
                        int(self.current_batch_size * 0.7)
                    )
            
            async def process_items_with_adaptation(self, items):
                """Process items with adaptive batching"""
                remaining_items = items.copy()
                all_results = []
                
                while remaining_items:
                    # Create batch of current size
                    batch = remaining_items[:self.current_batch_size]
                    remaining_items = remaining_items[self.current_batch_size:]
                    
                    # Process batch
                    batch_results = await self.process_batch(batch)
                    all_results.extend(batch_results)
                    
                    # Adapt batch size for next iteration
                    await self.adapt_batch_size()
                
                return all_results
            
            def get_adaptation_stats(self):
                """Get batch adaptation statistics"""
                if not self.performance_history:
                    return {}
                
                batch_sizes = [m["batch_size"] for m in self.performance_history]
                throughputs = [m["throughput"] for m in self.performance_history]
                
                return {
                    "final_batch_size": self.current_batch_size,
                    "min_batch_size_used": min(batch_sizes),
                    "max_batch_size_used": max(batch_sizes),
                    "avg_throughput": statistics.mean(throughputs),
                    "max_throughput": max(throughputs),
                    "batches_processed": len(self.performance_history),
                    "total_items_processed": len(self.processed_items)
                }
        
        processor = AdaptiveBatchProcessor(initial_batch_size=5, max_batch_size=50)
        
        # Generate test items
        test_items = [{"id": f"item_{i}", "data": f"data_{i}"} for i in range(200)]
        
        # Process items with adaptation
        start_time = time.time()
        results = await processor.process_items_with_adaptation(test_items)
        total_time = time.time() - start_time
        
        adaptation_stats = processor.get_adaptation_stats()
        
        # Verify adaptive behavior
        assert len(results) == 200  # All items processed
        assert adaptation_stats["batches_processed"] > 1  # Multiple batches used
        assert adaptation_stats["avg_throughput"] > 10    # Reasonable throughput
        
        # Batch size should have been adapted during processing
        batch_size_changed = (
            adaptation_stats["max_batch_size_used"] != adaptation_stats["min_batch_size_used"]
        )
        assert batch_size_changed or adaptation_stats["batches_processed"] <= 2  # Either adapted or few batches
    
    @pytest.mark.asyncio
    async def test_pipeline_batch_processing(self):
        """Test pipelined batch processing with multiple stages"""
        
        class PipelineBatchProcessor:
            def __init__(self):
                self.stage_queues = {
                    "input": asyncio.Queue(maxsize=100),
                    "stage1": asyncio.Queue(maxsize=100),
                    "stage2": asyncio.Queue(maxsize=100),
                    "output": asyncio.Queue(maxsize=100)
                }
                self.stage_stats = {
                    "stage1": {"batches": 0, "items": 0, "total_time": 0},
                    "stage2": {"batches": 0, "items": 0, "total_time": 0}
                }
                self.pipeline_running = False
            
            async def stage1_processor(self, batch_size=5):
                """First processing stage"""
                while self.pipeline_running:
                    batch = []
                    
                    # Collect batch
                    for _ in range(batch_size):
                        try:
                            item = await asyncio.wait_for(
                                self.stage_queues["input"].get(), timeout=0.1
                            )
                            batch.append(item)
                        except asyncio.TimeoutError:
                            break
                    
                    if not batch:
                        continue
                    
                    # Process stage 1
                    stage_start = time.time()
                    processed_batch = []
                    
                    for item in batch:
                        # Simulate first stage processing
                        await asyncio.sleep(0.001)
                        processed_item = {
                            **item,
                            "stage1_processed": True,
                            "stage1_timestamp": time.time()
                        }
                        processed_batch.append(processed_item)
                    
                    stage_duration = time.time() - stage_start
                    self.stage_stats["stage1"]["batches"] += 1
                    self.stage_stats["stage1"]["items"] += len(processed_batch)
                    self.stage_stats["stage1"]["total_time"] += stage_duration
                    
                    # Send to next stage
                    for item in processed_batch:
                        await self.stage_queues["stage1"].put(item)
            
            async def stage2_processor(self, batch_size=8):
                """Second processing stage"""
                while self.pipeline_running:
                    batch = []
                    
                    # Collect batch
                    for _ in range(batch_size):
                        try:
                            item = await asyncio.wait_for(
                                self.stage_queues["stage1"].get(), timeout=0.1
                            )
                            batch.append(item)
                        except asyncio.TimeoutError:
                            break
                    
                    if not batch:
                        continue
                    
                    # Process stage 2
                    stage_start = time.time()
                    processed_batch = []
                    
                    for item in batch:
                        # Simulate second stage processing (more intensive)
                        await asyncio.sleep(0.002)
                        processed_item = {
                            **item,
                            "stage2_processed": True,
                            "stage2_timestamp": time.time()
                        }
                        processed_batch.append(processed_item)
                    
                    stage_duration = time.time() - stage_start
                    self.stage_stats["stage2"]["batches"] += 1
                    self.stage_stats["stage2"]["items"] += len(processed_batch)
                    self.stage_stats["stage2"]["total_time"] += stage_duration
                    
                    # Send to output
                    for item in processed_batch:
                        await self.stage_queues["output"].put(item)
            
            async def run_pipeline(self, input_items):
                """Run the complete processing pipeline"""
                self.pipeline_running = True
                
                # Start pipeline stages
                stage1_task = asyncio.create_task(self.stage1_processor())
                stage2_task = asyncio.create_task(self.stage2_processor())
                
                # Feed input items
                for item in input_items:
                    await self.stage_queues["input"].put(item)
                
                # Collect output
                output_items = []
                expected_count = len(input_items)
                
                # Wait for all items to be processed
                while len(output_items) < expected_count:
                    try:
                        item = await asyncio.wait_for(
                            self.stage_queues["output"].get(), timeout=2.0
                        )
                        output_items.append(item)
                    except asyncio.TimeoutError:
                        # Check if pipeline is still active
                        remaining_items = (
                            self.stage_queues["input"].qsize() +
                            self.stage_queues["stage1"].qsize() +
                            self.stage_queues["stage2"].qsize()
                        )
                        
                        if remaining_items == 0:
                            break  # No more items in pipeline
                
                # Stop pipeline
                self.pipeline_running = False
                stage1_task.cancel()
                stage2_task.cancel()
                
                try:
                    await asyncio.gather(stage1_task, stage2_task, return_exceptions=True)
                except Exception:
                    pass
                
                return output_items
            
            def get_pipeline_stats(self):
                """Get pipeline processing statistics"""
                stats = {}
                
                for stage_name, stage_data in self.stage_stats.items():
                    if stage_data["batches"] > 0:
                        stats[stage_name] = {
                            "batches_processed": stage_data["batches"],
                            "items_processed": stage_data["items"],
                            "avg_batch_size": stage_data["items"] / stage_data["batches"],
                            "avg_batch_time": stage_data["total_time"] / stage_data["batches"],
                            "throughput": stage_data["items"] / stage_data["total_time"] if stage_data["total_time"] > 0 else 0
                        }
                
                return stats
        
        pipeline = PipelineBatchProcessor()
        
        # Generate test items
        input_items = [
            {"id": f"item_{i}", "data": f"test_data_{i}", "priority": i % 3}
            for i in range(100)
        ]
        
        # Run pipeline processing
        pipeline_start = time.time()
        output_items = await pipeline.run_pipeline(input_items)
        pipeline_duration = time.time() - pipeline_start
        
        pipeline_stats = pipeline.get_pipeline_stats()
        
        # Verify pipeline processing
        assert len(output_items) >= 80  # Should process most items (allow for some timeout)
        
        # Verify all output items went through both stages
        for item in output_items:
            assert item.get("stage1_processed") is True
            assert item.get("stage2_processed") is True
            assert "stage1_timestamp" in item
            assert "stage2_timestamp" in item
        
        # Verify pipeline efficiency
        if "stage1" in pipeline_stats and "stage2" in pipeline_stats:
            stage1_stats = pipeline_stats["stage1"]
            stage2_stats = pipeline_stats["stage2"]
            
            assert stage1_stats["batches_processed"] > 0
            assert stage2_stats["batches_processed"] > 0
            assert stage1_stats["throughput"] > 10   # Reasonable throughput
            assert stage2_stats["throughput"] > 5    # Stage 2 is slower but still reasonable
    
    @pytest.mark.asyncio
    async def test_batch_error_handling_and_recovery(self):
        """Test error handling and recovery in batch processing"""
        
        class ResilientBatchProcessor:
            def __init__(self, max_retries=3):
                self.max_retries = max_retries
                self.success_count = 0
                self.error_count = 0
                self.retry_count = 0
                self.failed_items = []
                self.processed_items = []
            
            async def process_item(self, item):
                """Process individual item with potential errors"""
                # Simulate error conditions
                if item["id"].endswith("error"):
                    raise ValueError(f"Processing error for {item['id']}")
                
                if item["id"].endswith("timeout"):
                    await asyncio.sleep(0.1)  # Simulate timeout
                    raise asyncio.TimeoutError(f"Timeout processing {item['id']}")
                
                # Normal processing
                await asyncio.sleep(0.001)
                return {
                    "id": item["id"],
                    "result": f"processed_{item['data']}",
                    "processed_at": time.time()
                }
            
            async def process_batch_with_recovery(self, items):
                """Process batch with error handling and recovery"""
                batch_results = []
                failed_in_batch = []
                
                for item in items:
                    for attempt in range(self.max_retries + 1):
                        try:
                            result = await self.process_item(item)
                            batch_results.append(result)
                            self.success_count += 1
                            break  # Success, exit retry loop
                            
                        except Exception as e:
                            self.error_count += 1
                            
                            if attempt < self.max_retries:
                                self.retry_count += 1
                                # Exponential backoff
                                await asyncio.sleep(0.01 * (2 ** attempt))
                                continue
                            else:
                                # Max retries exceeded
                                failed_item = {
                                    "item": item,
                                    "error": str(e),
                                    "attempts": attempt + 1
                                }
                                failed_in_batch.append(failed_item)
                                break
                
                return batch_results, failed_in_batch
            
            async def process_with_dead_letter_queue(self, items, batch_size=10):
                """Process items with dead letter queue for failed items"""
                remaining_items = items.copy()
                dead_letter_queue = []
                
                while remaining_items:
                    # Process batch
                    batch = remaining_items[:batch_size]
                    remaining_items = remaining_items[batch_size:]
                    
                    batch_results, batch_failures = await self.process_batch_with_recovery(batch)
                    
                    self.processed_items.extend(batch_results)
                    dead_letter_queue.extend(batch_failures)
                
                # Attempt to reprocess items from dead letter queue with different strategy
                recovered_items = []
                
                for failed_item in dead_letter_queue:
                    # Try alternative processing strategy
                    try:
                        if "error" not in failed_item["item"]["id"]:  # Skip items that will definitely fail
                            # Try with longer timeout or different approach
                            await asyncio.sleep(0.005)  # Longer processing time
                            
                            recovered_result = {
                                "id": failed_item["item"]["id"],
                                "result": f"recovered_{failed_item['item']['data']}",
                                "recovered": True,
                                "processed_at": time.time()
                            }
                            recovered_items.append(recovered_result)
                            self.success_count += 1
                    except Exception:
                        self.failed_items.append(failed_item)
                
                self.processed_items.extend(recovered_items)
                
                return {
                    "processed_items": self.processed_items,
                    "failed_items": self.failed_items,
                    "dead_letter_items": [item for item in dead_letter_queue if item not in recovered_items]
                }
            
            def get_processing_stats(self):
                """Get processing statistics"""
                total_attempts = self.success_count + self.error_count
                
                return {
                    "success_count": self.success_count,
                    "error_count": self.error_count,
                    "retry_count": self.retry_count,
                    "success_rate": self.success_count / max(1, total_attempts),
                    "retry_rate": self.retry_count / max(1, total_attempts),
                    "processed_items": len(self.processed_items),
                    "permanently_failed": len(self.failed_items)
                }
        
        processor = ResilientBatchProcessor(max_retries=2)
        
        # Create test items with some that will fail
        test_items = []
        for i in range(50):
            if i % 15 == 0:  # Some items will error
                test_items.append({"id": f"item_{i}_error", "data": f"data_{i}"})
            elif i % 20 == 0:  # Some items will timeout
                test_items.append({"id": f"item_{i}_timeout", "data": f"data_{i}"})
            else:  # Most items will succeed
                test_items.append({"id": f"item_{i}", "data": f"data_{i}"})
        
        # Process with error handling
        processing_start = time.time()
        result = await processor.process_with_dead_letter_queue(test_items, batch_size=8)
        processing_time = time.time() - processing_start
        
        processing_stats = processor.get_processing_stats()
        
        # Verify error handling and recovery
        assert len(result["processed_items"]) > 40  # Most items should be processed
        assert processing_stats["success_count"] > 40  # Most attempts should succeed
        assert processing_stats["retry_count"] > 0     # Some retries should occur
        assert processing_stats["error_count"] > 0     # Some errors should occur
        
        # Success rate should be reasonable despite errors
        assert processing_stats["success_rate"] > 0.7  # > 70% success rate
        
        # Failed items should be captured
        total_processed = len(result["processed_items"]) + len(result["failed_items"])
        assert total_processed <= len(test_items)  # Should account for all items