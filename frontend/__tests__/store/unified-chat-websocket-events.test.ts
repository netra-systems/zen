/**
 * UnifiedChatStore WebSocket Events Tests - Real Store Behavior Testing
 * 
 * BVJ (Business Value Justification):
 * - Segment: All (Real-time communication)
 * - Business Goal: Ensure reliable WebSocket event handling
 * - Value Impact: Critical for real-time agent interaction
 * - Revenue Impact: WebSocket failures lead to poor UX and churn
 * 
 * CRITICAL: Tests real store behavior, no mocking of store logic
 * Architecture: ≤300 lines, functions ≤8 lines each
 */

import { UnifiedChatStoreTestUtils, GlobalTestUtils } from './store-test-utils';
import type {
  AgentStartedEvent,
  ToolExecutingEvent,
  AgentThinkingEvent,
  PartialResultEvent,
  AgentCompletedEvent,
  FinalReportEvent,
  ErrorEvent,
} from '@/types/unified-chat';

describe('UnifiedChatStore - WebSocket Events', () => {
  let storeResult: ReturnType<typeof UnifiedChatStoreTestUtils.initializeStore>;

  // Setup test environment (≤8 lines)
  beforeAll(() => {
    GlobalTestUtils.setupStoreTestEnvironment();
  });

  // Reset store before each test (≤8 lines)
  beforeEach(() => {
    storeResult = UnifiedChatStoreTestUtils.initializeStore();
  });

  // Cleanup after all tests (≤8 lines)
  afterAll(() => {
    GlobalTestUtils.cleanupStoreTestEnvironment();
  });

  describe('Agent Started Events', () => {
    it('should handle agent_started event correctly', () => {
      const event: AgentStartedEvent = {
        type: 'agent_started',
        payload: {
          agent_name: 'Supervisor Agent',
          timestamp: Date.now(),
          run_id: 'run-456',
        },
      };

      storeResult.current.handleWebSocketEvent(event);

      expect(storeResult.current.isProcessing).toBe(true);
      expect(storeResult.current.currentRunId).toBe('run-456');
      expect(storeResult.current.fastLayerData?.agentName).toBe('Supervisor Agent');
      expect(storeResult.current.mediumLayerData).toBeNull();
      expect(storeResult.current.slowLayerData).toBeNull();
    });

    it('should reset layers on new agent start', () => {
      // First set up some existing data
      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, {
        agentName: 'Old Agent',
        activeTools: ['old-tool'],
        timestamp: Date.now() - 1000,
        runId: 'old-run',
      });

      const event: AgentStartedEvent = {
        type: 'agent_started',
        payload: {
          agent_name: 'New Agent',
          timestamp: Date.now(),
          run_id: 'new-run',
        },
      };

      storeResult.current.handleWebSocketEvent(event);
      expect(storeResult.current.currentRunId).toBe('new-run');
      expect(storeResult.current.fastLayerData?.agentName).toBe('New Agent');
    });
  });

  describe('Tool Executing Events', () => {
    it('should handle tool_executing event correctly', () => {
      // First set up fast layer data
      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, {
        agentName: 'Test Agent',
        activeTools: [],
        timestamp: Date.now(),
        runId: 'test-run',
      });

      const event: ToolExecutingEvent = {
        type: 'tool_executing',
        payload: {
          tool_name: 'cost_optimizer',
          agent_name: 'Test Agent',
          timestamp: Date.now(),
        },
      };

      storeResult.current.handleWebSocketEvent(event);
      expect(storeResult.current.fastLayerData?.activeTools).toContain('cost_optimizer');
    });

    it('should accumulate multiple active tools', () => {
      UnifiedChatStoreTestUtils.updateFastLayerAndVerify(storeResult, {
        agentName: 'Test Agent',
        activeTools: ['tool1'],
        timestamp: Date.now(),
        runId: 'test-run',
      });

      const event1: ToolExecutingEvent = {
        type: 'tool_executing',
        payload: {
          tool_name: 'tool2',
          agent_name: 'Test Agent',
          timestamp: Date.now(),
        },
      };

      const event2: ToolExecutingEvent = {
        type: 'tool_executing',
        payload: {
          tool_name: 'tool3',
          agent_name: 'Test Agent',
          timestamp: Date.now(),
        },
      };

      storeResult.current.handleWebSocketEvent(event1);
      storeResult.current.handleWebSocketEvent(event2);
      
      expect(storeResult.current.fastLayerData?.activeTools).toEqual(['tool1', 'tool2', 'tool3']);
    });
  });

  describe('Agent Thinking Events', () => {
    it('should handle agent_thinking event correctly', () => {
      const event: AgentThinkingEvent = {
        type: 'agent_thinking',
        payload: {
          thought: 'Analyzing workload patterns...',
          agent_name: 'Analysis Agent',
          step_number: 2,
          total_steps: 5,
        },
      };

      storeResult.current.handleWebSocketEvent(event);

      expect(storeResult.current.mediumLayerData?.thought).toBe('Analyzing workload patterns...');
      expect(storeResult.current.mediumLayerData?.stepNumber).toBe(2);
      expect(storeResult.current.mediumLayerData?.totalSteps).toBe(5);
    });

    it('should update step progress correctly', () => {
      const event1: AgentThinkingEvent = {
        type: 'agent_thinking',
        payload: {
          thought: 'Starting analysis...',
          agent_name: 'Analysis Agent',
          step_number: 1,
          total_steps: 3,
        },
      };

      const event2: AgentThinkingEvent = {
        type: 'agent_thinking',
        payload: {
          thought: 'Processing data...',
          agent_name: 'Analysis Agent',
          step_number: 2,
          total_steps: 3,
        },
      };

      storeResult.current.handleWebSocketEvent(event1);
      expect(storeResult.current.mediumLayerData?.stepNumber).toBe(1);

      storeResult.current.handleWebSocketEvent(event2);
      expect(storeResult.current.mediumLayerData?.stepNumber).toBe(2);
      expect(storeResult.current.mediumLayerData?.thought).toBe('Processing data...');
    });
  });

  describe('Partial Result Events', () => {
    it('should handle partial_result event correctly', () => {
      const event1: PartialResultEvent = {
        type: 'partial_result',
        payload: {
          content: 'Initial analysis shows',
          agent_name: 'Analysis Agent',
          is_complete: false,
        },
      };

      storeResult.current.handleWebSocketEvent(event1);
      expect(storeResult.current.mediumLayerData?.partialContent).toBe('Initial analysis shows');

      const event2: PartialResultEvent = {
        type: 'partial_result',
        payload: {
          content: ' potential optimizations',
          agent_name: 'Analysis Agent',
          is_complete: false,
        },
      };

      storeResult.current.handleWebSocketEvent(event2);
      expect(storeResult.current.mediumLayerData?.partialContent).toBe('Initial analysis shows potential optimizations');
    });

    it('should handle complete partial results', () => {
      const event: PartialResultEvent = {
        type: 'partial_result',
        payload: {
          content: 'Complete analysis result',
          agent_name: 'Analysis Agent',
          is_complete: true,
        },
      };

      storeResult.current.handleWebSocketEvent(event);
      expect(storeResult.current.mediumLayerData?.partialContent).toBe('Complete analysis result');
    });
  });

  describe('Agent Completed Events', () => {
    it('should handle agent_completed event correctly', () => {
      const event: AgentCompletedEvent = {
        type: 'agent_completed',
        payload: {
          agent_name: 'Optimization Agent',
          duration_ms: 3000,
          result: { optimizations: ['cache', 'batch'] },
          metrics: { tokens: 500 },
        },
      };

      storeResult.current.handleWebSocketEvent(event);

      expect(storeResult.current.slowLayerData?.completedAgents).toHaveLength(1);
      expect(storeResult.current.slowLayerData?.completedAgents[0].agentName).toBe('Optimization Agent');
      expect(storeResult.current.slowLayerData?.completedAgents[0].duration).toBe(3000);
    });

    it('should accumulate multiple completed agents', () => {
      const event1: AgentCompletedEvent = {
        type: 'agent_completed',
        payload: {
          agent_name: 'Agent1',
          duration_ms: 1000,
          result: { data: 'result1' },
          metrics: { tokens: 100 },
        },
      };

      const event2: AgentCompletedEvent = {
        type: 'agent_completed',
        payload: {
          agent_name: 'Agent2',
          duration_ms: 2000,
          result: { data: 'result2' },
          metrics: { tokens: 200 },
        },
      };

      storeResult.current.handleWebSocketEvent(event1);
      storeResult.current.handleWebSocketEvent(event2);

      expect(storeResult.current.slowLayerData?.completedAgents).toHaveLength(2);
      expect(storeResult.current.slowLayerData?.completedAgents[1].agentName).toBe('Agent2');
    });
  });

  describe('Final Report Events', () => {
    it('should handle final_report event correctly', () => {
      UnifiedChatStoreTestUtils.setProcessingAndVerify(storeResult, true);

      const event: FinalReportEvent = {
        type: 'final_report',
        payload: {
          report: { summary: 'Complete analysis' },
          total_duration_ms: 10000,
          agent_metrics: [],
          recommendations: [{
            id: 'rec1',
            title: 'Enable caching',
            description: 'Implement Redis caching',
            impact: 'high',
            effort: 'low',
            category: 'performance',
          }],
          action_plan: [{
            id: 'step1',
            step_number: 1,
            description: 'Install Redis',
            expected_outcome: 'Redis running',
          }],
        },
      };

      storeResult.current.handleWebSocketEvent(event);

      expect(storeResult.current.isProcessing).toBe(false);
      expect(storeResult.current.slowLayerData?.finalReport).toBeDefined();
      expect(storeResult.current.slowLayerData?.finalReport?.recommendations).toHaveLength(1);
      expect(storeResult.current.slowLayerData?.totalDuration).toBe(10000);
    });
  });

  describe('Error Events', () => {
    it('should handle error event correctly', () => {
      UnifiedChatStoreTestUtils.setProcessingAndVerify(storeResult, true);

      const event: ErrorEvent = {
        type: 'error',
        payload: {
          error_message: 'Connection timeout',
          error_code: 'TIMEOUT',
          agent_name: 'Network Agent',
          recoverable: false,
        },
      };

      storeResult.current.handleWebSocketEvent(event);

      expect(storeResult.current.isProcessing).toBe(false);
      expect(storeResult.current.messages).toHaveLength(1);
      expect(storeResult.current.messages[0].content).toBe('Connection timeout');
    });

    it('should handle recoverable errors differently', () => {
      const recoverableEvent: ErrorEvent = {
        type: 'error',
        payload: {
          error_message: 'Temporary network issue',
          error_code: 'NETWORK_RETRY',
          agent_name: 'Network Agent',
          recoverable: true,
        },
      };

      storeResult.current.handleWebSocketEvent(recoverableEvent);
      expect(storeResult.current.messages[0].content).toContain('Temporary network issue');
    });
  });
});