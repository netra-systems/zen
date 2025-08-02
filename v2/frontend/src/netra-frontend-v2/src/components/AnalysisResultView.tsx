"use client";

import React from 'react';
import { Card, CardBody, CardHeader } from "@nextui-org/react";
import { HelpCircle } from 'lucide-react';

export const AnalysisResultView = () => (
  <Card className="h-full">
    <CardHeader>
      <h2 className="text-xl font-semibold">Analysis Results</h2>
    </CardHeader>
    <CardBody>
      {/* Placeholder for analysis results */}
      <div className="text-center text-gray-500">
        <HelpCircle className="w-16 h-16 mx-auto" />
        <p className="mt-4">No analysis run yet. Start a new analysis to see results.</p>
      </div>
    </CardBody>
  </Card>
);
