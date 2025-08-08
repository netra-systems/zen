import { renderHook, act } from '@testing-library/react';
import { useAgent } from '../hooks/useAgent';
import { useChatStore } from '@/store';

jest.mock('@/store', () => ({
  useChatStore: jest.fn(),
}));

const mockSendMessage = jest.fn();

jest.mock('../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendMessage: mockSendMessage,
  }),
}));

describe('useAgent', () => {
  it('should send a user message', () => {
    const { result } = renderHook(() => useAgent());

    act(() => {
      result.current.sendUserMessage('test message');
    });

    expect(mockSendMessage).toHaveBeenCalledWith('user_message', { text: 'test message' });
  });

  it('should stop the agent', () => {
    const { result } = renderHook(() => useAgent());

    act(() => {
      result.current.stopAgent();
    });

    expect(mockSendMessage).toHaveBeenCalledWith('stop_agent', { run_id: '' });
  });
});