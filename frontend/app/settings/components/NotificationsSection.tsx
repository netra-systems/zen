/**
 * Notifications Section Component
 * Notification settings and preferences
 */

'use client';

import React, { useState } from 'react';

interface NotificationSettings {
  email_notifications: {
    optimization_complete: boolean;
    weekly_reports: boolean;
    system_updates: boolean;
    marketing: boolean;
  };
  in_app_notifications: {
    agent_updates: boolean;
    mentions: boolean;
    thread_replies: boolean;
  };
  push_notifications: {
    enabled: boolean;
    critical_only: boolean;
  };
}

export default function NotificationsSection() {
  const [settings, setSettings] = useState<NotificationSettings>({
    email_notifications: {
      optimization_complete: true,
      weekly_reports: true,
      system_updates: false,
      marketing: false
    },
    in_app_notifications: {
      agent_updates: true,
      mentions: true,
      thread_replies: true
    },
    push_notifications: {
      enabled: false,
      critical_only: false
    }
  });

  const [message, setMessage] = useState('');

  const handleToggle = (category: keyof NotificationSettings, setting: string) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [setting]: !prev[category][setting as keyof typeof prev[typeof category]]
      }
    }));
  };

  const handleSave = async () => {
    // Mock save
    setMessage('Notification settings updated successfully');
    setTimeout(() => setMessage(''), 3000);
  };

  return (
    <div className="notifications-section">
      <h3 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '24px' }}>
        Notification Settings
      </h3>

      {message && (
        <div 
          style={{ 
            padding: '12px', 
            marginBottom: '20px', 
            borderRadius: '8px',
            backgroundColor: '#d4edda',
            color: '#155724',
            border: '1px solid #c3e6cb'
          }}
        >
          {message}
        </div>
      )}

      <div style={{ display: 'grid', gap: '32px' }}>
        {/* Email Notifications */}
        <div>
          <h4 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '16px' }}>
            Email Notifications
          </h4>
          <div style={{ display: 'grid', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: '500' }}>Optimization Complete</div>
                <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  Get notified when your AI optimization tasks are finished
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={settings.email_notifications.optimization_complete}
                  onChange={() => handleToggle('email_notifications', 'optimization_complete')}
                  style={{ marginRight: '8px' }}
                />
                <span style={{ fontSize: '0.875rem' }}>Enable</span>
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: '500' }}>Weekly Reports</div>
                <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  Receive weekly summaries of your usage and optimizations
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={settings.email_notifications.weekly_reports}
                  onChange={() => handleToggle('email_notifications', 'weekly_reports')}
                  style={{ marginRight: '8px' }}
                />
                <span style={{ fontSize: '0.875rem' }}>Enable</span>
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: '500' }}>System Updates</div>
                <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  Important updates about Netra system changes and maintenance
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={settings.email_notifications.system_updates}
                  onChange={() => handleToggle('email_notifications', 'system_updates')}
                  style={{ marginRight: '8px' }}
                />
                <span style={{ fontSize: '0.875rem' }}>Enable</span>
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: '500' }}>Marketing & Features</div>
                <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  Updates about new features, tips, and Netra news
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={settings.email_notifications.marketing}
                  onChange={() => handleToggle('email_notifications', 'marketing')}
                  style={{ marginRight: '8px' }}
                />
                <span style={{ fontSize: '0.875rem' }}>Enable</span>
              </label>
            </div>
          </div>
        </div>

        {/* In-App Notifications */}
        <div>
          <h4 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '16px' }}>
            In-App Notifications
          </h4>
          <div style={{ display: 'grid', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: '500' }}>Agent Updates</div>
                <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  Real-time updates when agents are working on your tasks
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={settings.in_app_notifications.agent_updates}
                  onChange={() => handleToggle('in_app_notifications', 'agent_updates')}
                  style={{ marginRight: '8px' }}
                />
                <span style={{ fontSize: '0.875rem' }}>Enable</span>
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: '500' }}>Mentions</div>
                <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  When you're mentioned in comments or shared workspaces
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={settings.in_app_notifications.mentions}
                  onChange={() => handleToggle('in_app_notifications', 'mentions')}
                  style={{ marginRight: '8px' }}
                />
                <span style={{ fontSize: '0.875rem' }}>Enable</span>
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: '500' }}>Thread Replies</div>
                <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  New replies in conversations you're participating in
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={settings.in_app_notifications.thread_replies}
                  onChange={() => handleToggle('in_app_notifications', 'thread_replies')}
                  style={{ marginRight: '8px' }}
                />
                <span style={{ fontSize: '0.875rem' }}>Enable</span>
              </label>
            </div>
          </div>
        </div>

        {/* Push Notifications */}
        <div>
          <h4 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '16px' }}>
            Push Notifications
          </h4>
          <div style={{ display: 'grid', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: '500' }}>Enable Push Notifications</div>
                <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  Receive browser notifications when the app is not active
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={settings.push_notifications.enabled}
                  onChange={() => handleToggle('push_notifications', 'enabled')}
                  style={{ marginRight: '8px' }}
                />
                <span style={{ fontSize: '0.875rem' }}>Enable</span>
              </label>
            </div>

            {settings.push_notifications.enabled && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginLeft: '20px' }}>
                <div>
                  <div style={{ fontWeight: '500' }}>Critical Only</div>
                  <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                    Only show push notifications for critical updates and errors
                  </div>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={settings.push_notifications.critical_only}
                    onChange={() => handleToggle('push_notifications', 'critical_only')}
                    style={{ marginRight: '8px' }}
                  />
                  <span style={{ fontSize: '0.875rem' }}>Enable</span>
                </label>
              </div>
            )}
          </div>
        </div>
      </div>

      <div style={{ marginTop: '32px' }}>
        <button
          onClick={handleSave}
          style={{
            padding: '12px 24px',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: '500'
          }}
        >
          Save Notification Settings
        </button>
      </div>
    </div>
  );
}