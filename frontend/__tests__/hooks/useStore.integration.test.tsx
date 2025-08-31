import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
y/react';
import userEvent from '@testing-library/user-event';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';

// Custom hook that combines multiple store hooks
const useMultiStoreHook = () => {
  const chatState = useUnifiedChatStore();
  const authState = useAuthStore();
  
  const performComplexOperation = React.useCallback(async () => {
    authState.login({ id: 'complex-user', name: 'Complex User', email: 'complex@example.com' }, 'complex-token');
    
    chatState.updateFastLayer({
      agentName: 'Complex Agent',
      timestamp: Date.now(),
      runId: 'complex-run'
    });
    
    chatState.addMessage({
      id: `complex-msg-${Date.now()}`,
      role: 'user',
      content: 'Complex operation message',
      timestamp: Date.now()
    });
  }, [chatState, authState]);
  
  return {
    chatState,
    authState,
    performComplexOperation,
    isFullyLoaded: !!authState.user && !!chatState.fastLayerData
  };
};

// Hook for selective store subscriptions
const useSelectiveStoreHook = () => {
  const fastLayerData = useUnifiedChatStore(state => state.fastLayerData);
  const messages = useUnifiedChatStore(state => state.messages);
  const connectionStatus = useUnifiedChatStore(state => state.isConnected);
  
  const renderCount = React.useRef(0);
  renderCount.current += 1;
  
  return {
    fastLayerData,
    messages,
    connectionStatus,
    renderCount: renderCount.current
  };
};

// Hook with complex derived state
const useDerivedStoreState = () => {
  const messages = useUnifiedChatStore(state => state.messages);
  const executedAgents = useUnifiedChatStore(state => state.executedAgents);
  const optimisticMessages = useUnifiedChatStore(state => state.optimisticMessages);
  
  const derivedState = React.useMemo(() => {
    const totalMessages = messages.length + optimisticMessages.size;
    const totalAgents = executedAgents.size;
    const lastMessage = messages[messages.length - 1];
    
    return {
      totalMessages,
      totalAgents,
      lastMessage,
      hasActivity: totalMessages > 0 || totalAgents > 0,
      messageToAgentRatio: totalAgents > 0 ? totalMessages / totalAgents : 0
    };
  }, [messages, executedAgents, optimisticMessages]);
  
  return derivedState;
};

// Component to test hook integration
const HookIntegrationComponent: React.FC = () => {
  const {
    chatState,
    authState,
    performComplexOperation,
    isFullyLoaded
  } = useMultiStoreHook();
  
  const {
    fastLayerData,
    renderCount
  } = useSelectiveStoreHook();
  
  const {
    totalMessages,
    totalAgents,
    hasActivity,
    messageToAgentRatio
  } = useDerivedStoreState();
  
  return (
    <div>
      <div data-testid="is-loaded">{isFullyLoaded ? 'loaded' : 'not-loaded'}</div>
      <div data-testid="render-count">{renderCount}</div>
      <div data-testid="total-messages">{totalMessages}</div>
      <div data-testid="total-agents">{totalAgents}</div>
      <div data-testid="has-activity">{hasActivity ? 'active' : 'inactive'}</div>
      <div data-testid="message-ratio">{messageToAgentRatio.toFixed(2)}</div>
      <div data-testid="auth-user">{authState.user?.name || 'no-user'}</div>
      <div data-testid="fast-layer-agent">{fastLayerData?.agentName || 'no-agent'}</div>
      
      <button
        data-testid="complex-operation"
        onClick={performComplexOperation}
      />
    </div>
  );
};

