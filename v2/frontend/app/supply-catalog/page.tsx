'use client';

import React from 'react';

const SupplyCatalogPage = () => {
  return (
    <div className="flex flex-col h-full">
      <header className="bg-background border-b px-4 py-2 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Supply Catalog</h1>
      </header>
      <main className="flex-1 p-4 overflow-auto">
        <p>Supply Catalog content goes here.</p>
      </main>
    </div>
  );
};

export default SupplyCatalogPage;
