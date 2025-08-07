
import { useState, useEffect, useCallback } from 'react';
import { Message, StateUpdate } from '@/app/types/chat';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function parsePythonRepr(reprString: string): any {
    if (!reprString || typeof reprString !== 'string') {
        return {};
    }

    function jsonSafeParse(str: string) {
        try {
            return JSON.parse(str.replace(/'/g, '"').replace(/None/g, 'null').replace(/True/g, 'true').replace(/False/g, 'false'));
        } catch (e) {
            console.error("jsonSafeParse failed for string:", str, e);
            return null;
        }
    }

    const result: any = {};

    const contentMatch = reprString.match(/content='((?:\'|[^'])*)'/);
    if (contentMatch && contentMatch[1]) {
        result.content = contentMatch[1].replace(/\'/g, "'");
    }

    const toolCallsMatch = reprString.match(/tool_calls=(\[.*?\])(?=, additional_kwargs=|, response_metadata=|, id=|, usage_metadata=|, tool_call_chunks=|$)/s);
    if (toolCallsMatch && toolCallsMatch[1]) {
        result.tool_calls = jsonSafeParse(toolCallsMatch[1]);
    }

    const toolCallChunksMatch = reprString.match(/tool_call_chunks=(\[.*?\])(?=, additional_kwargs=|, response_metadata=|, id=|, usage_metadata=|$)/s);
    if (toolCallChunksMatch && toolCallChunksMatch[1]) {
        result.tool_call_chunks = jsonSafeParse(toolCallChunksMatch[1]);
    }
    
    if (Object.keys(result).length === 0) {
        return { content: reprString };
    }

    return result;
}


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
                    const chunk = typeof parsedData.data.chunk === 'string' 
                        ? parsePythonRepr(parsedData.data.chunk) 
                        : parsedData.data.chunk;

                    const toolCallChunks = chunk.tool_call_chunks;

                    if (toolCallChunks && toolCallChunks.length > 0) {
                        const toolCallChunk = toolCallChunks[0];
                        if (toolCallChunk.name && toolCallChunk.id) {
                            setMessages((prevMessages) => {
                                const existingMessageIndex = prevMessages.findIndex(msg => msg.id === toolCallChunk.id);
                                if (existingMessageIndex !== -1) {
                                    const updatedMessages = [...prevMessages];
                                    const existingMessage = updatedMessages[existingMessageIndex];
                                    
                                    let currentArgs = existingMessage.toolInput || '';
                                    if (typeof currentArgs !== 'string') {
                                        currentArgs = JSON.stringify(currentArgs);
                                    }
                                    
                                    const newArgsChunk = toolCallChunk.args || '';
                                    const combinedArgs = currentArgs + newArgsChunk;

                                    updatedMessages[existingMessageIndex] = {
                                        ...existingMessage,
                                        toolInput: combinedArgs,
                                    };
                                    return updatedMessages;
                                } else {
                                    return [
                                        ...prevMessages,
                                        {
                                            id: toolCallChunk.id,
                                            role: 'assistant',
                                            type: 'tool_start',
                                            content: `Starting tool ${toolCallChunk.name}...`,
                                            tool: toolCallChunk.name,
                                            toolInput: toolCallChunk.args || '',
                                        },
                                    ];
                                }
                            });
                        }
                    } else if (chunk.content) {
                        setMessages((prevMessages) => {
                            const lastMessage = prevMessages[prevMessages.length - 1];
                            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.type === 'text') {
                                return [
                                    ...prevMessages.slice(0, -1),
                                    { ...lastMessage, content: lastMessage.content + chunk.content },
                                ];
                            }
                            return [
                                ...prevMessages,
                                {
                                    id: Math.random().toString(),
                                    role: 'assistant',
                                    type: 'text',
                                    content: chunk.content,
                                },
                            ];
                        });
                    }
                } else if (parsedData.event === 'on_chat_model_end') {
                    const output = typeof parsedData.data.output === 'string'
                        ? parsePythonRepr(parsedData.data.output)
                        : parsedData.data.output;

                    if (output.content) {
                         setMessages((prevMessages) => {
                            const lastMessage = prevMessages[prevMessages.length - 1];
                            // If the last message was a tool call, we might need to add a new text message for the final answer.
                            // Or if the last message was a text message being streamed, update it.
                            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.type === 'text' && !lastMessage.content.endsWith(output.content)) {
                                return [
                                    ...prevMessages.slice(0, -1),
                                    { ...lastMessage, content: output.content },
                                ];
                            } else if (lastMessage && lastMessage.type !== 'text') {
                                return [
                                    ...prevMessages,
                                    {
                                        id: Math.random().toString(),
                                        role: 'assistant',
                                        type: 'text',
                                        content: output.content,
                                    },
                                ];
                            }
                            return prevMessages;
                        });
                    }
                } else if (parsedData.event === 'on_tool_end') {
                    setMessages((prevMessages) => {
                        const toolCallId = parsedData.run_id; // Assuming run_id from on_tool_end corresponds to tool call id
                        const lastMessage = prevMessages.findLast((msg) => msg.id === toolCallId);
                        if (lastMessage) {
                            return prevMessages.map((msg) =>
                                msg.id === lastMessage.id
                                    ? { ...msg, type: 'tool_end', toolOutput: parsedData.data.output }
                                    : msg
                            );
                        }
                        return prevMessages;
                    });
                } else if (parsedData.event === 'on_tool_error') {
                    setMessages((prevMessages) => {
                        const toolCallId = parsedData.run_id;
                        const lastMessage = prevMessages.findLast((msg) => msg.id === toolCallId);
                        if (lastMessage) {
                            return prevMessages.map((msg) =>
                                msg.id === lastMessage.id
                                    ? { ...msg, type: 'error', isError: true, toolOutput: parsedData.data.error }
                                    : msg
                            );
                        }
                        return prevMessages;
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
