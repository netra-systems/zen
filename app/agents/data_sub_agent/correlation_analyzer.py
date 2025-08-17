"""Correlation analysis module for DataSubAgent."""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from app.logging_config import central_logger as logger


class CorrelationAnalyzer:
    """Focused correlation analysis operations."""
    
    def __init__(self, query_builder: Any, clickhouse_ops: Any, redis_manager: Any) -> None:
        self.query_builder = query_builder
        self.clickhouse_ops = clickhouse_ops
        self.redis_manager = redis_manager
    
    async def analyze_correlations(
        self,
        user_id: int,
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Analyze correlations between multiple metrics."""
        if len(metrics) < 2:
            return {"error": "At least 2 metrics required for correlation analysis"}
        
        correlations = await self._calculate_pairwise_correlations(user_id, metrics, time_range)
        return self._build_correlation_response(time_range, metrics, correlations)
    
    async def _calculate_pairwise_correlations(self, user_id: int, metrics: List[str], 
                                             time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Calculate pairwise correlations between metrics."""
        start_time, end_time = time_range
        correlations = {}
        await self._process_metric_pairs(user_id, metrics, start_time, end_time, correlations)
        return correlations
    
    async def _process_metric_pairs(self, user_id: int, metrics: List[str], 
                                  start_time: datetime, end_time: datetime, correlations: Dict) -> None:
        """Process all metric pairs for correlation analysis."""
        for i in range(len(metrics)):
            await self._process_metric_pair_combinations(user_id, metrics, i, start_time, end_time, correlations)
    
    async def _process_metric_pair_combinations(self, user_id: int, metrics: List[str], i: int,
                                              start_time: datetime, end_time: datetime, correlations: Dict) -> None:
        """Process metric pair combinations for given index."""
        for j in range(i + 1, len(metrics)):
            correlation = await self._calculate_single_correlation(user_id, metrics[i], metrics[j], start_time, end_time)
            if correlation:
                pair_key = self._create_pair_key(metrics[i], metrics[j])
                correlations[pair_key] = correlation
    
    def _create_pair_key(self, metric1: str, metric2: str) -> str:
        """Create key for metric pair."""
        return f"{metric1}_vs_{metric2}"
    
    async def _calculate_single_correlation(self, user_id: int, metric1: str, metric2: str, 
                                          start_time: datetime, end_time: datetime) -> Optional[Dict]:
        """Calculate correlation between two metrics."""
        query = self._build_correlation_query(user_id, metric1, metric2, start_time, end_time)
        data = await self.clickhouse_ops.fetch_data(query, redis_manager=self.redis_manager)
        
        if self._has_sufficient_data(data):
            return self._format_correlation_data(data[0])
        return None
    
    def _build_correlation_query(self, user_id: int, metric1: str, metric2: str, 
                               start_time: datetime, end_time: datetime) -> str:
        """Build correlation analysis query."""
        return self.query_builder.build_correlation_analysis_query(
            user_id, metric1, metric2, start_time, end_time
        )
    
    def _has_sufficient_data(self, data: Optional[List[Dict]]) -> bool:
        """Check if correlation data has sufficient sample size."""
        return data and data[0]['sample_size'] > 10
    
    def _format_correlation_data(self, corr_data: Dict) -> Dict[str, Any]:
        """Format correlation data for response."""
        corr_coef = corr_data['correlation_coefficient']
        strength = self._interpret_correlation_strength(corr_coef)
        basic_info = self._create_correlation_basic_info(corr_coef, strength, corr_data)
        stats_info = self._create_correlation_stats_info(corr_data)
        return {**basic_info, **stats_info}
    
    def _create_correlation_basic_info(self, corr_coef: float, strength: str, corr_data: Dict) -> Dict[str, Any]:
        """Create basic correlation information."""
        return {
            "coefficient": corr_coef,
            "strength": strength,
            "direction": self._determine_direction(corr_coef),
            "sample_size": corr_data['sample_size']
        }
    
    def _determine_direction(self, corr_coef: float) -> str:
        """Determine correlation direction."""
        return "positive" if corr_coef > 0 else "negative"
    
    def _create_correlation_stats_info(self, corr_data: Dict) -> Dict[str, Any]:
        """Create correlation statistics information."""
        return {
            "metric1_stats": self._create_metric_stats(corr_data, 'metric1'),
            "metric2_stats": self._create_metric_stats(corr_data, 'metric2')
        }
    
    def _create_metric_stats(self, corr_data: Dict, metric_prefix: str) -> Dict[str, float]:
        """Create statistics for a single metric."""
        return {
            "mean": corr_data[f'{metric_prefix}_avg'],
            "std": corr_data[f'{metric_prefix}_std']
        }
    
    def _interpret_correlation_strength(self, corr_coef: float) -> str:
        """Interpret correlation coefficient strength."""
        abs_coef = abs(corr_coef)
        if abs_coef > 0.7:
            return "strong"
        elif abs_coef > 0.4:
            return "moderate"
        return "weak"
    
    def _build_correlation_response(self, time_range: Tuple[datetime, datetime], metrics: List[str], 
                                   correlations: Dict) -> Dict[str, Any]:
        """Build correlation analysis response."""
        start_time, end_time = time_range
        return {
            "time_range": self._create_time_range_info(start_time, end_time),
            "metrics_analyzed": metrics,
            "correlations": correlations,
            "strongest_correlation": self._find_strongest_correlation(correlations)
        }
    
    def _create_time_range_info(self, start_time: datetime, end_time: datetime) -> Dict[str, str]:
        """Create time range information."""
        return {
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        }
    
    def _find_strongest_correlation(self, correlations: Dict) -> Optional[Tuple]:
        """Find the strongest correlation in the data."""
        if not correlations:
            return None
        return max(correlations.items(), key=lambda x: abs(x[1]['coefficient']))