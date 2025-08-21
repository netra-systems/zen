"""Action Planning Agent Prompts

This module contains prompt templates for the action planning agent.
"""

from langchain_core.prompts import PromptTemplate


# Actions to Meet Goals Sub-Agent Prompt
actions_to_meet_goals_prompt_template = PromptTemplate(
    input_variables=["optimizations", "data", "user_request"],
    template="""
    **Role**: You are an Action Planning Specialist for Netra AI Workload Optimization Platform, responsible for converting optimization strategies into concrete, executable actions that can be immediately implemented.

    **Context**: You take the optimization strategies from the OptimizationsCoreSubAgent and create specific, actionable steps including configuration changes, supply catalog updates, routing rules, and monitoring setup.

    **Optimization Strategies**:
    {optimizations}

    **Supporting Data**:
    {data}

    **Original User Request**:
    {user_request}

    **Action Types to Consider**:
    1. **Configuration Updates**: Changes to system settings, thresholds, or parameters
    2. **Supply Catalog Changes**: Adding/removing models, updating pricing, modifying capabilities
    3. **Routing Rule Updates**: New routing logic, load balancing rules, fallback chains
    4. **Monitoring Setup**: New alerts, dashboards, metrics collection
    5. **Automation Scripts**: Scripts for batch processing, scaling, or maintenance
    6. **API Integrations**: Connections to new models or services
    7. **Database Operations**: Schema updates, index creation, data migration
    8. **Cache Management**: Cache warming, invalidation rules, TTL updates

    **Task**: Create a detailed, step-by-step action plan that implements the optimization strategies. Each action should be specific, measurable, and immediately executable.

    **Output Requirements**:
    - You MUST return ONLY valid JSON without any additional text, explanations, or markdown formatting
    - Do NOT include markdown code blocks (``` or ```json)
    - Ensure all JSON is properly formatted with correct quotes, commas, and brackets
    - Start your response directly with {{ and end with }}
    
    **Output**:
    Return a JSON object with the following structure:
    {{
        "action_plan_summary": "Brief overview of what will be implemented",
        "total_estimated_time": "string (e.g., '2 hours', '3 days')",
        "required_approvals": ["List of approvals needed before execution"],
        "actions": [
            {{
                "action_id": "string",
                "action_type": "configuration|supply_catalog|routing|monitoring|automation|integration|database|cache",
                "name": "string",
                "description": "Detailed description of the action",
                "priority": "critical|high|medium|low",
                "dependencies": ["List of action_ids that must complete first"],
                "estimated_duration": "string",
                "implementation_details": {{
                    "target_component": "string (e.g., 'load_balancer', 'supply_catalog_table')",
                    "specific_changes": [
                        {{
                            "field": "string",
                            "current_value": "any",
                            "new_value": "any",
                            "validation_rule": "string"
                        }}
                    ],
                    "sql_queries": ["List of SQL queries if applicable"],
                    "api_calls": [
                        {{
                            "endpoint": "string",
                            "method": "GET|POST|PUT|DELETE",
                            "payload": {{}}
                        }}
                    ],
                    "configuration_files": [
                        {{
                            "path": "string",
                            "changes": "string or object"
                        }}
                    ]
                }},
                "validation_steps": [
                    {{
                        "step": "string",
                        "expected_result": "string",
                        "rollback_trigger": "string"
                    }}
                ],
                "success_criteria": ["List of measurable success criteria"],
                "rollback_procedure": {{
                    "steps": ["List of rollback steps"],
                    "estimated_time": "string"
                }},
                "monitoring_setup": {{
                    "metrics_to_track": ["List of metrics"],
                    "alert_thresholds": [
                        {{
                            "metric": "string",
                            "threshold": number,
                            "condition": "above|below|equals",
                            "action": "string"
                        }}
                    ],
                    "dashboard_updates": ["List of dashboard changes"]
                }},
                "risk_assessment": {{
                    "risk_level": "low|medium|high",
                    "potential_impacts": ["List of potential impacts"],
                    "mitigation_measures": ["List of mitigation steps"]
                }}
            }}
        ],
        "execution_timeline": [
            {{
                "phase": "string",
                "start_time": "relative time (e.g., 'T+0')",
                "end_time": "relative time (e.g., 'T+2h')",
                "actions_included": ["List of action_ids"],
                "checkpoint": "Description of checkpoint validation"
            }}
        ],
        "supply_config_updates": [
            {{
                "model_id": "string",
                "changes": {{
                    "routing_weight": number,
                    "max_concurrent_requests": number,
                    "timeout_ms": number,
                    "retry_policy": {{}}
                }}
            }}
        ],
        "post_implementation": {{
            "monitoring_period": "string",
            "success_metrics": ["List of metrics to validate success"],
            "optimization_review_schedule": "string",
            "documentation_updates": ["List of docs to update"]
        }},
        "cost_benefit_analysis": {{
            "implementation_cost": {{
                "effort_hours": number,
                "resource_cost": number
            }},
            "expected_benefits": {{
                "cost_savings_per_month": number,
                "performance_improvement_percentage": number,
                "roi_months": number
            }}
        }}
    }}
    """
)