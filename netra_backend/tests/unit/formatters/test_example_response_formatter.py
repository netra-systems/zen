"""Comprehensive Unit Tests for ExampleResponseFormatter

MISSION-CRITICAL TEST SUITE: Complete validation of ExampleResponseFormatter SSOT patterns and business logic.

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Golden Path Reliability & User Experience
- Value Impact: Response formatting = Core user experience = $500K+ ARR protection
- Strategic Impact: ExampleResponseFormatter directly impacts user perception of AI value delivery,
  ensuring business insights are properly formatted and actionable for customers

COVERAGE TARGET: 90%+ of ExampleResponseFormatter critical methods including:
- Response format strategy selection and execution (lines 77-120)
- Cost optimization formatting (lines 121-195)
- Latency optimization formatting (lines 197-268)
- Model selection analysis formatting (lines 270-344)
- Scaling analysis formatting (lines 346-416)
- Advanced multi-dimensional optimization (lines 418-493)
- Chart generation utilities (lines 570-667)
- Export data generation (lines 669-702)
- Error handling and fallback responses (lines 536-568)

CRITICAL: Uses REAL services approach with minimal mocks per CLAUDE.md standards.
Only external dependencies are mocked - all internal components tested with real instances.
"""
import json
import pytest
import unittest
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.formatters.example_response_formatter import ExampleResponseFormatter, ResponseFormat, FormattedMetric, FormattedRecommendation, FormattedResult, format_example_response, get_response_formatter, response_formatter

class TestExampleResponseFormatter(SSotBaseTestCase):
    """Comprehensive test suite for ExampleResponseFormatter class.

    Tests all major formatting strategies and utility methods with emphasis on
    business logic validation and error handling.
    """

    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.formatter = ExampleResponseFormatter()
        self.set_env_var('TESTING', 'true')
        self.record_metric('test_started', datetime.now().isoformat())

    def teardown_method(self, method=None):
        """Cleanup after each test method."""
        super().teardown_method(method)

    @contextmanager
    def subTest(self, **kwargs):
        """Custom subTest implementation for SSotBaseTestCase compatibility."""
        params = ', '.join((f'{k}={v}' for k, v in kwargs.items()))
        self.logger.debug(f'Running subtest with params: {params}')
        try:
            yield
        except Exception as e:
            error_msg = f'SubTest failed ({params}): {str(e)}'
            raise AssertionError(error_msg) from e

    def fail(self, msg):
        """Custom fail method for compatibility."""
        assert False, msg

class TestFormatterInitialization(TestExampleResponseFormatter):
    """Test formatter initialization and strategy registration."""

    def test_formatter_initialization_strategies(self):
        """Test that formatter initializes with all expected strategies."""
        expected_strategies = {'cost_optimization', 'latency_optimization', 'model_selection', 'scaling_analysis', 'advanced_multi_dimensional'}
        actual_strategies = set(self.formatter.format_strategies.keys())
        self.assertEqual(expected_strategies, actual_strategies)
        for strategy_name, strategy_func in self.formatter.format_strategies.items():
            self.assertTrue(callable(strategy_func))
            self.record_metric(f'strategy_{strategy_name}_callable', True)

    def test_global_formatter_instance(self):
        """Test global formatter instance is accessible."""
        global_formatter = get_response_formatter()
        self.assertIsInstance(global_formatter, ExampleResponseFormatter)
        self.assertIsInstance(response_formatter, ExampleResponseFormatter)
        test_result = {'optimization_type': 'cost_optimization'}
        formatted = format_example_response(test_result)
        self.assertIsInstance(formatted, FormattedResult)

class TestDataClasses(TestExampleResponseFormatter):
    """Test data class functionality and validation."""

    def test_formatted_metric_creation(self):
        """Test FormattedMetric data class creation and defaults."""
        metric = FormattedMetric(label='Test Metric', value='100')
        self.assertEqual(metric.label, 'Test Metric')
        self.assertEqual(metric.value, '100')
        self.assertIsNone(metric.improvement)
        self.assertIsNone(metric.unit)
        self.assertIsNone(metric.trend)
        self.assertIsNone(metric.color)
        full_metric = FormattedMetric(label='Cost Reduction', value='$5,000', improvement='30% reduction', unit='USD', trend='down', color='green')
        self.assertEqual(full_metric.improvement, '30% reduction')
        self.assertEqual(full_metric.trend, 'down')
        self.assertEqual(full_metric.color, 'green')

    def test_formatted_recommendation_creation(self):
        """Test FormattedRecommendation data class creation."""
        rec = FormattedRecommendation(title='Optimize Model Selection', description='Switch to GPT-4 Turbo for cost efficiency', priority='high', impact='30% cost reduction', effort='Medium', timeline='2 weeks')
        self.assertEqual(rec.title, 'Optimize Model Selection')
        self.assertEqual(rec.priority, 'high')
        self.assertEqual(rec.impact, '30% cost reduction')
        self.assertIsNone(rec.business_value)
        rec_with_value = FormattedRecommendation(title='Test', description='Test', priority='low', impact='Low', effort='Low', timeline='1 week', business_value='$1000 savings')
        self.assertEqual(rec_with_value.business_value, '$1000 savings')

    def test_formatted_result_creation(self):
        """Test FormattedResult data class creation."""
        metrics = [FormattedMetric(label='Test', value='100')]
        recommendations = [FormattedRecommendation(title='Test', description='Test', priority='high', impact='High', effort='Low', timeline='1 week')]
        result = FormattedResult(title='Test Analysis', summary='Test summary', metrics=metrics, recommendations=recommendations, implementation_steps=['Step 1', 'Step 2'], business_impact={'roi': 'high'})
        self.assertEqual(result.title, 'Test Analysis')
        self.assertEqual(result.summary, 'Test summary')
        self.assertEqual(len(result.metrics), 1)
        self.assertEqual(len(result.recommendations), 1)
        self.assertEqual(len(result.implementation_steps), 2)
        self.assertEqual(result.business_impact['roi'], 'high')
        self.assertIsNone(result.technical_details)
        self.assertIsNone(result.charts_data)
        self.assertIsNone(result.export_data)

