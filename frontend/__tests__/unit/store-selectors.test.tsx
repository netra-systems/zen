/**
 * Test store selectors to verify they work correctly with the hook
 */

import { useUnifiedChatStore, resetMockState } from '@/store/unified-chat';

jest.mock('@/store/unified-chat', () => require('../../__mocks__/store/unified-chat'));

describe('Store Selectors', () => {
  beforeEach(() => {
    resetMockState();
  });

  it('should select functions from the store', () => {
    const setActiveThread = useUnifiedChatStore(state => state.setActiveThread);
    const completeThreadLoading = useUnifiedChatStore(state => state.completeThreadLoading);
    
    console.log('setActiveThread type:', typeof setActiveThread);
    console.log('completeThreadLoading type:', typeof completeThreadLoading);
    
    expect(typeof setActiveThread).toBe('function');
    expect(typeof completeThreadLoading).toBe('function');
  });

  it('should call selected functions and update state', () => {
    const setActiveThread = useUnifiedChatStore(state => state.setActiveThread);
    const completeThreadLoading = useUnifiedChatStore(state => state.completeThreadLoading);
    
    // Call the selected functions
    setActiveThread('test-thread-123');
    completeThreadLoading('test-thread-456', [{ id: 'msg-1', content: 'Hello' }]);
    
    // Check updated state
    const state = useUnifiedChatStore.getState();
    console.log('State after selector calls:', state);
    
    // The completeThreadLoading call should override the setActiveThread call
    expect(state.activeThreadId).toBe('test-thread-456');
    expect(state.messages).toHaveLength(1);
    expect(state.messages[0].content).toBe('Hello');
  });
});