import { useState, useEffect, useCallback } from 'react';
import {
    Message,
    AIMessageChunk,
    ServerEvent,
    AgentStartedData,
    ChainStartData,
    ChatModelStartData,
    ChatModelStreamData,
    RunCompleteData,
    ToolEndData,
    ToolErrorData,
    UpdateStateData
} from '@/app/types/chat';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function useAgent(userId: string, initialMessages: Message[] = []) {
    const [messages, setMessages] = useState<Message[]>(initialMessages);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [ws, setWs] = useState<WebSocket | null>(null);

    useEffect(() => {
        if (!userId) return;

        const wsUrl = `${API_URL.replace('http', 'ws')}/ws/${userId}`;
        const newWs = new WebSocket(wsUrl);

        newWs.onopen = () => {
            console.log('WebSocket connection established');
        };

        newWs.onmessage = (event) => {
            console.log('Received message:', event.data);
            try {
                const parsedData: ServerEvent = JSON.parse(event.data);

                setMessages((prevMessages) => {
                    let updatedMessages = [...prevMessages];
                    const lastMessage = updatedMessages[updatedMessages.length - 1];

                    switch (parsedData.event) {
                        case 'agent_started':
                            const agentStartedData = parsedData.data as AgentStartedData;
                            updatedMessages.push({
                                id: agentStartedData.run_id || Math.random().toString(),
                                role: 'assistant',
                                type: 'event',
                                content: `Agent started (Run ID: ${agentStartedData.run_id})`,
                                rawServerEvent: parsedData,
                            });
                            break;

                        case 'on_chain_start':
                            const chainStartData = parsedData.data as ChainStartData;
                            updatedMessages.push({
                                id: Math.random().toString(),
                                role: 'assistant',
                                type: 'event',
                                content: 'Chain started',
                                rawServerEvent: parsedData,
                            });
                            break;

                        case 'on_chat_model_start':
                            const chatModelStartData = parsedData.data as ChatModelStartData;
                            updatedMessages.push({
                                id: Math.random().toString(),
                                role: 'assistant',
                                type: 'event',
                                content: 'Chat model started',
                                rawServerEvent: parsedData,
                            });
                            break;

                        case 'on_chat_model_stream':
                            const streamData = parsedData.data as ChatModelStreamData;
                            const chunk = streamData.chunk;

                            if (chunk.tool_call_chunks && chunk.tool_call_chunks.length > 0) {
                                for (const toolCallChunk of chunk.tool_call_chunks) {
                                    const existingMessageIndex = updatedMessages.findIndex(msg => msg.id === toolCallChunk.id);

                                    if (existingMessageIndex !== -1) {
                                        const existingMessage = updatedMessages[existingMessageIndex];
                                        let currentArgs = existingMessage.toolInput || '';
                                        if (typeof currentArgs !== 'string') {
                                            currentArgs = JSON.stringify(currentArgs);
                                        }
                                        const newArgsChunk = toolCallChunk.args || '';
                                        updatedMessages[existingMessageIndex] = {
                                            ...existingMessage,
                                            toolInput: currentArgs + newArgsChunk,
                                            rawServerEvent: parsedData,
                                            usageMetadata: chunk.usage_metadata,
                                            responseMetadata: chunk.response_metadata,
                                        };
                                    } else {
                                        updatedMessages.push({
                                            id: toolCallChunk.id,
                                            role: 'assistant',
                                            type: 'tool_start',
                                            content: `Starting tool ${toolCallChunk.name}...`,
                                            tool: toolCallChunk.name,
                                            toolInput: toolCallChunk.args || '',
                                            rawServerEvent: parsedData,
                                            usageMetadata: chunk.usage_metadata,
                                            responseMetadata: chunk.response_metadata,
                                        });
                                    }
                                }
                            } else if (chunk.content) {
                                if (lastMessage && lastMessage.role === 'assistant' && lastMessage.type === 'text') {
                                    updatedMessages[updatedMessages.length - 1] = {
                                        ...lastMessage,
                                        content: lastMessage.content + chunk.content,
                                        rawServerEvent: parsedData,
                                        usageMetadata: chunk.usage_metadata,
                                        responseMetadata: chunk.response_metadata,
                                    };
                                } else {
                                    updatedMessages.push({
                                        id: chunk.id || Math.random().toString(),
                                        role: 'assistant',
                                        type: 'text',
                                        content: chunk.content,
                                        rawServerEvent: parsedData,
                                        usageMetadata: chunk.usage_metadata,
                                        responseMetadata: chunk.response_metadata,
                                    });
                                }
                            }
                            break;

                        case 'run_complete':
                            const runCompleteData = parsedData.data as RunCompleteData;
                            updatedMessages.push({
                                id: Math.random().toString(),
                                role: 'assistant',
                                type: 'event',
                                content: `Run complete (Status: ${runCompleteData.status})`,
                                rawServerEvent: parsedData,
                            });
                            break;

                        case 'on_tool_end':
                            const toolEndData = parsedData.data as ToolEndData;
                            const toolCallId = parsedData.run_id;
                            const msgIndex = updatedMessages.findIndex(msg => msg.id === toolCallId)
                            if (msgIndex !== -1) {
                                updatedMessages[msgIndex] = {
                                    ...updatedMessages[msgIndex],
                                    type: 'tool_end',
                                    toolOutput: toolEndData.output,
                                    rawServerEvent: parsedData,
                                };
                            }
                            break;

                        case 'on_tool_error':
                            const toolErrorData = parsedData.data as ToolErrorData;
                            const errorToolCallId = parsedData.run_id;
                            const errorMsgIndex = updatedMessages.findIndex(msg => msg.id === errorToolCallId)
                            if (errorMsgIndex !== -1) {
                                updatedMessages[errorMsgIndex] = {
                                    ...updatedMessages[errorMsgIndex],
                                    type: 'error',
                                    isError: true,
                                    toolOutput: toolErrorData.error,
                                    rawServerEvent: parsedData,
                                };
                            }
                            break;

                        case 'update_state':
                            const updateStateData = parsedData.data as UpdateStateData;
                            if (lastMessage) {
                                updatedMessages[updatedMessages.length - 1] = {
                                    ...lastMessage,
                                    state: updateStateData.data,
                                    rawServerEvent: parsedData,
                                };
                            }
                            break;

                        default:
                            updatedMessages.push({
                                id: Math.random().toString(),
                                role: 'assistant',
                                type: 'event',
                                content: `Unknown event: ${parsedData.event}`,
                                rawServerEvent: parsedData,
                            });
                            break;
                    }
                    return updatedMessages;
                });

            } catch (e) {
                console.error('Failed to parse message or update state:', e);
                setMessages((prevMessages) => [
                    ...prevMessages,
                    {
                        id: Math.random().toString(),
                        role: 'assistant',
                        type: 'text',
                        content: `Could not parse message: ${event.data}`,
                    },
                ]);
            }
        };

        newWs.onclose = () => {
            console.log('WebSocket connection closed');
        };

        newWs.onerror = (err) => {
            console.error('WebSocket error:', err);
            setError(new Error('WebSocket connection error'));
        };

        setWs(newWs);

        return () => {
            newWs.close();
        };
    }, [userId]);

    const sendMessage = useCallback(
        async (messageContent: string) => {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                setError(new Error('WebSocket is not connected.'));
                return;
            }

            if (!messageContent.trim()) return;

            const userMessage: Message = {
                id: Math.random().toString(),
                role: 'user',
                type: 'text',
                content: messageContent,
            };
            setMessages((prevMessages) => [...prevMessages, userMessage]);
            setIsLoading(true);

            try {
                ws.send(JSON.stringify({ type: 'user_message', data: messageContent }));
            } catch (err) {
                console.error('Failed to send message:', err);
                setError(err instanceof Error ? err : new Error('Failed to send message'));
            } finally {
                setIsLoading(false);
                setInput('');
            }
        },
        [ws]
    );

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setInput(e.target.value);
    };

    return {
        messages,
        input,
        isLoading,
        error,
        sendMessage,
        handleInputChange,
        setInput,
    };
}