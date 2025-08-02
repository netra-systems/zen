"use client";

import React from 'react';
import { Button, Card, CardBody, CardHeader } from "@nextui-org/react";
import { Zap, Settings, RefreshCw, BarChart2, HelpCircle } from 'lucide-react';

export const ControlPanel = () => (
  <Card>
    <CardHeader>
      <h2 className="text-xl font-semibold">Control Panel</h2>
    </CardHeader>
    <CardBody>
      <p className="text-sm text-gray-500">Start a new analysis or manage settings.</p>
      <div className="mt-6 space-y-4">
        <Button color="primary" startContent={<Zap />}>Start New Analysis</Button>
        <Button variant="bordered" startContent={<Settings />}>Admin Panel</Button>
        <Button variant="bordered" startContent={<RefreshCw />}>Generate Synthetic Data</Button>
        <Button variant="bordered" startContent={<BarChart2 />}>Ingest Data</Button>
        <Button variant="bordered" startContent={<HelpCircle />}>Demo Agent</Button>
        <Button variant="bordered" startContent={<Settings />}>Manage Supply Catalog</Button>
      </div>
    </CardBody>
  </Card>
);
