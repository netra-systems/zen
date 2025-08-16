'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Shield } from 'lucide-react';
import type { PermissionRule } from './types';

const permissionData: PermissionRule[] = [
  { userGroup: 'ML Team', role: 'Admin', accessLevel: 'Full Access' },
  { userGroup: 'Data Scientists', role: 'Editor', accessLevel: 'Read/Write' },
  { userGroup: 'Analytics Team', role: 'Viewer', accessLevel: 'Read Only' },
];

const AccessControls: React.FC = () => (
  <div className="grid grid-cols-2 gap-4">
    <div>
      <Label>Default Access Level</Label>
      <Select defaultValue="restricted">
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="public">Public</SelectItem>
          <SelectItem value="restricted">Restricted</SelectItem>
          <SelectItem value="private">Private</SelectItem>
        </SelectContent>
      </Select>
    </div>
    <div>
      <Label>Sharing Policy</Label>
      <Select defaultValue="team">
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="none">No Sharing</SelectItem>
          <SelectItem value="team">Team Only</SelectItem>
          <SelectItem value="org">Organization</SelectItem>
          <SelectItem value="external">Allow External</SelectItem>
        </SelectContent>
      </Select>
    </div>
  </div>
);

const PermissionsTable: React.FC<{ permissions: PermissionRule[] }> = ({ permissions }) => (
  <div className="border rounded-lg">
    <table className="w-full">
      <thead>
        <tr className="border-b">
          <th className="text-left p-3">User/Group</th>
          <th className="text-left p-3">Role</th>
          <th className="text-left p-3">Access Level</th>
          <th className="text-left p-3">Actions</th>
        </tr>
      </thead>
      <tbody>
        {permissions.map((permission, index) => (
          <tr key={index} className={index < permissions.length - 1 ? 'border-b' : ''}>
            <td className="p-3">{permission.userGroup}</td>
            <td className="p-3">{permission.role}</td>
            <td className="p-3">{permission.accessLevel}</td>
            <td className="p-3">
              <Button size="sm" variant="outline">Edit</Button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

export const PermissionsTab = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Access Control</CardTitle>
        <CardDescription>Manage who can access your corpus data</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <AccessControls />
          <PermissionsTable permissions={permissionData} />
          <Button>
            <Shield className="mr-2 h-4 w-4" />
            Add Permission Rule
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};