
import React from 'react';
import { JsonView } from 'react-json-view-lite';

import { JsonTreeViewProps } from '@/app/types/index';

const JsonTreeView: React.FC<JsonTreeViewProps> = ({ data }) => {
    return (
        <div className="text-sm">
            <JsonView data={data} />
        </div>
    );
};

export default JsonTreeView;
