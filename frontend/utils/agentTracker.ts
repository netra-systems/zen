// Agent Tracker Utility - Modular deduplication system
// Handles agent execution tracking and iteration counting

import type { AgentExecution } from '@/types/store-types';
import type { AgentResult } from '@/types/layer-types';
import { extractBaseAgentName, createIteratedAgentName } from './agent-matching';
import { getAgentIteration, incrementAgentIteration, updateExecutedAgent } from './agent-iteration-tracker';
import { deduplicateAgentResults as deduplicateCore } from './agent-deduplication';

// ============================================
// Agent Display Name Generation
// ============================================

export const generateAgentDisplayName = (agentId: string, iteration: number): string => {
  return createIteratedAgentName(agentId, iteration);
};

export const generateIterationDisplayName = (agentId: string, iteration: number): string => {
  return iteration > 1 ? `${agentId} (iteration ${iteration})` : agentId;
};

export const generateRunDisplayName = (agentId: string, iteration: number): string => {
  return iteration > 1 ? `${agentId} (Run #${iteration})` : agentId;
};

// ============================================
// Agent Execution Helpers
// ============================================

export const createAgentExecution = (
  agentId: string, 
  iteration: number,
  status: 'running' | 'completed' | 'failed' = 'running'
): AgentExecution => ({
  name: agentId,
  iteration,
  status,
  startTime: Date.now()
});

export const completeAgentExecution = (
  execution: AgentExecution,
  result?: unknown
): AgentExecution => ({
  ...execution,
  status: 'completed',
  endTime: Date.now(),
  result
});

// ============================================
// Deduplication Helpers
// ============================================

export const deduplicateAgentResults = (
  currentAgents: AgentResult[] | undefined,
  newAgent: AgentResult,
  agentIterations: Map<string, number>
): AgentResult[] => {
  return deduplicateCore(currentAgents, newAgent, agentIterations);
};

export const trackAgentExecution = (
  executions: Map<string, AgentExecution>,
  iterations: Map<string, number>,
  agentId: string
): AgentExecution => {
  const iteration = getAgentIteration(iterations, agentId);
  const execution = createAgentExecution(agentId, iteration);
  updateExecutedAgent(executions, agentId, execution);
  return execution;
};

// ============================================
// Agent State Validation
// ============================================

export const validateAgentState = (
  executedAgents: Map<string, AgentExecution>,
  agentIterations: Map<string, number>
): boolean => {
  // Ensure all executed agents have corresponding iterations
  for (const [agentId] of executedAgents) {
    if (!agentIterations.has(agentId)) return false;
  }
  return true;
};

// ============================================
// Known Agent List
// ============================================

export const KNOWN_AGENTS = [
  'TriageSubAgent',
  'DataSubAgent',
  'OptimizationsCoreSubAgent', 
  'ActionsToMeetGoalsSubAgent',
  'ReportingSubAgent',
  'CorpusAdminSubAgent',
  'SyntheticDataSubAgent'
] as const;

export type KnownAgent = typeof KNOWN_AGENTS[number];

export const isKnownAgent = (agentId: string): agentId is KnownAgent => {
  return KNOWN_AGENTS.includes(agentId as KnownAgent);
};