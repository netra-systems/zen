'use client';

import React, { useState } from 'react';

interface JsonTreeViewProps {
  data: any;
}

export const JsonTreeView: React.FC<JsonTreeViewProps> = ({ data }) => {
  const [isOpen, setIsOpen] = useState(false);

  const toggleOpen = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div>
      <button onClick={toggleOpen} className="text-sm text-gray-500">
        {isOpen ? 'Hide JSON' : 'Show JSON'}
      </button>
      {isOpen && (
        <pre className="bg-gray-100 p-2 rounded mt-2 text-xs">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
};