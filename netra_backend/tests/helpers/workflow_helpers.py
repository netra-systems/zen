"""Workflow and batch helper functions for Quality Gate Service tests"""

from netra_backend.app.services.quality_gate_service import ContentType

def create_mixed_content_batch():
    """Create batch with mixed content types"""
    return [
        ("Error: Out of memory", ContentType.ERROR_MESSAGE),
        ("SELECT * FROM users", ContentType.DATA_ANALYSIS),
        ("Step 1: Install package", ContentType.ACTION_PLAN),
        ("Report summary here", ContentType.REPORT),
        ("Route to optimization team", ContentType.TRIAGE),
        ("General content", ContentType.GENERAL),
        ("Reduce latency by 50ms", ContentType.OPTIMIZATION)
    ]

def setup_complete_optimization_workflow_content():
    """Create complete optimization workflow content (part 1)"""
    return """
    System Optimization Plan
    
    Current Performance Baseline:
    - Request latency: 450ms p95, 200ms p50
    - Throughput: 1,200 requests per second
    - GPU utilization: 45% average, 78% peak
    - Memory usage: 14GB / 16GB available
    - Monthly cost: $3,500 for compute resources
    
    Identified Bottlenecks:
    1. Inefficient batch processing (batch_size=4)
    2. No caching for repeated queries
    3. Synchronous I/O operations blocking GPU
    """

def setup_optimization_strategy_content():
    """Create optimization strategy content (part 2)"""
    return """
    Optimization Strategy:
    
    Phase 1 - Quick Wins (Week 1):
    - Increase batch_size to 32
    - Enable KV cache with 2GB allocation
    - Implement async I/O handlers
    
    Implementation Steps:
    ```bash
    # Update configuration
    sed -i 's/batch_size=4/batch_size=32/' config.yaml
    
    # Install caching layer
    pip install redis-cache==2.1.0
    python setup_cache.py --size 2GB --ttl 3600
    
    # Deploy async handlers
    git checkout feature/async-io
    python deploy.py --service inference --async
    ```
    """

def setup_optimization_outcomes_content():
    """Create optimization outcomes content (part 3)"""
    return """
    Phase 2 - Advanced Optimizations (Week 2):
    - Implement INT8 quantization
    - Enable tensor parallelism across 4 GPUs
    - Use Flash Attention 2 for transformer layers
    
    Expected Outcomes:
    - Latency: 450ms  ->  180ms p95 (60% reduction)
    - Throughput: 1,200  ->  3,600 RPS (3x increase)
    - GPU utilization: 45%  ->  85% (better resource usage)
    - Memory: 14GB  ->  8GB (43% reduction)
    - Cost: $3,500  ->  $2,100/month (40% savings)
    
    Success Metrics:
    - All API endpoints respond < 200ms p95
    - Zero downtime during migration
    - Accuracy degradation < 0.5%
    
    Rollback Plan:
    - Keep previous deployment in blue-green setup
    - Monitor error rates, rollback if > 1%
    - Maintain config backups in git
    
    Trade-offs:
    - 0.3% accuracy loss from quantization
    - Increased complexity in deployment
    - Initial 2-day migration effort required
    """

def setup_optimization_workflow_context():
    """Create context for optimization workflow testing"""
    return {
        "user_request": "Create a detailed plan to optimize our inference system",
        "data_source": "production_metrics",
        "constraints": "Must maintain 99.9% uptime"
    }

def combine_optimization_content():
    """Combine all optimization content parts"""
    part1 = setup_complete_optimization_workflow_content()
    part2 = setup_optimization_strategy_content()
    part3 = setup_optimization_outcomes_content()
    return f"{part1}\n\n{part2}\n\n{part3}"