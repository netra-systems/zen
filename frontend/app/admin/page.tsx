'use client';

import { NextPage } from 'next';
import { useState } from 'react';
import { authService } from '@/auth';
import { AuthGuard } from '@/components/AuthGuard';
import WebSocketAuthMonitor from '@/components/admin/WebSocketAuthMonitor';
import { Shield, Settings, Users, Database, Activity, FileText, LucideIcon, Wifi } from 'lucide-react';

interface AdminStat {
  label: string;
  value: string;
  icon: LucideIcon;
  color: string;
}

interface AdminSection {
  title: string;
  description: string;
  icon: LucideIcon;
  color: string;
}
import { motion } from 'framer-motion';

const AdminPage: NextPage = () => {
  authService.useAuth(); // Authentication check only
  const [activeTab, setActiveTab] = useState<string>('dashboard');

  return (
    <AuthGuard>
      <div className="container mx-auto p-6 space-y-6">
        <AdminHeader />

        {/* Navigation Tabs */}
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'dashboard'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Shield className="w-4 h-4" />
                <span>Dashboard</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('websocket-auth')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'websocket-auth'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <Wifi className="w-4 h-4" />
                <span>WebSocket Auth Monitor</span>
              </div>
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === 'dashboard' && (
          <>
            <AdminQuickStats />
            <AdminDashboard />
          </>
        )}

        {activeTab === 'websocket-auth' && (
          <WebSocketAuthMonitor />
        )}
      </div>
    </AuthGuard>
  );
};


const AdminHeader = () => {
  return (
    <div className="flex items-center space-x-4 mb-8">
      <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-red-600 rounded-full flex items-center justify-center">
        <Shield className="w-6 h-6 text-white" />
      </div>
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Admin Panel</h1>
        <p className="text-gray-600">System administration and management</p>
      </div>
    </div>
  );
};

const AdminQuickStats = () => {
  const stats = [
    { label: 'Active Users', value: '42', icon: Users, color: 'bg-blue-500' },
    { label: 'System Health', value: '98%', icon: Activity, color: 'bg-green-500' },
    { label: 'Storage Used', value: '67%', icon: Database, color: 'bg-yellow-500' },
    { label: 'Active Sessions', value: '18', icon: FileText, color: 'bg-purple-500' }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat, index) => createStatCard(stat, index))}
    </div>
  );
};

const createStatCard = (stat: AdminStat, index: number) => {
  const Icon = stat.icon;
  return (
    <motion.div
      key={stat.label}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className="bg-white rounded-lg shadow-sm border border-gray-100 p-6"
    >
      <div className="flex items-center space-x-4">
        <div className={`w-12 h-12 ${stat.color} rounded-lg flex items-center justify-center`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div>
          <p className="text-sm text-gray-600">{stat.label}</p>
          <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
        </div>
      </div>
    </motion.div>
  );
};

const AdminDashboard = () => {
  const adminSections = [
    {
      title: 'System Settings',
      description: 'Configure system-wide settings and preferences',
      icon: Settings,
      color: 'bg-blue-500',
      href: '#'
    },
    {
      title: 'User Management',
      description: 'Manage user accounts, permissions, and access',
      icon: Users,
      color: 'bg-green-500',
      href: '#'
    },
    {
      title: 'Database Admin',
      description: 'Monitor and manage database operations',
      icon: Database,
      color: 'bg-purple-500',
      href: '#'
    },
    {
      title: 'System Monitoring',
      description: 'View system health, logs, and performance metrics',
      icon: Activity,
      color: 'bg-orange-500',
      href: '#'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {adminSections.map((section, index) => createAdminSectionCard(section, index))}
    </div>
  );
};

const createAdminSectionCard = (section: AdminSection, index: number) => {
  const Icon = section.icon;
  return (
    <motion.div
      key={section.title}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      className="bg-white rounded-lg shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow cursor-pointer"
    >
      <div className="flex items-start space-x-4">
        <div className={`w-12 h-12 ${section.color} rounded-lg flex items-center justify-center`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">{section.title}</h3>
          <p className="text-sm text-gray-600">{section.description}</p>
        </div>
      </div>
    </motion.div>
  );
};

export default AdminPage;