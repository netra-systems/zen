// Agent Tracker Tests - Verification of deduplication logic
// Tests the core deduplication and iteration tracking functionality

import {
  generateAgentDisplayName,
  createAgentExecution,
  completeAgentExecution,
  deduplicateAgentResults,
  validateAgentState,
  isKnownAgent,
  trackAgentExecution
} from './agentTracker';
import { extractBaseAgentName, isExactAgentMatch, createIteratedAgentName } from './agent-matching';
import { getAgentIteration, incrementAgentIteration } from './agent-iteration-tracker';
import type { AgentExecution } from '@/types/store-types';
import type { AgentResult } from '@/types/layer-types';

// ============================================
// Display Name Generation Tests
// ============================================

describe('Agent Display Name Generation', () => {
  test('should return agent name for first iteration', () => {
    expect(generateAgentDisplayName('DataSubAgent', 1)).toBe('DataSubAgent');
  });

  test('should return agent name with iteration for multiple runs', () => {
    expect(generateAgentDisplayName('DataSubAgent', 2)).toBe('DataSubAgent (2)');
    expect(generateAgentDisplayName('TriageSubAgent', 3)).toBe('TriageSubAgent (3)');
  });
});

// ============================================
// Agent Execution Tests
// ============================================

describe('Agent Execution Management', () => {
  test('should create agent execution with correct defaults', () => {
    const execution = createAgentExecution('TestAgent', 1);
    
    expect(execution.name).toBe('TestAgent');
    expect(execution.iteration).toBe(1);
    expect(execution.status).toBe('running');
    expect(execution.startTime).toBeGreaterThan(0);
    expect(execution.endTime).toBeUndefined();
  });

  test('should complete agent execution properly', () => {
    const execution = createAgentExecution('TestAgent', 1);
    const result = { success: true, data: 'test data' };
    const completed = completeAgentExecution(execution, result);
    
    expect(completed.status).toBe('completed');
    expect(completed.endTime).toBeGreaterThanOrEqual(execution.startTime);
    expect(completed.result).toBe(result);
  });
});

// ============================================
// Deduplication Tests
// ============================================

describe('Agent Result Deduplication', () => {
  const mockAgentResult = (name: string, iteration: number): AgentResult => ({
    agentName: name,
    duration: 1000,
    result: { status: 'success', output: 'test' },
    metrics: { operations: 5 },
    iteration
  });

  test('should add new agent when none exist', () => {
    const newAgent = mockAgentResult('DataSubAgent', 1);
    const agentIterations = new Map<string, number>();
    const result = deduplicateAgentResults(undefined, newAgent, agentIterations);
    
    expect(result).toHaveLength(1);
    expect(result[0]).toBe(newAgent);
  });

  test('should replace existing agent on duplicate with exact matching', () => {
    const existingAgent = mockAgentResult('DataSubAgent', 1);
    const newAgent = mockAgentResult('DataSubAgent', 1);
    const existing = [existingAgent];
    const agentIterations = new Map([['DataSubAgent', 1]]);
    
    const result = deduplicateAgentResults(existing, newAgent, agentIterations);
    
    expect(result).toHaveLength(1);
    expect(result[0].agentName).toBe('DataSubAgent (2)');
    expect(result[0].iteration).toBe(2);
    expect(agentIterations.get('DataSubAgent')).toBe(2);
  });

  test('should add different agent without replacing', () => {
    const agent1 = mockAgentResult('DataSubAgent', 1);
    const agent2 = mockAgentResult('TriageSubAgent', 1);
    const existing = [agent1];
    const agentIterations = new Map([['DataSubAgent', 1]]);
    
    const result = deduplicateAgentResults(existing, agent2, agentIterations);
    
    expect(result).toHaveLength(2);
    expect(result).toContain(agent1);
    expect(result).toContain(agent2);
  });

  test('should not match similar agent names with exact matching', () => {
    const agent1 = mockAgentResult('Agent', 1);
    const agent2 = mockAgentResult('AgentSub', 1);
    const existing = [agent1];
    const agentIterations = new Map([['Agent', 1]]);
    
    const result = deduplicateAgentResults(existing, agent2, agentIterations);
    
    expect(result).toHaveLength(2);
    expect(result[0].agentName).toBe('Agent');
    expect(result[1].agentName).toBe('AgentSub');
  });
});

