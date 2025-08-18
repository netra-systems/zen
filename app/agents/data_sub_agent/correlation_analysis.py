"""Correlation analysis operations."""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from app.logging_config import central_logger as logger


class CorrelationAnalysisOperations:
    """Handles correlation analysis with proper type safety."""
    
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
        return await self._execute_correlation_analysis(user_id, metrics, time_range)

    async def _execute_correlation_analysis(
        self,
        user_id: int,
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Execute correlation analysis workflow."""
        validation_error = self._validate_metrics_for_correlation(metrics)
        if validation_error:
            return validation_error
        correlations = await self._compute_all_correlations(user_id, metrics, time_range)
        return self._format_correlation_results(correlations, metrics, time_range)

    def _validate_metrics_for_correlation(self, metrics: List[str]) -> Optional[Dict[str, str]]:
        """Validate metrics list for correlation analysis."""
        if len(metrics) < 2:
            return {"error": "At least 2 metrics required for correlation analysis"}
        return None
    
    async def _compute_all_correlations(
        self, user_id: int, metrics: List[str], time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Compute correlations for all metric pairs."""
        return await self._iterate_metric_correlations(user_id, metrics, time_range)

    async def _iterate_metric_correlations(
        self,
        user_id: int,
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Iterate through metrics and compute correlations."""
        start_time, end_time = time_range
        correlations = {}
        return await self._compute_all_metric_pairs(metrics, user_id, start_time, end_time, correlations)

    async def _compute_all_metric_pairs(
        self,
        metrics: List[str],
        user_id: int,
        start_time: datetime,
        end_time: datetime,
        correlations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute correlations for all metric pairs."""
        for i in range(len(metrics)):
            correlations.update(
                await self._compute_metric_correlations(i, metrics, user_id, start_time, end_time)
            )
        return correlations
    
    async def _compute_metric_correlations(
        self, i: int, metrics: List[str], user_id: int, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Compute correlations for a specific metric against later metrics."""
        return await self._process_metric_pairs(i, metrics, user_id, start_time, end_time)

    async def _process_metric_pairs(
        self,
        i: int,
        metrics: List[str],
        user_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Process correlation pairs for a specific metric index."""
        return await self._calculate_index_correlations(i, metrics, user_id, start_time, end_time)

    async def _calculate_index_correlations(
        self,
        i: int,
        metrics: List[str],
        user_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate correlations for specific metric index."""
        correlations = {}
        for j in range(i + 1, len(metrics)):
            pair_correlation = await self._compute_single_pair_correlation(i, j, metrics, user_id, start_time, end_time)
            correlations.update(pair_correlation)
        return correlations

    async def _compute_single_pair_correlation(
        self,
        i: int,
        j: int,
        metrics: List[str],
        user_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Compute correlation for a single metric pair."""
        return await self._calculate_metric_pair_correlation(i, j, metrics, user_id, start_time, end_time)

    async def _calculate_metric_pair_correlation(
        self,
        i: int,
        j: int,
        metrics: List[str],
        user_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Calculate correlation for metric pair at indices i, j."""
        metric1, metric2 = metrics[i], metrics[j]
        correlation = await self._calculate_pairwise_correlation(user_id, metric1, metric2, start_time, end_time)
        return self._format_pair_correlation_result(metric1, metric2, correlation)

    def _format_pair_correlation_result(self, metric1: str, metric2: str, correlation: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Format correlation result for metric pair."""
        if correlation:
            return {f"{metric1}_vs_{metric2}": correlation}
        return {}

    async def _calculate_pairwise_correlation(
        self,
        user_id: int,
        metric1: str,
        metric2: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """Calculate correlation between two metrics."""
        return await self._execute_pairwise_calculation(user_id, metric1, metric2, start_time, end_time)

    async def _execute_pairwise_calculation(
        self,
        user_id: int,
        metric1: str,
        metric2: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """Execute pairwise correlation calculation."""
        data = await self._fetch_correlation_data(user_id, metric1, metric2, start_time, end_time)
        return self._process_correlation_data(data)

    async def _fetch_correlation_data(
        self,
        user_id: int,
        metric1: str,
        metric2: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch correlation data from database."""
        query = self._build_correlation_query(user_id, metric1, metric2, start_time, end_time)
        return await self._fetch_cached_data(query, None)

    def _build_correlation_query(
        self,
        user_id: int,
        metric1: str,
        metric2: str,
        start_time: datetime,
        end_time: datetime
    ) -> str:
        """Build correlation query using query builder."""
        return self.query_builder.build_correlation_analysis_query(
            user_id, metric1, metric2, start_time, end_time
        )

    def _process_correlation_data(self, data: Optional[List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
        """Process correlation data and format result."""
        if not data or data[0]['sample_size'] <= 10:
            return None
        corr_data = data[0]
        return self._extract_and_format_correlation(corr_data)

    def _extract_and_format_correlation(self, corr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract correlation coefficient and format result."""
        corr_coef = corr_data['correlation_coefficient']
        return self._format_correlation_result(corr_data, corr_coef)
    
    def _format_correlation_result(self, corr_data: Dict[str, Any], corr_coef: float) -> Dict[str, Any]:
        """Format correlation analysis result."""
        base_info = self._build_correlation_base_info(corr_coef, corr_data)
        stats_info = self._build_correlation_stats(corr_data)
        return self._merge_correlation_info(base_info, stats_info)

    def _merge_correlation_info(self, base_info: Dict[str, Any], stats_info: Dict[str, Any]) -> Dict[str, Any]:
        """Merge correlation base and stats info."""
        return {**base_info, **stats_info}
    
    def _build_correlation_base_info(self, corr_coef: float, corr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build base correlation information."""
        return self._create_correlation_base_dict(corr_coef, corr_data)

    def _create_correlation_base_dict(self, corr_coef: float, corr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create correlation base information dictionary."""
        return {
            "coefficient": corr_coef,
            "strength": self._interpret_correlation_strength(corr_coef),
            "direction": "positive" if corr_coef > 0 else "negative",
            "sample_size": corr_data['sample_size']
        }
    
    def _build_correlation_stats(self, corr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build correlation statistics."""
        metric1_stats = self._build_metric_stats(corr_data, 'metric1')
        metric2_stats = self._build_metric_stats(corr_data, 'metric2')
        return self._create_correlation_stats_dict(metric1_stats, metric2_stats)

    def _create_correlation_stats_dict(self, metric1_stats: Dict[str, Any], metric2_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Create correlation statistics dictionary."""
        return {"metric1_stats": metric1_stats, "metric2_stats": metric2_stats}
    
    def _build_metric_stats(self, corr_data: Dict[str, Any], metric_prefix: str) -> Dict[str, Any]:
        """Build stats for a single metric."""
        return self._create_metric_stats_dict(corr_data, metric_prefix)

    def _create_metric_stats_dict(self, corr_data: Dict[str, Any], metric_prefix: str) -> Dict[str, Any]:
        """Create metric statistics dictionary."""
        return {
            "mean": corr_data[f'{metric_prefix}_avg'],
            "std": corr_data[f'{metric_prefix}_std']
        }
    
    def _interpret_correlation_strength(self, coefficient: float) -> str:
        """Interpret correlation coefficient strength."""
        return self._classify_correlation_strength(abs(coefficient))

    def _classify_correlation_strength(self, abs_coefficient: float) -> str:
        """Classify correlation strength by absolute coefficient."""
        return self._get_strength_classification(abs_coefficient)

    def _get_strength_classification(self, abs_coefficient: float) -> str:
        """Get strength classification for coefficient."""
        if abs_coefficient > 0.7:
            return "strong"
        elif abs_coefficient > 0.4:
            return "moderate"
        return "weak"
    
    def _format_correlation_results(
        self,
        correlations: Dict[str, Any],
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Format final correlation analysis results."""
        return self._build_correlation_summary(correlations, metrics, time_range)

    def _build_correlation_summary(
        self,
        correlations: Dict[str, Any],
        metrics: List[str],
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Build correlation analysis summary."""
        time_info = self._build_time_range_info(time_range)
        strongest = self._find_strongest_correlation(correlations)
        return self._create_correlation_summary_dict(time_info, metrics, correlations, strongest)

    def _create_correlation_summary_dict(
        self,
        time_info: Dict[str, Any],
        metrics: List[str],
        correlations: Dict[str, Any],
        strongest: Optional[Tuple[str, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Create correlation summary dictionary."""
        return {
            **time_info,
            "metrics_analyzed": metrics,
            "correlations": correlations,
            "strongest_correlation": strongest
        }
    
    def _build_time_range_info(self, time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Build time range information."""
        return self._create_time_range_dict(time_range)

    def _create_time_range_dict(self, time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Create time range dictionary."""
        start_time, end_time = time_range
        return self._format_time_range_dict(start_time, end_time)

    def _format_time_range_dict(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Format time range into dictionary."""
        return {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
    
    def _find_strongest_correlation(self, correlations: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Find strongest correlation from results."""
        if not correlations:
            return None
        return self._get_max_correlation(correlations)

    def _get_max_correlation(self, correlations: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Get correlation with maximum coefficient."""
        return max(
            correlations.items(),
            key=lambda x: abs(x[1]['coefficient'])
        )

    async def _fetch_cached_data(self, query: str, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch data with caching support."""
        return await self.clickhouse_ops.fetch_data(query, cache_key, self.redis_manager)