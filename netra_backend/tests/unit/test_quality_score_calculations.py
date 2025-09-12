"""
Test Quality Score Calculation Business Logic - Core Unit Tests

Business Value Justification (BVJ):
- Segment: All (Quality assessment affects all AI output evaluations)
- Business Goal: Content quality assurance and AI output optimization
- Value Impact: Ensures AI recommendations meet quality standards preventing poor customer experience
- Strategic Impact: CRITICAL - Quality assessment directly impacts customer satisfaction and platform credibility

This test suite validates the core business logic for quality score calculations
that determine the value and reliability of AI-generated content and recommendations.
"""

import pytest
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.services.quality.quality_score_calculators import QualityScoreCalculators


class TestQualityScoreCalculations(BaseTestCase):
    """Test quality score calculations deliver accurate content assessment for business value."""
    
    def setup_method(self):
        """Setup test environment with isolated configuration."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        
    def teardown_method(self):
        """Clean up test environment."""
        super().teardown_method()
        
    @pytest.mark.unit
    def test_specificity_score_detects_generic_content(self):
        """Test that specificity score correctly identifies and penalizes generic AI slop."""
        # High-quality specific content
        specific_content = """
        Configure Redis connection pool with max_connections=50 and timeout=5000ms.
        Set Redis cluster nodes to redis-cluster-0.internal:6379 and redis-cluster-1.internal:6379.
        Enable connection health checks every 30 seconds using PING commands.
        """
        
        specific_score = QualityScoreCalculators.calculate_specificity_score(specific_content)
        assert specific_score > 0.7, f"Specific content should score high: {specific_score}"
        
        # Generic AI slop content
        generic_content = """
        It is important to note that generally speaking, you should consider the following 
        various factors when optimizing performance. There are multiple aspects to improve
        efficiency and enhance capabilities for better results.
        """
        
        generic_score = QualityScoreCalculators.calculate_specificity_score(generic_content)
        assert generic_score < 0.5, f"Generic content should score low: {generic_score}"
        
        # Business requirement: Specific content should significantly outscore generic content
        score_difference = specific_score - generic_score
        assert score_difference > 0.3, f"Quality gap should be significant: {score_difference}"
        
    @pytest.mark.unit
    def test_actionability_score_identifies_executable_content(self):
        """Test that actionability score correctly identifies executable recommendations."""
        # Highly actionable content with concrete steps
        actionable_content = """
        Step 1: Install the Redis client using `pip install redis`
        Step 2: Configure connection with `redis.ConnectionPool(host='localhost', port=6379)`
        Step 3: Set connection timeout to 5 seconds using `socket_timeout=5`
        
        ```python
        import redis
        pool = redis.ConnectionPool(host='localhost', port=6379, socket_timeout=5)
        client = await get_redis_client()  # MIGRATED: was redis.Redis(connection_pool=pool)
        ```
        
        Set max_connections=100 for high-throughput scenarios.
        """
        
        actionable_score = QualityScoreCalculators.calculate_actionability_score(actionable_content)
        assert actionable_score > 0.8, f"Actionable content should score high: {actionable_score}"
        
        # Vague, non-actionable content
        vague_content = """
        Consider using better caching solutions. Think about optimizing your database queries.
        Look into improving performance. You might want to explore various options.
        """
        
        vague_score = QualityScoreCalculators.calculate_actionability_score(vague_content)
        assert vague_score < 0.3, f"Vague content should score low: {vague_score}"
        
        # Business requirement: Actionable content provides clear business value
        assert actionable_score > vague_score + 0.5, "Actionability gap should be substantial"
        
    @pytest.mark.unit
    def test_quantification_score_rewards_measurable_content(self):
        """Test that quantification score rewards content with measurable metrics."""
        # Quantified content with specific metrics
        quantified_content = """
        Reduce latency from 200ms to 50ms using connection pooling.
        Increase throughput by 3x to handle 1500 requests per second.
        Set cache TTL to 300 seconds for optimal performance.
        Configure batch size to 100 items for 25% efficiency improvement.
        Memory usage reduced by 40% with optimized data structures.
        """
        
        quantified_score = QualityScoreCalculators.calculate_quantification_score(quantified_content)
        assert quantified_score > 0.6, f"Quantified content should score well: {quantified_score}"
        
        # Unquantified, vague content
        unquantified_content = """
        Make it faster and more efficient. Improve performance significantly.
        Use better algorithms. Optimize for speed. Reduce resource usage.
        """
        
        unquantified_score = QualityScoreCalculators.calculate_quantification_score(unquantified_content)
        assert unquantified_score < 0.2, f"Unquantified content should score low: {unquantified_score}"
        
        # Business requirement: Quantified recommendations enable measurable business outcomes
        quantification_advantage = quantified_score - unquantified_score
        assert quantification_advantage > 0.4, "Quantification should provide clear scoring advantage"
        
    @pytest.mark.unit
    def test_novelty_score_penalizes_boilerplate_content(self):
        """Test that novelty score penalizes common boilerplate and rewards unique insights."""
        # Novel, unique content
        novel_content = """
        Implement Redis Cluster with consistent hashing for horizontal scaling.
        Use Redis Streams for event sourcing with XADD commands.
        Configure Redis persistence with RDB snapshots every 300 seconds.
        Implement circuit breaker pattern using Redis SET with EX for timeout tracking.
        """
        
        novel_score = QualityScoreCalculators.calculate_novelty_score(novel_content)
        assert novel_score > 0.6, f"Novel content should score well: {novel_score}"
        
        # Boilerplate content with common phrases
        boilerplate_content = """
        Thank you for your question. I hope this helps you with your implementation.
        Please let me know if you need any clarification. Feel free to reach out.
        Don't hesitate to ask if you have more questions. Thank you for using our service.
        """
        
        boilerplate_score = QualityScoreCalculators.calculate_novelty_score(boilerplate_content)
        assert boilerplate_score < 0.4, f"Boilerplate content should score low: {boilerplate_score}"
        
        # Business requirement: Novel content provides more customer value
        novelty_advantage = novel_score - boilerplate_score
        assert novelty_advantage > 0.2, "Novel content should significantly outscore boilerplate"
        
    @pytest.mark.unit
    def test_completeness_score_validates_content_depth(self):
        """Test that completeness score validates content depth for different output types."""
        # Test comprehensive report content
        comprehensive_report = """
        Redis Performance Optimization Analysis:
        
        Current State: Redis instance handles 500 QPS with 150ms average latency.
        
        Issues Identified:
        1. Single-threaded bottleneck on CPU-intensive operations
        2. Memory fragmentation at 35% causing inefficient allocation  
        3. Network latency from suboptimal connection pooling
        
        Recommendations:
        1. Enable Redis threading for network I/O (Redis 6.0+)
        2. Implement connection pooling with min=10, max=100 connections
        3. Configure memory defragmentation with active-defrag-cycle-min=25
        4. Set up Redis Cluster for horizontal scaling
        
        Expected Impact:
        - Latency reduction: 150ms  ->  50ms (67% improvement)
        - Throughput increase: 500 QPS  ->  1500 QPS (3x improvement)
        - Memory efficiency gain: 35%  ->  15% fragmentation
        
        Implementation Timeline: 2-week phased rollout with performance monitoring.
        """
        
        report_score = QualityScoreCalculators.calculate_completeness_score(
            comprehensive_report, "report"
        )
        assert report_score > 0.8, f"Comprehensive report should score high: {report_score}"
        
        # Test incomplete recommendation
        incomplete_recommendation = """
        Use Redis for caching. It's fast.
        """
        
        incomplete_score = QualityScoreCalculators.calculate_completeness_score(
            incomplete_recommendation, "recommendation"
        )
        assert incomplete_score < 0.5, f"Incomplete recommendation should score low: {incomplete_score}"
        
        # Business requirement: Complete content provides more customer value
        completeness_gap = report_score - incomplete_score
        assert completeness_gap > 0.3, "Completeness should provide significant value differentiation"
        
    @pytest.mark.unit
    def test_domain_relevance_score_validates_technical_expertise(self):
        """Test that domain relevance score validates technical expertise and domain knowledge."""
        # High domain relevance content
        domain_expert_content = """
        Configure Redis for optimal latency by setting tcp-keepalive to 300 seconds.
        Use Redis pipelining for batch operations to reduce network RTT overhead.
        Implement memory optimization with hash-max-ziplist-entries=512.
        Set up Redis Sentinel for high availability with quorum=2 configuration.
        Enable memory compression using LZF algorithm for string values.
        Configure connection pooling with max-idle-time=300 for resource efficiency.
        """
        
        domain_score = QualityScoreCalculators.calculate_domain_relevance_score(domain_expert_content)
        assert domain_score > 0.7, f"Domain expert content should score high: {domain_score}"
        
        # Low domain relevance content
        generic_tech_content = """
        Make your system work better by using good practices. Improve things
        by making them faster and more reliable. Use appropriate tools and
        configure them properly for your needs.
        """
        
        generic_score = QualityScoreCalculators.calculate_domain_relevance_score(generic_tech_content)
        assert generic_score < 0.3, f"Generic content should score low: {generic_score}"
        
        # Business requirement: Domain expertise should be clearly distinguished
        expertise_advantage = domain_score - generic_score
        assert expertise_advantage > 0.4, "Domain expertise should provide clear scoring advantage"
        
    @pytest.mark.unit
    def test_quality_calculator_pattern_detection_accuracy(self):
        """Test that quality calculators accurately detect various content patterns."""
        # Test generic phrase detection
        generic_phrases_text = "It is important to note that generally speaking, various factors contribute to better results."
        generic_count = QualityScoreCalculators._count_generic_phrases(generic_phrases_text.lower())
        assert generic_count >= 4, f"Should detect multiple generic phrases: {generic_count}"
        
        # Test circular reasoning detection
        circular_text = "To improve performance you should improve optimization by optimizing better algorithms."
        circular_count = QualityScoreCalculators._count_circular_patterns(circular_text.lower())
        assert circular_count >= 2, f"Should detect circular patterns: {circular_count}"
        
        # Test vague pattern detection
        vague_text = "Consider using better approaches. Think about optimizing. Look into various alternatives."
        vague_count = QualityScoreCalculators._count_vague_patterns(vague_text.lower())
        assert vague_count >= 3, f"Should detect vague patterns: {vague_count}"
        
        # Test action keyword detection
        action_text = "Install Redis, configure settings, deploy cluster, monitor performance, update configurations."
        action_count = QualityScoreCalculators._count_action_keywords(action_text.lower())
        assert action_count >= 5, f"Should detect action keywords: {action_count}"
        
    @pytest.mark.unit
    def test_quality_score_mathematical_consistency(self):
        """Test that quality score calculations maintain mathematical consistency."""
        test_content = """
        Configure Redis with max_connections=50 and timeout=5000ms.
        Set up connection pooling for 3x performance improvement.
        Enable monitoring with 30-second health checks.
        """
        
        # All scores should be between 0.0 and 1.0
        scores = {
            'specificity': QualityScoreCalculators.calculate_specificity_score(test_content),
            'actionability': QualityScoreCalculators.calculate_actionability_score(test_content),
            'quantification': QualityScoreCalculators.calculate_quantification_score(test_content),
            'novelty': QualityScoreCalculators.calculate_novelty_score(test_content),
            'completeness': QualityScoreCalculators.calculate_completeness_score(test_content, "recommendation"),
            'domain_relevance': QualityScoreCalculators.calculate_domain_relevance_score(test_content)
        }
        
        for score_name, score_value in scores.items():
            assert 0.0 <= score_value <= 1.0, \
                f"{score_name} score should be between 0.0 and 1.0: {score_value}"
            assert isinstance(score_value, float), \
                f"{score_name} score should be float: {type(score_value)}"
                
    @pytest.mark.unit
    def test_quality_score_edge_cases_robustness(self):
        """Test that quality score calculations handle edge cases robustly."""
        edge_cases = [
            "",  # Empty string
            " ",  # Whitespace only
            "a",  # Single character
            "Word",  # Single word
            "A" * 10000,  # Very long single character
        ]
        
        for edge_case in edge_cases:
            # Should not crash or return invalid scores
            specificity = QualityScoreCalculators.calculate_specificity_score(edge_case)
            actionability = QualityScoreCalculators.calculate_actionability_score(edge_case)
            quantification = QualityScoreCalculators.calculate_quantification_score(edge_case)
            novelty = QualityScoreCalculators.calculate_novelty_score(edge_case)
            completeness = QualityScoreCalculators.calculate_completeness_score(edge_case, "general")
            domain_relevance = QualityScoreCalculators.calculate_domain_relevance_score(edge_case)
            
            # All should return valid scores
            scores = [specificity, actionability, quantification, novelty, completeness, domain_relevance]
            for score in scores:
                assert 0.0 <= score <= 1.0, f"Edge case '{edge_case[:20]}...' produced invalid score: {score}"
                assert not (score != score), f"Edge case '{edge_case[:20]}...' produced NaN score"
                
    @pytest.mark.unit
    def test_quality_calculator_business_intelligence_patterns(self):
        """Test that quality calculators provide business intelligence for content assessment."""
        # Test content that should score well across all dimensions
        high_quality_content = """
        Step 1: Install Redis Cluster using `redis-server --cluster-enabled yes`
        Step 2: Configure cluster with 6 nodes (3 masters, 3 replicas)
        
        Expected performance improvement: 5x throughput to 2500 QPS
        Memory utilization: Reduced from 80% to 45%
        Latency improvement: From 200ms to 40ms average response time
        
        ```bash
        redis-cli --cluster create 127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 \
        127.0.0.1:7003 127.0.0.1:7004 127.0.0.1:7005 --cluster-replicas 1
        ```
        
        Configure cluster parameters:
        - cluster-node-timeout: 15000ms
        - cluster-migration-barrier: 1
        - cluster-require-full-coverage: yes
        """
        
        scores = {
            'specificity': QualityScoreCalculators.calculate_specificity_score(high_quality_content),
            'actionability': QualityScoreCalculators.calculate_actionability_score(high_quality_content),
            'quantification': QualityScoreCalculators.calculate_quantification_score(high_quality_content),
            'novelty': QualityScoreCalculators.calculate_novelty_score(high_quality_content),
            'completeness': QualityScoreCalculators.calculate_completeness_score(high_quality_content, "recommendation"),
            'domain_relevance': QualityScoreCalculators.calculate_domain_relevance_score(high_quality_content)
        }
        
        # High-quality content should score well across all dimensions
        for dimension, score in scores.items():
            assert score > 0.5, f"High-quality content should score well in {dimension}: {score}"
            
        # Overall quality should be high (average above 0.6)
        average_score = sum(scores.values()) / len(scores)
        assert average_score > 0.6, f"Overall quality should be high: {average_score}"
        
        # Record metrics for business intelligence
        self.record_metric("high_quality_content_average_score", average_score)
        self.record_metric("high_quality_content_dimensions", scores)
        
    @pytest.mark.unit
    def test_technical_terms_detection_business_value(self):
        """Test that technical term detection provides business value for expertise assessment."""
        # Technical content with CamelCase patterns
        technical_content = """
        Configure RedisConnectionPool with ConnectionMultiplexer for optimal performance.
        Use RedisDatabase for key-value operations and RedisSubscriber for pub/sub patterns.
        Implement DistributedCache with RedisCache for session management.
        Set up ConnectionPoolSettings with appropriate timeouts and retry policies.
        """
        
        tech_term_count = QualityScoreCalculators._count_technical_terms(technical_content)
        assert tech_term_count >= 6, f"Should detect multiple technical terms: {tech_term_count}"
        
        # Non-technical content
        simple_content = "Use redis for caching. It makes things faster and better."
        simple_term_count = QualityScoreCalculators._count_technical_terms(simple_content)
        assert simple_term_count <= 1, f"Should detect few technical terms in simple content: {simple_term_count}"
        
        # Business requirement: Technical expertise should be measurable
        expertise_difference = tech_term_count - simple_term_count
        assert expertise_difference >= 4, f"Technical expertise should be clearly distinguishable: {expertise_difference}"