class TestResponseFormatSelection(TestExampleResponseFormatter):
    """Test main format_response method and strategy selection."""

    def test_format_response_strategy_selection(self):
        """Test that correct strategy is selected based on optimization_type."""
        test_cases = [('cost_optimization', '_format_cost_optimization'), ('latency_optimization', '_format_latency_optimization'), ('model_selection', '_format_model_selection'), ('scaling_analysis', '_format_scaling_analysis'), ('advanced_multi_dimensional', '_format_advanced_optimization'), ('unknown_type', '_format_general_response')]
        for optimization_type, expected_method_name in test_cases:
            with self.subTest(optimization_type=optimization_type):
                result = {'optimization_type': optimization_type}
                mock_formatted_result = FormattedResult(title='Test', summary='Test', metrics=[], recommendations=[], implementation_steps=[], business_impact={})
                with patch.object(self.formatter, expected_method_name) as mock_method:
                    mock_method.return_value = mock_formatted_result
                    if optimization_type == 'unknown_type':
                        formatted = self.formatter.format_response(result)
                        mock_method.assert_called_once()
                    else:
                        original_strategy = self.formatter.format_strategies.get(optimization_type)
                        self.formatter.format_strategies[optimization_type] = mock_method
                        formatted = self.formatter.format_response(result)
                        mock_method.assert_called_once()
                        if original_strategy:
                            self.formatter.format_strategies[optimization_type] = original_strategy

    def test_format_response_with_different_response_formats(self):
        """Test formatting with different ResponseFormat values."""
        result = {'optimization_type': 'cost_optimization'}
        for response_format in ResponseFormat:
            with self.subTest(format=response_format):
                formatted = self.formatter.format_response(result, response_format)
                self.assertIsInstance(formatted, FormattedResult)
                self.assertIsNotNone(formatted.technical_details)
                self.assertEqual(formatted.technical_details['optimization_type'], 'cost_optimization')

    def test_format_response_with_different_user_tiers(self):
        """Test formatting with different user tier values."""
        result = {'optimization_type': 'latency_optimization'}
        user_tiers = ['free', 'early', 'mid', 'enterprise']
        for user_tier in user_tiers:
            with self.subTest(user_tier=user_tier):
                formatted = self.formatter.format_response(result, user_tier=user_tier)
                self.assertIsInstance(formatted, FormattedResult)
                self.assertIsNotNone(formatted.title)
                self.assertIsNotNone(formatted.summary)

    def test_format_response_technical_details_population(self):
        """Test that technical details are properly populated."""
        result = {'optimization_type': 'model_selection', 'processing_time_ms': 1500, 'message_id': 'msg-123'}
        formatted = self.formatter.format_response(result)
        self.assertIsNotNone(formatted.technical_details)
        tech_details = formatted.technical_details
        self.assertEqual(tech_details['processing_time_ms'], 1500)
        self.assertEqual(tech_details['message_id'], 'msg-123')
        self.assertEqual(tech_details['optimization_type'], 'model_selection')
        self.assertEqual(tech_details['formatter_version'], '1.0')

    def test_format_response_export_data_generation(self):
        """Test that export data is generated for all responses."""
        result = {'optimization_type': 'scaling_analysis'}
        formatted = self.formatter.format_response(result)
        self.assertIsNotNone(formatted.export_data)
        export_data = formatted.export_data
        self.assertIn('executive_summary', export_data)
        self.assertIn('metrics_summary', export_data)
        self.assertIn('recommendations', export_data)
        self.assertIn('export_metadata', export_data)
        metadata = export_data['export_metadata']
        self.assertIn('generated_at', metadata)
        self.assertIn('optimization_type', metadata)

