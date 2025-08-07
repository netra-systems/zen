import { useState, useEffect, useCallback } from 'react';
import {
    Message,
    ServerEvent,
    AgentStartedData,
    ChainStartData,
    ChatModelStartData,
    ChatModelStreamData,
    RunCompleteData,
    ToolEndData,
    ToolErrorData,
    UpdateStateData,
    UserMessage,
    EventMessage,
    TextMessage,
    ToolStartMessage,
    ToolEndMessage,
    ErrorMessage,
    ThinkingMessage,
    StateUpdateMessage,
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

                    switch (parsedData.event) {
                        case 'agent_started':
                            const agentStartedData = parsedData.data as AgentStartedData;
                            updatedMessages.push({
                                id: agentStartedData.run_id || Math.random().toString(),
                                role: 'assistant',
                                type: 'event',
                                content: `Agent started (Run ID: ${agentStartedData.run_id})`,
                                eventName: parsedData.event,
                                rawServerEvent: parsedData,
                            } as EventMessage);
                            break;

                        case 'on_chain_start':
                            updatedMessages.push({
                                id: parsedData.run_id || Math.random().toString(),
                                role: 'assistant',
                                type: 'event',
                                content: 'Chain started',
                                eventName: parsedData.event,
                                rawServerEvent: parsedData,
                            } as EventMessage);
                            break;

                        case 'on_chat_model_start':
                            updatedMessages.push({
                                id: parsedData.run_id || Math.random().toString(),
                                role: 'assistant',
                                type: 'event',
                                content: 'Chat model started',
                                eventName: parsedData.event,
                                rawServerEvent: parsedData,
                            } as EventMessage);
                            break;

                        case 'on_chat_model_stream':
                            const streamData = parsedData.data as ChatModelStreamData;
                            const chunk = streamData.chunk;

                            if (chunk.tool_call_chunks && chunk.tool_call_chunks.length > 0) {
                                for (const toolCallChunk of chunk.tool_call_chunks) {
                                    const existingMessageIndex = updatedMessages.findIndex(msg => msg.id === toolCallChunk.id);

                                    if (existingMessageIndex !== -1) {
                                        const existingMessage = updatedMessages[existingMessageIndex] as ToolStartMessage;
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
                                        } as ToolStartMessage;
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
                                        } as ToolStartMessage);
                                    }
                                }
                            } else if (chunk.content) {
                                const lastMessage = updatedMessages[updatedMessages.length - 1];
                                if (lastMessage && lastMessage.type === 'text') {
                                    (lastMessage as TextMessage).content += chunk.content;
                                    (lastMessage as TextMessage).usageMetadata = chunk.usage_metadata;
                                    (lastMessage as TextMessage).responseMetadata = chunk.response_metadata;
                                } else {
                                    updatedMessages.push({
                                        id: chunk.id || parsedData.run_id || Math.random().toString(),
                                        role: 'assistant',
                                        type: 'text',
                                        content: chunk.content,
                                        rawServerEvent: parsedData,
                                        usageMetadata: chunk.usage_metadata,
                                        responseMetadata: chunk.response_metadata,
                                    } as TextMessage);
                                }
                            }
                            break;

                        case 'run_complete':
                            const runCompleteData = parsedData.data as RunCompleteData;
                            updatedMessages.push({
                                id: parsedData.run_id || Math.random().toString(),
                                role: 'assistant',
                                type: 'event',
                                content: `Run complete (Status: ${runCompleteData.status})`,
                                eventName: parsedData.event,
                                rawServerEvent: parsedData,
                            } as EventMessage);
                            break;

                        case 'on_tool_end':
                            const toolEndData = parsedData.data as ToolEndData;
                            const toolCallId = parsedData.run_id;
                            const msgIndex = updatedMessages.findIndex(msg => msg.id === toolCallId);
                            if (msgIndex !== -1) {
                                const startMessage = updatedMessages[msgIndex] as ToolStartMessage;
                                updatedMessages[msgIndex] = {
                                    ...startMessage,
                                    type: 'tool_end',
                                    toolOutput: toolEndData.output,
                                    content: `Tool ${startMessage.tool} finished.`,
                                    rawServerEvent: parsedData,
                                } as ToolEndMessage;
                            }
                            break;

                        case 'on_tool_error':
                            const toolErrorData = parsedData.data as ToolErrorData;
                            const errorToolCallId = parsedData.run_id;
                            const errorMsgIndex = updatedMessages.findIndex(msg => msg.id === errorToolCallId);
                            if (errorMsgIndex !== -1) {
                                const startMessage = updatedMessages[errorMsgIndex] as ToolStartMessage;
                                updatedMessages[errorMsgIndex] = {
                                    ...startMessage,
                                    type: 'error',
                                    isError: true,
                                    toolOutput: toolErrorData.error,
                                    content: `Error in tool ${startMessage.tool}`,
                                    rawServerEvent: parsedData,
                                } as ErrorMessage;
                            }
                            break;

                        case 'update_state':
                            const updateStateData = parsedData.data as UpdateStateData;
                            const lastMessage = updatedMessages[updatedMessages.length - 1];
                            if (lastMessage) {
                                updatedMessages.push({
                                    id: parsedData.run_id || Math.random().toString(),
                                    role: 'assistant',
                                    type: 'state_update',
                                    content: 'State updated',
                                    state: updateStateData.data,
                                    rawServerEvent: parsedData,
                                } as StateUpdateMessage);
                            }
                            break;

                        default:
                            updatedMessages.push({
                                id: parsedData.run_id || Math.random().toString(),
                                role: 'assistant',
                                type: 'event',
                                content: `Unknown event: ${parsedData.event}`,
                                eventName: parsedData.event,
                                rawServerEvent: parsedData,
                            } as EventMessage);
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
                        type: 'error',
                        content: `Could not parse message: ${event.data}`,
                        isError: true,
                    } as ErrorMessage,
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

            const userMessage: UserMessage = {
                id: Math.random().toString(),
                role: 'user',
                type: 'user',
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
