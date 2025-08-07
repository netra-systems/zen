'use client';

import { useState } from 'react';

interface MessageFilterProps {
  onFilterChange: (filter: string) => void;
}

export function MessageFilter({ onFilterChange }: MessageFilterProps) {
  const [filter, setFilter] = useState('all');

  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newFilter = e.target.value;
    setFilter(newFilter);
    onFilterChange(newFilter);
  };

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="message-filter">Filter by:</label>
      <select
        id="message-filter"
        value={filter}
        onChange={handleFilterChange}
        className="p-2 border rounded"
      >
        <option value="all">All</option>
        <option value="user">User</option>
        <option value="assistant">Agent</option>
      </select>
    </div>
  );
}
