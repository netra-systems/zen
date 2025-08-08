import React from 'react';
import { WebSocketError } from '@/app/types';

const ErrorMessage: React.FC<WebSocketError> = ({ message }) => {
  return (
    <div className="p-4 bg-red-100 rounded-lg">
      <p className="text-red-700">{message}</p>
    </div>
  );
};

export default ErrorMessage;
