import React from 'react';
import { Message as MessageType } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { JsonView, allExpanded } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';

interface MessageProps {
  message: MessageType;
}

const Message: React.FC<MessageProps> = ({ message }) => {
  const getCardBorderColor = () => {
    switch (message.type) {
      case 'user':
        return 'border-blue-500';
      case 'agent':
        return 'border-green-500';
      case 'system':
        return 'border-gray-500';
      case 'error':
        return 'border-red-500';
      case 'tool':
        return 'border-yellow-500';
      default:
        return 'border-gray-200';
    }
  };

  return (
    <Card className={`mb-4 ${getCardBorderColor()}`}>
      <CardHeader>
        <CardTitle className="flex justify-between">
          <span>{message.sub_agent_name || message.type}</span>
          <span className="text-xs text-gray-500">{new Date(message.created_at).toLocaleTimeString()}</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p>{message.content}</p>
        {message.tool_info && (
          <div className="mt-2">
            <h4 className="font-semibold">Tool Info:</h4>
            <JsonView data={message.tool_info} shouldExpandNode={allExpanded} style={{}} />
          </div>
        )}
        {message.raw_data && (
          <div className="mt-2">
            <details>
              <summary className="cursor-pointer">Raw Data</summary>
              <JsonView data={message.raw_data} shouldExpandNode={allExpanded} style={{}} />
            </details>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default Message;
