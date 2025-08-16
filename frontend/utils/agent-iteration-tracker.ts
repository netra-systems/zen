// Agent Iteration Tracker - Map-based iteration counting and management
// Tracks agent reruns with proper state management

import type { AgentExecution } from '@/types/store-types';
import { extractBaseAgentName } from './agent-matching';

// ============================================
// Iteration Management
// ============================================

export const getAgentIteration = (iterations: Map<string, number>, agentId: string): number => {
  return iterations.get(agentId) || 1;
};

export const incrementAgentIteration = (iterations: Map<string, number>, agentId: string): number => {
  const current = getAgentIteration(iterations, agentId);
  const newIteration = current + 1;
  iterations.set(agentId, newIteration);
  return newIteration;
};

export const setAgentIteration = (iterations: Map<string, number>, agentId: string, iteration: number): void => {
  iterations.set(agentId, Math.max(1, iteration));
};

export const resetAgentIteration = (iterations: Map<string, number>, agentId: string): void => {
  iterations.set(agentId, 1);
};

// ============================================
// Execution Tracking
// ============================================

export const updateExecutedAgent = (executions: Map<string, AgentExecution>, agentId: string, execution: AgentExecution): void => {
  executions.set(agentId, execution);
};

export const getExecutedAgent = (executions: Map<string, AgentExecution>, agentId: string): AgentExecution | undefined => {
  return executions.get(agentId);
};

export const hasExecutedAgent = (executions: Map<string, AgentExecution>, agentId: string): boolean => {
  return executions.has(agentId);
};

export const removeExecutedAgent = (executions: Map<string, AgentExecution>, agentId: string): boolean => {
  return executions.delete(agentId);
};