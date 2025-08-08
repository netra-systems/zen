'use client';

import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { JsonView, allExpanded, defaultStyles } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { MessageContent } from '@/components/chat/MessageContent';
import { TodoListView } from '@/components/chat/TodoListView';
import { Message, MessageCardProps } from '@/types/index';

export function MessageCard({ message, user }: MessageCardProps) {
  const getToolName = (message: Message) => {
    if ('tool' in message) {
      return message.tool;
    }
    return null;
  };

  const toolName = getToolName(message);

  return (
    <Card className={`flex items-start gap-4 p-4 ${message.role === 'user' ? 'justify-end' : ''}`}>
      {message.role === 'assistant' && (
        <Avatar>
          <AvatarImage src="/agent-avatar.png" />
          <AvatarFallback>A</AvatarFallback>
        </Avatar>
      )}
      <div className={`rounded-lg p-3 max-w-[75%] ${message.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
        <div className="flex flex-col">
          {toolName && <CardHeader><CardTitle>{toolName}</CardTitle></CardHeader>}
          <MessageContent message={message} />
          {message.type === 'tool_end' && message.toolOutput?.is_error && (
            <div className="mt-2 text-red-500">
              <p>Error: {message.toolOutput.content}</p>
            </div>
          )}
          {message.type === 'state_update' && (
            <Accordion type="single" collapsible className="w-full mt-2">
              <AccordionItem value="item-1">
                <AccordionTrigger className="text-xs text-gray-500">TODO List</AccordionTrigger>
                <AccordionContent>
                  <TodoListView todoList={message.state} />
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          )}
          {message.type === 'error' && (
            <div className="mt-2 text-red-500">
              <p>Error: {message.content}</p>
            </div>
          )}
        </div>
        {message.role === 'assistant' && (
          <Accordion type="single" collapsible className="w-full mt-2">
            <AccordionItem value="item-1">
              <AccordionTrigger className="text-xs text-gray-500">Raw Message</AccordionTrigger>
              <AccordionContent>
                <JsonView data={message} shouldExpandNode={allExpanded} style={defaultStyles} />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        )}
      </div>
      {message.role === 'user' && user && (
        <Avatar>
          <AvatarImage src={user.picture} />
          <AvatarFallback>
            {user.name?.charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
      )}
    </Card>
  );
}