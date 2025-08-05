
import pandas as pd
from sklearn.cluster import KMeans
import json
from typing import List, Any
from app.schema import DiscoveredPattern
from app.config import settings

class LogPatternIdentifier:
    def __init__(self, llm_connector: Any):
        self.llm_connector = llm_connector

    async def identify_patterns(
        self, enriched_spans: List[dict], n_patterns: int = 5
    ) -> (List[DiscoveredPattern], List[str]):
        """Identifies patterns in the enriched logs."""
        if not enriched_spans:
            return [], []

        df = pd.DataFrame(enriched_spans).dropna()
        features = ['prefill_ratio', 'generation_ratio', 'throughput_tokens_per_sec']
        if len(df) < n_patterns:
            n_patterns = len(df)
        if n_patterns == 0:
            return [], []

        kmeans = KMeans(n_clusters=n_patterns, random_state=42, n_init='auto')
        df['pattern_id_num'] = kmeans.fit_predict(df[features])
        
        centroids = [df[df['pattern_id_num'] == i][features].mean().to_dict() for i in range(n_patterns) if not df[df['pattern_id_num'] == i].empty]
        
        if not centroids:
            return [], []

        # Generate descriptions
        descriptions = {}
        if self.llm_connector:
            features_json = json.dumps({f"pattern_{i}": features for i, features in enumerate(centroids)}, indent=2)
            prompt = f"""
            Analyze the following LLM usage pattern features. For each pattern, generate a concise, 2-4 word name and a one-sentence description.
            **Pattern Features (JSON):**
{features_json}

            **Output Format (JSON ONLY):**
            Respond with a single JSON object where keys are the pattern identifiers (e.g., "pattern_0"). Each value should be an object containing "name" and "description".
            """
            response = await self.llm_connector.generate_text_async(prompt, settings.google_model.analysis_model, settings.google_model.analysis_model_fallback)
            descriptions = json.loads(response) if response else {}

        patterns = []
        pattern_descriptions = []
        for i, centroid in enumerate(centroids):
            cluster_df = df[df['pattern_id_num'] == i]
            desc_data = descriptions.get(f"pattern_{i}", {})
            pattern = DiscoveredPattern(
                pattern_name=desc_data.get('name', f'Pattern {i+1}') if desc_data else f'Pattern {i+1}',
                pattern_description=desc_data.get('description', 'A general usage pattern.') if desc_data else 'A general usage pattern.',
                centroid_features=centroid, member_span_ids=cluster_df['span_id'].tolist(),
                member_count=len(cluster_df)
            )
            patterns.append(pattern)
            pattern_descriptions.append(pattern.pattern_description)

        return patterns, pattern_descriptions