describe('Store Hooks Integration Tests', () => {
    jest.setTimeout(10000);
  beforeEach(() => {
    // Reset all stores before each test
    act(() => {
      useUnifiedChatStore.getState().resetLayers();
      useAuthStore.getState().reset();
    });
  });

  describe('Multi-Store Hook Integration', () => {
      jest.setTimeout(10000);
    it('integrates multiple store hooks correctly', () => {
      const { result } = renderHook(() => useMultiStoreHook());
      
      expect(result.current.chatState).toBeDefined();
      expect(result.current.authState).toBeDefined();
      expect(result.current.isFullyLoaded).toBe(false);
      expect(typeof result.current.performComplexOperation).toBe('function');
    });

    it('handles complex multi-store operations', async () => {
      const { result } = renderHook(() => useMultiStoreHook());
      
      expect(result.current.isFullyLoaded).toBe(false);
      
      await act(async () => {
        await result.current.performComplexOperation();
      });
      
      expect(result.current.isFullyLoaded).toBe(true);
      expect(result.current.authState.user?.name).toBe('Complex User');
      expect(result.current.chatState.fastLayerData?.agentName).toBe('Complex Agent');
      expect(result.current.chatState.messages).toHaveLength(1);
    });

    it('maintains hook stability across re-renders', () => {
      const { result, rerender } = renderHook(() => useMultiStoreHook());
      
      const initialOperation = result.current.performComplexOperation;
      
      // Force re-render
      rerender();
      
      // Hook functions should be stable
      expect(result.current.performComplexOperation).toBe(initialOperation);
    });
  });

  describe('Selective Store Subscriptions', () => {
      jest.setTimeout(10000);
    it('implements selective subscriptions correctly', () => {
      const { result } = renderHook(() => useSelectiveStoreHook());
      
      expect(result.current.fastLayerData).toBeNull();
      expect(result.current.messages).toEqual([]);
      expect(result.current.connectionStatus).toBe(false);
      expect(result.current.renderCount).toBe(1);
    });

    it('prevents unnecessary re-renders with selective subscriptions', () => {
      const { result } = renderHook(() => useSelectiveStoreHook());
      
      const initialRenderCount = result.current.renderCount;
      
      // Update store state that is NOT subscribed to
      act(() => {
        useUnifiedChatStore.getState().updateMediumLayer({
          thought: 'Not subscribed',
          stepNumber: 1
        });
      });
      
      // Should not trigger re-render
      expect(result.current.renderCount).toBe(initialRenderCount);
      
      // Update subscribed state
      act(() => {
        useUnifiedChatStore.getState().updateFastLayer({
          agentName: 'Test Agent',
          timestamp: Date.now()
        });
      });
      
      // Should trigger re-render
      expect(result.current.renderCount).toBe(initialRenderCount + 1);
      expect(result.current.fastLayerData?.agentName).toBe('Test Agent');
    });

    it('handles rapid state updates efficiently', () => {
      const { result } = renderHook(() => useSelectiveStoreHook());
      
      const initialRenderCount = result.current.renderCount;
      
      // Perform rapid updates
      act(() => {
        for (let i = 0; i < 100; i++) {
          useUnifiedChatStore.getState().updateFastLayer({
            agentName: `Agent-${i}`,
            timestamp: Date.now() + i
          });
        }
      });
      
      // Should batch renders efficiently
      const finalRenderCount = result.current.renderCount;
      expect(finalRenderCount - initialRenderCount).toBeLessThan(10);
      
      // Final state should be correct
      expect(result.current.fastLayerData?.agentName).toBe('Agent-99');
    });
  });

  describe('Derived State Hook Integration', () => {
      jest.setTimeout(10000);
    it('computes derived state correctly', () => {
      const { result } = renderHook(() => useDerivedStoreState());
      
      expect(result.current.totalMessages).toBe(0);
      expect(result.current.totalAgents).toBe(0);
      expect(result.current.hasActivity).toBe(false);
      expect(result.current.messageToAgentRatio).toBe(0);
    });

    it('updates derived state when dependencies change', () => {
      const { result } = renderHook(() => useDerivedStoreState());
      
      // Add messages
      act(() => {
        useUnifiedChatStore.getState().addMessage({
          id: 'msg1',
          role: 'user',
          content: 'Test 1',
          timestamp: Date.now()
        });
        
        useUnifiedChatStore.getState().addMessage({
          id: 'msg2',
          role: 'assistant',
          content: 'Test 2',
          timestamp: Date.now()
        });
      });
      
      expect(result.current.totalMessages).toBe(2);
      expect(result.current.hasActivity).toBe(true);
      expect(result.current.lastMessage?.content).toBe('Test 2');
      
      // Add executed agent
      act(() => {
        useUnifiedChatStore.getState().updateExecutedAgent('agent1', {
          agentName: 'Test Agent',
          duration: 1000,
          result: {},
          metrics: {}
        });
      });
      
      expect(result.current.totalAgents).toBe(1);
      expect(result.current.messageToAgentRatio).toBe(2);
    });

    it('memoizes derived state calculations efficiently', () => {
      const { result } = renderHook(() => useDerivedStoreState());
      
      const spy = jest.spyOn(React, 'useMemo');
      
      // Add some data
      act(() => {
        useUnifiedChatStore.getState().addMessage({
          id: 'msg1',
          role: 'user',
          content: 'Test',
          timestamp: Date.now()
        });
      });
      
      const memoCallCount = spy.mock.calls.length;
      
      // Update unrelated state
      act(() => {
        useUnifiedChatStore.getState().setConnectionStatus(true);
      });
      
      // Memo should not recalculate
      expect(spy.mock.calls.length).toBe(memoCallCount);
      
      spy.mockRestore();
    });
  });

  describe('Hook Performance and Memory Management', () => {
      jest.setTimeout(10000);
    it('handles hook cleanup properly', () => {
      const TestComponent = () => {
        const { totalMessages } = useDerivedStoreState();
        return <div>{totalMessages}</div>;
      };

      const { unmount } = render(<TestComponent />);
      
      // Add data after mount
      act(() => {
        useUnifiedChatStore.getState().addMessage({
          id: 'test',
          role: 'user',
          content: 'Test',
          timestamp: Date.now()
        });
      });
      
      // Unmount component
      unmount();
      
      // Update store after unmount - should not cause errors
      expect(() => {
        act(() => {
          useUnifiedChatStore.getState().addMessage({
            id: 'after-unmount',
            role: 'user',
            content: 'After unmount',
            timestamp: Date.now()
          });
        });
      }).not.toThrow();
    });

    it('maintains performance with large datasets', () => {
      const { result } = renderHook(() => useDerivedStoreState());
      
      // Add large dataset
      act(() => {
        for (let i = 0; i < 10000; i++) {
          useUnifiedChatStore.getState().addMessage({
            id: `msg-${i}`,
            role: i % 2 === 0 ? 'user' : 'assistant',
            content: `Message ${i}`,
            timestamp: Date.now() + i
          });
        }
        
        for (let i = 0; i < 101; i++) {
          useUnifiedChatStore.getState().updateExecutedAgent(`agent-${i}`, {
            agentName: `Agent ${i}`,
            duration: 1000 + i,
            result: {},
            metrics: {}
          });
        }
      });
      
      const startTime = performance.now();
      
      // Access derived state
      const { totalMessages, totalAgents, messageToAgentRatio } = result.current;
      
      const endTime = performance.now();
      
      // Computation should be fast
      expect(endTime - startTime).toBeLessThan(50);
      
      // Results should be correct
      expect(totalMessages).toBe(10000);
      expect(totalAgents).toBe(102);
      expect(messageToAgentRatio).toBe(10000/102);
    });

    it('prevents memory leaks with optimistic messages', () => {
      const { result } = renderHook(() => useDerivedStoreState());
      
      // Add many optimistic messages
      act(() => {
        for (let i = 0; i < 1000; i++) {
          useUnifiedChatStore.getState().addOptimisticMessage({
            localId: `opt-${i}`,
            role: 'user',
            content: `Optimistic ${i}`,
            timestamp: Date.now() + i,
            status: 'pending'
          });
        }
      });
      
      expect(result.current.totalMessages).toBe(1000);
      
      // Clear optimistic messages
      act(() => {
        useUnifiedChatStore.getState().clearOptimisticMessages();
      });
      
      expect(result.current.totalMessages).toBe(0);
      
      // Verify state is actually cleared
      const optimisticCount = useUnifiedChatStore.getState().optimisticMessages.size;
      expect(optimisticCount).toBe(0);
    });
  });

  describe('Hook Integration with Components', () => {
      jest.setTimeout(10000);
    it('integrates hooks correctly in component context', async () => {
      const user = userEvent.setup();
      
      render(<HookIntegrationComponent />);

      // Initial state
      expect(screen.getByTestId('is-loaded')).toHaveTextContent('not-loaded');
      expect(screen.getByTestId('total-messages')).toHaveTextContent('0');
      expect(screen.getByTestId('has-activity')).toHaveTextContent('active');
      
      // Perform complex operation
      await user.click(screen.getByTestId('complex-operation'));
      
      // Verify integrated state updates
      expect(screen.getByTestId('is-loaded')).toHaveTextContent('loaded');
      expect(screen.getByTestId('total-messages')).toHaveTextContent('1');
      expect(screen.getByTestId('total-agents')).toHaveTextContent('0');
      expect(screen.getByTestId('has-activity')).toHaveTextContent('active');
      expect(screen.getByTestId('auth-user')).toHaveTextContent('Complex User');
      expect(screen.getByTestId('fast-layer-agent')).toHaveTextContent('Complex Agent');
    });

    it('maintains consistent render counts across hook integrations', async () => {
      const user = userEvent.setup();
      
      render(<HookIntegrationComponent />);

      const initialRenderCount = parseInt(screen.getByTestId('render-count').textContent || '0');
      
      // Perform operation that affects subscribed state
      await user.click(screen.getByTestId('complex-operation'));
      
      const finalRenderCount = parseInt(screen.getByTestId('render-count').textContent || '0');
      
      // Should have re-rendered due to fastLayerData change
      expect(finalRenderCount).toBeGreaterThan(initialRenderCount);
      expect(finalRenderCount - initialRenderCount).toBeLessThan(5); // Reasonable render count
    });

    it('handles concurrent hook operations correctly', async () => {
      const user = userEvent.setup();
      
      render(<HookIntegrationComponent />);

      // Perform multiple concurrent operations
      const promises = [];
      for (let i = 0; i < 10; i++) {
        promises.push(user.click(screen.getByTestId('complex-operation')));
      }
      
      await Promise.all(promises);
      
      // Verify final state is consistent
      expect(screen.getByTestId('is-loaded')).toHaveTextContent('loaded');
      expect(screen.getByTestId('auth-user')).toHaveTextContent('Complex User');
      expect(screen.getByTestId('fast-layer-agent')).toHaveTextContent('Complex Agent');
      
      // Messages should reflect all operations
      const messageCount = parseInt(screen.getByTestId('total-messages').textContent || '0');
      expect(messageCount).toBeGreaterThan(0);
    });
  });
});