class TestCostOptimizationFormatting(TestExampleResponseFormatter):
    """Test cost optimization specific formatting logic."""

    def test_cost_optimization_complete_data(self):
        """Test cost optimization formatting with complete data."""
        result = {'optimization_type': 'cost_optimization', 'analysis': {'current_spending': {'monthly_total': '$10,000'}, 'optimization_opportunities': [{'strategy': 'Model Right-sizing', 'description': 'Use smaller models for simple queries', 'potential_savings': '$2,000', 'implementation_effort': 'Medium'}, {'strategy': 'Batch Processing', 'description': 'Group similar requests together', 'potential_savings': '$1,500', 'implementation_effort': 'High'}]}, 'expected_outcomes': {'monthly_savings': '$3,500', 'savings_percentage': '35', 'payback_period': '2 months', 'quality_maintenance': '99.5%'}, 'implementation_roadmap': {'week_1': ['Analyze current usage patterns'], 'week_2': ['Implement model selection logic']}}
        formatted = self.formatter.format_response(result)
        self.assertIn('Cost Optimization', formatted.title)
        self.assertIn('$3,500', formatted.summary)
        self.assertIn('35%', formatted.summary)
        self.assertEqual(len(formatted.metrics), 4)
        metric_labels = [m.label for m in formatted.metrics]
        self.assertIn('Current Monthly Cost', metric_labels)
        self.assertIn('Potential Savings', metric_labels)
        self.assertIn('Payback Period', metric_labels)
        self.assertIn('Quality Maintenance', metric_labels)
        savings_metric = next((m for m in formatted.metrics if m.label == 'Potential Savings'))
        self.assertEqual(savings_metric.value, '$3,500')
        self.assertEqual(savings_metric.improvement, '35% reduction')
        self.assertEqual(savings_metric.trend, 'down')
        self.assertEqual(savings_metric.color, 'green')
        self.assertEqual(len(formatted.recommendations), 2)
        rec_titles = [r.title for r in formatted.recommendations]
        self.assertIn('Model Right-sizing', rec_titles)
        self.assertIn('Batch Processing', rec_titles)
        first_rec = formatted.recommendations[0]
        self.assertEqual(first_rec.priority, 'high')
        self.assertGreater(len(formatted.implementation_steps), 0)
        self.assertTrue(any(('Week 1' in step for step in formatted.implementation_steps)))
        business_impact = formatted.business_impact
        self.assertEqual(business_impact['monthly_savings'], '$3,500')
        self.assertIn('annual_impact', business_impact)
        self.assertEqual(business_impact['roi_category'], 'high_impact')

    def test_cost_optimization_minimal_data(self):
        """Test cost optimization formatting with minimal data."""
        result = {'optimization_type': 'cost_optimization', 'analysis': {}, 'expected_outcomes': {}}
        formatted = self.formatter.format_response(result)
        self.assertIsInstance(formatted, FormattedResult)
        self.assertIn('Cost Optimization', formatted.title)
        self.assertEqual(len(formatted.metrics), 4)
        for metric in formatted.metrics:
            self.assertIsNotNone(metric.label)
            self.assertIsNotNone(metric.value)

    def test_cost_optimization_charts_generation(self):
        """Test cost optimization chart data generation."""
        result = {'analysis': {'optimization_opportunities': [{'strategy': 'Model A', 'potential_savings': '$1,000/month'}, {'strategy': 'Model B', 'potential_savings': '$500/month'}], 'current_spending': {'monthly_total': '$5,000'}}, 'expected_outcomes': {'monthly_savings': '$1,500'}}
        charts = self.formatter._generate_cost_charts(result)
        self.assertIn('savings_breakdown', charts)
        self.assertIn('cost_timeline', charts)
        savings_chart = charts['savings_breakdown']
        self.assertEqual(savings_chart['type'], 'pie')
        self.assertIsInstance(savings_chart['data'], list)
        self.assertEqual(len(savings_chart['data']), 2)

class TestLatencyOptimizationFormatting(TestExampleResponseFormatter):
    """Test latency optimization specific formatting logic."""

    def test_latency_optimization_complete_data(self):
        """Test latency optimization formatting with complete data."""
        result = {'optimization_type': 'latency_optimization', 'current_performance': {'average_latency': '2500ms', 'p95_latency': '4000ms'}, 'optimization_strategies': [{'strategy': 'Response Streaming', 'description': 'Stream responses as they are generated', 'latency_improvement': '60% reduction'}, {'strategy': 'Edge Caching', 'description': 'Cache common responses at edge locations', 'latency_improvement': '40% reduction'}], 'projected_results': {'new_average_latency': '1000ms', 'new_p95_latency': '1800ms', 'improvement_factor': '2.5x faster', 'user_satisfaction_increase': '+25%'}}
        formatted = self.formatter.format_response(result)
        self.assertIn('Latency Optimization', formatted.title)
        self.assertIn('2.5x faster', formatted.summary)
        self.assertEqual(len(formatted.metrics), 4)
        metric_labels = [m.label for m in formatted.metrics]
        expected_labels = ['Current Average Latency', 'Optimized Latency', 'P95 Improvement', 'User Satisfaction']
        for label in expected_labels:
            self.assertIn(label, metric_labels)
        optimized_metric = next((m for m in formatted.metrics if m.label == 'Optimized Latency'))
        self.assertEqual(optimized_metric.value, '1000ms')
        self.assertEqual(optimized_metric.improvement, '2.5x faster')
        self.assertEqual(optimized_metric.trend, 'down')
        self.assertEqual(optimized_metric.color, 'green')
        self.assertGreaterEqual(len(formatted.recommendations), 2)
        rec_titles = [r.title for r in formatted.recommendations]
        self.assertIn('Response Streaming', rec_titles)
        self.assertIn('Edge Caching', rec_titles)
        first_rec = formatted.recommendations[0]
        self.assertEqual(first_rec.priority, 'high')
        business_impact = formatted.business_impact
        self.assertEqual(business_impact['latency_improvement'], '2.5x faster')
        self.assertEqual(business_impact['user_experience'], 'Significantly improved')
        self.assertEqual(business_impact['competitive_advantage'], 'High')

    def test_latency_optimization_charts_generation(self):
        """Test latency optimization chart data generation."""
        result = {'current_performance': {'average_latency': '2000ms', 'p95_latency': '3500ms'}, 'projected_results': {'new_average_latency': '800ms', 'new_p95_latency': '1200ms'}}
        charts = self.formatter._generate_latency_charts(result)
        self.assertIn('latency_comparison', charts)
        comparison_chart = charts['latency_comparison']
        self.assertEqual(comparison_chart['type'], 'bar')
        self.assertIn('data', comparison_chart)
        chart_data = comparison_chart['data']
        self.assertIn('current_avg', chart_data)
        self.assertIn('optimized_avg', chart_data)
        self.assertEqual(chart_data['current_avg'], '2000')
        self.assertEqual(chart_data['optimized_avg'], '800')

