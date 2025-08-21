import pandas as pd
from sklearn.cluster import KMeans
import json
from typing import List, Any, Tuple
from app.schemas import DiscoveredPattern
from app.config import settings
from app.services.apex_optimizer_agent.tools.base import BaseTool, ToolMetadata
from app.services.context import ToolContext

class LogPatternIdentifier(BaseTool):
    metadata = ToolMetadata(
        name="log_pattern_identifier",
        description="Identifies patterns in the enriched logs.",
        version="1.0.0",
        status="in_review"
    )
    llm_name = "analysis"

    def _validate_and_prepare_data(self, enriched_spans: List[dict], n_patterns: int) -> Tuple[pd.DataFrame, List[str], int]:
        """Validates input and prepares data for clustering."""
        if not enriched_spans:
            return None, [], 0
        df = pd.DataFrame(enriched_spans).dropna()
        features = ['prefill_ratio', 'generation_ratio', 'throughput_tokens_per_sec']
        n_patterns = min(len(df), n_patterns) if len(df) > 0 else 0
        return df, features, n_patterns

    def _perform_clustering(self, df: pd.DataFrame, features: List[str], n_patterns: int) -> pd.DataFrame:
        """Performs KMeans clustering on the data."""
        if n_patterns == 0:
            return df
        kmeans = KMeans(n_clusters=n_patterns, random_state=42, n_init='auto')
        df['pattern_id_num'] = kmeans.fit_predict(df[features])
        return df

    def _calculate_centroids(self, df: pd.DataFrame, features: List[str], n_patterns: int) -> List[dict]:
        """Calculates centroids for each cluster."""
        centroids = []
        for i in range(n_patterns):
            cluster_df = df[df['pattern_id_num'] == i]
            if not cluster_df.empty:
                centroids.append(cluster_df[features].mean().to_dict())
        return centroids

    async def _generate_descriptions(self, context: ToolContext, centroids: List[dict]) -> dict:
        """Generates pattern descriptions using LLM."""
        llm = context.llm_manager.get_llm(self.llm_name or "default")
        if not llm:
            return {}
        features_json = self._build_features_json(centroids)
        prompt = self._build_analysis_prompt(features_json)
        return await self._invoke_llm_and_parse_response(llm, prompt)

    def _build_features_json(self, centroids: List[dict]) -> str:
        """Build JSON representation of centroid features."""
        return json.dumps({f"pattern_{i}": features for i, features in enumerate(centroids)}, indent=2)

    async def _invoke_llm_and_parse_response(self, llm, prompt: str) -> dict:
        """Invoke LLM and parse JSON response."""
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        return json.loads(content) if content else {}

    def _build_analysis_prompt(self, features_json: str) -> str:
        """Builds the LLM analysis prompt."""
        return f"""
        Analyze the following LLM usage pattern features. For each pattern, generate a concise, 2-4 word name and a one-sentence description.
        **Pattern Features (JSON):**
{features_json}

        **Output Format (JSON ONLY):**
        Respond with a single JSON object where keys are the pattern identifiers (e.g., "pattern_0"). Each value should be an object containing "name" and "description".
        """

    def _create_pattern_objects(self, df: pd.DataFrame, centroids: List[dict], descriptions: dict) -> Tuple[List[DiscoveredPattern], List[str]]:
        """Creates pattern objects and descriptions."""
        patterns = []
        pattern_descriptions = []
        return self._build_pattern_lists(df, centroids, descriptions, patterns, pattern_descriptions)

    def _build_pattern_lists(self, df: pd.DataFrame, centroids: List[dict], descriptions: dict, 
                           patterns: List[DiscoveredPattern], pattern_descriptions: List[str]) -> Tuple[List[DiscoveredPattern], List[str]]:
        """Build lists of patterns and descriptions."""
        for i, centroid in enumerate(centroids):
            pattern = self._create_single_pattern(df, centroid, descriptions, i)
            patterns.append(pattern)
            pattern_descriptions.append(pattern.pattern_description)
        return patterns, pattern_descriptions

    def _create_single_pattern(self, df: pd.DataFrame, centroid: dict, descriptions: dict, index: int) -> DiscoveredPattern:
        """Creates a single pattern from centroid data."""
        cluster_df = df[df['pattern_id_num'] == index]
        desc_data = descriptions.get(f"pattern_{index}", {})
        return self._build_pattern(desc_data, centroid, cluster_df, index)

    def _build_pattern(self, desc_data: dict, centroid: dict, cluster_df: pd.DataFrame, index: int) -> DiscoveredPattern:
        """Builds a single DiscoveredPattern object."""
        name = desc_data.get('name', f'Pattern {index+1}') if desc_data else f'Pattern {index+1}'
        description = desc_data.get('description', 'A general usage pattern.') if desc_data else 'A general usage pattern.'
        return DiscoveredPattern(
            pattern_name=name, pattern_description=description,
            centroid_features=centroid, member_span_ids=cluster_df['span_id'].tolist(),
            member_count=len(cluster_df)
        )

    async def run(
        self, context: ToolContext, enriched_spans: List[dict], n_patterns: int = 5
    ) -> Tuple[List[DiscoveredPattern], List[str]]:
        """Identifies patterns in the enriched logs."""
        df, features, n_patterns = self._validate_and_prepare_data(enriched_spans, n_patterns)
        if df is None or n_patterns == 0:
            return [], []
        return await self._process_pattern_analysis(context, df, features, n_patterns)

    async def _process_pattern_analysis(self, context: ToolContext, df: pd.DataFrame, features: List[str], n_patterns: int) -> Tuple[List[DiscoveredPattern], List[str]]:
        """Processes clustering and pattern creation."""
        df = self._perform_clustering(df, features, n_patterns)
        centroids = self._calculate_centroids(df, features, n_patterns)
        if not centroids:
            return [], []
        descriptions = await self._generate_descriptions(context, centroids)
        return self._create_pattern_objects(df, centroids, descriptions)
