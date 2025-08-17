import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar, HardDrive, BarChart3, RefreshCw, Eye } from 'lucide-react';

export const CorpusVersions = () => {
  return (
    <Card>
      <CardHeader>
        <VersionsHeader />
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <CurrentVersion />
          <PreviousVersion />
        </div>
      </CardContent>
    </Card>
  );
};

const VersionsHeader = () => {
  return (
    <>
      <CardTitle>Version Control</CardTitle>
      <CardDescription>Track and manage different versions of your data</CardDescription>
    </>
  );
};

const CurrentVersion = () => {
  return (
    <div className="border rounded-lg p-4">
      <VersionHeader 
        title="Production Models v3.2"
        subtitle="Current version"
        badge="Active"
      />
      <VersionDetails 
        created="March 15, 2024"
        size="12.4 GB"
        records="45,231 records"
      />
    </div>
  );
};

const PreviousVersion = () => {
  return (
    <div className="border rounded-lg p-4 opacity-75">
      <VersionHeader 
        title="Production Models v3.1"
        subtitle="Previous version"
        badge="Archived"
        variant="secondary"
      />
      <VersionActions />
    </div>
  );
};

const VersionHeader = ({ 
  title, 
  subtitle, 
  badge, 
  variant = "default" 
}: { 
  title: string; 
  subtitle: string; 
  badge: string; 
  variant?: "default" | "secondary";
}) => {
  return (
    <div className="flex justify-between items-start mb-4">
      <div>
        <h3 className="font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{subtitle}</p>
      </div>
      <Badge variant={variant}>{badge}</Badge>
    </div>
  );
};

const VersionDetails = ({ 
  created, 
  size, 
  records 
}: { 
  created: string; 
  size: string; 
  records: string; 
}) => {
  return (
    <div className="space-y-2">
      <VersionDetailItem icon={<Calendar className="h-4 w-4 text-muted-foreground" />} text={`Created: ${created}`} />
      <VersionDetailItem icon={<HardDrive className="h-4 w-4 text-muted-foreground" />} text={`Size: ${size}`} />
      <VersionDetailItem icon={<BarChart3 className="h-4 w-4 text-muted-foreground" />} text={records} />
    </div>
  );
};

const VersionDetailItem = ({ 
  icon, 
  text 
}: { 
  icon: React.ReactNode; 
  text: string; 
}) => {
  return (
    <div className="flex items-center gap-2 text-sm">
      {icon}
      <span>{text}</span>
    </div>
  );
};

const VersionActions = () => {
  return (
    <div className="flex gap-2">
      <Button size="sm" variant="outline">
        <RefreshCw className="mr-2 h-4 w-4" />
        Restore
      </Button>
      <Button size="sm" variant="outline">
        <Eye className="mr-2 h-4 w-4" />
        Compare
      </Button>
    </div>
  );
};