class TestModelSelectionFormatting(TestExampleResponseFormatter):
    """Test model selection analysis formatting logic."""

    def test_model_selection_complete_data(self):
        """Test model selection formatting with complete data."""
        result = {'optimization_type': 'model_selection', 'model_comparison': {'gpt4': {'overall_score': 95, 'best_use_cases': ['complex analysis', 'creative tasks'], 'performance_metrics': {'speed': '1200ms', 'accuracy': '96%', 'consistency': '94%'}}, 'gpt3.5': {'overall_score': 85, 'best_use_cases': ['simple queries', 'data extraction'], 'performance_metrics': {'speed': '400ms', 'accuracy': '90%', 'consistency': '88%'}}}, 'recommendations': {'expected_impact': {'cost_reduction': '30%', 'quality_improvement': '15%'}}}
        formatted = self.formatter.format_response(result)
        self.assertIn('Model Selection', formatted.title)
        self.assertIn('30%', formatted.summary)
        self.assertIn('15%', formatted.summary)
        self.assertGreaterEqual(len(formatted.metrics), 4)
        metric_labels = [m.label for m in formatted.metrics]
        self.assertIn('GPT4 Score', metric_labels)
        self.assertIn('GPT4 Speed', metric_labels)
        self.assertIn('GPT3.5 Score', metric_labels)
        self.assertIn('GPT3.5 Speed', metric_labels)
        self.assertIn('Cost Reduction', metric_labels)
        self.assertIn('Quality Improvement', metric_labels)
        self.assertEqual(len(formatted.recommendations), 2)
        rec_titles = [r.title for r in formatted.recommendations]
        self.assertIn('Use GPT4', rec_titles)
        self.assertIn('Use GPT3.5', rec_titles)
        gpt4_rec = next((r for r in formatted.recommendations if 'GPT4' in r.title))
        self.assertEqual(gpt4_rec.priority, 'high')
        business_impact = formatted.business_impact
        self.assertEqual(business_impact['cost_optimization'], '30%')
        self.assertEqual(business_impact['quality_enhancement'], '15%')

    def test_model_selection_charts_generation(self):
        """Test model selection chart data generation."""
        result = {'model_comparison': {'model_a': {'overall_score': 90, 'performance_metrics': {'accuracy': '95%', 'consistency': '92%', 'speed': '800ms'}}, 'model_b': {'overall_score': 85, 'performance_metrics': {'accuracy': '88%', 'consistency': '90%', 'speed': '600ms'}}}}
        charts = self.formatter._generate_model_charts(result)
        self.assertIn('model_scores', charts)
        scores_chart = charts['model_scores']
        self.assertEqual(scores_chart['type'], 'radar')
        self.assertIn('data', scores_chart)
        chart_data = scores_chart['data']
        self.assertIn('model_a', chart_data)
        self.assertIn('model_b', chart_data)
        model_a_data = chart_data['model_a']
        self.assertEqual(model_a_data['overall'], 90)
        self.assertEqual(model_a_data['accuracy'], '95')
        self.assertEqual(model_a_data['consistency'], '92')

