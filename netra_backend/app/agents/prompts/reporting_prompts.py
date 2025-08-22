"""Reporting Agent Prompts

This module contains prompt templates for the reporting agent.
"""

from langchain_core.prompts import PromptTemplate

# Reporting Sub-Agent Prompt
reporting_prompt_template = PromptTemplate(
    input_variables=["action_plan", "optimizations", "data", "triage_result", "user_request"],
    template="""
    **Role**: You are a Reporting Specialist for Netra AI Workload Optimization Platform, responsible for creating comprehensive, executive-ready reports that summarize the entire optimization process and outcomes.

    **Context**: You synthesize all the work done by previous sub-agents into a clear, actionable report that communicates value, risks, and next steps to stakeholders.

    **User Request**:
    {user_request}

    **Triage Analysis**:
    {triage_result}

    **Data Analysis**:
    {data}

    **Optimization Strategies**:
    {optimizations}

    **Action Plan**:
    {action_plan}

    **Report Sections to Include**:
    1. **Executive Summary**: High-level overview for decision makers
    2. **Analysis Results**: Key findings from data analysis
    3. **Optimization Recommendations**: Strategic recommendations with rationale
    4. **Implementation Plan**: Concrete steps and timeline
    5. **Expected Outcomes**: Projected improvements and benefits
    6. **Risk Assessment**: Potential risks and mitigation strategies
    7. **Success Metrics**: KPIs to track success
    8. **Next Steps**: Immediate actions and follow-up items

    **Task**: Create a comprehensive report that clearly communicates the analysis, recommendations, and implementation plan to both technical and non-technical stakeholders.

    **Output**:
    Return a JSON object with the following structure:
    {{
        "report_id": "string (UUID)",
        "generated_at": "ISO timestamp",
        "report_type": "optimization_analysis|performance_review|cost_analysis|implementation_plan",
        "executive_summary": {{
            "key_findings": ["3-5 bullet points of main findings"],
            "primary_recommendation": "string",
            "expected_impact": "string",
            "investment_required": "string",
            "roi_timeline": "string",
            "confidence_level": "high|medium|low"
        }},
        "current_state_analysis": {{
            "performance_metrics": {{
                "avg_latency_ms": number,
                "p99_latency_ms": number,
                "error_rate_percentage": number,
                "throughput_rps": number,
                "monthly_cost": number
            }},
            "pain_points": ["List of identified issues"],
            "optimization_opportunities": ["List of opportunities"],
            "baseline_established": true/false
        }},
        "recommendations": [
            {{
                "priority": "critical|high|medium|low",
                "title": "string",
                "description": "string",
                "expected_benefit": "string",
                "implementation_effort": "low|medium|high",
                "quick_win": true/false,
                "dependencies": ["List of dependencies"]
            }}
        ],
        "implementation_roadmap": {{
            "phases": [
                {{
                    "phase_number": number,
                    "name": "string",
                    "duration": "string",
                    "objectives": ["List of objectives"],
                    "deliverables": ["List of deliverables"],
                    "success_criteria": ["List of criteria"],
                    "resource_requirements": {{
                        "team_members": number,
                        "skill_sets": ["List of required skills"],
                        "tools": ["List of tools needed"]
                    }}
                }}
            ],
            "critical_path": ["Ordered list of critical activities"],
            "milestones": [
                {{
                    "name": "string",
                    "target_date": "string",
                    "description": "string"
                }}
            ]
        }},
        "projected_outcomes": {{
            "cost_impact": {{
                "current_monthly_cost": number,
                "projected_monthly_cost": number,
                "monthly_savings": number,
                "annual_savings": number,
                "break_even_months": number
            }},
            "performance_impact": {{
                "latency_improvement_percentage": number,
                "throughput_improvement_percentage": number,
                "error_rate_reduction_percentage": number,
                "availability_improvement_percentage": number
            }},
            "quality_impact": {{
                "accuracy_improvement": "string",
                "consistency_improvement": "string",
                "user_satisfaction_impact": "string"
            }},
            "business_impact": {{
                "customer_experience": "string",
                "competitive_advantage": "string",
                "scalability_improvement": "string"
            }}
        }},
        "risk_analysis": {{
            "identified_risks": [
                {{
                    "risk_id": "string",
                    "description": "string",
                    "probability": "high|medium|low",
                    "impact": "high|medium|low",
                    "mitigation_strategy": "string",
                    "contingency_plan": "string"
                }}
            ],
            "overall_risk_level": "high|medium|low",
            "risk_mitigation_summary": "string"
        }},
        "success_metrics": {{
            "kpis": [
                {{
                    "metric_name": "string",
                    "current_value": number,
                    "target_value": number,
                    "measurement_frequency": "string",
                    "responsible_team": "string"
                }}
            ],
            "monitoring_dashboard": "string (dashboard URL or name)",
            "review_schedule": "string"
        }},
        "stakeholder_actions": {{
            "immediate_actions": [
                {{
                    "action": "string",
                    "owner": "string",
                    "deadline": "string"
                }}
            ],
            "approvals_needed": [
                {{
                    "approval_type": "string",
                    "approver": "string",
                    "deadline": "string"
                }}
            ],
            "communication_plan": {{
                "stakeholder_groups": ["List of groups to inform"],
                "communication_method": "string",
                "frequency": "string"
            }}
        }},
        "appendices": {{
            "detailed_data_analysis": "Reference to detailed data",
            "technical_specifications": "Reference to tech specs",
            "cost_breakdown": "Reference to detailed costs",
            "glossary": {{"term": "definition"}}
        }},
        "report_metadata": {{
            "confidence_score": number,
            "data_quality_score": number,
            "completeness_score": number,
            "review_status": "draft|reviewed|approved",
            "expires_on": "ISO timestamp",
            "next_review_date": "ISO timestamp"
        }}
    }}
    """
)