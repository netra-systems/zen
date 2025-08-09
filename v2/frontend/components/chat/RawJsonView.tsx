import React from 'react';

interface RawJsonViewProps {
  json: unknown;
}

export const RawJsonView = ({ json }: RawJsonViewProps) => {
  return (
    <pre className="p-2 my-2 text-xs bg-gray-800 text-white rounded overflow-x-auto">
      {JSON.stringify(json, null, 2)}
    </pre>
  );
};