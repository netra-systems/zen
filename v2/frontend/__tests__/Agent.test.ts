import { agent } from '../app/services/agent/Agent';
import { WebSocketClient } from '../app/services/agent/WebSocketClient';
import { getToken, getUserId } from '../app/lib/user';

jest.mock('../app/services/agent/WebSocketClient');
jest.mock('../app/lib/user');

describe('Agent', () => {
    let webSocketClient: jest.Mocked<WebSocketClient>;

    beforeEach(() => {
        webSocketClient = new (WebSocketClient as any)();
        (getToken as jest.Mock).mockResolvedValue('test-token');
        (getUserId as jest.Mock).mockReturnValue('test-user');
        agent['webSocketClient'] = webSocketClient;
        agent['isInitialized'] = true;
        agent['state'] = { messages: [], isThinking: false, error: null };
    });

    it('should process text stream correctly', () => {
        const message = {
            event: 'on_chat_model_stream',
            data: { chunk: { content: 'Hello' } },
            run_id: 'test-run-id',
        };

        agent['handleMessage']({ data: JSON.stringify(message) } as MessageEvent);

        expect(agent['state'].messages).toHaveLength(1);
        expect(agent['state'].messages[0].content).toBe('Hello');
        expect(agent['state'].messages[0].type).toBe('text');
    });

    it('should process tool calls correctly', () => {
        const message = {
            event: 'on_chat_model_stream',
            data: {
                chunk: {
                    tool_call_chunks: [
                        {
                            id: 'tool-call-id',
                            name: 'test-tool',
                            args: '{"test": "arg"}',
                        },
                    ],
                },
            },
            run_id: 'test-run-id',
        };

        agent['handleMessage']({ data: JSON.stringify(message) } as MessageEvent);

        expect(agent['state'].messages).toHaveLength(2);
        expect(agent['state'].messages[1].type).toBe('tool_start');
        expect(agent['state'].messages[1].tool).toBe('test-tool');
        expect(agent['state'].messages[1].toolInput).toBe('{"test": "arg"}');
    });

    it('should handle run_complete event', () => {
        agent['state'].isThinking = true;

        const message = {
            event: 'run_complete',
            data: {},
            run_id: 'test-run-id',
        };

        agent['handleMessage']({ data: JSON.stringify(message) } as MessageEvent);

        expect(agent['state'].isThinking).toBe(false);
    });
});