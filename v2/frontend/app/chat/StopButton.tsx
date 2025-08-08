
"use client";

import React from 'react';

const StopButton: React.FC = () => {
  const handleClick = () => {
    // Handle stop logic here
    console.log('Stop button clicked');
  };

  return (
    <button
      onClick={handleClick}
      className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded"
    >
      Stop
    </button>
  );
};

export default StopButton;
