"use client";

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { HelpCircle } from 'lucide-react';

export const AnalysisResultView = () => (
  <Card className="h-full flex flex-col">
    <CardHeader>
      <CardTitle>Analysis Results</CardTitle>
    </CardHeader>
    <CardContent className="flex-1 flex flex-col items-center justify-center text-center">
      <div className="text-muted-foreground">
        <HelpCircle className="w-16 h-16 mx-auto text-muted-foreground/40" />
        <p className="mt-4">No analysis run yet. Start a new analysis to see results.</p>
      </div>
    </CardContent>
  </Card>
);
