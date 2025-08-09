import React, { useEffect, useRef } from 'react';
import { Message as MessageType } from '@/types/chat';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { RawJsonView } from './RawJsonView';

interface MessageProps {
  message: MessageType;
}

export const MessageItem: React.FC<MessageProps> = ({ message }) => {
  const { type, content, sub_agent_name, tool_info, raw_data, references } = message;
  const messageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messageRef.current) {
      messageRef.current.classList.add('animate-fade-in');
    }
  }, []);

  const renderContent = () => {
    if (tool_info) {
      return (
        <Collapsible>
          <CollapsibleTrigger className="text-blue-500">View Tool Info</CollapsibleTrigger>
          <CollapsibleContent>
            <RawJsonView data={tool_info} />
          </CollapsibleContent>
        </Collapsible>
      );
    }
    return (
      <>
        <p>{content}</p>
        {type === 'user' && references && references.length > 0 && (
          <div className="mt-2 text-sm text-gray-600">
            <strong>References:</strong>
            <ul>
              {references.map((ref, index) => (
                <li key={index}>{ref}</li>
              ))}
            </ul>
          </div>
        )}
      </>
    );
  };

  return (
    <Card ref={messageRef} className={`mb-4 opacity-0 ${type === 'user' ? 'bg-blue-50' : 'bg-gray-50'}`}>
      <CardHeader>
        <div className="flex items-center">
          <Avatar className="mr-4">
            <AvatarImage src={type === 'user' ? '' : '/bot.png'} />
            <AvatarFallback>{type === 'user' ? 'U' : 'A'}</AvatarFallback>
          </Avatar>
          <CardTitle>{sub_agent_name || type}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        {renderContent()}
        {raw_data && (
          <Collapsible>
            <CollapsibleTrigger className="text-xs text-gray-500">View Raw Data</CollapsibleTrigger>
            <CollapsibleContent>
              <RawJsonView data={raw_data} />
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
};