
import React from 'react';
import { JsonView } from 'react-json-view-lite';

interface JsonTreeViewProps {
    data: any;
}

const JsonTreeView: React.FC<JsonTreeViewProps> = ({ data }) => {
    return (
        <div className="text-sm">
            <JsonView data={data} />
        </div>
    );
};

export default JsonTreeView;
