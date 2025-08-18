// JEST MODULE HOISTING - Mocks BEFORE imports
// Mock global fetch and WebSocket
global.fetch = jest.fn();
global.WebSocket = jest.fn(() => ({
  send: jest.fn(),
  close: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  readyState: WebSocket.OPEN
})) as any;

import { act, renderHook } from '@testing-library/react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import type {
  AgentStartedEvent,
  ToolExecutingEvent,
  AgentThinkingEvent,
  PartialResultEvent,
  AgentCompletedEvent,
  FinalReportEvent,
  ErrorEvent,
} from '@/types/unified-chat';

describe('UnifiedChatStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    const { result } = renderHook(() => useUnifiedChatStore());
    act(() => {
      result.current.resetLayers();
    });
  });

  describe('Layer Updates', () => {
    it('should update fast layer data', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      act(() => {
        result.current.updateFastLayer({
          agentName: 'Test Agent',
          activeTools: ['tool1'],
          timestamp: 123456,
          runId: 'test-run',
        });
      });

      expect(result.current.fastLayerData).toEqual({
        agentName: 'Test Agent',
        activeTools: ['tool1'],
        timestamp: 123456,
        runId: 'test-run',
      });
    });

    it('should update medium layer data and accumulate partial content', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      act(() => {
        result.current.updateMediumLayer({
          thought: 'Thinking...',
          partialContent: 'First part',
          stepNumber: 1,
          totalSteps: 3,
          agentName: 'Test Agent',
        });
      });

      expect(result.current.mediumLayerData?.partialContent).toBe('First part');

      act(() => {
        result.current.updateMediumLayer({
          partialContent: 'First partSecond part',
        });
      });

      expect(result.current.mediumLayerData?.partialContent).toBe('First partSecond part');
    });

    it('should update slow layer data and accumulate completed agents', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      act(() => {
        result.current.updateSlowLayer({
          completedAgents: [{
            agentName: 'Agent1',
            duration: 1000,
            result: {},
            metrics: {},
          }],
        });
      });

      expect(result.current.slowLayerData?.completedAgents).toHaveLength(1);

      act(() => {
        result.current.updateSlowLayer({
          completedAgents: [{
            agentName: 'Agent2',
            duration: 2000,
            result: {},
            metrics: {},
          }],
        });
      });

      expect(result.current.slowLayerData?.completedAgents).toHaveLength(2);
    });
  });

  describe('WebSocket Event Handling', () => {
    it('should handle agent_started event', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const event: AgentStartedEvent = {
        type: 'agent_started',
        payload: {
          agent_name: 'Supervisor Agent',
          timestamp: Date.now(),
          run_id: 'run-456',
        },
      };

      act(() => {
        result.current.handleWebSocketEvent(event);
      });

      expect(result.current.isProcessing).toBe(true);
      expect(result.current.currentRunId).toBe('run-456');
      expect(result.current.fastLayerData?.agentName).toBe('Supervisor Agent');
      expect(result.current.mediumLayerData).toBeNull();
      expect(result.current.slowLayerData).toBeNull();
    });

    it('should handle tool_executing event', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      // First set up fast layer data
      act(() => {
        result.current.updateFastLayer({
          agentName: 'Test Agent',
          activeTools: [],
          timestamp: Date.now(),
          runId: 'test-run',
        });
      });

      const event: ToolExecutingEvent = {
        type: 'tool_executing',
        payload: {
          tool_name: 'cost_optimizer',
          agent_name: 'Test Agent',
          timestamp: Date.now(),
        },
      };

      act(() => {
        result.current.handleWebSocketEvent(event);
      });

      expect(result.current.fastLayerData?.activeTools).toContain('cost_optimizer');
    });

    it('should handle agent_thinking event', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const event: AgentThinkingEvent = {
        type: 'agent_thinking',
        payload: {
          thought: 'Analyzing workload patterns...',
          agent_name: 'Analysis Agent',
          step_number: 2,
          total_steps: 5,
        },
      };

      act(() => {
        result.current.handleWebSocketEvent(event);
      });

      expect(result.current.mediumLayerData?.thought).toBe('Analyzing workload patterns...');
      expect(result.current.mediumLayerData?.stepNumber).toBe(2);
      expect(result.current.mediumLayerData?.totalSteps).toBe(5);
    });

    it('should handle partial_result event', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const event1: PartialResultEvent = {
        type: 'partial_result',
        payload: {
          content: 'Initial analysis shows',
          agent_name: 'Analysis Agent',
          is_complete: false,
        },
      };

      act(() => {
        result.current.handleWebSocketEvent(event1);
      });

      expect(result.current.mediumLayerData?.partialContent).toBe('Initial analysis shows');

      const event2: PartialResultEvent = {
        type: 'partial_result',
        payload: {
          content: ' potential optimizations',
          agent_name: 'Analysis Agent',
          is_complete: false,
        },
      };

      act(() => {
        result.current.handleWebSocketEvent(event2);
      });

      expect(result.current.mediumLayerData?.partialContent).toBe('Initial analysis shows potential optimizations');
    });

    it('should handle agent_completed event', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      const event: AgentCompletedEvent = {
        type: 'agent_completed',
        payload: {
          agent_name: 'Optimization Agent',
          duration_ms: 3000,
          result: { optimizations: ['cache', 'batch'] },
          metrics: { tokens: 500 },
        },
      };

      act(() => {
        result.current.handleWebSocketEvent(event);
      });

      expect(result.current.slowLayerData?.completedAgents).toHaveLength(1);
      expect(result.current.slowLayerData?.completedAgents[0].agentName).toBe('Optimization Agent');
      expect(result.current.slowLayerData?.completedAgents[0].duration).toBe(3000);
    });

    it('should handle final_report event', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      act(() => {
        result.current.setProcessing(true);
      });

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

      act(() => {
        result.current.handleWebSocketEvent(event);
      });

      expect(result.current.isProcessing).toBe(false);
      expect(result.current.slowLayerData?.finalReport).toBeDefined();
      expect(result.current.slowLayerData?.finalReport?.recommendations).toHaveLength(1);
      expect(result.current.slowLayerData?.totalDuration).toBe(10000);
    });

    it('should handle error event', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      act(() => {
        result.current.setProcessing(true);
      });

      const event: ErrorEvent = {
        type: 'error',
        payload: {
          error_message: 'Connection timeout',
          error_code: 'TIMEOUT',
          agent_name: 'Network Agent',
          recoverable: false,
        },
      };

      act(() => {
        result.current.handleWebSocketEvent(event);
      });

      expect(result.current.isProcessing).toBe(false);
      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].content).toBe('Connection timeout');
    });
  });

  describe('State Management', () => {
    it('should reset all layers', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      // Set some data
      act(() => {
        result.current.updateFastLayer({
          agentName: 'Test',
          activeTools: [],
          timestamp: Date.now(),
          runId: 'test',
        });
        result.current.setProcessing(true);
      });

      // Reset
      act(() => {
        result.current.resetLayers();
      });

      expect(result.current.fastLayerData).toBeNull();
      expect(result.current.mediumLayerData).toBeNull();
      expect(result.current.slowLayerData).toBeNull();
      expect(result.current.currentRunId).toBeNull();
      expect(result.current.isProcessing).toBe(false);
    });

    it('should add messages to history', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      act(() => {
        result.current.addMessage({
          id: 'msg1',
          role: 'user',
          content: 'Hello',
          timestamp: Date.now(),
        });
      });

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].content).toBe('Hello');
    });

    it('should set connection status', () => {
      const { result } = renderHook(() => useUnifiedChatStore());
      
      act(() => {
        result.current.setConnectionStatus(true);
      });

      expect(result.current.isConnected).toBe(true);
      expect(result.current.connectionError).toBeNull();

      act(() => {
        result.current.setConnectionStatus(false, 'Connection lost');
      });

      expect(result.current.isConnected).toBe(false);
      expect(result.current.connectionError).toBe('Connection lost');
    });
  });
});