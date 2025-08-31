import React from 'react';
import { render, waitFor, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
rt { render, waitFor, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import stores
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';

// Import test utilities
import { TestProviders } from '@/__tests__/setup/test-providers';

describe('State Synchronization', () => {
    jest.setTimeout(10000);
  beforeEach(async () => {
    jest.clearAllMocks();
    
    // Reset stores with proper async handling
    await act(async () => {
      useChatStore.setState({ messages: [], currentThread: null });
      useThreadStore.setState({ threads: [], currentThreadId: null, currentThread: null });
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Server State Sync', () => {
      jest.setTimeout(10000);
    it('should sync local state with server state', async () => {
      const serverState = {
        threads: [
          { id: 'thread-1', name: 'Thread 1', created_at: '2024-01-01' },
          { id: 'thread-2', name: 'Thread 2', created_at: '2024-01-02' }
        ],
        messages: [
          { id: 'msg-1', thread_id: 'thread-1', content: 'Message 1', role: 'user' }
        ]
      };
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => serverState
      });
      
      // Sync state with proper async handling
      const response = await fetch('/api/state/sync');
      const data = await response.json();
      
      // Update stores with act wrapping
      await act(async () => {
        useThreadStore.setState({ threads: data.threads });
        useChatStore.setState({ messages: data.messages });
      });
      
      expect(useThreadStore.getState().threads).toEqual(serverState.threads);
      expect(useChatStore.getState().messages).toEqual(serverState.messages);
    });

    it('should handle concurrent state updates', async () => {
      const updates = [
        { type: 'thread_created', data: { id: 'thread-1', name: 'Thread 1' } },
        { type: 'message_sent', data: { id: 'msg-1', content: 'Message 1', role: 'user' } },
        { type: 'thread_updated', data: { id: 'thread-1', name: 'Updated Thread' } }
      ];
      
      const TestComponent = () => {
        const threads = useThreadStore((state) => state.threads);
        const messages = useChatStore((state) => state.messages);
        const [isProcessing, setIsProcessing] = React.useState(false);
        
        React.useEffect(() => {
          const processUpdates = async () => {
            setIsProcessing(true);
            
            // Process updates with proper async handling
            for (const update of updates) {
              await new Promise(resolve => {
                queueMicrotask(() => {
                  if (update.type === 'thread_created') {
                    useThreadStore.getState().addThread(update.data);
                  } else if (update.type === 'message_sent') {
                    useChatStore.getState().addMessage(update.data);
                  } else if (update.type === 'thread_updated') {
                    useThreadStore.getState().updateThread(update.data.id, update.data);
                  }
                  resolve(undefined);
                });
              });
            }
            
            setIsProcessing(false);
          };
          
          processUpdates();
        }, []);
        
        return (
          <div>
            <div data-testid="threads">Threads: {threads.length}</div>
            <div data-testid="messages">Messages: {messages.length}</div>
            <div data-testid="processing">{isProcessing ? 'processing' : 'idle'}</div>
          </div>
        );
      };
      
      let getByTestId: any;
      await act(async () => {
        const result = render(<TestComponent />);
        getByTestId = result.getByTestId;
      });
      
      await waitFor(() => {
        expect(getByTestId('processing')).toHaveTextContent('idle');
      });
      
      expect(getByTestId('threads')).toHaveTextContent('Threads: 1');
      expect(getByTestId('messages')).toHaveTextContent('Messages: 1');
    });
  });
});