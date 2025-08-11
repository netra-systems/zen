import React from 'react';
import { JsonView, allExpanded, defaultStyles } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';

interface JsonViewerProps {
  data: unknown;
}

export const RawJsonView: React.FC<JsonViewerProps> = ({ data }) => {
  return (
    <div className="p-4 bg-gray-100 rounded-lg">
      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
      <JsonView data={data as object | any[]} shouldExpandNode={allExpanded} style={defaultStyles} />
    </div>
  );
};