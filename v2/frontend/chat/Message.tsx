import React from 'react';
import { Message as MessageType } from '@/types/chat';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { JsonViewer } from './JsonViewer';

interface MessageProps {
  message: MessageType;
}

export const Message: React.FC<MessageProps> = ({ message }) => {
  const { type, content, sub_agent_name, tool_info, raw_data } = message;

  const renderContent = () => {
    if (tool_info) {
      return (
        <Collapsible>
          <CollapsibleTrigger className="text-blue-500">View Tool Info</CollapsibleTrigger>
          <CollapsibleContent>
            <JsonViewer data={tool_info} />
          </CollapsibleContent>
        </Collapsible>
      );
    }
    return <p>{content}</p>;
  };

  return (
    <Card className={`mb-4 ${type === 'user' ? 'bg-blue-50' : 'bg-gray-50'}`}>
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
              <JsonViewer data={raw_data} />
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
};