class TestScalingAnalysisFormatting(TestExampleResponseFormatter):
    """Test scaling analysis specific formatting logic."""

    def test_scaling_analysis_complete_data(self):
        """Test scaling analysis formatting with complete data."""
        result = {'optimization_type': 'scaling_analysis', 'current_metrics': {'monthly_requests': '100,000', 'monthly_cost': '$5,000'}, 'scaling_projections': {'with_50_percent_growth': {'monthly_requests': '150,000', 'projected_cost_linear': '$7,500', 'projected_cost_optimized': '$6,200'}}, 'optimization_strategies': [{'strategy': 'Request Batching', 'description': 'Group similar requests to reduce overhead', 'cost_savings': '$800/month', 'complexity': 'Medium'}, {'strategy': 'Intelligent Load Balancing', 'description': 'Distribute requests based on complexity', 'performance_improvement': '25% faster', 'complexity': 'High'}], 'projected_outcomes': {'cost_efficiency': '18% improvement', 'performance_maintained': '99.9% uptime'}}
        formatted = self.formatter.format_response(result)
        self.assertIn('Scaling Analysis', formatted.title)
        self.assertIn('150,000', formatted.summary)
        self.assertEqual(len(formatted.metrics), 4)
        metric_labels = [m.label for m in formatted.metrics]
        expected_labels = ['Current Monthly Requests', 'Projected Requests', 'Optimized Cost', 'Performance Maintained']
        for label in expected_labels:
            self.assertIn(label, metric_labels)
        projected_metric = next((m for m in formatted.metrics if m.label == 'Projected Requests'))
        self.assertEqual(projected_metric.value, '150,000')
        self.assertEqual(projected_metric.improvement, '+50% growth')
        self.assertEqual(projected_metric.trend, 'up')
        cost_metric = next((m for m in formatted.metrics if m.label == 'Optimized Cost'))
        self.assertEqual(cost_metric.value, '$6,200')
        self.assertEqual(cost_metric.trend, 'down')
        self.assertEqual(len(formatted.recommendations), 2)
        rec_titles = [r.title for r in formatted.recommendations]
        self.assertIn('Request Batching', rec_titles)
        self.assertIn('Intelligent Load Balancing', rec_titles)
        business_impact = formatted.business_impact
        self.assertEqual(business_impact['cost_efficiency'], '18% improvement')
        self.assertEqual(business_impact['performance_reliability'], '99.9% uptime')
        self.assertEqual(business_impact['growth_readiness'], 'Excellent')

    def test_scaling_analysis_charts_generation(self):
        """Test scaling analysis chart data generation."""
        result = {'current_metrics': {'monthly_requests': '50,000', 'monthly_cost': '$2,500'}, 'scaling_projections': {'with_50_percent_growth': {'monthly_requests': '75,000', 'projected_cost_optimized': '$3,200'}}}
        charts = self.formatter._generate_scaling_charts(result)
        self.assertIn('scaling_projection', charts)
        projection_chart = charts['scaling_projection']
        self.assertEqual(projection_chart['type'], 'line')
        self.assertIn('data', projection_chart)
        chart_data = projection_chart['data']
        self.assertEqual(chart_data['current_requests'], '50000')
        self.assertEqual(chart_data['projected_requests'], '75000')
        self.assertEqual(chart_data['optimized_cost'], '3200')

class TestAdvancedOptimizationFormatting(TestExampleResponseFormatter):
    """Test advanced multi-dimensional optimization formatting logic."""

    def test_advanced_optimization_complete_data(self):
        """Test advanced optimization formatting with complete data."""
        result = {'optimization_type': 'advanced_multi_dimensional', 'constraints_analysis': {'cost_reduction_target': '25%', 'latency_improvement_target': '2x', 'scaling_target': '200% usage increase'}, 'optimization_solution': {'achieved_cost_reduction': '28%', 'achieved_latency_improvement': '2.3x', 'achieved_scaling_capacity': '250% growth support'}, 'solution_components': [{'component': 'Hybrid Model Routing', 'impact': {'cost': '15% reduction'}}, {'component': 'Predictive Caching', 'impact': {'cost': '8% reduction'}}], 'business_impact': {'monthly_savings': '$8,500', 'productivity_increase': '40%', 'user_satisfaction_score': '92%', 'competitive_advantage': 'Significant'}, 'implementation_timeline': {'phase_1': {'tasks': ['Setup monitoring', 'Baseline metrics'], 'expected_improvement': '5% cost reduction'}, 'phase_2': {'tasks': ['Deploy hybrid routing'], 'expected_improvement': '15% cost reduction'}}}
        formatted = self.formatter.format_response(result)
        self.assertIn('Advanced Multi-Dimensional', formatted.title)
        self.assertIn('28%', formatted.summary)
        self.assertIn('2.3x', formatted.summary)
        self.assertIn('250%', formatted.summary)
        self.assertEqual(len(formatted.metrics), 4)
        metric_labels = [m.label for m in formatted.metrics]
        expected_labels = ['Cost Reduction Achieved', 'Latency Improvement', 'Scaling Capacity', 'Monthly Savings']
        for label in expected_labels:
            self.assertIn(label, metric_labels)
        cost_metric = next((m for m in formatted.metrics if m.label == 'Cost Reduction Achieved'))
        self.assertEqual(cost_metric.value, '28%')
        self.assertEqual(cost_metric.improvement, 'Target: 25%')
        self.assertEqual(cost_metric.trend, 'down')
        self.assertEqual(len(formatted.recommendations), 2)
        rec_titles = [r.title for r in formatted.recommendations]
        self.assertIn('Hybrid Model Routing', rec_titles)
        self.assertIn('Predictive Caching', rec_titles)
        self.assertGreater(len(formatted.implementation_steps), 0)
        steps_text = ' '.join(formatted.implementation_steps)
        self.assertIn('Phase 1', steps_text)
        self.assertIn('Setup monitoring', steps_text)
        business_impact = formatted.business_impact
        self.assertEqual(business_impact['cost_savings'], '$8,500')
        self.assertEqual(business_impact['productivity_gain'], '40%')
        self.assertEqual(business_impact['user_satisfaction'], '92%')

    def test_advanced_optimization_charts_generation(self):
        """Test advanced optimization chart data generation."""
        result = {'constraints_analysis': {'cost_reduction_target': '20%', 'latency_improvement_target': '2x', 'scaling_target': '150% usage increase'}, 'optimization_solution': {'achieved_cost_reduction': '22%', 'achieved_latency_improvement': '2.1x', 'achieved_scaling_capacity': '160% growth support'}}
        charts = self.formatter._generate_advanced_charts(result)
        self.assertIn('optimization_results', charts)
        results_chart = charts['optimization_results']
        self.assertEqual(results_chart['type'], 'gauge')
        self.assertIn('data', results_chart)
        chart_data = results_chart['data']
        self.assertEqual(chart_data['cost_target'], '20')
        self.assertEqual(chart_data['cost_achieved'], '22')
        self.assertEqual(chart_data['latency_target'], '2')
        self.assertEqual(chart_data['latency_achieved'], '2.1')

