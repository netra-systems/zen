import { getToken, getUserId } from '../lib/user';
import { useCallback, useEffect, useState } from 'react';
import { Message, StreamEvent, ArtifactMessage } from '../types/chat';
import { produce } from 'immer';
import { useWebSocket, WebSocketStatus } from './useWebSocket';

const parseChunkData = (chunkStr: string): any => {
    if (typeof chunkStr !== 'string' || !chunkStr.trim()) {
        return chunkStr;
    }

    const result: { [key: string]: any } = {};
    // This regex splits the string by spaces that are followed by a key-like identifier and an equals sign.
    // This is to avoid splitting inside nested structures like dictionaries or lists.
    const parts = chunkStr.trim().split(/\s+(?=(?:[a-zA-Z_][a-zA-Z0-9_]*=))/);

    for (const part of parts) {
        const firstEqualIndex = part.indexOf('=');
        if (firstEqualIndex === -1) continue;

        const key = part.substring(0, firstEqualIndex);
        let valueStr = part.substring(firstEqualIndex + 1);

        try {
            // This is a workaround to parse Python-like string literals into JSON.
            // It's inherently fragile and might not cover all edge cases.
            // A proper fix would be for the backend to send valid JSON.
            const jsonStr = valueStr
                .replace(/None/g, 'null')
                .replace(/True/g, 'true')
                .replace(/False/g, 'false')
                .replace(/\\'/g, "'") // Unescape single quotes
                .replace(/\\"/g, '"') // Unescape double quotes
                .replace(/'/g, '"'); // Replace single quotes with double quotes for JSON

            result[key] = JSON.parse(jsonStr);
        } catch (e) {
            console.error('Failed to parse chunk value:', valueStr, e);
            // Fallback for simple strings or parsing errors
            result[key] = valueStr;
        }
    }
    return result;
};

const processStreamEvent = (draft: Message[], event: StreamEvent) => {
    const { event: eventName, data, run_id } = event;

    let existingMessage = draft.find((m) => m.id === run_id) as Message | undefined;

    if (!existingMessage) {
        const newMessage: Message = {
            id: run_id || `msg_${Date.now()}`,
            role: 'agent',
            timestamp: new Date().toISOString(),
            type: 'thinking',
            content: '',
        };
        draft.push(newMessage);
        existingMessage = newMessage;
    }

    const getMessageType = (eventName: string): Message['type'] => {
        switch (eventName) {
            case 'on_chain_start':
                return 'state_update';
            case 'on_chain_end':
                return 'tool_end';
            case 'on_chat_model_stream':
                return 'tool_code';
            case 'on_tool_end':
                return 'tool_end';
            case 'on_tool_start':
                return 'tool_start';
            case 'update_state':
                return 'state_update';
            default:
                return 'artifact';
        }
    };

    if (existingMessage.type === 'thinking') {
        existingMessage.type = getMessageType(eventName);
    }

    switch (eventName) {
        case 'on_chain_start':
            if (data.input?.todo_list) {
                existingMessage.state = {
                    todo_list: data.input.todo_list,
                    completed_steps: data.input.completed_steps || [],
                };
            }
            break;

        case 'on_chain_end':
            existingMessage.content = '';
            break;

        case 'on_chat_model_stream':
            const chunk = typeof data.chunk === 'string'
                ? parseChunkData(data.chunk)
                : data.chunk;

            if (chunk?.content) {
                existingMessage.content = (existingMessage.content || '') + chunk.content;
            }
            if (chunk?.tool_calls) {
                existingMessage.type = 'tool_start';
                // @ts-ignore
                if (!existingMessage.tool_calls) {
                    // @ts-ignore
                    existingMessage.tool_calls = [];
                }
                chunk.tool_calls.forEach((toolCall) => {
                    if (toolCall.name === 'update_state') {
                        existingMessage.state = toolCall.args as any;
                    } else {
                        existingMessage.tool = toolCall.name;
                        // @ts-ignore
                        const existingCallIndex = existingMessage.tool_calls.findIndex((tc) => tc.id === toolCall.id);
                        if (existingCallIndex > -1) {
                            // @ts-ignore
                            existingMessage.tool_calls[existingCallIndex] = toolCall;
                        } else {
                            // @ts-ignore
                            existingMessage.tool_calls.push(toolCall);
                        }
                    }
                });
            }
            break;

        case 'on_tool_start':
            existingMessage.tool = data.name;
            existingMessage.toolInput = data.input;
            break;

        case 'on_tool_end':
            if (data.output) {
                // @ts-ignore
                if (!existingMessage.tool_outputs) {
                    // @ts-ignore
                    existingMessage.tool_outputs = [];
                }
                const toolOutput = {
                    tool_call_id: run_id,
                    content: typeof data.output === 'string' ? data.output : JSON.stringify(data.output),
                    is_error: data.is_error || false,
                };
                // @ts-ignore
                existingMessage.tool_outputs.push(toolOutput);
            }
            break;
        case 'update_state':
            if (data.todo_list) {
                existingMessage.state = {
                    todo_list: data.todo_list,
                    completed_steps: data.completed_steps || [],
                };
            }
            break;
    }
};

export function useAgent() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [showThinking, setShowThinking] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const { sendMessage, lastMessage, status, connect, disconnect } = useWebSocket();

    useEffect(() => {
        const connectToSocket = async () => {
            const token = await getToken();
            if (!token) {
                setError(new Error('Authentication token not found.'));
                return;
            }
            const runId = `run_${Date.now()}`;
            const url = `ws://localhost:8000/agent/${runId}?token=${token}`;
            connect(url);
        };

        if (status === WebSocketStatus.Closed) {
            connectToSocket();
        }
    }, [status, connect]);

    useEffect(() => {
        if (status === WebSocketStatus.Open && lastMessage) {
            const message: StreamEvent = JSON.parse(lastMessage.data);
            console.log('Received message:', message);

            if (message.event === 'run_complete') {
                setShowThinking(false);
                return;
            }

            setMessages((draft) => produce(draft, (d) => processStreamEvent(d, message)));
        }
    }, [lastMessage, status]);

    const startAgent = useCallback(
        async (message: string) => {
            if (status !== WebSocketStatus.Open) {
                setError(new Error('WebSocket is not connected.'));
                return;
            }

            const userMessage: Message = {
                id: `msg_${Date.now()}`,
                role: 'user',
                timestamp: new Date().toISOString(),
                type: 'text',
                content: message,
            };
            setMessages((prev) => [...prev, userMessage]);

            setShowThinking(true);
            setError(null);

            const userId = getUserId();
            if (!userId) {
                console.error('User ID not found');
                setError(new Error('User ID not found.'));
                setShowThinking(false);
                return;
            }

            const analysisRequest = {
                settings: {
                    debug_mode: false,
                },
                request: {
                    user_id: userId,
                    query: message,
                    workloads: [],
                },
            };
            sendMessage({ action: 'start_agent', payload: analysisRequest });
        },
        [status, sendMessage],
    );

    return { startAgent, messages, showThinking, error, status };
}