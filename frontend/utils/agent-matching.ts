// Agent Matching Utilities - Exact string matching for agent deduplication
// Provides exact matching to avoid false positives from startsWith matching

import type { AgentResult } from '@/types/layer-types';

// ============================================
// Core Matching Functions
// ============================================

export const extractBaseAgentName = (agentName: string): string => {
  // Remove iteration indicators like " (2)", " (iteration 3)", " (Run #4)"
  return agentName.replace(/\s*\((iteration\s+\d+|Run\s+#\d+|\d+)\)\s*$/, '').trim();
};

export const extractIterationNumber = (agentName: string): number => {
  // Extract iteration number from names like "Agent (2)", "Agent (iteration 3)", "Agent (Run #4)"
  const iterationMatch = agentName.match(/\((?:iteration\s+|Run\s+#)?(\d+)\)$/);
  return iterationMatch ? parseInt(iterationMatch[1], 10) : 1;
};

export const isExactAgentMatch = (agentName: string, targetBaseId: string): boolean => {
  const baseName = extractBaseAgentName(agentName);
  return baseName === targetBaseId;
};

export const findExactAgentIndex = (agents: AgentResult[], targetBaseId: string): number => {
  return agents.findIndex(agent => isExactAgentMatch(agent.agentName, targetBaseId));
};

// ============================================
// Agent Name Validation
// ============================================

export const isValidAgentName = (agentName: string): boolean => {
  return agentName.trim().length > 0 && !agentName.includes('\n');
};

export const normalizeAgentName = (agentName: string): string => {
  return agentName.trim().replace(/\s+/g, ' ');
};

export const createIteratedAgentName = (baseId: string, iteration: number): string => {
  return iteration > 1 ? `${baseId} (${iteration})` : baseId;
};