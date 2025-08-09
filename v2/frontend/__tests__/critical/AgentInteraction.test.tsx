import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { renderHook } from '@testing-library/react-hooks';
import userEvent from '@testing-library/user-event';
import WS from 'jest-websocket-mock';
import { useChatWebSocket } from '../../hooks/useChatWebSocket';
import { WebSocketProvider } from '../../providers/WebSocketProvider';
import MainChat from '../../components/chat/MainChat';
import SubAgentStatus from '../../components/SubAgentStatus';

describe('Agent Interaction Tests', () => {
  let server: WS;
  const mockRunId = 'test-run-id-123';
  
  beforeEach(() => {
    server = new WS(`ws://localhost:8000/ws/${mockRunId}`);
  });

  afterEach(() => {
    WS.clean();
  });

  describe('Agent Lifecycle Management', () => {
    it('should start agent workflow on user message submission', async () => {
      const TestWrapper = () => (
        <WebSocketProvider>
          <MainChat />
        </WebSocketProvider>
      );

      render(<TestWrapper />);
      
      const messageInput = screen.getByPlaceholderText(/type your message/i);
      const sendButton = screen.getByRole('button', { name: /send/i });

      await userEvent.type(messageInput, 'Optimize my AI workload for inference speed');
      fireEvent.click(sendButton);

      await server.connected;
      await waitFor(() => {
        expect(server.messages).toHaveLength(1);
        const message = JSON.parse(server.messages[0] as string);
        expect(message.type).toBe('user_message');
        expect(message.content).toBe('Optimize my AI workload for inference speed');
      });
    });

    it('should handle agent_started event and show workflow progress', async () => {
      const { result } = renderHook(() => useChatWebSocket(mockRunId), {
        wrapper: WebSocketProvider,
      });

      await server.connected;

      act(() => {
        server.send(JSON.stringify({
          type: 'agent_started',
          payload: {
            run_id: mockRunId,
            total_steps: 5,
            estimated_duration: 120,
          },
        }));
      });

      await waitFor(() => {
        expect(result.current.agentStatus).toBe('RUNNING');
        expect(result.current.workflowProgress).toEqual({
          current_step: 0,
          total_steps: 5,
          estimated_duration: 120,
        });
      });
    });

    it('should track sub-agent execution stages', async () => {
      const TestWrapper = () => (
        <WebSocketProvider>
          <SubAgentStatus runId={mockRunId} />
        </WebSocketProvider>
      );

      render(<TestWrapper />);
      await server.connected;

      const subAgentUpdates = [
        {
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: 'TriageSubAgent',
            state: {
              lifecycle: 'RUNNING',
              messages: ['Analyzing request type...'],
              progress: 25,
            },
          },
        },
        {
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: 'TriageSubAgent',
            state: {
              lifecycle: 'COMPLETED',
              messages: ['Request classified as optimization task'],
              progress: 100,
            },
          },
        },
        {
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: 'DataSubAgent',
            state: {
              lifecycle: 'RUNNING',
              messages: ['Gathering system metrics...'],
              progress: 15,
            },
          },
        },
      ];

      for (const update of subAgentUpdates) {
        act(() => {
          server.send(JSON.stringify(update));
        });
      }

      await waitFor(() => {
        expect(screen.getByText('Request classified as optimization task')).toBeInTheDocument();
        expect(screen.getByText('Gathering system metrics...')).toBeInTheDocument();
      });
    });
  });

  describe('Real-time Message Streaming', () => {
    it('should handle streaming message updates in real-time', async () => {
      const { result } = renderHook(() => useChatWebSocket(mockRunId), {
        wrapper: WebSocketProvider,
      });

      await server.connected;

      const streamingMessages = [
        { type: 'message_chunk', payload: { content: 'Analyzing', is_complete: false } },
        { type: 'message_chunk', payload: { content: 'Analyzing your', is_complete: false } },
        { type: 'message_chunk', payload: { content: 'Analyzing your workload...', is_complete: true } },
      ];

      for (const chunk of streamingMessages) {
        act(() => {
          server.send(JSON.stringify(chunk));
        });
        
        await waitFor(() => {
          expect(result.current.streamingMessage).toContain(chunk.payload.content);
        });
      }

      // Verify final complete message
      expect(result.current.streamingMessage).toBe('Analyzing your workload...');
      expect(result.current.isStreaming).toBe(false);
    });

    it('should handle concurrent streaming from multiple sub-agents', async () => {
      const { result } = renderHook(() => useChatWebSocket(mockRunId), {
        wrapper: WebSocketProvider,
      });

      await server.connected;

      const concurrentStreams = [
        {
          type: 'sub_agent_stream',
          payload: {
            agent: 'DataSubAgent',
            content: 'CPU usage: 75%',
            stream_id: 'stream_1',
          },
        },
        {
          type: 'sub_agent_stream',
          payload: {
            agent: 'OptimizationsCoreSubAgent',
            content: 'Identifying bottlenecks...',
            stream_id: 'stream_2',
          },
        },
      ];

      concurrentStreams.forEach(stream => {
        act(() => {
          server.send(JSON.stringify(stream));
        });
      });

      await waitFor(() => {
        expect(result.current.subAgentStreams).toHaveProperty('stream_1');
        expect(result.current.subAgentStreams).toHaveProperty('stream_2');
        expect(result.current.subAgentStreams.stream_1.content).toBe('CPU usage: 75%');
        expect(result.current.subAgentStreams.stream_2.content).toBe('Identifying bottlenecks...');
      });
    });
  });

  describe('Error Handling and Recovery', () => {
    it('should handle sub-agent failures gracefully', async () => {
      const { result } = renderHook(() => useChatWebSocket(mockRunId), {
        wrapper: WebSocketProvider,
      });

      await server.connected;

      act(() => {
        server.send(JSON.stringify({
          type: 'sub_agent_error',
          payload: {
            sub_agent_name: 'DataSubAgent',
            error: {
              type: 'TOOL_EXECUTION_ERROR',
              message: 'Failed to connect to monitoring API',
              code: 'CONNECTION_TIMEOUT',
            },
            recovery_action: 'RETRY_WITH_FALLBACK',
          },
        }));
      });

      await waitFor(() => {
        expect(result.current.errors).toContainEqual(
          expect.objectContaining({
            agent: 'DataSubAgent',
            type: 'TOOL_EXECUTION_ERROR',
            recoverable: true,
          })
        );
      });
    });

    it('should implement fallback strategies for agent failures', async () => {
      const { result } = renderHook(() => useChatWebSocket(mockRunId), {
        wrapper: WebSocketProvider,
      });

      await server.connected;

      // Simulate critical agent failure
      act(() => {
        server.send(JSON.stringify({
          type: 'agent_failure',
          payload: {
            run_id: mockRunId,
            failed_agent: 'OptimizationsCoreSubAgent',
            fallback_strategy: 'SKIP_TO_REPORTING',
            reason: 'Maximum retry attempts exceeded',
          },
        }));
      });

      await waitFor(() => {
        expect(result.current.fallbackActive).toBe(true);
        expect(result.current.fallbackStrategy).toBe('SKIP_TO_REPORTING');
      });
    });

    it('should handle partial workflow completion', async () => {
      const { result } = renderHook(() => useChatWebSocket(mockRunId), {
        wrapper: WebSocketProvider,
      });

      await server.connected;

      act(() => {
        server.send(JSON.stringify({
          type: 'partial_completion',
          payload: {
            run_id: mockRunId,
            completed_agents: ['TriageSubAgent', 'DataSubAgent'],
            failed_agents: ['OptimizationsCoreSubAgent'],
            partial_results: {
              system_analysis: { cpu_usage: 75, memory_usage: 60 },
              recommendations: ['Consider upgrading CPU', 'Optimize memory allocation'],
            },
          },
        }));
      });

      await waitFor(() => {
        expect(result.current.partialResults).toBeDefined();
        expect(result.current.partialResults.system_analysis).toEqual({
          cpu_usage: 75,
          memory_usage: 60,
        });
        expect(result.current.completionStatus).toBe('PARTIAL');
      });
    });
  });

  describe('Agent Result Processing', () => {
    it('should aggregate results from all sub-agents', async () => {
      const { result } = renderHook(() => useChatWebSocket(mockRunId), {
        wrapper: WebSocketProvider,
      });

      await server.connected;

      const agentResults = [
        {
          type: 'sub_agent_completed',
          payload: {
            sub_agent_name: 'TriageSubAgent',
            result: {
              task_type: 'optimization',
              priority: 'high',
              estimated_complexity: 'medium',
            },
          },
        },
        {
          type: 'sub_agent_completed',
          payload: {
            sub_agent_name: 'DataSubAgent',
            result: {
              metrics: { latency: 150, throughput: 1000 },
              bottlenecks: ['CPU', 'Network I/O'],
            },
          },
        },
        {
          type: 'agent_completed',
          payload: {
            run_id: mockRunId,
            final_result: {
              optimization_plan: 'Implement model quantization and parallel processing',
              expected_improvement: '40% latency reduction',
            },
          },
        },
      ];

      for (const resultMsg of agentResults) {
        act(() => {
          server.send(JSON.stringify(resultMsg));
        });
      }

      await waitFor(() => {
        expect(result.current.finalResult).toEqual({
          optimization_plan: 'Implement model quantization and parallel processing',
          expected_improvement: '40% latency reduction',
        });
        expect(result.current.agentStatus).toBe('COMPLETED');
      });
    });

    it('should handle result validation and formatting', async () => {
      const { result } = renderHook(() => useChatWebSocket(mockRunId), {
        wrapper: WebSocketProvider,
      });

      await server.connected;

      // Test malformed result handling
      act(() => {
        server.send(JSON.stringify({
          type: 'agent_completed',
          payload: {
            run_id: mockRunId,
            final_result: null, // Invalid result
          },
        }));
      });

      await waitFor(() => {
        expect(result.current.errors).toContainEqual(
          expect.objectContaining({
            type: 'INVALID_RESULT',
            message: expect.stringContaining('null or invalid'),
          })
        );
      });
    });
  });

  describe('Workflow State Persistence', () => {
    it('should maintain workflow state across page refreshes', async () => {
      const mockState = {
        runId: mockRunId,
        agentStatus: 'RUNNING',
        currentStep: 3,
        totalSteps: 5,
        results: { triage: 'completed', data: 'in_progress' },
      };

      sessionStorage.setItem(`agent_workflow_${mockRunId}`, JSON.stringify(mockState));

      const { result } = renderHook(() => useChatWebSocket(mockRunId), {
        wrapper: WebSocketProvider,
      });

      await waitFor(() => {
        expect(result.current.agentStatus).toBe('RUNNING');
        expect(result.current.workflowProgress.current_step).toBe(3);
        expect(result.current.workflowProgress.total_steps).toBe(5);
      });
    });

    it('should handle workflow resumption after interruption', async () => {
      const { result } = renderHook(() => useChatWebSocket(mockRunId), {
        wrapper: WebSocketProvider,
      });

      await server.connected;

      // Simulate workflow resumption
      act(() => {
        server.send(JSON.stringify({
          type: 'workflow_resumed',
          payload: {
            run_id: mockRunId,
            resumed_from_step: 'OptimizationsCoreSubAgent',
            previous_results: {
              triage_result: { type: 'optimization' },
              data_result: { metrics: 'collected' },
            },
          },
        }));
      });

      await waitFor(() => {
        expect(result.current.workflowResumed).toBe(true);
        expect(result.current.previousResults).toBeDefined();
      });
    });
  });
});