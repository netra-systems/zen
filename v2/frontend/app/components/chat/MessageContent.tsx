import React from 'react';
import { Message } from '@/app/types/chat';
import JsonTreeView from './JsonTreeView';
import { TodoListView } from './TodoListView';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';

export interface MessageContentProps {
    message: Message;
}

export function MessageContent({ message }: MessageContentProps) {
    switch (message.type) {
        case 'text':
            return <p>{message.content}</p>;
        case 'thinking':
            return (
                <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900"></div>
                    <p>{message.content || 'Thinking...'}</p>
                </div>
            );
        case 'error':
            return (
                <div>
                    <p className="text-red-500">{message.content}</p>
                </div>
            );
        case 'tool_start':
            return (
                <div>
                    {message.toolInput && <JsonTreeView data={message.toolInput} />}
                </div>
            );
        case 'tool_end':
            return (
                <div>
                    {message.toolOutput && <JsonTreeView data={message.toolOutput} />}
                </div>
            );
        case 'state_update':
            return <div>{message.state && <TodoListView todoList={message.state} />}</div>;
        default:
            return (
                <Accordion type="single" collapsible className="w-full">
                    <AccordionItem value="item-1">
                        <AccordionTrigger>Raw Message</AccordionTrigger>
                        <AccordionContent>
                            <pre>{JSON.stringify(message, null, 2)}</pre>
                        </AccordionContent>
                    </AccordionItem>
                </Accordion>
            );
    }
}