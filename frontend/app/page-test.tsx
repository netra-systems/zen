'use client';

import { NextPage } from 'next';

const TestHomePage: NextPage = () => {
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Netra Apex</h1>
        <p className="text-lg text-gray-600">Test page without auth dependencies</p>
      </div>
    </div>
  );
};

export default TestHomePage;