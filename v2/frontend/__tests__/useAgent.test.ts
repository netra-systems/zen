import { renderHook, act } from '@testing-library/react';
import { useAgent } from '@/hooks/useAgent';
import { Message } from '@/app/types/chat';
import WS from 'jest-websocket-mock';

const server = new WS('ws://localhost:8000/ws/test-user');

describe('useAgent', () => {
    afterEach(() => {
        WS.clean();
    });

    it('should process a complete sequence of messages', async () => {
        const { result } = renderHook(() => useAgent('test-user'));

        await server.connected;

        const messages = [
            { event: 'agent_started', data: { status: 'agent_started', run_id: 'run_1754540329677' } },
            { event: 'on_chain_start', data: { input: { messages: [{ type: 'human', content: "I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?" }] } } },
            { event: 'on_chat_model_start', data: { input: { messages: [['content="You are an expert..."', { type: 'human', content: "I'm expecting a 50% increase..." }]] } } },
            { event: 'on_chat_model_stream', data: { chunk: { content: 'Here is' } } },
            { event: 'on_chat_model_stream', data: { chunk: { content: ' a list of the steps I will take to address your request...' } } },
            { event: 'on_chat_model_stream', data: { chunk: { tool_call_chunks: [{ name: 'cost_analyzer', args: '{}', id: 'd6de110a-fb41-4fa2-8868-bb14419ff2c4' }] } } },
            { event: 'run_complete', data: { status: 'complete' } },
        ];

        for (const message of messages) {
            act(() => {
                server.send(JSON.stringify(message));
            });
        }

        // Check final state of messages
        const finalMessages = result.current.messages;
        expect(finalMessages).toHaveLength(7);

        // Agent Started
        expect(finalMessages[0].type).toBe('event');
        expect(finalMessages[0].content).toContain('Agent started');
        expect(finalMessages[0].rawServerEvent).toEqual(messages[0]);

        // On Chain Start
        expect(finalMessages[1].type).toBe('event');
        expect(finalMessages[1].content).toContain('Chain started');
        expect(finalMessages[1].rawServerEvent).toEqual(messages[1]);

        // On Chat Model Start
        expect(finalMessages[2].type).toBe('event');
        expect(finalMessages[2].content).toContain('Chat model started');
        expect(finalMessages[2].rawServerEvent).toEqual(messages[2]);

        // On Chat Model Stream (content)
        expect(finalMessages[3].type).toBe('text');
        expect(finalMessages[3].content).toBe('Here is a list of the steps I will take to address your request...');
        expect(finalMessages[3].rawServerEvent).toEqual(messages[4]);

        // On Chat Model Stream (tool call)
        expect(finalMessages[4].type).toBe('tool_start');
        expect(finalMessages[4].tool).toBe('cost_analyzer');
        expect(finalMessages[4].rawServerEvent).toEqual(messages[5]);

        // Run Complete
        expect(finalMessages[5].type).toBe('event');
        expect(finalMessages[5].content).toContain('Run complete');
        expect(finalMessages[5].rawServerEvent).toEqual(messages[6]);
    }, 30000);
});