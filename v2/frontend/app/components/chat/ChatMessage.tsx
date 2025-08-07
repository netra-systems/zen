import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Message } from '@/app/types/chat';
import { MessageContent } from './MessageContent';
import { TodoListView } from './TodoListView';

export interface ChatMessageProps {
    message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
    const isToolMessage = message.type === 'tool_start' || message.type === 'tool_end' || message.type === 'error';

    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="text-lg">{isToolMessage ? message.tool : message.type}</CardTitle>
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
        </Card>
    );
}