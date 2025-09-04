// Event payload mapper - Maps backend event structures to frontend expectations
// Modular approach following CLAUDE.md 25-line function limit

/**
 * Maps backend agent_started event to frontend expected structure
 * Note: Receives the full event, not just the payload
 */
export const mapAgentStartedPayload = (fullEvent: any) => {
  // Extract agent_name from top level and payload fields from nested payload
  return {
    agent_id: fullEvent.agent_name || fullEvent.payload?.agent_id || 'unknown',
    agent_type: fullEvent.agent_name || fullEvent.payload?.agent_type || 'unknown',
    run_id: fullEvent.run_id,
    timestamp: fullEvent.timestamp,
    status: fullEvent.payload?.status || 'started',
    message: fullEvent.payload?.message || `Agent ${fullEvent.agent_name || 'Unknown'} started`
  };
};

/**
 * Maps backend agent_completed event to frontend expected structure
 * Note: Receives the full event, not just the payload
 */
export const mapAgentCompletedPayload = (fullEvent: any) => {
  return {
    agent_id: fullEvent.agent_name || fullEvent.payload?.agent_id || 'unknown',
    agent_type: fullEvent.agent_name || fullEvent.payload?.agent_type || 'unknown',
    duration_ms: fullEvent.payload?.execution_time_ms || fullEvent.payload?.duration_ms || 0,
    result: fullEvent.payload?.result || {},
    metrics: fullEvent.payload?.metrics || {},
    message: fullEvent.payload?.message || `Agent ${fullEvent.agent_name || 'Unknown'} completed`,
    iteration: fullEvent.payload?.iteration || 1
  };
};

/**
 * Maps backend agent_thinking event to frontend expected structure
 * Note: Receives the full event, not just the payload
 */
export const mapAgentThinkingPayload = (fullEvent: any) => {
  // Extract reasoning from payload
  const thought = fullEvent.payload?.reasoning || 
                  fullEvent.payload?.message || 
                  fullEvent.message || 
                  'Processing...';
  
  return {
    thought: thought,
    agent_id: fullEvent.agent_name || fullEvent.payload?.agent_id || 'unknown',
    agent_type: fullEvent.agent_name || fullEvent.payload?.agent_type || 'unknown',
    step_number: fullEvent.payload?.step_number || 0,
    total_steps: fullEvent.payload?.total_steps || 0,
    progress_percentage: fullEvent.payload?.progress_percentage || null
  };
};

/**
 * Maps backend tool_executing event to frontend expected structure
 * Note: Receives the full event, not just the payload
 */
export const mapToolExecutingPayload = (fullEvent: any) => {
  return {
    tool_name: fullEvent.payload?.tool_name || 'unknown_tool',
    agent_id: fullEvent.agent_name || fullEvent.payload?.agent_id || 'unknown',
    agent_type: fullEvent.agent_name || fullEvent.payload?.agent_type || 'unknown',
    timestamp: fullEvent.timestamp || Date.now(),
    parameters: fullEvent.payload?.parameters || {}
  };
};

/**
 * Maps backend tool_completed event to frontend expected structure
 * Note: Receives the full event, not just the payload
 */
export const mapToolCompletedPayload = (fullEvent: any) => {
  return {
    tool_name: fullEvent.payload?.tool_name || 'unknown_tool',
    name: fullEvent.payload?.tool_name || 'unknown_tool',
    result: fullEvent.payload?.result || {},
    agent_id: fullEvent.agent_name || fullEvent.payload?.agent_id || 'unknown',
    agent_type: fullEvent.agent_name || fullEvent.payload?.agent_type || 'unknown',
    timestamp: fullEvent.timestamp || Date.now(),
    execution_time_ms: fullEvent.payload?.execution_time_ms || null
  };
};

/**
 * Maps backend partial_result payload to frontend expected structure
 */
export const mapPartialResultPayload = (backendPayload: any) => {
  return {
    content: backendPayload.content || backendPayload.chunk || '',
    agent_id: backendPayload.agent_name || backendPayload.agent_id,
    agent_type: backendPayload.agent_name || backendPayload.agent_type,
    is_complete: backendPayload.is_complete || backendPayload.done || false
  };
};