class TestGeneralAndErrorFormatting(TestExampleResponseFormatter):
    """Test general response and error handling formatting."""

    def test_general_response_formatting(self):
        """Test general/fallback response formatting."""
        result = {'optimization_type': 'unknown'}
        formatted = self.formatter.format_response(result)
        self.assertIn('Optimization Analysis', formatted.title)
        self.assertIn('Analysis completed', formatted.summary)
        self.assertGreater(len(formatted.metrics), 0)
        analysis_metric = formatted.metrics[0]
        self.assertEqual(analysis_metric.label, 'Analysis Completed')
        self.assertEqual(analysis_metric.color, 'green')
        self.assertGreater(len(formatted.recommendations), 0)
        first_rec = formatted.recommendations[0]
        self.assertEqual(first_rec.title, 'Explore Full Platform')
        self.assertEqual(first_rec.priority, 'high')
        self.assertGreater(len(formatted.implementation_steps), 0)
        self.assertIn('Sign up', formatted.implementation_steps[0])
        business_impact = formatted.business_impact
        self.assertEqual(business_impact['demonstration'], 'Successful')

    def test_error_response_formatting(self):
        """Test error response formatting."""
        error_message = 'Test error occurred'
        formatted = self.formatter._format_error_response(error_message)
        self.assertIn('Analysis Error', formatted.title)
        self.assertIn('Test error occurred', formatted.summary)
        self.assertEqual(len(formatted.metrics), 1)
        status_metric = formatted.metrics[0]
        self.assertEqual(status_metric.label, 'Status')
        self.assertEqual(status_metric.value, 'Error')
        self.assertEqual(status_metric.color, 'red')
        self.assertEqual(len(formatted.recommendations), 1)
        retry_rec = formatted.recommendations[0]
        self.assertEqual(retry_rec.title, 'Retry Analysis')
        self.assertEqual(retry_rec.priority, 'high')
        self.assertGreater(len(formatted.implementation_steps), 0)
        self.assertIn('different example', formatted.implementation_steps[0])
        business_impact = formatted.business_impact
        self.assertEqual(business_impact['status'], 'error')
        self.assertEqual(business_impact['resolution'], 'retry_recommended')

    def test_format_response_exception_handling(self):
        """Test that format_response handles exceptions and returns error response."""
        result = {'optimization_type': 'cost_optimization'}

        def raise_exception(*args, **kwargs):
            raise Exception('Mock exception')
        original_strategy = self.formatter.format_strategies['cost_optimization']
        self.formatter.format_strategies['cost_optimization'] = raise_exception
        try:
            formatted = self.formatter.format_response(result)
            self.assertIn('Analysis Error', formatted.title)
            self.assertIn('Mock exception', formatted.summary)
        finally:
            self.formatter.format_strategies['cost_optimization'] = original_strategy

