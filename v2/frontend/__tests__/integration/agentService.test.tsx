import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import WS from 'jest-websocket-mock';
import { useChatStore } from '../../store/chat';
import { useAuth } from '../../auth/context';
import MainChat from '../../components/chat/MainChat';

jest.mock('../../auth/context');
jest.mock('../../store/chat');

const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockUseChatStore = useChatStore as jest.MockedFunction<typeof useChatStore>;

describe('Agent Service Integration', () => {
  let server: WS;
  const wsUrl = 'ws://localhost:8000/ws';
  const mockAuthToken = 'mock-jwt-token';
  
  const mockAddMessage = jest.fn();
  const mockSetSubAgentName = jest.fn();
  const mockSetSubAgentStatus = jest.fn();
  const mockSetProcessing = jest.fn();

  beforeEach(() => {
    server = new WS(wsUrl);
    
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: { id: '1', email: 'test@example.com', name: 'Test User' },
      login: jest.fn(),
      logout: jest.fn(),
      loading: false,
      error: null,
      token: mockAuthToken,
    } as any);

    mockUseChatStore.mockReturnValue({
      messages: [],
      subAgentName: 'Netra Agent',
      subAgentStatus: null,
      isProcessing: false,
      addMessage: mockAddMessage,
      setSubAgentName: mockSetSubAgentName,
      setSubAgentStatus: mockSetSubAgentStatus,
      setProcessing: mockSetProcessing,
      reset: jest.fn(),
    });

    jest.clearAllMocks();
  });

  afterEach(() => {
    WS.clean();
  });

  describe('Full Agent Workflow', () => {
    it('should handle complete multi-agent workflow', async () => {
      render(<MainChat />);
      
      await server.connected;
      
      // Simulate user sending a message
      const messageInput = screen.getByRole('textbox');
      const sendButton = screen.getByRole('button', { name: /send/i });
      
      await userEvent.type(messageInput, 'Analyze my workload performance');
      await userEvent.click(sendButton);

      // Verify user message was sent via WebSocket
      expect(server).toHaveReceivedMessages([
        JSON.stringify({ type: 'auth', token: mockAuthToken }),
        JSON.stringify({
          type: 'user_message',
          payload: {
            text: 'Analyze my workload performance',
            references: []
          }
        })
      ]);

      // Simulate agent workflow responses
      const agentWorkflow = [
        {
          type: 'agent_started',
          payload: { message: 'Starting analysis...' }
        },
        {
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: 'TriageAgent',
            state: {
              lifecycle: 'running',
              tools: ['request_analyzer']
            }
          }
        },
        {
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: 'DataAgent',
            state: {
              lifecycle: 'running',
              tools: ['workload_collector', 'performance_monitor']
            }
          }
        },
        {
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: 'OptimizationAgent',
            state: {
              lifecycle: 'running',
              tools: ['cost_analyzer', 'performance_optimizer']
            }
          }
        },
        {
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: 'ReportingAgent',
            state: {
              lifecycle: 'running',
              tools: ['report_generator', 'visualization_builder']
            }
          }
        },
        {
          type: 'agent_finished',
          payload: {
            result: 'Analysis complete',
            recommendations: ['Optimize memory usage', 'Scale horizontally']
          }
        }
      ];

      // Send each workflow step
      for (const step of agentWorkflow) {
        server.send(JSON.stringify(step));
        await waitFor(() => {
          expect(mockSetProcessing).toHaveBeenCalled();
        });
      }

      // Verify all sub-agents were invoked
      expect(mockSetSubAgentName).toHaveBeenCalledWith('TriageAgent');
      expect(mockSetSubAgentName).toHaveBeenCalledWith('DataAgent');
      expect(mockSetSubAgentName).toHaveBeenCalledWith('OptimizationAgent');
      expect(mockSetSubAgentName).toHaveBeenCalledWith('ReportingAgent');

      // Verify processing states
      expect(mockSetProcessing).toHaveBeenCalledWith(true);
      expect(mockSetProcessing).toHaveBeenLastCalledWith(false);
    });

    it('should handle agent error and recovery', async () => {
      render(<MainChat />);
      
      await server.connected;

      // Start workflow
      server.send(JSON.stringify({
        type: 'agent_started',
        payload: {}
      }));

      // Simulate error in DataAgent
      server.send(JSON.stringify({
        type: 'error',
        payload: {
          error: 'DataAgent failed: Unable to connect to data source',
          sub_agent: 'DataAgent'
        }
      }));

      // Verify error handling
      await waitFor(() => {
        expect(mockSetProcessing).toHaveBeenCalledWith(false);
        expect(mockAddMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            role: 'assistant',
            content: 'Error: DataAgent failed: Unable to connect to data source',
            error: true
          })
        );
      });

      // Simulate recovery with retry
      server.send(JSON.stringify({
        type: 'agent_started',
        payload: { message: 'Retrying with backup data source...' }
      }));

      server.send(JSON.stringify({
        type: 'sub_agent_update',
        payload: {
          sub_agent_name: 'DataAgent',
          state: {
            lifecycle: 'running',
            tools: ['backup_collector']
          }
        }
      }));

      server.send(JSON.stringify({
        type: 'agent_finished',
        payload: { result: 'Recovery successful' }
      }));

      // Verify recovery
      expect(mockSetProcessing).toHaveBeenCalledWith(true);
      expect(mockSetProcessing).toHaveBeenLastCalledWith(false);
      expect(mockAddMessage).toHaveBeenLastCalledWith(
        expect.objectContaining({
          content: 'Task completed successfully.'
        })
      );
    });

    it('should handle user stopping agent execution', async () => {
      mockUseChatStore.mockReturnValue({
        messages: [],
        subAgentName: 'DataAgent',
        subAgentStatus: { status: 'running', tools: ['analyzer'] },
        isProcessing: true,
        addMessage: mockAddMessage,
        setSubAgentName: mockSetSubAgentName,
        setSubAgentStatus: mockSetSubAgentStatus,
        setProcessing: mockSetProcessing,
        reset: jest.fn(),
      });

      render(<MainChat />);
      
      await server.connected;

      // Find and click stop button
      const stopButton = screen.getByTestId('stop-button');
      await userEvent.click(stopButton);

      // Verify stop message was sent
      expect(server).toHaveReceivedMessages(
        expect.arrayContaining([
          JSON.stringify({ type: 'stop_agent', payload: {} })
        ])
      );

      // Simulate server response to stop
      server.send(JSON.stringify({
        type: 'agent_stopped',
        payload: { message: 'Agent execution stopped by user' }
      }));

      // Verify stop handling
      await waitFor(() => {
        expect(mockSetProcessing).toHaveBeenCalledWith(false);
        expect(mockAddMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            content: 'Processing stopped.'
          })
        );
      });
    });
  });

  describe('Agent State Synchronization', () => {
    it('should maintain synchronized state across components', async () => {
      render(<MainChat />);
      
      await server.connected;

      // Send state updates
      const updates = [
        {
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: 'TriageAgent',
            state: { lifecycle: 'running', tools: ['analyzer'] }
          }
        },
        {
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: 'DataAgent',
            state: { lifecycle: 'completed', tools: ['collector'] }
          }
        },
        {
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: 'OptimizationAgent',
            state: { lifecycle: 'running', tools: ['optimizer', 'cost_analyzer'] }
          }
        }
      ];

      for (const update of updates) {
        server.send(JSON.stringify(update));
        await new Promise(resolve => setTimeout(resolve, 50));
      }

      // Verify state synchronization
      expect(mockSetSubAgentName).toHaveBeenCalledTimes(3);
      expect(mockSetSubAgentStatus).toHaveBeenCalledTimes(3);
      
      expect(mockSetSubAgentName).toHaveBeenNthCalledWith(1, 'TriageAgent');
      expect(mockSetSubAgentName).toHaveBeenNthCalledWith(2, 'DataAgent');
      expect(mockSetSubAgentName).toHaveBeenNthCalledWith(3, 'OptimizationAgent');
      
      expect(mockSetSubAgentStatus).toHaveBeenNthCalledWith(3, {
        status: 'running',
        tools: ['optimizer', 'cost_analyzer']
      });
    });

    it('should handle rapid agent transitions', async () => {
      render(<MainChat />);
      
      await server.connected;

      // Send rapid transitions
      const rapidUpdates = Array.from({ length: 20 }, (_, i) => ({
        type: 'sub_agent_update',
        payload: {
          sub_agent_name: `Agent${i}`,
          state: {
            lifecycle: i % 3 === 0 ? 'running' : i % 3 === 1 ? 'completed' : 'pending',
            tools: [`tool${i}`]
          }
        }
      }));

      for (const update of rapidUpdates) {
        server.send(JSON.stringify(update));
      }

      // Wait for all updates to process
      await waitFor(() => {
        expect(mockSetSubAgentName).toHaveBeenCalledTimes(20);
      });

      // Verify final state
      expect(mockSetSubAgentName).toHaveBeenLastCalledWith('Agent19');
    });
  });

  describe('Message Handling and Display', () => {
    it('should handle messages with display flags correctly', async () => {
      render(<MainChat />);
      
      await server.connected;

      // Send messages with different display flags
      const messages = [
        {
          type: 'agent_response',
          payload: { content: 'Analysis starting...' },
          displayed_to_user: true,
          role: 'assistant',
          content: 'Analysis starting...'
        },
        {
          type: 'internal_status',
          payload: { status: 'processing' },
          displayed_to_user: false
        },
        {
          type: 'user_facing_update',
          payload: { update: 'Found 5 optimization opportunities' },
          displayed_to_user: true,
          role: 'assistant',
          content: 'Found 5 optimization opportunities'
        }
      ];

      for (const message of messages) {
        server.send(JSON.stringify(message));
        await new Promise(resolve => setTimeout(resolve, 50));
      }

      // Only messages with displayed_to_user: true should be added
      expect(mockAddMessage).toHaveBeenCalledTimes(2);
      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          content: 'Analysis starting...'
        })
      );
      expect(mockAddMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          content: 'Found 5 optimization opportunities'
        })
      );
    });

    it('should preserve message metadata and formatting', async () => {
      render(<MainChat />);
      
      await server.connected;

      const messageWithMetadata = {
        type: 'rich_response',
        payload: {
          data: {
            charts: ['performance_chart', 'cost_chart'],
            recommendations: ['rec1', 'rec2'],
            severity: 'medium'
          }
        },
        displayed_to_user: true,
        role: 'assistant',
        content: 'Here is your optimization report',
        subAgentName: 'ReportingAgent'
      };

      server.send(JSON.stringify(messageWithMetadata));

      await waitFor(() => {
        expect(mockAddMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            role: 'assistant',
            content: 'Here is your optimization report',
            subAgentName: 'ReportingAgent',
            metadata: {
              data: {
                charts: ['performance_chart', 'cost_chart'],
                recommendations: ['rec1', 'rec2'],
                severity: 'medium'
              }
            }
          })
        );
      });
    });
  });

  describe('Performance Under Load', () => {
    it('should handle high-frequency agent updates efficiently', async () => {
      render(<MainChat />);
      
      await server.connected;

      const startTime = performance.now();

      // Send 200 rapid updates
      for (let i = 0; i < 200; i++) {
        server.send(JSON.stringify({
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: `LoadTestAgent${i % 10}`,
            state: {
              lifecycle: 'running',
              tools: [`tool${i}`]
            }
          }
        }));
      }

      await waitFor(() => {
        expect(mockSetSubAgentName).toHaveBeenCalledTimes(200);
      });

      const endTime = performance.now();
      const processingTime = endTime - startTime;

      // Should process updates efficiently (under 2 seconds)
      expect(processingTime).toBeLessThan(2000);
      expect(mockSetSubAgentName).toHaveBeenCalledTimes(200);
      expect(mockSetSubAgentStatus).toHaveBeenCalledTimes(200);
    });

    it('should handle concurrent message streams', async () => {
      render(<MainChat />);
      
      await server.connected;

      // Simulate concurrent streams from different agents
      const streams = [
        Array.from({ length: 50 }, (_, i) => ({
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: 'TriageAgent',
            state: { lifecycle: 'running', tools: [`triage_tool_${i}`] }
          }
        })),
        Array.from({ length: 50 }, (_, i) => ({
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: 'DataAgent',
            state: { lifecycle: 'running', tools: [`data_tool_${i}`] }
          }
        })),
        Array.from({ length: 50 }, (_, i) => ({
          type: 'sub_agent_update',
          payload: {
            sub_agent_name: 'OptimizationAgent',
            state: { lifecycle: 'running', tools: [`opt_tool_${i}`] }
          }
        }))
      ];

      // Send all messages concurrently
      const promises = streams.map(stream => 
        Promise.all(stream.map(msg => {
          server.send(JSON.stringify(msg));
          return new Promise(resolve => setTimeout(resolve, Math.random() * 10));
        }))
      );

      await Promise.all(promises);

      await waitFor(() => {
        expect(mockSetSubAgentName).toHaveBeenCalledTimes(150);
      });

      // Verify all updates were processed
      expect(mockSetSubAgentStatus).toHaveBeenCalledTimes(150);
    });
  });

  describe('Error Recovery and Resilience', () => {
    it('should handle WebSocket reconnection during agent execution', async () => {
      render(<MainChat />);
      
      await server.connected;

      // Start agent execution
      server.send(JSON.stringify({
        type: 'agent_started',
        payload: {}
      }));

      server.send(JSON.stringify({
        type: 'sub_agent_update',
        payload: {
          sub_agent_name: 'DataAgent',
          state: { lifecycle: 'running', tools: ['collector'] }
        }
      }));

      // Simulate connection loss
      server.error();
      
      // Create new server connection
      server = new WS(wsUrl);
      await server.connected;

      // Continue agent execution after reconnection
      server.send(JSON.stringify({
        type: 'sub_agent_update',
        payload: {
          sub_agent_name: 'OptimizationAgent',
          state: { lifecycle: 'running', tools: ['optimizer'] }
        }
      }));

      server.send(JSON.stringify({
        type: 'agent_finished',
        payload: {}
      }));

      // Verify resilience
      expect(mockSetSubAgentName).toHaveBeenCalledWith('DataAgent');
      expect(mockSetSubAgentName).toHaveBeenLastCalledWith('OptimizationAgent');
      expect(mockSetProcessing).toHaveBeenLastCalledWith(false);
    });

    it('should gracefully handle malformed agent responses', async () => {
      render(<MainChat />);
      
      await server.connected;

      const malformedMessages = [
        '{"type": "sub_agent_update", "payload":',  // Invalid JSON
        '{"type": "sub_agent_update"}',             // Missing payload
        '{"payload": {"sub_agent_name": "Test"}}',  // Missing type
        '{"type": "unknown_type", "payload": {}}',  // Unknown type
      ];

      // Send malformed messages
      for (const malformed of malformedMessages) {
        try {
          server.send(malformed);
        } catch (error) {
          // Expected for invalid JSON
        }
      }

      // Send valid message to verify system still works
      server.send(JSON.stringify({
        type: 'sub_agent_update',
        payload: {
          sub_agent_name: 'RecoveryAgent',
          state: { lifecycle: 'running', tools: ['recovery'] }
        }
      }));

      await waitFor(() => {
        expect(mockSetSubAgentName).toHaveBeenCalledWith('RecoveryAgent');
      });

      // System should still be responsive
      expect(mockSetSubAgentStatus).toHaveBeenLastCalledWith({
        status: 'running',
        tools: ['recovery']
      });
    });
  });
});