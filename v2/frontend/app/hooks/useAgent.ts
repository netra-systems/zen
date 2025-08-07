import { getToken, getUserId } from '../lib/user';
import { useCallback, useEffect, useState } from 'react';
import { Message, StreamEvent, ArtifactMessage } from '../types/chat';
import { produce } from 'immer';
import { useWebSocket, WebSocketStatus } from './useWebSocket';

const processStreamEvent = (draft: Message[], event: StreamEvent) => {
    const { event: eventName, data, run_id } = event;

    let existingMessage = draft.find((m) => m.id === run_id) as ArtifactMessage | undefined;

    if (!existingMessage || existingMessage.type !== 'artifact') {
        const newMessage: ArtifactMessage = {
            id: run_id || `msg_${Date.now()}`,
            role: 'agent',
            timestamp: new Date().toISOString(),
            type: 'artifact',
            name: eventName,
            data: data,
            tool_calls: [],
            tool_outputs: [],
            state_updates: { todo_list: [], completed_steps: [] },
        };
        draft.push(newMessage);
        existingMessage = newMessage;
    } else {
        existingMessage.name = eventName;
        existingMessage.data = data;
    }

    switch (eventName) {
        case 'on_chain_start':
            if (data.input?.todo_list) {
                existingMessage.state_updates = {
                    todo_list: data.input.todo_list,
                    completed_steps: data.input.completed_steps || [],
                };
            }
            break;

        case 'on_chain_end':
            existingMessage.content = undefined;
            break;

        case 'on_chain_end':
            existingMessage.content = undefined;
            break;

        case 'on_chat_model_stream':
            if (data.chunk?.content) {
                existingMessage.content = (existingMessage.content || '') + data.chunk.content;
            }
            if (data.chunk?.tool_calls) {
                data.chunk.tool_calls.forEach((toolCall) => {
                    if (toolCall.name === 'update_state') {
                        existingMessage.state_updates = toolCall.args as any;
                    } else {
                        const existingCallIndex = existingMessage.tool_calls.findIndex((tc) => tc.id === toolCall.id);
                        if (existingCallIndex > -1) {
                            existingMessage.tool_calls[existingCallIndex] = toolCall;
                        } else {
                            existingMessage.tool_calls.push(toolCall);
                        }
                    }
                });
            }
            break;

        case 'on_tool_end':
            if (data.output) {
                const toolOutput = {
                    tool_call_id: run_id,
                    content: typeof data.output === 'string' ? data.output : JSON.stringify(data.output),
                    is_error: data.is_error || false,
                };
                existingMessage.tool_outputs.push(toolOutput);
            }
            break;

        default:
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