class TestExportDataGeneration(TestExampleResponseFormatter):
    """Test export data generation functionality."""

    def test_export_data_generation_complete(self):
        """Test export data generation with complete formatted result."""
        result = {'optimization_type': 'cost_optimization', 'processing_time_ms': 2000}
        formatted_result = FormattedResult(title='Test Cost Analysis', summary='Found 3 optimization opportunities with $2000 monthly savings', metrics=[FormattedMetric(label='Monthly Savings', value='$2000', improvement='20% reduction', trend='down')], recommendations=[FormattedRecommendation(title='Optimize Models', description='Switch to smaller models', priority='high', impact='$1000 savings', effort='Medium', timeline='2 weeks', business_value='Significant cost reduction')], implementation_steps=['Analyze current usage', 'Implement model switching', 'Monitor performance'], business_impact={'monthly_savings': '$2000', 'roi_category': 'high'})
        export_data = self.formatter._generate_export_data(result, formatted_result)
        self.assertIn('executive_summary', export_data)
        exec_summary = export_data['executive_summary']
        self.assertEqual(exec_summary['title'], 'Test Cost Analysis')
        self.assertEqual(exec_summary['key_findings'], formatted_result.summary)
        self.assertEqual(exec_summary['business_impact'], formatted_result.business_impact)
        self.assertEqual(len(exec_summary['next_steps']), 3)
        self.assertIn('metrics_summary', export_data)
        metrics_summary = export_data['metrics_summary']
        self.assertEqual(len(metrics_summary), 1)
        metric_export = metrics_summary[0]
        self.assertEqual(metric_export['metric'], 'Monthly Savings')
        self.assertEqual(metric_export['value'], '$2000')
        self.assertEqual(metric_export['improvement'], '20% reduction')
        self.assertEqual(metric_export['trend'], 'down')
        self.assertIn('recommendations', export_data)
        rec_export = export_data['recommendations']
        self.assertEqual(len(rec_export), 1)
        rec_data = rec_export[0]
        self.assertEqual(rec_data['title'], 'Optimize Models')
        self.assertEqual(rec_data['priority'], 'high')
        self.assertEqual(rec_data['impact'], '$1000 savings')
        self.assertEqual(rec_data['business_value'], 'Significant cost reduction')
        self.assertIn('export_metadata', export_data)
        metadata = export_data['export_metadata']
        self.assertIn('generated_at', metadata)
        self.assertEqual(metadata['optimization_type'], 'cost_optimization')
        self.assertEqual(metadata['processing_time'], 2000)
        generated_at = metadata['generated_at']
        self.assertIsInstance(generated_at, str)
        parsed_time = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
        self.assertIsInstance(parsed_time, datetime)

class TestPublicInterface(TestExampleResponseFormatter):
    """Test public interface functions and global instances."""

    def test_public_format_function(self):
        """Test the public format_example_response function."""
        result = {'optimization_type': 'model_selection'}
        formatted = format_example_response(result)
        self.assertIsInstance(formatted, FormattedResult)
        formatted_custom = format_example_response(result, ResponseFormat.TECHNICAL, 'enterprise')
        self.assertIsInstance(formatted_custom, FormattedResult)
        self.assertIsNotNone(formatted.technical_details)
        self.assertIsNotNone(formatted_custom.technical_details)

    def test_get_response_formatter_function(self):
        """Test the get_response_formatter function."""
        formatter_instance = get_response_formatter()
        self.assertIsInstance(formatter_instance, ExampleResponseFormatter)
        self.assertIsInstance(response_formatter, ExampleResponseFormatter)
        result = {'optimization_type': 'latency_optimization'}
        formatted = formatter_instance.format_response(result)
        self.assertIsInstance(formatted, FormattedResult)

    def test_response_format_enum_values(self):
        """Test that all ResponseFormat enum values work."""
        result = {'optimization_type': 'scaling_analysis'}
        for format_type in ResponseFormat:
            with self.subTest(format=format_type):
                formatted = format_example_response(result, format_type)
                self.assertIsInstance(formatted, FormattedResult)
                self.assertIsNotNone(formatted.title)
                self.assertIsNotNone(formatted.summary)

class TestEdgeCasesAndErrorHandling(TestExampleResponseFormatter):
    """Test edge cases, error conditions, and robustness."""

    def test_empty_result_handling(self):
        """Test handling of empty result dictionary."""
        result = {}
        formatted = self.formatter.format_response(result)
        self.assertIsInstance(formatted, FormattedResult)
        self.assertIsNotNone(formatted.title)
        self.assertIsNotNone(formatted.summary)

    def test_none_values_handling(self):
        """Test handling of None values in result data."""
        result = {'optimization_type': 'cost_optimization', 'analysis': None, 'expected_outcomes': None}
        formatted = self.formatter.format_response(result)
        self.assertIsInstance(formatted, FormattedResult)
        self.assertGreater(len(formatted.metrics), 0)

    def test_malformed_data_handling(self):
        """Test handling of malformed data structures."""
        result = {'optimization_type': 'latency_optimization', 'current_performance': 'not_a_dict', 'optimization_strategies': 'not_a_list'}
        formatted = self.formatter.format_response(result)
        self.assertIsInstance(formatted, FormattedResult)

    def test_large_data_handling(self):
        """Test handling of large datasets."""
        large_opportunities = []
        for i in range(100):
            large_opportunities.append({'strategy': f'Strategy {i}', 'description': f'Description {i}', 'potential_savings': f'${i * 100}'})
        result = {'optimization_type': 'cost_optimization', 'analysis': {'optimization_opportunities': large_opportunities}}
        formatted = self.formatter.format_response(result)
        self.assertIsInstance(formatted, FormattedResult)
        self.assertLessEqual(len(formatted.recommendations), 10)

    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        result = {'optimization_type': 'model_selection', 'model_comparison': {'gpt-4-turbo-π': {'overall_score': 95, 'best_use_cases': ['Analysis with émojis 🚀', 'Special chars & symbols']}}}
        formatted = self.formatter.format_response(result)
        self.assertIsInstance(formatted, FormattedResult)
        rec_titles = [r.title for r in formatted.recommendations]
        self.assertTrue(any(('Π' in title for title in rec_titles)), f'Expected Π in recommendation titles, got: {rec_titles}')

    def test_numeric_string_parsing_edge_cases(self):
        """Test edge cases in numeric string parsing for charts."""
        result = {'analysis': {'optimization_opportunities': [{'strategy': 'Test', 'potential_savings': 'invalid_number'}, {'strategy': 'Test2', 'potential_savings': ''}, {'strategy': 'Test3', 'potential_savings': '$1,000.50/month'}]}}
        charts = self.formatter._generate_cost_charts(result)
        self.assertIn('savings_breakdown', charts)
        chart_data = charts['savings_breakdown']['data']
        self.assertEqual(len(chart_data), 3)

    def test_memory_efficiency_large_export(self):
        """Test memory efficiency with large export data."""
        large_metrics = []
        for i in range(1000):
            large_metrics.append(FormattedMetric(label=f'Metric {i}', value=f'Value {i}', improvement=f'Improvement {i}'))
        large_result = FormattedResult(title='Large Test', summary='Large test data', metrics=large_metrics, recommendations=[], implementation_steps=[], business_impact={})
        export_data = self.formatter._generate_export_data({}, large_result)
        self.assertIn('metrics_summary', export_data)
        self.assertEqual(len(export_data['metrics_summary']), 1000)
        self.record_metric('large_export_test_completed', True)

