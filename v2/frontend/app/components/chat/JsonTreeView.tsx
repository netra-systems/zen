'use client';

import React from 'react';
import JsonView from '@uiw/react-json-view';
import { darkTheme } from '@uiw/react-json-view/dark';

interface JsonTreeViewProps {
  data: object;
}

const JsonTreeView: React.FC<JsonTreeViewProps> = ({ data }) => {
  return (
    <JsonView
      value={data}
      style={darkTheme}
      displayDataTypes={false}
      enableClipboard={true}
      iconStyle="square"
    />
  );
};

export default JsonTreeView;