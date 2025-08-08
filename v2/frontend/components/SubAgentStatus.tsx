'use client';

import React from 'react';

interface SubAgentStatusProps {
  name: string;
  status: string;
}

export const SubAgentStatus = ({ name, status }: SubAgentStatusProps) => {
  return (
    <div className="text-sm text-muted-foreground">
      <strong>{name}:</strong> {status}
    </div>
  );
};
