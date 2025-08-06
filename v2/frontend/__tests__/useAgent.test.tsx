
import { renderHook, act } from '@testing-library/react-hooks';
import { useAgent } from '../app/hooks/useAgent';
import fetchMock from 'jest-fetch-mock';

fetchMock.enableMocks();

describe('useAgent', () => {
  beforeEach(() => {
    fetchMock.resetMocks();
  });

  it('should send a message and receive a response', async () => {
    const { result, waitForNextUpdate } = renderHook(() => useAgent());
    const message = 'Test message';

    fetchMock.mockResponseOnce(JSON.stringify({ message: 'Test response' }));

    await act(async () => {
      result.current.startAgent(message);
      await waitForNextUpdate();
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0].content).toBe(message);
    expect(result.current.messages[0].sender).toBe('user');
    expect(result.current.messages[1].content).toBe('Test response');
    expect(result.current.messages[1].sender).toBe('agent');
  });

  it('should add user message to messages list immediately', async () => {
    const { result } = renderHook(() => useAgent());
    const message = 'Test message';

    act(() => {
      result.current.startAgent(message);
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe(message);
    expect(result.current.messages[0].sender).toBe('user');
  });

  it('should handle errors gracefully', async () => {
    const { result, waitForNextUpdate } = renderHook(() => useAgent());
    const message = 'Test message';

    fetchMock.mockRejectOnce(new Error('API Error'));

    await act(async () => {
      result.current.startAgent(message);
      await waitForNextUpdate();
    });

    expect(result.current.messages).toHaveLength(1);
  });
});
