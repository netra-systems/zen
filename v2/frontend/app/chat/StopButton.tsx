"use client";

import React from 'react';
import { Button } from '../components/ui/button';
import { useAgent } from '../hooks/useAgent';

const StopButton: React.FC = () => {
  const { stopAgent } = useAgent();

  return (
    <Button onClick={stopAgent} variant="destructive">
      Stop
    </Button>
  );
};

export default StopButton;