// Settings Tab Component - Business Value: Configurable defaults reduce setup time for repeat users
// Supports Growth & Enterprise segments with operational customization

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';

export const SettingsTab = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Ingestion Settings</CardTitle>
        <CardDescription>Configure default settings for data ingestion</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <GeneralSettings />
        <NotificationSettings />
        <SaveButton />
      </CardContent>
    </Card>
  );
};

const GeneralSettings = () => {
  return (
    <div className="grid grid-cols-2 gap-6">
      <ProcessingModeSelector />
      <ErrorHandlingSelector />
      <ParallelJobsInput />
      <RetentionPeriodInput />
    </div>
  );
};

const ProcessingModeSelector = () => {
  return (
    <div className="space-y-2">
      <Label>Default Processing Mode</Label>
      <Select defaultValue="batch">
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="batch">Batch Processing</SelectItem>
          <SelectItem value="stream">Stream Processing</SelectItem>
          <SelectItem value="micro-batch">Micro-batch</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
};

const ErrorHandlingSelector = () => {
  return (
    <div className="space-y-2">
      <Label>Error Handling</Label>
      <Select defaultValue="skip">
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="skip">Skip Errors</SelectItem>
          <SelectItem value="fail">Fail on Error</SelectItem>
          <SelectItem value="quarantine">Quarantine Failed Records</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
};

const ParallelJobsInput = () => {
  return (
    <div className="space-y-2">
      <Label>Max Parallel Jobs</Label>
      <Input type="number" defaultValue="5" />
    </div>
  );
};

const RetentionPeriodInput = () => {
  return (
    <div className="space-y-2">
      <Label>Retention Period (days)</Label>
      <Input type="number" defaultValue="30" />
    </div>
  );
};

const NotificationSettings = () => {
  return (
    <div className="space-y-4">
      <AutoRetryToggle />
      <NotificationToggle />
      <MonitoringToggle />
    </div>
  );
};

const AutoRetryToggle = () => {
  return (
    <div className="flex items-center justify-between">
      <ToggleDescription 
        title="Auto-retry Failed Jobs"
        description="Automatically retry failed ingestion jobs"
      />
      <Switch defaultChecked />
    </div>
  );
};

const NotificationToggle = () => {
  return (
    <div className="flex items-center justify-between">
      <ToggleDescription 
        title="Send Notifications"
        description="Get notified about ingestion status"
      />
      <Switch defaultChecked />
    </div>
  );
};

const MonitoringToggle = () => {
  return (
    <div className="flex items-center justify-between">
      <ToggleDescription 
        title="Enable Monitoring"
        description="Track detailed metrics and performance"
      />
      <Switch defaultChecked />
    </div>
  );
};

interface ToggleDescriptionProps {
  title: string;
  description: string;
}

const ToggleDescription = ({ title, description }: ToggleDescriptionProps) => {
  return (
    <div>
      <p className="font-medium">{title}</p>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
};

const SaveButton = () => {
  return <Button>Save Settings</Button>;
};