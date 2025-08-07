import { renderHook, waitFor, act } from '@testing-library/react';
import { useAgent } from '../app/hooks/useAgent';
import WS from 'jest-websocket-mock';
import { Message } from '@/app/types/chat';

describe('useAgent - Extended Message Parsing', () => {
  let server: WS;
  const userId = 'test-user';
  const wsUrl = `ws://localhost:8000/ws/${userId}`;

  beforeEach(() => {
    server = new WS(wsUrl, { jsonProtocol: true });
  });

  afterEach(() => {
    WS.clean();
  });

  it('should correctly parse and process various message types', async () => {
    const { result } = renderHook(() => useAgent(userId));

    await server.connected;

    const messages = [
      { event: 'on_chat_model_stream', data: { chunk: { content: 'Here is' } } },
      { event: 'on_chat_model_stream', data: { chunk: { content: ' a list of the steps I will take to address your request:\n\n*   Analyze current costs\n*   Identify cost drivers\n' } } },
      { event: 'on_chat_model_stream', data: { chunk: { content: '*   Model future usage\n*   Simulate cost impact\n*   Simulate rate limit impact\n*   Generate' } } },
      { event: 'on_chat_model_stream', data: { chunk: { content: ' final report\n' } } },
      {
        event: 'on_chat_model_stream',
        data: {
          chunk: {
            content: '',
            additional_kwargs: { function_call: { name: 'cost_analyzer', arguments: '{}' } },
            response_metadata: { finish_reason: 'STOP', model_name: 'gemini-2.5-pro', safety_ratings: [] },
            id: 'run--9fb39c87-3029-4a31-967b-97bcfe64efe3',
            tool_calls: [{ name: 'cost_analyzer', args: {}, id: '60e57d84-7c6b-47e2-ba52-90cb2fe6d52b', type: 'tool_call' }],
            usage_metadata: { output_token_details: { reasoning: 0 }, output_tokens: 10, input_tokens: 0, input_token_details: { cache_read: 0 }, total_tokens: 10 },
            tool_call_chunks: [{ name: 'cost_analyzer', args: '{}', id: '60e57d84-7c6b-47e2-ba52-90cb2fe6d52b', index: null, type: 'tool_call_chunk' }]
          }
        }
      },
      { event: 'run_complete', data: { status: 'complete' } }
    ];

    for (const message of messages) {
        await act(async () => {
            server.send(JSON.stringify(message));
        });
    }

    await waitFor(() => {
      const { messages } = result.current;
      expect(messages.length).toBeGreaterThan(0);

      const textMessage = messages.find(m => m.type === 'text');
      expect(textMessage?.content).toContain('Here is a list of the steps');

      const toolMessage = messages.find(m => m.type === 'tool_start');
      expect(toolMessage).toBeDefined();
      expect(toolMessage?.tool).toBe('cost_analyzer');
      
      expect(toolMessage?.rawChunk).toBeDefined();
      if(toolMessage?.rawChunk) {
        expect(toolMessage.rawChunk.tool_call_chunks).toBeDefined();
        expect(toolMessage.rawChunk.tool_call_chunks?.[0].name).toBe('cost_analyzer');
      }
    }, { timeout: 20000 });
  });
});
