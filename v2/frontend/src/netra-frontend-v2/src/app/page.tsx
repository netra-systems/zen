"use client";

import React from 'react';
import { Navbar, NavbarBrand, NavbarContent, NavbarItem, Link, Button, Card, CardBody, CardHeader, CardFooter } from "@nextui-org/react";
import { Zap, Settings, RefreshCw, BarChart2, DollarSign, HelpCircle, LogOut } from 'lucide-react';

// --- Main App Component ---
export default function App() {
  return (
    <div className="flex flex-col h-screen">
      <Header />
      <main className="flex-grow container mx-auto p-6">
        <Dashboard />
      </main>
      <Footer />
    </div>
  );
}

// --- Layout Components ---
const Header = () => (
  <Navbar>
    <NavbarBrand>
      <p className="font-bold text-inherit">Netra</p>
    </NavbarBrand>
    <NavbarContent justify="end">
      <NavbarItem>
        <Button as={Link} color="primary" href="#" variant="flat">
          Logout
        </Button>
      </NavbarItem>
    </NavbarContent>
  </Navbar>
);

const Footer = () => (
  <footer className="text-center p-4 text-sm text-gray-500">
    <p>&copy; {new Date().getFullYear()} Netra, Inc. All rights reserved.</p>
  </footer>
);

// --- Dashboard Component ---
const Dashboard = () => (
  <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
    <div className="lg:col-span-1">
      <ControlPanel />
    </div>
    <div className="lg:col-span-2">
      <AnalysisResultView />
    </div>
  </div>
);

// --- Control Panel Component ---
const ControlPanel = () => (
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

// --- Analysis Result Component ---
const AnalysisResultView = () => (
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