'use client';

import { useState } from 'react';
import { Message, ToolCall, ToolOutput, StateUpdate, ArtifactMessage } from '../types/chat';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { JsonView, allExpanded, defaultStyles } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';

interface MessageCardProps {
  message: Message;
  user: {
    name: string;
    picture: string;
  } | undefined
}

const getToolName = (message: ArtifactMessage): string | null => {
  if (message.tool_calls && message.tool_calls.length > 0) {
    const toolNames = message.tool_calls.map(tc => tc.name).filter(name => name !== 'update_state');
    if (toolNames.length > 0) return toolNames.join(', ');
  }
  if (message.name.startsWith('on_tool')) {
    return message.name;
  }
  return null;
};

const getAIMessage = (message: Message): string | null => {
  if (message.type === 'text') {
    return message.content;
  }
  if (message.type === 'artifact' && message.content) {
    return message.content;
  }
  return null;
};

const getTodoList = (message: Message): StateUpdate | null => {
  if (message.type === 'artifact' && message.state_updates) {
    return message.state_updates;
  }
  return null;
};

const getToolErrors = (message: Message): ToolOutput[] | null => {
  if (message.type !== 'artifact' || !message.tool_outputs) return null;
  return message.tool_outputs.filter(to => to.is_error);
};

export function MessageCard({ message, user }: MessageCardProps) {
  const [showRaw, setShowRaw] = useState(false);

  const toggleRaw = () => setShowRaw(!showRaw);

  if (message.type === 'thinking') {
    return (
      <div className="flex items-start gap-4" data-testid="thinking-indicator">
        <Avatar>
          <AvatarImage src="/agent-avatar.png" />
          <AvatarFallback>A</AvatarFallback>
        </Avatar>
        <div className="rounded-lg p-3 max-w-[75%] bg-muted">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse"></div>
            <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse delay-75"></div>
            <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse delay-150"></div>
          </div>
        </div>
      </div>
    );
  }

  const toolName = message.type === 'artifact' ? getToolName(message) : null;
  const aiMessage = getAIMessage(message);
  const todoList = getTodoList(message);
  const toolErrors = getToolErrors(message);

  return (
    <Card className={`flex items-start gap-4 p-4 ${message.role === 'user' ? 'justify-end' : ''}`}>
      {message.role === 'agent' && (
        <Avatar>
          <AvatarImage src="/agent-avatar.png" />
          <AvatarFallback>A</AvatarFallback>
        </Avatar>
      )}
      <div className={`rounded-lg p-3 max-w-[75%] ${message.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
        <>
          {toolName && <p className="font-bold text-sm">Tool: {toolName}</p>}
          {aiMessage && <p className="text-sm">{aiMessage}</p>}
          {todoList && (todoList.todo_list.length > 0 || todoList.completed_steps.length > 0) && (
            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="item-1">
                <AccordionTrigger>TODO List</AccordionTrigger>
                <AccordionContent>
                  {todoList.todo_list.length > 0 && (
                    <ul className="list-disc pl-5">
                      {todoList.todo_list.map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  )}
                  {todoList.completed_steps.length > 0 && (
                    <>
                      <h4 className="font-bold mt-2">Completed Steps</h4>
                      <ul className="list-disc pl-5">
                        {todoList.completed_steps.map((item, index) => (
                          <li key={index} className="line-through">{item}</li>
                        ))}
                      </ul>
                    </>
                  )}
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          )}
          {toolErrors && toolErrors.length > 0 && (
            <div className="mt-2">
              <p className="font-bold text-red-500">Errors:</p>
              <ul className="list-disc pl-5 text-red-500">
                {toolErrors.map((error, index) => (
                  <li key={index}>{error.content}</li>
                ))}
              </ul>
            </div>
          )}
        </>
        {message.role === 'agent' && (
          <div>
            <button onClick={toggleRaw} className="text-blue-500 hover:underline mt-2">
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
