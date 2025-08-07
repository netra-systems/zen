'use client';

import { Message } from '../types/chat';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { JsonView, allExpanded, defaultStyles } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { MessageContent } from './chat/MessageContent';

interface MessageCardProps {
  message: Message;
  user: {
    name: string;
    picture: string;
  } | undefined
}

export function MessageCard({ message, user }: MessageCardProps) {
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
          <MessageContent message={message} />
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