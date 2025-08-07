
import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Message } from '@/app/types/chat';
import { MessageContent } from './MessageContent';
import { TodoListView } from './TodoListView';
import JsonTreeView from './JsonTreeView';

export interface ChatMessageProps {
    message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
    const isToolMessage = message.type === 'tool_start' || message.type === 'tool_end' || message.type === 'error';
    const title = isToolMessage ? message.tool : message.role === 'user' ? 'User' : 'Assistant';

    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="text-lg">{title}</CardTitle>
                {isToolMessage && message.content && <p className="text-sm text-gray-500">{message.content}</p>}
            </CardHeader>
            <CardContent>
                <MessageContent message={message} />
            </CardContent>
            {message.state && (
                <CardFooter>
                    <Accordion type="single" collapsible className="w-full">
                        <AccordionItem value="item-1">
                            <AccordionTrigger>TODO List</AccordionTrigger>
                            <AccordionContent>
                                <TodoListView todoList={message.state} />
                            </AccordionContent>
                        </AccordionItem>
                    </Accordion>
                </CardFooter>
            )}
            {message.type === 'error' && message.toolOutput && (
                <CardFooter>
                    <Accordion type="single" collapsible className="w-full">
                        <AccordionItem value="item-1">
                            <AccordionTrigger>Error</AccordionTrigger>
                            <AccordionContent>
                                <JsonTreeView data={message.toolOutput} />
                            </AccordionContent>
                        </AccordionItem>
                    </Accordion>
                </CardFooter>
            )}
        </Card>
    );
}
