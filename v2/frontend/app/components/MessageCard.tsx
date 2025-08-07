'use client';

import { useState } from 'react';
import { Message } from '../types/chat';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { JsonView, allExpanded, defaultStyles } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { AlertCircle } from 'lucide-react';
import { TodoListView } from './chat/TodoListView';

interface MessageCardProps {
  message: Message;
  user: {
    name: string;
    picture: string;
  } | undefined
}

export function MessageCard({ message, user }: MessageCardProps) {
  const [showRaw, setShowRaw] = useState(false);

  const toggleRaw = () => setShowRaw(!showRaw);

  const renderContent = () => {
    switch (message.type) {
      case 'text':
        return <p className="text-sm">{message.content}</p>;
      case 'thinking':
        return (
          <div data-testid="thinking-indicator" className="flex items-center space-x-2">
            <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse"></div>
            <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse delay-75"></div>
            <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse delay-150"></div>
          </div>
        );
      case 'tool_start':
        return <p className="text-sm">Tool: {message.tool}</p>;
      case 'state_update':
        return message.state && (message.state.todo_list.length > 0 || message.state.completed_steps.length > 0) ? (
          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="item-1">
              <AccordionTrigger>
                <span className="font-medium">TODO List</span>
              </AccordionTrigger>
              <AccordionContent>
                <TodoListView todoList={message.state} />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        ) : null;
      case 'tool_end':
        const toolErrors = message.toolOutput?.is_error ? [message.toolOutput] : [];
        return toolErrors && toolErrors.length > 0 ? (
          <div className="mt-2">
            <p className="font-bold text-red-500 flex items-center"><AlertCircle className="h-4 w-4 mr-1" /> Errors:</p>
            <ul className="list-disc pl-5 text-red-500">
              {toolErrors.map((error, index) => (
                <li key={index}>{error.content}</li>
              ))}
            </ul>
          </div>
        ) : null;
      default:
        return null;
    }
  };

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
          {renderContent()}
        </div>
        {message.role === 'assistant' && (
          <div className="mt-2">
            <button onClick={toggleRaw} className="text-blue-500 hover:underline text-xs">
              {showRaw ? 'Hide Raw Message' : 'Show Raw Message'}
            </button>
            {showRaw && (
              <div className="mt-2">
                <JsonView data={message} shouldExpandNode={allExpanded} style={defaultStyles} />
              </div>
            )}
          </div>
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
