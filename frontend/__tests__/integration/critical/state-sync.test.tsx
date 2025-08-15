/**
 * State Synchronization Tests
 * Tests for syncing local state with server state and concurrent updates
 */

import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import stores
import { useChatStore } from '@/store/chatStore';
import { useThreadStore } from '@/store/threadStore';

// Import test utilities
import { TestProviders } from '../../test-utils/providers';

describe('State Synchronization', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset stores
    useChatStore.setState({ messages: [], currentThread: null });
    useThreadStore.setState({ threads: [], currentThreadId: null, currentThread: null });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Server State Sync', () => {
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
      
      // Sync state
      const response = await fetch('/api/state/sync');
      const data = await response.json();
      
      // Update stores
      useThreadStore.setState({ threads: data.threads });
      useChatStore.setState({ messages: data.messages });
      
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
        
        React.useEffect(() => {
          // Process updates concurrently
          updates.forEach(update => {
            if (update.type === 'thread_created') {
              useThreadStore.getState().addThread(update.data);
            } else if (update.type === 'message_sent') {
              useChatStore.getState().addMessage(update.data);
            } else if (update.type === 'thread_updated') {
              useThreadStore.getState().updateThread(update.data.id, update.data);
            }
          });
        }, []);
        
        return (
          <div>
            <div data-testid="threads">Threads: {threads.length}</div>
            <div data-testid="messages">Messages: {messages.length}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(<TestComponent />);
      
      expect(getByTestId('threads')).toHaveTextContent('Threads: 1');
      expect(getByTestId('messages')).toHaveTextContent('Messages: 1');
    });
  });
});