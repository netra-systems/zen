'use client';

import React, { useState } from 'react';
import { MessageToUser } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ReactJson } from '@microlink/react-json-view';

interface MessageProps {
  message: MessageToUser;
}

export const Message = ({ message }: MessageProps) => {
  const [isRawVisible, setRawVisible] = useState(false);

  const toggleRawView = () => {
    setRawVisible(!isRawVisible);
  };

  return (
    <Card
      className={message.sender === 'user' ? 'self-end bg-primary text-primary-foreground' : 'self-start bg-muted'}
    >
      <CardHeader>
        <CardTitle className="text-sm font-normal">{message.content}</CardTitle>
      </CardHeader>
      {message.sender === 'agent' && message.metadata && (
        <CardContent>
          <Button onClick={toggleRawView} variant="ghost" size="sm">
            {isRawVisible ? 'Hide' : 'Show'} Raw
          </Button>
          {isRawVisible && <ReactJson src={message.metadata} />}
        </CardContent>
      )}
    </Card>
  );
};