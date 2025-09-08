/**
 * Test store actions to verify they work correctly
 */

import { useUnifiedChatStore, resetMockState } from '@/store/unified-chat';

jest.mock('@/store/unified-chat', () => require('../../__mocks__/store/unified-chat'));

describe('Store Actions', () => {
  beforeEach(() => {
    resetMockState();
  });

  it('should call completeThreadLoading and update state', () => {
    const store = useUnifiedChatStore.getState();
    
    // Call the action
    store.completeThreadLoading('test-thread', [{ id: '1', content: 'Test message' }]);
    
    // Check the updated state
    const updatedState = useUnifiedChatStore.getState();
    console.log('Updated state:', updatedState);
    
    expect(updatedState.activeThreadId).toBe('test-thread');
    expect(updatedState.isThreadLoading).toBe(false);
    expect(updatedState.messages).toHaveLength(1);
    expect(updatedState.messages[0].content).toBe('Test message');
  });

  it('should call startThreadLoading and update state', () => {
    const store = useUnifiedChatStore.getState();
    
    // Call the action
    store.startThreadLoading('test-thread');
    
    // Check the updated state
    const updatedState = useUnifiedChatStore.getState();
    console.log('Updated state after startThreadLoading:', updatedState);
    
    expect(updatedState.activeThreadId).toBe('test-thread');
    expect(updatedState.isThreadLoading).toBe(true);
    expect(updatedState.messages).toHaveLength(0);
  });
});