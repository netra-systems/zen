"""Core Tests - Split from test_corpus_generation_pipeline_integration.py

Business Value Justification (BVJ):
- Segment: All customer tiers using AI-powered optimization features
- Business Goal: Knowledge base accuracy and response quality
- Value Impact: Ensures accurate, actionable AI responses through quality corpus
- Strategic/Revenue Impact: Protects $12K MRR from poor knowledge retrieval

Test Coverage:
- Synthetic data generation with quality validation
- Corpus creation and indexing pipeline
- Knowledge retrieval accuracy testing
- End-to-end pipeline integrity validation
"""

import asyncio
import pytest
import time
import uuid
import json
import tempfile
import os
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from tests.unified.jwt_token_helpers import JWTTestHelper
from app.schemas.shared_types import ProcessingResult

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for processing."""
        return {
            "content_id": self.content_id,
            "source_type": self.source_type, 
            "content": self.content,
            "metadata": self.metadata,
            "quality_score": self.quality_score
        }

    def __init__(self):
        """Initialize corpus generation tester."""
        self.jwt_helper = JWTTestHelper()
        self.backend_url = "http://localhost:8000"
        self.temp_files: List[str] = []
        self.test_corpus_ids: List[str] = []
