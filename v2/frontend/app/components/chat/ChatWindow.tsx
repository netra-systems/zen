import React, { useState, FormEvent, useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Send } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { MessageFilterControl } from './MessageFilter';
import { useAgentStreaming } from '@/app/hooks/useAgentStreaming';

export function ChatWindow() {
    const { messages, addMessage, messageFilters, setMessageFilters, processStream } = useAgentStreaming();
    const [input, setInput] = useState('');
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSendMessage = (e: FormEvent) => {
        e.preventDefault();
        if (input.trim()) {
            addMessage(input.trim());
            // Here you would typically send the message to the agent
            // and start processing the stream of responses.
            // For demonstration purposes, we'll simulate a stream.
            const exampleStream = [
                'Thinking about your request...',
                JSON.stringify({ event: 'on_chain_start', data: { input: { messages: [] } } }),
                'Analyzing data...',
                JSON.stringify({ event: 'on_tool_start', data: { tool: 'calculator', input: '2+2' } }),
                'Performing calculations...',
                JSON.stringify({ event: 'on_tool_end', data: { tool: 'calculator', output: '4' } }),
                'Finalizing response...',
                JSON.stringify({ event: 'on_chain_end', data: { output: { answer: 'The answer is 4.' } } }),
            ];
            exampleStream.forEach((chunk, index) => {
                setTimeout(() => {
                    processStream(chunk);
                }, index * 1000);
            });
            setInput('');
        }
    };

    const isAgentThinking = messages.some(m => m.type === 'thinking');

    return (
        <div className="flex flex-col h-full border rounded-xl shadow-sm">
            <div className="p-4 border-b bg-background rounded-t-xl">
                <MessageFilterControl messageFilters={messageFilters} setMessageFilters={setMessageFilters} />
            </div>
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((message) => (
                    <ChatMessage key={message.id} message={message} />
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
            </div>
        </div>
    );
}
