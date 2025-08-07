
import React from 'react';

const Thinking = () => (
    <div className="flex items-center space-x-2">
        <div role="status" className="w-2 h-2 bg-gray-500 rounded-full animate-pulse-fast"></div>
        <div role="status" className="w-2 h-2 bg-gray-500 rounded-full animate-pulse-medium"></div>
        <div role="status" className="w-2 h-2 bg-gray-500 rounded-full animate-pulse-slow"></div>
    </div>
);

export default Thinking;
