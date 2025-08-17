import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Shield } from 'lucide-react';

export const CorpusPermissions = () => {
  return (
    <Card>
      <CardHeader>
        <PermissionsHeader />
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <PermissionSettings />
          <PermissionTable />
          <AddPermissionButton />
        </div>
      </CardContent>
    </Card>
  );
};

const PermissionsHeader = () => {
  return (
    <>
      <CardTitle>Access Control</CardTitle>
      <CardDescription>Manage who can access your corpus data</CardDescription>
    </>
  );
};

const PermissionSettings = () => {
  return (
    <div className="grid grid-cols-2 gap-4">
      <AccessLevelSelect />
      <SharingPolicySelect />
    </div>
  );
};

const AccessLevelSelect = () => {
  return (
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
  );
};

const SharingPolicySelect = () => {
  return (
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
  );
};

const PermissionTable = () => {
  return (
    <div className="border rounded-lg">
      <table className="w-full">
        <PermissionTableHeader />
        <PermissionTableBody />
      </table>
    </div>
  );
};

const PermissionTableHeader = () => {
  return (
    <thead>
      <tr className="border-b">
        <th className="text-left p-3">User/Group</th>
        <th className="text-left p-3">Role</th>
        <th className="text-left p-3">Access Level</th>
        <th className="text-left p-3">Actions</th>
      </tr>
    </thead>
  );
};

const PermissionTableBody = () => {
  return (
    <tbody>
      <PermissionRow user="ML Team" role="Admin" access="Full Access" />
      <PermissionRow user="Data Scientists" role="Editor" access="Read/Write" />
      <PermissionRow user="Analytics Team" role="Viewer" access="Read Only" isLast />
    </tbody>
  );
};

const PermissionRow = ({ 
  user, 
  role, 
  access, 
  isLast = false 
}: { 
  user: string; 
  role: string; 
  access: string; 
  isLast?: boolean; 
}) => {
  return (
    <tr className={!isLast ? "border-b" : ""}>
      <td className="p-3">{user}</td>
      <td className="p-3">{role}</td>
      <td className="p-3">{access}</td>
      <td className="p-3">
        <Button size="sm" variant="outline">Edit</Button>
      </td>
    </tr>
  );
};

const AddPermissionButton = () => {
  return (
    <Button>
      <Shield className="mr-2 h-4 w-4" />
      Add Permission Rule
    </Button>
  );
};