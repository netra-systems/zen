
import React from 'react';

interface SystemMessageProps {
  message: string;
}

const SystemMessage: React.FC<SystemMessageProps> = ({ message }) => {
  return (
    <div className="text-center text-gray-500 text-sm mb-4">
      <p>{message}</p>
    </div>
  );
};

export default SystemMessage;
