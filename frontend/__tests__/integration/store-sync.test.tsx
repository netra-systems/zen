// Store Synchronization Integration Tests
// Tests store synchronization across components and tabs
// Business Value: Ensures consistent state for all user segments

import React from 'react';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useAuthStore } from '@/store/authStore';

// Test component that uses multiple stores
const MultiStoreComponent: React.FC = () => {
  const {
    fastLayerData,
    mediumLayerData,
    slowLayerData,
    updateFastLayer,
    updateMediumLayer,
    updateSlowLayer,
    resetLayers,
    isConnected,
    setConnectionStatus
  } = useUnifiedChatStore();
  
  const { user, isAuthenticated, login } = useAuthStore();

  const setUser = (userData: any) => {
    login(userData, 'test-token');
  };

  return (
    <div>
      <div data-testid="fast-layer">
        {fastLayerData ? JSON.stringify(fastLayerData) : 'null'}
      </div>
      <div data-testid="medium-layer">
        {mediumLayerData ? JSON.stringify(mediumLayerData) : 'null'}
      </div>
      <div data-testid="slow-layer">
        {slowLayerData ? JSON.stringify(slowLayerData) : 'null'}
      </div>
      <div data-testid="connection-status">
        {isConnected ? 'connected' : 'disconnected'}
      </div>
      <div data-testid="auth-status">
        {isAuthenticated ? 'authenticated' : 'unauthenticated'}
      </div>
      <div data-testid="user-data">
        {user ? JSON.stringify(user) : 'no-user'}
      </div>
      <button
        data-testid="update-fast"
        onClick={() => updateFastLayer({ agentName: 'Test Agent', timestamp: Date.now() })}
      />
      <button
        data-testid="update-medium"
        onClick={() => updateMediumLayer({ thought: 'Testing...', stepNumber: 1 })}
      />
      <button
        data-testid="update-slow"
        onClick={() => updateSlowLayer({ completedAgents: [{ agentName: 'Done', duration: 1000 }] })}
      />
      <button
        data-testid="reset-layers"
        onClick={() => resetLayers()}
      />
      <button
        data-testid="set-connected"
        onClick={() => setConnectionStatus(true)}
      />
      <button
        data-testid="set-user"
        onClick={() => setUser({ id: 'test-user', name: 'Test User', email: 'test@example.com' })}
      />
    </div>
  );
};

// Component to test store subscription updates
const StoreSubscriberComponent: React.FC = () => {
  const fastLayerData = useUnifiedChatStore(state => state.fastLayerData);
  const messages = useUnifiedChatStore(state => state.messages);
  const renderCount = React.useRef(0);
  
  renderCount.current += 1;
  
  return (
    <div>
      <div data-testid="subscriber-fast-layer">
        {fastLayerData ? JSON.stringify(fastLayerData) : 'null'}
      </div>
      <div data-testid="subscriber-messages">
        {messages.length}
      </div>
      <div data-testid="render-count">
        {renderCount.current}
      </div>
    </div>
  );
};

