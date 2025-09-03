/**
 * Tests for agent_thinking event payload mapping
 */

import { mapAgentThinkingPayload } from '@/utils/event-payload-mapper';

describe('mapAgentThinkingPayload', () => {
  it('should handle Format 1: Direct message field', () => {
    const input = {
      message: "Running triage with isolated instance...",
      agent_name: "Supervisor",
      connection_id: null,
      run_id: "thread_67cda1f0141943c4_run_1756920689989_61351ed4",
      thread_id: "thread_67cda1f0141943c4",
      timestamp: "2025-09-03T17:31:30.066488+00:00",
      type: "agent_thinking",
      user_id: "7c5e1032-ed21-4aea-b12a-aeddf3622bec"
    };

    const result = mapAgentThinkingPayload(input);
    
    expect(result.thought).toBe("Running triage with isolated instance...");
    expect(result.agent_id).toBe("Supervisor");
  });

  it('should handle Format 2: Nested in payload.reasoning', () => {
    const input = {
      type: "agent_thinking",
      run_id: "thread_67cda1f0141943c4_run_1756920689989_61351ed4",
      agent_name: "triage",
      timestamp: "2025-09-03T17:31:30.069038+00:00",
      payload: {
        reasoning: "Extracting entities and determining intent...",
        step_number: null,
        progress_percentage: null,
        status: "thinking"
      },
      thread_id: "thread_67cda1f0141943c4"
    };

    const result = mapAgentThinkingPayload(input);
    
    expect(result.thought).toBe("Extracting entities and determining intent...");
    expect(result.agent_id).toBe("triage");
  });

  it('should handle legacy thought field', () => {
    const input = {
      thought: "Legacy thinking message",
      agent_name: "LegacyAgent"
    };

    const result = mapAgentThinkingPayload(input);
    
    expect(result.thought).toBe("Legacy thinking message");
    expect(result.agent_id).toBe("LegacyAgent");
  });

  it('should fallback to "Processing..." when no message provided', () => {
    const input = {
      agent_name: "EmptyAgent"
    };

    const result = mapAgentThinkingPayload(input);
    
    expect(result.thought).toBe("Processing...");
    expect(result.agent_id).toBe("EmptyAgent");
  });

  it('should handle agent_id as fallback for agent_name', () => {
    const input = {
      message: "Test message",
      agent_id: "TestAgent"
    };

    const result = mapAgentThinkingPayload(input);
    
    expect(result.thought).toBe("Test message");
    expect(result.agent_id).toBe("TestAgent");
  });

  it('should handle step numbers from payload', () => {
    const input = {
      message: "Processing step",
      agent_name: "StepAgent",
      payload: {
        step_number: 3,
        total_steps: 5
      }
    };

    const result = mapAgentThinkingPayload(input);
    
    expect(result.thought).toBe("Processing step");
    expect(result.step_number).toBe(3);
    expect(result.total_steps).toBe(5);
  });
});