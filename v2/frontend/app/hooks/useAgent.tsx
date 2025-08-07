import { getToken, getUserId } from '../lib/user';
import { useCallback, useRef, useState } from 'react';
import { Message, StreamEvent, ArtifactMessage } from '../types/chat';
import { produce } from 'immer';

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
    const socketRef = useRef<WebSocket | null>(null);
    const runIdRef = useRef<string | null>(null);

    const addMessage = (message: Message) => {
        setMessages(
            produce((draft) => {
                const existingMessageIndex = draft.findIndex((m) => m.id === message.id);
                if (existingMessageIndex !== -1) {
                    draft[existingMessageIndex] = message;
                } else {
                    draft.push(message);
                }
            }),
        );
    };

    const disconnect = useCallback(() => {
        if (socketRef.current) {
            socketRef.current.close();
            socketRef.current = null;
        }
    }, []);

    const startAgent = useCallback(
        async (message: string) => {
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

            const token = await getToken();
            if (!token) {
                setError(new Error('Authentication token not found.'));
                setShowThinking(false);
                return;
            }

            if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
                const runId = `run_${Date.now()}`;
                runIdRef.current = runId;

                const ws = new WebSocket(`ws://localhost:8000/agent/${runId}?token=${token}`);
                socketRef.current = ws;

                ws.onopen = () => {
                    console.log('WebSocket connected');
                    const thinkingMessage: Message = {
                        id: runIdRef.current!,
                        role: 'agent',
                        timestamp: new Date().toISOString(),
                        type: 'thinking',
                    };
                    addMessage(thinkingMessage);

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
                            id: runIdRef.current,
                            user_id: userId,
                            query: message,
                            workloads: [],
                        },
                    };
                    ws.send(JSON.stringify({ action: 'start_agent', payload: analysisRequest }));
                };

                ws.onmessage = (event) => {
                    const message: StreamEvent = JSON.parse(event.data);
                    console.log('Received message:', message);

                    if (message.event === 'run_complete') {
                        setShowThinking(false);
                        return;
                    }

                    setMessages((draft) => produce(draft, (d) => processStreamEvent(d, message)));
                };

                ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    setShowThinking(false);
                };

                ws.onerror = (event) => {
                    console.error('WebSocket error:', event);
                    setError(new Error('WebSocket connection failed.'));
                    setShowThinking(false);
                };
            } else {
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
                        id: runIdRef.current,
                        user_id: userId,
                        query: message,
                        workloads: [],
                    },
                };
                socketRef.current.send(JSON.stringify({ action: 'start_agent', payload: analysisRequest }));
            }
        },
        [disconnect],
    );

    return { startAgent, messages, showThinking, error };
}