class TestBusinessLogicValidation(TestExampleResponseFormatter):
    """Test business logic validation and Golden Path compliance."""

    def test_golden_path_user_tier_handling(self):
        """Test that different user tiers receive appropriate content."""
        result = {'optimization_type': 'cost_optimization', 'analysis': {'optimization_opportunities': [{'strategy': 'Test Strategy', 'description': 'Test Description'}]}}
        user_tiers = ['free', 'early', 'mid', 'enterprise']
        for tier in user_tiers:
            with self.subTest(tier=tier):
                formatted = self.formatter.format_response(result, user_tier=tier)
                self.assertIsInstance(formatted, FormattedResult)
                self.assertGreater(len(formatted.recommendations), 0)
                self.assertGreater(len(formatted.implementation_steps), 0)

    def test_business_value_calculation_accuracy(self):
        """Test accuracy of business value calculations."""
        result = {'optimization_type': 'cost_optimization', 'expected_outcomes': {'monthly_savings': '$3,500', 'savings_percentage': '35'}}
        formatted = self.formatter.format_response(result)
        business_impact = formatted.business_impact
        annual_impact = business_impact.get('annual_impact', '')
        self.assertIn('$42,000', annual_impact)

    def test_recommendation_priority_logic(self):
        """Test that recommendation priorities are assigned logically."""
        result = {'optimization_type': 'cost_optimization', 'analysis': {'optimization_opportunities': [{'strategy': 'High Impact', 'potential_savings': '$5000'}, {'strategy': 'Medium Impact', 'potential_savings': '$2000'}, {'strategy': 'Low Impact', 'potential_savings': '$500'}]}}
        formatted = self.formatter.format_response(result)
        self.assertEqual(formatted.recommendations[0].priority, 'high')
        if len(formatted.recommendations) > 1:
            self.assertEqual(formatted.recommendations[1].priority, 'medium')
        if len(formatted.recommendations) > 2:
            self.assertEqual(formatted.recommendations[2].priority, 'low')

    def test_metrics_color_coding_logic(self):
        """Test that metrics are color-coded appropriately."""
        result = {'optimization_type': 'latency_optimization', 'projected_results': {'improvement_factor': '2x faster'}}
        formatted = self.formatter.format_response(result)
        improvement_metrics = [m for m in formatted.metrics if 'improvement' in m.label.lower() or 'latency' in m.label.lower()]
        for metric in improvement_metrics:
            if metric.trend == 'down':
                self.assertEqual(metric.color, 'green')

    def test_implementation_steps_completeness(self):
        """Test that implementation steps are comprehensive and actionable."""
        optimization_types = ['cost_optimization', 'latency_optimization', 'model_selection', 'scaling_analysis', 'advanced_multi_dimensional']
        for opt_type in optimization_types:
            with self.subTest(optimization_type=opt_type):
                result = {'optimization_type': opt_type}
                formatted = self.formatter.format_response(result)
                self.assertGreater(len(formatted.implementation_steps), 0)
                action_verbs = ['implement', 'deploy', 'set', 'configure', 'analyze', 'monitor']
                steps_text = ' '.join(formatted.implementation_steps).lower()
                has_action = any((verb in steps_text for verb in action_verbs))
                self.assertTrue(has_action, f'Implementation steps for {opt_type} lack actionable verbs')

    def test_error_recovery_business_continuity(self):
        """Test that errors don't break business continuity."""
        error_conditions = [{'optimization_type': None}, {'optimization_type': 123}, {'optimization_type': ''}, 'not_a_dict']
        for condition in error_conditions:
            with self.subTest(condition=str(condition)):
                try:
                    if isinstance(condition, dict):
                        formatted = self.formatter.format_response(condition)
                    else:
                        formatted = self.formatter.format_response(condition)
                    self.assertIsInstance(formatted, FormattedResult)
                    self.assertIsNotNone(formatted.title)
                    self.assertIsNotNone(formatted.summary)
                except Exception as e:
                    self.fail(f'Unhandled exception for condition {condition}: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')