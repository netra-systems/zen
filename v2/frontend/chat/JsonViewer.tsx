
"use client";

import React from 'react';
import { JsonView, allExpanded } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';

interface JsonViewerProps {
  data: any;
}

const JsonViewer: React.FC<JsonViewerProps> = ({ data }) => {
  return (
    <div className="bg-gray-100 p-2 rounded">
        <JsonView data={data} shouldExpandNode={allExpanded} style={{}} />
    </div>
  );
};

export default JsonViewer;
