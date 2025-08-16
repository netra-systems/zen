// Agent Deduplication Core - Exact matching deduplication logic
// Replaces flawed startsWith matching with exact string comparison

import type { AgentResult } from '@/types/layer-types';
import { findExactAgentIndex, extractBaseAgentName, createIteratedAgentName } from './agent-matching';
import { getAgentIteration, incrementAgentIteration } from './agent-iteration-tracker';

// ============================================
// Core Deduplication Logic
// ============================================

export const deduplicateAgentResults = (
  currentAgents: AgentResult[] | undefined,
  newAgent: AgentResult,
  agentIterations: Map<string, number>
): AgentResult[] => {
  if (!currentAgents) return [newAgent];
  
  const baseAgentId = extractBaseAgentName(newAgent.agentName);
  const existingIndex = findExactAgentIndex(currentAgents, baseAgentId);
  
  if (existingIndex >= 0) {
    return replaceExistingAgent(currentAgents, existingIndex, newAgent, agentIterations);
  } else {
    return addNewAgent(currentAgents, newAgent);
  }
};

export const replaceExistingAgent = (
  agents: AgentResult[],
  index: number,
  newAgent: AgentResult,
  agentIterations: Map<string, number>
): AgentResult[] => {
  const baseAgentId = extractBaseAgentName(newAgent.agentName);
  const newIteration = incrementAgentIteration(agentIterations, baseAgentId);
  
  const updatedAgent = {
    ...newAgent,
    agentName: createIteratedAgentName(baseAgentId, newIteration),
    iteration: newIteration
  };
  
  return replaceAgentAtIndex(agents, index, updatedAgent);
};

export const addNewAgent = (agents: AgentResult[], newAgent: AgentResult): AgentResult[] => {
  return [...agents, newAgent];
};

export const replaceAgentAtIndex = (agents: AgentResult[], index: number, newAgent: AgentResult): AgentResult[] => {
  const updated = [...agents];
  updated[index] = newAgent;
  return updated;
};