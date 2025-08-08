
"use client";

import React from 'react';
import { WebSocketMessage } from '../types';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '../components/ui/collapsible';
import { Button } from '../components/ui/button';

interface MessageProps {
  message: WebSocketMessage;
}

const Message: React.FC<MessageProps> = ({ message }) => {
  const [isRawViewOpen, setIsRawViewOpen] = React.useState(false);

  const renderContent = () => {
    switch (message.type) {
      case 'user_message':
        return <p>{message.payload.text}</p>;
      case 'agent_message':
        return <p>{message.payload.text}</p>;
      case 'tool_started':
        return (
          <div>
            <p>Tool started: <strong>{message.payload.tool_name}</strong></p>
          </div>
        );
      case 'tool_completed':
        return (
          <div>
            <p>Tool completed: <strong>{message.payload.tool_name}</strong></p>
            <Collapsible>
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm">
                  Show Result
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <pre className="bg-gray-100 p-2 rounded-md">
                  {JSON.stringify(message.payload.result, null, 2)}
                </pre>
              </CollapsibleContent>
            </Collapsible>
          </div>
        );
      case 'sub_agent_update':
        return (
            <div>
                <p>Sub-agent <strong>{message.payload.sub_agent_name}</strong> is now <strong>{message.payload.state.lifecycle}</strong></p>
            </div>
        )
      default:
        return <p>Unsupported message type: {message.type}</p>;
    }
  };

  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>{message.type}</span>
          <Button variant="ghost" size="sm" onClick={() => setIsRawViewOpen(!isRawViewOpen)}>
            {isRawViewOpen ? 'Hide Raw' : 'Show Raw'}
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {renderContent()}
        {isRawViewOpen && (
          <pre className="bg-gray-100 p-2 rounded-md mt-4">
            {JSON.stringify(message, null, 2)}
          </pre>
        )}
      </CardContent>
    </Card>
  );
};

export default Message;
