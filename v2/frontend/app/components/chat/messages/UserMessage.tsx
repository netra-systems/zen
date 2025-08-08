import React from 'react';
import { UserMessage as UserMessageProps } from '@/app/types';

const UserMessage: React.FC<UserMessageProps> = ({ text, references }) => {
  return (
    <div className="p-4 bg-blue-100 rounded-lg">
      <p>{text}</p>
      {references && references.length > 0 && (
        <div className="mt-2">
          <p className="font-bold">References:</p>
          <ul className="list-disc list-inside">
            {references.map((ref, index) => (
              <li key={index}>{ref}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default UserMessage;
