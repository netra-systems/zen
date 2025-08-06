import React from 'react';

interface JsonTreeViewProps {
    data: unknown;
}

const JsonTreeView: React.FC<JsonTreeViewProps> = ({ data }) => {
    if (typeof data !== 'object' || data === null) {
        return <div>{String(data)}</div>;
    }

    return (
        <ul className="pl-4">
            {Object.entries(data).map(([key, value]) => (
                <li key={key}>
                    <strong>{key}: </strong>
                    <JsonTreeView data={value} />
                </li>
            ))}
        </ul>
    );
};

export { JsonTreeView };