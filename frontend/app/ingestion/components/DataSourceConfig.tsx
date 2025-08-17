// Data Source Configuration Component - Business Value: Multi-source data import capability
// Supports Growth & Enterprise segments with professional data connectivity options

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { IngestionConfig } from '../types';
import { DATA_SOURCES } from '../utils';

interface DataSourceConfigProps {
  config: IngestionConfig;
  onConfigChange: (config: IngestionConfig) => void;
}

export const DataSourceConfig = ({ config, onConfigChange }: DataSourceConfigProps) => {
  return (
    <div className="space-y-6">
      <DataSourceSelector config={config} onConfigChange={onConfigChange} />
      <SourceSpecificConfig config={config} />
      <FormatConfig config={config} onConfigChange={onConfigChange} />
      <ProcessingOptions config={config} onConfigChange={onConfigChange} />
    </div>
  );
};

const DataSourceSelector = ({ config, onConfigChange }: DataSourceConfigProps) => {
  return (
    <div className="grid grid-cols-5 gap-4">
      {DATA_SOURCES.map((source) => (
        <Button
          key={source.id}
          variant={config.dataSource === source.id ? 'default' : 'outline'}
          className="h-24 flex-col gap-2"
          onClick={() => onConfigChange({ ...config, dataSource: source.id })}
        >
          {source.icon}
          <span className="text-xs">{source.label}</span>
        </Button>
      ))}
    </div>
  );
};

const SourceSpecificConfig = ({ config }: { config: IngestionConfig }) => {
  if (config.dataSource === 'database') return <DatabaseConfig />;
  if (config.dataSource === 'api') return <ApiConfig />;
  return null;
};

const DatabaseConfig = () => {
  return (
    <div className="space-y-4">
      <DatabaseTypeSelector />
      <ConnectionStringInput />
      <QueryInput />
    </div>
  );
};

const DatabaseTypeSelector = () => {
  return (
    <div>
      <Label htmlFor="db-type">Database Type</Label>
      <Select defaultValue="postgresql">
        <SelectTrigger id="db-type">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="postgresql">PostgreSQL</SelectItem>
          <SelectItem value="mysql">MySQL</SelectItem>
          <SelectItem value="mongodb">MongoDB</SelectItem>
          <SelectItem value="clickhouse">ClickHouse</SelectItem>
          <SelectItem value="redis">Redis</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
};

const ConnectionStringInput = () => {
  return (
    <div>
      <Label htmlFor="connection-string">Connection String</Label>
      <Input
        id="connection-string"
        type="password"
        placeholder="postgresql://user:password@host:port/database"
      />
    </div>
  );
};

const QueryInput = () => {
  return (
    <div>
      <Label htmlFor="query">Query / Collection</Label>
      <Textarea
        id="query"
        placeholder="SELECT * FROM table_name"
        rows={3}
      />
    </div>
  );
};

const ApiConfig = () => {
  return (
    <div className="space-y-4">
      <ApiEndpointInput />
      <AuthenticationSelector />
      <CustomHeadersInput />
    </div>
  );
};

const ApiEndpointInput = () => {
  return (
    <div>
      <Label htmlFor="api-url">API Endpoint</Label>
      <Input
        id="api-url"
        type="url"
        placeholder="https://api.example.com/data"
      />
    </div>
  );
};

const AuthenticationSelector = () => {
  return (
    <div>
      <Label htmlFor="auth-type">Authentication</Label>
      <Select defaultValue="bearer">
        <SelectTrigger id="auth-type">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="none">None</SelectItem>
          <SelectItem value="bearer">Bearer Token</SelectItem>
          <SelectItem value="apikey">API Key</SelectItem>
          <SelectItem value="oauth2">OAuth 2.0</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
};

const CustomHeadersInput = () => {
  return (
    <div>
      <Label htmlFor="headers">Custom Headers (JSON)</Label>
      <Textarea
        id="headers"
        placeholder='{"X-Custom-Header": "value"}'
        rows={2}
      />
    </div>
  );
};

const FormatConfig = ({ config, onConfigChange }: DataSourceConfigProps) => {
  return (
    <div className="grid grid-cols-2 gap-4">
      <DataFormatSelector config={config} onConfigChange={onConfigChange} />
      <ChunkSizeInput config={config} onConfigChange={onConfigChange} />
    </div>
  );
};

const DataFormatSelector = ({ config, onConfigChange }: DataSourceConfigProps) => {
  return (
    <div>
      <Label htmlFor="format">Data Format</Label>
      <Select 
        value={config.format} 
        onValueChange={(value) => onConfigChange({ ...config, format: value })}
      >
        <SelectTrigger id="format">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="json">JSON</SelectItem>
          <SelectItem value="csv">CSV</SelectItem>
          <SelectItem value="parquet">Parquet</SelectItem>
          <SelectItem value="avro">Avro</SelectItem>
          <SelectItem value="xml">XML</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
};

const ChunkSizeInput = ({ config, onConfigChange }: DataSourceConfigProps) => {
  return (
    <div>
      <Label htmlFor="chunk-size">Chunk Size (KB)</Label>
      <Input
        id="chunk-size"
        type="number"
        value={config.chunkSize}
        onChange={(e) => onConfigChange({ ...config, chunkSize: e.target.value })}
      />
    </div>
  );
};

const ProcessingOptions = ({ config, onConfigChange }: DataSourceConfigProps) => {
  return (
    <div className="space-y-4">
      <ValidationToggle config={config} onConfigChange={onConfigChange} />
      <DeduplicationToggle config={config} onConfigChange={onConfigChange} />
      <CompressionToggle config={config} onConfigChange={onConfigChange} />
    </div>
  );
};

const ValidationToggle = ({ config, onConfigChange }: DataSourceConfigProps) => {
  return (
    <div className="flex items-center justify-between">
      <Label htmlFor="validation">Enable Schema Validation</Label>
      <Switch
        id="validation"
        checked={config.enableValidation}
        onCheckedChange={(checked) => onConfigChange({ ...config, enableValidation: checked })}
      />
    </div>
  );
};

const DeduplicationToggle = ({ config, onConfigChange }: DataSourceConfigProps) => {
  return (
    <div className="flex items-center justify-between">
      <Label htmlFor="deduplication">Enable Deduplication</Label>
      <Switch
        id="deduplication"
        checked={config.enableDeduplication}
        onCheckedChange={(checked) => onConfigChange({ ...config, enableDeduplication: checked })}
      />
    </div>
  );
};

const CompressionToggle = ({ config, onConfigChange }: DataSourceConfigProps) => {
  return (
    <div className="flex items-center justify-between">
      <Label htmlFor="compression">Enable Compression</Label>
      <Switch
        id="compression"
        checked={config.enableCompression}
        onCheckedChange={(checked) => onConfigChange({ ...config, enableCompression: checked })}
      />
    </div>
  );
};