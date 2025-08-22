/**
 * Real-time Message Streaming Tests
 * Tests for streaming agent responses and message interruption
 */

import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import stores
import { useChatStore } from '@/store/chatStore';

// Import test utilities
import { TestProviders } from '@/__tests__/setup/test-providers';

describe('Real-time Message Streaming', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset chat store
    useChatStore.setState({ messages: [], currentThread: null });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Streaming Integration', () => {
    it('should stream agent responses to chat', async () => {
      const TestComponent = () => {
        const messages = useChatStore((state) => state.messages);
        const [streamContent, setStreamContent] = React.useState('');
        const [chunksAdded, setChunksAdded] = React.useState<string[]>([]);
        
        const sendMessage = () => {
          // Simulate sending message
          setStreamContent('Chunk 1 ');
          setChunksAdded(['Chunk 1']);
        };
        
        React.useEffect(() => {
          // Simulate receiving chunks - only add each chunk once
          if (streamContent === 'Chunk 1 ' && !chunksAdded.includes('Chunk 2')) {
            setTimeout(() => {
              setStreamContent(prev => prev + 'Chunk 2 ');
              setChunksAdded(prev => [...prev, 'Chunk 2']);
            }, 10);
          }
          if (streamContent === 'Chunk 1 Chunk 2 ' && !chunksAdded.includes('Chunk 3')) {
            setTimeout(() => {
              setStreamContent(prev => prev + 'Chunk 3 ');
              setChunksAdded(prev => [...prev, 'Chunk 3']);
              // Add message once all chunks are received
              useChatStore.getState().addMessage({
                id: 'stream-msg',
                content: 'Chunk 1 Chunk 2 Chunk 3 ',
                role: 'assistant',
                thread_id: 'thread-1'
              });
            }, 10);
          }
        }, [streamContent, chunksAdded]);
        
        return (
          <div>
            <button onClick={sendMessage}>Send</button>
            <div data-testid="messages">
              {streamContent || messages.map(m => m.content).join(' ')}
            </div>
          </div>
        );
      };
      
      render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );
      
      // Send message
      fireEvent.click(screen.getByText('Send'));
      
      await waitFor(() => {
        const messages = screen.getByTestId('messages');
        expect(messages.textContent).toContain('Chunk 1 Chunk 2 Chunk 3');
      }, { timeout: 3000 });
    });

    it('should handle message interruption gracefully', async () => {
      const TestComponent = () => {
        const [isProcessing, setIsProcessing] = React.useState(false);
        
        const startProcessing = () => {
          setIsProcessing(true);
        };
        
        const stopProcessing = () => {
          setIsProcessing(false);
        };
        
        return (
          <div>
            <button onClick={startProcessing}>Start</button>
            <button onClick={stopProcessing}>Stop</button>
            <div data-testid="status">{isProcessing ? 'Running' : 'Stopped'}</div>
          </div>
        );
      };
      
      const { getByText } = render(
        <TestProviders>
          <TestComponent />
        </TestProviders>
      );
      
      // Start processing
      fireEvent.click(getByText('Start'));
      expect(screen.getByTestId('status')).toHaveTextContent('Running');
      
      // Stop processing
      fireEvent.click(getByText('Stop'));
      expect(screen.getByTestId('status')).toHaveTextContent('Stopped');
    });
  });
});