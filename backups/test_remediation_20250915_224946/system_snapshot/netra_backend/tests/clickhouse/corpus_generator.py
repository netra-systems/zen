"""
Corpus Data Generator
Generates realistic corpus data for testing
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.tests.clickhouse.generator_base import DataGeneratorBase

class CorpusGenerator(DataGeneratorBase):
    """Generate realistic corpus data"""
    
    def _create_corpus_templates(self) -> Dict[str, List[tuple[str, str]]]:
        """Create corpus templates for different workload types"""
        return {
            "chat": [
                ("How do I optimize my {model} usage?", 
                 "To optimize {model} usage, consider: 1) Batch requests, 2) Use appropriate model size, 3) Cache responses"),
                ("What's the best way to reduce latency?",
                 "Reduce latency by: 1) Using edge deployments, 2) Optimizing prompts, 3) Implementing caching"),
            ],
            "code_generation": [
                ("Generate a Python function to {task}",
                 "def {function_name}():\n    # Implementation here\n    pass"),
                ("Write a SQL query to {task}",
                 "SELECT * FROM table WHERE condition;"),
            ],
            "analysis": [
                ("Analyze the performance of {metric}",
                 "Analysis shows {metric} has {trend} trend with {insight}"),
                ("What are the optimization opportunities?",
                 "Key opportunities: 1) {opt1}, 2) {opt2}, 3) {opt3}"),
            ]
        }
    
    def _fill_corpus_template(self, prompt_template: str, response_template: str) -> tuple[str, str]:
        """Fill corpus templates with realistic values"""
        prompt = prompt_template.format(
            model=random.choice(self.models),
            task=random.choice(["process data", "analyze metrics", "generate report"]),
            metric=random.choice(["latency", "throughput", "cost"])
        )
        
        response = response_template.format(
            model=random.choice(self.models),
            function_name=f"optimize_{random.choice(['performance', 'cost', 'quality'])}",
            task="optimize performance",
            metric="latency",
            trend=random.choice(["increasing", "decreasing", "stable"]),
            insight="correlation with request volume",
            opt1="Reduce model size",
            opt2="Implement caching",
            opt3="Batch requests"
        )
        return prompt, response
    
    def _create_corpus_metadata(self, prompt: str, response: str) -> Dict[str, Any]:
        """Create corpus metadata"""
        return {
            "quality_score": random.uniform(0.7, 1.0),
            "tokens": len(prompt.split()) + len(response.split()),
            "source": random.choice(["production", "synthetic", "curated"])
        }
    
    def _create_corpus_record(self, workload_type: str, prompt: str, 
                            response: str) -> Dict[str, Any]:
        """Create a single corpus record"""
        return {
            "record_id": str(uuid.uuid4()),
            "workload_type": workload_type,
            "prompt": prompt,
            "response": response,
            "metadata": self._create_corpus_metadata(prompt, response),
            "created_at": datetime.now() - timedelta(days=random.randint(0, 30))
        }
    
    def generate_corpus_data(self, count: int, 
                           workload_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Generate realistic corpus data for training"""
        if not workload_types:
            workload_types = self.workload_types
        
        corpus = []
        templates = self._create_corpus_templates()
        
        for i in range(count):
            workload_type = random.choice(workload_types)
            
            if workload_type in templates:
                prompt_template, response_template = random.choice(templates[workload_type])
                prompt, response = self._fill_corpus_template(prompt_template, response_template)
            else:
                prompt = f"Sample {workload_type} prompt {i}"
                response = f"Sample {workload_type} response {i}"
            
            record = self._create_corpus_record(workload_type, prompt, response)
            corpus.append(record)
        
        return corpus