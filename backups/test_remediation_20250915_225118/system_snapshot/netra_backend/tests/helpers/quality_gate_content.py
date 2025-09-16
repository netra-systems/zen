"""Test content generators for Quality Gate Service tests"""

from netra_backend.app.services.quality_gate_service import ContentType

def get_high_quality_optimization_content():
    """Get high-quality optimization content for testing"""
    return """
    Based on the analysis, we can optimize GPU utilization by:
    1. Increasing batch size from 16 to 32, reducing latency by 23ms (15% improvement)
    2. Implementing KV cache optimization, saving 2.3GB memory per request
    3. Enabling tensor parallelism across 4 GPUs, achieving 3.8x throughput increase
    4. Adjusting temperature from 1.0 to 0.7 for more deterministic outputs
    
    These changes will reduce cost per token from $0.002 to $0.0014 (30% reduction)
    and improve p95 latency from 150ms to 115ms.
    """

def get_low_quality_generic_content():
    """Get low-quality generic content for testing"""
    return """
    It is important to note that generally speaking, you might want to consider
    looking into optimization. Throughout history, we have seen that in general,
    things can be improved. You could try to enhance performance by making it better.
    It goes without saying that at the end of the day, optimization is about
    optimizing things. Needless to say, you should think about improving the system.
    """

def get_circular_reasoning_content():
    """Get content with circular reasoning patterns"""
    return """
    To improve performance, you should improve the performance metrics.
    Optimize the system by optimizing its components.
    For better results, use better algorithms to get better outcomes.
    """

def get_data_analysis_content():
    """Get data analysis content with quantitative metrics"""
    return """
    Analysis of the past 7 days shows:
    - Average GPU utilization: 78.3% (peak: 95%, trough: 42%)
    - Memory consumption: 14.2GB average, 18.7GB p95
    - Request latency: p50=45ms, p95=120ms, p99=280ms
    - Total requests processed: 1.2M with 99.94% success rate
    - Cost breakdown: $1,234 compute, $567 storage, $89 network
    
    Key finding: 65% of latency spikes correlate with batch sizes > 48
    """

def get_complete_action_plan_content():
    """Get complete action plan content for testing"""
    return """
    Action Plan for GPU Optimization:
    
    Timeline: 2 weeks from January 15-26, 2025.
    
    Step 1 - Deploy KV cache optimization in Week 1:
    Deploy to staging environment with 2 days timeline.
    Configuration requirements: cache size 8GB per GPU instance.
    Set TTL to 300 seconds for frequently accessed keys.
    Enable cache warming for top 1000 queries.
    Verification: run comprehensive test suite and monitor staging metrics.
    
    Step 2 - A/B Testing in Week 1, Days 3-5:
    Test with 10% production traffic.
    Control group uses current baseline configuration.
    Test group uses KV cache with above parameters.
    Monitor p50/p95/p99 latency, GPU memory, and cache hit rate.
    
    Step 3 - Analysis and Adjustment on Week 2, Day 1:
    Analyze test results against requirements.
    Target 35% cache hit rate and less than 50ms p95 latency.
    Adjust parameters if memory usage exceeds 85%.
    Verification: validate all adjustments in staging first.
    
    Step 4 - Production Rollout in Week 2, Days 2-4:
    Use gradual rollout: 25% then 50% then 100% traffic.
    Deploy 25% rollout Monday morning and monitor 24 hours.
    Deploy 50% rollout Tuesday if error rate stays below 0.1%.
    Deploy 100% rollout Thursday if all metrics meet requirements.
    Verification: maintain continuous monitoring at each step.
    
    Expected Outcome and Success Criteria:
    Reduce p95 latency from 180ms to 144ms for 20% improvement.
    Maintain 99.9% uptime requirement.
    Reduce cost per request from $0.0020 to $0.0015.
    Keep GPU memory utilization below 90% at peak load.
    """