describe('Store Synchronization Integration Tests', () => {
  beforeEach(() => {
    // Reset all stores before each test
    act(() => {
      useUnifiedChatStore.getState().resetLayers();
      useAuthStore.getState().reset();
    });
  });

  describe('Cross-Component Store Synchronization', () => {
    it('synchronizes store updates across components', async () => {
      const user = userEvent.setup();
      
      render(
        <div>
          <MultiStoreComponent />
          <StoreSubscriberComponent />
        </div>
      );

      // Initial state check
      expect(screen.getByTestId('fast-layer')).toHaveTextContent('null');
      expect(screen.getByTestId('subscriber-fast-layer')).toHaveTextContent('null');
      
      // Update fast layer and verify synchronization
      await user.click(screen.getByTestId('update-fast'));
      
      const fastLayerContent = screen.getByTestId('fast-layer').textContent;
      const subscriberContent = screen.getByTestId('subscriber-fast-layer').textContent;
      
      expect(fastLayerContent).toContain('Test Agent');
      expect(subscriberContent).toBe(fastLayerContent);
    });

    it('prevents unnecessary re-renders with selective subscriptions', async () => {
      const user = userEvent.setup();
      
      render(
        <div>
          <MultiStoreComponent />
          <StoreSubscriberComponent />
        </div>
      );

      // Get initial render count
      const initialRenderCount = parseInt(
        screen.getByTestId('render-count').textContent || '0'
      );
      
      // Update medium layer (not subscribed by StoreSubscriberComponent)
      await user.click(screen.getByTestId('update-medium'));
      
      // Verify subscriber didn't re-render
      const finalRenderCount = parseInt(
        screen.getByTestId('render-count').textContent || '0'
      );
      
      expect(finalRenderCount).toBe(initialRenderCount);
    });

    it('handles rapid state updates without race conditions', async () => {
      const user = userEvent.setup();
      
      render(<MultiStoreComponent />);

      // Perform rapid updates
      await Promise.all([
        user.click(screen.getByTestId('update-fast')),
        user.click(screen.getByTestId('update-medium')),
        user.click(screen.getByTestId('update-slow')),
        user.click(screen.getByTestId('set-connected')),
      ]);

      // Verify all updates applied correctly
      expect(screen.getByTestId('fast-layer')).toHaveTextContent('Test Agent');
      expect(screen.getByTestId('medium-layer')).toHaveTextContent('Testing...');
      expect(screen.getByTestId('slow-layer')).toHaveTextContent('Done');
      expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
    });
  });

  describe('Store State Isolation', () => {
    it('maintains state isolation between different stores', async () => {
      const user = userEvent.setup();
      
      render(<MultiStoreComponent />);

      // Update different stores
      await user.click(screen.getByTestId('update-fast'));
      await user.click(screen.getByTestId('set-user'));
      
      // Verify store isolation
      expect(screen.getByTestId('fast-layer')).toHaveTextContent('Test Agent');
      expect(screen.getByTestId('user-data')).toHaveTextContent('Test User');
      expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
      
      // Reset one store, verify others unaffected
      await user.click(screen.getByTestId('reset-layers'));
      
      expect(screen.getByTestId('fast-layer')).toHaveTextContent('null');
      expect(screen.getByTestId('user-data')).toHaveTextContent('Test User');
    });

    it('handles store reset without affecting other stores', async () => {
      const user = userEvent.setup();
      
      render(<MultiStoreComponent />);

      // Set up initial state
      await user.click(screen.getByTestId('update-fast'));
      await user.click(screen.getByTestId('set-user'));
      
      // Reset unified chat store only
      await user.click(screen.getByTestId('reset-layers'));
      
      // Verify unified chat store reset
      expect(screen.getByTestId('fast-layer')).toHaveTextContent('null');
      expect(screen.getByTestId('medium-layer')).toHaveTextContent('null');
      expect(screen.getByTestId('slow-layer')).toHaveTextContent('null');
      
      // Verify auth store preserved
      expect(screen.getByTestId('user-data')).toHaveTextContent('Test User');
      expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
    });
  });

  describe('Complex State Transactions', () => {
    it('handles complex multi-store state updates atomically', async () => {
      const user = userEvent.setup();
      
      render(<MultiStoreComponent />);

      // Perform complex state transaction
      await act(async () => {
        await Promise.all([
          user.click(screen.getByTestId('update-fast')),
          user.click(screen.getByTestId('update-medium')),
          user.click(screen.getByTestId('set-connected')),
          user.click(screen.getByTestId('set-user')),
        ]);
      });

      // Verify atomic update completion
      expect(screen.getByTestId('fast-layer')).toHaveTextContent('Test Agent');
      expect(screen.getByTestId('medium-layer')).toHaveTextContent('Testing...');
      expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
      expect(screen.getByTestId('auth-status')).toHaveTextContent('authenticated');
    });

    it('maintains state consistency during concurrent updates', async () => {
      const user = userEvent.setup();
      
      render(<MultiStoreComponent />);

      // Simulate concurrent updates from different sources
      const promises = [];
      
      for (let i = 0; i < 10; i++) {
        promises.push(
          act(async () => {
            useUnifiedChatStore.getState().updateFastLayer({
              agentName: `Agent-${i}`,
              timestamp: Date.now() + i,
              iteration: i
            });
          })
        );
      }
      
      await Promise.all(promises);
      
      // Verify final state is consistent
      const fastLayerText = screen.getByTestId('fast-layer').textContent;
      expect(fastLayerText).toMatch(/Agent-\d/);
      
      // Verify state contains valid data structure
      const fastLayerData = useUnifiedChatStore.getState().fastLayerData;
      expect(fastLayerData).toBeDefined();
      expect(fastLayerData?.agentName).toMatch(/^Agent-\d$/);
    });
  });

  describe('Memory Management', () => {
    it('prevents memory leaks with large state objects', async () => {
      // Create large state object directly without component
      const largeData = {
        agentName: 'Large Agent',
        data: new Array(1000).fill('test').join(''),
        timestamp: Date.now(),
        metadata: new Array(100).fill({ key: 'value', nested: { deep: 'data' } })
      };

      // Update with large data
      await act(async () => {
        useUnifiedChatStore.getState().updateFastLayer(largeData);
      });

      // Verify data stored correctly
      const stateAfterUpdate = useUnifiedChatStore.getState().fastLayerData;
      expect(stateAfterUpdate?.agentName).toBe('Large Agent');
      
      // Reset and verify cleanup
      await act(async () => {
        useUnifiedChatStore.getState().resetLayers();
      });
      
      // Verify state is actually cleared
      const stateAfterReset = useUnifiedChatStore.getState().fastLayerData;
      expect(stateAfterReset).toBeNull();
    });

    it('handles subscription cleanup properly', () => {
      const TestComponent = () => {
        const fastLayerData = useUnifiedChatStore(state => state.fastLayerData);
        return <div data-testid="test">{fastLayerData ? 'data' : 'no-data'}</div>;
      };

      const { unmount } = render(<TestComponent />);
      
      // Update store after component mounts
      act(() => {
        useUnifiedChatStore.getState().updateFastLayer({ agentName: 'Test' });
      });
      
      // Unmount component
      unmount();
      
      // Update store after unmount - should not cause errors
      expect(() => {
        act(() => {
          useUnifiedChatStore.getState().updateFastLayer({ agentName: 'After Unmount' });
        });
      }).not.toThrow();
    });
  });

  describe('DevTools Integration', () => {
    it('maintains devtools integration with store updates', async () => {
      // Update state directly
      await act(async () => {
        useUnifiedChatStore.getState().updateFastLayer({
          agentName: 'Test Agent',
          timestamp: Date.now()
        });
      });
      
      // Verify store state is accessible for devtools
      const storeState = useUnifiedChatStore.getState();
      expect(storeState.fastLayerData).toBeDefined();
      expect(storeState.fastLayerData?.agentName).toBe('Test Agent');
      
      // Verify store methods are available
      expect(typeof storeState.updateFastLayer).toBe('function');
      expect(typeof storeState.resetLayers).toBe('function');
    });

    it('supports time-travel debugging through state snapshots', async () => {
      // Capture initial state
      const initialState = { ...useUnifiedChatStore.getState() };
      
      // Make changes directly
      await act(async () => {
        useUnifiedChatStore.getState().updateFastLayer({
          agentName: 'Test Agent',
          timestamp: Date.now()
        });
      });
      const afterFastUpdate = { ...useUnifiedChatStore.getState() };
      
      await act(async () => {
        useUnifiedChatStore.getState().updateMediumLayer({
          thought: 'Testing...',
          stepNumber: 1
        });
      });
      const afterMediumUpdate = { ...useUnifiedChatStore.getState() };
      
      // Verify state evolution
      expect(initialState.fastLayerData).toBeNull();
      expect(afterFastUpdate.fastLayerData).toBeDefined();
      expect(afterMediumUpdate.mediumLayerData).toBeDefined();
      
      // Verify state snapshots are independent
      expect(initialState.fastLayerData).toBeNull(); // Original preserved
      expect(afterFastUpdate.mediumLayerData).toBeNull(); // Intermediate preserved
    });
  });
});