import React, { useState, FormEvent, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Send } from 'lucide-react';
import { ChatPanel } from './ChatPanel';
import { ChatMessageProps } from './ChatMessage';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';

interface ChatWindowProps {
    messages: ChatMessageProps['message'][];
    onSendMessage: (message: string) => void;
    isLoading: boolean;
    exampleQueries?: string[];
}

const ExampleQueries = ({ queries, onQueryClick }: { queries: string[], onQueryClick: (query: string) => void }) => (
    <div className="flex-1 overflow-y-auto p-4 flex justify-center">
        <Card className="w-full max-w-2xl flex flex-col overflow-hidden">
            <CardHeader>
                <CardTitle>Welcome to Apex Optimizer Agent</CardTitle>
                <CardDescription>Select an example query to start, or type your own message below.</CardDescription>
            </CardHeader>
            <CardContent className="overflow-y-auto">
                <div className="space-y-2">
                    {queries.map((q, i) => (
                        <Button key={i} variant="outline" className="w-full justify-start text-left h-auto p-2" onClick={() => onQueryClick(q)} style={{whiteSpace: 'normal', wordWrap: 'break-word'}}>
                            {q}
                        </Button>
                    ))}
                </div>
            </CardContent>
        </Card>
    </div>
);

export function ChatWindow({ messages, onSendMessage, isLoading, exampleQueries = [] }: ChatWindowProps) {
    const [input, setInput] = useState('');
    const [isAgentThinking, setIsAgentThinking] = useState(false);

    useEffect(() => {
        const lastMessage = messages[messages.length - 1];
        if (lastMessage?.role === 'agent' && lastMessage.isThinking) {
            setIsAgentThinking(true);
        } else {
            setIsAgentThinking(false);
        }
    }, [messages]);

    const handleSendMessage = (e: FormEvent) => {
        e.preventDefault();
        if (input.trim()) {
            onSendMessage(input.trim());
            setInput('');
        }
    };

    const handleExampleClick = (query: string) => {
        setInput(query);
    }

    return (
        <div className="flex flex-col h-full border rounded-xl shadow-sm">
            {messages.length > 0 ? (
                <ChatPanel messages={messages} />
            ) : (
                <ExampleQueries queries={exampleQueries} onQueryClick={handleExampleClick} />
            )}
            <div className="p-4 border-t bg-background rounded-b-xl">
                <form onSubmit={handleSendMessage} className="flex items-center gap-2">
                    <Input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={isAgentThinking ? "Agent is thinking..." : "Type your message..."}
                        disabled={isLoading || isAgentThinking}
                    />
                    <Button type="submit" size="icon" disabled={isLoading || isAgentThinking || !input.trim()}>
                        <Send className="h-4 w-4" />
                    </Button>
                </form>
            </div>
        </div>
    );
}