def get_borderline_quality_content():
    """Get borderline quality content for strict mode testing"""
    return """
    The system shows 180ms p95 latency which could benefit from optimization.
    Consider increasing batch size from 32 to 64 and implementing KV cache.
    Memory usage at 8GB is 85% of capacity and should be reduced to 6GB.
    Implement these changes to achieve 20% performance improvement.
    """

def get_good_error_message_content():
    """Get good error message content for testing"""
    return """
    Error: GPU memory exceeded (18.5GB used, 16GB available)
    
    Cause: Batch size 64 with model size 7B exceeds available VRAM
    
    Solutions:
    1. Reduce batch size to 32 or less
    2. Enable gradient checkpointing to save ~30% memory
    3. Use mixed precision training (fp16) to halve memory usage
    
    Run with --batch-size 32 --gradient-checkpoint to retry
    """

def get_redundant_report_content():
    """Get redundant report content for testing"""
    return """
    Executive Summary:
    The system needs optimization to improve performance.
    
    Introduction:
    This report discusses how the system needs optimization to improve performance.
    
    Analysis:
    Our analysis shows the system needs optimization to improve performance.
    
    Findings:
    We found that the system needs optimization to improve performance.
    
    Conclusion:
    In conclusion, the system needs optimization to improve performance.
    """

def get_domain_specific_content():
    """Get domain-specific content for testing"""
    return """
    Implemented flash attention with 8-bit quantization, reducing memory footprint
    by 42% while maintaining 98.5% accuracy. The KV cache optimization leverages
    tensor parallelism across 4 A100 GPUs, achieving 3,200 tokens/second throughput
    with p99 latency of 89ms. Cost per million tokens dropped from $2.10 to $1.35.
    """

def get_mediocre_content():
    """Get mediocre content for retry suggestion testing"""
    return """
    To optimize the system, you should reduce latency by implementing caching.
    This will improve performance by reducing database calls.
    Consider using Redis or similar in-memory caching solutions.
    Monitor the results and adjust as needed for your specific use case.
    """

def get_hallucination_risk_content():
    """Get content with potential hallucination risks"""
    return """
    According to the non-existent study by Dr. Fakename at Imaginary University,
    the XYZ-9000 algorithm (which I just invented) can achieve 110% accuracy
    and negative latency. This revolutionary approach violates no laws of physics
    and has been proven in -1 production environments.
    """

def get_triage_content():
    """Get triage content for testing"""
    return """
    Request Category: Performance Optimization
    Priority: High
    
    Analysis: User experiencing high latency (>500ms) on inference requests.
    Root cause appears to be inefficient batch processing with current configuration.
    
    Recommended next steps:
    1. Analyze current batch size and GPU utilization metrics
    2. Review model architecture for optimization opportunities
    3. Investigate caching strategies for repeated requests
    """

def get_high_specificity_content():
    """Get high specificity content for testing"""
    return """
    Configure batch_size=32, learning_rate=0.001, and max_tokens=2048.
    Use quantization with 8-bit precision for 42% memory reduction.
    Deploy on A100 GPUs with 80GB VRAM, achieving 3,200 tokens/second.
    """

def get_low_specificity_content():
    """Get low specificity content for testing"""
    return "You should optimize things to make them better and more efficient."

def get_high_actionability_content():
    """Get high actionability content for testing"""
    return """
    Step 1: Install Redis with `pip install redis`
    Step 2: Configure connection pooling with pool_size=20
    Step 3: Enable caching by adding @cache decorator
    Step 4: Set TTL to 3600 seconds for optimal performance
    """

def get_low_actionability_content():
    """Get low actionability content for testing"""
    return "You might want to consider perhaps looking into optimization possibilities."

def get_high_quantification_content():
    """Get high quantification content for testing"""
    return """
    Performance improved by 35% with latency reduced from 150ms to 97ms.
    Memory usage decreased by 2.1GB (45% reduction).
    Throughput increased to 4,500 QPS with 99.9% uptime.
    Cost per request dropped from $0.025 to $0.018 (28% savings).
    """

