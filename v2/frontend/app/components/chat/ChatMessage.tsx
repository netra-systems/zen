import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Message, ChatMessageProps } from '@/app/types';
import { MessageContent } from './MessageContent';
import { TodoListView } from './TodoListView';
import JsonTreeView from './JsonTreeView';
import { getTitle } from '@/app/lib/utils';

export function ChatMessage({ message }: ChatMessageProps) {
    const title = getTitle(message);

    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="text-lg">{title}</CardTitle>
                {message.type === 'tool_start' && message.content && <p className="text-sm text-gray-500">{message.content}</p>}
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