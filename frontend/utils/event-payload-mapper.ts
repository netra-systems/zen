// Event payload mapper - Maps backend event structures to frontend expectations
// Modular approach following CLAUDE.md 25-line function limit

/**
 * Maps backend agent_started payload to frontend expected structure
 */
export const mapAgentStartedPayload = (backendPayload: any) => {
  return {
    agent_id: backendPayload.agent_name || backendPayload.agent_id,
    agent_type: backendPayload.agent_name || backendPayload.agent_type,
    run_id: backendPayload.run_id,
    timestamp: backendPayload.timestamp,
    status: 'started',
    message: `Agent ${backendPayload.agent_name || 'Unknown'} started`
  };
};

/**
 * Maps backend agent_completed payload to frontend expected structure
 */
export const mapAgentCompletedPayload = (backendPayload: any) => {
  return {
    agent_id: backendPayload.agent_name || backendPayload.agent_id,
    agent_type: backendPayload.agent_name || backendPayload.agent_type,
    duration_ms: backendPayload.duration_ms || 0,
    result: backendPayload.result || {},
    metrics: backendPayload.metrics || {},
    iteration: backendPayload.iteration || 1
  };
};

/**
 * Maps backend agent_thinking payload to frontend expected structure
 */
export const mapAgentThinkingPayload = (backendPayload: any) => {
  return {
    thought: backendPayload.thought,
    agent_id: backendPayload.agent_name || backendPayload.agent_id,
    agent_type: backendPayload.agent_name || backendPayload.agent_type,
    step_number: backendPayload.step_number || 0,
    total_steps: backendPayload.total_steps || 0
  };
};

/**
 * Maps backend tool_executing payload to frontend expected structure
 */
export const mapToolExecutingPayload = (backendPayload: any) => {
  return {
    tool_name: backendPayload.tool_name,
    agent_id: backendPayload.agent_name || backendPayload.agent_id,
    agent_type: backendPayload.agent_name || backendPayload.agent_type,
    timestamp: backendPayload.timestamp || Date.now()
  };
};

/**
 * Maps backend tool_completed payload to frontend expected structure
 */
export const mapToolCompletedPayload = (backendPayload: any) => {
  return {
    tool_name: backendPayload.tool_name,
    name: backendPayload.tool_name,
    result: backendPayload.result,
    agent_id: backendPayload.agent_name || backendPayload.agent_id,
    agent_type: backendPayload.agent_name || backendPayload.agent_type,
    timestamp: backendPayload.timestamp || Date.now()
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
 * Main payload mapper - routes events to specific mappers
 */
export const mapEventPayload = (eventType: string, backendPayload: any) => {
  const mappers: Record<string, (payload: any) => any> = {
    'agent_started': mapAgentStartedPayload,
    'agent_completed': mapAgentCompletedPayload,
    'agent_thinking': mapAgentThinkingPayload,
    'tool_executing': mapToolExecutingPayload,
    'tool_completed': mapToolCompletedPayload,
    'partial_result': mapPartialResultPayload
  };
  
  const mapper = mappers[eventType];
  return mapper ? mapper(backendPayload) : backendPayload;
};