// ============================================
// State Validation Tests
// ============================================

describe('Agent State Validation', () => {
  test('should validate consistent agent state', () => {
    const executedAgents = new Map<string, AgentExecution>([
      ['DataSubAgent', createAgentExecution('DataSubAgent', 1)],
      ['TriageSubAgent', createAgentExecution('TriageSubAgent', 2)]
    ]);
    
    const agentIterations = new Map<string, number>([
      ['DataSubAgent', 1],
      ['TriageSubAgent', 2]
    ]);
    
    expect(validateAgentState(executedAgents, agentIterations)).toBe(true);
  });

  test('should detect inconsistent agent state', () => {
    const executedAgents = new Map<string, AgentExecution>([
      ['DataSubAgent', createAgentExecution('DataSubAgent', 1)],
      ['TriageSubAgent', createAgentExecution('TriageSubAgent', 2)]
    ]);
    
    const agentIterations = new Map<string, number>([
      ['DataSubAgent', 1]
      // Missing TriageSubAgent
    ]);
    
    expect(validateAgentState(executedAgents, agentIterations)).toBe(false);
  });
});

// ============================================
// Known Agent Tests
// ============================================

describe('Known Agent Recognition', () => {
  test('should recognize known agents', () => {
    expect(isKnownAgent('DataSubAgent')).toBe(true);
    expect(isKnownAgent('TriageSubAgent')).toBe(true);
    expect(isKnownAgent('CorpusAdminSubAgent')).toBe(true);
  });

  test('should reject unknown agents', () => {
    expect(isKnownAgent('UnknownAgent')).toBe(false);
    expect(isKnownAgent('RandomAgent')).toBe(false);
  });
});

// ============================================
// Agent Matching Tests
// ============================================

describe('Agent Matching Utilities', () => {
  test('should extract base agent name correctly', () => {
    expect(extractBaseAgentName('DataSubAgent')).toBe('DataSubAgent');
    expect(extractBaseAgentName('DataSubAgent (2)')).toBe('DataSubAgent');
    expect(extractBaseAgentName('TriageSubAgent (iteration 3)')).toBe('TriageSubAgent');
    expect(extractBaseAgentName('TestAgent (Run #4)')).toBe('TestAgent');
  });

  test('should perform exact agent matching', () => {
    expect(isExactAgentMatch('DataSubAgent', 'DataSubAgent')).toBe(true);
    expect(isExactAgentMatch('DataSubAgent (2)', 'DataSubAgent')).toBe(true);
    expect(isExactAgentMatch('Agent', 'AgentSub')).toBe(false);
    expect(isExactAgentMatch('AgentSub', 'Agent')).toBe(false);
  });

  test('should create iterated agent names', () => {
    expect(createIteratedAgentName('TestAgent', 1)).toBe('TestAgent');
    expect(createIteratedAgentName('TestAgent', 2)).toBe('TestAgent (2)');
    expect(createIteratedAgentName('TestAgent', 5)).toBe('TestAgent (5)');
  });
});

// ============================================
// Agent Iteration Tracking Tests
// ============================================

describe('Agent Iteration Tracking', () => {
  test('should get correct iteration count', () => {
    const iterations = new Map([['TestAgent', 3]]);
    
    expect(getAgentIteration(iterations, 'TestAgent')).toBe(3);
    expect(getAgentIteration(iterations, 'NewAgent')).toBe(1);
  });

  test('should increment iteration correctly', () => {
    const iterations = new Map([['TestAgent', 2]]);
    
    const newIteration = incrementAgentIteration(iterations, 'TestAgent');
    
    expect(newIteration).toBe(3);
    expect(iterations.get('TestAgent')).toBe(3);
  });

  test('should track agent execution', () => {
    const executions = new Map<string, AgentExecution>();
    const iterations = new Map([['TestAgent', 1]]);
    
    const execution = trackAgentExecution(executions, iterations, 'TestAgent');
    
    expect(execution.name).toBe('TestAgent');
    expect(execution.iteration).toBe(1);
    expect(executions.has('TestAgent')).toBe(true);
  });
});