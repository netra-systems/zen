"""
Context-Aware Fallback Handler for AI Slop Prevention
Replaces generic error messages with informative, actionable fallbacks
"""

import traceback
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
import json
import re
from app.logging_config import central_logger as logger



class FallbackContext(Enum):
    """Types of fallback contexts"""
    TRIAGE_FAILURE = "triage_failure"
    DATA_FAILURE = "data_failure"
    OPTIMIZATION_FAILURE = "optimization_failure"
    ACTION_FAILURE = "action_failure"
    REPORT_FAILURE = "report_failure"
    LLM_FAILURE = "llm_failure"
    VALIDATION_FAILURE = "validation_failure"
    GENERAL_FAILURE = "general_failure"


@dataclass
class FallbackMetadata:
    """Metadata for fallback generation"""
    error_type: str
    error_message: str
    agent_name: Optional[str] = None
    user_input: Optional[str] = None
    partial_data: Optional[Dict[str, Any]] = None
    attempted_operations: Optional[List[str]] = None
    stacktrace: Optional[str] = None


class FallbackHandler:
    """Handler for generating context-aware fallback responses"""
    
    def __init__(self):
        """Initialize the fallback handler with templates"""
        self.templates = self._initialize_templates()
        self.domain_detection_keywords = {
            'model_optimization': ['model', 'optimize', 'latency', 'throughput', 'inference'],
            'training': ['train', 'fine-tune', 'dataset', 'epochs', 'batch'],
            'deployment': ['deploy', 'production', 'scale', 'serve', 'endpoint'],
            'cost': ['cost', 'price', 'budget', 'expense', 'billing'],
            'performance': ['performance', 'speed', 'efficiency', 'benchmark'],
            'debugging': ['debug', 'error', 'issue', 'problem', 'fix'],
            'architecture': ['architecture', 'design', 'structure', 'component'],
            'data': ['data', 'dataset', 'preprocessing', 'pipeline']
        }
    
    def _initialize_templates(self) -> Dict[FallbackContext, str]:
        """Initialize fallback templates for different contexts"""
        return {
            FallbackContext.TRIAGE_FAILURE: """
I encountered an issue while analyzing your request: {error_reason}

Based on partial analysis, your request appears to be related to {detected_domain}.

**What I was able to determine:**
{partial_analysis}

**Suggested next steps:**
1. {alternative_action_1}
2. {alternative_action_2}
3. Try rephrasing your request with more specific details about {suggested_detail}

**Manual approach:**
While I work on resolving this issue, you can {manual_workaround}
""",
            
            FallbackContext.DATA_FAILURE: """
Data collection encountered {error_type} while accessing {data_source}.

**Partial data collected:**
{partial_data_summary}

**What went wrong:**
{error_details}

**Alternative data sources you can use:**
{alternative_sources}

**Recommended actions:**
1. Verify {data_source} is accessible and properly configured
2. Check your authentication credentials if applicable
3. Consider using {alternative_approach} for similar insights

**Available fallback data:**
{fallback_data}
""",
            
            FallbackContext.OPTIMIZATION_FAILURE: """
Optimization analysis could not be completed due to {limitation}.

**Preliminary findings before the error:**
{partial_results}

**Specific issue encountered:**
{error_details}

**Manual optimization steps you can take immediately:**
{manual_steps}

**Partial recommendations based on available analysis:**
{partial_recommendations}

**Tools you can use directly:**
{available_tools}

**Recovery suggestion:**
{recovery_action}
""",
            
            FallbackContext.ACTION_FAILURE: """
Unable to generate complete action plan due to {error_reason}.

**Actions successfully identified:**
{completed_actions}

**Where the planning failed:**
{failure_point}

**You can proceed with these immediate steps:**
{immediate_steps}

**Manual implementation guide:**
{manual_guide}

**Resources for self-service:**
{resources}
""",
            
            FallbackContext.REPORT_FAILURE: """
Report generation was interrupted by {error_type}.

**Report sections completed:**
{completed_sections}

**Data successfully analyzed:**
{analyzed_data}

**Key findings before interruption:**
{key_findings}

**You can access partial results here:**
{partial_results_location}

**To complete the report manually:**
{manual_completion_steps}
""",
            
            FallbackContext.LLM_FAILURE: """
The AI model encountered an issue: {error_message}

**Request details:**
- Model: {model_name}
- Operation: {operation_type}
- Tokens processed: {tokens_processed}

**Potential causes:**
{potential_causes}

**Immediate alternatives:**
1. {alternative_1}
2. {alternative_2}

**Retry options:**
{retry_options}
""",
            
            FallbackContext.VALIDATION_FAILURE: """
Output validation failed quality checks.

**Quality issues detected:**
{quality_issues}

**Specific problems:**
{specific_problems}

**Here's what we can provide instead:**
{alternative_output}

**To get better results:**
{improvement_suggestions}

**Manual verification steps:**
{verification_steps}
""",
            
            FallbackContext.GENERAL_FAILURE: """
An unexpected issue occurred: {error_message}

**Context:**
- Operation: {operation}
- Stage: {stage}
- Time elapsed: {elapsed_time}

**Diagnostic information:**
{diagnostics}

**Recommended recovery actions:**
{recovery_actions}

**Support resources:**
{support_resources}
"""
        }
    
    def generate_fallback(self,
                         context: FallbackContext,
                         metadata: FallbackMetadata) -> Dict[str, Any]:
        """
        Generate a context-aware fallback response
        
        Args:
            context: The type of failure context
            metadata: Metadata about the failure
            
        Returns:
            Dictionary containing the fallback response
        """
        # Get the appropriate template
        template = self.templates.get(context, self.templates[FallbackContext.GENERAL_FAILURE])
        
        # Generate template variables based on context
        template_vars = self._generate_template_variables(context, metadata)
        
        # Format the template
        try:
            formatted_response = template.format(**template_vars)
        except KeyError as e:
            # If template formatting fails, provide a structured fallback
            formatted_response = self._generate_structured_fallback(context, metadata)
        
        # Build the response dictionary
        response = {
            "type": "contextual_fallback",
            "context": context.value,
            "message": formatted_response,
            "metadata": {
                "error_type": metadata.error_type,
                "agent": metadata.agent_name,
                "has_partial_data": metadata.partial_data is not None,
                "recovery_available": True
            }
        }
        
        # Add partial data if available
        if metadata.partial_data:
            response["partial_data"] = metadata.partial_data
        
        # Add suggested actions
        response["suggested_actions"] = self._generate_suggested_actions(context, metadata)
        
        return response
    
    def _generate_template_variables(self,
                                    context: FallbackContext,
                                    metadata: FallbackMetadata) -> Dict[str, str]:
        """Generate variables for template formatting"""
        variables = {}
        
        # Common variables
        variables['error_type'] = metadata.error_type
        variables['error_message'] = metadata.error_message
        variables['error_reason'] = self._extract_error_reason(metadata.error_message)
        
        # Context-specific variables
        if context == FallbackContext.TRIAGE_FAILURE:
            variables.update(self._generate_triage_variables(metadata))
        elif context == FallbackContext.DATA_FAILURE:
            variables.update(self._generate_data_variables(metadata))
        elif context == FallbackContext.OPTIMIZATION_FAILURE:
            variables.update(self._generate_optimization_variables(metadata))
        elif context == FallbackContext.ACTION_FAILURE:
            variables.update(self._generate_action_variables(metadata))
        elif context == FallbackContext.REPORT_FAILURE:
            variables.update(self._generate_report_variables(metadata))
        elif context == FallbackContext.LLM_FAILURE:
            variables.update(self._generate_llm_variables(metadata))
        elif context == FallbackContext.VALIDATION_FAILURE:
            variables.update(self._generate_validation_variables(metadata))
        else:
            variables.update(self._generate_general_variables(metadata))
        
        return variables
    
    def _generate_triage_variables(self, metadata: FallbackMetadata) -> Dict[str, str]:
        """Generate variables for triage failure context"""
        detected_domain = self._detect_domain(metadata.user_input or "")
        
        return {
            'detected_domain': detected_domain,
            'partial_analysis': self._format_partial_data(metadata.partial_data),
            'alternative_action_1': f"Browse our {detected_domain} optimization guides",
            'alternative_action_2': f"Use specific {detected_domain} analysis tools",
            'suggested_detail': f"your {detected_domain} configuration or metrics",
            'manual_workaround': f"access the {detected_domain} dashboard directly"
        }
    
    def _generate_data_variables(self, metadata: FallbackMetadata) -> Dict[str, str]:
        """Generate variables for data failure context"""
        data_source = self._extract_data_source(metadata)
        
        return {
            'data_source': data_source,
            'partial_data_summary': self._summarize_partial_data(metadata.partial_data),
            'error_details': metadata.error_message,
            'alternative_sources': self._suggest_alternative_sources(data_source),
            'alternative_approach': "cached historical data",
            'fallback_data': self._format_fallback_data(metadata.partial_data)
        }
    
    def _generate_optimization_variables(self, metadata: FallbackMetadata) -> Dict[str, str]:
        """Generate variables for optimization failure context"""
        return {
            'limitation': self._identify_limitation(metadata),
            'partial_results': self._format_optimization_results(metadata.partial_data),
            'error_details': metadata.error_message,
            'manual_steps': self._generate_manual_optimization_steps(),
            'partial_recommendations': self._extract_partial_recommendations(metadata.partial_data),
            'available_tools': "Profiler, Benchmark Suite, Cost Calculator",
            'recovery_action': "Re-run with reduced scope or simplified parameters"
        }
    
    def _generate_action_variables(self, metadata: FallbackMetadata) -> Dict[str, str]:
        """Generate variables for action failure context"""
        return {
            'completed_actions': self._list_completed_actions(metadata.attempted_operations),
            'failure_point': self._identify_failure_point(metadata),
            'immediate_steps': self._generate_immediate_steps(metadata),
            'manual_guide': self._create_manual_guide(metadata),
            'resources': "Documentation, API Reference, Community Forums"
        }
    
    def _generate_report_variables(self, metadata: FallbackMetadata) -> Dict[str, str]:
        """Generate variables for report failure context"""
        return {
            'completed_sections': self._list_completed_sections(metadata.partial_data),
            'analyzed_data': self._summarize_analyzed_data(metadata.partial_data),
            'key_findings': self._extract_key_findings(metadata.partial_data),
            'partial_results_location': "/reports/partial/latest",
            'manual_completion_steps': self._generate_report_completion_steps()
        }
    
    def _generate_llm_variables(self, metadata: FallbackMetadata) -> Dict[str, str]:
        """Generate variables for LLM failure context"""
        return {
            'model_name': metadata.partial_data.get('model', 'Unknown') if metadata.partial_data else 'Unknown',
            'operation_type': metadata.partial_data.get('operation', 'inference') if metadata.partial_data else 'inference',
            'tokens_processed': str(metadata.partial_data.get('tokens', 0) if metadata.partial_data else 0),
            'potential_causes': "Rate limiting, context overflow, or temporary service disruption",
            'alternative_1': "Use a smaller context window",
            'alternative_2': "Switch to a different model",
            'retry_options': "Automatic retry in 30 seconds, or manual retry with reduced input"
        }
    
    def _generate_validation_variables(self, metadata: FallbackMetadata) -> Dict[str, str]:
        """Generate variables for validation failure context"""
        return {
            'quality_issues': self._format_quality_issues(metadata.partial_data),
            'specific_problems': self._identify_specific_problems(metadata),
            'alternative_output': self._generate_alternative_output(metadata),
            'improvement_suggestions': self._suggest_improvements(metadata),
            'verification_steps': self._generate_verification_steps()
        }
    
    def _generate_general_variables(self, metadata: FallbackMetadata) -> Dict[str, str]:
        """Generate variables for general failure context"""
        return {
            'operation': metadata.agent_name or "Unknown Operation",
            'stage': self._identify_stage(metadata),
            'elapsed_time': "N/A",
            'diagnostics': self._generate_diagnostics(metadata),
            'recovery_actions': self._suggest_recovery_actions(metadata),
            'support_resources': "Help Center, API Status Page, Support Ticket System"
        }
    
    def _detect_domain(self, user_input: str) -> str:
        """Detect the domain from user input"""
        input_lower = user_input.lower()
        
        for domain, keywords in self.domain_detection_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                return domain.replace('_', ' ')
        
        return "general optimization"
    
    def _extract_error_reason(self, error_message: str) -> str:
        """Extract a concise error reason from the full message"""
        # Remove technical details and stack traces
        reason = error_message.split('\n')[0]
        reason = re.sub(r'^\w+Error:\s*', '', reason)
        return reason[:100] + "..." if len(reason) > 100 else reason
    
    def _format_partial_data(self, partial_data: Optional[Dict[str, Any]]) -> str:
        """Format partial data for display"""
        if not partial_data:
            return "Initial analysis suggests this is an optimization-related query"
        
        formatted_items = []
        for key, value in partial_data.items():
            if isinstance(value, (str, int, float)):
                formatted_items.append(f"- {key}: {value}")
            elif isinstance(value, list) and len(value) > 0:
                formatted_items.append(f"- {key}: {len(value)} items collected")
            elif isinstance(value, dict):
                formatted_items.append(f"- {key}: Data structure with {len(value)} fields")
        
        return '\n'.join(formatted_items) if formatted_items else "Partial analysis completed"
    
    def _summarize_partial_data(self, partial_data: Optional[Dict[str, Any]]) -> str:
        """Summarize partial data collection results"""
        if not partial_data:
            return "No data was successfully collected before the error"
        
        summary = []
        total_items = 0
        
        for key, value in partial_data.items():
            if isinstance(value, list):
                total_items += len(value)
                summary.append(f"{len(value)} {key}")
            elif isinstance(value, dict):
                total_items += len(value)
                summary.append(f"{len(value)} {key} entries")
        
        if summary:
            return f"Collected {total_items} total items: " + ", ".join(summary)
        return "Some preliminary data was collected"
    
    def _extract_data_source(self, metadata: FallbackMetadata) -> str:
        """Extract data source information from metadata"""
        if metadata.partial_data and 'source' in metadata.partial_data:
            return metadata.partial_data['source']
        
        # Try to extract from error message
        if 'database' in metadata.error_message.lower():
            return "database"
        elif 'api' in metadata.error_message.lower():
            return "API endpoint"
        elif 'file' in metadata.error_message.lower():
            return "file system"
        
        return "data source"
    
    def _suggest_alternative_sources(self, data_source: str) -> str:
        """Suggest alternative data sources"""
        alternatives = {
            'database': "1. Cache layer\n2. Read replica\n3. Data warehouse",
            'API endpoint': "1. Alternative API version\n2. GraphQL endpoint\n3. Webhook data",
            'file system': "1. Object storage\n2. Database export\n3. API data stream"
        }
        
        return alternatives.get(data_source, "1. Manual data export\n2. Alternative API\n3. Cached results")
    
    def _format_fallback_data(self, partial_data: Optional[Dict[str, Any]]) -> str:
        """Format available fallback data"""
        if not partial_data:
            return "No fallback data available"
        
        # Provide a structured view of available data
        try:
            return json.dumps(partial_data, indent=2, default=str)[:500]
        except Exception as e:
            logger.warning(f"Failed to serialize fallback data: {e}")
            return "Structured data available but cannot be displayed"
    
    def _identify_limitation(self, metadata: FallbackMetadata) -> str:
        """Identify the specific limitation encountered"""
        error_lower = metadata.error_message.lower()
        
        if 'timeout' in error_lower:
            return "processing timeout"
        elif 'memory' in error_lower:
            return "memory constraints"
        elif 'rate' in error_lower:
            return "rate limiting"
        elif 'permission' in error_lower:
            return "permission restrictions"
        elif 'connection' in error_lower:
            return "connection issues"
        
        return "technical constraints"
    
    def _format_optimization_results(self, partial_data: Optional[Dict[str, Any]]) -> str:
        """Format partial optimization results"""
        if not partial_data:
            return "Initial optimization scan completed"
        
        results = []
        if 'metrics' in partial_data:
            results.append(f"Metrics analyzed: {partial_data['metrics']}")
        if 'bottlenecks' in partial_data:
            results.append(f"Bottlenecks identified: {partial_data['bottlenecks']}")
        if 'recommendations' in partial_data:
            results.append(f"Recommendations generated: {len(partial_data['recommendations'])}")
        
        return '\n'.join(results) if results else "Preliminary analysis completed"
    
    def _generate_manual_optimization_steps(self) -> str:
        """Generate manual optimization steps"""
        return """1. Profile current performance metrics
2. Identify top 3 bottlenecks using monitoring tools
3. Apply standard optimization patterns:
   - Enable caching (Redis/Memcached)
   - Implement request batching
   - Add connection pooling
   - Enable compression
4. Measure improvements
5. Iterate on successful changes"""
    
    def _extract_partial_recommendations(self, partial_data: Optional[Dict[str, Any]]) -> str:
        """Extract partial recommendations from data"""
        if not partial_data or 'recommendations' not in partial_data:
            return "Standard optimizations: caching, batching, async processing"
        
        recs = partial_data['recommendations']
        if isinstance(recs, list):
            return '\n'.join(f"- {rec}" for rec in recs[:3])
        return str(recs)
    
    def _list_completed_actions(self, operations: Optional[List[str]]) -> str:
        """List completed actions from attempted operations"""
        if not operations:
            return "No actions were completed before the failure"
        
        return '\n'.join(f"✓ {op}" for op in operations)
    
    def _identify_failure_point(self, metadata: FallbackMetadata) -> str:
        """Identify where the failure occurred"""
        if metadata.stacktrace:
            # Extract the most relevant line from stacktrace
            lines = metadata.stacktrace.split('\n')
            for line in lines:
                if 'File' in line and '.py' in line:
                    return f"Failed at: {line.strip()}"
        
        return f"Failed during: {metadata.agent_name or 'processing'}"
    
    def _generate_immediate_steps(self, metadata: FallbackMetadata) -> str:
        """Generate immediate actionable steps"""
        return """1. Review current configuration
2. Validate input parameters
3. Check system resources
4. Retry with simplified parameters
5. Consult documentation for constraints"""
    
    def _create_manual_guide(self, metadata: FallbackMetadata) -> str:
        """Create a manual implementation guide"""
        return """Step-by-step manual implementation:
1. Access the optimization dashboard
2. Navigate to the configuration panel
3. Adjust parameters based on partial analysis
4. Apply changes incrementally
5. Monitor impact after each change
6. Document successful optimizations"""
    
    def _list_completed_sections(self, partial_data: Optional[Dict[str, Any]]) -> str:
        """List completed report sections"""
        if not partial_data:
            return "No sections completed"
        
        sections = []
        for key in ['summary', 'analysis', 'recommendations', 'metrics', 'conclusions']:
            if key in partial_data:
                sections.append(f"✓ {key.capitalize()}")
        
        return '\n'.join(sections) if sections else "Report initialization completed"
    
    def _summarize_analyzed_data(self, partial_data: Optional[Dict[str, Any]]) -> str:
        """Summarize data that was analyzed"""
        if not partial_data:
            return "No data analysis completed"
        
        return f"Analyzed {len(partial_data)} data points across multiple dimensions"
    
    def _extract_key_findings(self, partial_data: Optional[Dict[str, Any]]) -> str:
        """Extract key findings from partial data"""
        if not partial_data:
            return "Analysis incomplete - no findings available"
        
        findings = []
        if 'findings' in partial_data:
            return str(partial_data['findings'])
        
        # Generate findings from available data
        for key, value in partial_data.items():
            if isinstance(value, (int, float)):
                findings.append(f"{key}: {value}")
        
        return '\n'.join(findings[:5]) if findings else "Preliminary analysis started"
    
    def _generate_report_completion_steps(self) -> str:
        """Generate steps to complete the report manually"""
        return """1. Export partial results from dashboard
2. Open report template
3. Copy completed sections
4. Fill in missing sections using dashboard data
5. Generate visualizations manually
6. Export final report"""
    
    def _format_quality_issues(self, partial_data: Optional[Dict[str, Any]]) -> str:
        """Format quality issues found"""
        if not partial_data or 'quality_issues' not in partial_data:
            return "Output did not meet quality thresholds"
        
        issues = partial_data['quality_issues']
        if isinstance(issues, list):
            return '\n'.join(f"- {issue}" for issue in issues)
        return str(issues)
    
    def _identify_specific_problems(self, metadata: FallbackMetadata) -> str:
        """Identify specific problems from metadata"""
        problems = []
        
        if 'generic' in metadata.error_message.lower():
            problems.append("Too many generic phrases detected")
        if 'short' in metadata.error_message.lower():
            problems.append("Output length below minimum threshold")
        if 'actionable' in metadata.error_message.lower():
            problems.append("Lack of actionable recommendations")
        
        return '\n'.join(problems) if problems else "Quality score below acceptable threshold"
    
    def _generate_alternative_output(self, metadata: FallbackMetadata) -> str:
        """Generate an alternative output"""
        return """Based on standard best practices:
1. Implement caching layer (expect 30-40% latency reduction)
2. Enable request batching (batch size: 32)
3. Add connection pooling (pool size: 20)
4. Configure auto-scaling (min: 2, max: 10)
5. Set up monitoring alerts"""
    
    def _suggest_improvements(self, metadata: FallbackMetadata) -> str:
        """Suggest improvements for better results"""
        return """To get higher quality results:
1. Provide specific metrics or constraints
2. Include current configuration details
3. Specify optimization goals (latency, cost, throughput)
4. Share relevant logs or monitoring data
5. Define success criteria"""
    
    def _generate_verification_steps(self) -> str:
        """Generate manual verification steps"""
        return """Manual verification process:
1. Check output against requirements
2. Validate metrics and calculations
3. Verify actionability of recommendations
4. Test proposed changes in staging
5. Measure actual vs. predicted improvements"""
    
    def _identify_stage(self, metadata: FallbackMetadata) -> str:
        """Identify the processing stage where failure occurred"""
        if metadata.agent_name:
            return f"{metadata.agent_name} processing"
        return "Processing"
    
    def _generate_diagnostics(self, metadata: FallbackMetadata) -> str:
        """Generate diagnostic information"""
        diag = []
        
        if metadata.error_type:
            diag.append(f"Error Type: {metadata.error_type}")
        if metadata.agent_name:
            diag.append(f"Agent: {metadata.agent_name}")
        if metadata.attempted_operations:
            diag.append(f"Operations Attempted: {len(metadata.attempted_operations)}")
        
        return '\n'.join(diag) if diag else "Limited diagnostic information available"
    
    def _suggest_recovery_actions(self, metadata: FallbackMetadata) -> str:
        """Suggest recovery actions based on the error"""
        return """1. Retry the operation
2. Reduce input complexity
3. Check system status
4. Clear cache and retry
5. Contact support if issue persists"""
    
    def _generate_structured_fallback(self,
                                     context: FallbackContext,
                                     metadata: FallbackMetadata) -> str:
        """Generate a structured fallback when template formatting fails"""
        return f"""
An error occurred during {context.value}.

Error: {metadata.error_message}

What you can do:
1. Retry the operation with simpler parameters
2. Check the system status page
3. Review the documentation for constraints
4. Contact support with error code: {context.value}_{metadata.error_type}

Partial data may be available in the response metadata.
"""
    
    def _generate_suggested_actions(self,
                                   context: FallbackContext,
                                   metadata: FallbackMetadata) -> List[Dict[str, Any]]:
        """Generate suggested actions for recovery"""
        actions = []
        
        # Add retry action
        actions.append({
            "action": "retry",
            "description": "Retry the operation",
            "parameters": {
                "delay": "5s",
                "max_attempts": 3
            }
        })
        
        # Add simplify action
        actions.append({
            "action": "simplify",
            "description": "Retry with simplified parameters",
            "parameters": {
                "reduce_scope": True,
                "use_defaults": True
            }
        })
        
        # Add manual action
        actions.append({
            "action": "manual",
            "description": "Proceed with manual steps",
            "documentation_url": f"/docs/{context.value}"
        })
        
        return actions