import { useState, useEffect, useCallback } from 'react';
import { Message, AIMessageChunk } from '@/app/types/chat';

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
                const parsedData = JSON.parse(event.data);

                if (parsedData.event === 'on_chat_model_stream') {
                    const chunk: AIMessageChunk = parsedData.data.chunk;

                    setMessages((prevMessages) => {
                        let updatedMessages = [...prevMessages];
                        const lastMessage = updatedMessages[updatedMessages.length - 1];

                        // Handle tool call chunks
                        if (chunk.tool_call_chunks && chunk.tool_call_chunks.length > 0) {
                            for (const toolCallChunk of chunk.tool_call_chunks) {
                                const existingMessageIndex = updatedMessages.findIndex(msg => msg.id === toolCallChunk.id);

                                if (existingMessageIndex !== -1) {
                                    // Update existing tool message
                                    const existingMessage = updatedMessages[existingMessageIndex];
                                    let currentArgs = existingMessage.toolInput || '';
                                    if (typeof currentArgs !== 'string') {
                                        currentArgs = JSON.stringify(currentArgs);
                                    }
                                    const newArgsChunk = toolCallChunk.args || '';
                                    updatedMessages[existingMessageIndex] = {
                                        ...existingMessage,
                                        toolInput: currentArgs + newArgsChunk,
                                        rawChunk: chunk
                                    };
                                } else {
                                    // Add new tool message
                                    updatedMessages.push({
                                        id: toolCallChunk.id,
                                        role: 'assistant',
                                        type: 'tool_start',
                                        content: `Starting tool ${toolCallChunk.name}...`,
                                        tool: toolCallChunk.name,
                                        toolInput: toolCallChunk.args || '',
                                        rawChunk: chunk
                                    });
                                }
                            }
                        } else if (chunk.content) {
                            // Handle content chunks
                            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.type === 'text') {
                                // Append to last text message
                                updatedMessages[updatedMessages.length - 1] = {
                                    ...lastMessage,
                                    content: lastMessage.content + chunk.content,
                                    rawChunk: chunk
                                };
                            } else {
                                // Add new text message
                                updatedMessages.push({
                                    id: chunk.id || Math.random().toString(),
                                    role: 'assistant',
                                    type: 'text',
                                    content: chunk.content,
                                    rawChunk: chunk
                                });
                            }
                        }
                        return updatedMessages;
                    });
                } else if (parsedData.event === 'on_chat_model_end') {
                    const output: AIMessageChunk = parsedData.data.output;
                    if (output.content) {
                         setMessages((prevMessages) => {
                            const lastMessage = prevMessages[prevMessages.length - 1];
                            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.type === 'text' && !lastMessage.content.endsWith(output.content)) {
                                return [
                                    ...prevMessages.slice(0, -1),
                                    { ...lastMessage, content: output.content, rawChunk: output },
                                ];
                            } else if (lastMessage && lastMessage.type !== 'text') {
                                return [
                                    ...prevMessages,
                                    {
                                        id: output.id || Math.random().toString(),
                                        role: 'assistant',
                                        type: 'text',
                                        content: output.content,
                                        rawChunk: output
                                    },
                                ];
                            }
                            return prevMessages;
                        });
                    }
                } else if (parsedData.event === 'on_tool_end') {
                    setMessages((prevMessages) => {
                        const toolCallId = parsedData.run_id;
                        return prevMessages.map((msg) =>
                            msg.id === toolCallId
                                ? { ...msg, type: 'tool_end', toolOutput: parsedData.data.output }
                                : msg
                        );
                    });
                } else if (parsedData.event === 'on_tool_error') {
                    setMessages((prevMessages) => {
                        const toolCallId = parsedData.run_id;
                        return prevMessages.map((msg) =>
                            msg.id === toolCallId
                                ? { ...msg, type: 'error', isError: true, toolOutput: parsedData.data.error }
                                : msg
                        );
                    });
                } else if (parsedData.event === 'update_state') {
                    setMessages((prevMessages) => {
                        const lastMessage = prevMessages[prevMessages.length - 1];
                        if (lastMessage) {
                            return [
                                ...prevMessages.slice(0, -1),
                                { ...lastMessage, state: parsedData.data },
                            ];
                        }
                        return prevMessages;
                    });
                }
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