def get_low_quantification_content():
    """Get low quantification content for testing"""
    return "The system runs faster and uses less memory with better performance."

def get_optimization_context():
    """Get optimization context for testing"""
    return "Optimize GPU memory usage by enabling mixed precision training and gradient checkpointing."

def get_relevant_context():
    """Get relevant context for testing"""
    return {"user_request": "Help me reduce GPU memory consumption during training"}

def get_irrelevant_context():
    """Get irrelevant context for testing"""
    return {"user_request": "How do I bake a chocolate cake"}

def get_complete_optimization_content():
    """Get complete optimization content for testing"""
    return """
    Current system uses 8GB memory with 200ms latency.
    Proposed optimization implements caching layer.
    Implementation requires Redis installation and configuration.
    Expected improvement: 40% latency reduction.
    Trade-off: Slight increase in complexity and memory overhead.
    """

def get_complete_action_plan_simple():
    """Get complete action plan with simple structure"""
    return """
    Step 1: Assess current requirements and timeline.
    Step 2: Set up development environment and tools.
    Step 3: Implement core functionality with testing.
    Expected outcome: Fully functional deployment pipeline.
    Verification: Run automated tests and performance benchmarks.
    """

def get_clear_content():
    """Get clear, well-structured content for testing"""
    return """
    Optimization Plan:
    1. First, profile current performance
    2. Then, identify bottlenecks
    3. Finally, implement targeted improvements
    
    Expected results: 30% performance gain
    """

def get_unclear_content():
    """Get unclear, complex content for testing"""
    return """
    The system, which incorporates various SOTA methodologies and leverages state-of-the-art 
    architectures with complex interdependencies, requires optimization through multi-faceted 
    approaches that consider FLOPS, VRAM, TPU, GPU, CPU, and other hardware-specific constraints 
    (including but not limited to memory bandwidth, cache hierarchies, and interconnect topologies) 
    while maintaining backward compatibility with legacy systems.
    """

def get_high_redundancy_content():
    """Get high redundancy content for testing"""
    return """
    The system needs optimization for better performance.
    We should optimize the system to achieve better performance.
    Better performance requires system optimization efforts.
    Optimization will help the system perform better.
    """

def get_low_redundancy_content():
    """Get low redundancy content for testing"""
    return """
    First, profile the current system to identify bottlenecks.
    Second, implement caching to reduce database calls.
    Third, optimize algorithms for better time complexity.
    Finally, monitor performance improvements over time.
    """

def get_high_hallucination_risk_content():
    """Get high hallucination risk content for testing"""
    return """
    According to studies by Dr. Imaginary at FakeUniversity (2024),
    the new SuperAI-9000 algorithm achieves 150% accuracy rates
    and processes infinite data in zero time with guaranteed results.
    This revolutionary breakthrough violates no laws of physics.
    """

def get_low_hallucination_risk_content():
    """Get low hallucination risk content for testing"""
    return """
    Based on our benchmark testing, the optimization reduced latency by 25%
    from 100ms to 75ms average response time. Memory usage decreased from
    4GB to 3.2GB during peak load. These results are reproducible in our
    test environment with 95% confidence interval.
    """

def get_batch_validation_contents():
    """Get contents for batch validation testing"""
    return [
        ("High-quality content with specific metrics: latency=50ms, throughput=2000 QPS", ContentType.DATA_ANALYSIS),
        ("Generic content that needs improvement", ContentType.GENERAL),
        ("Detailed action plan: Step 1: Install Redis, Step 2: Configure caching", ContentType.ACTION_PLAN)
    ]

def get_batch_validation_context():
    """Get context for batch validation testing"""
    return {
        "user_request": "Help me optimize my machine learning training pipeline",
        "constraints": "Limited to 16GB VRAM"
    }

def get_brief_optimization_contents():
    """Get brief optimization contents for context testing"""
    return [
        ("Optimize GPU memory", ContentType.OPTIMIZATION),
        ("Reduce training time", ContentType.OPTIMIZATION)
    ]