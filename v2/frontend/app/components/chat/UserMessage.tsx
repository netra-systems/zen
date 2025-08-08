
import React from 'react';

interface UserMessageProps {
  message: string;
}

const UserMessage: React.FC<UserMessageProps> = ({ message }) => {
  return (
    <div className="flex justify-end mb-4">
      <div className="bg-blue-500 text-white rounded-lg p-3">
        <p>{message}</p>
      </div>
    </div>
  );
};

export default UserMessage;
