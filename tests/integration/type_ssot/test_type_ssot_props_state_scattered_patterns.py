"""
Test Props and State Definition Scattered Pattern SSOT Violations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Consolidate scattered Props and State definitions for maintainability  
- Value Impact: Reduces code duplication and prevents inconsistent component behavior
- Strategic Impact: Component consistency directly impacts user experience quality

CRITICAL: Props and State definitions scattered across multiple files violate SSOT
principles and create inconsistent component behavior. This breaks UI reliability
and creates maintenance overhead that slows feature development.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List, Optional, Union, Set
from dataclasses import dataclass, field
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture


@dataclass
class ComponentPropsDefinition:
    """Props definition for a React component."""
    component_name: str
    file_path: str
    props: Dict[str, Dict[str, Any]]
    required_props: Set[str] = field(default_factory=set)
    optional_props: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        for prop_name, prop_def in self.props.items():
            if prop_def.get('required', False):
                self.required_props.add(prop_name)
            else:
                self.optional_props.add(prop_name)


@dataclass
class ComponentStateDefinition:
    """State definition for a React component."""
    component_name: str
    file_path: str
    state: Dict[str, Dict[str, Any]]
    initial_state: Dict[str, Any] = field(default_factory=dict)


class TestPropsStateScatteredPatterns(BaseIntegrationTest):
    """Integration tests for Props and State definition consolidation."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_component_props_duplication_detection(self, real_services_fixture):
        """
        Test detection of duplicated Props definitions across components.
        
        MISSION CRITICAL: Duplicated Props definitions create inconsistent
        component behavior and maintenance overhead.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock component props analyzer
        class ComponentPropsAnalyzer:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.detected_duplications = []
            
            def analyze_props_definitions(self, components: List[ComponentPropsDefinition]) -> Dict[str, Any]:
                """Analyze components for Props definition duplications."""
                analysis_result = {
                    'analyzed_at': asyncio.get_event_loop().time(),
                    'total_components': len(components),
                    'total_props_definitions': 0,
                    'duplicated_props': {},
                    'scattered_patterns': [],
                    'consolidation_opportunities': []
                }
                
                # Build prop usage map
                prop_usage_map = {}
                
                for component in components:
                    analysis_result['total_props_definitions'] += len(component.props)
                    
                    for prop_name, prop_def in component.props.items():
                        if prop_name not in prop_usage_map:
                            prop_usage_map[prop_name] = []
                        
                        prop_usage_map[prop_name].append({
                            'component': component.component_name,
                            'file_path': component.file_path,
                            'definition': prop_def,
                            'required': prop_name in component.required_props
                        })
                
                # Identify duplicated props
                for prop_name, usages in prop_usage_map.items():
                    if len(usages) > 1:
                        # Check if definitions are actually different
                        unique_definitions = set()
                        for usage in usages:
                            # Create comparable definition
                            comparable_def = {
                                'type': usage['definition'].get('type'),
                                'required': usage['required'],
                                'default': usage['definition'].get('default')
                            }
                            unique_definitions.add(json.dumps(comparable_def, sort_keys=True))
                        
                        if len(unique_definitions) > 1:
                            # Multiple different definitions for same prop name
                            analysis_result['duplicated_props'][prop_name] = {
                                'usage_count': len(usages),
                                'unique_definitions': len(unique_definitions),
                                'usages': usages,
                                'severity': 'high' if len(usages) > 3 else 'medium'
                            }
                        elif len(usages) > 2:
                            # Same definition repeated multiple times
                            analysis_result['scattered_patterns'].append({
                                'prop_name': prop_name,
                                'definition': usages[0]['definition'],
                                'repetition_count': len(usages),
                                'components': [u['component'] for u in usages],
                                'consolidation_potential': 'high'
                            })
                
                # Identify consolidation opportunities
                for pattern in analysis_result['scattered_patterns']:
                    if pattern['repetition_count'] >= 3:
                        analysis_result['consolidation_opportunities'].append({
                            'type': 'shared_props_interface',
                            'prop_name': pattern['prop_name'],
                            'affected_components': pattern['components'],
                            'potential_savings': f"{pattern['repetition_count']} definitions -> 1 shared interface"
                        })
                
                return analysis_result
            
            async def store_analysis_results(self, results: Dict[str, Any]):
                """Store Props analysis results."""
                await self.redis.setex(
                    'props_duplication_analysis',
                    3600,
                    json.dumps(results)
                )
                
                return results
        
        analyzer = ComponentPropsAnalyzer(redis_client)
        
        # Mock component definitions with Props duplications
        test_components = [
            ComponentPropsDefinition(
                component_name='UserCard',
                file_path='/frontend/components/UserCard.tsx',
                props={
                    'user_id': {'type': 'string', 'required': True},
                    'name': {'type': 'string', 'required': True},
                    'email': {'type': 'string', 'required': True},
                    'avatar_url': {'type': 'string', 'required': False, 'default': None},
                    'is_active': {'type': 'boolean', 'required': False, 'default': True}
                }
            ),
            ComponentPropsDefinition(
                component_name='UserProfile',
                file_path='/frontend/pages/UserProfile.tsx',
                props={
                    'user_id': {'type': 'string', 'required': True},  # Duplicate
                    'name': {'type': 'string', 'required': True},     # Duplicate
                    'email': {'type': 'string', 'required': True},   # Duplicate
                    'bio': {'type': 'string', 'required': False},
                    'preferences': {'type': 'object', 'required': False}
                }
            ),
            ComponentPropsDefinition(
                component_name='UserList',
                file_path='/frontend/components/UserList.tsx',
                props={
                    'users': {'type': 'array', 'required': True},
                    'on_user_select': {'type': 'function', 'required': True},
                    'loading': {'type': 'boolean', 'required': False, 'default': False}
                }
            ),
            ComponentPropsDefinition(
                component_name='ThreadCard', 
                file_path='/frontend/components/ThreadCard.tsx',
                props={
                    'thread_id': {'type': 'string', 'required': True},
                    'title': {'type': 'string', 'required': True},
                    'user_id': {'type': 'string', 'required': True},  # Duplicate
                    'created_at': {'type': 'string', 'required': True},
                    'is_active': {'type': 'boolean', 'required': False, 'default': True}  # Different default
                }
            ),
            ComponentPropsDefinition(
                component_name='MessageBubble',
                file_path='/frontend/components/MessageBubble.tsx', 
                props={
                    'message_id': {'type': 'string', 'required': True},
                    'content': {'type': 'string', 'required': True},
                    'user_id': {'type': 'string', 'required': True},  # Duplicate
                    'timestamp': {'type': 'string', 'required': True},
                    'is_edited': {'type': 'boolean', 'required': False, 'default': False}
                }
            )
        ]
        
        # Analyze Props duplications
        analysis_results = analyzer.analyze_props_definitions(test_components)
        
        # Validate detection of Props duplications
        assert len(analysis_results['duplicated_props']) > 0, (
            "Should detect Props duplications across components"
        )
        
        # Validate specific duplications
        assert 'user_id' in analysis_results['duplicated_props'], (
            "Should detect user_id Props duplication"
        )
        
        user_id_duplication = analysis_results['duplicated_props']['user_id']
        assert user_id_duplication['usage_count'] >= 4, (
            f"user_id should be used in at least 4 components, found {user_id_duplication['usage_count']}"
        )
        
        # Validate scattered patterns detection
        assert len(analysis_results['scattered_patterns']) > 0, (
            "Should detect scattered Props patterns"
        )
        
        # Validate consolidation opportunities
        assert len(analysis_result := analysis_results['consolidation_opportunities']) > 0, (
            "Should identify consolidation opportunities"
        )
        
        # Check for shared interface opportunities
        shared_interface_opportunities = [
            opp for opp in analysis_results['consolidation_opportunities']
            if opp['type'] == 'shared_props_interface'
        ]
        
        assert len(shared_interface_opportunities) > 0, (
            "Should identify shared Props interface opportunities"
        )
        
        # Store and validate results
        stored_results = await analyzer.store_analysis_results(analysis_results)
        
        assert stored_results['total_components'] == len(test_components), (
            "Analysis must cover all test components"
        )
        
        # Cleanup
        await redis_client.delete('props_duplication_analysis')


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_component_state_consolidation_validation(self, real_services_fixture):
        """
        Test validation of component State definition consolidation opportunities.
        
        GOLDEN PATH CRITICAL: Consistent State management prevents bugs and
        improves component reliability across the chat interface.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock state consolidation validator
        class StateConsolidationValidator:
            def __init__(self, redis_client):
                self.redis = redis_client
            
            def analyze_state_patterns(self, components: List[ComponentStateDefinition]) -> Dict[str, Any]:
                """Analyze component State patterns for consolidation opportunities."""
                analysis_result = {
                    'analyzed_at': asyncio.get_event_loop().time(),
                    'total_components': len(components),
                    'total_state_fields': 0,
                    'common_state_patterns': {},
                    'state_duplications': [],
                    'consolidation_recommendations': []
                }
                
                # Build state field usage map
                state_field_map = {}
                
                for component in components:
                    analysis_result['total_state_fields'] += len(component.state)
                    
                    for state_field, field_def in component.state.items():
                        if state_field not in state_field_map:
                            state_field_map[state_field] = []
                        
                        state_field_map[state_field].append({
                            'component': component.component_name,
                            'file_path': component.file_path,
                            'definition': field_def,
                            'initial_value': component.initial_state.get(state_field)
                        })
                
                # Identify common state patterns
                for field_name, usages in state_field_map.items():
                    if len(usages) > 1:
                        # Analyze consistency across usages
                        types = set(usage['definition'].get('type') for usage in usages)
                        initial_values = set(
                            str(usage['initial_value']) for usage in usages 
                            if usage['initial_value'] is not None
                        )
                        
                        if len(types) == 1 and len(initial_values) <= 1:
                            # Consistent usage pattern
                            analysis_result['common_state_patterns'][field_name] = {
                                'usage_count': len(usages),
                                'type': list(types)[0],
                                'consistent': True,
                                'components': [u['component'] for u in usages],
                                'consolidation_potential': 'high' if len(usages) >= 3 else 'medium'
                            }
                        else:
                            # Inconsistent usage
                            analysis_result['state_duplications'].append({
                                'field_name': field_name,
                                'usage_count': len(usages),
                                'type_variations': list(types),
                                'initial_value_variations': list(initial_values),
                                'components': [u['component'] for u in usages],
                                'severity': 'high'
                            })
                
                # Generate consolidation recommendations
                for field_name, pattern in analysis_result['common_state_patterns'].items():
                    if pattern['usage_count'] >= 3:
                        analysis_result['consolidation_recommendations'].append({
                            'type': 'shared_state_hook',
                            'field_name': field_name,
                            'affected_components': pattern['components'],
                            'recommendation': f"Create shared hook for {field_name} state management",
                            'benefit': f"Reduce {pattern['usage_count']} duplicate state definitions"
                        })
                
                # Identify complex state consolidation opportunities
                loading_states = [
                    field for field in state_field_map 
                    if 'loading' in field.lower() and len(state_field_map[field]) > 1
                ]
                
                if loading_states:
                    analysis_result['consolidation_recommendations'].append({
                        'type': 'loading_state_pattern',
                        'fields': loading_states,
                        'recommendation': 'Consolidate loading states into unified loading manager',
                        'benefit': 'Consistent loading UX across components'
                    })
                
                error_states = [
                    field for field in state_field_map
                    if 'error' in field.lower() and len(state_field_map[field]) > 1
                ]
                
                if error_states:
                    analysis_result['consolidation_recommendations'].append({
                        'type': 'error_state_pattern',
                        'fields': error_states,
                        'recommendation': 'Consolidate error states into unified error handler',
                        'benefit': 'Consistent error handling across components'
                    })
                
                return analysis_result
            
            def validate_state_consolidation_benefits(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
                """Validate benefits of state consolidation."""
                validation_result = {
                    'validated_at': asyncio.get_event_loop().time(),
                    'total_recommendations': len(analysis['consolidation_recommendations']),
                    'estimated_code_reduction': 0,
                    'consistency_improvements': 0,
                    'maintenance_benefits': [],
                    'implementation_complexity': {}
                }
                
                for recommendation in analysis['consolidation_recommendations']:
                    rec_type = recommendation['type']
                    
                    if rec_type == 'shared_state_hook':
                        # Estimate code reduction
                        affected_count = len(recommendation['affected_components'])
                        validation_result['estimated_code_reduction'] += (affected_count - 1) * 10  # ~10 lines per hook
                        validation_result['consistency_improvements'] += 1
                        
                        validation_result['implementation_complexity'][rec_type] = 'medium'
                        validation_result['maintenance_benefits'].append({
                            'type': 'reduced_duplication',
                            'field': recommendation['field_name'],
                            'impact': f"Single source of truth for {recommendation['field_name']} state"
                        })
                    
                    elif rec_type in ['loading_state_pattern', 'error_state_pattern']:
                        # Cross-cutting concern consolidation
                        validation_result['estimated_code_reduction'] += 50  # Larger consolidation
                        validation_result['consistency_improvements'] += 5
                        
                        validation_result['implementation_complexity'][rec_type] = 'high'
                        validation_result['maintenance_benefits'].append({
                            'type': 'unified_behavior',
                            'pattern': rec_type,
                            'impact': recommendation['benefit']
                        })
                
                return validation_result
            
            async def store_consolidation_analysis(self, analysis: Dict[str, Any], validation: Dict[str, Any]):
                """Store state consolidation analysis and validation."""
                combined_results = {
                    'analysis': analysis,
                    'validation': validation,
                    'stored_at': asyncio.get_event_loop().time()
                }
                
                await self.redis.setex(
                    'state_consolidation_analysis',
                    3600,
                    json.dumps(combined_results)
                )
                
                return combined_results
        
        validator = StateConsolidationValidator(redis_client)
        
        # Mock component state definitions
        test_state_components = [
            ComponentStateDefinition(
                component_name='ChatInterface',
                file_path='/frontend/components/ChatInterface.tsx',
                state={
                    'messages': {'type': 'array'},
                    'loading': {'type': 'boolean'},
                    'error': {'type': 'string | null'},
                    'input_value': {'type': 'string'},
                    'websocket_connected': {'type': 'boolean'}
                },
                initial_state={
                    'messages': [],
                    'loading': False,
                    'error': None,
                    'input_value': '',
                    'websocket_connected': False
                }
            ),
            ComponentStateDefinition(
                component_name='ThreadList',
                file_path='/frontend/components/ThreadList.tsx',
                state={
                    'threads': {'type': 'array'},
                    'loading': {'type': 'boolean'},  # Duplicate
                    'error': {'type': 'string | null'},  # Duplicate
                    'selected_thread': {'type': 'string | null'},
                    'search_query': {'type': 'string'}
                },
                initial_state={
                    'threads': [],
                    'loading': False,
                    'error': None,
                    'selected_thread': None,
                    'search_query': ''
                }
            ),
            ComponentStateDefinition(
                component_name='AgentSelector',
                file_path='/frontend/components/AgentSelector.tsx',
                state={
                    'agents': {'type': 'array'},
                    'loading': {'type': 'boolean'},  # Duplicate
                    'error': {'type': 'string | null'},  # Duplicate
                    'selected_agent': {'type': 'string | null'},
                    'filter_type': {'type': 'string'}
                },
                initial_state={
                    'agents': [],
                    'loading': False,
                    'error': None,
                    'selected_agent': None,
                    'filter_type': 'all'
                }
            ),
            ComponentStateDefinition(
                component_name='UserSettings',
                file_path='/frontend/components/UserSettings.tsx',
                state={
                    'settings': {'type': 'object'},
                    'saving': {'type': 'boolean'},  # Different loading pattern
                    'save_error': {'type': 'string | null'},  # Different error pattern
                    'modified': {'type': 'boolean'}
                },
                initial_state={
                    'settings': {},
                    'saving': False,
                    'save_error': None,
                    'modified': False
                }
            )
        ]
        
        # Analyze state patterns
        analysis_results = validator.analyze_state_patterns(test_state_components)
        
        # Validate common state pattern detection
        assert len(analysis_results['common_state_patterns']) > 0, (
            "Should detect common state patterns"
        )
        
        # Validate specific common patterns
        assert 'loading' in analysis_results['common_state_patterns'], (
            "Should detect loading state pattern"
        )
        
        loading_pattern = analysis_results['common_state_patterns']['loading']
        assert loading_pattern['usage_count'] >= 3, (
            f"Loading pattern should be used in at least 3 components, found {loading_pattern['usage_count']}"
        )
        assert loading_pattern['consistent'] is True, (
            "Loading pattern should be consistent across components"
        )
        
        # Validate consolidation recommendations
        assert len(analysis_results['consolidation_recommendations']) > 0, (
            "Should generate consolidation recommendations"
        )
        
        # Check for specific recommendation types
        recommendation_types = set(
            rec['type'] for rec in analysis_results['consolidation_recommendations']
        )
        
        assert 'shared_state_hook' in recommendation_types, (
            "Should recommend shared state hooks"
        )
        
        # Validate consolidation benefits
        validation_results = validator.validate_state_consolidation_benefits(analysis_results)
        
        assert validation_results['estimated_code_reduction'] > 0, (
            "Should estimate positive code reduction"
        )
        assert validation_results['consistency_improvements'] > 0, (
            "Should identify consistency improvements"
        )
        assert len(validation_results['maintenance_benefits']) > 0, (
            "Should identify maintenance benefits"
        )
        
        # Store analysis and validation
        combined_results = await validator.store_consolidation_analysis(
            analysis_results, validation_results
        )
        
        assert 'analysis' in combined_results, "Combined results must include analysis"
        assert 'validation' in combined_results, "Combined results must include validation"
        
        # Cleanup
        await redis_client.delete('state_consolidation_analysis')


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_props_state_refactoring_impact_analysis(self, real_services_fixture):
        """
        Test impact analysis for Props and State refactoring initiatives.
        
        BUSINESS CRITICAL: Refactoring impact analysis ensures safe consolidation
        without breaking existing functionality or user experience.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock refactoring impact analyzer
        class RefactoringImpactAnalyzer:
            def __init__(self, redis_client):
                self.redis = redis_client
            
            def analyze_refactoring_impact(
                self, 
                components: List[Union[ComponentPropsDefinition, ComponentStateDefinition]],
                consolidation_plan: Dict[str, Any]
            ) -> Dict[str, Any]:
                """Analyze impact of Props/State refactoring."""
                impact_analysis = {
                    'analyzed_at': asyncio.get_event_loop().time(),
                    'consolidation_plan': consolidation_plan,
                    'affected_components': set(),
                    'breaking_changes': [],
                    'migration_complexity': {},
                    'testing_requirements': [],
                    'rollout_strategy': {},
                    'risk_assessment': {}
                }
                
                # Analyze component impact
                for component in components:
                    component_affected = False
                    
                    if isinstance(component, ComponentPropsDefinition):
                        # Check if component's props are in consolidation plan
                        for prop_name in component.props:
                            if prop_name in consolidation_plan.get('props_to_consolidate', []):
                                component_affected = True
                                impact_analysis['affected_components'].add(component.component_name)
                                break
                    
                    elif isinstance(component, ComponentStateDefinition):
                        # Check if component's state is in consolidation plan
                        for state_field in component.state:
                            if state_field in consolidation_plan.get('state_to_consolidate', []):
                                component_affected = True
                                impact_analysis['affected_components'].add(component.component_name)
                                break
                    
                    if component_affected:
                        # Analyze migration complexity for this component
                        complexity_score = self._calculate_migration_complexity(component, consolidation_plan)
                        impact_analysis['migration_complexity'][component.component_name] = complexity_score
                
                # Identify breaking changes
                for prop_name in consolidation_plan.get('props_to_consolidate', []):
                    # Check for type changes or requirement changes
                    prop_usages = self._find_prop_usages(components, prop_name)
                    if self._has_incompatible_definitions(prop_usages):
                        impact_analysis['breaking_changes'].append({
                            'type': 'props_incompatibility',
                            'prop_name': prop_name,
                            'affected_components': [usage['component'] for usage in prop_usages],
                            'mitigation': 'Type union or migration adapter required'
                        })
                
                # Generate testing requirements
                impact_analysis['testing_requirements'] = [
                    {
                        'type': 'unit_tests',
                        'scope': 'All affected components',
                        'priority': 'high',
                        'effort': 'medium'
                    },
                    {
                        'type': 'integration_tests',
                        'scope': 'Component interaction with shared interfaces',
                        'priority': 'high',
                        'effort': 'high'
                    },
                    {
                        'type': 'visual_regression',
                        'scope': 'UI consistency validation',
                        'priority': 'medium',
                        'effort': 'medium'
                    }
                ]
                
                # Develop rollout strategy
                component_count = len(impact_analysis['affected_components'])
                if component_count <= 3:
                    impact_analysis['rollout_strategy'] = {
                        'approach': 'big_bang',
                        'phases': 1,
                        'estimated_duration': '1 sprint',
                        'risk_level': 'low'
                    }
                elif component_count <= 8:
                    impact_analysis['rollout_strategy'] = {
                        'approach': 'phased',
                        'phases': 2,
                        'estimated_duration': '2 sprints',
                        'risk_level': 'medium'
                    }
                else:
                    impact_analysis['rollout_strategy'] = {
                        'approach': 'gradual',
                        'phases': 3,
                        'estimated_duration': '3-4 sprints',
                        'risk_level': 'high'
                    }
                
                # Risk assessment
                impact_analysis['risk_assessment'] = {
                    'overall_risk': 'medium',
                    'technical_risks': [
                        'Type incompatibilities between consolidated interfaces',
                        'Runtime errors from missing prop validations',
                        'State update conflicts in shared hooks'
                    ],
                    'business_risks': [
                        'Temporary UI inconsistencies during migration',
                        'Potential user experience disruptions',
                        'Development velocity slowdown during transition'
                    ],
                    'mitigation_strategies': [
                        'Comprehensive test coverage before refactoring',
                        'Gradual rollout with feature flags',
                        'Runtime prop validation in development',
                        'Automated visual regression testing'
                    ]
                }
                
                return impact_analysis
            
            def _calculate_migration_complexity(
                self, 
                component: Union[ComponentPropsDefinition, ComponentStateDefinition],
                consolidation_plan: Dict[str, Any]
            ) -> Dict[str, Any]:
                """Calculate migration complexity for a component."""
                complexity = {
                    'score': 0,
                    'factors': [],
                    'level': 'low'
                }
                
                if isinstance(component, ComponentPropsDefinition):
                    affected_props = [
                        prop for prop in component.props
                        if prop in consolidation_plan.get('props_to_consolidate', [])
                    ]
                    
                    complexity['score'] += len(affected_props) * 2
                    complexity['factors'].append(f"{len(affected_props)} props affected")
                    
                    # Check for required props
                    required_affected = len(component.required_props & set(affected_props))
                    if required_affected > 0:
                        complexity['score'] += required_affected * 3
                        complexity['factors'].append(f"{required_affected} required props affected")
                
                elif isinstance(component, ComponentStateDefinition):
                    affected_state = [
                        state for state in component.state
                        if state in consolidation_plan.get('state_to_consolidate', [])
                    ]
                    
                    complexity['score'] += len(affected_state) * 3
                    complexity['factors'].append(f"{len(affected_state)} state fields affected")
                
                # Determine complexity level
                if complexity['score'] <= 5:
                    complexity['level'] = 'low'
                elif complexity['score'] <= 15:
                    complexity['level'] = 'medium'
                else:
                    complexity['level'] = 'high'
                
                return complexity
            
            def _find_prop_usages(self, components: List, prop_name: str) -> List[Dict[str, Any]]:
                """Find all usages of a specific prop."""
                usages = []
                for component in components:
                    if isinstance(component, ComponentPropsDefinition) and prop_name in component.props:
                        usages.append({
                            'component': component.component_name,
                            'definition': component.props[prop_name],
                            'required': prop_name in component.required_props
                        })
                return usages
            
            def _has_incompatible_definitions(self, usages: List[Dict[str, Any]]) -> bool:
                """Check if prop usages have incompatible definitions."""
                if len(usages) <= 1:
                    return False
                
                types = set(usage['definition'].get('type') for usage in usages)
                requirements = set(usage['required'] for usage in usages)
                
                return len(types) > 1 or len(requirements) > 1
            
            async def store_impact_analysis(self, analysis: Dict[str, Any]):
                """Store refactoring impact analysis."""
                # Convert sets to lists for JSON serialization
                serializable_analysis = json.loads(json.dumps(analysis, default=str))
                
                await self.redis.setex(
                    'refactoring_impact_analysis',
                    3600,
                    json.dumps(serializable_analysis)
                )
                
                return serializable_analysis
        
        analyzer = RefactoringImpactAnalyzer(redis_client)
        
        # Combined test components (both Props and State)
        all_components = [
            ComponentPropsDefinition(
                component_name='UserCard',
                file_path='/frontend/components/UserCard.tsx',
                props={
                    'user_id': {'type': 'string', 'required': True},
                    'name': {'type': 'string', 'required': True},
                    'on_click': {'type': 'function', 'required': False}
                }
            ),
            ComponentStateDefinition(
                component_name='ChatInterface',
                file_path='/frontend/components/ChatInterface.tsx',
                state={
                    'loading': {'type': 'boolean'},
                    'error': {'type': 'string | null'},
                    'messages': {'type': 'array'}
                }
            )
        ]
        
        # Mock consolidation plan
        consolidation_plan = {
            'props_to_consolidate': ['user_id', 'name'],
            'state_to_consolidate': ['loading', 'error'],
            'target_interfaces': {
                'UserProps': ['user_id', 'name'],
                'LoadingErrorState': ['loading', 'error']
            }
        }
        
        # Analyze refactoring impact
        impact_analysis = analyzer.analyze_refactoring_impact(all_components, consolidation_plan)
        
        # Validate impact analysis
        assert len(impact_analysis['affected_components']) > 0, (
            "Should identify affected components"
        )
        
        assert 'UserCard' in impact_analysis['affected_components'], (
            "UserCard should be affected by props consolidation"
        )
        
        assert 'ChatInterface' in impact_analysis['affected_components'], (
            "ChatInterface should be affected by state consolidation"
        )
        
        # Validate migration complexity analysis
        assert len(impact_analysis['migration_complexity']) > 0, (
            "Should analyze migration complexity"
        )
        
        # Validate testing requirements
        assert len(impact_analysis['testing_requirements']) > 0, (
            "Should define testing requirements"
        )
        
        test_types = set(req['type'] for req in impact_analysis['testing_requirements'])
        assert 'unit_tests' in test_types, "Should require unit tests"
        assert 'integration_tests' in test_types, "Should require integration tests"
        
        # Validate rollout strategy
        assert 'rollout_strategy' in impact_analysis, (
            "Should define rollout strategy"
        )
        
        rollout = impact_analysis['rollout_strategy']
        assert rollout['approach'] in ['big_bang', 'phased', 'gradual'], (
            "Should define valid rollout approach"
        )
        assert 'estimated_duration' in rollout, "Should estimate duration"
        assert 'risk_level' in rollout, "Should assess risk level"
        
        # Validate risk assessment
        assert 'risk_assessment' in impact_analysis, (
            "Should include risk assessment"
        )
        
        risk_assessment = impact_analysis['risk_assessment']
        assert 'technical_risks' in risk_assessment, "Should identify technical risks"
        assert 'business_risks' in risk_assessment, "Should identify business risks"
        assert 'mitigation_strategies' in risk_assessment, "Should provide mitigation strategies"
        
        # Store impact analysis
        stored_analysis = await analyzer.store_impact_analysis(impact_analysis)
        
        assert 'analyzed_at' in stored_analysis, "Stored analysis must include timestamp"
        assert 'consolidation_plan' in stored_analysis, "Stored analysis must include consolidation plan"
        
        # Cleanup
        await redis_client.delete('refactoring_impact_analysis')