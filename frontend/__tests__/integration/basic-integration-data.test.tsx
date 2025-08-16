/**
 * Data Flow Integration Tests
 * Tests for WebSocket, chat, threads, and agent integration
 */

import React from 'react';
import { render, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';

import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';
import { ChatComponent, ThreadComponent } from './helpers/test-components';
import { setupTestEnvironment, clearStorages, resetStores, cleanupWebSocket } from './helpers/test-setup';
import { createMockMessage, createMockThread } from './helpers/test-builders';
import { assertTextContent, assertMessageCount, assertThreadCount } from './helpers/test-assertions';
import { waitForConnection, sendMessage, sendStreamChunk, sendAgentStart, sendAgentMessage, sendAgentComplete } from './helpers/websocket-helpers';

describe('Data Flow Integration Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    server = setupTestEnvironment();
    clearStorages();
    resetStores();
  });

  afterEach(() => {
    cleanupWebSocket();
  });

  describe('WebSocket Connection', () => {
    it('should establish WebSocket connection', async () => {
      const TestComponent = () => {
        const [connected, setConnected] = React.useState(false);
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          ws.onopen = () => setConnected(true);
          ws.onclose = () => setConnected(false);
          return () => ws.close();
        }, []);
        
        return (
          <div data-testid="connection-status">
            {connected ? 'Connected' : 'Disconnected'}
          </div>
        );
      };
      
      const { getByTestId } = render(<TestComponent />);
      
      await waitForConnection(server);
      await assertTextContent(getByTestId('connection-status'), 'Connected');
    });

    it('should handle WebSocket messages', async () => {
      const TestComponent = () => {
        const [message, setMessage] = React.useState('');
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setMessage(data.content);
          };
          return () => ws.close();
        }, []);
        
        return <div data-testid="message">{message}</div>;
      };
      
      const { getByTestId } = render(<TestComponent />);
      
      await waitForConnection(server);
      sendMessage(server, JSON.stringify({ content: 'Hello from server' }));
      
      await assertTextContent(getByTestId('message'), 'Hello from server');
    });
  });

  describe('Chat Functionality', () => {
    it('should send and receive messages', async () => {
      const { getByText, getByTestId } = render(<ChatComponent />);
      
      const input = getByTestId('message-input');
      
      fireEvent.change(input, { target: { value: 'Test message' } });
      fireEvent.click(getByText('Send'));
      
      const messageList = getByTestId('message-list');
      await assertTextContent(messageList, 'Test message');
      assertMessageCount(1);
    });

    it('should handle streaming messages', async () => {
      const StreamingComponent = () => {
        const [streamingContent, setStreamingContent] = React.useState('');
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'stream_chunk') {
              setStreamingContent(prev => prev + data.chunk);
            }
          };
          return () => ws.close();
        }, []);
        
        return (
          <div data-testid="streaming-content">{streamingContent}</div>
        );
      };
      
      const { getByTestId } = render(<StreamingComponent />);
      
      await waitForConnection(server);
      
      sendStreamChunk(server, 'Hello ');
      await assertTextContent(getByTestId('streaming-content'), 'Hello ');
      
      sendStreamChunk(server, 'World!');
      await assertTextContent(getByTestId('streaming-content'), 'Hello World!');
    });
  });

  describe('Thread Management', () => {
    it('should create and switch threads', async () => {
      const { getByText, getByTestId } = render(<ThreadComponent />);
      
      await assertTextContent(getByTestId('thread-count'), '0 threads');
      
      fireEvent.click(getByText('Create Thread'));
      
      await assertTextContent(getByTestId('thread-count'), '1 threads');
      
      const thread = useThreadStore.getState().threads[0];
      fireEvent.click(getByTestId(`thread-${thread.id}`));
      
      await assertTextContent(getByTestId('active-thread'), 'New Thread');
    });

    it('should delete threads', async () => {
      const mockThread = createMockThread({ id: 'thread-1', title: 'Test Thread' });
      useThreadStore.getState().addThread(mockThread);
      
      const DeleteThreadComponent = () => {
        const { threads, deleteThread } = useThreadStore();
        
        return (
          <div>
            <div data-testid="thread-count">{threads.length} threads</div>
            {threads.map(thread => (
              <div key={thread.id}>
                <span>{thread.title || 'Untitled'}</span>
                <button onClick={() => deleteThread(thread.id)}>Delete</button>
              </div>
            ))}
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<DeleteThreadComponent />);
      
      await assertTextContent(getByTestId('thread-count'), '1 threads');
      
      fireEvent.click(getByText('Delete'));
      
      await assertTextContent(getByTestId('thread-count'), '0 threads');
    });
  });

  describe('Agent Integration', () => {
    it('should handle agent messages through WebSocket', async () => {
      const AgentComponent = () => {
        const [agentStatus, setAgentStatus] = React.useState('idle');
        const [agentMessage, setAgentMessage] = React.useState('');
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'agent_started') {
              setAgentStatus('processing');
            } else if (data.type === 'agent_message') {
              setAgentMessage(data.content);
            } else if (data.type === 'agent_completed') {
              setAgentStatus('completed');
            }
          };
          
          const startAgent = () => {
            ws.send(JSON.stringify({
              type: 'start_agent',
              task: 'analyze'
            }));
          };
          
          setTimeout(startAgent, 100);
          
          return () => ws.close();
        }, []);
        
        return (
          <div>
            <div data-testid="agent-status">{agentStatus}</div>
            <div data-testid="agent-message">{agentMessage}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<AgentComponent />);
      
      await waitForConnection(server);
      await new Promise(resolve => setTimeout(resolve, 200));
      
      sendAgentStart(server);
      await assertTextContent(getByTestId('agent-status'), 'processing');
      
      sendAgentMessage(server, 'Analysis in progress...');
      await assertTextContent(getByTestId('agent-message'), 'Analysis in progress...');
      
      sendAgentComplete(server);
      await assertTextContent(getByTestId('agent-status'), 'completed');
    });
  });

  describe('State Synchronization', () => {
    it('should sync state between components', async () => {
      const ComponentA = () => {
        const { messages, addMessage } = useChatStore();
        
        const sendMessage = () => {
          const message = createMockMessage({
            id: 'msg-1',
            content: 'From Component A'
          });
          addMessage(message);
        };
        
        return (
          <div>
            <button onClick={sendMessage}>Send from A</button>
            <div data-testid="messages-a">{messages.length} messages</div>
          </div>
        );
      };
      
      const ComponentB = () => {
        const { messages } = useChatStore();
        
        return (
          <div data-testid="messages-b">
            {messages.map(msg => (
              <div key={msg.id}>{msg.content}</div>
            ))}
          </div>
        );
      };
      
      const App = () => (
        <div>
          <ComponentA />
          <ComponentB />
        </div>
      );
      
      const { getByText, getByTestId } = render(<App />);
      
      fireEvent.click(getByText('Send from A'));
      
      await assertTextContent(getByTestId('messages-a'), '1 messages');
      await assertTextContent(getByTestId('messages-b'), 'From Component A');
    });
  });
});