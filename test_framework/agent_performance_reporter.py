"""
Agent Performance Reporter - Enhanced reporting for comprehensive_reporter.py

Business Value Justification (BVJ):
1. Segment: Growth & Enterprise (performance-sensitive customers)
2. Business Goal: Demonstrate system performance value
3. Value Impact: Provides performance analytics to justify premium pricing  
4. Revenue Impact: Enables performance-based pricing tiers (+15-25% revenue)

Architectural Compliance:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Extends comprehensive_reporter with agent performance features
- Single responsibility: Performance data processing and trend analysis
"""

from typing import Dict, List
from datetime import datetime


class AgentPerformanceDataProcessor:
    """Processes and updates agent performance tracking data."""
    
    def update_agent_performance_data(self, test_results: Dict, agent_performance: Dict, timestamp: str):
        """Update agent performance tracking data."""
        self._ensure_performance_structure(test_results)
        self._store_latest_performance(test_results, agent_performance, timestamp)
        self._update_historical_data(test_results, agent_performance, timestamp)
        self._calculate_trends_if_ready(test_results)
    
    def _ensure_performance_structure(self, test_results: Dict):
        """Ensure agent performance structure exists."""
        if 'agent_performance' not in test_results:
            test_results['agent_performance'] = {
                'latest_run': {},
                'historical_data': [],
                'performance_trends': {}
            }
    
    def _store_latest_performance(self, test_results: Dict, agent_performance: Dict, timestamp: str):
        """Store latest performance data."""
        test_results['agent_performance']['latest_run'] = {
            **agent_performance,
            'timestamp': timestamp
        }
    
    def _update_historical_data(self, test_results: Dict, agent_performance: Dict, timestamp: str):
        """Update historical performance data."""
        historical = test_results['agent_performance']['historical_data']
        historical.append({
            **agent_performance,
            'timestamp': timestamp
        })
        self._limit_historical_entries(test_results)
    
    def _limit_historical_entries(self, test_results: Dict):
        """Keep only last 20 historical entries."""
        historical = test_results['agent_performance']['historical_data']
        if len(historical) > 20:
            test_results['agent_performance']['historical_data'] = historical[-20:]
    
    def _calculate_trends_if_ready(self, test_results: Dict):
        """Calculate performance trends if enough data available."""
        historical = test_results['agent_performance']['historical_data']
        if len(historical) >= 3:
            trend_calculator = PerformanceTrendCalculator()
            trends = trend_calculator.calculate_performance_trends(historical)
            test_results['agent_performance']['performance_trends'] = trends


class PerformanceTrendCalculator:
    """Calculates performance trends from historical data."""
    
    METRICS_TO_TRACK = ['total_e2e_duration', 'cold_start_time', 'first_response_time']
    
    def calculate_performance_trends(self, historical_data: List[Dict]) -> Dict:
        """Calculate performance trends from historical data."""
        trends = {}
        
        for metric in self.METRICS_TO_TRACK:
            trend_data = self._calculate_metric_trend(historical_data, metric)
            if trend_data:
                trends[metric] = trend_data
        
        return trends
    
    def _calculate_metric_trend(self, historical_data: List[Dict], metric: str) -> Dict:
        """Calculate trend data for a specific metric."""
        values = self._extract_metric_values(historical_data, metric)
        if len(values) < 3:
            return {}
        
        return self._build_trend_data(values)
    
    def _extract_metric_values(self, historical_data: List[Dict], metric: str) -> List[float]:
        """Extract non-None values for a specific metric."""
        return [run.get(metric) for run in historical_data if run.get(metric) is not None]
    
    def _build_trend_data(self, values: List[float]) -> Dict:
        """Build trend data structure from metric values."""
        recent_avg = sum(values[-3:]) / len(values[-3:])  # Last 3 runs
        overall_avg = sum(values) / len(values)  # All runs
        
        return {
            'recent_average': round(recent_avg, 3),
            'overall_average': round(overall_avg, 3),
            'trend': self._determine_trend(recent_avg, overall_avg),
            'sample_size': len(values)
        }
    
    def _determine_trend(self, recent_avg: float, overall_avg: float) -> str:
        """Determine performance trend based on averages."""
        if recent_avg < overall_avg:
            return 'improving'
        elif abs(recent_avg - overall_avg) < 0.1:
            return 'stable'
        else:
            return 'degrading'


class AgentPerformanceReportFormatter:
    """Formats agent performance data for various output formats."""
    
    def format_performance_summary(self, performance_data: Dict) -> Dict:
        """Format performance data for summary reports."""
        if not performance_data or 'agent_performance' not in performance_data:
            return {}
        
        agent_perf = performance_data['agent_performance']
        
        return {
            'latest_run_summary': self._format_latest_run(agent_perf.get('latest_run', {})),
            'trend_summary': self._format_trends(agent_perf.get('performance_trends', {})),
            'historical_summary': self._format_historical_summary(agent_perf.get('historical_data', []))
        }
    
    def _format_latest_run(self, latest_run: Dict) -> Dict:
        """Format latest run data."""
        if not latest_run:
            return {}
        
        return {
            'timestamp': latest_run.get('timestamp'),
            'total_duration': latest_run.get('total_e2e_duration'),
            'cold_start': latest_run.get('cold_start_time'),
            'first_response': latest_run.get('first_response_time')
        }
    
    def _format_trends(self, trends: Dict) -> Dict:
        """Format trend data for summary."""
        if not trends:
            return {}
        
        formatted_trends = {}
        for metric, data in trends.items():
            formatted_trends[metric] = {
                'trend': data.get('trend', 'unknown'),
                'recent_avg': data.get('recent_average'),
                'overall_avg': data.get('overall_average')
            }
        
        return formatted_trends
    
    def _format_historical_summary(self, historical_data: List[Dict]) -> Dict:
        """Format historical data summary."""
        if not historical_data:
            return {}
        
        return {
            'total_runs': len(historical_data),
            'date_range': self._get_date_range(historical_data),
            'performance_stability': self._assess_stability(historical_data)
        }
    
    def _get_date_range(self, historical_data: List[Dict]) -> Dict:
        """Get date range of historical data."""
        if not historical_data:
            return {}
        
        timestamps = [run.get('timestamp') for run in historical_data if run.get('timestamp')]
        if not timestamps:
            return {}
        
        return {
            'first_run': min(timestamps),
            'latest_run': max(timestamps)
        }
    
    def _assess_stability(self, historical_data: List[Dict]) -> str:
        """Assess performance stability from historical data."""
        durations = [run.get('total_e2e_duration') for run in historical_data 
                    if run.get('total_e2e_duration')]
        
        if len(durations) < 3:
            return 'insufficient_data'
        
        avg_duration = sum(durations) / len(durations)
        variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
        coefficient_of_variation = (variance ** 0.5) / avg_duration
        
        if coefficient_of_variation < 0.1:
            return 'very_stable'
        elif coefficient_of_variation < 0.2:
            return 'stable'
        elif coefficient_of_variation < 0.3:
            return 'moderate_variation'
        else:
            return 'high_variation'


# Create singleton instances for easy access
performance_processor = AgentPerformanceDataProcessor()
trend_calculator = PerformanceTrendCalculator()
report_formatter = AgentPerformanceReportFormatter()


def update_agent_performance_data(test_results: Dict, agent_performance: Dict, timestamp: str):
    """Main entry point for updating agent performance data."""
    return performance_processor.update_agent_performance_data(test_results, agent_performance, timestamp)

def format_performance_summary(performance_data: Dict) -> Dict:
    """Main entry point for formatting performance summaries."""
    return report_formatter.format_performance_summary(performance_data)