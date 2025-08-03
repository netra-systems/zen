
import React from 'react';

const Spinner = ({ className = '' }: { className?: string }) => (
    <div className={`flex justify-center items-center h-full ${className}`}>
        <div className="w-16 h-16 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
    </div>
);

export default Spinner;
