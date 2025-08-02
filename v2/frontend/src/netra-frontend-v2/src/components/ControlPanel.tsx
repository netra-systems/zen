"use client";

import React from 'react';
import { Button, Card, CardBody, CardHeader } from "@nextui-org/react";
import { Zap, Settings, RefreshCw, BarChart2, HelpCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';

export const ControlPanel = () => {
  const router = useRouter();

  return (
    <Card>
      <CardHeader>
        <h2 className="text-xl font-semibold">Control Panel</h2>
      </CardHeader>
      <CardBody>
        <p className="text-sm text-gray-500">Start a new analysis or manage settings.</p>
        <div className="mt-6 space-y-4">
          <Button color="primary" startContent={<Zap />} fullWidth onPress={() => router.push('/analysis')}>Start New Analysis</Button>
          <Button variant="bordered" startContent={<Settings />} fullWidth onPress={() => router.push('/admin')}>Admin Panel</Button>
          <Button variant="bordered" startContent={<RefreshCw />} fullWidth onPress={() => router.push('/generation')}>Generate Synthetic Data</Button>
          <Button variant="bordered" startContent={<BarChart2 />} fullWidth onPress={() => router.push('/ingestion')}>Ingest Data</Button>
          <Button variant="bordered" startContent={<HelpCircle />} fullWidth onPress={() => router.push('/demo')}>Demo Agent</Button>
          <Button variant="bordered" startContent={<Settings />} fullWidth onPress={() => router.push('/supply-catalog')}>Manage Supply Catalog</Button>
        </div>
      </CardBody>
    </Card>
  );
};