/**
 * Maps backend agent_registered payload to frontend expected structure
 */
export const mapAgentRegisteredPayload = (backendPayload: any) => {
  return {
    agent_id: backendPayload.agent_id,
    agent_type: backendPayload.agent_type || 'unknown',
    timestamp: backendPayload.timestamp || Date.now(),
    status: 'registered',
    message: `Agent ${backendPayload.agent_id} registered`
  };
};

/**
 * Maps backend agent_failed payload to frontend expected structure
 */
export const mapAgentFailedPayload = (backendPayload: any) => {
  return {
    agent_id: backendPayload.agent_id || backendPayload.agent_name,
    agent_type: backendPayload.agent_type || backendPayload.agent_name,
    error: backendPayload.error || backendPayload.message,
    timestamp: backendPayload.timestamp || Date.now(),
    status: 'failed'
  };
};

/**
 * Maps backend agent_cancelled payload to frontend expected structure
 */
export const mapAgentCancelledPayload = (backendPayload: any) => {
  return {
    agent_id: backendPayload.agent_id || backendPayload.agent_name,
    agent_type: backendPayload.agent_type || backendPayload.agent_name,
    reason: backendPayload.reason || 'User cancelled',
    timestamp: backendPayload.timestamp || Date.now(),
    status: 'cancelled'
  };
};

/**
 * Maps backend agent_metrics_updated payload to frontend expected structure
 */
export const mapAgentMetricsUpdatedPayload = (backendPayload: any) => {
  return {
    agent_id: backendPayload.agent_id || backendPayload.agent_name,
    agent_type: backendPayload.agent_type || backendPayload.agent_name,
    metrics: backendPayload.metrics || {},
    timestamp: backendPayload.timestamp || Date.now()
  };
};

/**
 * Maps backend agent_unregistered payload to frontend expected structure
 */
export const mapAgentUnregisteredPayload = (backendPayload: any) => {
  return {
    agent_id: backendPayload.agent_id,
    agent_type: backendPayload.agent_type || 'unknown',
    timestamp: backendPayload.timestamp || Date.now(),
    status: 'unregistered',
    message: `Agent ${backendPayload.agent_id} unregistered`
  };
};

/**
 * Maps backend agent_status_changed payload to frontend expected structure
 */
export const mapAgentStatusChangedPayload = (backendPayload: any) => {
  return {
    agent_id: backendPayload.agent_id || backendPayload.agent_name,
    agent_type: backendPayload.agent_type || backendPayload.agent_name,
    old_status: backendPayload.old_status,
    new_status: backendPayload.new_status,
    timestamp: backendPayload.timestamp || Date.now()
  };
};

/**
 * Maps backend agent_manager_shutdown payload to frontend expected structure
 */
export const mapAgentManagerShutdownPayload = (backendPayload: any) => {
  return {
    reason: backendPayload.reason || 'System shutdown',
    timestamp: backendPayload.timestamp || Date.now(),
    active_agents_count: backendPayload.active_agents_count || 0,
    message: 'Agent manager shutting down'
  };
};

/**
 * Main event mapper - routes events to specific mappers
 * CRITICAL: Pass the full event object, not just the payload
 */
export const mapEventPayload = (eventType: string, fullEvent: any) => {
  const mappers: Record<string, (event: any) => any> = {
    'agent_started': mapAgentStartedPayload,
    'agent_completed': mapAgentCompletedPayload,
    'agent_thinking': mapAgentThinkingPayload,
    'tool_executing': mapToolExecutingPayload,
    'tool_completed': mapToolCompletedPayload,
    'partial_result': mapPartialResultPayload,
    'agent_registered': mapAgentRegisteredPayload,
    'agent_failed': mapAgentFailedPayload,
    'agent_cancelled': mapAgentCancelledPayload,
    'agent_metrics_updated': mapAgentMetricsUpdatedPayload,
    'agent_unregistered': mapAgentUnregisteredPayload,
    'agent_status_changed': mapAgentStatusChangedPayload,
    'agent_manager_shutdown': mapAgentManagerShutdownPayload
  };
  
  const mapper = mappers[eventType];
  return mapper ? mapper(fullEvent) : fullEvent;
};