"""Pre-built templates for various reporting scenarios.

Business Value: Ensures ReportingSubAgent NEVER crashes and ALWAYS delivers value.
UVS Requirement: Works with NO data, partial data, or full data.
"""

from typing import Dict, Any, List
from datetime import datetime


class ReportTemplates:
    """Pre-built templates for guaranteed value delivery in all scenarios."""
    
    @staticmethod
    def get_no_data_template() -> Dict[str, Any]:
        """Template for when no data is available - still provides value."""
        return {
            'report_type': 'guidance',
            'status': 'awaiting_data',
            'welcome_message': "I'm here to help optimize your AI costs and performance. Let's get started!",
            'value_proposition': {
                'title': 'How I Can Help You Save on AI Costs',
                'benefits': [
                    '[U+1F4B0] Reduce cloud AI spending by 20-40% on average',
                    ' LIGHTNING:  Improve model performance and response times',
                    ' CHART:  Get visibility into your AI usage patterns',
                    ' TARGET:  Optimize model selection for your use cases'
                ]
            },
            'quick_assessment': {
                'title': 'Quick Assessment Questions',
                'questions': [
                    "What AI/ML services are you currently using? (OpenAI, AWS Bedrock, Azure AI, etc.)",
                    "What's your approximate monthly AI spend?",
                    "What are your primary use cases? (Chat, embeddings, image generation, etc.)",
                    "Are you experiencing any performance issues or bottlenecks?"
                ]
            },
            'data_collection_guide': {
                'title': 'How to Get Your Usage Data',
                'providers': {
                    'openai': {
                        'name': 'OpenAI',
                        'steps': [
                            "Log into your OpenAI dashboard",
                            "Navigate to Usage  ->  Daily usage",
                            "Click 'Export' to download CSV"
                        ]
                    },
                    'aws': {
                        'name': 'AWS Bedrock/SageMaker',
                        'steps': [
                            "Open AWS Cost Explorer",
                            "Filter by service (Bedrock/SageMaker)",
                            "Export Cost and Usage Report"
                        ]
                    },
                    'azure': {
                        'name': 'Azure AI Services',
                        'steps': [
                            "Access Azure Cost Management",
                            "Select your AI resource group",
                            "Download usage details as CSV"
                        ]
                    },
                    'gcp': {
                        'name': 'Google Cloud AI',
                        'steps': [
                            "Open Cloud Billing reports",
                            "Filter by AI/ML services",
                            "Export billing data"
                        ]
                    }
                }
            },
            'next_steps': [
                "Answer the quick assessment questions above",
                "Upload any available usage data (CSV, JSON, or text)",
                "Or simply describe your current AI setup and goals"
            ],
            'example_optimizations': {
                'title': 'Common Optimization Opportunities',
                'examples': [
                    {
                        'scenario': 'High-volume chat applications',
                        'optimization': 'Switch from GPT-4 to GPT-3.5-turbo for 90% cost reduction',
                        'savings': 'Up to $10,000/month'
                    },
                    {
                        'scenario': 'Batch processing workloads',
                        'optimization': 'Implement request batching and caching',
                        'savings': '30-50% reduction in API calls'
                    },
                    {
                        'scenario': 'Development environments',
                        'optimization': 'Use smaller models or mock responses for testing',
                        'savings': '80% reduction in dev costs'
                    }
                ]
            },
            'metadata': {
                'template_version': '1.0',
                'generated_at': datetime.utcnow().isoformat(),
                'uvs_compliant': True
            }
        }
    
    @staticmethod
    def get_partial_data_template(available_sections: List[str]) -> Dict[str, Any]:
        """Template for partial data scenarios."""
        sections_text = ', '.join(available_sections) if available_sections else 'initial analysis'
        
        return {
            'report_type': 'partial_analysis',
            'status': 'partial_complete',
            'message': f"I've completed {sections_text}. Here's what I found:",
            'data_completeness': {
                'status': 'partial',
                'available': available_sections,
                'missing_info': 'Additional data would enable deeper analysis'
            },
            'partial_insights': {
                'title': 'Initial Findings',
                'note': 'Based on available information'
            },
            'recommendations': {
                'title': 'Current Recommendations',
                'note': 'These are based on partial data - more insights possible with complete information'
            },
            'missing_data_guidance': {
                'title': 'To Complete Analysis',
                'suggestions': [
                    "Provide usage data from your AI providers",
                    "Share specific cost concerns or performance issues",
                    "Include any error logs or performance metrics"
                ]
            },
            'next_steps': [
                f"Review the {sections_text} provided above",
                "Upload additional data for deeper analysis",
                "Start with quick wins from current recommendations"
            ],
            'metadata': {
                'template_version': '1.0',
                'analysis_type': 'partial',
                'uvs_compliant': True
            }
        }
    
    @staticmethod
    def get_error_recovery_template(error_context: str = None) -> Dict[str, Any]:
        """Template for error recovery - still provides value."""
        return {
            'report_type': 'recovery',
            'status': 'ready_to_help',
            'message': "I encountered a technical issue but I'm still ready to help you optimize your AI usage.",
            'alternative_actions': {
                'title': 'Let\'s Try a Different Approach',
                'options': [
                    "Share your data in a different format (CSV, JSON, or plain text)",
                    "Describe specific optimization questions you have",
                    "Tell me about your use case and I'll provide tailored advice"
                ]
            },
            'general_optimization_tips': {
                'title': 'Quick Optimization Tips While We Troubleshoot',
                'tips': [
                    {
                        'category': 'Token Usage',
                        'tip': 'Monitor and optimize prompt lengths - shorter prompts save costs',
                        'impact': '10-20% cost reduction'
                    },
                    {
                        'category': 'Model Selection',
                        'tip': 'Use appropriate models for each task - not everything needs GPT-4',
                        'impact': 'Up to 90% savings on suitable tasks'
                    },
                    {
                        'category': 'Caching',
                        'tip': 'Cache frequent requests to avoid repeated API calls',
                        'impact': '30-50% reduction in redundant calls'
                    },
                    {
                        'category': 'Batch Processing',
                        'tip': 'Batch similar requests together when possible',
                        'impact': 'Better throughput and lower per-unit costs'
                    }
                ]
            },
            'conversation_starters': [
                "What's your biggest AI cost concern right now?",
                "Which AI models are you using most frequently?",
                "Are you looking to optimize for cost, performance, or both?"
            ],
            'next_steps': [
                "Try one of the alternative approaches above",
                "Review the optimization tips for immediate value",
                "Or start fresh by describing your needs"
            ],
            'metadata': {
                'template_version': '1.0',
                'recovery_mode': True,
                'error_context': error_context,
                'uvs_compliant': True
            }
        }
    
    @staticmethod
    def get_emergency_fallback_template(debug_id: str = None) -> Dict[str, Any]:
        """Ultimate fallback - MUST return valid response."""
        return {
            'report_type': 'fallback',
            'status': 'ready_to_help',
            'message': "I'm ready to help optimize your AI usage. Let's explore your needs together.",
            'capabilities': {
                'title': 'How I Can Help',
                'services': [
                    "Cost optimization across all major AI providers",
                    "Performance tuning and latency reduction",
                    "Model selection and sizing guidance",
                    "Usage pattern analysis and forecasting",
                    "Best practices for AI implementation"
                ]
            },
            'conversation_starters': {
                'title': 'Where Should We Start?',
                'options': [
                    "Tell me about your current AI/ML workloads",
                    "Share any cost concerns or budget constraints",
                    "Describe performance bottlenecks you're facing",
                    "What are your main business objectives with AI?"
                ]
            },
            'quick_resources': {
                'title': 'Helpful Resources',
                'links': [
                    {
                        'title': 'AI Cost Calculator',
                        'description': 'Estimate potential savings'
                    },
                    {
                        'title': 'Model Comparison Guide',
                        'description': 'Compare performance vs cost across models'
                    },
                    {
                        'title': 'Best Practices Checklist',
                        'description': 'Common optimization techniques'
                    }
                ]
            },
            'next_steps': [
                "Choose a conversation starter above",
                "Upload any usage data you have available",
                "Or ask a specific optimization question"
            ],
            'metadata': {
                'template_version': '1.0',
                'fallback_mode': True,
                'debug_id': debug_id,
                'uvs_compliant': True,
                'guaranteed_delivery': True
            }
        }
    
    @staticmethod
    def enhance_with_context(template: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Enhance any template with user context if available."""
        if context and hasattr(context, 'user_id'):
            template['user_context'] = {
                'user_id': context.user_id,
                'thread_id': getattr(context, 'thread_id', None),
                'run_id': getattr(context, 'run_id', None)
            }
        
        # Add any available partial data
        if context and hasattr(context, 'metadata'):
            metadata = context.metadata or {}
            if metadata.get('user_request'):
                template['user_request_acknowledged'] = True
                template['original_request'] = metadata.get('user_request')[:200]  # First 200 chars
        
        return template