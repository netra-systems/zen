
import { useState, useEffect, useCallback } from 'react';
import { Message, StateUpdate } from '@/app/types/chat';

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
            const parsedData = JSON.parse(event.data);

            // Handle on_chat_model_stream
            if (parsedData.event === 'on_chat_model_stream') {
                const chunk = parsedData.data.chunk;
                if (chunk.content) {
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
            }
            // Handle on_tool_start
            else if (parsedData.event === 'on_tool_start') {
                setMessages((prevMessages) => [
                    ...prevMessages,
                    {
                        id: Math.random().toString(),
                        role: 'assistant',
                        type: 'tool_start',
                        content: `Starting tool ${parsedData.name}...`,
                        tool: parsedData.name,
                        toolInput: parsedData.data.input,
                    },
                ]);
            }
            // Handle on_tool_end
            else if (parsedData.event === 'on_tool_end') {
                setMessages((prevMessages) => [
                    ...prevMessages,
                    {
                        id: Math.random().toString(),
                        role: 'assistant',
                        type: 'tool_end',
                        content: `Tool ${parsedData.name} finished.`,
                        tool: parsedData.name,
                        toolOutput: parsedData.data.output,
                    },
                ]);
            }
            // Handle on_tool_error
            else if (parsedData.event === 'on_tool_error') {
                setMessages((prevMessages) => [
                    ...prevMessages,
                    {
                        id: Math.random().toString(),
                        role: 'assistant',
                        type: 'error',
                        content: `Error in tool ${parsedData.name}.`,
                        tool: parsedData.name,
                        isError: true,
                        toolOutput: parsedData.data.error,
                    },
                ]);
            }
            // Handle update_state
            else if (parsedData.event === 'update_state') {
                setMessages((prevMessages) => [
                    ...prevMessages,
                    {
                        id: Math.random().toString(),
                        role: 'assistant',
                        type: 'state_update',
                        content: 'State updated.',
                        state: parsedData.data,
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
