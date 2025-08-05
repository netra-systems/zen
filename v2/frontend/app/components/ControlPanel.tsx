"use client";

import React from 'react';
import { Button } from "./ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "./ui/card";
import { Zap, Settings, RefreshCw, BarChart2, HelpCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';

export const ControlPanel = () => {
  const router = useRouter();

  const buttons = [
    
    { 
      text: 'Generate Admin Corpus', 
      icon: <Settings className="mr-2 h-4 w-4" />, 
      onClick: () => router.push('/admin'),
      variant: 'outline' as const
    },
    { 
      text: 'Create & Ingest Synthetic Data', 
      icon: <RefreshCw className="mr-2 h-4 w-4" />, 
      onClick: () => router.push('/generation'),
      variant: 'outline' as const
    },
    { 
      text: 'Apex Optimizer Agent', 
      icon: <Zap className="mr-2 h-4 w-4" />, 
      onClick: () => router.push('/apex-optimizer-agent'),
      variant: 'outline' as const
    },
    { 
      text: 'Manage Supply Catalog', 
      icon: <Settings className="mr-2 h-4 w-4" />, 
      onClick: () => router.push('/supply-catalog'),
      variant: 'outline' as const
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Control Panel</CardTitle>
        <CardDescription>Start a new analysis or manage settings.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {buttons.map((button, index) => (
          <Button 
            key={index} 
            variant={button.variant} 
            className="w-full justify-start"
            onClick={button.onClick}
          >
            {button.icon}
            {button.text}
          </Button>
        ))}
      </CardContent>
    </Card>
  );
};
