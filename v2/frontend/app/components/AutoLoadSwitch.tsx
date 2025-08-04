'use client';

import React from 'react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';

interface AutoLoadSwitchProps {
  isAutoLoad: boolean;
  onAutoLoadChange: (value: boolean) => void;
}

export function AutoLoadSwitch({ isAutoLoad, onAutoLoadChange }: AutoLoadSwitchProps) {
  return (
    <div className="flex items-center space-x-2">
      <Switch id="auto-load-example" checked={isAutoLoad} onCheckedChange={onAutoLoadChange} />
      <Label htmlFor="auto-load-example">Auto-load example</Label>
    </div>
  );
}