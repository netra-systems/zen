import React from 'react';
import { JsonView, allExpanded, defaultStyles } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';

interface JsonViewerProps {
  data: any;
}

export const JsonViewer: React.FC<JsonViewerProps> = ({ data }) => {
  return (
    <div className="p-4 bg-gray-100 rounded-lg">
      <JsonView data={data} shouldExpandNode={allExpanded} style={defaultStyles} />
    </div>
  );
};