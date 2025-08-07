import { renderHook, act, waitFor } from '@testing-library/react';
import { useAgent } from '../useAgent';
import { getToken, getUserId } from '../../lib/user';
import WS from 'jest-websocket-mock';

jest.setTimeout(10000);

jest.mock('../../lib/user', () => ({
    getToken: jest.fn(),
    getUserId: jest.fn(),
}));

describe('useAgent', () => {
    let server: WS;

    beforeEach(() => {
        jest.spyOn(Date, 'now').mockImplementation(() => 123);
        (getToken as jest.Mock).mockResolvedValue('test-token');
        (getUserId as jest.Mock).mockReturnValue('test-user');
        server = new WS('ws://localhost:8000/agent/run_123?token=test-token', { jsonProtocol: true });
    });

    afterEach(() => {
        WS.clean();
        jest.restoreAllMocks();
    });

    it('should connect on mount and disconnect on unmount', async () => {
        const { unmount } = renderHook(() => useAgent());
        await server.connected;
        expect(server.server.clients()).toHaveLength(1);
        unmount();
        await server.closed;
        expect(server.server.clients()).toHaveLength(0);
    });


    it('should start the agent, show thinking indicator, and process the response', async () => {
        const { result } = renderHook(() => useAgent());

        await server.connected;

        await act(async () => {
            result.current.startAgent('Test message');
        });

        await waitFor(() => expect(result.current.showThinking).toBe(true));
        await waitFor(() => expect(result.current.messages).toHaveLength(2));
        expect(result.current.messages[0].content).toBe('Test message');
        expect(result.current.messages[1].type).toBe('thinking');

        await act(async () => {
            server.send({
                event: 'on_chain_start',
                data: { input: { todo_list: ['step 1'] } },
                run_id: 'run_123',
            });
        });

        await waitFor(() => {
            expect(result.current.messages[1].type).toBe('artifact');
            const artifactMessage = result.current.messages[1] as any;
            expect(artifactMessage.state_updates.todo_list).toEqual(['step 1']);
        });

        await act(async () => {
            server.send({
                event: 'on_chat_model_stream',
                data: { chunk: { content: 'Hello' } },
                run_id: 'run_123',
            });
        });

        await waitFor(() => {
            const artifactMessage = result.current.messages[1] as any;
            expect(artifactMessage.content).toBe('Hello');
        });

        await act(async () => {
            server.send({ event: 'run_complete' });
        });

        await waitFor(() => expect(result.current.showThinking).toBe(false));
    });

    it('should handle errors when calling the agent', async () => {
        const { result } = renderHook(() => useAgent());

        await server.connected;

        await act(async () => {
            result.current.startAgent('Test message');
        });

        await act(async () => {
            server.error();
        });

        await waitFor(() => expect(result.current.error).not.toBeNull());
        await waitFor(() => expect(result.current.showThinking).toBe(false));
    });

    it('should not start the agent if no token is available', async () => {
        (getToken as jest.Mock).mockResolvedValue(null);
        const { result } = renderHook(() => useAgent());

        await act(async () => {
            result.current.startAgent('Test message');
        });

        await waitFor(() => expect(result.current.error).not.toBeNull());
    });
});