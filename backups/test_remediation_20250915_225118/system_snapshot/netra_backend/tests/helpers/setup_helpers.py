"""Content setup helper functions for Quality Gate Service tests"""

def setup_large_optimization_content():
    """Create comprehensive optimization content for testing"""
    return """
    Performance Optimization Report:
    
    Current State: The system processes 500 requests per second with 200ms p95 latency.
    GPU utilization sits at 65% with 12GB memory usage.
    
    Proposed Changes:
    1. Enable batch processing with batch_size=32 (currently 8)
    2. Implement KV cache with 2GB allocation
    3. Use INT8 quantization for 50% memory reduction
    
    Implementation:
    ```bash
    pip install optimization-toolkit
    python optimize.py --batch-size 32 --quantize int8
    ```
    
    Expected Results:
    - Throughput: 500 RPS  ->  1500 RPS (200% increase)
    - Latency: 200ms  ->  120ms (40% reduction)
    - Memory: 12GB  ->  6GB (50% reduction)
    - Cost: $1000/month  ->  $600/month
    
    Trade-offs: 0.5% accuracy loss acceptable for 3x performance gain.
    """

def setup_specificity_test_content():
    """Create content with all specificity indicators"""
    return """
    Configure batch_size=64, learning_rate=0.001, temperature=0.7, top_k=50.
    Using quantization and pruning for optimization.
    Achieve 250ms latency, 95% GPU utilization, 3200 QPS throughput.
    Set context_window=4096, max_tokens=2048, num_beams=4.
    """

def setup_actionability_test_content():
    """Create content with file paths and URLs"""
    return """
    1. Edit /etc/config/model.yaml
    2. Download weights from https://models.example.com/weights.bin
    3. Run the script at C:\\Users\\model\\optimize.py
    """

def setup_code_block_content():
    """Create content with code blocks"""
    return """
    Execute the following:
    ```python
    model.compile(optimizer='adam')
    model.fit(data, epochs=10)
    ```
    Then run: `python train.py --epochs 10`
    """

def setup_quantification_patterns_content():
    """Create content with all quantification patterns"""
    return """
    Results show 85% accuracy improvement.
    Latency reduced by 150ms (from 200ms to 50ms).
    Memory usage: 4.5GB, storage: 250MB.
    Processing 1500 tokens per second.
    Throughput increased to 2000 QPS.
    Performance improved by 3.5x.
    Cost decreased by 40% monthly.
    """

def setup_relevance_test_context():
    """Create context for relevance testing"""
    return {
        "user_request": "How to speed up neural network training with multiple graphics cards"
    }

def setup_completeness_report_content():
    """Create content for completeness testing"""
    return """
    Summary: System performance analyzed.
    Findings: Identified three bottlenecks.
    Recommendations: Implement caching and optimization.
    Conclusion: 40% improvement expected.
    Metrics: Latency 200ms, throughput 1000 QPS.
    """

def setup_completeness_general_content():
    """Create general content for completeness testing"""
    return """
    The system needs optimization. However, there are trade-offs to consider.
    This is because performance improvements may affect accuracy.
    We have analyzed the situation thoroughly.
    """

def setup_poor_content_for_improvement():
    """Create poor content for improvement cycle testing"""
    return """
    You should probably consider maybe optimizing things.
    It's important to note that optimization is important.
    To improve performance, improve the performance.
    Generally speaking, things could be better.
    """

def setup_improved_content_after_adjustments():
    """Create improved content based on prompt adjustments"""
    return """
    Optimization Plan:
    1. Set batch_size=32 for 40% throughput increase
    2. Enable GPU caching to reduce memory transfers by 2GB
    3. Implement quantization for 50% model size reduction
    
    Expected results: 200ms latency reduction, $500/month cost savings
    """

def create_very_long_sentence():
    """Create sentence with 50+ words for clarity testing"""
    return " ".join(["word"] * 50) + "."

def create_excessive_acronyms_content():
    """Create content with many unexplained acronyms"""
    return "Use API, SDK, CLI, GUI, REST, SOAP, XML, JSON, YAML, CSV for integration."

def create_nested_parentheses_content():
    """Create content with nested parentheses"""
    return "The system (which includes components (like cache (Redis) and database)) is complex."

def create_high_overlap_content():
    """Create content with high word overlap for redundancy testing"""
    return """
    The optimization improves system performance significantly today.
    System performance optimization improves significantly with results today.
    Performance optimization system significantly improves results today.
    """

def create_multiple_impossible_claims_content():
    """Create content with multiple impossible claims"""
    return """
    Achieve 100% improvement with zero latency.
    Perfect accuracy guaranteed with infinite throughput.
    No cost solution with unlimited scaling.
    """

def create_claims_with_evidence_content():
    """Create content with evidence-based claims"""
    return "Studies show improvement according to Smith et al. (2023) [1]."

def create_context_with_data_source():
    """Create context with data source for hallucination testing"""
    return {"data_source": "production_metrics"}