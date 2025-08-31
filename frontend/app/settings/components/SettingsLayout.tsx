/**
 * Settings Layout Component
 * Main layout for settings page with navigation tabs
 */

'use client';

import React, { useState } from 'react';
import ProfileSection from './ProfileSection';
import SecuritySection from './SecuritySection';
import ApiKeysSection from './ApiKeysSection';
import NotificationsSection from './NotificationsSection';
import PrivacySection from './PrivacySection';

export default function SettingsLayout() {
  const [activeSection, setActiveSection] = useState('profile');

  const sections = [
    { id: 'profile', label: 'Profile', component: ProfileSection },
    { id: 'security', label: 'Security', component: SecuritySection },
    { id: 'api-keys', label: 'API Keys', component: ApiKeysSection },
    { id: 'notifications', label: 'Notifications', component: NotificationsSection },
    { id: 'privacy', label: 'Privacy', component: PrivacySection }
  ];

  const ActiveComponent = sections.find(s => s.id === activeSection)?.component || ProfileSection;

  return (
    <div className="settings-container" style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Settings Navigation */}
      <div className="settings-sidebar" style={{ width: '250px', borderRight: '1px solid #e5e7eb', padding: '20px' }}>
        <h2 style={{ marginBottom: '20px', fontSize: '1.5rem', fontWeight: '600' }}>Settings</h2>
        <nav>
          {sections.map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`settings-nav-item ${activeSection === section.id ? 'active' : ''}`}
              style={{
                display: 'block',
                width: '100%',
                padding: '12px 16px',
                marginBottom: '8px',
                border: 'none',
                borderRadius: '8px',
                textAlign: 'left',
                backgroundColor: activeSection === section.id ? '#3b82f6' : 'transparent',
                color: activeSection === section.id ? 'white' : '#374151',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              {section.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Settings Content */}
      <div className="settings-content" style={{ flex: 1, padding: '40px' }}>
        <ActiveComponent />
      </div>
    </div>
  );
}