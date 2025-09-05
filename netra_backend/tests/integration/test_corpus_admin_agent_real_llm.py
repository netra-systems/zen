"""Integration tests for CorpusAdminSubAgent with REAL LLM usage.

These tests validate actual corpus management and knowledge base operations using real LLM,
real services, and actual system components - NO MOCKS.

Business Value: Ensures accurate knowledge management and retrieval for AI systems.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.corpus_admin.agent import CorpusAdminSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.database import get_db
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Real environment configuration
env = IsolatedEnvironment()


@pytest.fixture
async def real_llm_manager():
    """Get real LLM manager instance with actual API credentials."""
    from netra_backend.app.core.config import get_settings
    settings = get_settings()
    llm_manager = LLMManager(settings)
    yield llm_manager


@pytest.fixture
async def real_tool_dispatcher():
    """Get real tool dispatcher with actual tools loaded."""
    dispatcher = ToolDispatcher()
    return dispatcher


@pytest.fixture
async def real_corpus_admin_agent(real_llm_manager, real_tool_dispatcher):
    """Create real CorpusAdminSubAgent instance."""
    agent = CorpusAdminSubAgent(
        llm_manager=real_llm_manager,
        tool_dispatcher=real_tool_dispatcher,
        websocket_manager=None  # Real websocket in production
    )
    yield agent
    # Cleanup not needed for tests


class TestCorpusAdminAgentRealLLM:
    """Test suite for CorpusAdminSubAgent with real LLM interactions."""
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_knowledge_base_indexing_and_organization(
        self, real_corpus_admin_agent, db_session
    ):
        """Test 1: Index and organize knowledge base content using real LLM."""
        # Knowledge base management request
        state = DeepAgentState(
            run_id="test_corpus_001",
            user_query="Organize and index our technical documentation for better AI retrieval",
            triage_result={
                "intent": "knowledge_organization",
                "entities": ["documentation", "indexing", "retrieval"],
                "confidence": 0.94
            },
            data_result={
                "corpus_content": {
                    "documents": [
                        {
                            "id": "doc_001",
                            "title": "API Reference Guide",
                            "content": "Complete API documentation for REST endpoints...",
                            "metadata": {"type": "technical", "version": "2.1", "last_updated": "2024-01-15"},
                            "word_count": 15000,
                            "sections": 42
                        },
                        {
                            "id": "doc_002",
                            "title": "Architecture Overview",
                            "content": "System architecture and design patterns...",
                            "metadata": {"type": "architecture", "version": "1.5", "last_updated": "2024-01-10"},
                            "word_count": 8000,
                            "sections": 18
                        },
                        {
                            "id": "doc_003",
                            "title": "Best Practices Guide",
                            "content": "Development best practices and coding standards...",
                            "metadata": {"type": "guidelines", "version": "3.0", "last_updated": "2024-01-20"},
                            "word_count": 12000,
                            "sections": 35
                        }
                    ],
                    "existing_structure": {
                        "categories": ["api", "architecture", "guides", "tutorials"],
                        "tags": ["backend", "frontend", "database", "security", "performance"],
                        "index_type": "basic_keyword"
                    }
                },
                "requirements": {
                    "search_capabilities": ["semantic", "keyword", "fuzzy"],
                    "retrieval_speed": "< 100ms",
                    "accuracy_target": 0.95,
                    "use_cases": ["chatbot", "documentation_search", "code_generation"]
                }
            }
        )
        
        # Execute knowledge base organization with real LLM
        await real_corpus_admin_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.corpus_result if hasattr(state, 'corpus_result') else state.data_result
        
        # Validate indexing structure
        assert result["status"] == "success"
        assert "indexing_strategy" in result
        
        strategy = result["indexing_strategy"]
        assert "index_structure" in strategy
        assert "taxonomy" in strategy
        assert "metadata_schema" in strategy
        
        # Verify taxonomy creation
        taxonomy = strategy["taxonomy"]
        assert "primary_categories" in taxonomy
        assert "subcategories" in taxonomy
        assert "cross_references" in taxonomy
        assert len(taxonomy["primary_categories"]) >= 3
        
        # Check metadata enrichment
        assert "metadata_enrichment" in result
        enrichment = result["metadata_enrichment"]
        assert len(enrichment) == 3  # One for each document
        
        for doc_enrich in enrichment:
            assert "document_id" in doc_enrich
            assert "extracted_entities" in doc_enrich
            assert "key_concepts" in doc_enrich
            assert "suggested_tags" in doc_enrich
            assert "relevance_scores" in doc_enrich
        
        # Verify search optimization
        assert "search_optimization" in result
        search_opt = result["search_optimization"]
        assert "embedding_strategy" in search_opt
        assert "chunking_strategy" in search_opt
        assert "ranking_algorithm" in search_opt
        
        # Check for quality metrics
        assert "quality_metrics" in result
        metrics = result["quality_metrics"]
        assert "coverage_score" in metrics
        assert "organization_score" in metrics
        assert "retrievability_score" in metrics
        assert metrics["retrievability_score"] >= 0.90
        
        logger.info(f"Organized {len(enrichment)} documents with {len(taxonomy['primary_categories'])} primary categories")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_content_deduplication_and_consolidation(
        self, real_corpus_admin_agent, db_session
    ):
        """Test 2: Detect and consolidate duplicate content using real LLM."""
        # Deduplication scenario
        state = DeepAgentState(
            run_id="test_corpus_002",
            user_query="Find and consolidate duplicate or overlapping content in our knowledge base",
            triage_result={
                "intent": "content_deduplication",
                "entities": ["duplicate", "consolidation", "knowledge_base"],
                "confidence": 0.92
            },
            data_result={
                "corpus_analysis": {
                    "total_documents": 150,
                    "total_size_mb": 45,
                    "content_samples": [
                        {
                            "doc_id": "kb_101",
                            "content": "To configure authentication, set the API_KEY environment variable...",
                            "category": "setup"
                        },
                        {
                            "doc_id": "kb_102",
                            "content": "Authentication setup requires setting the API_KEY in environment...",
                            "category": "configuration"
                        },
                        {
                            "doc_id": "kb_103",
                            "content": "For API authentication, you need to configure the API_KEY...",
                            "category": "api"
                        },
                        {
                            "doc_id": "kb_201",
                            "content": "Error handling best practices include try-catch blocks...",
                            "category": "practices"
                        },
                        {
                            "doc_id": "kb_202",
                            "content": "Best practices for error handling involve using try-catch...",
                            "category": "guidelines"
                        }
                    ],
                    "similarity_threshold": 0.85,
                    "content_overlaps": {
                        "exact_duplicates": 5,
                        "near_duplicates": 18,
                        "semantic_overlaps": 32
                    }
                }
            }
        )
        
        # Execute deduplication analysis
        await real_corpus_admin_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.corpus_result if hasattr(state, 'corpus_result') else state.data_result
        
        assert result["status"] == "success"
        assert "duplication_analysis" in result
        
        analysis = result["duplication_analysis"]
        assert "duplicate_clusters" in analysis
        assert len(analysis["duplicate_clusters"]) >= 2
        
        # Verify duplicate cluster identification
        for cluster in analysis["duplicate_clusters"]:
            assert "cluster_id" in cluster
            assert "documents" in cluster
            assert len(cluster["documents"]) >= 2
            assert "similarity_score" in cluster
            assert "recommended_action" in cluster
            assert cluster["recommended_action"] in ["merge", "consolidate", "cross_reference", "keep_separate"]
        
        # Check consolidation recommendations
        assert "consolidation_plan" in result
        plan = result["consolidation_plan"]
        assert "merge_operations" in plan
        assert "content_synthesis" in plan
        
        for merge_op in plan["merge_operations"]:
            assert "source_documents" in merge_op
            assert "merged_content" in merge_op
            assert "preserved_unique_sections" in merge_op
            assert "consolidation_rationale" in merge_op
        
        # Verify content quality improvements
        assert "quality_improvements" in result
        improvements = result["quality_improvements"]
        assert "reduced_redundancy_percentage" in improvements
        assert improvements["reduced_redundancy_percentage"] >= 20
        assert "improved_clarity_score" in improvements
        assert "space_saved_mb" in improvements
        
        # Check for cross-referencing strategy
        assert "cross_reference_strategy" in result
        cross_refs = result["cross_reference_strategy"]
        assert len(cross_refs) >= 3
        
        for ref in cross_refs:
            assert "from_document" in ref
            assert "to_document" in ref
            assert "relationship_type" in ref
            assert "link_text" in ref
        
        logger.info(f"Identified {len(analysis['duplicate_clusters'])} duplicate clusters with {improvements['reduced_redundancy_percentage']}% redundancy reduction")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_semantic_search_optimization(
        self, real_corpus_admin_agent, db_session
    ):
        """Test 3: Optimize corpus for semantic search using real LLM."""
        # Semantic search optimization
        state = DeepAgentState(
            run_id="test_corpus_003",
            user_query="Optimize our knowledge base for semantic search and question answering",
            triage_result={
                "intent": "search_optimization",
                "entities": ["semantic_search", "question_answering", "optimization"],
                "confidence": 0.93
            },
            data_result={
                "search_performance": {
                    "current_metrics": {
                        "avg_query_time_ms": 250,
                        "relevance_score": 0.72,
                        "recall_at_10": 0.65,
                        "precision_at_10": 0.58
                    },
                    "query_patterns": [
                        {"type": "how_to", "frequency": 0.35},
                        {"type": "troubleshooting", "frequency": 0.25},
                        {"type": "conceptual", "frequency": 0.20},
                        {"type": "api_reference", "frequency": 0.20}
                    ],
                    "failed_queries": [
                        "How do I implement custom authentication?",
                        "What's the difference between sync and async processing?",
                        "Why is my API returning 429 errors?"
                    ]
                },
                "corpus_characteristics": {
                    "total_chunks": 5000,
                    "avg_chunk_size": 512,
                    "embedding_model": "text-embedding-ada-002",
                    "vector_dimensions": 1536,
                    "index_type": "HNSW"
                },
                "optimization_constraints": {
                    "max_chunk_size": 1024,
                    "min_chunk_size": 128,
                    "overlap_percentage": 20,
                    "computational_budget": "moderate"
                }
            }
        )
        
        # Execute semantic optimization
        await real_corpus_admin_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.corpus_result if hasattr(state, 'corpus_result') else state.data_result
        
        assert result["status"] == "success"
        assert "optimization_strategy" in result
        
        strategy = result["optimization_strategy"]
        assert "chunking_optimization" in strategy
        assert "embedding_optimization" in strategy
        assert "retrieval_optimization" in strategy
        
        # Verify chunking improvements
        chunking = strategy["chunking_optimization"]
        assert "optimal_chunk_size" in chunking
        assert "semantic_boundaries" in chunking
        assert "context_preservation" in chunking
        assert chunking["optimal_chunk_size"] >= 128
        assert chunking["optimal_chunk_size"] <= 1024
        
        # Check embedding strategy
        embedding = strategy["embedding_optimization"]
        assert "recommended_model" in embedding
        assert "fine_tuning_required" in embedding
        assert "domain_specific_adjustments" in embedding
        
        # Verify retrieval enhancements
        retrieval = strategy["retrieval_optimization"]
        assert "hybrid_search" in retrieval
        assert "reranking_strategy" in retrieval
        assert "query_expansion" in retrieval
        
        # Check for query understanding improvements
        assert "query_processing" in result
        query_proc = result["query_processing"]
        assert "intent_classification" in query_proc
        assert "entity_extraction" in query_proc
        assert "query_reformulation" in query_proc
        
        # Verify performance projections
        assert "projected_improvements" in result
        projections = result["projected_improvements"]
        assert "query_time_reduction" in projections
        assert projections["query_time_reduction"] >= 0.30  # 30% improvement
        assert "relevance_improvement" in projections
        assert projections["relevance_improvement"] >= 0.20  # 20% improvement
        
        # Check for specific optimizations for failed queries
        assert "failed_query_solutions" in result
        solutions = result["failed_query_solutions"]
        assert len(solutions) == 3  # Solutions for each failed query
        
        for solution in solutions:
            assert "original_query" in solution
            assert "root_cause" in solution
            assert "optimization_applied" in solution
            assert "expected_result" in solution
        
        logger.info(f"Optimized semantic search with {projections['relevance_improvement']*100:.1f}% relevance improvement")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_knowledge_gap_analysis_and_recommendations(
        self, real_corpus_admin_agent, db_session
    ):
        """Test 4: Identify knowledge gaps and recommend content additions using real LLM."""
        # Knowledge gap analysis
        state = DeepAgentState(
            run_id="test_corpus_004",
            user_query="Analyze our knowledge base for gaps and missing content areas",
            triage_result={
                "intent": "gap_analysis",
                "entities": ["knowledge_gaps", "content_analysis", "recommendations"],
                "confidence": 0.91
            },
            data_result={
                "current_coverage": {
                    "documented_topics": [
                        "authentication", "api_basics", "error_handling",
                        "deployment", "monitoring", "database_setup"
                    ],
                    "topic_depth": {
                        "authentication": "comprehensive",
                        "api_basics": "comprehensive",
                        "error_handling": "moderate",
                        "deployment": "basic",
                        "monitoring": "basic",
                        "database_setup": "moderate"
                    }
                },
                "user_queries": {
                    "unanswered_queries": [
                        "How to implement rate limiting?",
                        "What are the security best practices?",
                        "How to optimize for high traffic?",
                        "Disaster recovery procedures?",
                        "GDPR compliance guidelines?"
                    ],
                    "frequent_support_tickets": [
                        {"topic": "performance_tuning", "count": 45},
                        {"topic": "integration_guides", "count": 38},
                        {"topic": "troubleshooting_advanced", "count": 32},
                        {"topic": "migration_procedures", "count": 28}
                    ]
                },
                "competitor_documentation": {
                    "common_topics": [
                        "webhooks", "batch_processing", "rate_limiting",
                        "security_hardening", "compliance", "sdk_guides",
                        "video_tutorials", "interactive_demos"
                    ]
                },
                "business_priorities": {
                    "upcoming_features": ["real_time_sync", "advanced_analytics", "ml_integration"],
                    "target_audience": ["developers", "architects", "devops"],
                    "compliance_requirements": ["SOC2", "GDPR", "HIPAA"]
                }
            }
        )
        
        # Execute gap analysis
        await real_corpus_admin_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.corpus_result if hasattr(state, 'corpus_result') else state.data_result
        
        assert result["status"] == "success"
        assert "gap_analysis" in result
        
        gaps = result["gap_analysis"]
        assert "critical_gaps" in gaps
        assert "moderate_gaps" in gaps
        assert "nice_to_have" in gaps
        
        # Verify critical gaps identification
        critical = gaps["critical_gaps"]
        assert len(critical) >= 3
        
        for gap in critical:
            assert "topic" in gap
            assert "impact_score" in gap
            assert "user_demand" in gap
            assert "business_alignment" in gap
            assert gap["impact_score"] >= 8  # High impact
        
        # Check content recommendations
        assert "content_recommendations" in result
        recommendations = result["content_recommendations"]
        assert len(recommendations) >= 5
        
        for rec in recommendations:
            assert "content_type" in rec
            assert "topic" in rec
            assert "priority" in rec
            assert "estimated_effort" in rec
            assert "expected_impact" in rec
            assert "outline" in rec
        
        # Verify prioritization matrix
        assert "prioritization_matrix" in result
        matrix = result["prioritization_matrix"]
        assert "high_impact_low_effort" in matrix
        assert "high_impact_high_effort" in matrix
        assert len(matrix["high_impact_low_effort"]) >= 2  # Quick wins
        
        # Check for coverage improvement plan
        assert "coverage_improvement_plan" in result
        plan = result["coverage_improvement_plan"]
        assert "phases" in plan
        assert len(plan["phases"]) >= 3
        
        for phase in plan["phases"]:
            assert "timeline" in phase
            assert "topics_to_cover" in phase
            assert "resources_required" in phase
            assert "success_metrics" in phase
        
        # Verify competitive analysis insights
        assert "competitive_insights" in result
        insights = result["competitive_insights"]
        assert "missing_vs_competitors" in insights
        assert "unique_strengths" in insights
        assert "recommended_additions" in insights
        
        logger.info(f"Identified {len(critical)} critical gaps and {len(recommendations)} content recommendations")
    
    @pytest.mark.integration
    @pytest.mark.real_llm
    async def test_multilingual_corpus_management(
        self, real_corpus_admin_agent, db_session
    ):
        """Test 5: Manage multilingual corpus and cross-language retrieval using real LLM."""
        # Multilingual corpus scenario
        state = DeepAgentState(
            run_id="test_corpus_005",
            user_query="Set up and optimize multilingual knowledge base for global users",
            triage_result={
                "intent": "multilingual_management",
                "entities": ["multilingual", "global", "localization"],
                "confidence": 0.90
            },
            data_result={
                "language_distribution": {
                    "english": {"documents": 500, "queries_percentage": 0.60},
                    "spanish": {"documents": 50, "queries_percentage": 0.15},
                    "french": {"documents": 30, "queries_percentage": 0.10},
                    "german": {"documents": 20, "queries_percentage": 0.08},
                    "japanese": {"documents": 10, "queries_percentage": 0.05},
                    "other": {"documents": 5, "queries_percentage": 0.02}
                },
                "translation_quality": {
                    "machine_translated": 0.70,
                    "human_reviewed": 0.25,
                    "native_content": 0.05
                },
                "cross_language_queries": {
                    "frequency": 0.35,
                    "common_patterns": [
                        "Spanish query -> English content",
                        "French query -> English content",
                        "Japanese query -> English content"
                    ]
                },
                "localization_requirements": {
                    "cultural_adaptation": True,
                    "legal_compliance": ["GDPR_EU", "CCPA_US", "LGPD_Brazil"],
                    "date_time_formats": True,
                    "currency_examples": True
                },
                "technical_constraints": {
                    "storage_budget_gb": 100,
                    "translation_api_budget": 5000,
                    "supported_languages": 10
                }
            }
        )
        
        # Execute multilingual management
        await real_corpus_admin_agent.execute(state, state.run_id, stream_updates=False)
        
        # Get result from state
        result = state.corpus_result if hasattr(state, 'corpus_result') else state.data_result
        
        assert result["status"] == "success"
        assert "multilingual_strategy" in result
        
        strategy = result["multilingual_strategy"]
        assert "language_prioritization" in strategy
        assert "translation_approach" in strategy
        assert "cross_language_retrieval" in strategy
        
        # Verify language prioritization
        prioritization = strategy["language_prioritization"]
        assert "tier1_languages" in prioritization
        assert "tier2_languages" in prioritization
        assert "tier3_languages" in prioritization
        assert len(prioritization["tier1_languages"]) >= 2
        
        # Check translation strategy
        translation = strategy["translation_approach"]
        assert "content_prioritization" in translation
        assert "quality_tiers" in translation
        assert "hybrid_approach" in translation
        
        for tier in translation["quality_tiers"]:
            assert "content_type" in tier
            assert "translation_method" in tier
            assert "review_process" in tier
        
        # Verify cross-language retrieval
        cross_lang = strategy["cross_language_retrieval"]
        assert "embedding_strategy" in cross_lang
        assert "query_translation" in cross_lang
        assert "result_translation" in cross_lang
        assert "confidence_thresholds" in cross_lang
        
        # Check localization recommendations
        assert "localization_plan" in result
        localization = result["localization_plan"]
        assert "cultural_adaptations" in localization
        assert "regional_examples" in localization
        assert "compliance_adjustments" in localization
        
        # Verify quality assurance
        assert "quality_assurance" in result
        qa = result["quality_assurance"]
        assert "translation_validation" in qa
        assert "consistency_checks" in qa
        assert "native_speaker_review" in qa
        
        # Check for efficiency optimizations
        assert "efficiency_optimizations" in result
        optimizations = result["efficiency_optimizations"]
        assert "shared_embeddings" in optimizations
        assert "caching_strategy" in optimizations
        assert "on_demand_translation" in optimizations
        
        # Verify cost projections
        assert "cost_analysis" in result
        costs = result["cost_analysis"]
        assert "translation_costs" in costs
        assert "storage_costs" in costs
        assert "maintenance_costs" in costs
        assert "roi_projection" in costs
        
        logger.info(f"Set up multilingual corpus for {len(prioritization['tier1_languages'])} tier-1 languages with cross-language retrieval")


if __name__ == "__main__":
    # Run tests with real services
    asyncio.run(pytest.main([__file__, "-v", "--real-llm"]))