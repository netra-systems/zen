"""Corpus-specific operations for DataSubAgent."""

from typing import Any, Dict, List, Optional

from netra_backend.app.schemas.shared_types import (
    AnomalyDetectionResponse,
    DataAnalysisResponse,
    UsagePattern,
)


class CorpusOperations:
    """Handles corpus-specific operations for DataSubAgent."""
    
    def __init__(self, agent):
        self.agent = agent
    
    async def analyze_corpus_data(self, corpus_id: str) -> Optional[DataAnalysisResponse]:
        """Analyze data related to a specific corpus."""
        query = self.agent.query_builder.build_corpus_analysis_query(corpus_id)
        data = await self.agent._fetch_clickhouse_data(query, f"corpus:{corpus_id}")
        if data:
            return await self.agent.analysis_engine.analyze_corpus_insights(data, corpus_id)
        return None
    
    async def get_corpus_usage_patterns(self, corpus_id: str) -> List[UsagePattern]:
        """Retrieve usage patterns for a specific corpus."""
        query = self.agent.query_builder.build_usage_pattern_query(corpus_id)
        usage_data = await self.agent._fetch_clickhouse_data(query, f"usage:{corpus_id}")
        if usage_data:
            return await self.agent.analysis_engine.extract_usage_patterns(usage_data)
        return []
    
    async def detect_corpus_anomalies(self, corpus_id: str) -> Optional[AnomalyDetectionResponse]:
        """Detect anomalies in corpus usage and performance."""
        metrics_data = await self._fetch_corpus_metrics(corpus_id)
        if metrics_data:
            return await self.agent.analysis_engine.detect_corpus_anomalies(metrics_data)
        return None
    
    async def _fetch_corpus_metrics(self, corpus_id: str) -> Optional[Dict[str, Any]]:
        """Fetch corpus-specific metrics from ClickHouse."""
        query = self.agent.query_builder.build_corpus_metrics_query(corpus_id)
        cache_key = f"corpus_metrics:{corpus_id}"
        return await self.agent._fetch_clickhouse_data(query, cache_key)
    
    async def generate_corpus_insights(self, corpus_id: str) -> Dict[str, Any]:
        """Generate comprehensive insights for a corpus."""
        analysis = await self.analyze_corpus_data(corpus_id)
        patterns = await self.get_corpus_usage_patterns(corpus_id)
        anomalies = await self.detect_corpus_anomalies(corpus_id)
        
        return self._compile_corpus_insights(analysis, patterns, anomalies)
    
    def _compile_corpus_insights(self, analysis, patterns, anomalies) -> Dict[str, Any]:
        """Compile corpus insights from analysis components."""
        return {
            "analysis": analysis.model_dump() if analysis else None,
            "usage_patterns": [p.model_dump() for p in patterns] if patterns else [],
            "anomalies": anomalies.model_dump() if anomalies else None,
            "summary": self._generate_corpus_summary(analysis, patterns, anomalies)
        }
    
    def _generate_corpus_summary(self, analysis, patterns, anomalies) -> str:
        """Generate summary text for corpus insights."""
        components = self._collect_summary_components(analysis, patterns, anomalies)
        if not components:
            return "No significant insights found"
        return f"Found: {', '.join(components)}"
    
    def _collect_summary_components(self, analysis, patterns, anomalies) -> list:
        """Collect components for corpus summary."""
        components = []
        if analysis: components.append("performance analysis")
        if patterns: components.append(f"{len(patterns)} usage patterns")
        if anomalies and anomalies.anomalies_detected: components.append("anomalies detected")
        return components