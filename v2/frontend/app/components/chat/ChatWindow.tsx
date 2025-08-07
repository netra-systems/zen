'use client';
import React, { useState, FormEvent, useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Send } from 'lucide-react';
import { MessageOrchestrator } from './MessageOrchestrator';
import { MessageFilterControl } from './MessageFilter';
import { Message, MessageFilter, ChatWindowProps } from '@/app/types/index';

export function ChatWindow({ 
    messages, 
    onSendMessage, 
    isLoading, 
    initialQuery, 
    messageFilters, 
    setMessageFilters, 
    exampleQueries = [] 
}: ChatWindowProps) {
    const [input, setInput] = useState(initialQuery || '');
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSendMessage = (e: FormEvent) => {
        e.preventDefault();
        if (input.trim()) {
            onSendMessage(input.trim());
            setInput('');
        }
    };

    const isAgentThinking = messages.some(m => m.type === 'thinking');

    

    return (
        <div className="flex flex-col h-full border rounded-xl shadow-sm">
            <div className="p-4 border-b bg-background rounded-t-xl">
                <MessageFilterControl 
                    messageFilters={messageFilters} 
                    setMessageFilters={setMessageFilters} 
                    showThinking={isLoading} 
                    setShowThinking={() => {}} 
                />
            </div>
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((message) => (
                    <MessageOrchestrator key={message.id} message={message} />
                ))}
            </div>
            <div className="p-4 border-t bg-background rounded-b-xl">
                <form onSubmit={handleSendMessage} className="flex items-center gap-2">
                    <Input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={isAgentThinking ? "Agent is thinking..." : "Type your message..."}
                        disabled={isAgentThinking}
                    />
                    <Button type="submit" size="icon" disabled={isAgentThinking || !input.trim()}>
                        <Send className="h-4 w-4" />
                    </Button>
                </form>
                <div className="flex flex-wrap gap-2 mt-2">
                    {exampleQueries.map((query) => (
                        <button
                            key={query}
                            onClick={() => handleExampleClick(query)}
                            className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-2 py-1 rounded-md text-sm"
                        >
                            {query}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}