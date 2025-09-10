"""
Test ReportData Type Definition SSOT Violations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure consistent reporting data structures across analytics
- Value Impact: Prevents data inconsistencies in business intelligence and metrics
- Strategic Impact: Accurate reporting is critical for business decision making

CRITICAL: ReportData type definitions scattered across multiple files violate SSOT
principles and create inconsistent data structures for business intelligence,
analytics, and operational reporting that directly impact business decisions.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture


@dataclass
class ReportDataDefinition:
    """Definition of a ReportData type."""
    name: str
    module_path: str
    fields: Dict[str, Dict[str, Any]]
    usage_context: str
    
    def get_field_signature(self) -> str:
        """Get comparable signature of fields."""
        sorted_fields = sorted(self.fields.items())
        field_sigs = []
        for name, definition in sorted_fields:
            field_type = definition.get('type', 'unknown')
            required = definition.get('required', False)
            field_sigs.append(f"{name}:{field_type}:{'req' if required else 'opt'}")
        return "|".join(field_sigs)


class TestReportDataSSotViolations(BaseIntegrationTest):
    """Integration tests for ReportData type SSOT compliance."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_report_data_definition_consolidation(self, real_services_fixture):
        """
        Test detection and consolidation of scattered ReportData definitions.
        
        MISSION CRITICAL: Consistent ReportData structures ensure accurate
        business intelligence and prevent analytics inconsistencies.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock ReportData consolidation analyzer
        class ReportDataConsolidationAnalyzer:
            def __init__(self, redis_client):
                self.redis = redis_client
            
            def analyze_report_data_definitions(self, definitions: List[ReportDataDefinition]) -> Dict[str, Any]:
                """Analyze ReportData definitions for SSOT violations."""
                analysis_result = {
                    'analyzed_at': asyncio.get_event_loop().time(),
                    'total_definitions': len(definitions),
                    'unique_signatures': set(),
                    'duplicate_patterns': {},
                    'ssot_violations': [],
                    'consolidation_opportunities': [],
                    'business_impact_assessment': {}
                }
                
                # Group definitions by name and analyze duplicates
                name_groups = {}
                for definition in definitions:
                    if definition.name not in name_groups:
                        name_groups[definition.name] = []
                    name_groups[definition.name].append(definition)
                
                # Analyze each name group for SSOT violations
                for name, group_definitions in name_groups.items():
                    if len(group_definitions) > 1:
                        # Multiple definitions with same name - potential SSOT violation
                        signatures = set(defn.get_field_signature() for defn in group_definitions)
                        
                        if len(signatures) > 1:
                            # Different structures - definite SSOT violation
                            analysis_result['ssot_violations'].append({
                                'type_name': name,
                                'violation_type': 'structural_inconsistency',
                                'definition_count': len(group_definitions),
                                'unique_structures': len(signatures),
                                'locations': [defn.module_path for defn in group_definitions],
                                'usage_contexts': [defn.usage_context for defn in group_definitions],
                                'severity': 'high'
                            })
                        else:
                            # Same structure, multiple locations - duplication violation
                            analysis_result['ssot_violations'].append({
                                'type_name': name,
                                'violation_type': 'location_duplication',
                                'definition_count': len(group_definitions),
                                'locations': [defn.module_path for defn in group_definitions],
                                'usage_contexts': [defn.usage_context for defn in group_definitions],
                                'severity': 'medium'
                            })
                
                # Find consolidation opportunities
                analysis_result['consolidation_opportunities'] = self._identify_consolidation_opportunities(
                    name_groups, analysis_result['ssot_violations']
                )
                
                # Assess business impact
                analysis_result['business_impact_assessment'] = self._assess_business_impact(
                    analysis_result['ssot_violations']
                )
                
                return analysis_result
            
            def _identify_consolidation_opportunities(self, name_groups: Dict[str, List], violations: List[Dict]) -> List[Dict[str, Any]]:
                """Identify opportunities for ReportData consolidation."""
                opportunities = []
                
                for violation in violations:
                    type_name = violation['type_name']
                    group_definitions = name_groups[type_name]
                    
                    if violation['violation_type'] == 'structural_inconsistency':
                        # Need to create unified structure
                        opportunities.append({
                            'type': 'structural_unification',
                            'target_type': type_name,
                            'action': 'Create unified ReportData interface with field unions',
                            'affected_modules': violation['locations'],
                            'complexity': 'high',
                            'business_risk': 'medium'
                        })
                    
                    elif violation['violation_type'] == 'location_duplication':
                        # Need to consolidate to single location
                        canonical_location = self._determine_canonical_location(group_definitions)
                        opportunities.append({
                            'type': 'location_consolidation',
                            'target_type': type_name,
                            'action': f'Consolidate to canonical location: {canonical_location}',
                            'source_modules': [loc for loc in violation['locations'] if loc != canonical_location],
                            'canonical_location': canonical_location,
                            'complexity': 'medium',
                            'business_risk': 'low'
                        })
                
                return opportunities
            
            def _determine_canonical_location(self, definitions: List[ReportDataDefinition]) -> str:
                """Determine canonical location for ReportData type."""
                # Prefer shared/types or reports/types locations
                for definition in definitions:
                    if 'shared/types' in definition.module_path:
                        return definition.module_path
                    if 'reports/types' in definition.module_path:
                        return definition.module_path
                
                # Fall back to first definition
                return definitions[0].module_path
            
            def _assess_business_impact(self, violations: List[Dict]) -> Dict[str, Any]:
                """Assess business impact of ReportData SSOT violations."""
                impact_assessment = {
                    'overall_risk': 'medium',
                    'data_consistency_risk': 0,
                    'analytics_reliability_risk': 0,
                    'decision_making_impact': [],
                    'technical_debt_score': 0
                }
                
                for violation in violations:
                    if violation['violation_type'] == 'structural_inconsistency':
                        impact_assessment['data_consistency_risk'] += 3
                        impact_assessment['analytics_reliability_risk'] += 2
                        impact_assessment['technical_debt_score'] += 5
                        
                        impact_assessment['decision_making_impact'].append({
                            'type': 'data_inconsistency',
                            'affected_reports': violation['usage_contexts'],
                            'impact': 'Inconsistent data structures may lead to incorrect business metrics'
                        })
                    
                    elif violation['violation_type'] == 'location_duplication':
                        impact_assessment['technical_debt_score'] += 2
                        
                        impact_assessment['decision_making_impact'].append({
                            'type': 'maintenance_overhead',
                            'affected_modules': violation['locations'],
                            'impact': 'Multiple maintenance points increase risk of inconsistent updates'
                        })
                
                # Determine overall risk level
                total_risk = impact_assessment['data_consistency_risk'] + impact_assessment['analytics_reliability_risk']
                if total_risk >= 8:
                    impact_assessment['overall_risk'] = 'high'
                elif total_risk >= 4:
                    impact_assessment['overall_risk'] = 'medium'
                else:
                    impact_assessment['overall_risk'] = 'low'
                
                return impact_assessment
            
            async def store_consolidation_analysis(self, analysis: Dict[str, Any]):
                """Store ReportData consolidation analysis."""
                # Convert sets to lists for JSON serialization
                serializable_analysis = json.loads(json.dumps(analysis, default=str))
                
                await self.redis.setex(
                    'report_data_consolidation_analysis',
                    3600,
                    json.dumps(serializable_analysis)
                )
                
                return serializable_analysis
        
        analyzer = ReportDataConsolidationAnalyzer(redis_client)
        
        # Mock scattered ReportData definitions
        test_report_definitions = [
            ReportDataDefinition(
                name='UserMetricsReportData',
                module_path='scripts/status_types.py',
                fields={
                    'user_count': {'type': 'int', 'required': True},
                    'active_users': {'type': 'int', 'required': True},
                    'signup_rate': {'type': 'float', 'required': True},
                    'retention_rate': {'type': 'float', 'required': False}
                },
                usage_context='status_reporting'
            ),
            ReportDataDefinition(
                name='UserMetricsReportData',
                module_path='analytics/user_analytics.py',
                fields={
                    'user_count': {'type': 'int', 'required': True},
                    'active_users': {'type': 'int', 'required': True},
                    'signup_rate': {'type': 'float', 'required': True},
                    'churn_rate': {'type': 'float', 'required': True},  # Different field
                    'ltv': {'type': 'float', 'required': False}  # Additional field
                },
                usage_context='analytics_dashboard'
            ),
            ReportDataDefinition(
                name='ThreadMetricsReportData',
                module_path='scripts/status_renderer.py',
                fields={
                    'total_threads': {'type': 'int', 'required': True},
                    'active_threads': {'type': 'int', 'required': True},
                    'avg_messages_per_thread': {'type': 'float', 'required': True}
                },
                usage_context='operational_metrics'
            ),
            ReportDataDefinition(
                name='ThreadMetricsReportData',
                module_path='reports/thread_analytics.py',
                fields={
                    'total_threads': {'type': 'int', 'required': True},
                    'active_threads': {'type': 'int', 'required': True},
                    'avg_messages_per_thread': {'type': 'float', 'required': True}
                },
                usage_context='analytics_reporting'
            ),
            ReportDataDefinition(
                name='AgentPerformanceReportData',
                module_path='netra_backend/app/analytics/agent_metrics.py',
                fields={
                    'agent_id': {'type': 'str', 'required': True},
                    'execution_count': {'type': 'int', 'required': True},
                    'avg_execution_time': {'type': 'float', 'required': True},
                    'success_rate': {'type': 'float', 'required': True},
                    'error_count': {'type': 'int', 'required': True}
                },
                usage_context='agent_analytics'
            )
        ]
        
        # Analyze ReportData definitions
        analysis_results = analyzer.analyze_report_data_definitions(test_report_definitions)
        
        # Validate SSOT violation detection
        assert len(analysis_results['ssot_violations']) > 0, (
            "Should detect ReportData SSOT violations"
        )
        
        # Validate specific violations
        violation_types = set(v['violation_type'] for v in analysis_results['ssot_violations'])
        assert 'structural_inconsistency' in violation_types, (
            "Should detect structural inconsistencies in UserMetricsReportData"
        )
        assert 'location_duplication' in violation_types, (
            "Should detect location duplications in ThreadMetricsReportData"
        )
        
        # Find UserMetricsReportData violation
        user_metrics_violations = [
            v for v in analysis_results['ssot_violations']
            if v['type_name'] == 'UserMetricsReportData'
        ]
        assert len(user_metrics_violations) > 0, "Should detect UserMetricsReportData violations"
        
        user_violation = user_metrics_violations[0]
        assert user_violation['violation_type'] == 'structural_inconsistency', (
            "UserMetricsReportData should have structural inconsistency"
        )
        assert user_violation['unique_structures'] > 1, (
            "UserMetricsReportData should have multiple unique structures"
        )
        
        # Validate consolidation opportunities
        assert len(analysis_results['consolidation_opportunities']) > 0, (
            "Should identify consolidation opportunities"
        )
        
        # Check for specific opportunity types
        opportunity_types = set(opp['type'] for opp in analysis_results['consolidation_opportunities'])
        assert 'structural_unification' in opportunity_types, (
            "Should recommend structural unification"
        )
        assert 'location_consolidation' in opportunity_types, (
            "Should recommend location consolidation"
        )
        
        # Validate business impact assessment
        business_impact = analysis_results['business_impact_assessment']
        assert 'overall_risk' in business_impact, "Should assess overall risk"
        assert 'data_consistency_risk' in business_impact, "Should assess data consistency risk"
        assert 'analytics_reliability_risk' in business_impact, "Should assess analytics reliability risk"
        assert len(business_impact['decision_making_impact']) > 0, (
            "Should identify decision making impacts"
        )
        
        # Store analysis results
        stored_results = await analyzer.store_consolidation_analysis(analysis_results)
        
        assert 'ssot_violations' in stored_results, "Stored results must include violations"
        assert 'consolidation_opportunities' in stored_results, "Stored results must include opportunities"
        
        # Cleanup
        await redis_client.delete('report_data_consolidation_analysis')


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_report_data_analytics_consistency_validation(self, real_services_fixture):
        """
        Test validation of ReportData consistency across analytics pipelines.
        
        BUSINESS CRITICAL: Analytics consistency ensures accurate business
        intelligence and prevents incorrect strategic decisions.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock analytics consistency validator
        class AnalyticsConsistencyValidator:
            def __init__(self, redis_client):
                self.redis = redis_client
            
            def validate_analytics_consistency(self, report_definitions: List[ReportDataDefinition]) -> Dict[str, Any]:
                """Validate consistency of ReportData across analytics pipelines."""
                validation_result = {
                    'validated_at': asyncio.get_event_loop().time(),
                    'total_analytics_pipelines': 0,
                    'consistent_pipelines': 0,
                    'inconsistent_pipelines': 0,
                    'consistency_violations': [],
                    'data_quality_risks': [],
                    'business_metrics_impact': {}
                }
                
                # Group definitions by analytics context
                analytics_contexts = {}
                for definition in report_definitions:
                    context = definition.usage_context
                    if 'analytics' in context or 'metrics' in context or 'reporting' in context:
                        if context not in analytics_contexts:
                            analytics_contexts[context] = []
                        analytics_contexts[context].append(definition)
                
                validation_result['total_analytics_pipelines'] = len(analytics_contexts)
                
                # Validate consistency within each analytics context
                for context, definitions in analytics_contexts.items():
                    context_validation = self._validate_context_consistency(context, definitions)
                    
                    if context_validation['is_consistent']:
                        validation_result['consistent_pipelines'] += 1
                    else:
                        validation_result['inconsistent_pipelines'] += 1
                        validation_result['consistency_violations'].extend(context_validation['violations'])
                        validation_result['data_quality_risks'].extend(context_validation['quality_risks'])
                
                # Assess business metrics impact
                validation_result['business_metrics_impact'] = self._assess_metrics_impact(
                    validation_result['consistency_violations']
                )
                
                return validation_result
            
            def _validate_context_consistency(self, context: str, definitions: List[ReportDataDefinition]) -> Dict[str, Any]:
                """Validate consistency within a specific analytics context."""
                context_validation = {
                    'context': context,
                    'is_consistent': True,
                    'violations': [],
                    'quality_risks': []
                }
                
                # Check for field naming consistency
                all_fields = {}
                for definition in definitions:
                    for field_name, field_def in definition.fields.items():
                        if field_name not in all_fields:
                            all_fields[field_name] = []
                        all_fields[field_name].append({
                            'definition': definition,
                            'field_def': field_def
                        })
                
                # Validate field consistency
                for field_name, field_usages in all_fields.items():
                    if len(field_usages) > 1:
                        # Check type consistency
                        types = set(usage['field_def'].get('type') for usage in field_usages)
                        if len(types) > 1:
                            context_validation['is_consistent'] = False
                            context_validation['violations'].append({
                                'type': 'field_type_inconsistency',
                                'field_name': field_name,
                                'context': context,
                                'types_found': list(types),
                                'affected_definitions': [usage['definition'].name for usage in field_usages]
                            })
                        
                        # Check requirement consistency
                        requirements = set(usage['field_def'].get('required', False) for usage in field_usages)
                        if len(requirements) > 1:
                            context_validation['is_consistent'] = False
                            context_validation['violations'].append({
                                'type': 'field_requirement_inconsistency',
                                'field_name': field_name,
                                'context': context,
                                'requirements_found': list(requirements),
                                'affected_definitions': [usage['definition'].name for usage in field_usages]
                            })
                
                # Identify data quality risks
                if not context_validation['is_consistent']:
                    context_validation['quality_risks'].append({
                        'risk_type': 'aggregation_errors',
                        'context': context,
                        'description': 'Inconsistent field types may cause aggregation errors in analytics',
                        'severity': 'high'
                    })
                    
                    context_validation['quality_risks'].append({
                        'risk_type': 'metric_calculation_errors',
                        'context': context,
                        'description': 'Field requirement inconsistencies may cause missing data in calculations',
                        'severity': 'medium'
                    })
                
                return context_validation
            
            def _assess_metrics_impact(self, violations: List[Dict[str, Any]]) -> Dict[str, Any]:
                """Assess impact on business metrics."""
                metrics_impact = {
                    'affected_metrics': set(),
                    'calculation_reliability': 'high',
                    'data_accuracy_risk': 'low',
                    'strategic_decision_impact': []
                }
                
                for violation in violations:
                    field_name = violation.get('field_name', '')
                    
                    # Identify affected business metrics
                    if 'rate' in field_name or 'percentage' in field_name:
                        metrics_impact['affected_metrics'].add('conversion_metrics')
                    if 'count' in field_name or 'total' in field_name:
                        metrics_impact['affected_metrics'].add('volume_metrics')
                    if 'time' in field_name or 'duration' in field_name:
                        metrics_impact['affected_metrics'].add('performance_metrics')
                    if 'user' in field_name:
                        metrics_impact['affected_metrics'].add('user_engagement_metrics')
                    if 'revenue' in field_name or 'cost' in field_name:
                        metrics_impact['affected_metrics'].add('financial_metrics')
                
                # Assess calculation reliability
                if len(violations) >= 3:
                    metrics_impact['calculation_reliability'] = 'low'
                    metrics_impact['data_accuracy_risk'] = 'high'
                elif len(violations) >= 1:
                    metrics_impact['calculation_reliability'] = 'medium'
                    metrics_impact['data_accuracy_risk'] = 'medium'
                
                # Identify strategic decision impacts
                if 'financial_metrics' in metrics_impact['affected_metrics']:
                    metrics_impact['strategic_decision_impact'].append({
                        'area': 'revenue_planning',
                        'impact': 'Inconsistent financial data may lead to incorrect revenue projections',
                        'severity': 'critical'
                    })
                
                if 'user_engagement_metrics' in metrics_impact['affected_metrics']:
                    metrics_impact['strategic_decision_impact'].append({
                        'area': 'product_development',
                        'impact': 'Inconsistent user metrics may misguide product roadmap decisions',
                        'severity': 'high'
                    })
                
                if 'performance_metrics' in metrics_impact['affected_metrics']:
                    metrics_impact['strategic_decision_impact'].append({
                        'area': 'operational_efficiency',
                        'impact': 'Inconsistent performance data may mask operational issues',
                        'severity': 'medium'
                    })
                
                # Convert sets to lists for serialization
                metrics_impact['affected_metrics'] = list(metrics_impact['affected_metrics'])
                
                return metrics_impact
            
            async def store_validation_results(self, results: Dict[str, Any]):
                """Store analytics consistency validation results."""
                await self.redis.setex(
                    'analytics_consistency_validation',
                    3600,
                    json.dumps(results, default=str)
                )
                
                return results
        
        validator = AnalyticsConsistencyValidator(redis_client)
        
        # Mock analytics-focused ReportData definitions
        analytics_report_definitions = [
            ReportDataDefinition(
                name='UserEngagementMetrics',
                module_path='analytics/user_analytics.py',
                fields={
                    'user_count': {'type': 'int', 'required': True},
                    'session_count': {'type': 'int', 'required': True},
                    'avg_session_duration': {'type': 'float', 'required': True},
                    'bounce_rate': {'type': 'float', 'required': True}
                },
                usage_context='user_analytics'
            ),
            ReportDataDefinition(
                name='ConversionMetrics',
                module_path='analytics/conversion_analytics.py',
                fields={
                    'total_visitors': {'type': 'int', 'required': True},
                    'converted_users': {'type': 'int', 'required': True},
                    'conversion_rate': {'type': 'float', 'required': True},
                    'revenue_per_conversion': {'type': 'float', 'required': False}
                },
                usage_context='conversion_analytics'
            ),
            ReportDataDefinition(
                name='PerformanceMetrics',
                module_path='analytics/performance_reporting.py',
                fields={
                    'avg_response_time': {'type': 'float', 'required': True},
                    'error_rate': {'type': 'float', 'required': True},
                    'throughput': {'type': 'int', 'required': True},
                    'uptime_percentage': {'type': 'float', 'required': True}
                },
                usage_context='performance_analytics'
            ),
            # Inconsistent definition for testing
            ReportDataDefinition(
                name='UserEngagementMetrics',
                module_path='reports/user_dashboard.py',
                fields={
                    'user_count': {'type': 'str', 'required': True},  # Type inconsistency
                    'session_count': {'type': 'int', 'required': False},  # Requirement inconsistency
                    'avg_session_duration': {'type': 'float', 'required': True},
                    'bounce_rate': {'type': 'float', 'required': True}
                },
                usage_context='user_analytics'
            )
        ]
        
        # Validate analytics consistency
        validation_results = validator.validate_analytics_consistency(analytics_report_definitions)
        
        # Validate pipeline analysis
        assert validation_results['total_analytics_pipelines'] > 0, (
            "Should identify analytics pipelines"
        )
        
        assert validation_results['inconsistent_pipelines'] > 0, (
            "Should detect inconsistent analytics pipelines"
        )
        
        # Validate consistency violations
        assert len(validation_results['consistency_violations']) > 0, (
            "Should detect consistency violations"
        )
        
        # Check for specific violation types
        violation_types = set(v['type'] for v in validation_results['consistency_violations'])
        assert 'field_type_inconsistency' in violation_types or 'field_requirement_inconsistency' in violation_types, (
            "Should detect field inconsistencies"
        )
        
        # Validate data quality risks
        assert len(validation_results['data_quality_risks']) > 0, (
            "Should identify data quality risks"
        )
        
        # Validate business metrics impact
        metrics_impact = validation_results['business_metrics_impact']
        assert 'affected_metrics' in metrics_impact, "Should identify affected metrics"
        assert 'calculation_reliability' in metrics_impact, "Should assess calculation reliability"
        assert 'strategic_decision_impact' in metrics_impact, "Should assess strategic impact"
        
        # Store validation results
        stored_results = await validator.store_validation_results(validation_results)
        
        assert 'consistency_violations' in stored_results, "Stored results must include violations"
        assert 'business_metrics_impact' in stored_results, "Stored results must include business impact"
        
        # Cleanup
        await redis_client.delete('analytics_consistency_validation')


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_report_data_migration_strategy_validation(self, real_services_fixture):
        """
        Test validation of migration strategy for ReportData consolidation.
        
        OPERATIONAL CRITICAL: Migration strategy ensures safe consolidation
        without disrupting business intelligence and reporting operations.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock migration strategy validator
        class ReportDataMigrationValidator:
            def __init__(self, redis_client):
                self.redis = redis_client
            
            def validate_migration_strategy(
                self, 
                current_definitions: List[ReportDataDefinition],
                consolidation_plan: Dict[str, Any]
            ) -> Dict[str, Any]:
                """Validate migration strategy for ReportData consolidation."""
                validation_result = {
                    'validated_at': asyncio.get_event_loop().time(),
                    'migration_plan': consolidation_plan,
                    'affected_systems': set(),
                    'data_migration_requirements': [],
                    'backward_compatibility_analysis': {},
                    'rollout_phases': [],
                    'risk_mitigation_strategies': [],
                    'business_continuity_plan': {}
                }
                
                # Analyze affected systems
                for definition in current_definitions:
                    if definition.name in consolidation_plan.get('types_to_consolidate', []):
                        system = self._extract_system_from_path(definition.module_path)
                        validation_result['affected_systems'].add(system)
                
                # Generate data migration requirements
                validation_result['data_migration_requirements'] = self._generate_migration_requirements(
                    current_definitions, consolidation_plan
                )
                
                # Analyze backward compatibility
                validation_result['backward_compatibility_analysis'] = self._analyze_backward_compatibility(
                    current_definitions, consolidation_plan
                )
                
                # Design rollout phases
                validation_result['rollout_phases'] = self._design_rollout_phases(
                    validation_result['affected_systems'], consolidation_plan
                )
                
                # Develop risk mitigation strategies
                validation_result['risk_mitigation_strategies'] = self._develop_risk_mitigation(
                    validation_result['data_migration_requirements'],
                    validation_result['backward_compatibility_analysis']
                )
                
                # Create business continuity plan
                validation_result['business_continuity_plan'] = self._create_continuity_plan(
                    validation_result['affected_systems']
                )
                
                # Convert sets to lists for serialization
                validation_result['affected_systems'] = list(validation_result['affected_systems'])
                
                return validation_result
            
            def _extract_system_from_path(self, module_path: str) -> str:
                """Extract system name from module path."""
                if 'analytics' in module_path:
                    return 'analytics_system'
                elif 'scripts' in module_path:
                    return 'status_reporting_system'
                elif 'reports' in module_path:
                    return 'business_reporting_system'
                elif 'netra_backend' in module_path:
                    return 'backend_system'
                else:
                    return 'unknown_system'
            
            def _generate_migration_requirements(
                self, 
                definitions: List[ReportDataDefinition], 
                plan: Dict[str, Any]
            ) -> List[Dict[str, Any]]:
                """Generate data migration requirements."""
                requirements = []
                
                for type_name in plan.get('types_to_consolidate', []):
                    type_definitions = [d for d in definitions if d.name == type_name]
                    
                    if len(type_definitions) > 1:
                        requirements.append({
                            'type_name': type_name,
                            'migration_type': 'schema_unification',
                            'source_schemas': len(type_definitions),
                            'data_transformation_needed': True,
                            'affected_tables': [f"{type_name.lower()}_data"],
                            'estimated_records': 10000,  # Mock estimate
                            'migration_complexity': 'medium'
                        })
                
                # Add cross-system data synchronization requirements
                if len(set(self._extract_system_from_path(d.module_path) for d in definitions)) > 1:
                    requirements.append({
                        'type_name': 'cross_system_sync',
                        'migration_type': 'data_synchronization',
                        'source_systems': list(set(self._extract_system_from_path(d.module_path) for d in definitions)),
                        'sync_frequency': 'real_time',
                        'consistency_guarantees': 'eventual_consistency',
                        'migration_complexity': 'high'
                    })
                
                return requirements
            
            def _analyze_backward_compatibility(
                self, 
                definitions: List[ReportDataDefinition], 
                plan: Dict[str, Any]
            ) -> Dict[str, Any]:
                """Analyze backward compatibility requirements."""
                compatibility_analysis = {
                    'overall_compatibility': 'partial',
                    'breaking_changes': [],
                    'deprecated_fields': [],
                    'new_fields': [],
                    'compatibility_layers_needed': []
                }
                
                for type_name in plan.get('types_to_consolidate', []):
                    type_definitions = [d for d in definitions if d.name == type_name]
                    
                    if len(type_definitions) > 1:
                        # Find field differences
                        all_fields = set()
                        common_fields = None
                        
                        for definition in type_definitions:
                            definition_fields = set(definition.fields.keys())
                            all_fields.update(definition_fields)
                            
                            if common_fields is None:
                                common_fields = definition_fields
                            else:
                                common_fields &= definition_fields
                        
                        # Fields that exist in some but not all definitions
                        optional_fields = all_fields - common_fields
                        
                        for field in optional_fields:
                            compatibility_analysis['deprecated_fields'].append({
                                'type_name': type_name,
                                'field_name': field,
                                'reason': 'Not present in all schema variants',
                                'migration_strategy': 'Add with default value'
                            })
                        
                        # Need compatibility layer for each variant
                        compatibility_analysis['compatibility_layers_needed'].append({
                            'type_name': type_name,
                            'layer_type': 'schema_adapter',
                            'purpose': f'Adapt between {len(type_definitions)} schema variants',
                            'implementation_complexity': 'medium'
                        })
                
                return compatibility_analysis
            
            def _design_rollout_phases(self, affected_systems: set, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
                """Design phased rollout strategy."""
                phases = []
                
                # Phase 1: Schema consolidation
                phases.append({
                    'phase': 1,
                    'name': 'Schema Consolidation',
                    'duration': '2 weeks',
                    'activities': [
                        'Create unified ReportData schemas',
                        'Implement backward compatibility layers',
                        'Unit test new schemas'
                    ],
                    'affected_systems': list(affected_systems),
                    'rollback_plan': 'Revert to original schemas',
                    'success_criteria': ['All schemas compile', 'Unit tests pass']
                })
                
                # Phase 2: System-by-system migration
                for i, system in enumerate(sorted(affected_systems)):
                    phases.append({
                        'phase': i + 2,
                        'name': f'Migrate {system}',
                        'duration': '1 week',
                        'activities': [
                            f'Update {system} to use unified schemas',
                            f'Migrate {system} data',
                            f'Validate {system} reports'
                        ],
                        'affected_systems': [system],
                        'dependencies': ['Phase 1'],
                        'rollback_plan': f'Restore {system} to original schema',
                        'success_criteria': [f'{system} reports match baseline', 'No data loss']
                    })
                
                # Final phase: Cleanup
                phases.append({
                    'phase': len(phases) + 1,
                    'name': 'Legacy Cleanup',
                    'duration': '1 week',
                    'activities': [
                        'Remove deprecated schemas',
                        'Clean up compatibility layers',
                        'Update documentation'
                    ],
                    'affected_systems': list(affected_systems),
                    'dependencies': [f'Phase {i}' for i in range(2, len(affected_systems) + 2)],
                    'rollback_plan': 'Maintain compatibility layers if needed',
                    'success_criteria': ['No references to old schemas', 'Documentation updated']
                })
                
                return phases
            
            def _develop_risk_mitigation(
                self, 
                migration_requirements: List[Dict[str, Any]], 
                compatibility_analysis: Dict[str, Any]
            ) -> List[Dict[str, Any]]:
                """Develop risk mitigation strategies."""
                strategies = [
                    {
                        'risk': 'Data loss during migration',
                        'mitigation': 'Full data backup before each phase',
                        'responsibility': 'Infrastructure team',
                        'validation': 'Automated backup verification'
                    },
                    {
                        'risk': 'Report calculation errors',
                        'mitigation': 'Parallel execution with result comparison',
                        'responsibility': 'Analytics team',
                        'validation': 'Statistical comparison of report outputs'
                    },
                    {
                        'risk': 'Business intelligence disruption',
                        'mitigation': 'Maintain dual systems during transition',
                        'responsibility': 'Business intelligence team',
                        'validation': 'Dashboard uptime monitoring'
                    },
                    {
                        'risk': 'Schema compatibility breaks',
                        'mitigation': 'Comprehensive compatibility testing',
                        'responsibility': 'Development team',
                        'validation': 'Automated compatibility test suite'
                    }
                ]
                
                return strategies
            
            def _create_continuity_plan(self, affected_systems: set) -> Dict[str, Any]:
                """Create business continuity plan."""
                continuity_plan = {
                    'business_impact_assessment': {
                        'critical_reports': [
                            'Daily user metrics',
                            'Revenue analytics', 
                            'Operational dashboards'
                        ],
                        'maximum_acceptable_downtime': '4 hours',
                        'data_recovery_time_objective': '1 hour'
                    },
                    'contingency_procedures': [
                        {
                            'scenario': 'Migration failure',
                            'procedure': 'Rollback to previous version',
                            'estimated_time': '30 minutes',
                            'responsible_team': 'Infrastructure'
                        },
                        {
                            'scenario': 'Data corruption',
                            'procedure': 'Restore from backup',
                            'estimated_time': '2 hours',
                            'responsible_team': 'Database'
                        },
                        {
                            'scenario': 'Report calculation errors',
                            'procedure': 'Switch to backup analytics system',
                            'estimated_time': '15 minutes',
                            'responsible_team': 'Analytics'
                        }
                    ],
                    'communication_plan': {
                        'stakeholders': ['Business intelligence team', 'Executive dashboard users', 'Analytics consumers'],
                        'notification_channels': ['Email', 'Slack', 'Status page'],
                        'update_frequency': 'Every 30 minutes during migration'
                    }
                }
                
                return continuity_plan
            
            async def store_migration_validation(self, validation: Dict[str, Any]):
                """Store migration strategy validation."""
                await self.redis.setex(
                    'report_data_migration_validation',
                    3600,
                    json.dumps(validation, default=str)
                )
                
                return validation
        
        validator = ReportDataMigrationValidator(redis_client)
        
        # Mock current definitions and consolidation plan
        current_definitions = [
            ReportDataDefinition(
                name='BusinessMetrics',
                module_path='analytics/business_analytics.py',
                fields={'revenue': {'type': 'float', 'required': True}},
                usage_context='business_reporting'
            ),
            ReportDataDefinition(
                name='BusinessMetrics',
                module_path='scripts/business_status.py',
                fields={'revenue': {'type': 'float', 'required': True}},
                usage_context='status_reporting'
            )
        ]
        
        consolidation_plan = {
            'types_to_consolidate': ['BusinessMetrics'],
            'target_location': 'shared/types/report_data.py',
            'unified_schema': {
                'BusinessMetrics': {
                    'revenue': {'type': 'float', 'required': True},
                    'period': {'type': 'str', 'required': True}
                }
            }
        }
        
        # Validate migration strategy
        validation_results = validator.validate_migration_strategy(current_definitions, consolidation_plan)
        
        # Validate migration analysis
        assert len(validation_results['affected_systems']) > 0, (
            "Should identify affected systems"
        )
        
        assert len(validation_results['data_migration_requirements']) > 0, (
            "Should define data migration requirements"
        )
        
        # Validate backward compatibility analysis
        compatibility = validation_results['backward_compatibility_analysis']
        assert 'overall_compatibility' in compatibility, "Should assess overall compatibility"
        assert 'compatibility_layers_needed' in compatibility, "Should identify compatibility needs"
        
        # Validate rollout phases
        assert len(validation_results['rollout_phases']) > 0, (
            "Should define rollout phases"
        )
        
        # Check for required phases
        phase_names = set(phase['name'] for phase in validation_results['rollout_phases'])
        assert 'Schema Consolidation' in phase_names, "Should include schema consolidation phase"
        assert 'Legacy Cleanup' in phase_names, "Should include cleanup phase"
        
        # Validate risk mitigation
        assert len(validation_results['risk_mitigation_strategies']) > 0, (
            "Should provide risk mitigation strategies"
        )
        
        # Validate business continuity plan
        continuity_plan = validation_results['business_continuity_plan']
        assert 'business_impact_assessment' in continuity_plan, "Should assess business impact"
        assert 'contingency_procedures' in continuity_plan, "Should define contingency procedures"
        assert 'communication_plan' in continuity_plan, "Should include communication plan"
        
        # Store migration validation
        stored_results = await validator.store_migration_validation(validation_results)
        
        assert 'rollout_phases' in stored_results, "Stored results must include rollout phases"
        assert 'risk_mitigation_strategies' in stored_results, "Stored results must include risk mitigation"
        
        # Cleanup
        await redis_client.delete('report_data_migration_validation')