import { renderHook, act, screen } from '@testing-library/react';
import { useAgent } from '../useAgent';
import { getToken, getUserId } from '../../lib/user';
import WS from 'jest-websocket-mock';

jest.mock('../../lib/user', () => ({
    getToken: jest.fn(),
    getUserId: jest.fn(),
}));

describe('useAgent', () => {
    let server: WS;

    beforeEach(() => {
        (getToken as jest.Mock).mockResolvedValue('test-token');
        (getUserId as jest.Mock).mockReturnValue('test-user');
        server = new WS('ws://localhost:8000/agent/run_123?token=test-token');
    });

    afterEach(() => {
        WS.clean();
    });

  it('should start the agent, show thinking indicator, and process the response', async () => {
        const { result } = renderHook(() => useAgent());

        await act(async () => {
            result.current.startAgent('Test message');
            await server.connected;
        });

        expect(result.current.showThinking).toBe(true);

        await act(async () => {
            server.send(
                JSON.stringify({
                    event: 'on_chat_model_stream',
                    data: { chunk: { content: 'Hello' } },
                    run_id: result.current.messages[0].id,
                }),
            );
        });

        expect(result.current.messages[1].content).toBe('Hello');

        await act(async () => {
            server.send(JSON.stringify({ event: 'run_complete' }));
        });

        expect(result.current.showThinking).toBe(false);
    });

  it('should handle errors when calling the agent', async () => {
        const { result } = renderHook(() => useAgent());

        await act(async () => {
            result.current.startAgent('Test message');
            await server.connected;
        });

        await act(async () => {
            server.error();
        });

        expect(result.current.error).not.toBeNull();
        expect(result.current.showThinking).toBe(false);
    });

    it('should not start the agent if no token is available', async () => {
        (getToken as jest.Mock).mockResolvedValue(null);
        const { result } = renderHook(() => useAgent());

        await act(async () => {
            result.current.startAgent('Test message');
        });

        expect(result.current.error).not.toBeNull();
    });
});
